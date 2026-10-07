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
from ..sandbox.exactsets import at_risk, exact_complement, exact_intersection, set_is_empty
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied, condition_unsolved
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


def _bounded_hull(dom):
    """(inf, sup) of a domain when both are finite numbers, else None."""
    try:
        lo, hi = dom.inf, dom.sup
    except Exception:  # noqa: BLE001 - an unsolved condition (ConditionSet) has no hull
        return None
    if lo.is_number and hi.is_number and lo.is_finite and hi.is_finite:
        return lo, hi
    return None


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
    certified. Otherwise the equation must be of an exact class (sandbox.exactsets.class_solveset);
    two solvers agreeing was taken for completeness until round 5 of part d4b (2 Oct 2026) and is no
    proof: they share blind spots."""
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
    window_set = None
    window_how = None
    hull = _bounded_hull(domain)
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
    if "numerator_real_roots" not in ev:
        # not rational (2**x + 3**x is a "polynomial" in the generator 2**x for Poly, whose real roots it
        # cannot isolate): an equation of the exact classes (sandbox.exactsets.class_solveset: one
        # trigonometric function, one strictly monotone function or a same-frequency sin/cos combination,
        # of a linear argument; products) has its set in closed form, on the bounded hull of the domain
        # when there is one, never from a numeric search. On ℝ the solvers give the principal roots and
        # an ImageSet, so the right {pi/4, 5*pi/4, 9*pi/4} of tan x = 1 on [0, 10) was refuted before
        # (fourth audit G2); (1/2)**x = 4 was left to the two solvers, whose -2 and -log(4)/log(2) did not
        # agree as written, and sin x - cos x = 2 to their complex roots (round 4 of part d4b)
        rc = sb_run("mathverify.sandbox.exactsets:class_solveset", rel_r, var,
                    sp.Interval(*hull) if hull is not None else S.Reals, timeout=timeout)
        if rc.ok and (rc.value is S.EmptySet or isinstance(rc.value, FiniteSet)):
            window_set = list(rc.value)
            cands += window_set
            window_how = "exact_class" if hull is None else "exact_class_on_bounded_hull"
            ev["class_set"] = [str(c) for c in window_set]
        elif rc.ok and isinstance(rc.value, sp.Set) and not rc.value.has(ConditionSet):
            # an exact set with an interval in it (Max(log x, 0) = 0 on (0, 1]): no finite claim is it,
            # unless the domain leaves finitely many of its points (on the integers, {1}): those are the set
            on_dom = _finite_points(rc.value, domain)
            if on_dom is not None:
                window_set = on_dom
                cands += window_set
                window_how = "exact_class_met_with_the_domain"
                ev["class_set"] = [str(c) for c in window_set]
            else:
                try:                           # oo.is_positive is False; a finite set's measure is a Python 0
                    infinite = sp.Intersection(rc.value, domain).measure.is_extended_positive is True
                except Exception:  # noqa: BLE001
                    infinite = False
                if infinite:
                    ev["class_set_infinite"] = str(rc.value)
    # de-duplicate: exactly equal only (an undecided pair stays two candidates; the guard
    # decides each). Exact real roots first, so they are the representatives kept.
    uniq: list = []
    for c in poly_roots + cands:
        if not any(scalar_equal(c, u) is True for u in uniq):
            uniq.append(c)
    kept, rejected = guard_roots(rel, var, uniq, domain)
    ev["rejected"] = [(str(c), why) for c, why in rejected]
    ev["kept"] = [str(c) for c in kept]
    if window_set is not None:
        complete = not any(_undecided(why) for _, why in rejected) and all(
            any(scalar_equal(k, w) is True for w in window_set) for k in kept)
        ev["completeness_method"] = window_how
        ev["complete"] = complete
    elif p is not None and poly_roots is not None and (p.domain.is_Exact and "numerator_real_roots" in ev):
        undecided = [c for c, why in rejected if _undecided(why)]
        complete = not undecided
        ev["completeness_method"] = "exact_real_roots_of_numerator"
        ev["complete"] = complete
    else:
        # no exact class: the solvers' roots are candidates only. Two solvers agreeing is no proof of
        # completeness either (they share blind spots: 3**x = 2**x was certified {0} from solve and
        # solveset agreeing; round 5 of part d4b, 2 Oct 2026). Before, √(x − a) = √(2 − x) with a free
        # had its root a/2 + 1 undecided and ∅ certified that way (part vi, 30 Sep 2026)
        ev["complete"] = None
        ev["completeness_method"] = ("none (odd roots read as real roots)" if odd_rewritten
                                     else "none (no exact class)")
    return kept, ev


def _finite_points(exact: sp.Set, domain: sp.Set) -> list | None:
    """The points of an exact set the domain leaves, when they are finitely many (at most 400) and listed
    exactly: (0, 1] on the integers is [1]. None otherwise (also when SymPy cannot meet the two)."""
    try:
        on = exact_intersection(exact, domain)
        if isinstance(on, sp.Range) and on.size.is_finite and on.size <= 400:
            on = FiniteSet(*on)
    except Exception:  # noqa: BLE001
        return None
    if on is S.EmptySet:
        return []
    if isinstance(on, FiniteSet) and all(getattr(p, "is_number", False) for p in on):
        return list(on)
    return None


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
    from ..equiv.forms import has_closed_form
    from ..normalize.parse import ParseError, parse_relation, read_condition
    rels: list = []
    for src in ctx.ir.givens:
        # `x > 0 and x < 3`, `x in (0, 3)`, `x < -3 or x > 1`: read as a condition, never dropped; one read
        # as no condition raises and the certificate abstains (fourth audit G1). A text that reads as a
        # relation is read as before (`Ctx.rel`, its closed forms confirmed by numbers)
        g = read_condition(src, ctx.ns)
        try:
            parse_relation(src, ctx.ns)
            g = ctx.rel(src)
        except ParseError:
            if has_closed_form(g):
                raise ParseError(f"a closed form in the condition {src!r}: not confirmed here") from None
        if g != exclude and var in getattr(g, "free_symbols", set()):
            rels.append(g)
    rels, unbound = ctx.on_var(rels, var)
    # a chain or an And: each relation alone (solveset reads no conjunction, and the chain 0 < x < 3 left
    # the domain unsolved). An Or or a membership is a side condition `Ctx.domain_for` has applied (or the
    # verifier abstained on it: given_not_applied)
    plain = [a for g in rels for a in (g.args if isinstance(g, And) else (g,))
             if isinstance(a, sp.core.relational.Relational)]
    dom = ctx.cut_by(var, dom, [real_odd_roots(a) for a in plain])
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
    # where the value of the problem's expressions is a convention (an odd root of a negative base,
    # 0**0, C(n, r) outside 0 <= r <= n, Mod by a non-positive divisor, a reversed Sum range): a root
    # there is neither kept nor dropped, a root of the rest of the domain missing from the claim still
    # refutes it, and nothing is certified complete (DECISIONS §80; part d4a: C(n, 2) = 3 was UNKNOWN
    # for {-2} and the empty set, which miss the root 3 under every reading)
    from .domain import is_convention
    conv = [c for c in unbound if isinstance(c, sp.Basic) and is_convention(c) and c.free_symbols <= {var}]
    unbound = [c for c in unbound if not any(c is k for k in conv)]
    if unbound:
        return condition_not_applied(LAYER, unbound)
    if dom is None:
        return unknown(LAYER, "given_inequality_not_solvable")
    ev: dict[str, Any] = {"claimed": str(claimed), "domain": str(dom)}
    region = ctx.convention_region(var) if conv else S.EmptySet
    if conv:
        ev["convention_region"] = str(region)
    if not isinstance(claimed, FiniteSet):
        roots, sev = solve_guarded(rel, var, dom, ctx.timeout)
        ev["solve_guarded"] = sev
        if sev.get("identity"):
            if conv:
                return unknown(LAYER, "convention_region_candidates", 0, ev)
            return _verify_identity(rel, var, dom, claimed, ev, ctx, t)
        if claimed is S.EmptySet:
            if roots or sev.get("class_set_infinite"):
                ev["reason"] = "solutions_exist"
                return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
            if sev.get("complete") and not conv:
                return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
            return unknown(LAYER, "convention_region_candidates" if conv else "completeness_unknown", 0, ev)
        return unknown(LAYER, "claimed_set_not_finite", 0, ev)
    # (1) every claimed root must satisfy the original relation + definedness + domain
    kept, rejected = guard_roots(rel, var, list(claimed.args), dom)
    if conv:
        # a claimed root where the value is a convention: undecided, not outside the domain
        rejected = [(c, "definedness_undecided: convention" if w == "outside_domain_of_discourse"
                     and in_domain(region, c) is not False else w) for c, w in rejected]
    ev["claimed_check"] = {"kept": [str(k) for k in kept], "rejected": [(str(c), w) for c, w in rejected]}
    hard_bad = [(c, w) for c, w in rejected if not _undecided(w)]
    if hard_bad:
        ev["reason"] = f"claimed_root_invalid: {hard_bad[0][1]}"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    if rejected and not conv:
        return unknown(LAYER, "claimed_root_undecided", 0, ev)
    # (2) completeness: are there true roots missing from the claim? (with a claimed root where the
    # value is a convention too: a root of the rest of the domain the claim misses refutes it)
    roots, sev = solve_guarded(rel, var, dom, ctx.timeout)
    ev["solve_guarded"] = sev
    if sev.get("identity"):
        if conv:
            return unknown(LAYER, "convention_region_candidates", 0, ev)
        return _verify_identity(rel, var, dom, claimed, ev, ctx, t)
    if sev.get("class_set_infinite") and not conv:
        ev["reason"] = "solution_set_infinite"
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
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
    if rejected:
        return unknown(LAYER, "claimed_root_undecided", 0, ev)
    if conv:
        return unknown(LAYER, "convention_region_candidates", 0, ev)
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
    # the endpoints proved equal written one way (round 7, RK6: (3, 4) against dom (log(8)/log(2), oo))
    inside = [pt[var] for pt in sample_points({var: exact_intersection(claimed_set, dom)}, n, seed, special=True)]
    outside_set = exact_complement(dom, claimed_set)
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
    from .domain import is_convention
    cond_unsolved: list = []
    for c in definedness_conditions(rel, var):
        # a trigonometric one on the domain the others leave (on ℝ: one period, sandbox.exactsets)
        rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, dom if at_risk(c, var) else S.Reals,
                    timeout=ctx.timeout)
        if rr.ok and isinstance(rr.value, sp.Set) and not rr.value.has(ConditionSet):
            dom = exact_intersection(dom, rr.value)
        elif not is_convention(c):
            # never dropped: x + atan(x) <= 1 of an asin left the domain all of x >= 0 and [0, oo) was
            # certified for (|x| - x)*asin(x + atan(x)) <= 0 (round 8 of part d4b, YO-1). A sampled
            # counterexample still refutes (the points are checked as written); no set is compared
            cond_unsolved.append(c)
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
    if ctx.unsolved_conditions(var):
        # the domain is cut by a trigonometric condition with no closed form on ℝ (the written
        # cos(x) != 0 of tan x): the solution set is no set the comparison reads (fourth audit G2)
        return condition_unsolved(LAYER, ctx.unsolved_conditions(var), 0, ev)
    if cond_unsolved:
        return condition_unsolved(LAYER, cond_unsolved, 0, ev)
    truth, r = dom, None
    flat: list = []
    for one in rels:
        flat.extend(one.args if isinstance(one, And) else [one])     # a chained 1 < x < 5
    # a relation with a trigonometric function last, on the set the others leave: on ℝ SymPy reads it
    # on one period (sandbox.exactsets), on a bounded set it is rebuilt and checked
    flat = [o for o in flat if not at_risk(o, var)] + [o for o in flat if at_risk(o, var)]
    for one in flat:
        r = sb_run("mathverify.sandbox.ops:solveset_in", one, var, truth if at_risk(one, var) else dom,
                   timeout=ctx.timeout)
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
    x + gcd(x, 2) - gcd(2, x) at pi + E was certified (V16, 30 Sep 2026). So is one where a Sum/Product
    range of the problem runs backwards (`Ctx.reversed_region`, DECISIONS §80): with n**2 = 4, n = -2 was
    dropped and the value 3 of Σ_{k=1}^{n} k certified (1 Oct 2026). A solution some other check
    drops is dropped."""
    from .domain import decide_membership
    out = []
    cons = ctx.var_constraints()
    for s_ in sols:
        ok, held = True, False
        for v in ctx.syms():
            if v in s_:
                val = s_[v]
                if val.free_symbols:
                    continue
                if val.is_real is False:
                    ok = False
                    break
                d = in_domain(ctx.domain_for(v), val)
                if d is None:
                    # no exact check decides the membership (x = 2*(atan(1/3) + ...) = pi against x > pi):
                    # neither kept nor dropped (fourth audit G10); kept, a contradicted IR was certified
                    held = True
                    continue
                if d is False:
                    if undecided is not None and in_domain(ctx.reversed_region(v), val) is not False:
                        held = True
                        continue
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
                        if m is False:
                            ok = False
                            break
                        if m is None and undecided is not None:
                            held = True
                            continue
                    if isinstance(h, (sp.core.relational.Relational, sp.And, sp.Or)) and not h.free_symbols:
                        hv = relation_holds_at(h, sp.Symbol("_dummy"), 0)
                        if hv is False:
                            ok = False
                            break
                        if hv is None:
                            held = True
                except Exception:
                    held = True                         # a constraint no check reads at the solution
        if ok and held:
            if undecided is None:
                continue                                # neither kept nor dropped: not a solution here
            undecided.append(s_)
        elif ok:
            out.append(s_)
    return out


