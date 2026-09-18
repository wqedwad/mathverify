"""Two-sided extremum certificates (E5): attained AND nothing better exists."""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S, Interval, FiniteSet, ConditionSet, oo

from ..equiv import answers_equivalent
from ..equiv.numeric import to_mp
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.extremum"


def _num(v):
    try:
        r = to_mp(v, 40)
        return None if isinstance(r, mp.mpc) else r
    except Exception:
        return None


def certify_extremum(f, var, interval: Interval, which: str, claimed, timeout: float = 8.0
                     ) -> tuple[bool | None, dict[str, Any]]:
    """which: max | min | argmax | argmin. Returns (True|False|None, evidence)."""
    ev: dict[str, Any] = {"which": which, "interval": str(interval), "claimed": str(claimed)}
    f = sp.sympify(f)
    is_max = which in ("max", "argmax")
    r = sb_run("mathverify.sandbox.ops:critical_points", f, var, interval, timeout=timeout)
    if not r.ok:
        ev["error"] = r.error
        return None, ev
    cands = list(r.value)
    if not interval.left_open and interval.inf != -oo:
        cands.append(interval.inf)
    if not interval.right_open and interval.sup != oo:
        cands.append(interval.sup)
    cands = list(dict.fromkeys(cands))
    if not cands:
        ev["reason"] = "no_candidates"
        return None, ev
    vals = []
    for c in cands:
        fc = sp.simplify(f.subs(var, c))
        vals.append((c, fc, _num(fc)))
    vals = [v for v in vals if v[2] is not None]
    if not vals:
        ev["reason"] = "candidates_not_real"
        return None, ev
    ev["candidates"] = [(str(c), str(fc)) for c, fc, _ in vals]
    best_num = max(v[2] for v in vals) if is_max else min(v[2] for v in vals)
    best = [v for v in vals if abs(v[2] - best_num) <= mp.mpf("1e-25") * max(1, abs(best_num))]
    best_val = best[0][1]
    ev["best_value"] = str(best_val)
    ev["attained_at"] = [c for c, _, _ in best]

    # open endpoints: the extremum may only be approached, never attained
    for end, is_open in ((interval.inf, interval.left_open), (interval.sup, interval.right_open)):
        if is_open:
            rl = sb_run("mathverify.sandbox.ops:limit_default", f, var, end, timeout=timeout) if end in (oo, -oo) \
                else sb_run("mathverify.certify.limits:_limit_dir", f, var, end, "+" if end == interval.inf else "-", timeout=timeout)
            if rl.ok:
                lv = rl.value
                ln = _num(lv) if not (lv in (oo, -oo)) else (mp.inf if lv == oo else -mp.inf)
                ev.setdefault("open_end_limits", []).append((str(end), str(lv)))
                if ln is not None and ((is_max and ln > best_num) or ((not is_max) and ln < best_num)):
                    ev["reason"] = "extremum_not_attained_open_endpoint"
                    return False, ev

    # second side: nothing better exists on the interval
    strict_rel = (f > best_val) if is_max else (f < best_val)
    rs = sb_run("mathverify.sandbox.ops:solveset_in", strict_rel, var, interval, timeout=timeout)
    proven = False
    if rs.ok and not isinstance(rs.value, ConditionSet):
        ev["superlevel_set"] = str(rs.value)
        if rs.value == S.EmptySet:
            proven = True
        else:
            ev["superlevel_empty"] = False
            ev["reason"] = "better_value_exists_symbolic"
            return False, ev
    if not proven:
        # EVT route: continuous on a closed bounded interval + complete critical set
        rc = sb_run("mathverify.sandbox.ops:continuous_domain", f, var, interval, timeout=timeout)
        rd = sb_run("mathverify.sandbox.ops:solveset_in", sp.diff(f, var), var, interval, timeout=timeout)
        closed = (not interval.left_open and not interval.right_open and interval.inf != -oo and interval.sup != oo)
        if rc.ok and rc.value == interval and closed and rd.ok and isinstance(rd.value, FiniteSet):
            proven = True
            ev["proof"] = "EVT+complete_critical_set"
        else:
            # numeric scan as evidence (never a proof)
            fn = sp.lambdify(var, f, "mpmath")
            lo = float(interval.inf) if interval.inf != -oo else -1e3
            hi = float(interval.sup) if interval.sup != oo else 1e3
            worse_found = False
            with mp.workdps(30):
                for k in range(1, 2000):
                    xk = mp.mpf(lo) + (mp.mpf(hi) - mp.mpf(lo)) * k / 2000
                    try:
                        v = fn(xk)
                    except Exception:
                        continue
                    if isinstance(v, mp.mpc):
                        continue
                    if (is_max and v > best_num + mp.mpf("1e-12")) or ((not is_max) and v < best_num - mp.mpf("1e-12")):
                        worse_found = True
                        ev["numeric_better_point"] = (mp.nstr(xk, 12), mp.nstr(v, 12))
                        break
            if worse_found:
                ev["reason"] = "better_value_found_numerically"
                return False, ev
    ev["superlevel_empty"] = proven

    if which in ("max", "min"):
        ok, cev = answers_equivalent(claimed, best_val, shape="scalar")
        ev["compare"] = cev
        if ok is True:
            return (True if proven else None), ev
        if ok is False:
            cn = _num(claimed)
            if cn is not None:
                if (is_max and cn > best_num) or ((not is_max) and cn < best_num):
                    ev["reason"] = "not_attained"
                else:
                    ev["reason"] = "better_value_exists"
            return False, ev
        return None, ev
    # argmax / argmin
    ok_in = interval.contains(claimed)
    if ok_in is sp.false:
        ev["reason"] = "argument_outside_interval"
        return False, ev
    fcl = sp.simplify(f.subs(var, claimed))
    ok, cev = answers_equivalent(fcl, best_val, shape="scalar")
    ev["compare"] = cev
    if ok is False:
        ev["reason"] = "argument_does_not_attain_extremum"
        return False, ev
    if ok is None:
        return None, ev
    if len(best) > 1:
        ev["reason"] = "multiple_extremizers"
        return None, ev
    return (True if proven else None), ev


