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
"""
from __future__ import annotations

import re
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S, Eq, Ne
from sympy.functions.elementary.hyperbolic import HyperbolicFunction
from sympy.functions.elementary.trigonometric import TrigonometricFunction

from ..equiv import answers_equivalent
from ..equiv.numeric import num_equal, to_mp
from ..equiv.random_point import random_point_equal
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied
from .domain import (definedness_conditions, written_definedness, written_undefined_in, relation_holds_at,
                     in_domain)
from .limits import membership_conditions, written_undefined_everywhere

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


_ZERO_LADDER = (30, 50, 80)


def integral_abs_scale(integrand, var, a, b, pts=None, timeout: float = 8.0):
    """∫|f| over [a, b] (an mpf), or None: the size of the rounding residue a quadrature of f leaves
    at a given precision. A value that cancels to 0 comes out as that residue, not as 0: ∫_0^3 (x² - 2x) dx
    gave -4.6e-55 at 50 digits (third audit of 30 Sep 2026, N2). None unless the 20- and 30-digit
    quadratures agree: on a non-integrable f they grow with the precision (∫_{-1}^{1} |x^-3| came out
    4e48, then 4e68), and such a "scale" would let any residue pass; SymPy even gives 0 for the
    divergent ∫_{-1}^{1} x·e^(1/x²) dx (measured 30 Sep 2026)."""
    a, b = sp.sympify(a), sp.sympify(b)
    if pts is None:
        pts = find_breakpoints(integrand, var, a, b, timeout)
    vals = []
    for dps in (20, 30):
        r = sb_run("mathverify.sandbox.ops:quad_breakpoints", sp.Abs(sp.sympify(integrand)), var, a, b, pts, dps,
                   "tanh-sinh", timeout=timeout)
        if not r.ok:
            return None
        try:
            s = mp.mpf(r.value[0])
        except (TypeError, ValueError):
            return None
        if not (mp.isfinite(s) and s >= 0):
            return None
        vals.append(s)
    s20, s30 = vals
    with mp.workdps(40):
        if abs(s30 - s20) > mp.mpf("1e-3") * s30:
            return None
    return s30


def definite_integral_is_zero(integrand, var, a, b, timeout: float = 12.0) -> tuple[bool | None, dict[str, Any]]:
    """Is ∫_a^b f exactly 0, as far as numbers can tell? True, False (certainly not 0) or None.

    A relative tolerance cannot compare anything with an exact 0: every integral whose value is 0 came
    out as a residue of 1e-51...1e-59, so SymPy's right value 0 was never confirmed, the claim 0 stayed
    UNKNOWN and a true step "∫_0^3 (x² - 2x) dx = 0" was refuted (third audit of 30 Sep 2026, N2).
    The residue is measured against the integrand's own scale S = ∫|f| instead, at EVERY rung of the
    ladder (30, 50, 80 digits): True when |value| and the integrator's error estimate are both at most
    10^-(dps-10)·S at each rung, i.e. the residue falls with the precision. A value that is not 0 stays
    where it is: ∫_0^1 10^-40 dx is 1e-40 at every rung, above the 50-digit (1e-40) and far above the
    80-digit bound (1e-110 here, S being 1e-40), so no value above ~1e-70·S is ever taken for 0.
    False only when the value stands clear of that bound (and of ten times the error estimate) at the
    two highest rungs and the two agree: a difference is not called nonzero inside the residue."""
    ev: dict[str, Any] = {"integrand": str(integrand), "a": str(a), "b": str(b)}
    if isinstance(integrand, sp.Basic) and integrand.has(sp.Integral, sp.Sum, sp.Product, sp.Limit):
        ev["error"] = "a form inside the integrand has no confirmed numeric value"
        return None, ev
    a, b = sp.sympify(a), sp.sympify(b)
    if not (a.is_finite and b.is_finite):
        ev["error"] = "infinite range"
        return None, ev
    pts = find_breakpoints(integrand, var, a, b, timeout)
    scale = integral_abs_scale(integrand, var, a, b, pts, timeout)
    if scale is None:
        ev["error"] = "no scale: the integral of |f| failed"
        return None, ev
    ev["abs_scale"] = mp.nstr(scale, 5)
    rungs = []
    for dps in _ZERO_LADDER:
        r = sb_run("mathverify.sandbox.ops:quad_breakpoints", sp.sympify(integrand), var, a, b, pts, dps,
                   "tanh-sinh", timeout=timeout * (2 if dps == 80 else 1))
        if not r.ok:
            ev["error"] = r.error
            ev["flags"] = r.flags
            return None, ev
        val_s, err_s = r.value
        with mp.workdps(dps + 10):
            try:
                v = mp.mpf(val_s)
                err = abs(mp.mpf(err_s)) if err_s not in (None, "None") else mp.inf
            except (TypeError, ValueError):     # a complex value, or no number at all
                ev["error"] = f"no real value at {dps} digits: {val_s}"
                return None, ev
            bound = mp.mpf(10) ** (-(dps - 10)) * scale
            rungs.append((dps, v, err, bound))
        ev.setdefault("ladder", []).append({"dps": dps, "value": mp.nstr(v, 5), "err": mp.nstr(err, 5),
                                            "bound": mp.nstr(bound, 5)})
    if all(mp.isfinite(v) and abs(v) <= bound and err <= bound for _, v, err, bound in rungs):
        ev["decided_by"] = "residue_below_the_scale_bound_at_every_rung"
        return True, ev
    (_, v1, e1, b1), (_, v2, e2, b2) = rungs[-2:]
    if all(mp.isfinite(x_) for x_ in (v1, v2, e1, e2)) and abs(v1) > 10 * (b1 + e1) \
            and abs(v2) > 10 * (b2 + e2) and abs(v2 - v1) <= 10 * (e1 + e2) + b1:
        ev["decided_by"] = "value_stable_above_the_residue"
        return False, ev
    ev["decided_by"] = "undecided"
    return None, ev


def integrand_undefined_on_a_subinterval(src, expr, var, a, b, ns, timeout: float = 8.0) -> bool | None:
    """Is the integrand, as written or as parsed, undefined on a piece of (a, b) of positive
    length? Isolated points are fine (improper integrals). exp(log(x)) parses to x, and
    "∫_{-2}^{-1} exp(log x) dx = -3/2" was certified (audit of 25 Sep 2026)."""
    ineq = (sp.StrictLessThan, sp.LessThan, sp.StrictGreaterThan, sp.GreaterThan)
    conds = [c for c in list(written_definedness(src, ns)[0]) + list(definedness_conditions(expr, var))
             if isinstance(c, ineq) and c.free_symbols == {var}]
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
_JUMPY = (sp.floor, sp.ceiling, sp.frac, sp.Piecewise, sp.Heaviside, sp.DiracDelta, sp.Mod)


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


def antiderivative_domain_check(F, f, var, discourse=S.Reals, f_extra=(), F_extra=(),
                                timeout: float = 8.0) -> tuple[bool | None, dict[str, Any]]:
    """F' = f is not enough: F must be real and continuous at every point where f is defined.
    False comes with a witness point (f defined there, F not / F jumps there); True needs a proof
    (the offending set is empty, or it misses the domain of f); otherwise None. Periodic domains
    are not solved as sets: solveset returns ONE period for `1 + cos(x) != 0` (measured)."""
    ev: dict[str, Any] = {}
    F, f = sp.sympify(F), sp.sympify(f)
    if F.has(*_JUMPY):
        ev["reason"] = "discontinuous_primitive_in_antiderivative"
        return None, ev
    cf = _conditions(f, var, f_extra)
    cF = _conditions(F, var, F_extra)
    if cf is None or cF is None:
        ev["reason"] = "conditions_involve_parameters"
        return None, ev
    for s_ in F.atoms(sp.sign):                   # sign(u) jumps where u changes sign
        if s_.args[0].has(var):
            c = Ne(s_.args[0], 0)
            if c not in cF:
                cF.append(c)
    todo = [c for c in cF if c not in cf]
    ev["checked_conditions"] = [str(c) for c in todo]
    df = None
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
            if any(cc.has(TrigonometricFunction, HyperbolicFunction) for cc in cf):
                ev["reason"] = f"undecided (periodic domain): {c}"
                return None, ev
            df = discourse
            for cc in cf:
                rr = sb_run("mathverify.sandbox.ops:solveset_in", cc, var, S.Reals, timeout=timeout)
                if not rr.ok or rr.value.has(sp.ConditionSet):
                    ev["reason"] = f"undecided domain: {cc}"
                    return None, ev
                df = sp.Intersection(df, rr.value)
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
    return True, ev


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
        # domain-aware numeric equality of dF and integrand
        if domain is None:
            dom = S.Reals
            for c in definedness_conditions(integrand, var) + definedness_conditions(F, var):
                rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=timeout)
                if rr.ok and not isinstance(rr.value, sp.ConditionSet):
                    dom = sp.Intersection(dom, rr.value)
            domain = dom
        ev["domain"] = str(domain)
        ok, rev = random_point_equal(dF, integrand, var, domain, seed=0, n=40)
        ev["random_point"] = rev
        ev["method"] = "random_point"
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


def _unreadable_task_expression(src, expr, var, ns, ms):
    """UNKNOWN when the task's function or integrand is undefined as written for every value of `var`
    (limits.written_undefined_everywhere) or carries a membership condition on it
    (limits.membership_conditions); None when neither holds."""
    if written_undefined_everywhere(src, ns):
        return unknown(LAYER, "expression_undefined_as_written", ms, {"expr": src},
                       flags=["expression_undefined_as_written"])
    members = membership_conditions(src, expr, var, ns)
    if members:
        return unknown(LAYER, "membership_condition_on_variable", ms, {"conditions": [str(c) for c in members]},
                       flags=["membership_condition"])
    return None


def _point_not_interior(ctx: Ctx, var, at, ms):
    """UNKNOWN unless `at` is an interior point of the variable's domain (`Ctx.domain_for`): a derivative
    and a tangent line are two-sided (a one-sided derivative is no derivative in the curriculum). With x
    declared positive the parse folds |x| and sqrt(x**2) to x, and with x declared nonnegative 0 is the
    closed end: there the derivative 1 and the tangent y = x of |x| at 0 were certified (30 Sep 2026).
    A condition naming a symbol no given fixes (x >= b, b free) leaves the domain unknown: the
    certificate abstains (part vi). None when the point is interior."""
    unapplied = ctx.unapplied_conditions(var)
    if unapplied:
        return condition_not_applied(LAYER, unapplied, ms)
    try:
        inside = in_domain(ctx.domain_for(var).interior, at)
    except Exception:  # noqa: BLE001 - an interior SymPy cannot form is no proof
        inside = None
    if inside is not True:
        return unknown(LAYER, "point_not_interior_to_the_domain", ms,
                       {"at": str(at), "domain": str(ctx.domain_for(var))}, flags=["point_not_interior"])
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
            integrand, err = parse_or_unknown(LAYER, ctx.expr, p["integrand"])
            if err:
                return err
            bad = _unreadable_task_expression(p["integrand"], integrand, var, ctx.ns, t.ms)
            if bad is not None:
                return bad
            from ..normalize.parse import parse_expr_str
            payload = _TRAILING_C.sub("", str(solution.claimed_answer.payload))
            C = sp.Symbol("C")
            ns2, err = parse_or_unknown(LAYER, ctx.claim_ns, solution, C=C)
            if err:
                return err
            F_full, err = parse_or_unknown(LAYER, parse_expr_str, payload, ns2)
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
            f_extra = written_definedness(p["integrand"], ctx.ns)[0]
            F_extra = [c for c in written_definedness(payload, ns2)[0] if not c.has(C)]
            ok, ev = antiderivative_certificate(F, integrand, var, timeout=ctx.timeout,
                                                discourse=ctx.domain_for(var), f_extra=f_extra,
                                                F_extra=F_extra)
            conf = 0.99 if ev.get("method") == "symbolic" else 0.97
        elif kind == "definite_integral":
            # the variable of a definite integral runs over [a, b], not over its declared domain (the
            # rule of normalize.parse for a written Integral): with x declared positive, ∫_{-1}^{1} |x| dx
            # was read as ∫ x dx = 0 and the claim 0 certified (audit of 29 Sep 2026)
            from ..normalize.parse import parse_expr_str
            var = sp.Symbol(var.name, real=True)
            ns_i = dict(ctx.ns, **{var.name: var})
            integrand, err = parse_or_unknown(LAYER, parse_expr_str, p["integrand"], ns_i)
            if err:
                return err
            bad = _unreadable_task_expression(p["integrand"], integrand, var, ns_i, t.ms)
            if bad is not None:
                return bad
            a, err = parse_or_unknown(LAYER, ctx.expr, str(p["a"]))
            if err:
                return err
            b, err = parse_or_unknown(LAYER, ctx.expr, str(p["b"]))
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            undefined = integrand_undefined_on_a_subinterval(p["integrand"], integrand, var, a, b, ns_i,
                                                             timeout=ctx.timeout)
            if undefined is not False:
                return unknown(LAYER, "integrand_undefined_on_the_interval_as_written" if undefined
                               else "integrand_domain_undecided", t.ms, {"integrand": p["integrand"]},
                               flags=["written_domain"] if undefined else [])
            val, ev = definite_integral_numeric(integrand, var, a, b, timeout=ctx.timeout * 1.5)
            if val is None:
                return unknown(LAYER, "numeric_integration_failed", 0, ev, flags=ev.get("flags", []))
            ev["claimed"] = str(claimed)
            declared = float(p.get("rel_tol") or 0.0)
            tol = max(declared, float(ev.get("rel_err", "1e-25")))
            ev["rel_tol_used"] = tol
            converged = bool(ev.get("converged", False))
            okN, cev = num_equal(claimed, val, rel_tol=tol)
            ev["compare"] = cev
            # an exact value, when SymPy has one, is what the claim is compared with: a numeric
            # tolerance of 1e-25 accepted 262537412640768743 for ∫_0^{π√163} e^x dx, whose value
            # is e^(π√163) - 1 = 262537412640768742.99999999999925… (audit of 25 Sep 2026)
            exact = None
            rs = sb_run("mathverify.sandbox.ops:integrate_symbolic", integrand, var, a, b, timeout=ctx.timeout)
            if rs.ok and not rs.value.has(sp.Integral) and not rs.value.free_symbols \
                    and not rs.value.has(sp.AccumBounds, sp.zoo, sp.nan):
                exact = rs.value
                ev["symbolic"] = str(exact)
            # an exact 0 on either side is no relative comparison: the numbers of an integral whose
            # value is 0 are a residue of 1e-51...1e-59, and SymPy's right 0 disagreed with them, the
            # claim 0 was refuted (third audit of 30 Sep 2026, N2). The residue is measured against
            # the integrand's scale at every rung instead (a nonzero value is never taken for 0).
            exact_zero = exact is not None and exact == 0
            claimed_zero = isinstance(claimed, sp.Basic) and claimed.is_Rational and claimed == 0
            if exact_zero or claimed_zero:
                zero, zev = definite_integral_is_zero(integrand, var, a, b, timeout=ctx.timeout * 1.5)
                ev["zero_test"] = zev
                if claimed_zero:
                    okN = zero
            if exact is not None:
                agree, _ = num_equal(exact, val, rel_tol=tol) if not exact_zero else (zero, None)
                ev["symbolic_agrees_numeric"] = agree
                if declared:
                    # a declared tolerance means an approximate answer: compare with the exact value's
                    # decimal expansion (two Rationals would be compared exactly, ignoring rel_tol)
                    okS, sev = num_equal(claimed, sp.N(exact, 60), rel_tol=declared)
                else:
                    okS, sev = answers_equivalent(claimed, exact, shape="scalar")
                ev["compare_exact"] = sev
                if converged and agree is True:
                    ok = okS if okS is not None else (False if okN is False else None)
                elif okS is False and okN is False:
                    ok = False                     # two independent computations reject the claim
                else:
                    # a numeric value that did not converge (x^(-999/1000) on [0,1]: 176.5 instead
                    # of 1000) or that contradicts SymPy never decides alone
                    reason = "numeric_not_converged" if not converged else "symbolic_numeric_disagreement"
                    return unknown(LAYER, reason, t.ms, ev, flags=[reason])
            elif converged:
                ok = okN
            else:
                return unknown(LAYER, "numeric_not_converged", t.ms, ev, flags=["numeric_not_converged"])
            conf = 0.99
        elif kind == "derivative":
            f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
            if err:
                return err
            bad = _unreadable_task_expression(p["f"], f, var, ctx.ns, t.ms)
            if bad is not None:
                return bad
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
                bad = _point_not_interior(ctx, var, at, t.ms)
                if bad is not None:
                    return bad
                # x²/x is x after parsing, but it has no value (so no derivative) at 0
                if written_undefined_in(p["f"], ctx.ns, var, sp.FiniteSet(at)) is True:
                    return unknown(LAYER, "f_undefined_at_point_as_written", t.ms,
                                   {"f": p["f"], "at": str(at)}, flags=["written_domain"])
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
                dom = ctx.domain_for(var)
                for c in definedness_conditions(f, var) + [c for c in written_definedness(p["f"], ctx.ns)[0]
                                                           if c.free_symbols == {var}]:
                    rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=ctx.timeout)
                    if rr.ok and not isinstance(rr.value, sp.ConditionSet):
                        dom = sp.Intersection(dom, rr.value)
                ok, cev = answers_equivalent(claimed, truth, shape="expression", domain=dom, var=var)
            ev["compare"] = cev
            conf = 0.99 if cev.get("method") in ("symbolic", "numeric", "differentiability",
                                                 "not_differentiable", "finite_derivative") else 0.97
        else:  # tangent_line
            f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
            if err:
                return err
            at, err = parse_or_unknown(LAYER, ctx.expr, str(p["at"]))
            if err:
                return err
            bad = _unreadable_task_expression(p["f"], f, var, ctx.ns, t.ms) \
                or _point_not_interior(ctx, var, at, t.ms)
            if bad is not None:
                return bad
            if written_undefined_in(p["f"], ctx.ns, var, sp.FiniteSet(at)) is True:
                return unknown(LAYER, "f_undefined_at_point_as_written", t.ms,
                               {"f": p["f"], "at": str(at)}, flags=["written_domain"])
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
