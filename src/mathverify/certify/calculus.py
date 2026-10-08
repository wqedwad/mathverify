"""Calculus certificates (E3, E8): derivative certificate for antiderivatives, breakpoint-aware
tanh-sinh numeric definite integrals with a precision ladder, derivatives, tangent lines.

Audit of 25 Sep 2026 (each item was measured as a false verdict before the change):
  * a derivative at a point is certified only when f is differentiable there: SymPy's sign(0) = 0
    and Heaviside(0) = 1/2 made "d/dx |x| at 0 = 0" and "the tangent to |x| at 0 is y = 0" CORRECT;
  * an antiderivative must be real and continuous wherever the integrand is defined: "∫ 1/x = log x",
    "∫ 1/(1+x²) = -atan(1/x)" and the tan(x/2) form of ∫ 1/(2+cos x) passed on a zero residual;
  * the constant C must enter additively: "∫ cos = sin(x + C)" passed with C replaced by 0;
  * a tangent line is compared as a LINE: "(y - 2x + 1)(y - 5) = 0" passed as the tangent to x² at 1;
  * a definite integral with an exact value is compared exactly (a 1e-25 tolerance accepted
    e^(π√163) - 1 ≈ 262537412640768743), and a numeric value that did not converge never refutes;
  * SymPy's distributional derivative (DiracDelta, Heaviside) is read classically.

Fourth audit of 1 Oct 2026: numbers never ACCEPT a definite integral. An exact value is SymPy's,
confirmed by the quadrature, or one proved symbolically (`certified_integral_value`: the integrand is
0, odd about the midpoint and absolutely integrable, or an antiderivative checked by differentiation
and continuous on the range); SymPy's 0 counts only when proved. Numbers alone decide only through a
rigorous enclosure (`certify.enclosure`, interval arithmetic; review of d4c, 2 Oct 2026): a claim outside
it is refuted, an approximate claim whose declared tolerance holds it is accepted.
"""
from __future__ import annotations

import itertools
import re
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S, Eq, Ne, Interval, oo

from ..equiv import _equals_false_stands, answers_equivalent
from ..equiv.numeric import NONREAL, certified_sign, is_number_expr, num_equal, read_tolerance, to_mp, within_rel_tol
from ..equiv.random_point import random_point_equal
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied
from .domain import (definedness_conditions, written_definedness, written_undefined_in, relation_holds_at,
                     in_domain)
from .limits import membership_conditions, membership_holds_on, neighbourhoods, written_undefined_everywhere

LAYER = "certify.calculus"


# ---------------------------------------------------------------------------
def classical(expr):
    """SymPy differentiates Abs/Max/sign as distributions: DiracDelta terms and Heaviside steps.
    Classically the DiracDelta terms vanish off their (isolated) support, where the classical
    derivative does not exist anyway, and Heaviside(u) is (1 + sign(u))/2 off u = 0. Neither can
    be evaluated numerically, and random-point equality read that as "undefined on one side" and
    refuted right answers (measured: (x|x|)'' = 2 sign(x), ∫ 1/x² = -1/x + sign(x))."""
    expr = sp.sympify(expr)
    if expr.has(sp.DiracDelta):
        expr = expr.replace(lambda e: isinstance(e, sp.DiracDelta), lambda e: S.Zero)
    if expr.has(sp.Heaviside):
        expr = expr.replace(lambda e: isinstance(e, sp.Heaviside), lambda e: (1 + sp.sign(e.args[0])) / 2)
    return expr


def _real_finite(v) -> bool | None:
    try:
        v = sp.sympify(v)
        if v.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or v.free_symbols:
            return False
        m = to_mp(v, 30)
    except Exception:  # noqa: BLE001
        return None
    return not isinstance(m, mp.mpc) and mp.isfinite(m)


# ---------------------------------------------------------------------------
def find_breakpoints(expr, var, a, b, timeout: float = 8.0) -> list:
    r = sb_run("mathverify.sandbox.ops:breakpoints_of", sp.sympify(expr), var, sp.sympify(a), sp.sympify(b),
               timeout=timeout)
    if not r.ok:
        return []
    return [p for p in r.value if a < p < b]


def definite_integral_numeric(integrand, var, a, b, timeout: float = 12.0) -> tuple[sp.Float | None, dict[str, Any]]:
    """tanh-sinh with breakpoints on a precision ladder (30 -> 50 -> 80 digits).

    Converged when two successive levels agree within 10x the larger error estimate (plus the
    rounding of the LOWER level's printed value) and that estimate is below 1e-18 relative. The
    returned evidence carries `rel_err`, the relative tolerance the caller must use when comparing
    a claim with the value — never a fixed 1e-12 (E3). Gauss–Legendre is deliberately NOT used:
    measured to be off by 5e-3 on the endpoint-singular ln x/sqrt x.
    """
    ev: dict[str, Any] = {"integrand": str(integrand), "a": str(a), "b": str(b)}
    if isinstance(integrand, sp.Basic) and integrand.has(sp.Integral, sp.Sum, sp.Product, sp.Limit):
        # a form inside the integrand is evaluated by its own quadrature or summation, whose error
        # the ladder does not see: the constant ∫|cos t| over [-pi, pi] came out 3.99999920... at 30
        # and at 50 digits, "converged", and the true value 4 was refuted (audit of 29 Sep 2026)
        ev["error"] = "a form inside the integrand has no confirmed numeric value"
        return None, ev
    a, b = sp.sympify(a), sp.sympify(b)
    pts = find_breakpoints(integrand, var, a, b, timeout)
    ev["breakpoints"] = pts
    ladder: list[tuple[int, str, str]] = []
    ev["ladder"] = []
    prev = None
    converged = False
    for dps in (30, 50, 80):
        r = sb_run("mathverify.sandbox.ops:quad_breakpoints", sp.sympify(integrand), var, a, b, pts, dps,
                   "tanh-sinh", timeout=timeout * (2 if dps == 80 else 1))
        if not r.ok:
            if not ladder:
                ev["error"] = r.error
                ev["flags"] = r.flags
                return None, ev
            ev.setdefault("flags", []).extend(r.flags)
            break
        val_s, err_s = r.value
        ladder.append((dps, val_s, err_s))
        ev["ladder"].append({"dps": dps, "value": val_s, "err": err_s})
        with mp.workdps(dps + 10):
            v = mp.mpf(val_s)
            err = abs(mp.mpf(err_s)) if err_s not in (None, "None") else mp.mpf(1)
            scale = max(abs(v), mp.mpf(1))
            if prev is not None:
                pv, perr, pdps = prev
                # the previous value was printed with only `pdps` digits: its rounding is part of
                # the comparison. With 10^-(dps-5) instead, ∫_0^1 x^2 never "converged" (its
                # 30-digit value differs from the 50-digit one by 3e-31, measured 25 Sep 2026)
                agree = abs(v - pv) / scale <= 10 * max(err, perr) / scale + mp.mpf(10) ** (-(pdps - 5))
                if agree and err / scale < mp.mpf("1e-18"):
                    converged = True
                    prev = (v, err, dps)
                    break
            prev = (v, err, dps)
    v, err, _ = prev
    with mp.workdps(90):
        scale = max(abs(v), mp.mpf(1))
        rel_err = max(10 * err / scale, mp.mpf("1e-25"))
    ev["converged"] = converged
    ev["rel_err"] = mp.nstr(rel_err, 5)
    ev["value"] = mp.nstr(v, 40)
    return sp.Float(mp.nstr(v, 60), 60), ev


# ---------------------------------------------------------------------------
# An exact 0 for a definite integral (fourth audit of 1 Oct 2026, S1/S6). No number proves that an
# integral is 0: ∫_0^{2π} e^(cos x)·cos 50x dx = 2π·I_50(1) = 1.8e-79 sat below 10^-70·∫|f| at every
# rung of the old residue test and the claim 0 was certified, as was SymPy's wrong 0 for
# ∫_{-1}^{1} (x + |cos x|/10^80) dx. The residue test only BOUNDS the value; 0 is taken with a symbolic
# certificate: the integrand is 0, the integral is odd about the midpoint of the range and absolutely
# convergent, or an antiderivative checked by differentiation is continuous on the range and takes
# the same value at both ends (the fundamental theorem of calculus).
_JUMPY = (sp.floor, sp.ceiling, sp.frac, sp.Piecewise, sp.Heaviside, sp.DiracDelta, sp.Mod)
# a primitive that jumps: SymPy's acot jumps from -π/2 to π/2 at 0
_PRIMITIVE_JUMPS = _JUMPY + (sp.sign, sp.acot)
_LOCAL_EXPONENTS = (S.Zero, S.Half, sp.Rational(2, 3), sp.Rational(3, 4), sp.Rational(4, 5), sp.Rational(9, 10))
_TAIL_EXPONENTS = (sp.Integer(2), sp.Rational(3, 2), sp.Rational(6, 5))


def _exact_conditions(e, var) -> list | None:
    """The conditions for `e` to be a real number, EXACT or None (`definedness_conditions_strict`),
    with a fractional power read as real only for a base >= 0 (> 0 when the exponent is negative):
    SymPy's x**(1/3) is complex for x < 0, and no condition said so. The odd-root convention of such a power
    (`Contains(b, Convention(odd_root))`: the real root or the principal value at b < 0) is met by that rule
    for that very base: on b >= 0 the two readings are one value. It had made every certificate with t**(1/3)
    fail, ∫_0^∞ e^(-t^(1/3)) dt = 6 among them (merge of d4c round 3 with d4a, BİRLEŞİK-1)."""
    from .domain import Convention, definedness_conditions_strict
    conds = definedness_conditions_strict(e, var)
    if conds is None:
        return None
    fractional = {node.base for node in sp.preorder_traversal(e) if isinstance(node, sp.Pow)
                  and node.base.has(var) and node.exp.is_Rational and not node.exp.is_Integer}
    out: list = []
    for c in conds:
        if c is sp.true:
            continue
        if isinstance(c, sp.Contains) and isinstance(c.args[1], Convention) and c.args[1].kind == "odd_root" \
                and c.args[0] in fractional:
            continue                                  # the fractional power rule below holds it
        if not getattr(c, "free_symbols", None):
            return None                               # a constant condition: no rule decides it here
        if c.free_symbols != {var} or not isinstance(c, sp.core.relational.Relational):
            return None
        out.append(c)
    for node in sp.preorder_traversal(e):
        if isinstance(node, sp.Pow) and node.base.has(var):
            ex = node.exp
            if not ex.is_number:
                return None
            if ex.is_Rational and not ex.is_Integer:
                c = node.base >= 0 if ex > 0 else node.base > 0
                if c is sp.false:
                    return None
                if c is not sp.true and c not in out:
                    out.append(c)
    return out


def _bad_points(e, var, lo, hi, timeout) -> list | None:
    """The points of [lo, hi] where `e` is not a real number: a finite list, or None (not computable,
    or a piece of positive length)."""
    conds = _exact_conditions(e, var)
    if conds is None:
        return None
    region = sp.Interval(lo, hi)
    pts: list = []
    for c in conds:
        neg = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else c.negated
        r = sb_run("mathverify.sandbox.ops:solveset_in", neg, var, region, timeout=timeout)
        if not r.ok or not isinstance(r.value, (sp.FiniteSet, type(S.EmptySet))):
            return None
        for p in r.value:
            if not (getattr(p, "is_number", False) and p.is_real):
                return None
            if not any(p == q for q in pts):
                pts.append(p)
    return pts


def _switch_points(e, var, lo, hi, timeout) -> list | None:
    """Points of (lo, hi) where Abs/sign/Max/Min in `e` can change branch (finite), or None."""
    from ..equiv.random_point import _nonsmooth
    eqs = []
    for n in _nonsmooth(e):
        if isinstance(n, (sp.Abs, sp.sign)):
            eqs.append(n.args[0])
        elif isinstance(n, (sp.Max, sp.Min)):
            args = list(n.args)
            eqs += [args[i] - args[j] for i in range(len(args)) for j in range(i + 1, len(args))]
        else:
            return None
    pts: list = []
    for g in eqs:
        if not g.has(var):
            continue
        r = sb_run("mathverify.sandbox.ops:solveset_in", Eq(g, 0), var, sp.Interval.open(lo, hi), timeout=timeout)
        if not r.ok or not isinstance(r.value, (sp.FiniteSet, type(S.EmptySet))):
            return None
        for p in r.value:
            if not (getattr(p, "is_number", False) and p.is_real):
                return None
            if not any(p == q for q in pts):
                pts.append(p)
    try:
        return sorted(pts, key=lambda p: float(p))
    except (TypeError, ValueError):
        return None


def deep_probe(expr, var, point, side, dps: int = 100) -> list[str | None]:
    """Sandbox worker: expr at point ± 10^-k (or at ±10^k for an infinite point), k = 15, 30, 45, 60."""
    f = sp.lambdify(var, expr, "mpmath")
    out: list[str | None] = []
    with mp.workdps(dps):
        if point in (sp.oo, -sp.oo):
            xs = [mp.mpf(10) ** k * (1 if point == sp.oo else -1) for k in (15, 30, 45, 60)]
        else:
            p = mp.mpf(str(sp.N(point, dps + 5)))
            xs = [p + (1 if side == "+" else -1) * mp.mpf(10) ** (-k) for k in (15, 30, 45, 60)]
        for xv in xs:
            try:
                v = mp.mpmathify(f(xv))
                out.append(None if isinstance(v, mp.mpc) or not mp.isfinite(v) else mp.nstr(v, 30))
            except Exception:  # noqa: BLE001
                out.append(None)
    return out


def _finite_limit(e, var, point, side, timeout):
    """SymPy's one-sided limit, corroborated numerically (`classify_limit`), when it is finite. A limit
    approached slowly (√x·ln x at 0 is -5.5e-5 at x = 10^-12, beyond `classify_limit`'s probe) is
    corroborated further in: at 10^-15 ... 10^-60 its distance to SymPy's value must shrink to 10^-8."""
    from .limits import classify_limit
    inf = point in (sp.oo, -sp.oo)
    cls = classify_limit(e, var, point, None if inf else side, timeout=timeout)
    v = cls.get("value")
    if cls.get("kind") == "VAR" and v is not None and _real_finite(v) is True:
        return v
    if cls.get("kind") != "UNKNOWN" or "symbolic_numeric_disagreement" not in (cls.get("flags") or []):
        return None
    v = cls.get("right") if (side == "+" if not inf else point == -sp.oo) else cls.get("left")
    if v is None or _real_finite(v) is not True:
        return None
    r = sb_run("mathverify.certify.calculus:deep_probe", e, var, point, side, timeout=timeout)
    if not r.ok or any(x_ is None for x_ in r.value):
        return None
    with mp.workdps(40):
        target = to_mp(v, 40)
        gaps = [abs(mp.mpf(x_) - target) for x_ in r.value]
        if all(g2 <= g1 for g1, g2 in zip(gaps, gaps[1:])) and gaps[-1] <= mp.mpf("1e-8") * max(1, abs(target)):
            return v
    return None


def _absolutely_integrable(f, var, lo, hi, timeout) -> bool:
    """Is ∫_lo^hi |f| finite? f is real and continuous off finitely many points of [lo, hi] (up to the
    bounded jumps of sign), and near each such point p, |f|·|x - p|^β has a finite limit for some
    β < 1 (at an infinite end, |f|·|x|^β for some β > 1): then |f| <= C·|x - p|^(-β) there."""
    if f.has(*_JUMPY):
        return False
    pts = _bad_points(f, var, lo, hi, timeout)
    if pts is None:
        return False
    for p in pts:
        for side in ("+", "-"):
            if (side == "+" and p == hi) or (side == "-" and p == lo):
                continue
            if not any(_finite_limit(sp.Abs(f) * sp.Abs(var - p) ** beta, var, p, side, timeout) is not None
                       for beta in _LOCAL_EXPONENTS):
                return False
    for end in (lo, hi):
        if end in (sp.oo, -sp.oo) and not any(
                _finite_limit(sp.Abs(f) * sp.Abs(var) ** beta, var, end, None, timeout) is not None
                for beta in _TAIL_EXPONENTS):
            return False
    return True


