"""Limits (E6): both one-sided limits, AccumBounds/zoo classification, numeric probe.

Audit of 25 Sep 2026 (each item was measured as a false verdict before the change):
  * a limit is a REAL limit: a side on which the expression is not real-valued near the point is
    not approached (lim_{x->0-} sqrt(x) was certified 0, lim_{x->0} sqrt(x-1) was certified I);
  * AccumBounds is an enclosure, not a proof of divergence: sin(x)^2 + cos(x)^2 came back as
    AccumBounds(0, 2) and "does not exist" was certified;
  * an oscillating factor whose zeros accumulate at the point, inside a log or a non-integer power,
    is where SymPy's own limit is wrong (|sin x|^(1/x) -> 1, although it is 0 at every k*pi);
  * the numeric probe ran in the main process without a timeout (exp(-exp(x)) never returned).
"""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp
from sympy import oo, zoo, nan, AccumBounds, S, Interval
from sympy.functions.elementary.hyperbolic import HyperbolicFunction

from ..equiv import answers_equivalent
from ..equiv.numeric import certified_sign, to_mp
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from ..sandbox.exactsets import at_risk
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied
from .domain import (Convention, _violations, closed_condition_undecided, convention_null_on, definedness_conditions,
                     open_conditions_empty, written_definedness)

LAYER = "certify.limits"

_UNEVALUATED = (sp.Limit, sp.Derivative, sp.Integral, sp.Subs, sp.Sum, sp.Product)
_OSCILLATORS = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.floor, sp.ceiling, sp.frac, sp.sign)
_INEQ = (sp.StrictLessThan, sp.LessThan, sp.StrictGreaterThan, sp.GreaterThan)


def _is_real_number(v) -> bool | None:
    """True / False / None (undecided) for a closed-form number."""
    r = getattr(v, "is_real", None)
    if r is True or r is False:
        return r
    try:
        return not isinstance(to_mp(v, 30), mp.mpc)
    except Exception:  # noqa: BLE001
        return None


def _kind_of(v) -> str:
    """VAR (a real number) | INF (+-oo) | OSC (AccumBounds involved, needs corroboration) |
    UNKNOWN. A complex value is UNKNOWN: a real limit never has one (audit of 25 Sep 2026)."""
    if v is None:
        return "UNKNOWN"
    if isinstance(v, AccumBounds) or (hasattr(v, "has") and v.has(AccumBounds)):
        return "OSC"
    if v in (oo, -oo):
        return "INF"
    if v is zoo or v is nan or (hasattr(v, "has") and v.has(zoo, nan)):
        return "UNKNOWN"
    if hasattr(v, "has") and v.has(*_UNEVALUATED):
        return "UNKNOWN"
    if getattr(v, "is_number", False) or not getattr(v, "free_symbols", {None}):
        return "VAR" if _is_real_number(v) is True else "UNKNOWN"
    return "UNKNOWN"


def limit_conditions(expr, var, extra=()) -> list[Any]:
    """Inequality definedness conditions in `var` alone (sqrt, log, asin, real powers). `!=`
    conditions remove isolated points only and never keep a side from being approached."""
    out: list[Any] = []
    for c in list(definedness_conditions(expr, var)) + list(extra):
        if isinstance(c, _INEQ) and c.free_symbols == {var} and c not in out:
            out.append(c)
    return out


def _side_status(conds, var, point, side):
    """Worker: is the expression real-valued on a whole one-sided neighbourhood of `point`
    ("full"), on none of it ("empty"), or neither / undecidable (None)? Only algebraic
    conditions are solved: solveset on periodic conditions is not trusted (it returns a single
    period for `1 + cos(x) != 0`, measured 25 Sep 2026)."""
    # (the trigonometric part of this rule is sandbox.exactsets.at_risk, shared with every solveset)
    if any(at_risk(c, var) or c.has(HyperbolicFunction) for c in conds):
        return None
    bad = S.EmptySet
    good = S.Reals
    for c in conds:
        good = sp.Intersection(good, sp.solveset(c, var, S.Reals))
        bad = sp.Union(bad, sp.solveset(c.negated, var, S.Reals))
    if good.has(sp.ConditionSet) or bad.has(sp.ConditionSet):
        return None
    if point == oo:
        region, far = Interval(0, oo), (lambda s_: s_.sup < oo)
    elif point == -oo:
        region, far = Interval(-oo, 0), (lambda s_: s_.inf > -oo)
    elif side == "+":
        region, far = Interval.open(point, point + 1), (lambda s_: s_.inf > point)
    else:
        region, far = Interval.open(point - 1, point), (lambda s_: s_.sup < point)
    b = sp.Intersection(bad, region)
    if b is S.EmptySet or far(b) is sp.true:
        return "full"
    g = sp.Intersection(good, region)
    if g is S.EmptySet or far(g) is sp.true:
        return "empty"
    return None


