"""Algebra certificates (E2): guarded roots, inequalities, evaluation under givens,
expression simplification. No single solver API is trusted; completeness of a root
set is certified by Sturm counting for polynomials and by solver agreement otherwise."""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Eq, FiniteSet, Interval, ConditionSet, And, oo

from ..equiv import answers_equivalent
from ..equiv.random_point import sample_points
from ..equiv.sets import set_equal, scalar_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown
from .domain import guard_roots, relation_holds_at, definedness_conditions, in_domain

LAYER = "certify.algebra"


# ---------------------------------------------------------------------------
def _as_equation(rel):
    if isinstance(rel, Eq):
        return rel
    return Eq(rel, 0)


def _poly_in(expr, var):
    try:
        p = sp.Poly(expr, var)
        return p if not p.free_symbols_in_domain else None
    except Exception:
        return None


def solve_guarded(rel, var, domain: sp.Set = S.Reals, timeout: float = 8.0) -> tuple[list, dict[str, Any]]:
    """Candidates from `solve` ∪ `solveset`, filtered by guard_roots. Evidence records both."""
    rel = _as_equation(rel)
    ev: dict[str, Any] = {"equation": str(rel), "domain": str(domain)}
    cands: list = []
    r1 = sb_run("mathverify.sandbox.ops:solve_list", rel, var, timeout=timeout)
    r2 = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, S.Reals, timeout=timeout)
    ev["solve"] = [str(c) for c in r1.value] if r1.ok else f"error: {r1.error}"
    if r2.ok:
        ev["solveset"] = [str(c) for c in r2.value] if isinstance(r2.value, FiniteSet) else str(r2.value)
    else:
        ev["solveset"] = f"error: {r2.error}"
    if r1.ok:
        cands += [c for c in r1.value if not isinstance(c, dict)]
    if r2.ok and isinstance(r2.value, FiniteSet):
        cands += list(r2.value)
    # numerator roots of the rational form are candidates too: the ones killed by the
    # denominator / definedness must be *seen and rejected* by the guard so that the
    # Sturm completeness count can account for them (e.g. x/(x-3) = 3/(x-3) + 2 -> {})
    d0 = sp.together(rel.lhs - rel.rhs)
    num0, _den0 = sp.fraction(d0)
    p0 = _poly_in(sp.expand(num0), var)
    if p0 is not None and p0.degree() <= 8:
        r3 = sb_run("mathverify.sandbox.ops:poly_real_roots", sp.expand(num0), var, timeout=timeout)
        if r3.ok:
            cands += list(r3.value)
    # de-duplicate by structural/numeric equality
    uniq: list = []
    for c in cands:
        if not any(scalar_equal(c, u) is True for u in uniq):
            uniq.append(c)
    kept, rejected = guard_roots(rel, var, uniq, domain)
    ev["rejected"] = [(str(c), why) for c, why in rejected]
    ev["kept"] = [str(c) for c in kept]
    # completeness certificate
    complete: bool | None = None
    d = sp.together(rel.lhs - rel.rhs)
    num, den = sp.fraction(d)
    p = _poly_in(sp.expand(num), var)
    if p is not None:
        lo = domain.inf if isinstance(domain, Interval) else -oo
        hi = domain.sup if isinstance(domain, Interval) else oo
        rc = sb_run("mathverify.sandbox.ops:poly_count_roots", sp.expand(num), var, lo, hi, timeout=timeout)
        if rc.ok:
            # roots of numerator inside domain; those killed by the denominator/guard are not solutions
            ev["sturm_numerator_roots"] = rc.value
            n_valid = len(kept)
            n_rejected_by_guard = sum(1 for _, why in rejected if why.startswith(("definedness", "does_not", "outside")))
            complete = (rc.value == n_valid + n_rejected_by_guard) or (rc.value == n_valid)
            ev["complete"] = complete
            ev["completeness_method"] = "sturm"
    if complete is None:
        both = r1.ok and r2.ok and isinstance(r2.value, FiniteSet) and not isinstance(r2.value, ConditionSet)
        if both:
            s1 = {str(c) for c in r1.value}
            s2 = {str(c) for c in r2.value}
            complete = (s1 == s2) or (set(ev["kept"]) <= s1 and set(ev["kept"]) <= s2)
            ev["completeness_method"] = "solver_agreement"
            ev["complete"] = complete
        else:
            ev["complete"] = None
    return kept, ev


