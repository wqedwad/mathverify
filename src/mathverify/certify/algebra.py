"""Algebra certificates (E2): guarded roots, inequalities, evaluation under givens,
expression simplification. No single solver API is trusted; completeness of a root
set is certified by Sturm counting for polynomials and by solver agreement otherwise."""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Eq, FiniteSet, ConditionSet, And, oo

from ..equiv import answers_equivalent
from ..equiv.random_point import sample_points
from ..equiv.numeric import real_odd_roots
from ..equiv.sets import set_equal, scalar_equal, normalize_set
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied
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


def _real_roots_worker(num, var):
    """Sandbox worker: every real root of a polynomial, exactly (rationals / radicals / CRootOf)."""
    return list(sp.Poly(num, var).real_roots())


def _undecided(why: str) -> bool:
    return why.startswith(("undecided", "definedness_undecided"))


def solve_guarded(rel, var, domain: sp.Set = S.Reals, timeout: float = 8.0) -> tuple[list, dict[str, Any]]:
    """Candidates from `solve` ∪ `solveset` ∪ the exact real roots of the numerator, filtered by
    guard_roots. Evidence records all of them.

    Completeness (audit of 25 Sep 2026). When lhs − rhs is a rational function of `var`, every
    solution is a real root of its numerator, and `Poly.real_roots()` lists ALL of those exactly:
    the solution set is complete once the guard has decided every one of them (kept or rejected
    for a definite reason). The old Sturm count compared a count over the CLOSED hull
    [inf, sup] of the domain with the guard's rejections, which also counted roots outside that
    hull: x³ = x on x > 0 was never complete and the right answer {1} ended INCORRECT. A
    numerator that is identically 0 is an identity (every point of the domain solves it) and is
    reported as such — before, (x + 1)² = x² + 2x + 1 was "complete with no root" and ∅ was
    certified. Otherwise the two solvers must agree; never when an odd root was read as a real
    root (the solvers work on the principal branch)."""
    rel = _as_equation(rel)
    rel_r = real_odd_roots(rel)
    odd_rewritten = rel_r != rel
    ev: dict[str, Any] = {"equation": str(rel), "domain": str(domain)}
    cands: list = []
    r1 = sb_run("mathverify.sandbox.ops:solve_list", rel_r, var, timeout=timeout)
    r2 = sb_run("mathverify.sandbox.ops:solveset_in", rel_r, var, S.Reals, timeout=timeout)
    ev["solve"] = [str(c) for c in r1.value] if r1.ok else f"error: {r1.error}"
    if r2.ok:
        ev["solveset"] = [str(c) for c in r2.value] if isinstance(r2.value, FiniteSet) else str(r2.value)
    else:
        ev["solveset"] = f"error: {r2.error}"
    if r1.ok:
        cands += [c for c in r1.value if not isinstance(c, dict)]
    if r2.ok and isinstance(r2.value, FiniteSet):
        cands += list(r2.value)
    if odd_rewritten:
        # the principal-branch solvers may still propose roots; the guard decides each one
        r1p = sb_run("mathverify.sandbox.ops:solve_list", rel, var, timeout=timeout)
        if r1p.ok:
            cands += [c for c in r1p.value if not isinstance(c, dict)]
    complete: bool | None = None
    poly_roots: list = []
    try:
        d = sp.together(rel_r.lhs - rel_r.rhs)
        num, _den = sp.fraction(d)
        num = sp.expand(num)
    except Exception:  # noqa: BLE001
        num = None
    p = _poly_in(num, var) if num is not None and not (num.free_symbols - {var}) else None
    if p is not None and p.domain.is_Exact:
        if p.is_zero:
            ev["identity"] = True
            ev["complete"] = None
            ev["kept"] = []
            ev["rejected"] = []
            return [], ev
        rr = sb_run("mathverify.certify.algebra:_real_roots_worker", num, var, timeout=timeout)
        if rr.ok:
            poly_roots = list(rr.value)
            cands += poly_roots
            ev["numerator_real_roots"] = [str(r) for r in poly_roots]
    # de-duplicate: exactly equal only (an undecided pair stays two candidates; the guard
    # decides each). Exact real roots first, so they are the representatives kept.
    uniq: list = []
    for c in poly_roots + cands:
        if not any(scalar_equal(c, u) is True for u in uniq):
            uniq.append(c)
    kept, rejected = guard_roots(rel, var, uniq, domain)
    ev["rejected"] = [(str(c), why) for c, why in rejected]
    ev["kept"] = [str(c) for c in kept]
    if p is not None and poly_roots is not None and (p.domain.is_Exact and "numerator_real_roots" in ev):
        undecided = [c for c, why in rejected if _undecided(why)]
        complete = not undecided
        ev["completeness_method"] = "exact_real_roots_of_numerator"
        ev["complete"] = complete
    elif not odd_rewritten:
        both = r1.ok and r2.ok and isinstance(r2.value, FiniteSet) and not isinstance(r2.value, ConditionSet)
        if both:
            s1 = {str(c) for c in r1.value}
            s2 = {str(c) for c in r2.value}
            complete = (s1 == s2) or (set(ev["kept"]) <= s1 and set(ev["kept"]) <= s2)
            # a candidate the guard could not decide may be a root: agreeing solvers say nothing about
            # it. With a free a, √(x − a) = √(2 − x) had its root a/2 + 1 undecided and ∅ certified,
            # though it is the answer only for a > 2 (part vi, 30 Sep 2026)
            complete = complete and not any(_undecided(why) for _, why in rejected)
            ev["completeness_method"] = "solver_agreement"
            ev["complete"] = complete
        else:
            ev["complete"] = None
    else:
        ev["complete"] = None
        ev["completeness_method"] = "none (odd roots read as real roots)"
    return kept, ev