def _oscillation_risk(expr, var, point, dirs) -> bool:
    """Worker: does an oscillating function whose argument diverges at the point sit inside a
    log or a non-integer / variable power? Its zeros accumulate at the point there, and SymPy's
    limit ignores them (measured: lim_{x->oo} |sin x|^(1/x) = 1, although the expression is 0 at
    every k*pi, so the limit does not exist)."""
    sensitive = []
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.log):
            sensitive.append(node.args[0])
        elif isinstance(node, sp.Pow):
            b, e = node.args
            if var in e.free_symbols or not e.is_Integer:
                sensitive.append(b)
    for s_ in sensitive:
        for o in sp.preorder_traversal(s_):
            if isinstance(o, _OSCILLATORS) and o.args[0].has(var):
                for d in dirs:
                    lim = sp.limit(o.args[0], var, point) if point in (oo, -oo) \
                        else sp.limit(o.args[0], var, point, d)
                    if lim in (oo, -oo) or not getattr(lim, "is_number", False) or lim.has(AccumBounds):
                        return True
    return False


def _oscillation(expr, var, point, side) -> list[tuple[float, float, float]] | None:
    """Worker: relative spread of the (real) values on shrinking windows approaching the point.
    Evidence of genuine oscillation only: an identity such as sin^2 + cos^2 has spread ~1e-30."""
    f = sp.lambdify(var, expr, "mpmath")
    out = []
    with mp.workdps(30):
        for k in (2, 4, 6, 8):
            if point == oo:
                xs = [mp.mpf(10) ** k + mp.mpf(j) * mp.mpf("0.37") for j in range(300)]
            elif point == -oo:
                xs = [-(mp.mpf(10) ** k) - mp.mpf(j) * mp.mpf("0.37") for j in range(300)]
            else:
                p = mp.mpf(str(sp.N(point, 40)))
                sgn = 1 if side == "+" else -1
                h0 = mp.mpf(10) ** (-k)
                xs = [p + sgn * h0 * (1 + mp.mpf(j) / 300) for j in range(300)]
            vals = []
            for xv in xs:
                try:
                    v = f(xv)
                    if isinstance(v, mp.mpc):
                        if abs(v.imag) > mp.mpf(10) ** -20 * max(1, abs(v.real)):
                            continue
                        v = v.real
                    v = mp.mpf(v)
                except Exception:  # noqa: BLE001
                    continue
                if mp.isfinite(v):
                    vals.append(v)
            if len(vals) < 100:
                return None
            hi, lo = max(vals), min(vals)
            out.append((float((hi - lo) / max(1, abs(hi), abs(lo))), float(lo) if abs(lo) < 1e300 else float(mp.sign(lo)) * 1e300,
                        float(hi) if abs(hi) < 1e300 else float(mp.sign(hi)) * 1e300))
    return out


def _grows_without_bound(windows) -> bool:
    """The values on the nearest window stay on one side of 0 and their envelope towards 0 grew a
    hundredfold from the first window: they tend to ±oo while oscillating, which is no DNE.
    x(2 + sin x) -> oo was certified as DNE and oo refuted (audit of 29 Sep 2026)."""
    (_, lo0, hi0), (_, lo1, hi1) = windows[0], windows[-1]
    return (lo0 > 0 and lo1 >= 100 * lo0) or (hi0 < 0 and hi1 <= 100 * hi0)


def _limit_dir(expr, var, point, d):
    return sp.limit(expr, var, point, d)


def _limit_simplified(expr, var, point, d=None):
    e = sp.simplify(expr)
    if point in (oo, -oo) or d is None:
        return sp.limit(e, var, point)
    return sp.limit(e, var, point, d)


def _one_side(expr, var, point, d, timeout) -> tuple[str, Any, dict[str, Any]]:
    """Classify the limit from one side (d is '+' or '-'; ignored at +-oo)."""
    ev: dict[str, Any] = {}
    if point in (oo, -oo):
        r = sb_run("mathverify.sandbox.ops:limit_default", expr, var, point, timeout=timeout)
    else:
        r = sb_run("mathverify.certify.limits:_limit_dir", expr, var, point, d, timeout=timeout)
    if not r.ok:
        ev["error"], ev["flags"] = r.error, r.flags
        return "UNKNOWN", None, ev
    v = r.value
    k = _kind_of(v)
    ev["sympy"] = str(v)
    if k == "VAR":
        # SymPy's one-sided limit is corroborated numerically: it returns 2 for the left limit
        # of Piecewise((x**2, x < 1), (2*x, x >= 1)) at 1, whose true value is 1 (measured)
        vals = _probe(expr, var, point, d, timeout)
        ev["numeric_probe"] = vals
        if _probe_agrees(vals, v) is False:
            ev["flags"] = ["symbolic_numeric_disagreement"]
            return "UNKNOWN", v, ev
        if all(x_ is None for x_ in vals):
            # nothing near the point could be evaluated, so nothing corroborates SymPy, which
            # substitutes into a function it does not know: lim_{x->0} gcd(x, 4) = 4 was certified
            # (audit of 29 Sep 2026)
            ev["flags"] = ["numeric_probe_failed"]
            return "UNKNOWN", v, ev
    if k != "OSC":
        return k, v, ev
    # AccumBounds only says where the limit points could lie. It is DNE when the values really
    # keep oscillating; an identity in disguise is retried after simplification instead.
    ro = sb_run("mathverify.certify.limits:_oscillation", expr, var, point, d, timeout=timeout)
    ev["oscillation_spread"] = [w[0] for w in ro.value] if ro.ok and ro.value else None
    if ro.ok and ro.value and all(w[0] >= 1e-3 for w in ro.value):
        if _grows_without_bound(ro.value):
            ev["flags"] = ["oscillates_while_diverging"]
            return "UNKNOWN", v, ev
        return "DNE", v, ev
    rs = sb_run("mathverify.certify.limits:_limit_simplified", expr, var, point,
                None if point in (oo, -oo) else d, timeout=timeout)
    if rs.ok:
        ks = _kind_of(rs.value)
        ev["simplified"] = str(rs.value)
        if ks == "VAR" and _probe_agrees(_probe(expr, var, point, d, timeout), rs.value) is False:
            ev["flags"] = ["symbolic_numeric_disagreement"]
            return "UNKNOWN", rs.value, ev
        if ks in ("VAR", "INF"):
            return ks, rs.value, ev
    return "UNKNOWN", v, ev