def _primitive_difference(g, var, p, q, timeout):
    """F(q) - F(p) for SymPy's antiderivative F of a SMOOTH g on [p, q], or None. Taken only when
    F' - g is 0 symbolically, F is real and continuous on [p, q] (its conditions fail at most at an
    end, where its one-sided limit is finite), and g and F' fail at finitely many points: F is then
    continuous on [p, q] and differentiable off a finite set with F' = g, so ∫_p^q g = F(q) - F(p).
    SymPy's default antiderivative of ln x/√x is a Meijer-G Piecewise; its manual one, 2√x·ln x - 4√x,
    is tried too."""
    r = sb_run("mathverify.sandbox.ops:antiderivatives", g, var, timeout=timeout)
    if not r.ok or not isinstance(r.value, list):
        return None
    for F in r.value[:2]:
        v = _checked_difference(F, g, var, p, q, timeout)
        if v is None:
            R = _real_primitive(F, var, p, q)
            if R is not None and R != F:
                v = _checked_difference(R, g, var, p, q, timeout)
        if v is not None:
            return v
    return None


def _real_on(u, var, p, q, pieces: int = 64):
    """Interval (lo, hi) of the real expression u over [p, q] (finite ends; the hull of `pieces` cells), or None."""
    from .enclosure import _ends, _hull, constant_interval, iv_eval
    ip, iq = constant_interval(p), constant_interval(q)
    if ip is None or iq is None or not ip[1] < iq[0]:
        return None
    saved = mp.iv.dps
    try:
        mp.iv.dps = 30
        with mp.workdps(30):
            lo_, hi_ = mp.inf, -mp.inf
            ends = [ip[0]] + [ip[1] + (iq[0] - ip[1]) * k / pieces for k in range(1, pieces)] + [iq[1]]
            for l_, r_ in zip(ends, ends[1:]):
                a_, b_ = _ends(iv_eval(u, {var: _hull(l_, r_)}))
                lo_, hi_ = min(lo_, a_), max(hi_, b_)
            return lo_, hi_
    except (ArithmeticError, ValueError, TypeError, AttributeError):
        return None
    finally:
        mp.iv.dps = saved


def _real_primitive(F, var, p, q):
    """SymPy's complex-valued primitive written as a real one on [p, q], or None: log(u) with u < 0 on all of
    [p, q] (certified by interval arithmetic) as log(-u), the same derivative and real there; exp_polar(iπk) in a
    polylog's argument as (-1)^k (any other exp_polar: None). The result is only a candidate: `_checked_difference`
    proves its derivative and its continuity, and a polylog's argument past 1, where Li_s is complex, fails the
    definedness rule there (`domain.definedness_conditions_strict`: z <= 1). SymPy's primitives of 1/x on [-2, -1],
    1/(x - 2), sec x, tan x on (π/2, π) and ln(1 + x)/x were never real there, and the textbook values -ln 2,
    ln(1 + √2), π²/12 had no certificate (attack on d4c round 3, KK-1)."""
    if not isinstance(F, sp.Basic):
        return None
    reps = {}
    for n in F.atoms(sp.exp_polar):
        k = sp.simplify(n.args[0] / (sp.I * sp.pi))
        if not k.is_Integer:
            return None
        reps[n] = sp.Integer(-1) ** k
    R = F.xreplace(reps) if reps else F
    if R.has(sp.exp_polar):
        return None
    logs = {}
    for n in R.atoms(sp.log):
        box = _real_on(n.args[0], var, p, q)
        if box is not None and box[1] < 0:
            logs[n] = sp.log(-n.args[0])
    return R.xreplace(logs) if logs else R


def _checked_difference(F, g, var, p, q, timeout):
    """F(q) - F(p) when F is an antiderivative of g continuous on [p, q] (`_primitive_difference`)."""
    if not isinstance(F, sp.Basic):
        return None
    if F.has(sp.Integral) or F.has(*_PRIMITIVE_JUMPS) or F.has(sp.Abs, sp.Max, sp.Min) \
            or F.free_symbols - {var} or F.has(sp.zoo, sp.nan, sp.I):
        return None
    rd = sb_run("mathverify.sandbox.ops:diff_expr", F, var, 1, timeout=timeout)
    if not rd.ok:
        return None
    # Li_1(z) = -log(1 - z): SymPy leaves the derivative of Li_2 as polylog(1, ·), which simplify does not reduce
    dF = rd.value.replace(lambda n: isinstance(n, sp.polylog) and n.args[0] == 1, lambda n: -sp.log(1 - n.args[1]))
    rs = sb_run("mathverify.sandbox.ops:simplify_diff", dF, g, timeout=timeout)
    if not rs.ok or rs.value != 0:
        return None
    bad_F = _bad_points(F, var, p, q, timeout)
    if bad_F is None or any(x_ != p and x_ != q for x_ in bad_F):
        return None
    if _bad_points(g, var, p, q, timeout) is None or _bad_points(dF, var, p, q, timeout) is None:
        return None
    vals = []
    for end, side in ((p, "+"), (q, "-")):
        v = None
        if end not in (sp.oo, -sp.oo) and not any(end == x_ for x_ in bad_F):
            v = F.subs(var, end)
            v = v if _real_finite(v) is True else None
        if v is None:
            # an end where F has no value (0 for a positive variable): its one-sided limit
            v = _finite_limit(F, var, end, side, timeout)
        if v is None:
            return None
        vals.append(v)
    return vals[1] - vals[0]


def _fundamental_theorem_value(f, var, lo, hi, timeout):
    """∫_lo^hi f by the fundamental theorem of calculus, split where Abs/sign/Max/Min switch branch
    (on each piece f is the analytic branch it takes there), or None."""
    from ..equiv.random_point import _nonsmooth, _smooth_on_cell
    cuts = _switch_points(f, var, lo, hi, timeout) if _nonsmooth(f) else []
    if cuts is None or len(cuts) > 12:
        return None
    ends = [lo] + cuts + [hi]
    total = S.Zero
    for p, q in zip(ends, ends[1:]):
        g = f
        if _nonsmooth(f):
            mid = (p + q) / 2 if p.is_finite and q.is_finite else (q - 1 if p == -sp.oo else p + 1)
            if mid in (sp.oo, -sp.oo):
                mid = S.Zero
            g = _smooth_on_cell(f, var, mid)
            if g is None:
                return None
        v = _primitive_difference(g, var, p, q, timeout)
        if v is None:
            return None
        total += v
    return total


def certified_integral_value(integrand, var, a, b, timeout: float = 8.0) -> tuple[Any, dict[str, Any]]:
    """(value, evidence): ∫_a^b f PROVED symbolically, or (None, evidence). 0 when the integrand is 0
    or odd about the midpoint of the range and absolutely integrable; otherwise F(b) - F(a) for an
    antiderivative F checked by differentiation and continuous on the range (the fundamental theorem
    of calculus). See the comment above `_exact_conditions`."""
    ev: dict[str, Any] = {"integrand": str(integrand), "a": str(a), "b": str(b)}
    try:
        f, a, b = sp.sympify(integrand), sp.sympify(a), sp.sympify(b)
    except (sp.SympifyError, TypeError):
        return None, ev
    if f.has(sp.Integral, sp.Sum, sp.Product, sp.Limit) or f.free_symbols - {var} \
            or (a.free_symbols | b.free_symbols) or a.has(sp.zoo, sp.nan) or b.has(sp.zoo, sp.nan):
        ev["reason"] = "not_a_closed_integral_of_one_variable"
        return None, ev
    if f == 0 or a == b:
        ev["certificate"] = "identically_zero"
        return S.Zero, ev
    if not (a.is_comparable and b.is_comparable):
        ev["reason"] = "range_not_comparable"
        return None, ev
    sign = 1
    if bool(a > b):
        a, b, sign = b, a, -1
    rz = sb_run("mathverify.sandbox.ops:simplify_diff", f, S.Zero, timeout=timeout)
    if rz.ok and rz.value == 0:
        ev["certificate"] = "identically_zero"
        return S.Zero, ev
    # odd about the midpoint: f(a + b - x) = -f(x) (f(-x) = -f(x) on the whole line)
    mirror = -var if (a, b) == (-sp.oo, sp.oo) else (a + b - var if a.is_finite and b.is_finite else None)
    even = None
    if mirror is not None:
        rs = sb_run("mathverify.sandbox.ops:simplify_diff", f.xreplace({var: mirror}), -f, timeout=timeout)
        if rs.ok and rs.value == 0:
            if _absolutely_integrable(f, var, a, b, timeout):
                ev["certificate"] = "odd_about_the_midpoint_and_absolutely_integrable"
                return S.Zero, ev
            ev["odd"] = "absolute_convergence_not_proved"
        elif rs.ok and isinstance(rs.value, sp.Basic) and not rs.value.has(sp.zoo, sp.nan):
            even = rs.value / 2                  # (f(x) + f(a + b - x))/2, the part about the midpoint
    v = _fundamental_theorem_value(f, var, a, b, timeout)
    if v is None and even is not None and (a, b) != (-sp.oo, sp.oo):
        # ∫_a^b f = ∫_a^b (f(x) + f(a + b - x))/2 for an absolutely integrable f: the odd part of
        # sin(x^5)·e^(cos x) + 1 on [-1, 1] has no antiderivative, the even part is 1
        v = _fundamental_theorem_value(even, var, a, b, timeout)
        if v is not None and not _absolutely_integrable(f, var, a, b, timeout):
            v = None
        if v is not None:
            ev["symmetrized"] = str(even)
    if v is not None:
        ev["certificate"] = "fundamental_theorem_of_calculus"
        ev["value"] = str(sign * v)
        return sign * v, ev
    ev["reason"] = ev.get("odd") or "no_certificate"
    return None, ev


def zero_integral_certificate(integrand, var, a, b, timeout: float = 8.0) -> tuple[bool | None, dict[str, Any]]:
    """True when ∫_a^b f = 0 is PROVED symbolically (`certified_integral_value`), else None (never
    False: the absence of a proof says nothing about the value)."""
    v, ev = certified_integral_value(integrand, var, a, b, timeout)
    if v is not None and certified_sign(v, timeout=timeout) == 0:
        return True, ev
    return None, ev


# ---------------------------------------------------------------------------
# Numbers decide a definite integral only through a RIGOROUS enclosure (`certify.enclosure`: interval
# arithmetic on cells, outward rounding). A quadrature's error estimate is no proof: tanh-sinh and
# Gauss-Legendre missed the peak e^(-10^8 (x - 1/3)^2) together, and with an error estimate small but not 0
# the true value of ∫_0^1 (x² + 10^4 sech²(10^4 (x - 1/3))) dx was refuted (review of d4c, 2 Oct 2026). A
# claim outside the enclosure is refuted; an approximate claim whose tolerance window holds the enclosure
# is accepted; anything else, and every infinite range, decides nothing.
def claim_interval(claimed):
    """(lo, hi) mpf holding the constant `claimed` (interval arithmetic, else strict evalf), or None."""
    from .enclosure import constant_interval
    try:
        c = sp.sympify(claimed)
    except (sp.SympifyError, TypeError):
        return None
    if c.free_symbols or c.has(sp.Integral, sp.Sum, sp.Product, sp.Limit, sp.zoo, sp.nan):
        return None
    if c in (sp.oo, -sp.oo):
        return (mp.inf, mp.inf) if c is sp.oo else (-mp.inf, -mp.inf)
    out = constant_interval(c)
    if out is not None:
        return out
    from sympy.core.evalf import PrecisionExhausted
    try:
        v = c.evalf(40, strict=True)
        if not v.is_Float:
            return None
        m = mp.mpf(v._mpf_)
    except (PrecisionExhausted, TypeError, ValueError, AttributeError):
        return None
    with mp.workdps(60):
        eps = mp.mpf(10) ** -35 * (1 + abs(m))
        return m - eps, m + eps


def _raw_pair(lo, hi):
    from .enclosure import _raw
    return _raw(mp.mpf(lo)), _raw(mp.mpf(hi))


_ENCLOSURE_SAFETY = 120.0       # seconds: past it an enclosure is abandoned (UNKNOWN), never cut short


def rigorous_integral(integrand, var, a, b, outside=None, inside=None, timeout: float = 8.0):
    """(lo, hi) mpf: an interval holding ∫_a^b f, refined until it misses `outside` or lies within
    `inside` ((lo, hi) mpf pairs) or the budget is spent; None without an enclosure (an infinite range,
    an operation with no interval extension). The ends may be infinite (a singularity)."""
    from .enclosure import from_raw
    try:
        f, a, b = sp.sympify(integrand), sp.sympify(a), sp.sympify(b)
    except (sp.SympifyError, TypeError):
        return None
    if f.has(sp.Integral, sp.Sum, sp.Product, sp.Limit) or not (a.is_finite and b.is_finite):
        return None
    # the budget is the number of cells (deterministic); the time is only a safety stop (RK-C)
    r = sb_run("mathverify.certify.enclosure:rigorous_enclosure", f, var, a, b,
               _raw_pair(*outside) if outside else None, _raw_pair(*inside) if inside else None,
               4000, _ENCLOSURE_SAFETY, timeout=_ENCLOSURE_SAFETY + 10)
    if not r.ok or r.value is None:
        return None
    return from_raw(r.value[0]), from_raw(r.value[1])


def integral_excludes(integrand, var, a, b, claimed, timeout: float = 8.0) -> tuple[bool, dict[str, Any]]:
    """Is the claimed number certainly not ∫_a^b f (outside a rigorous enclosure)?"""
    ev: dict[str, Any] = {}
    c = claim_interval(claimed)
    if c is None:
        ev["claim_interval"] = None
        return False, ev
    enc = rigorous_integral(integrand, var, a, b, outside=c, timeout=timeout)
    ev["enclosure"] = None if enc is None else [mp.nstr(enc[0], 15), mp.nstr(enc[1], 15)]
    if enc is None:
        return False, ev
    lo, hi = enc
    return bool(hi < c[0] or lo > c[1]), ev