# ---------------------------------------------------------------------------
def _claimed_as_set(ctx: Ctx, solution) -> sp.Set | None:
    ca = solution.claimed_answer
    from ..normalize.parse import parse_answer
    if ca.kind in ("set", "interval"):
        return parse_answer(ca.kind, ca.payload, ctx.claim_ns(solution))
    if ca.kind == "none":
        return S.EmptySet
    v = parse_answer("value", ca.payload, ctx.claim_ns(solution))
    return v if isinstance(v, sp.Set) else FiniteSet(v)


def _defined_region(rel, var, dom, timeout) -> sp.Set | None:
    """Where the equation is defined: the domain of discourse (with the written conditions)
    ∩ the definedness conditions of the parsed relation. None when not computable."""
    region = dom
    for c in definedness_conditions(rel, var):
        rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=timeout)
        if not rr.ok or isinstance(rr.value, ConditionSet):
            return None
        region = sp.Intersection(region, rr.value)
    return region


def _verify_identity(rel, var, dom, claimed, ev, ctx, t):
    """lhs − rhs vanishes identically: the solution set is the region where the equation is
    defined. A finite claim is wrong when that region is infinite; a set claim is compared."""
    region = _defined_region(rel, var, dom, ctx.timeout)
    ev["identity_region"] = str(region)
    if region is None:
        return unknown(LAYER, "identity_equation_region_not_computable", 0, ev)
    if isinstance(claimed, FiniteSet) or claimed is S.EmptySet:
        norm = normalize_set(region)
        infinite = region.is_subset(S.Integers) is not True and norm is not None and any(
            iv.measure > 0 for iv in norm[0])
        if region.is_subset(S.Integers) is True:
            try:
                infinite = region.is_finite_set is False
            except Exception:  # noqa: BLE001
                infinite = False
        if infinite:
            ev["reason"] = "identity_equation_every_point_of_the_domain_solves_it"
            return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    ok, sev = set_equal(claimed, region)
    ev["compare"] = sev
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        ev["reason"] = "identity_equation_solution_set_differs"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "identity_equation_undecided", 0, ev)