def classify_limit(expr, var, point, side: str | None = None, timeout: float = 8.0,
                   conds=None) -> dict[str, Any]:
    """Return {"kind": VAR|INF|DNE|UNKNOWN, "value", "left", "right", ...}.

    `conds`: inequality definedness conditions (see `limit_conditions`); derived from `expr`
    when None. A side on which the expression is not real-valued is not approached."""
    out: dict[str, Any] = {"kind": "UNKNOWN", "value": None, "left": None, "right": None, "point": str(point)}
    if conds is None:
        conds = limit_conditions(expr, var)
    if point in (oo, -oo):
        sides = ["-"] if point == oo else ["+"]
    elif side in ("+", "-"):
        sides = [side]
    else:
        sides = ["+", "-"]
    status: dict[str, Any] = {}
    for d in sides:
        if not conds:
            status[d] = "full"
            continue
        r = sb_run("mathverify.certify.limits:_side_status", conds, var, point, d, timeout=timeout)
        status[d] = r.value if r.ok else None
    out["side_status"] = dict(status)
    if any(s_ is None for s_ in status.values()):
        out["reason"] = "domain_near_point_undecided"
        return out
    full = [d for d in sides if status[d] == "full"]
    if not full:
        out["kind"] = "DNE"                     # the point is not approached within the domain
        out["reason"] = "not_real_valued_near_point"
        return out
    rr = sb_run("mathverify.certify.limits:_oscillation_risk", expr, var, point, full, timeout=timeout)
    if not rr.ok or rr.value is not False:
        out["reason"] = "oscillating_factor_in_log_or_power"
        return out
    res = {}
    for d in full:
        k, v, ev = _one_side(expr, var, point, d, timeout)
        res[d] = (k, v)
        out.setdefault("sides", {})[d] = ev
        if ev.get("flags"):
            out.setdefault("flags", []).extend(ev["flags"])
    if "+" in res:
        out["right"] = res["+"][1]
    if "-" in res:
        out["left"] = res["-"][1]
    kinds = [res[d][0] for d in full]
    if len(full) < len(sides):
        # one side lies outside the domain: "lim_{x->0} sqrt(x)" is 0 in one convention and does
        # not exist in another. Only an approached side that itself diverges decides it.
        out["kind"] = "DNE" if "DNE" in kinds else "UNKNOWN"
        out["reason"] = "only_one_side_in_domain"
        return out
    if len(full) == 1:
        k, v = res[full[0]]
        out["kind"] = k
        out["value"] = v if k in ("VAR", "INF") else None
        return out
    (kp, plus), (km, minus) = res["+"], res["-"]
    if "UNKNOWN" in (kp, km):
        return out
    if kp == "DNE" or km == "DNE":
        out["kind"] = "DNE"
        return out
    if kp != km:
        out["kind"] = "DNE"
        return out
    if kp == "INF":
        if plus == minus:
            out["kind"] = "INF"
            out["value"] = plus
        else:
            out["kind"] = "DNE"
        return out
    same = scalar_equal(plus, minus)
    if same is True:
        out["kind"] = "VAR"
        out["value"] = plus
    elif same is False:
        out["kind"] = "DNE"
    else:
        out["kind"] = "UNKNOWN"
    return out