def tolerance_by_enclosure(integrand, var, a, b, claimed, rel_tol, timeout: float = 8.0
                           ) -> tuple[bool | None, dict[str, Any]]:
    """The declared relative tolerance decided over a rigorous enclosure E of the integral: |c - v| <= t·|v|
    for every v in E (True), for none (False), or undecided (None; also when E holds 0, where a relative
    tolerance means nothing). For c > 0 the values v the claim stands for are [c/(1 + t), c/(1 - t)] (for
    c < 0 the mirror image), computed with interval arithmetic over the claim's own interval: the window
    was [c - t|c|, c + t|c|], scaled by the claim, and with t >= 1 it held any value (YO-4, RK-E)."""
    ev: dict[str, Any] = {}
    c = claim_interval(claimed)
    if c is not None and not (mp.isfinite(c[0]) and mp.isfinite(c[1])):
        # an infinite claim: any finite enclosure refutes it (SG-1)
        no, xev = integral_excludes(integrand, var, a, b, claimed, timeout=timeout)
        ev.update(xev)
        return (False if no else None), ev
    if c is None:
        im = _imaginary_part(claimed)
        if im is not None:
            # |c - v| >= |Im c| > t·|v| for every real v of an enclosure E: refuted when |Im c| - t·max|E| > 0 is
            # certified (SG-1); E is refined until it lies inside (-|Im c|/t, |Im c|/t) or misses it
            si, im_c = im
            t_ = sp.Rational(rel_tol)
            with mp.workdps(30):
                far = abs(to_mp(im_c, 30)) * (1 - mp.mpf(10) ** -10) / mp.mpf(t_.p) * t_.q
            enc = rigorous_integral(integrand, var, a, b, outside=(-far, far), inside=(-far, far), timeout=timeout)
            ev["enclosure"] = None if enc is None else [mp.nstr(enc[0], 15), mp.nstr(enc[1], 15)]
            if enc is not None and mp.isfinite(enc[0]) and mp.isfinite(enc[1]):
                B = max(_mpf_rational(abs(enc[0])), _mpf_rational(abs(enc[1])))
                if certified_sign(si * im_c - t_ * B) == 1:
                    ev["reason"] = "imaginary_part_beyond_the_tolerance"
                    return False, ev
    if c is None or c[0] <= 0 <= c[1]:
        ev["reason"] = "claim_not_a_nonzero_number"
        return None, ev
    iv, saved = mp.iv, mp.iv.dps
    try:
        iv.dps = 60
        with mp.workdps(60):
            C = iv.mpf([c[0], c[1]])
            t_ = sp.Rational(rel_tol)
            T = iv.mpf(int(t_.p)) / int(t_.q)
            lo_v, hi_v = (C / (1 + T), C / (1 - T)) if c[0] > 0 else (C / (1 - T), C / (1 + T))
            # every v in `inside` is within the tolerance of every c; no v outside `outside` is within it of any c
            inside = (mp.make_mpf(lo_v._mpi_[1]), mp.make_mpf(hi_v._mpi_[0]))
            outside = (mp.make_mpf(lo_v._mpi_[0]), mp.make_mpf(hi_v._mpi_[1]))
    finally:
        iv.dps = saved
    enc = rigorous_integral(integrand, var, a, b, outside=outside, inside=inside if inside[0] <= inside[1] else None,
                            timeout=timeout)
    ev["enclosure"] = None if enc is None else [mp.nstr(enc[0], 15), mp.nstr(enc[1], 15)]
    ev["values_within_tolerance"] = [mp.nstr(outside[0], 15), mp.nstr(outside[1], 15)]
    if enc is None:
        return None, ev
    lo, hi = enc
    if lo <= 0 <= hi:
        ev["reason"] = "enclosure_holds_zero"
        return None, ev
    if inside[0] <= lo and hi <= inside[1]:
        return True, ev
    if hi < outside[0] or lo > outside[1]:
        return False, ev
    return None, ev


def _imaginary_part(claimed):
    """(sign, Im c) for a closed claim c whose imaginary part is certified nonzero, else None."""
    try:
        c = sp.sympify(claimed)
        if not is_number_expr(c) or c.has(sp.oo, -sp.oo, sp.zoo, sp.nan):
            return None
        im_c = sp.im(c)
        si = certified_sign(im_c)
        return (si, im_c) if si in (1, -1) else None
    except (sp.SympifyError, TypeError, ValueError, ArithmeticError, AttributeError):
        return None


def _mpf_rational(x):
    """The binary number x (finite mpf) as an exact Rational."""
    m, e = mp.mpf(x).man_exp
    return sp.Integer(m) * sp.Integer(2) ** e


def integrand_undefined_on_a_subinterval(src, expr, var, a, b, ns, timeout: float = 8.0,
                                         pins: dict | None = None) -> bool | None:
    """Is the integrand, as written or as parsed, undefined on a piece of (a, b) of positive
    length? Isolated points are fine (improper integrals). exp(log(x)) parses to x, and
    "∫_{-2}^{-1} exp(log x) dx = -3/2" was certified (audit of 25 Sep 2026). The written conditions are
    read with the values `pins` holds; one that still names another symbol leaves it undecided (None)."""
    ineq = (sp.StrictLessThan, sp.LessThan, sp.StrictGreaterThan, sp.GreaterThan)
    conds = [c for c in list(written_definedness(src, ns, pins)[0]) + list(definedness_conditions(expr, var))
             if isinstance(c, ineq) and var in c.free_symbols]
    if any(c.free_symbols != {var} for c in conds):
        return None
    if not conds:
        return False
    lo, hi = sp.Min(a, b), sp.Max(a, b)
    region = sp.Interval.open(lo, hi)
    for c in conds:
        r = sb_run("mathverify.sandbox.ops:solveset_in", c.negated, var, region, timeout=timeout)
        if not r.ok or r.value.has(sp.ConditionSet):
            return None
        bad = r.value
        if bad is S.EmptySet or isinstance(bad, sp.FiniteSet):
            continue
        try:
            m = bad.measure
        except Exception:  # noqa: BLE001
            return None
        if m.is_positive:
            return True
        if not m.is_zero:
            return None
    return False


# ---------------------------------------------------------------------------
def _normal_condition(c):
    """`|u| > 0` and `u**2 > 0` say `u != 0`; spell them that way so they match the integrand's."""
    if isinstance(c, sp.StrictGreaterThan) and c.rhs == 0:
        u = c.lhs
        if isinstance(u, sp.Abs):
            return Ne(u.args[0], 0)
        if isinstance(u, sp.Pow) and u.exp.is_Integer and u.exp.is_even and u.exp > 0:
            return Ne(u.base, 0)
    if isinstance(c, Ne) and c.rhs == 0 and isinstance(c.lhs, sp.Abs):
        return Ne(c.lhs.args[0], 0)
    return c


def _conditions(expr, var, extra=()) -> list[Any] | None:
    out: list[Any] = []
    for c in list(definedness_conditions(expr, var)) + list(extra):
        fs = getattr(c, "free_symbols", set())
        if not fs:
            continue
        if fs != {var}:
            return None                       # a parameter: the check below cannot decide it
        c = _normal_condition(c)
        if c not in out:
            out.append(c)
    return out


def _points_of(s_, k: int = 4) -> list:
    """A few concrete points of a solveset result (witness candidates)."""
    out: list = []
    try:
        if isinstance(s_, sp.FiniteSet):
            out = [e for e in s_.args if e.is_number][:k]
        elif isinstance(s_, sp.Interval):
            lo, hi = s_.inf, s_.sup
            if lo == -sp.oo and hi == sp.oo:
                out = [S.Zero, S.One, -S.One]
            elif lo == -sp.oo:
                out = [hi - 1, hi - sp.Rational(1, 7)]
            elif hi == sp.oo:
                out = [lo + 1, lo + sp.Rational(1, 7)]
            else:
                out = [(lo + hi) / 2, lo + (hi - lo) / 7]
        elif isinstance(s_, sp.Union):
            for part in s_.args:
                out += _points_of(part, 2)
        elif isinstance(s_, (sp.ImageSet, sp.Intersection, sp.Complement)):
            it = iter(s_)
            for _ in range(k):
                out.append(next(it))
    except Exception:  # noqa: BLE001
        pass
    return [p for p in out if getattr(p, "is_number", False)][:8]


def _defined_at(expr, conds, var, p) -> bool | None:
    for c in conds:
        h = relation_holds_at(c, var, p)
        if h is not True:
            return h
    return _real_finite(sp.sympify(expr).subs(var, p))


def _integrand_region(cf, var, discourse, timeout):
    """The points of `discourse` where the integrand's conditions `cf` hold, or None when no exact set is
    found (a relation SymPy reads on one period only is solved by `sandbox.exactsets`)."""
    region = discourse
    for cc in cf:
        rr = sb_run("mathverify.sandbox.ops:solveset_in", cc, var, discourse, timeout=timeout)
        if not rr.ok or not isinstance(rr.value, sp.Set) or rr.value.has(sp.ConditionSet):
            return None
        region = sp.Intersection(region, rr.value)
    return region


def _pieces(region) -> list | None:
    """The intervals `region` is the disjoint union of, or None when it is not a finite union of them."""
    if isinstance(region, sp.Interval):
        return [region]
    if isinstance(region, sp.Union) and all(isinstance(a, sp.Interval) for a in region.args):
        return list(region.args)
    return None


def _reality(v):
    """NONREAL, a sign (-1, 0, 1) when `v` is real, or None. A symbol left in it (the constant C of F + C, a
    parameter) is a real constant: its sign does not matter, SymPy's `is_real` does."""
    others = getattr(v, "free_symbols", set())
    if not others:
        return certified_sign(v)
    # a declared parameter keeps its declaration (k > 0: exp(k*x)/k is real; read as any real k, k = 0 left it
    # undecided, review of d4e, R3); the constant C and an undeclared symbol are any real number
    v = v.xreplace({s_: sp.Dummy(s_.name, real=True) for s_ in others if s_.is_real is not True})
    return NONREAL if v.is_real is False else 0 if v.is_real is True else None


# entire or meromorphic on ℂ: a sum, product or integer power of these is one meromorphic function
_MEROMORPHIC = (sp.exp, sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.sinh, sp.cosh, sp.tanh, sp.coth, sp.sech,
                sp.csch)


def meromorphic(F, var) -> bool:
    """Is F, as a function of `var`, built of rational operations, integer powers, c**var (c > 0) and the
    functions above only: one meromorphic function on ℂ? Two such primitives of f differ by a constant on ℂ minus
    their poles, a connected set: on every piece of a real region the SAME constant. tan(x**2) for
    2x/cos(x**2)**2 lives on infinitely many pieces, and was undecided (review of d4e, R1); log|x|, atan and a
    root are not of that kind (atan(tan(x**2)) - x**2 is constant on each piece, a different one on each)."""
    for n in sp.preorder_traversal(F):
        if n.is_Atom or isinstance(n, (sp.Add, sp.Mul) + _MEROMORPHIC):
            if n.is_Atom and isinstance(n, sp.Symbol) and n != var and getattr(n, "is_real", None) is not True:
                return False
            continue
        if isinstance(n, sp.Pow) and (n.exp.is_Integer or (var not in n.base.free_symbols and n.base.is_positive)):
            continue
        return False
    return True


def _continuous_across(F, var, gaps, timeout) -> bool:
    """Does F extend continuously across each gap point (equal finite one-sided limits)? Then a primitive on the
    pieces around them carries one constant: |x| for x/|x| on x != 0, x*log|x| for log|x| + 1 (review of d4e, R6)."""
    from .limits import classify_limit
    for g in gaps:
        lims = [classify_limit(F, var, g, d, timeout=timeout) for d in ("+", "-")]
        if any(lm["kind"] != "VAR" for lm in lims) or scalar_equal(lims[0]["value"], lims[1]["value"]) is not True:
            return False
    return True


def _one_constant(F, f, var, region, timeout) -> tuple[bool | None, dict[str, Any]]:
    """On a region of several pieces (1/x on x != 0), F' = f says F differs from a reference primitive by a
    constant on EACH piece. The curriculum's F + C has one constant; different constants on the pieces
    (log|x| + sign(x)) are a convention, never certified (fourth audit G12, decision of 2 Oct 2026). True
    when F minus SymPy's primitive (or its real part: log(x) is log|x| + i*pi on x < 0) is one constant,
    None otherwise."""
    ev: dict[str, Any] = {}
    pieces = _pieces(region) if region is not None else None
    if pieces is not None and len(pieces) <= 1:
        return True, ev
    if meromorphic(F, var):
        ev["reason"] = "one_meromorphic_primitive"
        return True, ev
    if pieces is not None:
        # the closure one interval: the pieces meet at finitely many gap points, and F continuous across each of
        # them binds the constants (`_continuous_across`)
        ordered = sorted(pieces, key=lambda iv: iv.inf)
        gaps = [a.sup for a, b in zip(ordered, ordered[1:]) if a.sup == b.inf]
        if len(gaps) == len(ordered) - 1 and all(g.is_finite for g in gaps) \
                and _continuous_across(F, var, gaps, timeout):
            ev["reason"] = "continuous_across_the_gaps"
            ev["gaps"] = [str(g) for g in gaps]
            return True, ev
    r = sb_run("mathverify.sandbox.ops:integrate_symbolic", f, var, timeout=timeout)
    if not r.ok or not isinstance(r.value, sp.Expr) or r.value.has(sp.Integral, *_PRIMITIVE_JUMPS):
        ev["reason"] = "antiderivative_pieces_undecided"
        return None, ev
    differs = False
    for ref in (r.value, sp.re(r.value)):
        if ref.has(sp.re, sp.im):
            continue
        rs = sb_run("mathverify.sandbox.ops:simplify_diff", F, ref, timeout=timeout)
        if rs.ok and isinstance(rs.value, sp.Expr) and var not in rs.value.free_symbols:
            ev["reference"] = str(ref)
            return True, ev
        if pieces is None:
            continue
        gaps = []
        for piece in pieces:
            pts = _points_of(piece, 1)
            if not pts:
                break
            gaps.append(sp.sympify(F - ref).subs(var, pts[0]))
        if len(gaps) != len(pieces):
            continue
        signs = [certified_sign(g - gaps[0]) for g in gaps[1:]]
        if all(s_ == 0 for s_ in signs):
            ev["reference"] = str(ref)
            return True, ev
        differs = differs or any(s_ in (1, -1) for s_ in signs)
    ev["reason"] = "constant_differs_between_pieces" if differs else "antiderivative_pieces_undecided"
    return None, ev


def antiderivative_domain_check(F, f, var, discourse=S.Reals, f_extra=(), F_extra=(),
                                timeout: float = 8.0) -> tuple[bool | None, dict[str, Any]]:
    """F' = f is not enough: F must be real and continuous at every point where f is defined.
    False comes with a witness point (f defined there, F not / F jumps there / F not real there);
    True needs a proof (the offending set is empty, or it misses the domain of f, and F is one
    primitive plus one constant over the pieces of that domain); otherwise None. Periodic domains
    are solved by `sandbox.exactsets` (SymPy returns ONE period for `1 + cos(x) != 0`)."""
    ev: dict[str, Any] = {}
    F, f = sp.sympify(F), sp.sympify(f)
    if F.has(*_JUMPY):
        ev["reason"] = "discontinuous_primitive_in_antiderivative"
        return None, ev
    # a closed condition of F that fails: F has no real value anywhere. x positive folds log(-x)'s
    # -x > 0 to false, which named no variable and was dropped, so log(-x) was certified for 1/x
    # (fourth audit G12); with x > 0 as a constraint the same claim was refuted
    closed = [c for c in list(definedness_conditions(F, var)) + list(F_extra)
              if not getattr(c, "free_symbols", set()) and c is not sp.true]
    cf = _conditions(f, var, f_extra)
    cF = _conditions(F, var, F_extra)
    if cf is None or cF is None:
        ev["reason"] = "conditions_involve_parameters"
        return None, ev
    df = None
    if closed:
        df = _integrand_region(cf, var, discourse, timeout)
        if any(c is sp.false for c in closed) and df is not None:
            for p_ in _points_of(df):
                if _defined_at(f, cf, var, p_) is True:
                    ev["reason"] = "antiderivative_undefined_everywhere_as_written"
                    ev["witness"] = {"x": str(p_)}
                    return False, ev
        ev["reason"] = "antiderivative_condition_undecided"
        return None, ev
    for s_ in F.atoms(sp.sign):                   # sign(u) jumps where u changes sign
        if s_.args[0].has(var):
            c = Ne(s_.args[0], 0)
            if c not in cF:
                cF.append(c)
    todo = [c for c in cF if c not in cf]
    ev["checked_conditions"] = [str(c) for c in todo]
    for c in todo:
        neg = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else c.negated
        r = sb_run("mathverify.sandbox.ops:solveset_in", neg, var, discourse, timeout=timeout)
        if not r.ok or isinstance(r.value, sp.ConditionSet):
            ev["reason"] = f"undecided: {c}"
            return None, ev
        bad = r.value
        if bad is S.EmptySet:
            continue
        for p_ in _points_of(bad):
            if _defined_at(f, cf, var, p_) is True and relation_holds_at(c, var, p_) is False:
                ev["reason"] = "antiderivative_not_defined_or_continuous_where_integrand_is"
                ev["witness"] = {"x": str(p_), "condition": str(c)}
                return False, ev
        if df is None:
            df = _integrand_region(cf, var, discourse, timeout)
            if df is None:
                ev["reason"] = f"undecided domain: {c}"
                return None, ev
        inter = sp.Intersection(bad, df)
        if inter is S.EmptySet:
            continue
        for p_ in _points_of(inter):
            if _defined_at(f, cf, var, p_) is True and relation_holds_at(c, var, p_) is False:
                ev["reason"] = "antiderivative_not_defined_or_continuous_where_integrand_is"
                ev["witness"] = {"x": str(p_), "condition": str(c)}
                return False, ev
        ev["reason"] = f"undecided: {c} on {inter}"
        return None, ev
    if df is None:
        df = _integrand_region(cf, var, discourse, timeout)
    # F real where f is: a complex constant (x + I for 1, log(x) + I*pi for 1/x) is no real primitive. Its
    # imaginary part is constant on each piece (F' = f is real); `_one_constant` compares the pieces
    checked = 0
    for batch in (_points_of(df if df is not None else discourse), _INTERIOR_PROBES):
        for p_ in batch:
            if discourse.contains(p_) is not sp.true or any(relation_holds_at(c, var, p_) is not True for c in cf):
                continue
            try:
                fv = sp.sympify(f).subs(var, p_)
                if not (_reality(fv) in (-1, 0, 1) if fv.free_symbols else _real_finite(fv) is True):
                    continue                           # f has no real value there
                sg = _reality(F.subs(var, p_))
            except Exception:  # noqa: BLE001
                sg = None
            if sg == NONREAL:
                ev["reason"] = "antiderivative_not_real_where_integrand_is"
                ev["witness"] = {"x": str(p_)}
                return False, ev
            checked += sg in (-1, 0, 1)
        if checked:
            break
    if not checked:
        ev["reason"] = "antiderivative_reality_undecided"
        return None, ev
    one, oev = _one_constant(F, f, var, df, timeout)
    ev.update(oev)
    return one, ev