def _with_given_inequalities(ctx: Ctx, var, dom, exclude=None):
    """The domain restricted by every given on `var` other than the equation itself (`x > 5` next
    to `2x = 4`). Ignoring them certified {2} for 2x = 4, x > 5 in the z3 layer while the algebra
    layer refuted it (audit of 25 Sep 2026). A given equation restricts too (x³ = 8 next to x² = 4
    left {-2, 2} certified), and a symbol another given fixes is read as its value (x > b with
    b = 0); both were dropped (part vi, 30 Sep 2026). Returns (domain, givens that still name another
    symbol); the domain is None when a given cannot be solved."""
    rels = [g for g in ctx.givens() if g != exclude and isinstance(g, (sp.core.relational.Relational, And))
            and var in g.free_symbols]
    rels, unbound = ctx.on_var(rels, var)
    for g in rels:
        rr = sb_run("mathverify.sandbox.ops:solveset_in", real_odd_roots(g), var, S.Reals, timeout=ctx.timeout)
        if not rr.ok or isinstance(rr.value, ConditionSet):
            return None, unbound
        dom = sp.Intersection(dom, rr.value)
    return dom, unbound


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
    dom, unbound = _with_given_inequalities(ctx, var, ctx.domain_for(var), exclude=rel)
    # the equation's own definedness conditions are checked at every root by guard_roots
    unbound = ctx.unapplied_conditions(var, enforced=definedness_conditions(rel, var)) + unbound
    if unbound:
        return condition_not_applied(LAYER, unbound)
    if dom is None:
        return unknown(LAYER, "given_inequality_not_solvable")
    ev: dict[str, Any] = {"claimed": str(claimed), "domain": str(dom)}
    if not isinstance(claimed, FiniteSet):
        roots, sev = solve_guarded(rel, var, dom, ctx.timeout)
        ev["solve_guarded"] = sev
        if sev.get("identity"):
            return _verify_identity(rel, var, dom, claimed, ev, ctx, t)
        if claimed is S.EmptySet:
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
    hard_bad = [(c, w) for c, w in rejected if not _undecided(w)]
    if hard_bad:
        ev["reason"] = f"claimed_root_invalid: {hard_bad[0][1]}"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    if rejected:
        return unknown(LAYER, "claimed_root_undecided", 0, ev)
    # (2) completeness: are there true roots missing from the claim?
    roots, sev = solve_guarded(rel, var, dom, ctx.timeout)
    ev["solve_guarded"] = sev
    if sev.get("identity"):
        return _verify_identity(rel, var, dom, claimed, ev, ctx, t)
    # a root is missing only when it is PROVED different from every claimed root; an undecided
    # comparison is not evidence either way
    missing, undecided = [], []
    for r in roots:
        cmp = [scalar_equal(r, c) for c in claimed.args]
        if any(x_ is True for x_ in cmp):
            continue
        (missing if all(x_ is False for x_ in cmp) else undecided).append(r)
    ev["missing"] = [str(m) for m in missing]
    if missing:
        ev["reason"] = "missing_root"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    if undecided:
        ev["undecided_roots"] = [str(u) for u in undecided]
        return unknown(LAYER, "root_comparison_undecided", 0, ev)
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
    inside = [pt[var] for pt in sample_points({var: sp.Intersection(claimed_set, dom)}, n, seed, special=True)]
    outside_set = sp.Complement(dom, claimed_set)
    outside = [pt[var] for pt in sample_points({var: outside_set}, n, seed + 1, special=True)]
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


def _rational_inequality_set(rel, var, timeout: float) -> sp.Set | None:
    """Exact solution set of one polynomial/rational inequality in `var`: the real roots of the
    numerator and the denominator (exact, CRootOf) cut the line into cells; the sign on each cell
    is read at a rational point, and every root is decided on its own. Used when solveset
    returns a ConditionSet (it does for x³ − 3x + 1 > 0)."""
    if not isinstance(rel, (sp.StrictLessThan, sp.LessThan, sp.StrictGreaterThan, sp.GreaterThan)):
        return None
    try:
        num, den = sp.fraction(sp.together(rel.lhs - rel.rhs))
        num, den = sp.expand(num), sp.expand(den)
        pn, pd = sp.Poly(num, var), sp.Poly(den, var)
    except Exception:  # noqa: BLE001
        return None
    if (num.free_symbols | den.free_symbols) - {var} or not (pn.domain.is_Exact and pd.domain.is_Exact):
        return None
    if pn.is_zero:
        return None
    rn = sb_run("mathverify.certify.algebra:_real_roots_worker", num, var, timeout=timeout)
    rd = sb_run("mathverify.certify.algebra:_real_roots_worker", den, var, timeout=timeout) \
        if pd.degree() > 0 else None
    if not rn.ok or (rd is not None and not rd.ok):
        return None
    pts: list = []
    for r_ in list(rn.value) + (list(rd.value) if rd is not None else []):
        if not any(r_ == u for u in pts):
            pts.append(r_)
    try:
        pts = sorted(pts, key=lambda v: sp.N(v, 40))
    except Exception:  # noqa: BLE001
        return None
    den_roots = list(rd.value) if rd is not None else []

    def holds_at(v):
        return _num_relation_holds_exact(rel, var, v)

    pieces: list = []
    edges = [-oo] + pts + [oo]
    for lo, hi in zip(edges[:-1], edges[1:]):
        if lo == -oo and hi == oo:
            q = sp.Integer(0)
        elif lo == -oo:
            q = sp.floor(sp.N(hi, 40)) - 1
        elif hi == oo:
            q = sp.ceiling(sp.N(lo, 40)) + 1
        else:
            q = sp.nsimplify(sp.N((lo + hi) / 2, 40), rational=True)
            if not (lo < q < hi):
                return None
        h = holds_at(q)
        if h is None:
            return None
        if h:
            pieces.append(sp.Interval.open(lo, hi))
    for v in pts:
        if any(v == d_ for d_ in den_roots):
            continue
        h = holds_at(v)
        if h is None:
            return None
        if h:
            pieces.append(sp.FiniteSet(v))
    return sp.Union(*pieces) if pieces else S.EmptySet