def _finite_nonempty(s_: sp.Set) -> bool:
    try:
        return s_ is not S.EmptySet and s_.is_finite_set is True and s_.is_empty is False
    except Exception:  # noqa: BLE001
        return False


def _meets_inequalities(s_: dict, ineqs: list) -> bool | None:
    """Does the solution `s_` satisfy every given inequality? False when one is proved false, None when
    one is decided by no exact check (a chain or an Or too): the solution is then neither kept nor
    dropped. An undecided one counted as satisfied, and with x = 2*(atan(1/3) + ...) (= pi exactly) and
    the given x > pi the value 7 of y = 7 was certified (fourth audit G10)."""
    out: bool | None = True
    for iq in ineqs:
        h = iq.subs(s_)
        if h is sp.false:
            return False
        if h is sp.true or getattr(h, "free_symbols", None):
            continue
        hv = relation_holds_at(h, sp.Symbol("_d"), 0)
        if hv is False:
            return False
        if hv is None:
            out = None
    return out


def _algebraic(eq, syms) -> bool:
    """Is lhs - rhs a rational function of `syms` (exact coefficients)?"""
    try:
        num, den = sp.fraction(sp.together(eq.lhs - eq.rhs))
        pn, pd = sp.Poly(num, *syms), sp.Poly(den, *syms)
    except Exception:  # noqa: BLE001
        return False
    return pn.domain.is_Exact and pd.domain.is_Exact and not pn.free_symbols_in_domain & set(syms) \
        and not pd.free_symbols_in_domain & set(syms)


