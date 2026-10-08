"""Part 9 of 30 Sep 2026 (DECISIONS §80, "Ters toplam aralığı"; §79 Karr): a reversed symbolic range
decides nothing.

§79 made a Sum/Product with a symbolic bound need hi - lo + 1 >= 0, and a point where that fails was
dropped like a point where the expression is undefined. Below the empty range (hi < lo - 1) the value is
a convention, not undefined: SymPy's Karr sum gives one number, the empty-sum reading 0, the curriculum
none. Dropping the point picked a convention: with n**2 = 4 (n an integer) Σ_{k=1}^{n} k = 3 was CORRECT
because n = -2 was dropped, and Σ = 6 → {3} lost its Karr root -4 the same way. Now the range condition
is `Contains(hi - lo + 1, FORWARD_SPANS)`, undecided at a reversed point; `Ctx.domain_for` keeps only the
forward points (an expression is still compared where its value is no convention), and a candidate, root
or solution where the range runs backwards is neither kept nor dropped (`Ctx.reversed_region`,
`algebra._filter_solutions`, `Ctx.unapplied_conditions`). hi = lo - 1 (the empty sum, n = 0 -> 0) stays
defined. Measured on the code before the change (351f901): see the commit message for how many fail.
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.verifier import verify

K = {"name": "k", "domain": "integer"}
KN = [K, {"name": "n", "domain": "integer"}]
KP = [K, {"name": "n", "domain": "positive_integer"}]
K0 = [K, {"name": "n", "domain": "nonneg_integer"}]
KU = [K, {"name": "n"}]
S = "Sum(k, (k, 1, n))"


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def _ev(expr, givens=(), vars_=KN):
    return _ir("evaluate", {"expr": expr}, vars_, givens)


def _solve(eq, vars_=KN, givens=()):
    return _ir("solve_equation", {"var": "n", "equation": eq}, vars_, givens, shape="set")


def _constrained(*cons):
    return [K, {"name": "n", "domain": "integer", "constraints": list(cons)}]


def _verdict(ir, claim):
    kind = "set" if ir["answer_shape"] == "set" else "value"
    if ir["task"]["kind"].startswith("count"):
        kind = "count"
    return verify(ir, _sol(claim, kind)).verdict


# ---------------------------------------------------------------------------- a root in the reversed region
@pytest.mark.parametrize("ir,claim", [
    # n = -2: Karr's 1, the empty sum's 0, the curriculum none
    (_ev(S, ["n**2 = 4"]), "3"),
    (_ev(S, ["n**2 = 4"]), "1"),
    (_ev(S, ["n**2 = 4"]), "0"),
    (_ev(S, ["n**2 = 4"], KU), "3"),
    (_ev(S, ["n**2 - 4 = 0"]), "3"),
    (_ev(f"2*{S} + n", ["n**2 = 4"]), "8"),
    (_ev(r"\sum_{k=1}^{n} k", ["n**2 = 4"]), "3"),
    (_ev(S, ["n**2 = 9"]), "6"),
    # n = -1: Karr and the empty sum agree on 0, the curriculum still has none
    (_ev(S, ["n**2 = 1"]), "1"),
    (_ev(S, ["n*(n + 1) = 0"]), "0"),
    # the larger root is the reversed one
    (_ev("Sum(k, (k, n, 1))", ["n**2 = 9"]), "-5"),
    (_ev("Sum(k, (k, n, 0))", ["n**2 = 4"]), "-3"),
    # a Product: Karr's 1/90 at n = -2, the empty product's 1
    (_ev("Product(k + 10, (k, 1, n))", ["n**2 = 4"]), "132"),
    (_ev("Product(k + 10, (k, 1, n))", ["n**2 = 4"]), "1/90"),
    # a given inequality that leaves the reversed root in; the bound in a second symbol
    (_ev(S, ["n**2 = 4", "n < 3"]), "3"),
    (_ev("Sum(k, (k, 1, m))", ["m = n - 1", "n**2 = 4"], KN + [{"name": "m", "domain": "integer"}]), "1"),
    (_ev(f"x + {S}", ["n = -2", "x = 1"], KN + [{"name": "x"}]), "2"),
    # the lower bound fixed by a given: n = 4 is the empty sum (0), n = -4 runs backwards
    (_ev("Sum(k, (k, m, n))", ["m = 5", "n**2 = 16"], KN + [{"name": "m", "domain": "integer"}]), "0"),
    # other bounds: floor(-2/2) = -1 and (-2)**3 = -8 run backwards
    (_ev("Sum(k, (k, 1, floor(n/2)))", ["n**2 = 4"]), "1"),
    (_ev("Sum(k, (k, 1, n**3))", ["n**2 = 4"]), "36"),
    # constraints that confine n to finitely many values, some reversed: candidates too
    (_ev(S, [], _constrained("n**2 = 4")), "3"),
    (_ev(S, [], _constrained("n**2 = 4")), "n + 1"),
    (_ev(S, [], _constrained("n >= -5", "n <= 5")), "n*(n + 1)/2"),
])
def test_a_value_that_rests_on_a_reversed_range_is_not_certified(ir, claim):
    assert _verdict(ir, claim) == "UNKNOWN"


# ---------------------------------------------------------------------------- an equation in the bound
@pytest.mark.parametrize("ir,claim", [
    # Karr's n(n + 1)/2 = 6 has the root -4, the empty sum is 0 there
    (_solve(f"{S} = 6"), "{3}"),
    (_solve(f"{S} = 6"), "{-4, 3}"),
    (_solve(f"{S} = 0"), "{0}"),
    (_solve(f"{S} = 0"), "{-1, 0}"),
    # the Sum cancels as written: n = -2 solves the equation under any value of the sum
    (_solve(f"n**2 - 4 + {S} - {S} = 0"), "{2}"),
    (_solve(f"n**2 - 4 + {S} - {S} = 0"), "{-2, 2}"),
    (_solve(f"n**2 = 4 + {S} - {S}"), "{2}"),
    (_solve(f"n**2 = 4 + {S} - {S}", KU), "{2}"),
    (_solve("n**2 = 4 + Product(k + 10, (k, 1, n)) - Product(k + 10, (k, 1, n))"), "{2}"),
    (_solve(f"(n - 2)*(n + 3) = {S} - {S}"), "{2}"),
    (_ir("count_roots", {"var": "n", "expr": f"n**2 - 4 + {S} - {S}"}, KN), "1"),
    (_ir("count_roots", {"var": "n", "expr": f"n**2 - 4 + {S} - {S}"}, KN), "2"),
    (_ir("solve_inequality", {"var": "n", "inequality": f"n**2 < 5 + {S} - {S}"}, KN, shape="set"),
     "{-2, -1, 0, 1, 2}"),
    (_ir("solve_inequality", {"var": "n", "inequality": f"n**2 < 5 + {S} - {S}"}, KN, shape="set"), "{0, 1, 2}"),
    # an equation in x, the range reversed for certain by the given n = -2
    (_ir("solve_equation", {"var": "x", "equation": f"x + {S} = 0"}, KN + [{"name": "x"}], ["n = -2"], "set"),
     "EmptySet"),
    (_ir("solve_equation", {"var": "x", "equation": f"x + {S} = 0"}, KN + [{"name": "x"}], ["n = -2"], "set"),
     "{0}"),
])
def test_a_solution_set_that_rests_on_a_reversed_range_is_not_certified(ir, claim):
    assert _verdict(ir, claim) == "UNKNOWN"


def test_a_solution_resting_on_a_reversed_range_is_not_certified_through_steps():
    ir = _ev(S, ["n**2 = 4"])
    assert verify(ir, _sol("3", steps=[("eq", "n = 2"), ("compute", f"{S} = 3")])).verdict == "UNKNOWN"


# ---------------------------------------------------------------------------- what does not change
@pytest.mark.parametrize("ir,claim,verdict", [
    (_ev(S, ["n = 3"]), "6", "CORRECT"),
    (_ev(S, ["n = 3"]), "5", "INCORRECT"),
    (_ev(S, ["n = 0"]), "0", "CORRECT"),                       # hi = lo - 1: the empty sum
    (_ev(S, ["n = 0"]), "1", "INCORRECT"),
    (_ev(S, ["n = -1"]), "0", "UNKNOWN"),                      # reversed for certain
    (_ev(S, ["n = -2"]), "1", "UNKNOWN"),
    (_ev(S, ["n = -2"]), "0", "UNKNOWN"),
    (_ev(S, ["n**2 = 4", "n > 0"]), "3", "CORRECT"),           # the inequality excludes the reversed root
    (_ev(S, ["n**2 = 4", "n > 0"]), "1", "INCORRECT"),
    (_ev(S, ["n**2 = 4", "n >= 0"]), "3", "CORRECT"),
    (_ev(S, ["n**2 = 4"], KP), "3", "CORRECT"),                # declared positive: never reversed
    (_ev(S, ["n**2 = 4"], K0), "3", "CORRECT"),
    (_ev(S, ["n = 3"], KP), "6", "CORRECT"),
    (_ev(S, ["n = 3"], KU), "6", "CORRECT"),
    (_ev("Sum(k, (k, 1, n**2))", ["n**2 = 4"]), "10", "CORRECT"),
    (_ev("Sum(k, (k, 1, Abs(n)))", ["n**2 = 4"]), "3", "CORRECT"),
    (_ev("Sum(k, (k, 1, floor(n/2)))", ["n = 4"]), "3", "CORRECT"),
    (_ev("Sum(k, (k, n, n + 2))", ["n = -5"]), "-12", "CORRECT"),
    (_ev(S, ["n*(n - 3) = 0"]), "6", "UNKNOWN"),               # two forward values, 0 and 6
    (_ev("n**2 + 1", ["n**2 = 4"]), "5", "CORRECT"),
    (_ev("Product(k, (k, 3, n))", ["n = 2"]), "1", "CORRECT"),
    (_ev("Sum(k, (k, m, n))", ["m = 5", "n = 4"], KN + [{"name": "m", "domain": "integer"}]), "0", "CORRECT"),
    (_ev("Sum(k, (k, m, n))", ["m = 5", "n = 6"], KN + [{"name": "m", "domain": "integer"}]), "11", "CORRECT"),
    (_ev("Product(k, (k, 3, n))", ["n = 1"]), "1", "UNKNOWN"),
    # a formula's variable: compared where the value is no convention (§79's controls)
    (_ev(S), "n*(n + 1)/2", "CORRECT"),
    (_ev(S), "n**2/2", "INCORRECT"),
    (_ev(S, (), KP), "n*(n + 1)/2", "CORRECT"),
    (_ev(S, (), KU), "n*(n + 1)/2", "UNKNOWN"),          # n not declared an integer (review of d4f, YO-3)
    (_ir("simplify_expression", {"expr": S}, KN), "n*(n + 1)/2", "CORRECT"),
    (_ev(S, [], _constrained("n >= 0", "n <= 5")), "n*(n + 1)/2", "CORRECT"),
    (_solve(f"n**2 = 4 + {S} - {S}", KP), "{2}", "CORRECT"),
    (_solve(f"n**2 = 4 + {S} - {S}", KP), "{-2, 2}", "INCORRECT"),
    (_solve(f"n**2 = 4 + {S} - {S}", KN, ["n > 0"]), "{2}", "CORRECT"),
    (_ir("count_roots", {"var": "n", "expr": f"n**2 - 4 + {S} - {S}"}, KN, ["n > 0"]), "1", "CORRECT"),
    (_ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, [{"name": "x"}], shape="set"), "{-2, 2}",
     "CORRECT"),
    (_ev("Sum(1/k**2, (k, 1, oo))"), "pi**2/6", "CORRECT"),
    (_ev("Sum(2**k, (k, -oo, n))", ["n = 0"]), "2", "CORRECT"),
])
def test_what_the_reversed_range_does_not_touch(ir, claim, verdict):
    assert _verdict(ir, claim) == verdict


def test_steps_of_a_forward_instance_are_unchanged():
    r = verify(_ev("n**2", ["n = 3"]), _sol("9", steps=[("compute", f"{S} = 6")]))
    lay = next(l for l in r.layers if l.layer == "steps.refute")
    assert lay.evidence["steps"][0]["status"] == "verified"
    r = verify(_ev("n**2", ["n = 0"]), _sol("0", steps=[("compute", f"{S} = 0")]))
    lay = next(l for l in r.layers if l.layer == "steps.refute")
    assert lay.evidence["steps"][0]["status"] == "verified"


# ---------------------------------------------------------------------------- the solutions a given excludes
X = [{"name": "x"}]
G = "x + gcd(x, 2) - gcd(2, x)"


@pytest.mark.parametrize("ir,claim,verdict", [
    # pi + E is neither kept nor dropped (gcd's argument not proved rational), but x < 1 excludes it: the
    # verdict was UNKNOWN because the undecided solution was reported before the inequalities were read
    (_ev(G, ["(x - pi - E)*(x - 1/2) = 0", "x < 1"], X), "1/2", "CORRECT"),
    (_ev(G, ["(x - pi - E)*(x - 1/2) = 0", "x < 1"], X), "1", "INCORRECT"),
    (_ev(G, ["(x - pi - E)*(x - 1/2) = 0"], X), "1/2", "UNKNOWN"),
])
def test_an_undecided_solution_a_given_inequality_excludes_does_not_count(ir, claim, verdict):
    assert _verdict(ir, claim) == verdict


# ---------------------------------------------------------------------------- the pieces
def test_forward_spans_membership():
    from mathverify.certify.domain import FORWARD_SPANS, decide_membership, is_range_span, relation_holds_at
    n = sp.Symbol("n", integer=True)
    c = sp.Contains(n, FORWARD_SPANS)
    assert is_range_span(c) and not is_range_span(sp.Contains(n, sp.S.Integers)) and not is_range_span(n >= 0)
    assert c.subs(n, 3) is sp.true and c.subs(n, 0) is sp.true
    rev = c.subs(n, -2)
    assert isinstance(rev, sp.Contains) and not rev.free_symbols     # never false
    assert decide_membership(sp.Integer(-2), FORWARD_SPANS) is None
    assert decide_membership(sp.Integer(2), FORWARD_SPANS) is True
    assert relation_holds_at(c, n, sp.Integer(-2)) is None
    assert relation_holds_at(c, n, sp.Integer(5)) is True
    assert sp.Range(1, sp.oo).is_subset(FORWARD_SPANS) is True


def _ctx(ir):
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    return make_ctx(ProblemIR.from_dict(ir))


def test_the_domain_keeps_the_forward_points_and_names_the_reversed_ones():
    from mathverify.certify.domain import FORWARD_SPANS
    ctx = _ctx(_ev(S, ["n**2 = 4"]))
    n = ctx.sym("n")
    assert ctx.domain_for(n) == sp.Range(0, sp.oo)
    assert ctx.reversed_region(n) == sp.Range(-sp.oo, 0)
    # a certificate that reads its answer on the domain abstains, even one that checks the conditions
    # itself (guard_roots): the domain it checks a root against has left the reversed points out
    marker = sp.Contains(n, FORWARD_SPANS)
    assert ctx.unapplied_conditions(n) == [marker]
    assert ctx.unapplied_conditions(n, enforced=[marker]) == [marker]
    ctx = _ctx(_solve(f"n**2 = 4 + {S} - {S}", KN, ["n > 0"]))
    n = ctx.sym("n")
    assert ctx.reversed_region(n) is sp.S.EmptySet and ctx.unapplied_conditions(n) == []
    ctx = _ctx(_ev(S, ["n = 3"], KP))
    assert ctx.reversed_region(ctx.sym("n")) is sp.S.EmptySet
    ctx = _ctx(_ev(S, [], _constrained("n**2 = 4")))
    n = ctx.sym("n")
    assert ctx.domain_for(n) == sp.FiniteSet(2) and ctx.reversed_region(n) == sp.FiniteSet(-2)


def test_a_bound_a_given_fixes_is_read_as_its_value():
    ctx = _ctx(_ev("Sum(k, (k, m, n))", ["m = 5", "n**2 = 16"], KN + [{"name": "m", "domain": "integer"}]))
    n = ctx.sym("n")
    assert ctx.domain_for(n) == sp.Range(4, sp.oo)
    assert ctx.reversed_region(n) == sp.Range(-sp.oo, 4)


def test_filter_solutions_holds_a_reversed_solution():
    from mathverify.certify.algebra import _filter_solutions
    ctx = _ctx(_ev(S, ["n**2 = 4"]))
    n = ctx.sym("n")
    undecided: list = []
    kept = _filter_solutions([{n: sp.Integer(2)}, {n: sp.Integer(-2)}], ctx, undecided)
    assert kept == [{n: sp.Integer(2)}] and undecided == [{n: sp.Integer(-2)}]
    # without the list (no caller that can abstain) the old reading stays: dropped
    assert _filter_solutions([{n: sp.Integer(-2)}], ctx) == []