def _num_relation_holds_exact(rel, var, v):
    from .domain import relation_holds_at as _rh
    return _rh(rel, var, v)


def _verify_solve_inequality(ir, solution, ctx: Ctx, t):
    p = ir.task.params
    var = ctx.sym(p.get("var", "x"))
    rels = [ctx.rel(p["inequality"])] if p.get("inequality") else ctx.givens()
    # a symbol a given fixes is read as its value (the given b = 0 itself drops out); a relation or a
    # condition that still names another symbol cannot be read on var alone (part vi, 30 Sep 2026)
    rels, unbound = ctx.on_var(rels, var)
    unbound = ctx.unapplied_conditions(var) + unbound
    if unbound:
        return condition_not_applied(LAYER, unbound)
    if not rels:
        return unknown(LAYER, "no_inequality")
    # odd roots are real roots (see equiv.numeric.real_odd_roots); several givens are a system
    rels = [real_odd_roots(r) for r in rels]
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
    # (2) symbolic solution set, validated by sampling before it is trusted. One relation at a
    # time: solveset does not accept a conjunction, so every system of two or more givens was
    # UNKNOWN before (x > 1, x < 5 → (1, 5) included).
    truth, r = dom, None
    flat: list = []
    for one in rels:
        flat.extend(one.args if isinstance(one, And) else [one])     # a chained 1 < x < 5
    for one in flat:
        r = sb_run("mathverify.sandbox.ops:solveset_in", one, var, dom, timeout=ctx.timeout)
        if not r.ok or isinstance(r.value, ConditionSet):
            exact_set = _rational_inequality_set(one, var, ctx.timeout)
            if exact_set is None:
                break
            from ..sandbox.pool import CasResult
            r = CasResult(True, exact_set, None, False, 0.0, "exact_rational_inequality")
        try:
            truth = sp.Intersection(truth, r.value)
        except Exception as e:  # noqa: BLE001 - SymPy cannot always order symbolic endpoints
            ev["intersection_error"] = f"{type(e).__name__}: {e}"
            r = None
            break
    if r is not None and r.ok and not isinstance(r.value, ConditionSet):
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
        ev["solveset_error"] = "intersection" if r is None else (r.error if not r.ok else "ConditionSet")
    return unknown(LAYER, "symbolic_unavailable" if okS else "undecided", 0, ev)


def _filter_solutions(sols: list[dict], ctx: Ctx, undecided: list | None = None) -> list[dict]:
    """The solutions inside every domain and constraint. One whose membership in a number set no
    check decides (the written condition of a gcd/lcm argument, rational, or of a factorial argument,
    natural, at x = pi + E) is neither kept nor dropped: it goes to `undecided`. The value
    x + gcd(x, 2) - gcd(2, x) at pi + E was certified (V16, 30 Sep 2026)."""
    from .domain import decide_membership
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
                    if isinstance(h, sp.Contains) and not h.free_symbols:
                        m = decide_membership(*h.args)
                        if m is False or (m is None and undecided is not None):
                            if m is None:
                                undecided.append(s_)
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
            und, why = _claim_undefined_where_expr_defined(solution, ctx, dom)
            if und is True:
                ev["reason"] = f"claim_as_written: {why}"
                return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
            if und is None:
                return unknown(LAYER, f"claim_as_written_undecided: {why}", 0, ev)
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
        good, undecided = [], []
        admissible = _filter_solutions(sols, ctx, undecided)
        if undecided:
            ev["membership_undecided"] = [{str(k): str(v) for k, v in s_.items()} for s_ in undecided]
            return unknown(LAYER, "solution_membership_undecided", 0, ev)
        for s_ in admissible:
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