def _complete_solutions(eqs, ineqs, syms, sols, ctx: Ctx) -> tuple[list | None, str]:
    """The solutions of the given equations, when the list is PROVED complete; None otherwise.

    `solve`'s list is no proof: on a periodic equation it gives the principal solutions only (sin x = 0
    → [0, pi]), so with 3 < x < 7 the value -1 of cos x was certified though x = 2*pi gives 1, and
    pi/4 for x with tan x = 1, 0 < x < 4 though 5*pi/4 < 4 (fourth audit G5); on x*exp(x) = -1/5 it
    gives both LambertW branches but nothing says so. A system of rational equations keeps `solve`'s
    list (it solves those completely). One unknown: the solution set of an equation, on the bounded
    hull of the region the other givens and the domain leave when there is one, must be a finite set of
    an equation whose class proves it complete (sandbox.exactsets.class_solveset: rational, one
    trigonometric function or same-frequency sin/cos combination, one strictly monotone function, of a
    linear argument, and products of these). SymPy's finite set of any other equation is no proof:
    exp(x) = 3*x is W0 and W-1, sqrt and Abs equations go through branches (review of 2 Oct 2026:
    (x + 1)*Q = 0 with 0 < x < 4 gave pi/3 CORRECT, pi is a root too). The other equations are then
    checked at each of its points. Several unknowns: a rational system (`_polynomial_system_worker`)."""
    if all(_algebraic(e, syms) for e in eqs) and len(syms) > 1:
        r = sb_run("mathverify.certify.algebra:_polynomial_system_worker", eqs, syms, timeout=ctx.timeout)
        if not r.ok:
            return None, f"system_completeness_failed: {r.error}"
        out, how = r.value
        return out, how
    if len(syms) != 1:
        return None, "transcendental_system_in_several_unknowns"
    v = syms[0]
    region = ctx.cut_by(v, ctx.domain_for(v), [real_odd_roots(g) for g in ineqs
                                                 if getattr(g, "free_symbols", set()) == {v}])
    window = S.Reals
    if region is not None:
        try:
            lo, hi = region.inf, region.sup
            if lo.is_finite and hi.is_finite and lo.is_number and hi.is_number:
                window = sp.Interval(lo, hi)
        except Exception:  # noqa: BLE001 - an unsolved condition: no hull
            pass
    found = None
    for e in eqs:
        er = real_odd_roots(e)
        # the exact classes only (sandbox.exactsets.class_solveset): a rational equation, one trigonometric
        # function or a same-frequency sin/cos combination of a linear argument, one strictly monotone
        # function (exp, a**x, log, sinh, atan) of a linear argument, and products of these
        # On all of ℝ first: a finite set there leaves every point to `_filter_solutions`, which knows the
        # candidates a convention decides (a reversed range: with n**2 = 4, n < 3 the hull of n's domain
        # is [0, 2] and n = -2 was dropped there, so the value 3 of Σ_{k=1}^{n} k was certified); the
        # hull only for a set that is infinite on ℝ (a periodic equation)
        for w in ([S.Reals, window] if window != S.Reals else [S.Reals]):
            rr = sb_run("mathverify.sandbox.exactsets:class_solveset", er, v, w, timeout=ctx.timeout)
            if rr.ok and (rr.value is S.EmptySet or isinstance(rr.value, FiniteSet)):
                found = (e, list(rr.value))
                break
        if found is not None:
            break
    if found is None:
        return None, f"no_equation_with_a_finite_proved_solution_set_on {window}"
    out = []
    for c in found[1]:
        holds = [relation_holds_at(e, v, c) for e in eqs if e is not found[0]]
        if any(h is None for h in holds):
            return None, f"equation_undecided_at {c}"
        if all(holds):
            out.append({v: c})
    return out, f"solveset_on {window}"