# ---------------------------------------------------------------------------
def _claimed_as_set(ctx: Ctx, solution) -> sp.Set | None:
    ca = solution.claimed_answer
    from ..normalize.parse import parse_answer
    if ca.kind in ("set", "interval"):
        return parse_answer(ca.kind, ca.payload, ctx.ns)
    if ca.kind == "none":
        return S.EmptySet
    v = parse_answer("value", ca.payload, ctx.ns)
    return v if isinstance(v, sp.Set) else FiniteSet(v)


def _verify_solve_equation(ir, solution, ctx: Ctx, t):
    p = ir.task.params
    var = ctx.sym(p.get("var", "x"))
    eq_src = p.get("equation") or (ir.givens[0] if ir.givens else None)
    if eq_src is None:
        return unknown(LAYER, "no_equation")
    rel, err = parse_or_unknown(LAYER, ctx.rel, eq_src)
    if err:
        return err
    if not isinstance(rel, Eq):
        return unknown(LAYER, "not_an_equation")
    claimed, err = parse_or_unknown(LAYER, _claimed_as_set, ctx, solution)
    if err:
        return err
    dom = ctx.domain_for(var)
    ev: dict[str, Any] = {"claimed": str(claimed), "domain": str(dom)}
    if not isinstance(claimed, FiniteSet):
        if claimed is S.EmptySet:
            roots, sev = solve_guarded(rel, var, dom, ctx.timeout)
            ev["solve_guarded"] = sev
            if roots:
                ev["reason"] = "solutions_exist"
                return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
            if sev.get("complete"):
                return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
            return unknown(LAYER, "completeness_unknown", 0, ev)
        return unknown(LAYER, "claimed_set_not_finite", 0, ev)
    # (1) every claimed root must satisfy the original relation + definedness + domain
    kept, rejected = guard_roots(rel, var, list(claimed.args), dom)
    ev["claimed_check"] = {"kept": [str(k) for k in kept], "rejected": [(str(c), w) for c, w in rejected]}
    hard_bad = [(c, w) for c, w in rejected if not w.startswith("undecided") and not w.startswith("definedness_undecided")]
    if hard_bad:
        ev["reason"] = f"claimed_root_invalid: {hard_bad[0][1]}"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    if rejected:
        return unknown(LAYER, "claimed_root_undecided", 0, ev)
    # (2) completeness: are there true roots missing from the claim?
    roots, sev = solve_guarded(rel, var, dom, ctx.timeout)
    ev["solve_guarded"] = sev
    missing = [r for r in roots if not any(scalar_equal(r, c) is True for c in claimed.args)]
    ev["missing"] = [str(m) for m in missing]
    if missing:
        ev["reason"] = "missing_root"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    extra = [c for c in claimed.args if not any(scalar_equal(r, c) is True for r in roots)]
    if extra:
        # claimed root passed the guard but solvers did not produce it: it IS a root (guard verified),
        # so solvers were incomplete; keep it and mark completeness unknown
        ev["solver_missed_valid_root"] = [str(e) for e in extra]
    if sev.get("complete") is True and not extra:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    # all claimed roots verified, completeness not certified
    return unknown(LAYER, "completeness_uncertified", 0, ev, flags=["completeness_uncertified"])


def _endpoints(sset: sp.Set) -> tuple[list, list]:
    """(closed endpoints -> members, open endpoints -> non-members) of a normalised set."""
    from ..equiv.sets import normalize_set
    norm = normalize_set(sset)
    if norm is None:
        return [], []
    ivs, pts = norm
    members, non = list(pts), []
    for iv in ivs:
        for end, is_open in ((iv.inf, iv.left_open), (iv.sup, iv.right_open)):
            if end in (-oo, oo):
                continue
            (non if is_open else members).append(end)
    return members, non


