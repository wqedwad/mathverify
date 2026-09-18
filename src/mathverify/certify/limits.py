"""Limits (E6): both one-sided limits, AccumBounds/zoo classification, numeric probe."""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp
from sympy import oo, zoo, nan, AccumBounds

from ..equiv import answers_equivalent
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.limits"


def _kind_of(v) -> str:
    if v is None:
        return "UNKNOWN"
    if isinstance(v, AccumBounds):
        return "DNE"
    if v in (oo, -oo):
        return "INF"
    if v is zoo or v is nan:
        return "DNE"
    if getattr(v, "is_number", False) or not v.free_symbols:
        return "VAR"
    return "UNKNOWN"


def classify_limit(expr, var, point, side: str | None = None, timeout: float = 8.0) -> dict[str, Any]:
    """Return {"kind": VAR|INF|DNE|UNKNOWN, "value", "left", "right", ...}."""
    out: dict[str, Any] = {"kind": "UNKNOWN", "value": None, "left": None, "right": None, "point": str(point)}
    if point in (oo, -oo) or side in ("+", "-"):
        d = side or ("-" if point == oo else "+")
        r = sb_run("mathverify.sandbox.ops:limit_default", expr, var, point, timeout=timeout) \
            if point in (oo, -oo) else \
            sb_run("mathverify.certify.limits:_limit_dir", expr, var, point, d, timeout=timeout)
        if not r.ok:
            out["error"] = r.error
            out["flags"] = r.flags
            return out
        v = r.value
        out["value"] = v
        out["kind"] = _kind_of(v)
        if out["kind"] == "INF":
            out["value"] = v
        return out
    r = sb_run("mathverify.sandbox.ops:limit_two_sided", expr, var, point, timeout=timeout)
    if not r.ok:
        out["error"] = r.error
        out["flags"] = r.flags
        return out
    plus, minus = r.value
    out["right"], out["left"] = plus, minus
    kp, km = _kind_of(plus), _kind_of(minus)
    if kp == "DNE" or km == "DNE" or kp == "UNKNOWN" or km == "UNKNOWN":
        out["kind"] = "DNE" if "UNKNOWN" not in (kp, km) else "UNKNOWN"
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


def _limit_dir(expr, var, point, d):
    return sp.limit(expr, var, point, d)


def numeric_probe(expr, var, point, side: str, dps: int = 50) -> list[str | None]:
    """f(point ± h) for shrinking h (or growing x for ±oo). Evidence only."""
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
        cls = classify_limit(expr, var, point, side, timeout=ctx.timeout)
        ev: dict[str, Any] = {"classification": {k: str(v) for k, v in cls.items()}}
        ca = solution.claimed_answer
        if cls["kind"] == "UNKNOWN":
            return unknown(LAYER, "limit_undecided", t.ms if hasattr(t, "ms") else 0, ev,
                           flags=cls.get("flags", []))
        # numeric corroboration
        probes = {}
        for s_ in (["+", "-"] if side is None and point not in (oo, -oo) else [side or "+"]):
            probes[s_] = numeric_probe(expr, var, point, s_)
        ev["numeric_probe"] = probes
        if ca.kind == "dne":
            ok = cls["kind"] == "DNE"
            ev["claimed"] = "DNE"
        elif ca.kind == "infinite" or (ca.kind == "value" and str(ca.payload).strip() in ("oo", "-oo", "inf", "-inf", "+oo", "∞", "-∞", "+∞")):
            claimed, err = parse_or_unknown(LAYER, ctx.expr, str(ca.payload or "oo"))
            if err:
                return err
            ev["claimed"] = str(claimed)
            ok = cls["kind"] == "INF" and cls["value"] == claimed
            if cls["kind"] == "VAR":
                ok = False
        else:
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            ev["claimed"] = str(claimed)
            if cls["kind"] != "VAR":
                ok = False
            else:
                ok, cev = answers_equivalent(claimed, cls["value"], shape="scalar")
                ev["compare"] = cev
                if ok is True:
                    agree = [_probe_agrees(v, cls["value"]) for v in probes.values()]
                    ev["probe_agrees"] = agree
                    if any(a is False for a in agree):
                        return unknown(LAYER, "symbolic_numeric_disagreement", t.ms if hasattr(t, "ms") else 0,
                                       ev, flags=["symbolic_numeric_disagreement"])
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "undecided", t.ms, ev)
