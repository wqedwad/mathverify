"""Trigonometric equations (E1): never compare infinite solution sets directly.

Both the true solution set and the candidate are periodic; we pick a common window
W = lcm(period of the equation, steps of the candidate progressions), enumerate both
sets on [0, W) as FINITE sets and compare those.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Interval, FiniteSet, Union, ImageSet, ConditionSet, Lambda, oo

from ..equiv.sets import set_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.trig"


def detect_period(expr, var, timeout: float = 8.0):
    r = sb_run("mathverify.certify.trig:_periodicity", expr, var, timeout=timeout)
    if r.ok and r.value is not None:
        return r.value
    return None


def _periodicity(expr, var):
    from sympy.calculus.util import periodicity
    return periodicity(expr, var)


def _progressions(cand) -> list[tuple[Any, Any]] | None:
    """Decompose a candidate set into arithmetic progressions [(c, a)] meaning {c + a*n}."""
    if isinstance(cand, ImageSet):
        lam = cand.lamda
        if len(lam.variables) != 1 or cand.base_set != S.Integers:
            return None
        n = lam.variables[0]
        e = sp.expand(lam.expr)
        a = e.coeff(n, 1)
        c = e.subs(n, 0)
        if sp.expand(e - (a * n + c)) != 0:
            return None
        return [(c, a)]
    if isinstance(cand, Union):
        out = []
        for part in cand.args:
            p = _progressions(part)
            if p is None:
                return None
            out += p
        return out
    if isinstance(cand, FiniteSet):
        return [(e, 0) for e in cand.args]
    return None


def _rational_multiple(a, P):
    q = sp.nsimplify(sp.simplify(a / P), rational=True)
    return q if isinstance(q, sp.Rational) else None


def _enumerate_on_window(progs, W) -> FiniteSet | None:
    elems = []
    for c, a in progs:
        if a == 0:
            elems.append(c)
            continue
        # n range such that 0 <= c + a n < W
        lo = sp.ceiling(-c / a) if a > 0 else sp.ceiling((W - c) / a)
        hi = sp.floor((W - c) / a) if a > 0 else sp.floor(-c / a)
        try:
            lo_i, hi_i = int(lo), int(hi)
        except TypeError:
            return None
        if hi_i - lo_i > 10000:
            return None
        for k in range(lo_i, hi_i + 1):
            v = sp.simplify(c + a * k)
            if v == W or (v.is_number and (v < 0 or v >= W)):
                continue
            elems.append(sp.nsimplify(v))
    return FiniteSet(*elems)


def periodic_solution_set_equal(rel, var, candidate, window=None, timeout: float = 8.0
                                ) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"candidate": str(candidate)}
    expr = rel.lhs - rel.rhs if isinstance(rel, sp.Equality) else rel
    if window is not None:
        r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, window, timeout=timeout)
        if not r.ok or isinstance(r.value, ConditionSet):
            ev["error"] = "solveset_failed_on_window"
            return None, ev
        truth = r.value
        ev["true_window"] = [str(e) for e in truth]
        if not isinstance(candidate, FiniteSet):
            progs = _progressions(candidate)
            if progs is None:
                return None, ev
            candidate = _enumerate_window_of_interval(progs, window)
            if candidate is None:
                return None, ev
        ev["candidate_window"] = [str(e) for e in candidate]
        ok, sev = set_equal(candidate, truth)
        ev["compare"] = sev
        return ok, ev

    P = detect_period(expr, var, timeout)
    ev["period"] = P
    if P is None:
        # not periodic: compare solution sets on the reals if finite
        r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, S.Reals, timeout=timeout)
        if r.ok and isinstance(r.value, FiniteSet) and isinstance(candidate, FiniteSet):
            ok, sev = set_equal(candidate, r.value)
            ev["compare"] = sev
            return ok, ev
        return None, ev
    progs = _progressions(candidate)
    if progs is None:
        ev["error"] = "candidate_not_decomposable"
        return None, ev
    # common window
    L = sp.Integer(1)
    for c, a in progs:
        if a == 0:
            ev["error"] = "finite_candidate_for_periodic_equation"
            return False, ev
        q = _rational_multiple(a, P)
        if q is None:
            ev["error"] = f"step {a} is not a rational multiple of period {P}"
            return None, ev
        # lcm of rationals: lcm(num)/gcd(den)
        L = sp.Rational(sp.ilcm(L.p, abs(q.p)), sp.igcd(L.q, q.q))
    W = sp.simplify(L * P)
    ev["window"] = str(W)
    r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, Interval.Ropen(0, W), timeout=timeout)
    if not r.ok or not isinstance(r.value, FiniteSet):
        ev["error"] = f"solveset on window failed: {r.error or type(r.value).__name__}"
        return None, ev
    truth = r.value
    cand_w = _enumerate_on_window(progs, W)
    if cand_w is None:
        ev["error"] = "enumeration_failed"
        return None, ev
    ev["true_window"] = [e for e in truth]
    ev["candidate_window"] = [e for e in cand_w]
    ok, sev = set_equal(cand_w, truth)
    ev["compare"] = sev
    return ok, ev


def _enumerate_window_of_interval(progs, window: Interval):
    lo, hi = window.inf, window.sup
    if lo == -oo or hi == oo:
        return None
    elems = []
    for c, a in progs:
        if a == 0:
            if window.contains(c) == True:  # noqa: E712
                elems.append(c)
            continue
        klo = sp.ceiling((lo - c) / a) if a > 0 else sp.ceiling((hi - c) / a)
        khi = sp.floor((hi - c) / a) if a > 0 else sp.floor((lo - c) / a)
        for k in range(int(klo), int(khi) + 1):
            v = sp.nsimplify(sp.simplify(c + a * k))
            if window.contains(v) == True:  # noqa: E712
                elems.append(v)
    return FiniteSet(*elems)


def general_solution_from_claim(claimed, ns) -> Any:
    """Turn a claimed set whose elements contain the integer symbol n/k into ImageSets."""
    if not isinstance(claimed, FiniteSet):
        return claimed
    parts = []
    for e in claimed.args:
        ints = [s_ for s_ in e.free_symbols if s_.name in ("n", "k", "m")]
        if ints:
            n = ints[0]
            nn = sp.Symbol("n", integer=True)
            parts.append(ImageSet(Lambda(nn, e.subs(n, nn)), S.Integers))
        else:
            parts.append(FiniteSet(e))
    return Union(*parts) if len(parts) > 1 else parts[0]


def verify(ir, solution, ctx: Ctx):
    """Task `trig_solve`: params {"equation"?: str, "var": str, "interval"?: str}."""
    if ir.task.kind != "trig_solve":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        var = ctx.sym(p.get("var", "x"))
        eq_src = p.get("equation") or (ir.givens[0] if ir.givens else None)
        if eq_src is None:
            return unknown(LAYER, "no_equation")
        rel, err = parse_or_unknown(LAYER, ctx.rel, eq_src)
        if err:
            return err
        ns2 = dict(ctx.ns)
        for nm in ("n", "k"):
            ns2.setdefault(nm, sp.Symbol(nm, integer=True))
        from ..normalize.parse import parse_answer, parse_set_str
        ca = solution.claimed_answer
        try:
            if ca.kind in ("set", "interval"):
                claimed = parse_answer(ca.kind, ca.payload, ns2)
            else:
                claimed = FiniteSet(parse_answer("value", ca.payload, ns2))
        except Exception as e:
            return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
        window = None
        if p.get("interval"):
            window = parse_set_str(p["interval"], ns2)
        claimed_g = general_solution_from_claim(claimed, ns2) if window is None else claimed
        ok, ev = periodic_solution_set_equal(rel, var, claimed_g, window=window, timeout=ctx.timeout)
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("error", "undecided"), t.ms, ev)