def antiderivative_certificate(F, integrand, var, domain=None, timeout: float = 8.0,
                               discourse=S.Reals, f_extra=(), F_extra=()) -> tuple[bool | None, dict[str, Any]]:
    """d/dx F - integrand == 0 ? Constant shifts are automatically accepted (E8). A zero residual
    is then checked against the integrand's domain (`antiderivative_domain_check`)."""
    ev: dict[str, Any] = {"F": str(F), "integrand": str(integrand)}
    F, integrand = sp.sympify(F), sp.sympify(integrand)
    r = sb_run("mathverify.sandbox.ops:diff_expr", F, var, 1, timeout=timeout)
    if not r.ok:
        ev["error"] = r.error
        return None, ev
    dF = classical(r.value)
    ev["dF"] = str(dF)
    ok = None
    rs = sb_run("mathverify.sandbox.ops:simplify_diff", dF, integrand, timeout=timeout)
    if rs.ok:
        res = rs.value
        ev["residual"] = res
        if res == 0:
            ev["method"] = "symbolic"
            ok = True
        elif res.is_number and res.is_zero is False:
            ev["method"] = "nonzero_constant_residual"
            return False, ev
    else:
        ev["residual"] = None
        ev["flags"] = rs.flags
    if ok is None:
        # domain-aware numeric equality of dF and integrand, on the variable's region: read on all of R,
        # x - |x| refuted x**2/2 as a primitive of |x| under the constraint x > 0 (fourth audit G12)
        wide = None
        if domain is None:
            wide = S.Reals
            for c in definedness_conditions(integrand, var) + definedness_conditions(F, var):
                rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=timeout)
                if rr.ok and not isinstance(rr.value, sp.ConditionSet):
                    wide = sp.Intersection(wide, rr.value)
            domain = sp.Intersection(discourse, wide)
        ev["domain"] = str(domain)
        ok, rev = random_point_equal(dF, integrand, var, domain, seed=0, n=40)
        ev["random_point"] = rev
        ev["method"] = "random_point"
        agreed_on = domain
        if ok is None and wide is not None and discourse != S.Reals:
            # the proof at a kink reads its whole cell: on (1, oo) the cell (0, oo) of log|x| is not inside, and
            # log|x| was left undecided for 1/x under x > 1. Agreement where both are defined is agreement on
            # the region too; a disagreement there may lie outside it and refutes nothing
            okw, wev = random_point_equal(dF, integrand, var, wide, seed=0, n=40)
            ev["random_point_wide"] = wev
            if okw is True:
                ok, agreed_on = True, wide
        if ok is True and agreed_on == S.Reals and _equals_false_stands(dF, integrand):
            # SymPy's `equals` says they differ on the real line: agreement at sample points does not overrule it,
            # here as in `answers_equivalent` (x² + cos(Nπx)/(10^40·Nπ) as a primitive of 2x; attack on d4c round 3,
            # YO-B). A counterexample still refutes
            ok = None
            ev["conflict"] = "sympy_equals_false"
    if ok is True:
        okd, dev = antiderivative_domain_check(F, integrand, var, discourse, f_extra, F_extra, timeout)
        ev["domain_check"] = dev
        if okd is not True:
            if okd is False:
                ev["reason"] = dev.get("reason")
            return okd, ev
    return ok, ev


def _constant_not_additive(F_full, var, C, timeout) -> tuple[bool | None, dict[str, Any]]:
    """True when d/dx F depends on C, i.e. the claimed family is not F + constant. Measured before:
    "sin(x) + C*x", "sin(x + C)" and "(1 + C)*sin(x)" were all certified as ∫ cos(x) dx."""
    ev: dict[str, Any] = {}
    d_full = sp.diff(F_full, var)
    d_zero = sp.diff(F_full.subs(C, 0), var)
    r = sb_run("mathverify.sandbox.ops:simplify_diff", d_full, d_zero, timeout=timeout)
    if r.ok and r.value == 0:
        return False, ev
    gap = (d_full - d_zero).subs(C, 1)
    for p_ in (sp.Rational(1, 3), sp.Rational(7, 5), -sp.Rational(3, 2), sp.Rational(1, 10)):
        v = gap.subs(var, p_)
        try:
            ok, _ = num_equal(v, 0)
        except Exception:  # noqa: BLE001
            ok = None
        if ok is False and _real_finite(v) is True:
            ev["witness"] = {"C": "1", str(var): str(p_), "d/dx difference": str(sp.N(v, 15))}
            return True, ev
    return None, ev


# ---------------------------------------------------------------------------
def derivative_at_point(f, var, order: int, at, timeout: float = 8.0) -> dict[str, Any]:
    """Is f^(order) defined at `at`, and what is it? Certificate (mean value theorem): with
    g = f^(order-1) continuous at a and differentiable around it, the one-sided derivatives of g
    at a are the one-sided limits of g'. Returns {"status": value | infinite | cusp | corner |
    discontinuous | unknown, "value": ...}. Substituting a into SymPy's derivative is NOT a
    certificate: sign(0) = 0 made "d/dx |x| at 0 = 0" CORRECT (audit of 25 Sep 2026)."""
    from .limits import classify_limit
    ev: dict[str, Any] = {"status": "unknown"}
    f = sp.sympify(f)
    if order > 1:
        r = sb_run("mathverify.sandbox.ops:diff_expr", f, var, order - 1, timeout=timeout)
        if not r.ok:
            return ev
        g = classical(r.value)
    else:
        g = f
    r = sb_run("mathverify.sandbox.ops:diff_expr", f, var, order, timeout=timeout)
    if not r.ok:
        return ev
    gp = classical(r.value)
    ev["derivative"] = str(gp)
    rg = sb_run("mathverify.sandbox.ops:simplify_diff", g.subs(var, at), 0, timeout=timeout)
    if not rg.ok or _real_finite(rg.value) is not True:
        ev["reason"] = "lower_derivative_not_a_real_number_at_point"
        return ev
    ga = rg.value
    cg = classify_limit(g, var, at, None, timeout=timeout)
    ev["continuity"] = {"kind": cg["kind"], "limit": str(cg["value"]), "value": str(ga)}
    if cg["kind"] in ("DNE", "INF"):
        ev["status"] = "discontinuous"
        return ev
    if cg["kind"] != "VAR":
        return ev
    same = scalar_equal(cg["value"], ga)
    if same is False:
        ev["status"] = "discontinuous"
        return ev
    if same is not True:
        return ev
    lp = classify_limit(gp, var, at, "+", timeout=timeout)
    lm = classify_limit(gp, var, at, "-", timeout=timeout)
    ev["one_sided"] = {"+": (lp["kind"], str(lp["value"])), "-": (lm["kind"], str(lm["value"]))}
    kp, km = lp["kind"], lm["kind"]
    if kp == "VAR" and km == "VAR":
        s_ = scalar_equal(lp["value"], lm["value"])
        if s_ is True:
            ev["status"], ev["value"] = "value", lp["value"]
        elif s_ is False:
            ev["status"] = "corner"
    elif kp == "INF" and km == "INF":
        if lp["value"] == lm["value"]:
            ev["status"], ev["value"] = "infinite", lp["value"]
        else:
            ev["status"] = "cusp"
    elif {kp, km} == {"VAR", "INF"}:
        ev["status"] = "corner"
    return ev


_KINK_POINTS = 8          # the zeros of a switch of f classified one by one
_KINK_BUDGET = 3          # `derivative_at_point` calls per reading, whatever the number of kinks (round 3, RK-5)
# analytic on the interior of the domain their written conditions give (acosh, atanh, acot have none: never read)
_SMOOTH = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.asin, sp.acos, sp.atan, sp.sinh, sp.cosh, sp.tanh,
           sp.asinh, sp.exp, sp.log)
_SWITCHES = (sp.Abs, sp.sign, sp.Heaviside, sp.Max, sp.Min, sp.Piecewise)
_BINDERS = (sp.Integral, sp.Sum, sp.Product, sp.Derivative, sp.Subs, sp.Limit)


def abs_form(f):
    """f with each Max/Min of two arguments written with |.|: Max(a, b) = (a + b + |a - b|)/2, Min(a, b) =
    (a + b - |a - b|)/2 (real a, b). Max(x, -x) is |x|, and its kink is read as |x|'s is (round 3, YO-4)."""
    try:
        return f.replace(lambda e: isinstance(e, (sp.Max, sp.Min)) and len(e.args) == 2,
                         lambda e: (e.args[0] + e.args[1] + (1 if isinstance(e, sp.Max) else -1)
                                    * sp.Abs(e.args[0] - e.args[1])) / 2)
    except Exception:  # noqa: BLE001
        return f


def switch_arguments(f, var) -> list | None:
    """The u whose zeros are the only points where f may switch, off its written conditions: |u|, sign(u),
    Heaviside(u), a - b of a Max/Min(a, b, ...), lhs - rhs of a Piecewise's relations. The kink rule of R8 read |u|
    alone, so Max(x, -x), x*sign(x) and sign(x) had sign(x) and 0 certified as derivatives that have a value where
    there is none (round 3, YO-4). None when f holds a switch with no such u (floor, frac, Mod, a Piecewise condition
    that is no relation). In the order of f's tree, never of a set: the reading does not hang on the hash seed, as
    f.atoms(Abs) made it (round 3, RK-6)."""
    out: list = []

    def add(u):
        if var in u.free_symbols and u not in out:
            out.append(u)
    for n in sp.preorder_traversal(f):
        if var not in getattr(n, "free_symbols", set()):
            continue
        if isinstance(n, (sp.Abs, sp.sign, sp.Heaviside)):
            add(n.args[0])
        elif isinstance(n, (sp.Max, sp.Min)):
            for a, b in itertools.combinations(n.args, 2):
                add(a - b)
        elif isinstance(n, sp.Piecewise):
            for _, c in n.args:
                if c in (sp.true, sp.false):
                    continue
                if not isinstance(c, (sp.core.relational.Relational, sp.And, sp.Or, sp.Not)):
                    return None
                rels = list(c.atoms(sp.core.relational.Relational))
                if not rels:
                    return None
                for r in rels:
                    add(r.lhs - r.rhs)
        elif isinstance(n, (sp.floor, sp.ceiling, sp.frac, sp.Mod, sp.DiracDelta)):
            return None
    return out


def _poly(e, var):
    try:
        P = sp.Poly(e, var)
        return P if P.domain.is_QQ or P.domain.is_ZZ else None
    except Exception:  # noqa: BLE001
        return None


def _nonzero_at(w, var, p, root_of=None) -> bool | None:
    """Is w(p) != 0, exactly (True), = 0 (False), or undecided (None)? With p a root of the polynomial `root_of`
    and w a polynomial with rational coefficients, a constant gcd proves it for every root at once (the roots of
    x**4 - 10*x**2 + 1 are nested radicals: a value is slow to certify, round 3 RK-5)."""
    if root_of is not None:
        Pu, Pw = _poly(root_of, var), _poly(w, var)
        if Pu is not None and Pw is not None and Pu.degree() > 0 and sp.gcd(Pu, Pw).degree() == 0:
            return True
    try:
        sg = certified_sign(sp.sympify(w).subs(var, p))
    except Exception:  # noqa: BLE001
        return None
    return True if sg in (1, -1) else False if sg == 0 else None


def smooth_at(f, var, p, switches, fconds, root_of=None) -> bool:
    """Is f analytic near the number p? Each switch u (`switch_arguments`) is nonzero at p, each written condition
    of f holds strictly there (`strict_at`: a membership or a convention never does), and every operation is
    analytic on the interior of its domain (`_SMOOTH`, powers, the switches off their zeros). Then a derivative of
    every order exists at p: a point where the claim, as written, has no value is a wrong claim (RK-8), and a
    disagreement there refutes it (RK-2)."""
    if switches is None or not getattr(p, "is_number", False) or getattr(p, "is_real", None) is not True:
        return False
    for n in sp.preorder_traversal(f):
        if isinstance(n, _BINDERS):
            return False
        if isinstance(n, sp.Function) and not isinstance(n, _SMOOTH + _SWITCHES):
            return False
    if any(_nonzero_at(u, var, p, root_of=root_of) is not True for u in switches):
        return False
    return all(strict_at(c, var, p) for c in fconds if getattr(c, "free_symbols", None))


def _linear_switch_rule(fa, var, p, u, switches, fconds) -> str | None:
    """f = h + g*S**r near p for the one switch S = |u|, sign(u) or Heaviside(u) at p (f read with `abs_form`), r a
    positive rational (1 for sign and Heaviside), g, h and u analytic at p (`smooth_at`; p is a zero of u by its
    solution). |u|**r with r > 1, and g*|u| with g(p) = 0, add nothing to h'(p): f has a derivative. With g(p) != 0
    and u'(p) != 0 (a simple zero) |u| makes a corner (one-sided derivatives h'(p) ± g(p)*|u'(p)|), |u|**r with
    r < 1 an infinite slope, sign(u) and Heaviside(u) a jump: none. Exact, no limit taken: |log x| at 1 was
    undecided by SymPy's one-sided limits (round 3, RK-1), and 7 radical kinks took 186 s (RK-5). None when the
    rule does not apply or decides nothing."""
    others = [v for v in switches if v != u]
    if any(_nonzero_at(v, var, p, root_of=u) is not True for v in others):
        return None
    atoms = [a for a in fa.atoms(sp.Abs, sp.sign, sp.Heaviside) if a.args[0] == u]
    if len(atoms) != 1:
        return None
    A = atoms[0]
    D = sp.Dummy("switch")
    F = fa.xreplace({A: D})
    h, rest = F.as_independent(D, as_Add=True)
    g, r = rest.as_coeff_exponent(D)
    if rest == 0 or g.has(D) or not (r.is_Rational and r.is_positive):
        return None
    if not isinstance(A, sp.Abs) and r != 1:
        return None
    if not all(smooth_at(e, var, p, others, fconds, root_of=u) for e in (g, h, u)):
        return None
    if isinstance(A, sp.Abs) and r > 1:
        return "value"
    gp = _nonzero_at(g, var, p, root_of=u)
    if gp is False:
        return "value" if isinstance(A, sp.Abs) and r == 1 else None
    if gp is not True or _nonzero_at(sp.diff(u, var), var, p, root_of=u) is not True:
        return None
    return "corner"