def _sample_inequality(rel, var, claimed_set: sp.Set, dom: sp.Set, seed: int, n: int = 40) -> tuple[bool | None, dict]:
    """Inside the claimed set the relation must hold; in dom \\ claimed it must fail.
    Endpoints are checked explicitly (continuous sampling never hits them)."""
    ev: dict[str, Any] = {}
    inside = [pt[var] for pt in sample_points({var: sp.Intersection(claimed_set, dom)}, n, seed)]
    outside_set = sp.Complement(dom, claimed_set)
    outside = [pt[var] for pt in sample_points({var: outside_set}, n, seed + 1)]
    members, non = _endpoints(claimed_set)
    inside += [m for m in members if in_domain(dom, m) is not False]
    outside += [m for m in non if in_domain(dom, m) is True]
    ev["n_inside"], ev["n_outside"] = len(inside), len(outside)
    for c in inside:
        h = relation_holds_at(rel, var, c)
        if h is False:
            ev["counterexample"] = ("inside_but_false", str(c))
            return False, ev
    for c in outside:
        h = relation_holds_at(rel, var, c)
        if h is True:
            ev["counterexample"] = ("outside_but_true", str(c))
            return False, ev
    if len(inside) + len(outside) < 6:
        return None, ev
    return True, ev


def _verify_solve_inequality(ir, solution, ctx: Ctx, t):
    p = ir.task.params
    var = ctx.sym(p.get("var", "x"))
    rels = [ctx.rel(p["inequality"])] if p.get("inequality") else ctx.givens()
    if not rels:
        return unknown(LAYER, "no_inequality")
    rel = And(*rels) if len(rels) > 1 else rels[0]
    claimed, err = parse_or_unknown(LAYER, _claimed_as_set, ctx, solution)
    if err:
        return err
    dom = ctx.domain_for(var)
    for c in definedness_conditions(rel, var):
        rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=ctx.timeout)
        if rr.ok and not isinstance(rr.value, ConditionSet):
            dom = sp.Intersection(dom, rr.value)
    ev: dict[str, Any] = {"claimed": str(claimed), "domain": str(dom)}
    # (1) direct refutation of the claim by sampling (incl. endpoints)
    okS, sev = _sample_inequality(rel, var, claimed, dom, ctx.seed)
    ev["sampling"] = sev
    if okS is False:
        ev["reason"] = "sampling_counterexample"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    # (2) symbolic solution set, validated by sampling before it is trusted
    r = sb_run("mathverify.sandbox.ops:solveset_in", rel, var, dom, timeout=ctx.timeout)
    if r.ok and not isinstance(r.value, ConditionSet):
        truth = r.value
        ev["truth"] = str(truth)
        okT, tev = _sample_inequality(rel, var, truth, dom, ctx.seed + 7)
        ev["truth_validation"] = tev
        if okT is False:
            return unknown(LAYER, "solveset_result_failed_validation", 0, ev, flags=["cas_unreliable"])
        ok, cev = set_equal(claimed, truth)
        ev["compare"] = cev
        if ok is True:
            return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
        if ok is False:
            ev["reason"] = "solution_set_differs"
            return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    else:
        ev["solveset_error"] = r.error if not r.ok else "ConditionSet"
    return unknown(LAYER, "symbolic_unavailable" if okS else "undecided", 0, ev)


def _filter_solutions(sols: list[dict], ctx: Ctx) -> list[dict]:
    out = []
    cons = ctx.var_constraints()
    for s_ in sols:
        ok = True
        for v in ctx.syms():
            if v in s_:
                val = s_[v]
                if val.free_symbols:
                    continue
                if val.is_real is False:
                    ok = False
                    break
                if in_domain(ctx.domain_for(v), val) is False:
                    ok = False
                    break
        if ok:
            for c in cons:
                try:
                    h = c.subs(s_)
                    if h is sp.false:
                        ok = False
                        break
                    if isinstance(h, sp.core.relational.Relational) and not h.free_symbols:
                        hv = relation_holds_at(h, sp.Symbol("_dummy"), 0)
                        if hv is False:
                            ok = False
                            break
                except Exception:
                    pass
        if ok:
            out.append(s_)
    return out