def _claim_undefined_where_expr_defined(solution, ctx: Ctx, dom: dict) -> tuple[bool | None, str]:
    """Is the CLAIM, read as written, undefined at some point where the problem's expression is
    defined? The claim is parsed with SymPy's automatic simplification, which erases its own
    undefined points: `sqrt(x)**2` becomes x, and was certified as a simplification of x on ℝ
    (Lean audit E10, 25 Sep 2026). True -> the claim is not equal to the expression on its domain."""
    from .domain import written_definedness
    payload = solution.claimed_answer.payload
    if not isinstance(payload, str):
        return False, "payload_not_text"
    try:
        conds, nowhere = written_definedness(payload, ctx.claim_ns(solution))
    except Exception as e:  # noqa: BLE001
        return None, f"claim_not_readable_as_written: {type(e).__name__}"
    if nowhere & set(dom):
        return True, "claim_defined_nowhere"
    # a problem symbol the claim names only as written (x + log(y) - log(y) folds to x): the problem's
    # expression, which does not name it, is defined for all its values. Left out of `dom`, the
    # claim's condition on it was skipped, and x + log(y) - log(y), x + sqrt(y) - sqrt(y),
    # x + y! - y! and x + gcd(y, 2) - gcd(2, y) were certified simplifications of x (V16, 30 Sep 2026)
    dom = dict(dom)
    for c in conds:
        for s_ in sorted(c.free_symbols - set(dom), key=lambda q: q.name):
            if ctx.ns.get(s_.name) == s_:
                dom[s_] = ctx.domain_for(s_)
    for c in conds:
        fs = c.free_symbols & set(dom)
        if not fs:
            continue
        if len(fs) > 1:
            return None, f"multivariate_claim_condition: {c}"
        (v,) = tuple(fs)
        bad = sp.Eq(c.lhs, c.rhs) if isinstance(c, sp.Ne) else sp.Not(c)
        rr = sb_run("mathverify.sandbox.ops:solveset_in", bad, v, dom[v], timeout=ctx.timeout)
        if not rr.ok or isinstance(rr.value, ConditionSet):
            return None, f"claim_condition_undecided: {c}"
        if rr.value is not S.EmptySet:
            return True, f"claim_undefined_on {rr.value} (condition {c})"
    return False, "claim_defined_on_expression_domain"


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
    joint: list = []
    for s_ in syms:
        d = ctx.domain_for(s_)
        for c in definedness_conditions(expr, s_):
            if getattr(c, "free_symbols", set()) - {s_}:
                # a condition on several variables (a − b ≠ 0) is not a domain of s_ alone: its
                # solution set has a symbolic endpoint, and the sampler died on float(b) (measured:
                # a caught TypeError on (a² − b²)/(a − b) = a − b)
                if c not in joint:
                    joint.append(c)
                continue
            rr = sb_run("mathverify.sandbox.ops:solveset_in", c, s_, S.Reals, timeout=ctx.timeout)
            if rr.ok and not isinstance(rr.value, ConditionSet):
                d = sp.Intersection(d, rr.value)
        dom[s_] = d
    if any(not isinstance(c, sp.Ne) for c in joint):
        # an inequality between variables (√(a − b)) would put half the random points where the
        # problem's expression is undefined: only a symbolic proof decides here
        from ..equiv.symbolic import sym_equal
        okS, sev = sym_equal(claimed, expr)
        ev = {"expr": str(expr), "claimed": str(claimed), "symbolic": sev, "joint_conditions": [str(c) for c in joint]}
        if okS is True:
            return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
        return unknown(LAYER, "multivariate_definedness_needs_symbolic_proof", 0, ev)
    und, why = _claim_undefined_where_expr_defined(solution, ctx, dom)
    if und is True:
        ev = {"expr": str(expr), "claimed": str(claimed), "reason": f"claim_as_written: {why}"}
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    if und is None:
        return unknown(LAYER, f"claim_as_written_undecided: {why}", 0, {"expr": str(expr), "claimed": str(claimed)})
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