def numeric_probe(expr, var, point, side: str, dps: int = 50) -> list[str | None]:
    """f(point ± h) for shrinking h (or growing x for ±oo). Evidence only. Runs in the sandbox
    worker (see `_probe`): exp(-exp(10^6)) alone never returned in the main process."""
    f = sp.lambdify(var, expr, "mpmath")
    vals = []
    with mp.workdps(dps):
        if point in (oo, -oo):
            xs = [mp.mpf(10) ** k * (1 if point == oo else -1) for k in (3, 6, 9, 12)]
        else:
            p = mp.mpf(str(sp.N(point, dps + 5)))
            sgn = 1 if side == "+" else -1
            xs = [p + sgn * mp.mpf(10) ** (-k) for k in (3, 6, 9, 12)]
        for xv in xs:
            try:
                v = f(xv)
                vals.append(mp.nstr(v, 12))
            except Exception:
                vals.append(None)
    return vals


def _probe(expr, var, point, side, timeout) -> list[str | None]:
    r = sb_run("mathverify.certify.limits:numeric_probe", expr, var, point, side, timeout=timeout)
    return r.value if r.ok else [None]


def _probe_agrees(vals: list[str | None], target) -> bool | None:
    try:
        last = vals[-1]
        if last is None:
            return None
        tv = mp.mpf(str(sp.N(target, 30)))
        lv = mp.mpmathify(last)
        if isinstance(lv, mp.mpc):
            if abs(lv.imag) > 1e-6 * max(1, abs(lv.real)):
                return False
            lv = lv.real
        scale = max(abs(tv), mp.mpf(1))
        return abs(lv - tv) / scale < mp.mpf("1e-5")
    except Exception:
        return None


def written_undefined_everywhere(src, ns) -> bool:
    """Is a task's expression (limit, derivative, tangent line, integral, extremum), AS WRITTEN,
    defined for no value of its variable? A condition that fails outright (`log(-1)` needs -1 > 0), or
    a closed one no exact check proves (`closed_condition_undecided`). `written_definedness` records the
    first only through the expression's free symbols, so an expression with none (log(-1) - log(-1) + 2
    is 2 after parsing) passed: its limit 2, its derivative 0, the tangent y = 2 and its maximum 2 on
    [0, 1] were certified, and x + acos(2) - acos(2) had the derivative 1 and the integral 1/2 over
    [0, 1] (30 Sep 2026). Open conditions that hold nowhere together count too (`open_conditions_empty`):
    the limit 1 of x + log(x) - log(x) + log(-x) - log(-x) at 1 was refuted as if it had values (fourth
    audit TAN-06)."""
    from ..normalize.parse import parse_as_written
    e = parse_as_written(src, ns)
    if e is None:
        return False
    try:
        conds = definedness_conditions(e, None)
    except Exception:  # noqa: BLE001 - a failed reading adds no fact
        return False
    return any(c is sp.false for c in conds) or closed_condition_undecided(conds) or open_conditions_empty(conds)


def membership_conditions(src, expr, var, ns, pins=None) -> list[Any]:
    """The membership conditions naming `var` (a gcd/lcm argument rational, an n! or C(n, r) argument a
    natural number: certify.domain) of a task's expression, as written or as parsed. No interval rule
    reads them, and the limit, derivative and integral certificates dropped them: with x + x! - x!
    (x after parsing), the limit -3 at -3, the derivative 1 at -3 and the integral -4 over [-3, -1]
    were certified, although the expression has a value at the natural numbers alone (30 Sep 2026). A
    variable whose declaration settles the membership (n a positive integer: n! has its value) carries
    no such condition. The values the givens fix (`pins`, `Ctx.task_pins`) are put in: the condition of
    atan2(y, x) that y**2 + x**2 is not 0 holds for every x with y = 2, and the derivative -1/2 at 0 was
    UNKNOWN (round 9 of part d4b, RK-5)."""
    conds = list(written_definedness(src, ns)[0])
    try:
        conds += definedness_conditions(expr, var)
    except Exception:  # noqa: BLE001 - a failed reading adds no fact
        pass
    if pins:
        conds = [c.xreplace(pins) if isinstance(c, sp.Basic) else c for c in conds]
    return [c for c in dict.fromkeys(conds) if isinstance(c, sp.Contains) and var in c.free_symbols]


_DELTAS = (S.Half, S.One / 10, S.One / 1000)
_TAILS = (S.Zero, S(10), S(1000), S(10) ** 6)