def _verify_evaluate(ir, solution, ctx: Ctx, t):
    p = ir.task.params
    expr_src = p.get("expr") or ir.unknown_of_interest
    if not expr_src:
        return unknown(LAYER, "no_target_expression")
    target, err = parse_or_unknown(LAYER, ctx.expr, expr_src)
    if err:
        return err
    claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
    if err:
        return err
    ev: dict[str, Any] = {"target": str(target), "claimed": str(claimed)}
    shape = "scalar" if not target.free_symbols or not ir.givens else "scalar"
    if not ir.givens:
        # pure computation
        dom = None
        if target.free_symbols:
            dom = {s_: ctx.domain_for(s_) for s_ in target.free_symbols}
            shape = "expression"
        ok, cev = answers_equivalent(claimed, target, shape=shape, domain=dom,
                                     rel_tol=p.get("rel_tol"), abs_tol=p.get("abs_tol"))
        ev["compare"] = cev
        ev["method"] = "direct"
    else:
        rels = ctx.givens()
        syms = [s_ for s_ in ctx.syms() if any(s_ in r.free_symbols for r in rels)]
        if not syms:
            return unknown(LAYER, "no_unknowns_in_givens")
        eqs = [r for r in rels if isinstance(r, Eq)]
        ineqs = [r for r in rels if not isinstance(r, Eq)]
        if not eqs:
            return unknown(LAYER, "no_equations_to_solve")
        r = sb_run("mathverify.sandbox.ops:solve_system", eqs, syms, True, timeout=ctx.timeout)
        if not r.ok:
            return unknown(LAYER, f"solve_failed: {r.error}", 0, ev, flags=r.flags)
        sols = r.value if isinstance(r.value, list) else [r.value]
        sols = [s_ for s_ in sols if isinstance(s_, dict)]
        ev["raw_solutions"] = [{str(k): str(v) for k, v in s_.items()} for s_ in sols]
        # keep solutions satisfying inequalities/constraints/domains
        good = []
        for s_ in _filter_solutions(sols, ctx):
            okall = True
            for iq in ineqs:
                h = iq.subs(s_)
                if h is sp.false:
                    okall = False
                    break
                if h is not sp.true and isinstance(h, sp.core.relational.Relational) and not h.free_symbols:
                    from .domain import _num_relation_holds
                    if _num_relation_holds(h, sp.Symbol("_d"), 0) is False:
                        okall = False
                        break
            if okall:
                good.append(s_)
        ev["admissible_solutions"] = [{str(k): str(v) for k, v in s_.items()} for s_ in good]
        if not good:
            return unknown(LAYER, "ir_inconsistent_no_solution", 0, ev, flags=["ir_inconsistent"])
        values = []
        for s_ in good:
            v = sp.simplify(target.subs(s_))
            if v.free_symbols:
                # the equations alone do not pin the target (integrality/inequalities may);
                # this is NOT evidence of an incomplete IR — z3 decides that (E7)
                return unknown(LAYER, "target_not_determined_by_equations", 0, ev)
            if not any(scalar_equal(v, u) is True for u in values):
                values.append(v)
        ev["target_values"] = [str(v) for v in values]
        if len(values) > 1:
            return unknown(LAYER, "target_not_unique", 0, ev, flags=["ir_incomplete"])
        ok, cev = answers_equivalent(claimed, values[0], shape="scalar",
                                     rel_tol=p.get("rel_tol"), abs_tol=p.get("abs_tol"))
        ev["compare"] = cev
        ev["method"] = "solve_system"
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "undecided", 0, ev)


def _verify_simplify(ir, solution, ctx: Ctx, t):
    p = ir.task.params
    expr, err = parse_or_unknown(LAYER, ctx.expr, p["expr"])
    if err:
        return err
    claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
    if err:
        return err
    syms = sorted(expr.free_symbols | sp.sympify(claimed).free_symbols, key=lambda s_: s_.name)
    dom = {}
    for s_ in syms:
        d = ctx.domain_for(s_)
        for c in definedness_conditions(expr, s_):
            rr = sb_run("mathverify.sandbox.ops:solveset_in", c, s_, S.Reals, timeout=ctx.timeout)
            if rr.ok and not isinstance(rr.value, ConditionSet):
                d = sp.Intersection(d, rr.value)
        dom[s_] = d
    ok, cev = answers_equivalent(claimed, expr, shape="expression", domain=dom)
    ev = {"expr": str(expr), "claimed": str(claimed), "compare": cev, "domain": {str(k): str(v) for k, v in dom.items()}}
    if ok is True:
        return result(LAYER, "pass", 0.99 if cev.get("method") == "symbolic" else 0.97, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "undecided", 0, ev)


_HANDLERS = {
    "solve_equation": _verify_solve_equation,
    "solve_inequality": _verify_solve_inequality,
    "evaluate": _verify_evaluate,
    "simplify_expression": _verify_simplify,
}


def verify(ir, solution, ctx: Ctx):
    handler = _HANDLERS.get(ir.task.kind)
    if handler is None:
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        out = handler(ir, solution, ctx, t)
    out.latency_ms = round(t.ms, 2)
    return out