_MAX_STANDARD_MONOMIALS = 20000


def _is_zero_algebraic(z) -> bool | None:
    """Is the algebraic number z zero? Its minimal polynomial decides it (that of 0 is the variable
    itself); None when it is not computed (z not algebraic, or too hard)."""
    if z == 0:
        return True
    try:
        t = sp.Dummy("t")
        return sp.minimal_polynomial(z, t) == t
    except Exception:  # noqa: BLE001
        return None


def _is_real_algebraic(v) -> bool | None:
    """Is the algebraic number v real? v is one root of its minimal polynomial m; the roots of m are
    isolated exactly (CRootOf, which knows whether each is real), and v's value to 50 digits must lie
    nearer to one of them than a tenth of their least separation: that root is v. No sign is read off
    a rounded imaginary part (Cardano's form of a real root has one). None when undecided."""
    try:
        t = sp.Dummy("t")
        m = sp.Poly(sp.minimal_polynomial(v, t), t)
        if m.degree() == 1:
            return True
        roots = m.all_roots()
        approx = [complex(sp.N(r_, 50)) for r_ in roots]
        sep = min(abs(a - b) for i, a in enumerate(approx) for b in approx[i + 1:])
        x = complex(sp.N(v, 50))
        near = [r_ for r_, a in zip(roots, approx) if abs(a - x) < sep / 10]
        if len(near) != 1:
            return None
        return bool(near[0].is_real)
    except Exception:  # noqa: BLE001
        return None