def _classify_kink(f, fa, var, order, p, u, switches, fconds, budget, timeout) -> str | None:
    """'value' (f has a derivative of `order` at the zero p of the switch u), 'corner' (none: a corner, a cusp, a
    jump, an infinite slope) or None (undecided, or the reading's budget of `derivative_at_point` calls spent)."""
    if order == 1:
        st = _linear_switch_rule(fa, var, p, u, switches, fconds)
        if st is not None:
            return st
    if budget[0] <= 0:
        return None
    budget[0] -= 1
    st = derivative_at_point(f, var, order, p, timeout=timeout)["status"]
    return "value" if st == "value" else "corner" if st in ("corner", "cusp", "discontinuous", "infinite") else None


def _generic_points(K, u=None, var=None) -> list | None:
    """The points of a set of zeros as expressions: a finite set's elements, the term of a family indexed by the
    integers with its index an integer Dummy (2*n*pi), none of the empty set; a Complement or an Intersection
    (tan x = 0 is n*pi off the poles, x positive cuts a family) is read as its family when each of the family's
    points is a zero of u (round 3, RK-2). None for any other set."""
    out: list = []
    for s_ in (K.args if isinstance(K, sp.Union) else (K,)):
        if s_ is S.EmptySet:
            continue
        if isinstance(s_, sp.FiniteSet):
            out += list(s_)
        elif isinstance(s_, sp.ImageSet) and tuple(s_.base_sets) == (S.Integers,) and len(s_.lamda.variables) == 1:
            out.append(s_.lamda.expr.xreplace({s_.lamda.variables[0]: sp.Dummy("n", integer=True)}))
        elif isinstance(s_, (sp.Complement, sp.Intersection)) and u is not None:
            base = s_.args[0] if isinstance(s_, sp.Complement) else \
                next((a for a in s_.args if isinstance(a, sp.ImageSet)), None)
            if base is None or (isinstance(s_, sp.Intersection)
                                and not all(a is base or isinstance(a, sp.Interval) for a in s_.args)):
                return None
            pts = _generic_points(base)
            if pts is None:
                return None
            for q in pts:
                try:
                    if sp.simplify(u.subs(var, q)) != 0:
                        return None
                except Exception:  # noqa: BLE001
                    return None
            out += pts
        else:
            return None
    return out


def _claim_undefined_at(claim_conds, nowhere, claimed, var, p) -> bool | None:
    """Has the claim, read as written, no value at the point p (True: a written condition fails there, or its value
    is nan/zoo, as Piecewise((1, x > 0), (-1, x < 0)) at 0), a value (False: sign(x) at 0 is 0), or is that not
    decided (None)? At a family of points (p names an integer Dummy) only a failing condition or a nan proves it."""
    if nowhere:
        return True
    undecided = False
    for c in claim_conds:
        if var not in getattr(c, "free_symbols", set()):
            continue
        try:
            v = c.subs(var, p)
        except Exception:  # noqa: BLE001
            undecided = True
            continue
        if v is sp.false:
            return True
        if v is not sp.true:
            undecided = True
    try:
        val = sp.sympify(claimed).subs(var, p)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(val, sp.Basic) and val.has(sp.nan, sp.zoo):
        return True
    if undecided:
        return None
    if getattr(p, "free_symbols", None):
        return False                              # no condition fails at the family: it has a value there
    rf = _real_finite(val)
    return None if rf is None else not rf


def _continuous_where_defined(e) -> bool:
    """Is `e` built of operations continuous on the interior of their domain (see `strict_at`)?"""
    return all(n.is_Atom or isinstance(n, (sp.Add, sp.Mul, sp.Pow) + _CONTINUOUS) for n in sp.preorder_traversal(e))


def _abs_factor(f, u):
    """g when f is exactly g*|u|, g and u continuous where defined (no other |.|, no sign or jump); None otherwise."""
    a = sp.Abs(u)
    if not _continuous_where_defined(u) or u.has(sp.Abs):
        return None
    if f == a:
        return S.One
    if not isinstance(f, sp.Mul) or list(f.args).count(a) != 1:
        return None
    g = sp.Mul(*[x for x in f.args if x != a])
    return g if not g.has(sp.Abs) and _continuous_where_defined(g) else None


def _is_zero_at(u, var, p) -> bool:
    try:
        return sp.simplify(u.subs(var, p)) == 0
    except Exception:  # noqa: BLE001
        return False


def kink_reading(f, var, order: int, region, claimed, claim_conds, nowhere, fconds, timeout: float = 8.0) -> dict:
    """Where a switch u of f (`switch_arguments`: |u|, sign(u), Heaviside(u), Max, Min, Piecewise) has u = 0, f may
    have no derivative (|x| at 0: a corner), and the derivative function lives off those points. Compared on all of
    f's domain, the derivative x/|x| of |x| was refuted against SymPy's sign(0) = 0, and sign(x) itself certified
    (attack on d4e, R8); read on |u| alone, Max(x, -x) and sign(x) kept that (round 3, YO-4). Returns a dict:

    * kinks: finite zeros p where f has no derivative (a corner, a cusp, a jump, an infinite slope), left out of the
      comparison; values: those where it has one (|x|**3 at 0, x*|x| at 0), compared there. Each is classified by
      `_linear_switch_rule` (exact) or, within a budget of `_KINK_BUDGET` calls, `derivative_at_point`;
    * families: (u, points) for infinitely many zeros (sin(x) = 0), read for f = g*|u| alone, of order 1, at the
      family's generic point: g = 0 there gives f a derivative (0) at each (`value_families`, compared); g != 0 with
      a simple zero (u' != 0) a corner at each, left out by u != 0 (`opens`), SymPy's sign(u) read as u/|u| (`signs`);
    * reasons: why the claim cannot be certified: claim_value_at_a_kink (a value where f has no derivative: a
      convention), kink_undecided (a kink left out but not classified), kinks_not_solved (a switch whose zeros are
      not read, or f's switch has no u: they stay in the comparison, and a refutation needs a point where f is
      analytic, `smooth_at`), kink_budget (zeros not classified, left in the comparison: the same);
    * switches, fa: the switches and f in `abs_form`, for `smooth_at`."""
    fa = abs_form(f)
    switches = switch_arguments(fa, var)
    out: dict[str, Any] = {"kinks": [], "values": [], "families": [], "value_families": [], "opens": [],
                           "signs": [], "reasons": set(), "switches": switches, "fa": fa}
    reasons = out["reasons"]
    if switches is None:
        reasons.add("kinks_not_solved")
        return out
    budget = [_KINK_BUDGET]
    for u in switches:
        r = sb_run("mathverify.sandbox.ops:solveset_in", Eq(u, 0), var, S.Reals, timeout=timeout)
        K = r.value if r.ok and isinstance(r.value, sp.Set) and not r.value.has(sp.ConditionSet) else None
        pts = _generic_points(K, u, var) if K is not None else None
        if pts is None:
            reasons.add("kinks_not_solved")
            continue
        finite = [q for q in pts if not getattr(q, "free_symbols", None)]
        family = [q for q in pts if getattr(q, "free_symbols", None)]
        if len(finite) > _KINK_POINTS:
            reasons.add("kink_budget")
            finite = []
        for p_ in finite:
            # a kink off the region's interior is no point of the comparison (an end: |x| + sqrt(x) - sqrt(x) at 0)
            try:
                off_inside = in_domain(region.interior, p_) is False
            except Exception:  # noqa: BLE001
                off_inside = in_domain(region, p_) is False
            if off_inside or p_ in out["kinks"] or p_ in out["values"]:
                continue
            st = _classify_kink(f, fa, var, order, p_, u, switches, fconds, budget, timeout)
            if st == "value":
                out["values"].append(p_)
                continue
            out["kinks"].append(p_)
            if st is None:
                reasons.add("kink_undecided" if budget[0] > 0 else "kink_budget")
                continue
            und = _claim_undefined_at(claim_conds, nowhere, claimed, var, p_)
            if und is False:
                reasons.add("claim_value_at_a_kink")
            elif und is None:
                reasons.add("kink_undecided")
        if not family:
            continue
        # f = g*|u| of order 1, read at the family's generic point: g = 0 there gives f a derivative (0) at each
        # of them, and the family stays in the comparison (sin(x)*|sin(x)|: 2*cos(x)*|sin(x)| was certified before
        # and stays so); g != 0 and u' != 0 there give a corner at each, and the family is left out
        g = _abs_factor(fa, u) if order == 1 else None
        gv = [sp.simplify(g.subs(var, p_)) for p_ in family] if g is not None else []
        if g is not None and all(v.is_zero is True for v in gv):
            out["value_families"].append(u)
            continue
        out["opens"].append(Ne(u, 0))
        out["signs"].append(u)
        out["families"].append((u, family))
        du = sp.diff(u, var)
        simple = g is not None and all(v.is_zero is False and v.is_finite is True for v in gv) and all(
            (lambda v: v.is_zero is False and v.is_finite is True)(du.subs(var, p_)) for p_ in family)
        if not simple:
            reasons.add("kink_undecided")
            continue
        for p_ in family:
            und = _claim_undefined_at(claim_conds, nowhere, claimed, var, p_)
            if und is False:
                reasons.add("claim_value_at_a_kink")
            elif und is None:
                reasons.add("kink_undecided")
    return out


def _has_derivative_at(kr, var, p, fconds) -> bool:
    """Has f (read by `kink_reading`) a derivative at the number p: analytic there, or a zero of a switch where it
    was classified as having one?"""
    if p in kr["values"] or any(_is_zero_at(u, var, p) for u in kr["value_families"]):
        return True
    return smooth_at(kr["fa"], var, p, kr["switches"], fconds)


def _no_derivative_at(kr, var, p) -> bool:
    """Is p (a number, or a family's generic point) a kink `kink_reading` left out (f has no derivative there)?"""
    return p in kr["kinks"] or any(_is_zero_at(u, var, p) for u, _ in kr["families"])


def _in_comparison(dom, loose, var, p) -> bool | None:
    """Is the number p in the comparison region: the interior of `dom` where the unsolved conditions `loose` hold
    strictly?"""
    try:
        inside = in_domain(dom.interior, p)
    except Exception:  # noqa: BLE001
        inside = None
    if inside is not True:
        return inside
    for c in loose:
        # the comparison is drawn on the open part of each (`comparison_region`): sin(x) >= 0 is sin(x) > 0 there
        if relation_holds_at(c, var, p) is False or relation_holds_at(_open_condition(c), var, p) is False:
            return False
        if not strict_at(_open_condition(c), var, p):
            return None
    return True


def _zero_factors(w) -> list:
    """The factors of w whose zeros are w's (|u| and u**k read as u; a positive power's base; a nonzero number and
    a negative power dropped)."""
    out: list = []
    for a in sp.Mul.make_args(w):
        while True:
            if isinstance(a, sp.Abs):
                a = a.args[0]
            elif isinstance(a, sp.Pow) and a.args[1].is_number and a.args[1].is_positive:
                a = a.args[0]
            else:
                break
        if isinstance(a, sp.Pow) and a.args[1].is_number and a.args[1].is_negative:
            continue
        if a.is_number:
            continue
        out.append(a)
    return out


def _candidates(s_, var) -> list:
    """Points of a set to try as witnesses: a few of its own, then the fixed probes it holds."""
    pts = list(_points_of(s_))
    for q in _INTERIOR_PROBES:
        try:
            if in_domain(s_, q) is True and q not in pts:
                pts.append(q)
        except Exception:  # noqa: BLE001
            continue
    return pts[:12]


def claim_where_derivative(ctx: Ctx, claim_conds, claim_nowhere, var, dom, loose, kr, fconds) -> tuple[str, str]:
    """Where the claim, as written, has no value, against where f has a derivative (round 3, RK-8 and YO-3):
    'undefined' when a point of the comparison region where f has one (`_has_derivative_at`) has none of the claim:
    the claim is wrong there, the convention of simplify (claim_as_written) and of the antiderivative (2*x**2/x for
    (x**2)', 2*x + 0*sqrt(-x), x**2*exp(x)*(2/x + 1) were certified); 'defined' when the claim has a value at every
    point of the region off the kinks f has no derivative at (x/|x| for |x|: R8); 'undecided' otherwise, and then
    the claim is never certified (a condition on a free parameter: 1/(x + 1/a) with a >= 0)."""
    opens = _orient(fconds, var)
    if var in claim_nowhere:
        for q in _candidates(dom, var):
            if _in_comparison(dom, loose, var, q) is True and _has_derivative_at(kr, var, q, fconds):
                return "undefined", f"claim_defined_nowhere (f has a derivative at {q})"
        return "undecided", "claim_defined_nowhere"
    state, why = "defined", ""
    for c in claim_conds:
        fs = getattr(c, "free_symbols", set())
        if not fs:
            continue
        if c in fconds:
            continue                     # f's own condition (a convention both read alike): holds where f does
        if fs - {var} or isinstance(c, sp.Contains):
            if not _implied(c, opens, var):
                state, why = "undecided", f"claim_condition_not_proved: {c}"
            continue
        if isinstance(c, Ne):
            w = c.lhs - c.rhs
            if _implied(c, opens, var):
                continue                 # f's own condition, in another writing (cos(x**2)**2 != 0)
            for z in _zero_factors(w):
                rr = sb_run("mathverify.sandbox.ops:solveset_in", Eq(z, 0), var, S.Reals, timeout=ctx.timeout)
                K = rr.value if rr.ok and isinstance(rr.value, sp.Set) and not rr.value.has(sp.ConditionSet) else None
                pts = _generic_points(K, z, var) if K is not None else None
                if pts is None:
                    state, why = "undecided", f"claim_condition_undecided: {c}"
                    continue
                for q in pts:
                    if _no_derivative_at(kr, var, q):
                        continue
                    concrete = [q] if not getattr(q, "free_symbols", None) else \
                        [q.xreplace({d: k}) for d in q.free_symbols for k in (0, 1, -1, 2)]
                    hit = False
                    for qq in concrete:
                        inside = _in_comparison(dom, loose, var, qq)
                        if inside is False:
                            continue
                        if inside is True and _has_derivative_at(kr, var, qq, fconds):
                            return "undefined", f"claim_undefined_at {qq} (condition {c}), where f has a derivative"
                        hit = True
                    if hit:
                        state, why = "undecided", f"claim_condition_undecided: {c} at {q}"
            continue
        bad = sp.Not(c)
        rr = sb_run("mathverify.sandbox.ops:solveset_in", bad, var, S.Reals, timeout=ctx.timeout)
        F = rr.value if rr.ok and isinstance(rr.value, sp.Set) and not rr.value.has(sp.ConditionSet) else None
        if F is None:
            state, why = "undecided", f"claim_condition_undecided: {c}"
            continue
        try:
            inner = sp.Intersection(F, dom.interior)
            empty = inner.is_empty
        except Exception:  # noqa: BLE001
            inner, empty = F, None
        if empty is True:
            continue
        for q in _candidates(inner, var) + _candidates(F, var):
            if relation_holds_at(c, var, q) is False and _in_comparison(dom, loose, var, q) is True \
                    and _has_derivative_at(kr, var, q, fconds):
                return "undefined", f"claim_undefined_at {q} (condition {c}), where f has a derivative"
        state, why = "undecided", f"claim_condition_undecided: {c} on {inner}"
    return state, why


def _linear_factors(v, var) -> list | None:
    """The roots of v, when v is a product of factors linear in var with nonzero slopes and pairwise different
    roots for every value of its other symbols (by their assumptions); None otherwise."""
    roots: list = []
    try:
        for a in sp.Mul.make_args(sp.factor(v)):
            if not a.has(var):
                continue
            if isinstance(a, sp.Pow):
                return None
            k = sp.diff(a, var)
            if k.has(var) or k.is_zero is not False:
                return None
            roots.append(sp.simplify(-a.subs(var, 0) / k))
    except Exception:  # noqa: BLE001
        return None
    for r1, r2 in itertools.combinations(roots, 2):
        if sp.simplify(r1 - r2).is_zero is not False:
            return None
    return roots