def membership_holds_on(c, var, regions) -> bool:
    """Does the membership condition `c` on `var` (see `membership_conditions`) hold at every point of one of
    `regions` (unions of intervals), for certain? Proved for a set ℝ ∖ D (Γ off its poles 0, -1, -2, ...) with an
    argument linear in `var`: the image of the region misses D. Γ has a value on (-1, 0) ∪ (0, 1), around its pole
    0, and the limit 1 of x Γ(x) at 0, the integral of x Γ(1 + x)/Γ(1 + x) over [0, 1] and the derivative of
    Γ(x + 1)/Γ(x) at 2 were UNKNOWN (review of d4f, RK-F2). A natural-number condition (x!) holds on no interval.
    The convention that the operand of atan2 or arg is not 0 (`domain.Convention` `origin`) holds where its exact
    zeros are not: everywhere for y**2 + x**2 with y = 2, on a neighbourhood of 2 for (x - 1)**2 (round 9 of part
    d4b, RK-5); at a zero it stays undecided."""
    st = c.args[1] if isinstance(c, sp.Contains) else None
    if isinstance(st, Convention) and st.kind in ("origin", "zero_power"):
        return _origin_avoided(c.args[0], var, regions)
    if isinstance(st, Convention) and st.kind == "real_power":
        # x**x: the one value where the base is positive (round 9 attack on part d4b, RK-1)
        return _base_positive(c.args[0][0], var, regions)
    if not (isinstance(st, sp.Complement) and st.args[0] == S.Reals) or not regions:
        return False
    arg, hole = c.args[0], st.args[1]
    try:
        poly = sp.Poly(arg, var)
        if arg.free_symbols != {var} or poly.degree() != 1:
            return False
        a, b = poly.all_coeffs()
        if not (a.is_number and b.is_number and a.is_extended_real and b.is_extended_real and a != 0):
            return False
    except Exception:  # noqa: BLE001 - not linear in var
        return False
    for region in regions:
        try:
            parts = region.args if isinstance(region, sp.Union) else (region,)
            if not all(isinstance(q, sp.Interval) for q in parts):
                continue
            images = []
            for q in parts:
                lo, hi = a * q.start + b, a * q.end + b
                lo_open, hi_open = q.left_open, q.right_open
                if a.is_negative:
                    lo, hi, lo_open, hi_open = hi, lo, hi_open, lo_open
                images.append(Interval(lo, hi, lo_open, hi_open))
            if all(sp.Intersection(img, hole).is_empty is True for img in images):
                return True
        except Exception:  # noqa: BLE001 - a region SymPy cannot cut proves nothing
            continue
    return False


def _origin_avoided(u, var, regions) -> bool:
    """Is the operand `u` (in `var` alone) certainly not 0 on all of ℝ, or on the closure of one of `regions`? Its
    zeros from the exact classes (sandbox.exactsets), a finite set checked point by point; anything else: False."""
    from ..sandbox.exactsets import exact_solveset
    from .domain import in_domain
    if not isinstance(u, sp.Expr) or u.free_symbols != {var}:
        return False
    try:
        zs = exact_solveset(sp.Eq(u, 0), var, S.Reals)
    except Exception:  # noqa: BLE001 - zeros not found exactly prove nothing
        return False
    if zs is S.EmptySet:
        return True
    if not isinstance(zs, sp.FiniteSet):
        return False
    for region in regions:
        try:
            closure = region.closure
        except Exception:  # noqa: BLE001
            continue
        if all(in_domain(closure, z) is False for z in zs):
            return True
    return False


def _base_positive(b, var, regions) -> bool:
    """Is the base `b` (in `var` alone) certainly positive on the closure of one of `regions`: no point of it where
    b <= 0, by the exact classes (sandbox.exactsets)?"""
    from ..sandbox.exactsets import exact_solveset
    if not isinstance(b, sp.Expr) or b.free_symbols != {var}:
        return False
    for region in regions:
        try:
            if exact_solveset(sp.Le(b, 0), var, region.closure) is S.EmptySet:
                return True
        except Exception:  # noqa: BLE001 - a region SymPy cannot cut proves nothing
            continue
    return False


def approach_regions(point, side) -> list:
    """Regions where a condition holding proves it holds near the limit point: punctured neighbourhoods of a finite
    point (on the side approached), tails toward an infinite one."""
    if point == oo:
        return [Interval.open(m, oo) for m in _TAILS]
    if point == -oo:
        return [Interval.open(-oo, -m) for m in _TAILS]
    if not (getattr(point, "is_number", False) and point.is_extended_real is True):
        return []
    out = []
    for d in _DELTAS:
        left, right = Interval.open(point - d, point), Interval.open(point, point + d)
        out.append(right if side == "+" else left if side == "-" else sp.Union(left, right))
    return out


def neighbourhoods(point) -> list:
    """Open neighbourhoods of a finite real point (a derivative's)."""
    if not (getattr(point, "is_number", False) and point.is_extended_real is True and point.is_finite):
        return []
    return [Interval.open(point - d, point + d) for d in _DELTAS]


def holds_on_the_tail(c, var, point) -> bool:
    """Does the membership condition `c` (see `membership_conditions`) hold at every value of the
    sequence `var` from some point on, toward the infinite `point`? A limit there reads only that tail:
    with x a positive integer (x - 2)! has its value from x = 2 on, and lim_{x->oo} (x - 2)!/x^x = 0 was
    UNKNOWN (fourth audit G14). Over the reals a natural-number condition holds on no tail (it fails
    between the integers); a violation set no exact check finds is no proof either. Any condition (x**x != 0,
    cos(πx/2) != 0) is read the same way (review of d4f, YO-4), on the integers of the tail's sign: x**x = 0 is
    no equation solveset takes over all of ℤ."""
    if point not in (oo, -oo) or not getattr(var, "is_integer", None):
        return False
    over = sp.Range(1, oo) if point == oo else sp.Range(-oo, 0)
    try:
        bad = _violations(c, var, over)
        if bad is not None and (bad.is_empty is True or getattr(bad.sup if point == oo else bad.inf, "is_finite",
                                                                 None) is True):
            return True
    except Exception:  # noqa: BLE001 - not decided there (Intersection({log(1000)/log(2)}, Range(1, oo)) has no sup)
        pass
    return _eventually(c, var, point)


