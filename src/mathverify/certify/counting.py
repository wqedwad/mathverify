"""Exact counting (E10): Sturm root counts, integers in a set, small brute force."""
from __future__ import annotations

import itertools
from typing import Any

import sympy as sp
from sympy import S, Interval, FiniteSet, Union, oo, And

from ..equiv.sets import normalize_set
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.counting"


def count_real_roots(expr, var, lo=-oo, hi=oo, distinct: bool = True) -> int:
    expr = sp.sympify(expr)
    try:
        p = sp.Poly(expr, var)
    except sp.PolynomialError as e:
        raise ValueError(f"not a polynomial in {var}: {e}") from e
    if not p.domain.is_Exact and p.domain != sp.QQ and not p.domain.is_ZZ:
        try:
            p = sp.Poly(sp.nsimplify(expr), var)
        except Exception:
            pass
    if p.free_symbols_in_domain:
        raise ValueError("polynomial has symbolic coefficients")
    if distinct:
        return int(p.count_roots(lo, hi))
    rr = p.real_roots()
    return sum(1 for r in rr if (lo == -oo or r >= lo) and (hi == oo or r <= hi))


def count_integers_in(sset: sp.Set) -> int | None:
    sset = sp.sympify(sset)
    if sset is S.EmptySet:
        return 0
    if isinstance(sset, sp.Range):
        try:
            return len(sset)
        except (TypeError, ValueError):
            return None
    if isinstance(sset, sp.Intersection):
        # Interval ∩ Integers that SymPy left unevaluated
        ivs = [a for a in sset.args if isinstance(a, (Interval, Union, FiniteSet))]
        if len(ivs) == 1 and all(a in (S.Integers, S.Naturals, S.Naturals0) or a is ivs[0] for a in sset.args):
            base = count_integers_in(ivs[0])
            if base is None:
                return None
            lo_cut = 1 if S.Naturals in sset.args else (0 if S.Naturals0 in sset.args else None)
            if lo_cut is None:
                return base
            return count_integers_in(sp.Intersection(ivs[0], Interval(lo_cut, oo)))
        return None
    norm = normalize_set(sset)
    if norm is None:
        return None
    ivs, pts = norm
    total = 0
    for iv in ivs:
        lo, hi = iv.inf, iv.sup
        if lo == -oo or hi == oo:
            return None
        a = sp.ceiling(lo)
        if iv.left_open and a == lo:
            a += 1
        b = sp.floor(hi)
        if iv.right_open and b == hi:
            b -= 1
        total += max(0, int(b - a + 1))
    for p in pts:
        if p.is_integer:
            total += 1
    return total


def _brute_force_count(givens, syms, bounds: dict[str, tuple[int, int]], limit: int = 2_000_000) -> int | None:
    ranges = []
    size = 1
    for s_ in syms:
        lo, hi = bounds[s_.name]
        ranges.append(range(int(lo), int(hi) + 1))
        size *= len(ranges[-1])
        if size > limit:
            return None
    f = sp.lambdify(syms, And(*givens) if len(givens) > 1 else givens[0], "math") if givens else None
    cnt = 0
    for tup in itertools.product(*ranges):
        try:
            if f is None or f(*tup):
                cnt += 1
        except (ZeroDivisionError, ValueError):
            continue
    return cnt


def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("count_roots", "count_integers", "count_solutions"):
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        ca = solution.claimed_answer
        try:
            claimed = int(ca.payload) if ca.kind == "count" else int(sp.sympify(ctx.claimed(solution)))
        except Exception as e:
            return unknown(LAYER, f"claimed_not_integer: {e}", flags=["parse_error"])
        ev: dict[str, Any] = {"claimed": claimed}
        if kind == "count_roots":
            var = ctx.sym(p.get("var", "x"))
            expr, err = parse_or_unknown(LAYER, ctx.expr, p["expr"])
            if err:
                return err
            lo = ctx.expr(str(p["lo"])) if "lo" in p else -oo
            hi = ctx.expr(str(p["hi"])) if "hi" in p else oo
            r = sb_run("mathverify.certify.counting:count_real_roots", expr, var, lo, hi,
                       p.get("distinct", True), timeout=ctx.timeout)
            if not r.ok:
                return unknown(LAYER, r.error or "count_failed", 0, ev, flags=r.flags)
            truth = r.value
            ev["method"] = "sturm"
        elif kind == "count_integers":
            var = ctx.sym(p.get("var", "x"))
            rels = ctx.givens()
            dom = ctx.domain_for(var)
            cond = And(*rels) if len(rels) > 1 else rels[0]
            r = sb_run("mathverify.sandbox.ops:solveset_in", cond, var, S.Reals, timeout=ctx.timeout)
            if not r.ok or isinstance(r.value, sp.ConditionSet):
                return unknown(LAYER, "solveset_failed", 0, ev, flags=r.flags)
            sol = sp.Intersection(r.value, dom) if dom != S.Reals and not dom.is_subset(S.Integers) else r.value
            if dom.is_subset(S.Integers) and dom != S.Integers:
                sol = sp.Intersection(r.value, dom)
            ev["solution_set"] = str(sol)
            truth = count_integers_in(sol) if not isinstance(sol, sp.Intersection) else count_integers_in(sol.args[0])
            if truth is None:
                return unknown(LAYER, "infinite_or_unsupported_set", 0, ev)
            ev["method"] = "interval_integer_count"
        else:  # count_solutions: brute force over integer boxes
            syms = ctx.syms()
            bounds = {}
            for v in ir.vars:
                b = p.get("bounds", {}).get(v.name)
                if b is None:
                    return unknown(LAYER, f"no_bounds_for_{v.name}", 0, ev)
                bounds[v.name] = (int(sp.sympify(b[0])), int(sp.sympify(b[1])))
            rels = ctx.givens() + ctx.var_constraints()
            truth = _brute_force_count(rels, syms, bounds)
            if truth is None:
                return unknown(LAYER, "search_space_too_large", 0, ev, flags=["brute_force_limit"])
            ev["method"] = "brute_force"
            ev["bounds"] = bounds
        ev["truth"] = truth
        ok = (truth == claimed)
    conf = 0.99
    return result(LAYER, "pass" if ok else "fail", conf, True, ev, t.ms, primary=True)