def _orient(fconds, var) -> list:
    """f's written conditions as (v, kind) with v > 0 ('pos'), v != 0 ('ne') or v >= 0 ('nonneg') on the comparison
    region (the interior of the points where they hold): v >= 0 is v > 0 there when v's zeros are simple (linear
    factors with different roots: a sign change, an end of the region, never inside)."""
    out: list = []
    for c in fconds:
        if not getattr(c, "free_symbols", None) or var not in c.free_symbols:
            continue
        if isinstance(c, Ne):
            out.append((c.lhs - c.rhs, "ne"))
        elif isinstance(c, (sp.StrictGreaterThan, sp.StrictLessThan)):
            v = c.lhs - c.rhs if isinstance(c, sp.StrictGreaterThan) else c.rhs - c.lhs
            out.append((v, "pos"))
        elif isinstance(c, (sp.GreaterThan, sp.LessThan)):
            v = c.lhs - c.rhs if isinstance(c, sp.GreaterThan) else c.rhs - c.lhs
            out.append((v, "pos" if _linear_factors(v, var) is not None else "nonneg"))
    return out


def _implied(c, opens, var) -> bool:
    """Does the claim's condition c hold on the comparison region, where f's conditions hold (`_orient`)? c holds
    by the assumptions alone, or its w is r*v (or w**2 = r*v, or r*v1*v2) for f's v with r free of var and of the
    right sign: 1/(x + 1/a) needs x + 1/a != 0, which a*x + 1 > 0 gives with a > 0; 1/sqrt(a**2 - x**2) needs
    a**2 - x**2 > 0, which -1 < x/a < 1 gives (a**2 times their product)."""
    if c is sp.true:
        return True
    if isinstance(c, Ne):
        w, kind = c.lhs - c.rhs, "ne"
    elif isinstance(c, (sp.StrictGreaterThan, sp.StrictLessThan)):
        w, kind = (c.lhs - c.rhs if isinstance(c, sp.StrictGreaterThan) else c.rhs - c.lhs), "pos"
    elif isinstance(c, (sp.GreaterThan, sp.LessThan)):
        w, kind = (c.lhs - c.rhs if isinstance(c, sp.GreaterThan) else c.rhs - c.lhs), "nonneg"
    else:
        return False
    if var not in w.free_symbols:
        sign_ok = {"ne": w.is_zero is False, "pos": w.is_positive is True, "nonneg": w.is_nonnegative is True}
        return bool(sign_ok[kind])
    pos = [v for v, k in opens if k == "pos"]
    nonzero = [v for v, k in opens if k in ("pos", "ne")]
    nonneg = [v for v, k in opens if k in ("pos", "nonneg")]

    def free_ratio(num, den):
        try:
            r = sp.simplify(num / den)
        except Exception:  # noqa: BLE001
            return None
        return None if r.has(var) or r.has(sp.nan, sp.zoo) else r
    if kind == "nonneg":
        return any((r := free_ratio(w, v)) is not None and r.is_nonnegative is True for v in nonneg) or \
            any((r := free_ratio(w, v1 * v2)) is not None and r.is_nonnegative is True
                for v1, v2 in itertools.combinations(pos, 2))
    if kind == "pos":
        return any((r := free_ratio(w, v)) is not None and r.is_positive is True for v in pos) or \
            any((r := free_ratio(w, v1 * v2)) is not None and r.is_positive is True
                for v1, v2 in itertools.combinations(pos, 2))
    # w != 0: each factor whose zeros are w's (`_zero_factors`: cos(x**2)**2 is cos(x**2), sqrt(a**2 - x**2) is
    # a**2 - x**2) is nonzero by the parameters' signs or a nonzero multiple of f's v (or of a product of two)
    for z in _zero_factors(w):
        if var not in z.free_symbols:
            if z.is_zero is not False:
                return False
            continue
        if not any(any((r := free_ratio(z ** k, v)) is not None and r.is_zero is False for v in nonzero)
                   or any((r := free_ratio(z ** k, v1 * v2)) is not None and r.is_zero is False
                          for v1, v2 in itertools.combinations(nonzero, 2)) for k in (1, 2)):
            return False
    return True


def _smooth_witness(kr, var, claimed, truth, dom, loose, fconds, cev) -> Any:
    """A point where f is analytic (`smooth_at`), in the comparison region, at which the claim and the derivative
    differ exactly: the counterexample the comparison found, or a probe. With zeros of a switch not read
    (`kink_reading`'s kinks_not_solved, kink_budget), a disagreement may lie where f has no derivative; at such a
    point it does not, and the refutation stands: |tan(x)|' = 1/cos(x)**2 was left undecided (round 3, RK-2)."""
    from ..equiv.random_point import _exact_counterexample
    found: list = []

    def walk(e):
        if isinstance(e, dict):
            ce = e.get("counterexample")
            if isinstance(ce, dict) and isinstance(ce.get("point"), dict) and str(var) in ce["point"]:
                found.append(ce["point"][str(var)])
            for v in e.values():
                walk(v)
        elif isinstance(e, (list, tuple)):
            for v in e:
                walk(v)
    walk(cev)
    pts: list = []
    for txt in found:
        try:
            pts.append(sp.Rational(str(txt)))
        except Exception:  # noqa: BLE001
            continue
    pts += [q for q in _INTERIOR_PROBES if q not in pts]
    for q in pts:
        if _in_comparison(dom, loose, var, q) is not True or not smooth_at(kr["fa"], var, q, kr["switches"], fconds):
            continue
        try:
            ce = _exact_counterexample(sp.sympify(claimed), sp.sympify(truth), [var], {var: q})
        except Exception:  # noqa: BLE001
            continue
        if isinstance(ce, dict):
            return q
    return None


def _sign_off(truth, signs):
    """SymPy's sign(u) as u/|u| for each u in `signs`: the same value wherever u != 0, where the comparison is
    drawn (`kink_reading`); a family of kinks leaves no breakpoints the numbers could prove a sign on."""
    if not signs:
        return truth
    return truth.replace(lambda e: isinstance(e, sp.sign) and e.args[0] in signs, lambda e: e.args[0] / sp.Abs(e.args[0]))


# ---------------------------------------------------------------------------
def _line_equal(claimed, truth, var, dep) -> tuple[bool | None, dict[str, Any]]:
    """Same line? A linear claim is compared by proportionality (exact); a non-linear claim can
    only be refuted: solving for x alone dropped factors in y, so "(y - 2x + 1)(y - 5) = 0" was
    certified as the tangent y = 2x - 1 (audit of 25 Sep 2026)."""
    ev: dict[str, Any] = {"claimed": str(claimed), "truth": str(truth)}
    d1 = sp.expand(claimed.lhs - claimed.rhs)
    d2 = sp.expand(truth.lhs - truth.rhs)
    if d1.free_symbols - {var, dep}:
        ev["method"] = "unbound_symbols"
        return None, ev
    try:
        deg = sp.Poly(d1, var, dep).total_degree()
    except sp.PolynomialError:
        deg = None
    if deg is not None and deg <= 1:
        if deg == 0:
            ev["method"] = "not_a_line"
            return False, ev
        q = sp.cancel(sp.together(d1 / d2))
        ev["method"] = "linear_proportionality"
        ev["ratio"] = str(q)
        return bool(q.is_number and q != 0), ev
    ok, cev = answers_equivalent(claimed, truth, shape="equation", var=var)
    ev["method"] = "nonlinear_claim_refutation_only"
    ev["compare"] = cev
    return (False if ok is False else None), ev


_TRAILING_C = re.compile(r"\s*\+\s*[Cc]\s*$")


def _unreadable_task_expression(src, expr, var, ns, ms, regions=()):
    """UNKNOWN when the task's function or integrand is undefined as written for every value of `var`
    (limits.written_undefined_everywhere) or carries a membership condition on it
    (limits.membership_conditions) that does not hold on one of `regions` for certain (the integral's
    interval, a neighbourhood of the derivative's point: `limits.membership_holds_on`); None otherwise."""
    if written_undefined_everywhere(src, ns):
        return unknown(LAYER, "expression_undefined_as_written", ms, {"expr": src},
                       flags=["expression_undefined_as_written"])
    members = [c for c in membership_conditions(src, expr, var, ns) if not membership_holds_on(c, var, regions)]
    if members:
        return unknown(LAYER, "membership_condition_on_variable", ms, {"conditions": [str(c) for c in members]},
                       flags=["membership_condition"])
    return None


def _closed_real(txt, ctx, pins):
    """The task's number `txt` (a bound, a point) read at the values the givens fix; None when it is not a real
    number or not read."""
    if txt is None:
        return None
    try:
        v = ctx.with_pins(ctx.expr(str(txt)), pins)
    except Exception:  # noqa: BLE001 - read again by the certificate, which reports it
        return None
    return v if getattr(v, "is_number", False) and v.is_extended_real is True else None


def _interval_regions(p, ctx, pins) -> list:
    """[the integral's interval [a, b]] when both bounds are real numbers; [] otherwise."""
    a, b = _closed_real(p.get("a"), ctx, pins), _closed_real(p.get("b"), ctx, pins)
    if a is None or b is None:
        return []
    try:
        return [sp.Interval(sp.Min(a, b), sp.Max(a, b))]
    except Exception:  # noqa: BLE001
        return []


# points tried for an interior point of a function's domain after the ones its solved part offers
_INTERIOR_PROBES = (S.Half, S(3) / 2, -S.Half, S.One / 3, S(2), S(-2), S(5), S(-5), S.One / 10, -S(3) / 2)


def _open_condition(c):
    """The open part of a definedness condition: u >= 0 read as u > 0 (where u = 0 the function has, at best, a
    one-sided neighbourhood). A comparison is drawn there only: sign(0) = 0 refuted the derivative 1 of
    |x| + sqrt(x) - sqrt(x), which needs x >= 0, at its end 0 (fourth audit TAN-06)."""
    if isinstance(c, sp.GreaterThan):
        return sp.StrictGreaterThan(c.lhs, c.rhs)
    if isinstance(c, sp.LessThan):
        return sp.StrictLessThan(c.lhs, c.rhs)
    return c


def task_conditions(ctx: Ctx, src, var, pins) -> tuple[list, list]:
    """(the written definedness conditions of the task's function on `var`, with the values `pins` holds put in;
    the ones that name another symbol). A membership (n!, gcd) is `_unreadable_task_expression`'s business, and
    so is a function defined nowhere (a closed condition that fails, with or without the values:
    `Ctx.binding_issues`). A condition naming a parameter was dropped, so the derivative 1 of
    x + 0*sqrt(b - x) + 0*sqrt(x - b), defined at b alone, was certified (review of d4e)."""
    conds, _ = written_definedness(src, ctx.ns, pins)
    on_var: list = []
    other: list = []
    for c in conds:
        fs = getattr(c, "free_symbols", set())
        if fs - {var}:
            other.append(c)
        elif var in fs and not isinstance(c, sp.Contains):
            on_var.append(c)
    return on_var, other


def _names(conds, var) -> list[str]:
    return sorted({str(s_) for c in conds for s_ in getattr(c, "free_symbols", set()) - {var}})


def _half_line_for_every_value(ctx: Ctx, conds, other, var) -> bool:
    """Do the written conditions naming another symbol (`other`) bound `var` from one side only, the side the
    variable's region cut by its own conditions (`conds`) leaves unbounded? Each must read k*var + q >= 0, > 0
    or != 0 with k a nonzero number (q may name the parameters). The points where all hold then hold a
    half-line for EVERY value of the parameters, so a derivative function has an open set to live on: the
    derivative 1/(2*sqrt(x - a)) of sqrt(x - a) stays certified with a free, as before the review of d4e.
    Bounded on both sides (x + 0*sqrt(b - x) + 0*sqrt(x - b), defined at b alone) it is not."""
    sides = set()
    for c in other:
        if isinstance(c, Ne):
            continue                                   # a point
        if isinstance(c, (sp.GreaterThan, sp.StrictGreaterThan)):
            u = c.lhs - c.rhs
        elif isinstance(c, (sp.LessThan, sp.StrictLessThan)):
            u = c.rhs - c.lhs
        else:
            return False
        k = sp.diff(u, var)
        if not (k.is_number and k.is_zero is False and k.is_real is True) or sp.diff(u, var, 2) != 0:
            return False
        sides.add(k.is_positive)
    if len(sides) != 1:
        return not sides                               # points only: the region's own interior decides
    region, loose = task_region(ctx, conds, var)
    if loose:
        return False
    upward = sides.pop()
    parts = list(region.args) if isinstance(region, sp.Union) else [region]
    end = oo if upward else -oo
    return any(isinstance(part, Interval) and (part.sup if upward else part.inf) == end for part in parts)


def task_region(ctx: Ctx, conds, var, window=None, region=None) -> tuple[sp.Set, list]:
    """(the points of `region` (`var`'s region, `Ctx.domain_for`, by default) within `window` where the conditions
    `conds` hold, each solved exactly on the window (ℝ without one); the conditions left unsolved). On a bounded
    window `sandbox.exactsets` solves a periodic condition exactly; on ℝ cos(x) != 0 stays a ConditionSet."""
    base = S.Reals if window is None else window
    if region is None:
        region = ctx.domain_for(var)
        # a periodic condition `domain_for` left unsolved on ℝ (the given cos(x) > 0) is one of `conds` here:
        # solved exactly on a bounded window, loose otherwise (review of d4e, R5)
        extra = [c for c in ctx.unsolved_conditions(var) if c not in conds]
        if extra:
            region, conds = _solved_part(region), list(conds) + extra
    region = region if window is None else sp.Intersection(region, window)
    loose: list = []
    for c in conds:
        r = sb_run("mathverify.sandbox.ops:solveset_in", c, var, base, timeout=ctx.timeout)
        if r.ok and isinstance(r.value, sp.Set) and not r.value.has(sp.ConditionSet):
            region = sp.Intersection(region, r.value)
        else:
            loose.append(c)
    return region, loose


# functions continuous on the interior of their domain (SymPy's acot jumps at 0, floor and the like jump anywhere)
_CONTINUOUS = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.asin, sp.acos, sp.atan, sp.sinh, sp.cosh, sp.tanh,
               sp.coth, sp.asinh, sp.acosh, sp.atanh, sp.exp, sp.log, sp.Abs, sp.Max, sp.Min)


def strict_at(c, var, p) -> bool:
    """Does the written condition `c` on `var` hold STRICTLY at p (u(p) != 0 for u != 0, u(p) > 0 for u > 0 or
    u >= 0), with u built of operations continuous where they are defined? Then it holds on a neighbourhood of p:
    p is interior to it without solving it (tan(x**2) at 1: cos(1) != 0; review of d4e, R1). A jump (floor(x) at
    1), a binder or a membership proves nothing."""
    if not isinstance(c, (Ne, sp.StrictGreaterThan, sp.GreaterThan, sp.StrictLessThan, sp.LessThan)):
        return False
    if getattr(c, "free_symbols", set()) != {var}:
        return False
    u = c.lhs - c.rhs
    for n in sp.preorder_traversal(u):
        if not (n.is_Atom or isinstance(n, (sp.Add, sp.Mul, sp.Pow) + _CONTINUOUS)):
            return False
    try:
        sg = certified_sign(u.subs(var, p))
    except Exception:  # noqa: BLE001
        return False
    if isinstance(c, Ne):
        return sg in (1, -1)
    return sg == (1 if isinstance(c, (sp.StrictGreaterThan, sp.GreaterThan)) else -1)


def _solved_part(region):
    """`region` with each ConditionSet (a periodic condition `Ctx.domain_for` left unsolved) read as its base set:
    the condition itself is solved on a bounded window by the caller (`task_region`)."""
    try:
        return region.replace(lambda e: isinstance(e, sp.ConditionSet), lambda e: e.base_set)
    except Exception:  # noqa: BLE001
        return region