def _eventually(c, var, point) -> bool:
    """Does the relation `c` (f != g, f > g, f >= g, ...) hold on a whole real tail toward the infinite `point`?
    So it does when the limit of f - g there is certified on the relation's side of 0 (a nonzero limit, ±oo):
    its violation set is then bounded on that side, and the integers past it are a tail. 2**n = 1000, n! = 100,
    n**2 = 2**n, n = 10*log(n) and floor(n/2) = 0 are no equations solveset takes over the integers, and the
    sequences 1/(2**n - 1000), n**2/(n**2 - 2**n), log(n)/(n - log(n)), 1/floor(n/2) were "undefined on the
    tail" (attack on d4f round 2, RK-2). Read on a plain real variable: a real limit speaks for the integers too;
    (-1)**n or cos(pi*n/2), with no limit, prove nothing."""
    sides = {sp.Ne: (1, -1), sp.StrictGreaterThan: (1,), sp.GreaterThan: (1,), sp.StrictLessThan: (-1,),
             sp.LessThan: (-1,)}.get(type(c))
    if sides is None:
        return False
    x = sp.Dummy(var.name, real=True)
    try:
        h = (c.lhs - c.rhs).xreplace({var: x})
        cls = classify_limit(h, x, point)
        if cls["kind"] == "INF":
            sign = 1 if cls["value"] == oo else -1 if cls["value"] == -oo else None
        elif cls["kind"] == "VAR":
            sign = certified_sign(cls["value"])
        else:
            return False
    except Exception:  # noqa: BLE001 - not decided
        return False
    return sign in sides


def declared_side(var, point, side):
    """The side ('+', '-', None: both) from which the task's limit approaches `point` inside the
    variable's declared domain, or False when the approach leaves it. The task's variable keeps its
    declared assumptions (the parse folds sqrt(x**2) to x for x > 0), so with x declared positive
    lim_{x->-oo} sqrt(x**2)/x was certified to be 1 (it is -1), lim_{x->-1} sqrt(x**2) to be -1 and
    the left limit of x*log(x) at 0 to be 0; with n declared an integer, sin(pi*n)/(n - 1) folded
    to 0 and its limit at n = 1 was certified 0 (it is -pi). At the closed end of the declared domain
    the limit is the one-sided limit from inside it (30 Sep 2026)."""
    nonneg = getattr(var, "is_nonnegative", None)
    if getattr(var, "is_integer", None):
        # a sequence: only an infinite end its values reach
        return side if point == oo or (point == -oo and not nonneg) else False
    if not nonneg or point == oo:
        return side
    if point == -oo:
        return False
    if getattr(point, "is_positive", None):
        return side
    if getattr(point, "is_zero", None) and side in (None, "+"):
        return "+"
    return False


def _near(region, point, d) -> str | None:
    """Does `region` hold a whole one-sided neighbourhood of `point` ("full": (p, p + e) for d = '+',
    (p - e, p) for '-', (M, oo) at oo, (-oo, M) at -oo), none of it ("empty"), or neither / undecided
    (None)? A point the region does not reach on that side is not approached from it."""
    if point == oo:
        win = Interval.open(0, oo) if region.inf is S.NegativeInfinity else Interval.open(region.inf, oo)
    elif point == -oo:
        win = Interval.open(-oo, 0) if region.sup is S.Infinity else Interval.open(-oo, region.sup)
    else:
        win = Interval.open(point, point + 1) if d == "+" else Interval.open(point - 1, point)
    bad = sp.Complement(win, region)
    good = sp.Intersection(win, region)
    if bad.has(sp.Complement, sp.ConditionSet) or good.has(sp.Complement, sp.ConditionSet):
        return None

    def apart(s_) -> bool:
        # every point of s_ stays away from the point on this side
        if s_.is_empty is True:
            return True
        if point == oo:
            return s_.sup.is_finite is True
        if point == -oo:
            return s_.inf.is_finite is True
        try:
            gap = certified_sign(s_.inf - point if d == "+" else point - s_.sup)
        except Exception:  # noqa: BLE001
            return False
        return gap == 1

    if apart(bad):
        return "full"
    if apart(good):
        return "empty"
    return None


UNDECIDED = "undecided"