def _polynomial_system_worker(eqs, syms):
    """Worker: (the real solutions of a rational system in several unknowns, how), the list None unless
    it is PROVED complete. `solve`'s list for such a system is no proof by itself, so:
    - a linear system (constant denominators): `solve` solves it completely, parametric when
      underdetermined (Gaussian elimination);
    - otherwise the numerators must span a zero-dimensional ideal I (lex Gröbner basis). For each unknown
      the ideal holds a polynomial in that unknown alone (the elimination polynomial); I plus their
      square-free parts is the radical of I (Seidenberg's lemma), and the dimension of the quotient by
      it (its standard monomials) is the number of distinct complex solutions. `solve` (over the
      complex numbers) must give as many points, each proved a solution and proved distinct from the
      others (minimal polynomials of algebraic numbers): then none is missing.
    The non-real points and those where a denominator vanishes are dropped; a point whose realness or
    denominator no check decides leaves the list unproved."""
    plain = [sp.Dummy(str(v)) for v in syms]
    back = dict(zip(plain, syms))
    nums, dens = [], []
    for e in eqs:
        n, d = sp.fraction(sp.together((e.lhs - e.rhs).xreplace(dict(zip(syms, plain)))))
        nums.append(sp.expand(n))
        dens.append(d)
    polys = [sp.Poly(n, *plain) for n in nums if n != 0]
    if not polys:
        return None, "identity_system"
    if all(p.total_degree() <= 1 for p in polys) and all(not (d.free_symbols & set(plain)) for d in dens):
        out = []
        for s_ in sp.solve(nums, plain, dict=True):
            real = [_is_real_algebraic(v) for v in s_.values() if not v.free_symbols]
            if any(r_ is None for r_ in real):
                return None, "realness_undecided"
            if all(real):
                out.append({back[k]: v.xreplace(back) for k, v in s_.items()})
        return out, "linear_system"
    G = sp.groebner(polys, *plain, order="lex")
    if list(G.exprs) == [1]:
        return [], "inconsistent_system"
    extra = []                  # each unknown has a polynomial in it alone iff the ideal is zero-dimensional
    for j, x in enumerate(plain):
        order = plain[:j] + plain[j + 1:] + [x]
        Gj = sp.groebner(polys, *order, order="lex")
        elim = [g for g in Gj.exprs if g.free_symbols <= {x}]
        if not elim:
            return None, f"system_not_zero_dimensional: no polynomial in {back[x]} alone"
        extra.append(sp.sqf_part(elim[0], x))
    R = sp.groebner(polys + [sp.Poly(q, *plain) for q in extra], *plain, order="lex")
    lms = [p.monoms(order="lex")[0] for p in R.polys]
    bounds = []
    for j in range(len(plain)):
        pure = [m[j] for m in lms if all(k == 0 for i, k in enumerate(m) if i != j)]
        bounds.append(min(pure))
    total = 1
    for b in bounds:
        total *= b
    if total > _MAX_STANDARD_MONOMIALS:
        return None, "quotient_too_large"
    import itertools
    dim = sum(1 for m in itertools.product(*[range(b) for b in bounds])
              if not any(all(m[i] >= l_[i] for i in range(len(plain))) for l_ in lms))
    found = []
    for s_ in sp.solve(nums, plain, dict=True):
        if set(s_) != set(plain) or any(v.free_symbols for v in s_.values()):
            return None, "solve_gave_a_non_point"
        for n in nums:
            z = _is_zero_algebraic(sp.expand(n.xreplace(s_)))
            if z is not True:
                return None, "solve_point_not_proved_a_solution"
        same = False
        for u in found:
            eq_ = [_is_zero_algebraic(s_[x] - u[x]) for x in plain]
            if any(q is None for q in eq_):
                return None, "solve_points_not_proved_distinct"
            if all(eq_):
                same = True
                break
        if not same:
            found.append(s_)
    if len(found) != dim:
        return None, f"solve_found_{len(found)}_of_{dim}_solutions"
    out = []
    for s_ in found:
        real = [_is_real_algebraic(s_[x]) for x in plain]
        if any(r_ is None for r_ in real):
            return None, "realness_undecided"
        if not all(real):
            continue
        zero = [_is_zero_algebraic(sp.expand(d.xreplace(s_))) for d in dens if d.free_symbols & set(plain)]
        if any(z is None for z in zero):
            return None, "denominator_undecided"
        if not any(zero):
            out.append({back[x]: s_[x] for x in plain})
    return out, f"zero_dimensional_ideal_{dim}_solutions"


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
        if dom and ok is not False:
            ok = _beyond_value_conventions(ctx, claimed, target, sorted(dom, key=lambda s_: s_.name), ok, ev)
        # a variable the problem confines to finitely many values where a range runs backwards
        # (the constraint n**2 = 4 next to Σ_{k=1}^{n} k): those values are candidates, neither kept
        # nor dropped (_filter_solutions); a formula's variable (n an integer) is compared where the
        # value is no convention (DECISIONS §80)
        if ok is True and dom and any(_finite_nonempty(ctx.reversed_region(s_)) for s_ in dom):
            ev["reversed_range_at"] = {str(s_): str(ctx.reversed_region(s_)) for s_ in dom}
            return unknown(LAYER, "reversed_range_candidate", 0, ev)
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
        if any(real_odd_roots(e) != e for e in eqs) and any(
                ctx.convention_region(s_).is_empty is not True for s_ in syms):
            # an odd root written as a power where its base may be negative: SymPy solves on the
            # principal branch, the real root has other solutions (x**(1/3) = x, x != 0: {1} and
            # {-1, 1}), and `solve` misses them in sign(x)·|x|**(1/3) form too. With candidates where
            # the value is a convention not all known, no value is unique (part d4a)
            ev["raw_solutions"] = [{str(k): str(v) for k, v in s_.items()} for s_ in sols]
            return unknown(LAYER, "odd_root_convention_candidates", 0, ev)
        ev["raw_solutions"] = [{str(k): str(v) for k, v in s_.items()} for s_ in sols]
        sols, how = _complete_solutions(eqs, ineqs, syms, sols, ctx)
        ev["completeness"] = how
        if sols is None:
            return unknown(LAYER, f"solution_set_not_proved_complete: {how}", 0, ev,
                           flags=["completeness_uncertified"])
        # keep solutions satisfying inequalities/constraints/domains
        undecided: list = []
        admissible = _filter_solutions(sols, ctx, undecided)
        # one a given inequality excludes is no solution either way (n**2 = 4, n > 0)
        undecided = [s_ for s_ in undecided if _meets_inequalities(s_, ineqs) is not False]
        undecided += [s_ for s_ in admissible if _meets_inequalities(s_, ineqs) is None]
        if undecided:
            ev["membership_undecided"] = [{str(k): str(v) for k, v in s_.items()} for s_ in undecided]
            return unknown(LAYER, "solution_membership_undecided", 0, ev)
        good = [s_ for s_ in admissible if _meets_inequalities(s_, ineqs) is True]
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