def interior_at(ctx: Ctx, conds, var, p) -> bool | None:
    """Is `p` PROVED an interior point of the points of `var`'s region where `conds` hold? Read on
    [p - 1, p + 1] (`task_region`); a condition not solved there counts when it holds strictly at p and is
    continuous (`strict_at`). None when that is not decided."""
    try:
        if getattr(p, "is_real", None) is not True or p.is_finite is not True:
            return None
        region, loose = task_region(ctx, conds, var, Interval(p - 1, p + 1))
        inside = in_domain(region.interior, p)
        if not loose or inside is not True:
            return inside if not loose or inside is False else None
        return True if all(strict_at(c, var, p) for c in loose) else None
    except Exception:  # noqa: BLE001 - an interior SymPy cannot form is no proof
        return None


def interior_point(ctx: Ctx, conds, var, region):
    """A point PROVED interior to the points of `var`'s region where `conds` hold (`interior_at`): a point of
    `region` (their solved part) or a fixed probe. None when none is found, and then a derivative function or
    a primitive has no open set to live on, as for a function defined at 0 alone or nowhere: the derivative
    1 and the primitive x of such functions were certified (fourth audit TAN-06, G6)."""
    for p_ in list(_points_of(region)) + list(_INTERIOR_PROBES):
        if interior_at(ctx, conds, var, p_) is True:
            return p_
    return None


def comparison_region(region, loose, var):
    """Where a derivative or a primitive is compared with the claim: the interior of `region` (two-sided), cut
    by the open part of each condition `task_region` left unsolved (sampled by rejection: cos(x) != 0)."""
    try:
        inner = region.interior
        if isinstance(inner, sp.Set) and not inner.has(sp.Complement):
            region = inner
    except Exception:  # noqa: BLE001 - the region as it is
        pass
    if loose:
        region = sp.ConditionSet(var, sp.And(*[_open_condition(c) for c in loose]), region)
    return region


_WITNESSES = (S.Zero, S.One, -S.One, S.Half, -S.Half, S(2), S(-2))
_PARAMETER_SAMPLES = (S.One, S(2), S.Half, S(3), -S.One, S(-2))


def _parameter_dummies(ctx: Ctx, params) -> dict | None:
    """Each parameter as a Dummy with the sign its region has (`Ctx._declared_region`: the declaration, the domain
    of discourse, the constraints and the givens on it alone: a > 0 positive), and that region; None when a region
    is not read."""
    out: dict = {}
    for p_ in params:
        reg = ctx._declared_region(ctx.sym(p_.name), givens=True)
        if reg is None or reg.free_symbols:
            return None
        facts = {"real": True}
        if getattr(p_, "is_integer", None):
            facts["integer"] = True
        for name, half in (("positive", Interval.open(0, oo)), ("negative", Interval.open(-oo, 0)),
                           ("nonnegative", Interval(0, oo)), ("nonpositive", Interval(-oo, 0))):
            try:
                if reg.is_subset(half) is True:
                    facts[name] = True
                    break
            except Exception:  # noqa: BLE001
                continue
        out[p_] = (sp.Dummy(p_.name, **facts), reg)
    return out


def _strict_for_every(c, var, x0) -> bool:
    """`strict_at` for a condition that also names parameters (read as Dummies of known sign): it holds strictly
    at x0 for EVERY value they may take, decided by SymPy's assumptions (a**2 > 0 for a > 0, k*1 > 0 for k > 0)."""
    if not isinstance(c, (Ne, sp.StrictGreaterThan, sp.GreaterThan, sp.StrictLessThan, sp.LessThan)):
        return False
    u = c.lhs - c.rhs
    for n in sp.preorder_traversal(u):
        if not (n.is_Atom or isinstance(n, (sp.Add, sp.Mul, sp.Pow) + _CONTINUOUS)):
            return False
    try:
        v = sp.simplify(u.subs(var, x0))
    except Exception:  # noqa: BLE001
        return False
    if isinstance(c, Ne):
        return v.is_zero is False
    return (v.is_positive if isinstance(c, (sp.StrictGreaterThan, sp.GreaterThan)) else v.is_negative) is True


def for_every_parameter_value(ctx: Ctx, var, conds, other, f, claimed, truth, claim_conds=(), claim_nowhere=(),
                              fconds=()) -> tuple[bool | None, dict[str, Any]]:
    """The derivative function of f, whose written domain names parameters (`other`), compared with the claim for
    EVERY value the parameters may take (review of d4e, R2: asin(x/a), sqrt(a**2 - x**2), log(a*x + b) and log(k*x)
    with a, b, k > 0 declared or given were `condition_not_applied`). The domain has interior for every value
    when one point x0 satisfies every written condition strictly whatever the values are (`_strict_for_every`;
    with a free sqrt(a**2 - x**2) is defined at 0 alone for a = 0, and no point is found). Then the claim is
    CORRECT by a symbolic identity read with the parameters' signs, INCORRECT by a disagreement at an allowed
    value of them on the domain the value leaves (`answers_equivalent` with numbers put in), undecided otherwise.
    A function or claim with a kink (|u|, sign) is not read this way. The claim's written conditions must hold on
    the domain for every value (`_implied`): 1/(x + 1/a) with a >= 0, (a - 1)/((a - 1)*sqrt(a**2 - x**2)) with
    a > 0 were certified (round 3, YO-3); one that fails at x0, where f is analytic for every value, refutes the
    claim (1/x + 0*sqrt(-x) for log(a*x), RK-8)."""
    from ..equiv.symbolic import sym_equal
    ev: dict[str, Any] = {"method": "for_every_parameter_value"}
    params = sorted({s_ for c in other for s_ in c.free_symbols} - {var}, key=lambda s_: s_.name)
    nonsmooth = (sp.Abs, sp.sign, sp.Heaviside, sp.Piecewise, sp.floor, sp.ceiling, sp.frac, sp.Mod, sp.Max, sp.Min)
    dums = _parameter_dummies(ctx, params) if not (f.has(*nonsmooth) or sp.sympify(claimed).has(*nonsmooth)) else None
    if dums is None:
        ev["reason"] = "no_interior_point_for_every_value"
        return None, ev
    rep = {p_: d for p_, (d, _) in dums.items()}
    allc = [c.xreplace(rep) for c in list(conds) + list(other)]
    region = ctx.domain_for(var)
    witness = None
    for x0 in _WITNESSES:
        try:
            if in_domain(region.interior, x0) is not True:
                continue
        except Exception:  # noqa: BLE001
            continue
        if all(_strict_for_every(c, var, x0) for c in allc):
            witness = x0
            break
    if witness is None:
        ev["reason"] = "no_interior_point_for_every_value"
        return None, ev
    ev["witness"] = str(witness)
    ev["parameters"] = {str(p_): str(reg) for p_, (_, reg) in dums.items()}
    cstate = _claim_for_every_value(f, var, witness, rep, list(conds) + list(other), claim_conds, claim_nowhere,
                                    fconds, ev)
    if cstate == "undefined":
        return False, ev
    okS, sev = sym_equal(sp.sympify(claimed).xreplace(rep), sp.sympify(truth).xreplace(rep))
    ev["symbolic"] = sev
    if okS is True and cstate == "defined":
        return True, ev
    # refuted at an allowed value of the parameters, on the domain that value leaves
    samples = []
    for p_ in params:
        reg = dums[p_][1]
        vals = [v for v in _PARAMETER_SAMPLES if (not getattr(p_, "is_integer", None) or v.is_integer)
                and in_domain(reg, v) is True][:2]
        samples.append(vals)
    for vals in itertools.product(*samples):
        inst = dict(zip(params, vals))
        ci = [c.xreplace(inst) for c in list(conds) + list(other)]
        dom_i, loose_i = task_region(ctx, ci, var)
        if interior_point(ctx, ci, var, dom_i) is None:
            continue
        ok_i, ev_i = answers_equivalent(sp.sympify(claimed).xreplace(inst), sp.sympify(truth).xreplace(inst),
                                        shape="expression", domain=comparison_region(dom_i, loose_i, var), var=var)
        if ok_i is False:
            ev["instance"] = {str(k): str(v) for k, v in inst.items()}
            ev["compare"] = ev_i
            return False, ev
    ev["reason"] = "not_proved_for_every_parameter_value"
    return None, ev


def _claim_for_every_value(f, var, x0, rep, fc, claim_conds, claim_nowhere, fconds, ev) -> str:
    """The claim's written conditions in `for_every_parameter_value`, the parameters read as the Dummies `rep`:
    'undefined' when the claim has no value at the witness x0, where f is analytic for every allowed value (its
    conditions hold strictly there, its operations are analytic: `_SMOOTH`); 'defined' when each condition holds by
    the parameters' signs, is one of f's or follows from them (`_implied`); 'undecided' otherwise."""
    analytic = all(not isinstance(n, sp.Function) or isinstance(n, _SMOOTH) for n in sp.preorder_traversal(f)) \
        and not f.has(*_BINDERS)
    if claim_nowhere & ({var} | set(rep)):
        ev["claim_as_written"] = "claim_defined_nowhere"
        return "undefined" if analytic else "undecided"
    opens = _orient([c.xreplace(rep) for c in list(fc) + list(fconds)], var)
    state = "defined"
    for c in claim_conds:
        if not getattr(c, "free_symbols", None):
            continue
        cd = c.xreplace(rep)
        if cd is sp.true or c in fconds or c in fc:
            continue
        if var in getattr(cd, "free_symbols", set()) and analytic:
            try:
                at = cd.subs(var, x0)
            except Exception:  # noqa: BLE001
                at = None
            if at is sp.false:
                ev["claim_as_written"] = f"claim_undefined_at {x0} (condition {c}) for every value"
                return "undefined"
        if not _implied(cd, opens, var):
            ev["claim_as_written"] = f"claim_condition_not_proved: {c}"
            state = "undecided"
    return state


def _point_not_interior(ctx: Ctx, src, var, at, pins, ms):
    """UNKNOWN unless `at` is an interior point of the variable's region (`Ctx.domain_for`: declaration,
    constraints, givens, domain of discourse) cut by the written domain of the task's function
    (`task_conditions`): a derivative and a tangent line are two-sided (a one-sided derivative is no
    derivative in the curriculum). With x declared positive the parse folds |x| and sqrt(x**2) to x, and with
    x declared nonnegative 0 is the closed end: there the derivative 1 and the tangent y = x of |x| at 0 were
    certified (30 Sep 2026); with x >= 0 as a given it was refuted (fourth audit G6), and the derivative 1 of
    sqrt(x)**2 and of x + acos(x) - acos(x) at their ends 0 and 1 was certified (TAN-06). A condition naming
    a symbol nothing fixes (x >= b, sqrt(x - b) with b free) leaves the domain unknown: the certificate
    abstains (part vi). None when the point is interior."""
    unapplied = ctx.unapplied_conditions(var)
    if unapplied:
        return condition_not_applied(LAYER, unapplied, ms)
    # a condition naming a symbol nothing fixes (sqrt(x - b), b free) left `written_undefined_in` undecided at the
    # point, and the certificate abstained before this
    conds, _ = task_conditions(ctx, src, var, pins)
    if interior_at(ctx, conds, var, at) is not True:
        return unknown(LAYER, "point_not_interior_to_the_domain", ms,
                       {"at": str(at), "domain": str(ctx.domain_for(var)), "conditions": [str(c) for c in conds]},
                       flags=["point_not_interior"])
    return None


