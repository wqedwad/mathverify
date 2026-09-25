"""Two-sided extremum certificates (E5): attained AND nothing better exists.

Audit of 25 Sep 2026 (each item was measured as a false verdict before the change):
  * kinks where f' is nonzero on both sides (|x - 1| plus a slope) were never candidates, and the
    closed-interval route still called the candidate set complete: the maximum of
    e^x/100 - |x-1| on [0, 5] was certified as the endpoint value -99/100 (it is e/100 at x = 1);
  * "a better value exists" was measured against the best CANDIDATE, not against the claim, so an
    incomplete candidate set refuted true maxima (max of e^(-x²)cos(50x) on [-1, 1] is 1);
  * argmax/argmin must be unique: argmin of floor(x) on [1/2, 3] was certified as 1/2;
  * an unknown `which` fell into the argmin branch;
  * the numeric scan ran in the main process without a timeout.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S, Interval, FiniteSet, ConditionSet, oo

from ..equiv import answers_equivalent
from ..equiv.numeric import num_equal, to_mp
from ..equiv.sets import scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.extremum"

WHICH = ("max", "min", "argmax", "argmin", "local_max", "local_min", "local_argmax", "local_argmin")
# nodes whose non-differentiable points are enumerated below; anything else non-smooth makes the
# candidate set incomplete
_KINKED = (sp.Abs, sp.sign, sp.Heaviside, sp.Max, sp.Min)
_UNENUMERATED = (sp.floor, sp.ceiling, sp.frac, sp.Piecewise, sp.Mod, sp.re, sp.im, sp.arg,
                 sp.DiracDelta)


def _num(v):
    try:
        r = to_mp(v, 40)
        return None if isinstance(r, mp.mpc) else r
    except Exception:
        return None


def _better(a, b, is_max: bool) -> bool:
    return a > b if is_max else a < b


def _strictly_better(fa, na, fb, nb, is_max: bool) -> bool:
    """fa beats fb for certain: exact inequality (strict ladder) AND the right direction."""
    if na is None or nb is None or not _better(na, nb, is_max):
        return False
    try:
        eq, _ = num_equal(fa, fb)
    except Exception:  # noqa: BLE001
        return False
    return eq is False


def _classical(e):
    from .calculus import classical
    return classical(e)


def _kinks(f, var, region, timeout) -> tuple[list, bool]:
    """Points of `region` where f may not be differentiable although f' is not singular there:
    zeros of Abs/sign/Heaviside arguments and switching points of Max/Min. The bool says whether
    that list is complete (False when f has floor, Piecewise, ... or a zero set is not finite)."""
    if f.has(*_UNENUMERATED):
        return [], False
    pts: list = []
    complete = True
    for node in sp.preorder_traversal(f):
        if isinstance(node, (sp.Abs, sp.sign, sp.Heaviside)):
            eqs = [node.args[0]]
        elif isinstance(node, (sp.Max, sp.Min)):
            eqs = [a - b for a, b in combinations(node.args, 2)]
        else:
            continue
        for u in eqs:
            if not u.has(var):
                continue
            r = sb_run("mathverify.sandbox.ops:solveset_in", sp.Eq(u, 0), var, region, timeout=timeout)
            if r.ok and (r.value is S.EmptySet or isinstance(r.value, FiniteSet)):
                pts += [p for p in r.value if p.is_number and p.is_real]
            else:
                complete = False
    return list(dict.fromkeys(pts)), complete


def _scan_better(f, var, lo, hi, cval, is_max, n=2000):
    """Worker: a grid point of [lo, hi] where f is better than cval by > 1e-12 (evidence; the
    caller re-evaluates the point exactly before using it)."""
    fn = sp.lambdify(var, f, "mpmath")
    with mp.workdps(30):
        c = mp.mpf(str(cval))
        lo_, hi_ = mp.mpf(str(lo)), mp.mpf(str(hi))
        for k in range(1, n):
            xk = lo_ + (hi_ - lo_) * k / n
            try:
                v = fn(xk)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(v, mp.mpc):
                continue
            if (is_max and v > c + mp.mpf("1e-12")) or ((not is_max) and v < c - mp.mpf("1e-12")):
                return sp.Rational(mp.nstr(xk, 20))
    return None


def certify_extremum(f, var, interval: Interval, which: str, claimed, timeout: float = 8.0
                     ) -> tuple[bool | None, dict[str, Any]]:
    """which: max | min | argmax | argmin. Returns (True|False|None, evidence).

    False only with a witness against the CLAIM (a point with a better value, an open end whose
    limit is better, or an upper bound that is never attained). True needs: nothing better than
    the claim ({f better than c} is empty, or f is continuous on a closed bounded interval and the
    candidate set is complete), attainment, and — for argmax/argmin — uniqueness."""
    ev: dict[str, Any] = {"which": which, "interval": str(interval), "claimed": str(claimed)}
    f = sp.sympify(f)
    is_max = which in ("max", "argmax")
    r = sb_run("mathverify.sandbox.ops:critical_points", f, var, interval, timeout=timeout)
    cands = list(r.value) if r.ok else []
    rd = sb_run("mathverify.sandbox.ops:solveset_in", _classical(sp.diff(f, var)), var, interval, timeout=timeout)
    kinks, kinks_complete = _kinks(f, var, interval, timeout)
    cands += kinks
    closed = (not interval.left_open and not interval.right_open and interval.inf != -oo and interval.sup != oo)
    if not interval.left_open and interval.inf != -oo:
        cands.append(interval.inf)
    if not interval.right_open and interval.sup != oo:
        cands.append(interval.sup)
    cands = list(dict.fromkeys(cands))
    rc = sb_run("mathverify.sandbox.ops:continuous_domain", f, var, interval, timeout=timeout)
    complete = bool(r.ok and rd.ok and (rd.value is S.EmptySet or isinstance(rd.value, FiniteSet))
                    and kinks_complete and rc.ok and rc.value == interval)
    ev["complete_candidates"] = complete
    vals = []
    for c in cands:
        fc = sp.simplify(f.subs(var, c))
        vals.append((c, fc, _num(fc)))
    vals = [v for v in vals if v[2] is not None]
    ev["candidates"] = [(str(c), str(fc)) for c, fc, _ in vals]

    # the value the claim stands for
    if which in ("max", "min"):
        cval = sp.sympify(claimed)
        xs = None
    else:
        xs = sp.sympify(claimed)
        inside = interval.contains(xs)
        if inside is sp.false:
            ev["reason"] = "argument_outside_interval"
            return False, ev
        if inside is not sp.true:
            ev["reason"] = "argument_membership_undecided"
            return None, ev
        cval = sp.simplify(f.subs(var, xs))
    cn = _num(cval)
    if cn is None:
        ev["reason"] = "claimed_value_not_real"
        return (False if getattr(cval, "is_number", False) and cval.is_real is False else None), ev
    wrong = "better_value_exists" if which in ("max", "min") else "argument_does_not_attain_extremum"

    # 1. a candidate point beats the claim
    for c, fc, fn_ in vals:
        if _strictly_better(fc, fn_, cval, cn, is_max):
            ev["reason"] = wrong
            ev["witness"] = (str(c), str(fc))
            return False, ev
    # 2. an open end whose limit beats the claim: points near it do too
    for end, is_open in ((interval.inf, interval.left_open), (interval.sup, interval.right_open)):
        if not is_open:
            continue
        rl = sb_run("mathverify.sandbox.ops:limit_default", f, var, end, timeout=timeout) if end in (oo, -oo) \
            else sb_run("mathverify.certify.limits:_limit_dir", f, var, end, "+" if end == interval.inf else "-",
                        timeout=timeout)
        if not rl.ok:
            continue
        lv = rl.value
        ev.setdefault("open_end_limits", []).append((str(end), str(lv)))
        if lv in (oo, -oo):
            if (lv == oo) == is_max:
                ev["reason"] = "better_value_near_open_endpoint"
                return False, ev
            continue
        ln = _num(lv)
        if ln is not None and _strictly_better(lv, ln, cval, cn, is_max):
            ev["reason"] = "better_value_near_open_endpoint"
            return False, ev
    # 3. nothing beats the claim
    strict_rel = (f > cval) if is_max else (f < cval)
    rs = sb_run("mathverify.sandbox.ops:solveset_in", strict_rel, var, interval, timeout=timeout)
    bound = None
    if rs.ok and not rs.value.has(ConditionSet):
        ev["superlevel_set"] = str(rs.value)
        if rs.value is S.EmptySet:
            bound = True
        else:
            from .calculus import _points_of
            for p_ in _points_of(rs.value):
                fp = sp.simplify(f.subs(var, p_))
                if _strictly_better(fp, _num(fp), cval, cn, is_max):
                    ev["reason"] = "better_value_exists_symbolic"
                    ev["witness"] = (str(p_), str(fp))
                    return False, ev
    if bound is None and complete and closed:
        # EVT: f continuous on [a, b] attains its extremum at a candidate, none of which beats c
        bound = True
        ev["proof"] = "EVT+complete_critical_set"
    if bound is None and interval.inf.is_number and interval.sup.is_number:
        lo = interval.inf if interval.inf != -oo else -1000
        hi = interval.sup if interval.sup != oo else 1000
        rn = sb_run("mathverify.certify.extremum:_scan_better", f, var, sp.N(lo, 30), sp.N(hi, 30), sp.N(cval, 30),
                    is_max, timeout=timeout)
        if rn.ok and rn.value is not None and interval.contains(rn.value) is sp.true:
            fp = sp.simplify(f.subs(var, rn.value))
            if _strictly_better(fp, _num(fp), cval, cn, is_max):
                ev["reason"] = "better_value_found_numerically"
                ev["numeric_better_point"] = (str(rn.value), str(sp.N(fp, 12)))
                return False, ev
    ev["superlevel_empty"] = bound is True
    if bound is not True:
        ev["reason"] = "upper_bound_unproven" if is_max else "lower_bound_unproven"
        return None, ev

    # 4. attained (and, for argmax/argmin, uniquely)
    eqs = [(c, scalar_equal(fc, cval)) for c, fc, _ in vals]
    hits = [c for c, e in eqs if e is True]
    ev["attained_at"] = hits
    if which in ("max", "min"):
        if hits:
            return True, ev
        if complete and closed and all(e is False for _, e in eqs):
            ev["reason"] = "not_attained"      # the extremum is attained at a candidate, none equals c
            return False, ev
        ra = sb_run("mathverify.sandbox.ops:solveset_in", sp.Eq(f, cval), var, interval, timeout=timeout)
        if ra.ok and ra.value is S.EmptySet:
            ev["reason"] = "not_attained"
            return False, ev
        if ra.ok and isinstance(ra.value, FiniteSet):
            for p_ in ra.value:
                if p_.is_number and scalar_equal(sp.simplify(f.subs(var, p_)), cval) is True:
                    ev["attained_at"] = [p_]
                    return True, ev
        ev["reason"] = "attainment_undecided"
        return None, ev
    # argmax / argmin: every point where f is at least as good as c must be xs itself
    weak_rel = (f >= cval) if is_max else (f <= cval)
    rw = sb_run("mathverify.sandbox.ops:solveset_in", weak_rel, var, interval, timeout=timeout)
    if rw.ok and isinstance(rw.value, FiniteSet) and len(rw.value) == 1 \
            and scalar_equal(list(rw.value)[0], xs) is True:
        ev["unique"] = "solveset"
        return True, ev
    if rw.ok and not rw.value.has(ConditionSet) and rw.value != FiniteSet(xs):
        ev["reason"] = "multiple_extremizers"
        ev["extremizers"] = str(rw.value)
        return None, ev
    if complete and closed and len(hits) == 1 and scalar_equal(hits[0], xs) is True:
        ev["unique"] = "EVT+complete_critical_set"
        return True, ev
    ev["reason"] = "multiple_extremizers" if len(hits) > 1 else "uniqueness_undecided"
    return None, ev


def certify_local_extremum(f, var, domain: sp.Set, which: str, claimed, timeout: float = 8.0
                           ) -> tuple[bool | None, dict[str, Any]]:
    """which: local_max | local_min | local_argmax | local_argmin.

    Certificate: critical points of f (f' = 0 as a complete FiniteSet, points where f' is
    undefined, and the kinks of Abs/Max/Min/sign) classified by the sign change of f' between
    consecutive points (first-derivative test). The claim must match the (unique) local extremum
    of the requested type; several distinct values => ill-posed question => None. Without the
    kinks, x² - 4|x - 1| had its local minimum at 2 and its local maximum at 1 misread (measured)."""
    ev: dict[str, Any] = {"which": which, "claimed": str(claimed), "domain": str(domain)}
    f = sp.sympify(f)
    is_max = which in ("local_max", "local_argmax")
    region = domain if isinstance(domain, Interval) else None
    if region is None:
        ev["reason"] = "domain_not_an_interval"
        return None, ev
    df = _classical(sp.diff(f, var))
    rd = sb_run("mathverify.sandbox.ops:solveset_in", df, var, region, timeout=timeout)
    if not rd.ok or not (rd.value is S.EmptySet or isinstance(rd.value, FiniteSet)):
        ev["reason"] = "critical_points_not_finite"
        return None, ev
    kinks, kc = _kinks(f, var, region, timeout)
    if not kc:
        ev["reason"] = "non_differentiable_points_not_enumerated"
        return None, ev
    cps = [c for c in rd.value if c.is_real] + kinks
    rs = sb_run("mathverify.sandbox.ops:critical_points", f, var, region, timeout=timeout)
    if not rs.ok:
        ev["reason"] = "critical_points_failed"
        return None, ev
    for c in rs.value:
        if c.is_number and c.is_real:
            cps.append(c)
    cps = sorted(dict.fromkeys(cps), key=lambda c: float(c))
    ev["critical_points"] = [str(c) for c in cps]
    lo = region.inf if region.inf != -oo else None
    hi = region.sup if region.sup != oo else None
    extrema = []           # (point, value) of the requested type
    for i, c in enumerate(cps):
        left = (cps[i - 1] + c) / 2 if i > 0 else (c - 1 if lo is None else (lo + c) / 2)
        right = (c + cps[i + 1]) / 2 if i + 1 < len(cps) else (c + 1 if hi is None else (c + hi) / 2)
        if (lo is not None and c == lo) or (hi is not None and c == hi):
            continue                            # an end of the region is not an interior extremum
        try:
            sl = sp.sign(sp.N(df.subs(var, left), 30))
            sr = sp.sign(sp.N(df.subs(var, right), 30))
        except Exception:  # noqa: BLE001
            sl = sr = None
        if sl not in (-1, 0, 1) or sr not in (-1, 0, 1) or sl == 0 or sr == 0:
            ev["reason"] = "classification_undecided"
            return None, ev
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
        which = p.get("which", "max")
        if which not in WHICH:
            # "maximum" used to fall through to the argmin branch (audit of 25 Sep 2026)
            return unknown(LAYER, f"unknown_which:{which}")
        var = ctx.sym(p.get("var", "x"))
        f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
        if err:
            return err
        from ..normalize.parse import parse_set_str
        iv = parse_set_str(p.get("interval", "Reals"), ctx.ns) if p.get("interval") else ctx.domain_for(var)
        claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
        if err:
            return err
        if isinstance(claimed, sp.Set) or not getattr(claimed, "is_number", False):
            return unknown(LAYER, "claim_is_not_a_number", t.ms)
        # f as written must be defined on the whole interval: x/x − x² parses to 1 − x², whose
        # maximum 1 sits exactly at the point x/x excludes (measured: certified CORRECT)
        from .domain import written_undefined_in
        if isinstance(iv, sp.Set) and written_undefined_in(p["f"], ctx.ns, var, iv) is True:
            return unknown(LAYER, "f_undefined_on_interval_as_written", t.ms, {"f": p["f"]},
                           flags=["written_domain"])
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