def _beyond_value_conventions(ctx: Ctx, claimed, truth, syms, ok, ev: dict):
    """The comparison's verdict once the points `domain_for` left out because a value of the problem is
    another value there under the other convention are read too (`convention_counterexample`): refuted
    where both readings differ, otherwise never certified (part d4a, attack A: Abs(x) for (x**3)**(1/3)
    was CORRECT, it is wrong at x = -2 under both readings; cbrt(x) for x**(1/3) holds under one)."""
    from .base import convention_counterexample
    present, pt = convention_counterexample(ctx, claimed, truth, syms)
    if not present:
        return ok
    if pt is not None:
        ev["reason"] = "differs_where_a_value_is_a_convention"
        ev["counterexample_both_readings"] = pt
        return False
    ev["value_convention_region"] = {str(s_): str(ctx.value_convention_region(s_)) for s_ in syms
                                     if ctx.ns.get(s_.name) == s_}
    return None


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
        empty = set_is_empty(rr.value)
        if empty is None:
            # a set of progressions SymPy cannot decide (sandbox.exactsets): no proof either way
            return None, f"claim_condition_undecided: {c} on {rr.value}"
        if not empty:
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
    if ok is not False:
        ok = _beyond_value_conventions(ctx, claimed, expr, syms, ok, ev)
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
