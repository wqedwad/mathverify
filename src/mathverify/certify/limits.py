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
from sympy.functions.elementary.trigonometric import TrigonometricFunction

from ..equiv import answers_equivalent
from ..equiv.numeric import to_mp
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown
from .domain import definedness_conditions, written_definedness

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
    if any(c.has(TrigonometricFunction, HyperbolicFunction) for c in conds):
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


def _oscillation(expr, var, point, side) -> list[float] | None:
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
            out.append(float((hi - lo) / max(1, abs(hi), abs(lo))))
    return out


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
    ev["oscillation_spread"] = ro.value if ro.ok else None
    if ro.ok and ro.value and all(s_ >= 1e-3 for s_ in ro.value):
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
        side = p.get("side")
        if side in ("", "+-"):
            side = None
        if side not in (None, "+", "-"):
            # "right", "left", ...: guessing the direction would decide a different question
            return unknown(LAYER, f"unknown_side:{side}")
        extra = [c for c in written_definedness(p["expr"], ctx.ns)[0]
                 if getattr(c, "free_symbols", set()) == {var}]
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