def defined_nowhere_in(region, conds, var) -> bool:
    """Do the written conditions on `var` alone (`conds`, read at the pinned values) hold at no point of
    `region` together, proved exactly? Then the expression has no value anywhere the variable may be, and
    no limit of it is the curriculum's: with x > 0 a constraint, a given or the domain of discourse the
    limit DNE of x + 0*sqrt(-x) at 0 and of x + 0*log(-x) at 2 was certified, and 0 refuted (attack on
    d4e, YO-6); declared positive, the same expression was undefined as written. A condition whose
    violations are not found exactly proves nothing (False)."""
    good = region
    for c in conds:
        if getattr(c, "free_symbols", set()) != {var}:
            continue
        try:
            bad = _violations(c, var, region)
            if bad is None:
                continue
            good = sp.Intersection(good, sp.Complement(region, bad))
        except Exception:  # noqa: BLE001 - not decided
            continue
    try:
        return good.is_empty is True
    except Exception:  # noqa: BLE001
        return False


def region_side(ctx: Ctx, var, point, side):
    """The side ('+', '-', None: both) from which the limit approaches `point` inside the variable's
    region (`Ctx.domain_for`: its declaration, constraints, givens and domain of discourse, with the
    values the givens fix), False when the point is not approached from inside it, UNDECIDED when that
    is not decided. Only the declaration was read (`declared_side`): with x > 0 as a constraint, a given
    or the domain of discourse, lim_{x->0} |x|/x was certified DNE and 1 refuted, while the declaration
    gave 1; the limit of x at 0 under x > 1 was certified 0 and the limit of x at -oo under x > 0 -oo
    (fourth audit G6). At an end of the region the limit is the one-sided limit from inside it, the
    rule of a declared domain's closed end (30 Sep 2026); an isolated point or a point outside the
    region is not approached."""
    region = ctx.domain_for(var)
    unsolved = ctx.unsolved_conditions(var)
    if unsolved:
        # a periodic condition left unsolved on ℝ (the given cos(x) < 0) is solved on [p - 1, p + 1] around a finite
        # point (`sandbox.exactsets` on a bounded domain); near an infinite one it is not (review of d4e, R5)
        if point in (oo, -oo):
            return UNDECIDED
        from .calculus import _solved_part
        win = Interval(point - 1, point + 1)
        region = sp.Intersection(_solved_part(region), win)
        for c in unsolved:
            r = sb_run("mathverify.sandbox.ops:solveset_in", c, var, win, timeout=ctx.timeout)
            if not (r.ok and isinstance(r.value, sp.Set)) or r.value.has(sp.ConditionSet):
                return UNDECIDED
            region = sp.Intersection(region, r.value)
    if getattr(var, "is_integer", None) and point in (oo, -oo):
        # a sequence (`declared_side` refuses a finite point): only an infinite end its values reach
        try:
            end = region.sup if point == oo else region.inf
        except Exception:  # noqa: BLE001
            return UNDECIDED
        return side if end == point else False if getattr(end, "is_finite", None) is True else UNDECIDED
    sides = ["-"] if point == oo else ["+"] if point == -oo else ["+", "-"]
    try:
        status = {d: _near(region, point, d) for d in sides}
    except Exception:  # noqa: BLE001 - a region SymPy cannot cut decides nothing
        return UNDECIDED
    want = sides if side is None or point in (oo, -oo) else [side]
    if any(status[d] is None for d in want):
        return UNDECIDED
    full = [d for d in want if status[d] == "full"]
    if not full:
        return False
    if point in (oo, -oo) or len(full) == 2:
        return side
    return full[0]