def certify_local_extremum(f, var, domain: sp.Set, which: str, claimed, timeout: float = 8.0
                           ) -> tuple[bool | None, dict[str, Any]]:
    """which: local_max | local_min | local_argmax | local_argmin.

    Certificate: critical points of f (f' = 0 as a complete FiniteSet, plus points where
    f' is undefined) classified by the sign change of f' (first-derivative test with
    exact one-sided evaluation). The claim must match the (unique) local extremum of the
    requested type; several distinct values => ill-posed question => None."""
    ev: dict[str, Any] = {"which": which, "claimed": str(claimed), "domain": str(domain)}
    f = sp.sympify(f)
    is_max = which in ("local_max", "local_argmax")
    df = sp.diff(f, var)
    rd = sb_run("mathverify.sandbox.ops:solveset_in", df, var, domain if isinstance(domain, Interval) else S.Reals,
                timeout=timeout)
    if not rd.ok or not isinstance(rd.value, FiniteSet):
        ev["reason"] = "critical_points_not_finite"
        return None, ev
    cps = [c for c in rd.value if c.is_real]
    rs = sb_run("mathverify.sandbox.ops:critical_points", f, var, domain if isinstance(domain, Interval) else Interval(-oo, oo),
                timeout=timeout)
    if rs.ok:
        for c in rs.value:
            if c.is_number and c not in cps and c.is_real:
                cps.append(c)
    cps = sorted(cps, key=lambda c: float(c))
    ev["critical_points"] = [str(c) for c in cps]
    extrema = []           # (point, value) of the requested type
    for i, c in enumerate(cps):
        left = (cps[i - 1] + c) / 2 if i > 0 else c - 1
        right = (c + cps[i + 1]) / 2 if i + 1 < len(cps) else c + 1
        try:
            sl = sp.sign(sp.N(df.subs(var, left), 30))
            sr = sp.sign(sp.N(df.subs(var, right), 30))
        except Exception:
            continue
        if is_max and sl > 0 and sr < 0:
            extrema.append((c, sp.simplify(f.subs(var, c))))
        if (not is_max) and sl < 0 and sr > 0:
            extrema.append((c, sp.simplify(f.subs(var, c))))
    ev["local_extrema"] = [(str(c), str(v)) for c, v in extrema]
    if not extrema:
        ev["reason"] = "no_local_extremum_of_requested_type"
        return False, ev
    if which in ("local_max", "local_min"):
        vals = []
        for _, v in extrema:
            if not any(scalar_equal(v, u) is True for u in vals):
                vals.append(v)
        if len(vals) > 1:
            ev["reason"] = "several_distinct_local_extremum_values"
            return None, ev
        ok, cev = answers_equivalent(claimed, vals[0], shape="scalar")
        ev["compare"] = cev
        return ok, ev
    pts = [c for c, _ in extrema]
    if len(pts) > 1:
        ev["reason"] = "several_local_extremizers"
        return None, ev
    ok, cev = answers_equivalent(claimed, pts[0], shape="scalar")
    ev["compare"] = cev
    return ok, ev


def verify(ir, solution, ctx: Ctx):
    """Task `extremum`: params {"f": str, "var": str, "interval": str,
    "which": max|min|argmax|argmin|local_max|local_min|local_argmax|local_argmin}."""
    if ir.task.kind != "extremum":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        var = ctx.sym(p.get("var", "x"))
        f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
        if err:
            return err
        from ..normalize.parse import parse_set_str
        iv = parse_set_str(p.get("interval", "Reals"), ctx.ns) if p.get("interval") else ctx.domain_for(var)
        claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
        if err:
            return err
        which = p.get("which", "max")
        if which.startswith("local_"):
            ok, ev = certify_local_extremum(f, var, iv, which, claimed, timeout=ctx.timeout)
        else:
            if not isinstance(iv, Interval):
                return unknown(LAYER, "interval_required", 0)
            ok, ev = certify_extremum(f, var, iv, which, claimed, timeout=ctx.timeout)
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", "undecided"), t.ms, ev)