# ---------------------------------------------------------------------------
def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("antiderivative", "definite_integral", "derivative", "tangent_line"):
        return unknown(LAYER, "not_applicable")
    p = ir.task.params
    with Timer() as t:
        var = ctx.sym(p.get("var", "x"))
        ev: dict[str, Any] = {}
        if kind != "definite_integral" and getattr(var, "is_integer", None):
            # a derivative or antiderivative in a variable declared an integer is no question, and
            # its assumption folds the function first: with n a positive integer sin(pi*n) was 0, so
            # "d/dn at 1 is 0" (it is -pi), "y = 0 is the tangent" and "7 is an antiderivative"
            # were certified (30 Sep 2026)
            return unknown(LAYER, "variable_declared_integer", t.ms, {"var": str(var)},
                           flags=["variable_declared_integer"])
        if kind == "antiderivative":
            # a symbol a given or a declared constraint fixes is read as its value in the integrand and in the
            # claim (`Ctx.task_pins`): the primitive 3*x**2/2 of a*x with a = 3 was left undecided
            pins = ctx.task_pins(var)
            integrand, err = parse_or_unknown(LAYER, ctx.expr, p["integrand"])
            if err:
                return err
            bad = _unreadable_task_expression(p["integrand"], integrand, var, ctx.ns, t.ms)
            if bad is not None:
                return bad
            integrand, err = parse_or_unknown(LAYER, ctx.with_pins, integrand, pins)
            if err:
                return err
            from ..normalize.parse import parse_expr_str
            payload = _TRAILING_C.sub("", str(solution.claimed_answer.payload))
            C = sp.Symbol("C")
            ns2, err = parse_or_unknown(LAYER, ctx.claim_ns, solution, C=C)
            if err:
                return err
            F_full, err = parse_or_unknown(LAYER, parse_expr_str, payload, ns2)
            if err:
                return err
            F_full, err = parse_or_unknown(LAYER, ctx.with_pins, F_full, pins)
            if err:
                return err
            if F_full.has(C):
                bad_c, cev = _constant_not_additive(F_full, var, C, ctx.timeout)
                if bad_c is not False:
                    ev = {"constant_check": cev, "reason": "constant_C_not_additive"}
                    if bad_c is True:
                        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
                    return unknown(LAYER, "constant_C_undecided", t.ms, ev)
            F = F_full.subs(C, 0)
            # the primitive lives on the variable's region (declaration, constraints, givens, domain of
            # discourse: `Ctx.domain_for`) where the integrand is defined: the given x < 0 was not read, so
            # log(-x) was refuted for 1/x, and under the constraint x > 0 x**2/2 was refuted for |x| (fourth
            # audit G12); on a region without interior (1 + sqrt(x) - sqrt(x) + sqrt(-x) - sqrt(-x), defined
            # at 0 alone, or a function defined nowhere) x was certified (TAN-06)
            region = ctx.domain_for(var)
            unapplied = ctx.unapplied_conditions(var)
            if unapplied:
                return condition_not_applied(LAYER, unapplied, t.ms)
            f_extra, other = task_conditions(ctx, p["integrand"], var, pins)
            if other:
                return condition_not_applied(LAYER, _names(other, var), t.ms)
            conds = f_extra + [c for c in definedness_conditions(integrand, var) if c not in f_extra
                               and getattr(c, "free_symbols", set()) == {var} and not isinstance(c, sp.Contains)]
            # (a trigonometric condition on the variable left unsolved leaves no interior point proved)
            if interior_point(ctx, conds, var, task_region(ctx, conds, var)[0]) is None:
                return unknown(LAYER, "region_without_interior", t.ms, {"region": str(region)},
                               flags=["point_not_interior"])
            claim_conds, claim_nowhere = written_definedness(payload, ns2, pins)
            # a claim defined nowhere as written (x**2 + 0*log(-x) with x positive) carries `false`
            F_extra = [c for c in claim_conds if not c.has(C)] + ([sp.false] if claim_nowhere else [])
            ok, ev = antiderivative_certificate(F, integrand, var, timeout=ctx.timeout,
                                                discourse=region, f_extra=f_extra,
                                                F_extra=F_extra)
            conf = 0.99 if ev.get("method") == "symbolic" else 0.97
        elif kind == "definite_integral":
            # the variable of a definite integral runs over [a, b], not over its declared domain (the
            # rule of normalize.parse for a written Integral): with x declared positive, ∫_{-1}^{1} |x| dx
            # was read as ∫ x dx = 0 and the claim 0 certified (audit of 29 Sep 2026)
            from ..normalize.parse import parse_expr_str
            pins = ctx.task_pins(var)
            var = sp.Symbol(var.name, real=True)
            ns_i = dict(ctx.ns, **{var.name: var})
            integrand, err = parse_or_unknown(LAYER, parse_expr_str, p["integrand"], ns_i)
            if err:
                return err
            bad = _unreadable_task_expression(p["integrand"], integrand, var, ns_i, t.ms,
                                              _interval_regions(p, ctx, pins))
            if bad is not None:
                return bad
            # a symbol a given or a declared constraint fixes is read as its value in the integrand, the
            # bounds and the claim (`Ctx.task_pins`), in its written conditions too: x + 0*sqrt(b - x) is x
            # after parsing, and with b = 1/2 (or b free) its integral 1/2 over [0, 1] was certified (review
            # of d4e)
            integrand, err = parse_or_unknown(LAYER, ctx.with_pins, integrand, pins)
            if err:
                return err
            a, err = parse_or_unknown(LAYER, ctx.expr, str(p["a"]))
            if err:
                return err
            b, err = parse_or_unknown(LAYER, ctx.expr, str(p["b"]))
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            (a, b, claimed), err = parse_or_unknown(LAYER, lambda es: tuple(ctx.with_pins(e, pins) for e in es),
                                                    (a, b, claimed))
            if err:
                return err
            # a declared tolerance, read once: |c - v|/|v| <= t against the true value v, t in (0, 1); anything
            # else is a malformed input (equiv.numeric.read_tolerance; YO-4, RK-E, RK-F)
            declared, bad_tol = read_tolerance(p.get("rel_tol"))
            if bad_tol:
                return unknown(LAYER, "malformed_tolerance", t.ms, {"rel_tol": str(p.get("rel_tol"))},
                               flags=["malformed_tolerance"])
            undefined = integrand_undefined_on_a_subinterval(p["integrand"], integrand, var, a, b, ns_i,
                                                             timeout=ctx.timeout, pins=pins)
            if undefined is not False:
                return unknown(LAYER, "integrand_undefined_on_the_interval_as_written" if undefined
                               else "integrand_domain_undecided", t.ms, {"integrand": p["integrand"]},
                               flags=["written_domain"] if undefined else [])
            val, ev = definite_integral_numeric(integrand, var, a, b, timeout=ctx.timeout * 1.5)
            ev["claimed"] = str(claimed)
            converged = val is not None and bool(ev.get("converged", False))
            # SymPy's value is evidence only. It is taken with a symbolic certificate (below) or not at all: a
            # quadrature that agrees with it may share its blind spot (a narrow peak: SymPy's wrong π for
            # ∫_0^π (atan(tan x) + 1 + peak) and tanh-sinh agreed, and 3.14159265358979 was accepted with
            # rel_tol 1e-9; the value is π + π²/2), and SymPy's value can be off by less than any enclosure is
            # wide (2 for ∫_{-1}^{1} (1 + |cos x|/10^80) dx, which is 2 + 2 sin(1)/10^80): attack on d4c
            # round 2, YO-2. An exact 0 needs the certificate as well (fourth audit of 1 Oct 2026, S1)
            rs = sb_run("mathverify.sandbox.ops:integrate_symbolic", integrand, var, a, b, timeout=ctx.timeout)
            if rs.ok and isinstance(rs.value, sp.Basic):
                ev["symbolic"] = str(rs.value)
            # the value the certificate proves (an integrand 0, odd symmetry, the fundamental theorem with a
            # primitive checked by differentiation and continuous on the range, pieces split where it jumps)
            cval, cev = certified_integral_value(integrand, var, a, b, timeout=ctx.timeout * 1.5)
            ev["certificate"] = cev
            if cval is not None:
                if converged and certified_sign(cval, timeout=ctx.timeout) != 0 and \
                        num_equal(cval, val, rel_tol=float(ev.get("rel_err", "1e-25")))[0] is False and \
                        not integral_excludes(integrand, var, a, b, val, timeout=ctx.timeout * 1.5)[0]:
                    # a proof that a converged numeric value contradicts, and no rigorous enclosure that shows the
                    # numeric value wrong: something is wrong (never the declared tolerance here: it let SymPy's
                    # wrong value "agree", YO-2). A quadrature that missed a narrow peak (1/3 for ∫_0^1 (x² +
                    # e^(-10^8 (x - 1/3)²)) dx, which the erf primitive proves) is shown wrong and the proof stands
                    return unknown(LAYER, "symbolic_numeric_disagreement", t.ms, ev,
                                   flags=["symbolic_numeric_disagreement"])
                ev["decided_by"] = "certified_value"
                if declared is not None:
                    ok = within_rel_tol(claimed, cval, declared, timeout=ctx.timeout)
                    if ok is None:
                        return unknown(LAYER, "relative_tolerance_undecided", t.ms, ev,
                                       flags=["relative_tolerance_undecided"])
                else:
                    ok, sev = answers_equivalent(claimed, cval, shape="scalar")
                    ev["compare_exact"] = sev
            elif declared is not None:
                # an approximate claim and no proved value: a rigorous enclosure inside the tolerance accepts,
                # one outside it refutes
                ok, tev = tolerance_by_enclosure(integrand, var, a, b, claimed, declared, timeout=ctx.timeout * 1.5)
                ev["enclosure"] = tev
                ev["decided_by"] = "rigorous_enclosure_and_tolerance"
                if ok is None:
                    return unknown(LAYER, "no_certified_value", t.ms, ev, flags=["no_certified_value"])
            else:
                # no value proved: a claim outside a rigorous enclosure is refuted, nothing is accepted
                no, xev = integral_excludes(integrand, var, a, b, claimed, timeout=ctx.timeout * 1.5)
                ev["enclosure"] = xev
                if not no:
                    return unknown(LAYER, "no_certified_value", t.ms, ev, flags=["no_certified_value"])
                ok = False
                ev["decided_by"] = "rigorous_enclosure"
            conf = 0.99
        elif kind == "derivative":
            # a symbol a given or a declared constraint fixes is read as its value in f, the point and the
            # claim (`Ctx.task_pins`): with a = 3 the derivative 6*x of a*x**2 was refuted
            pins = ctx.task_pins(var)
            f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
            if err:
                return err
            bad = _unreadable_task_expression(p["f"], f, var, ctx.ns, t.ms,
                                              neighbourhoods(_closed_real(p.get("at"), ctx, pins)))
            if bad is not None:
                return bad
            f, err = parse_or_unknown(LAYER, ctx.with_pins, f, pins)
            if err:
                return err
            try:
                order = int(p.get("order", 1))
            except (TypeError, ValueError):
                return unknown(LAYER, "bad_order")
            if order < 1:
                return unknown(LAYER, "bad_order")
            ca = solution.claimed_answer
            if "at" in p:
                at, err = parse_or_unknown(LAYER, ctx.expr, str(p["at"]))
                if err:
                    return err
                at, err = parse_or_unknown(LAYER, ctx.with_pins, at, pins)
                if err:
                    return err
                # x²/x is x after parsing, but it has no value (so no derivative) at 0
                if written_undefined_in(p["f"], ctx.ns, var, sp.FiniteSet(at), pins) is not False:
                    # undefined there, or not decided (fail-closed: d4b round 8, YO-2)
                    return unknown(LAYER, "f_undefined_at_point_as_written", t.ms,
                                   {"f": p["f"], "at": str(at)}, flags=["written_domain"])
                bad = _point_not_interior(ctx, p["f"], var, at, pins, t.ms)
                if bad is not None:
                    return bad
                dap = derivative_at_point(f, var, order, at, timeout=ctx.timeout)
                ev["derivative_at_point"] = {k: str(v) for k, v in dap.items()}
                st = dap["status"]
                if ca.kind == "dne":
                    ok = True if st in ("corner", "discontinuous", "cusp") else \
                        False if st == "value" else None
                    cev = {"method": "differentiability", "status": st}
                else:
                    claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
                    if err:
                        return err
                    claimed, err = parse_or_unknown(LAYER, ctx.with_pins, claimed, pins)
                    if err:
                        return err
                    if st == "value":
                        if claimed in (sp.oo, -sp.oo):
                            ok, cev = False, {"method": "finite_derivative"}
                        else:
                            ok, cev = answers_equivalent(claimed, dap["value"], shape="scalar")
                    elif st in ("corner", "discontinuous", "cusp") or (st == "infinite" and claimed not in (sp.oo, -sp.oo)):
                        ok, cev = False, {"method": "not_differentiable", "status": st}
                    else:
                        ok, cev = None, {"method": "undecided", "status": st}
            else:
                r = sb_run("mathverify.sandbox.ops:diff_expr", f, var, order, timeout=ctx.timeout)
                if not r.ok:
                    return unknown(LAYER, "diff_failed", 0, flags=r.flags)
                truth = classical(r.value)
                ev["derivative"] = str(truth)
                claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
                if err:
                    return err
                claimed, err = parse_or_unknown(LAYER, ctx.with_pins, claimed, pins)
                if err:
                    return err
                # the derivative function lives on the open part of the variable's region (`Ctx.domain_for`)
                # where f is defined, and is compared there: on all of ℝ the derivative 1 of |x| under the
                # given x > 0 and of |x| + sqrt(x) - sqrt(x) was refuted (sign(0) = 0 at the end 0), and a
                # function defined at 0 alone or nowhere had both 1 and 0 certified (fourth audit G6, TAN-06)
                unapplied = ctx.unapplied_conditions(var)
                if unapplied:
                    return condition_not_applied(LAYER, unapplied, t.ms)
                conds, other = task_conditions(ctx, p["f"], var, pins)
                # the claim, as written, has a value wherever the derivative exists (`claim_where_derivative`):
                # 2*x**2/x for (x**2)' was certified, 1/(x + 1/a) with a >= 0 too (round 3, RK-8 and YO-3)
                fconds = written_definedness(p["f"], ctx.ns, pins)[0]
                claim_conds, claim_nowhere = written_definedness(str(ca.payload), ctx.claim_ns(solution), pins)
                if other and not _half_line_for_every_value(ctx, conds, other, var):
                    # a parameter of declared sign (a > 0: asin(x/a), log(k*x)): a domain with interior for every
                    # allowed value is proved by one point, the claim by a symbolic identity (R2)
                    ok, cev = for_every_parameter_value(ctx, var, conds, other, f, claimed, truth,
                                                        claim_conds, claim_nowhere, fconds)
                    if cev.get("reason") == "no_interior_point_for_every_value":
                        return condition_not_applied(LAYER, _names(other, var), t.ms)
                else:
                    conds += [c for c in definedness_conditions(f, var) if c not in conds
                              and getattr(c, "free_symbols", set()) == {var} and not isinstance(c, sp.Contains)]
                    dom, loose = task_region(ctx, conds, var)
                    if interior_point(ctx, conds, var, dom) is None:
                        return unknown(LAYER, "region_without_interior", t.ms, {"region": str(dom)},
                                       flags=["point_not_interior"])
                    # ... and off the points where f has no derivative (`kink_reading`, R8)
                    kr = kink_reading(f, var, order, dom, claimed, claim_conds, claim_nowhere, fconds,
                                      timeout=ctx.timeout)
                    kinks, kopen, reasons = kr["kinks"], kr["opens"], kr["reasons"]
                    cstate, cwhy = claim_where_derivative(ctx, claim_conds, claim_nowhere, var, dom, loose, kr,
                                                          fconds)
                    truth_k = _sign_off(truth, kr["signs"])
                    off = sp.FiniteSet(*kinks)
                    cdom = comparison_region(sp.Complement(dom, off) if kinks else dom, loose + kopen, var)
                    if cstate == "undefined":
                        ok, cev = False, {"method": "claim_as_written", "reason": cwhy}
                    else:
                        ok, cev = answers_equivalent(claimed, truth_k, shape="expression", domain=cdom, var=var)
                    if ok is None and ctx.domain_for(var) != S.Reals:
                        # the proof at a kink reads its whole cell: on (1, oo) the cell (0, oo) of log|x| is not
                        # inside, and 1/x was left undecided under x > 1. Agreement where f is defined is agreement
                        # on the region too; a disagreement may lie outside it and refutes nothing
                        wide, wloose = task_region(ctx, conds, var, region=S.Reals)
                        okw, wev = answers_equivalent(
                            claimed, truth_k, shape="expression", var=var,
                            domain=comparison_region(sp.Complement(wide, off) if kinks else wide, wloose + kopen, var))
                        cev["wide"] = wev
                        if okw is True:
                            ok = True
                    if kinks or kopen or reasons or kr["values"]:
                        cev["kinks"] = {"left_out": [str(k) for k in kinks], "families": [str(c) for c in kopen],
                                        "values": [str(k) for k in kr["values"]], "why": sorted(reasons)}
                    if cstate == "undecided":
                        cev["claim_as_written"] = cwhy
                    if ok is True and (reasons or cstate == "undecided"):
                        # equal where the derivative exists, but a value where it does not (sign(0) = 0) is a
                        # convention, an undecided kink no proof, and a claim not proved to have a value where the
                        # derivative does no derivative function
                        ok = None
                    if ok is False and cstate != "undefined" and reasons & {"kinks_not_solved", "kink_budget"}:
                        # zeros of a switch not read stay in the comparison: the disagreement counts at a point
                        # where f is analytic (`_smooth_witness`), and may lie where f has no derivative otherwise
                        w = _smooth_witness(kr, var, claimed, truth_k, dom, loose, fconds, cev)
                        if w is None:
                            ok = None
                        else:
                            cev["smooth_witness"] = str(w)
            ev["compare"] = cev
            conf = 0.99 if cev.get("method") in ("symbolic", "numeric", "differentiability",
                                                 "not_differentiable", "finite_derivative") else 0.97
        else:  # tangent_line
            # the values the givens fix, never the line's own dependent variable (`Ctx.task_pins`)
            pins = ctx.task_pins(var, str(p.get("dep", "y")))
            f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
            if err:
                return err
            at, err = parse_or_unknown(LAYER, ctx.expr, str(p["at"]))
            if err:
                return err
            bad = _unreadable_task_expression(p["f"], f, var, ctx.ns, t.ms,
                                              neighbourhoods(_closed_real(p.get("at"), ctx, pins)))
            if bad is not None:
                return bad
            f, err = parse_or_unknown(LAYER, ctx.with_pins, f, pins)
            if err:
                return err
            at, err = parse_or_unknown(LAYER, ctx.with_pins, at, pins)
            if err:
                return err
            if written_undefined_in(p["f"], ctx.ns, var, sp.FiniteSet(at), pins) is not False:
                # undefined there, or not decided (fail-closed: d4b round 8, YO-2)
                return unknown(LAYER, "f_undefined_at_point_as_written", t.ms,
                               {"f": p["f"], "at": str(at)}, flags=["written_domain"])
            bad = _point_not_interior(ctx, p["f"], var, at, pins, t.ms)
            if bad is not None:
                return bad
            y = ctx.sym(p.get("dep", "y"))
            dap = derivative_at_point(f, var, 1, at, timeout=ctx.timeout)
            ev["derivative_at_point"] = {k: str(v) for k, v in dap.items()}
            st = dap["status"]
            ca = solution.claimed_answer
            if ca.kind == "dne":
                ok = True if st in ("corner", "discontinuous") else False if st in ("value", "infinite") else None
            else:
                claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
                if err:
                    return err
                claimed, err = parse_or_unknown(LAYER, ctx.with_pins, claimed, pins)
                if err:
                    return err
                if not isinstance(claimed, sp.Equality):
                    # allow "m*x + c" expression form meaning y = ...
                    claimed = sp.Eq(y, claimed)
                if st == "value":
                    y0 = sp.simplify(f.subs(var, at))
                    truth = sp.Eq(y, sp.simplify(dap["value"]) * (var - at) + y0)
                elif st == "infinite":
                    truth = sp.Eq(var, at)            # vertical tangent: f continuous, |f'| -> oo
                else:
                    truth = None
                ev["truth"] = str(truth)
                if truth is not None:
                    ok, cev = _line_equal(claimed, truth, var, y)
                    ev["compare"] = cev
                elif st in ("corner", "discontinuous"):
                    ok = False                         # no tangent line exists at a corner
                else:
                    ok = None
            conf = 0.99
    if ok is True:
        return result(LAYER, "pass", conf, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason") or "undecided", t.ms, ev)