def verify(ir, solution, ctx: Ctx):
    """Task `limit`: params {"expr": str, "var": str, "to": str, "side"?: "+"|"-"}."""
    if ir.task.kind != "limit":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        var = ctx.sym(p.get("var", "x"))
        expr, err = parse_or_unknown(LAYER, ctx.expr, p["expr"])
        if err:
            return err
        point, err = parse_or_unknown(LAYER, ctx.expr, str(p.get("to", "0")))
        if err:
            return err
        # a parameter (a symbol other than the variable) is read at the number a given pins it to;
        # one no given pins leaves the limit without a value (DECISIONS §80): with n an integer
        # SymPy's limit of a*n*sin(pi/n) at oo is 0 (it is a*pi), and 0 was certified and 2*pi refuted
        # with a = 2 (part iv, 1 Oct 2026)
        # A declared constraint `a = 3` pins it too, and so does every value for the written conditions (below):
        # x + 0*sqrt(b - x) is x after parsing, and its limit 0 at 0 was certified with b free and with b = -1,
        # where 0 is no point of its domain (review of d4e; `Ctx.solved_pins`)
        pins = ctx.solved_pins(var)
        expr, err = parse_or_unknown(LAYER, ctx.with_pins, expr, pins)
        if err:
            return err
        point, err = parse_or_unknown(LAYER, ctx.with_pins, point, pins)
        if err:
            return err
        left = (getattr(expr, "free_symbols", set()) | getattr(point, "free_symbols", set())) - {var}
        if left:
            return unknown(LAYER, "parametric_limit", t.ms, {"parameters": sorted(str(s_) for s_ in left)},
                           flags=["parametric_limit"])
        side = p.get("side")
        if side in ("", "+-"):
            side = None
        if side not in (None, "+", "-"):
            # "right", "left", ...: guessing the direction would decide a different question
            return unknown(LAYER, f"unknown_side:{side}")
        within = declared_side(var, point, side)
        if within is False:
            return unknown(LAYER, "approach_outside_declared_domain", t.ms,
                           {"var": str(var), "to": str(point), "side": str(side)},
                           flags=["approach_outside_declared_domain"])
        # the conditions on the variable however they are written: one naming a symbol no given fixes
        # (x > b, b free) leaves the region unknown; a trigonometric one left unsolved leaves it undecided
        # near the point (`region_side`)
        unapplied = ctx.unapplied_conditions(var)
        if unapplied:
            return condition_not_applied(LAYER, unapplied, t.ms)
        within = region_side(ctx, var, point, within)
        if within is False or within == UNDECIDED:
            outside = within is False
            return unknown(LAYER, "approach_outside_declared_domain" if outside else "region_near_point_undecided",
                           t.ms, {"var": str(var), "to": str(point), "side": str(side),
                                  "region": str(ctx.domain_for(var))},
                           flags=["approach_outside_declared_domain"] if outside else [])
        side = within
        # the pinned values go in before the conditions are read: x**a has x > 0 only while a is free (TAN-09)
        written, nowhere = written_definedness(p["expr"], ctx.ns, pins)
        if nowhere or written_undefined_everywhere(p["expr"], ctx.ns):
            # undefined as written for every value (a sum with an undefined term), or a binder whose
            # body is not proved to exist: lim_{x->0} x + Σ_{k=-1}^{1} k/k = 3 was certified (review
            # of 30 Sep 2026; the value parse reads k/k as 1)
            return unknown(LAYER, "expression_undefined_as_written", t.ms, {"expr": p["expr"]},
                           flags=["expression_undefined_as_written"])
        if defined_nowhere_in(ctx.domain_for(var), written, var):
            return unknown(LAYER, "expression_undefined_as_written", t.ms,
                           {"expr": p["expr"], "region": str(ctx.domain_for(var))},
                           flags=["expression_undefined_as_written"])
        unpinned = sorted({str(s_) for c in written for s_ in getattr(c, "free_symbols", set()) - {var}})
        if unpinned:
            return unknown(LAYER, "parametric_limit", t.ms, {"parameters": unpinned}, flags=["parametric_limit"])
        # a limit does not read the point itself: a convention failing at finitely many points of a punctured
        # neighbourhood is passed by a smaller one (`domain.convention_null_on`): 0**0 had left lim_{x->0+} x**x = 1
        # UNKNOWN since d4b round 10 (merge of 15 Oct 2026)
        near = approach_regions(point, side)
        members = [c for c in membership_conditions(p["expr"], expr, var, ctx.ns, pins)
                   if not holds_on_the_tail(c, var, point) and not membership_holds_on(c, var, near)
                   and not any(convention_null_on(c, var, r) for r in near)]
        if members:
            return unknown(LAYER, "membership_condition_on_variable", t.ms,
                           {"conditions": [str(c) for c in members]}, flags=["membership_condition"])
        if point in (oo, -oo) and getattr(var, "is_integer", None):
            # a sequence: its limit reads the tail, so every written condition must hold from some index on.
            # cos(πx/2) in a denominator fails at every odd x, and the limit 1 of cos(πx/2)/cos(πx/2) (and of
            # (x - 2)!/x^x + cos(πx/2)/cos(πx/2)) was certified (review of d4f, YO-4)
            off = [c for c in written if var in getattr(c, "free_symbols", set()) and not isinstance(c, sp.Contains)
                   and not holds_on_the_tail(c, var, point)]
            if off:
                return unknown(LAYER, "sequence_undefined_on_the_tail", t.ms, {"conditions": [str(c) for c in off]},
                               flags=["sequence_undefined_on_the_tail"])
        extra = [c for c in written if getattr(c, "free_symbols", set()) == {var}]
        cls = classify_limit(expr, var, point, side, timeout=ctx.timeout,
                             conds=limit_conditions(expr, var, extra))
        ev: dict[str, Any] = {"classification": {k: str(v) for k, v in cls.items()}}
        ca = solution.claimed_answer
        if cls["kind"] == "UNKNOWN":
            return unknown(LAYER, "limit_undecided", t.ms, ev, flags=cls.get("flags", []))
        if ca.kind == "dne":
            ok = cls["kind"] == "DNE"
            ev["claimed"] = "DNE"
        else:
            # parse first, THEN recognise an infinite claim: "\infty", "+\infty" and "S.Infinity"
            # with kind "value" were read as finite values and refuted (audit of 25 Sep 2026)
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.with_pins, claimed, pins)
            if err:
                return err
            ev["claimed"] = str(claimed)
            if claimed in (oo, -oo):
                ok = cls["kind"] == "INF" and cls["value"] == claimed
            elif cls["kind"] != "VAR":
                ok = False
            else:
                # (each finite one-sided value was corroborated numerically in classify_limit)
                ok, cev = answers_equivalent(claimed, cls["value"], shape="scalar")
                ev["compare"] = cev
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "undecided", t.ms, ev)
