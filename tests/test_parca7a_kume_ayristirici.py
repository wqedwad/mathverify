"""Part (v-b A) of 30 Sep 2026 (HANDOFF V16, DECISIONS §73 "Açık kalanlar"): the set and parser items.

(1) SymPy's set `+`/`-` built Union/Complement without the endpoint unification of `_set_op`: with
    R = sqrt(11 + 6*sqrt(2)) - sqrt(2) (= 3), Interval.open(-oo, R) + Interval.open(3, oo) was the whole
    line, CORRECT as the domain of x + 1 (and the right domain of 1/(x - 3) written so was INCORRECT).
(2) `normalize_set` sorted intervals by `float`: two starts 1e-40 apart tied and the interval listed
    first swallowed the other ([sqrt(2) - 2e-40, sqrt(2) - 1e-40) U (sqrt(2), 5) read as (sqrt(2), 5)).
(3) a Sum/Product bound that is a constant but no plain number (sqrt(1)) escaped the reversed-range check
    made before SymPy builds the binder, so floor(Sum(k, (k, 3, sqrt(1)))) = -2 (Karr) was certified.
(5) the gcd/lcm "not a value" check (GCD-10) was skipped for a set written as a list.
(6) the 300-constant limit of `unify_endpoints` counts rationals too, on purpose (it bounds the size of a
    set written as text); these tests pin it.
Measured on the code before the change (20d4edf): see the commit message for how many of these fail.
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.equiv.sets import normalize_set
from mathverify.normalize.parse import ParseError, _SAFE_NAMES, parse_as_written, parse_expr_str, parse_set_str
from mathverify.verifier import verify

X = [{"name": "x"}]
KI = [{"name": "k", "domain": "integer"}]
R = "(sqrt(11 + 6*sqrt(2)) - sqrt(2))"          # = 3
R_NEAR = "sqrt(9 + exp(-10000))"                # > 3, not decided


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [dict(s, text="") for s in steps]}


def _dom(expr):
    return _ir("domain_of", {"expr": expr, "var": "x"}, X, shape="set")


def _ns(**syms):
    return dict(_SAFE_NAMES, **syms)


# ---------------------------------------------------------------------------- (1) set + and -
@pytest.mark.parametrize("ir,claim,verdict", [
    (_dom("x + 1"), f"Interval.open(-oo, {R}) + Interval.open(3, oo)", "INCORRECT"),
    (_dom("x + 1"), f"Interval.open(-oo, 3) + Interval.open({R}, oo)", "INCORRECT"),
    (_dom("x + 1"), f"Reals - Interval({R}, 3)", "INCORRECT"),
    (_dom("x + 1"), f"S.Reals - Interval(3, {R})", "INCORRECT"),
    (_dom("x + 1"), f"Interval(4, oo) + (Interval.open(-oo, {R}) + Interval.open(3, 4))", "INCORRECT"),
    (_dom("x + 1"), f"Interval.open(-oo, {R}) + {{3 + 1}} + Interval.open(3, oo)", "INCORRECT"),
    (_dom("x + 1"), f"Interval.open(-oo, {R}) + FiniteSet(7) + Interval.open(3, oo)", "INCORRECT"),
    # an operation nested inside a constructor's argument
    (_dom("x + 1"), f"Union(Interval(4, oo), Intersection(Interval.open(-oo, {R}) + Interval.open(3, 4), Reals))",
     "INCORRECT"),
    (_dom("sqrt(x)*sqrt(5 - x)"), f"Interval.Ropen(0, {R}) + Interval.Lopen(3, 5)", "INCORRECT"),
    (_ir("solve_inequality", {"var": "x"}, X, ["x**2 + 1 > 0"], "interval"),
     f"Interval.open(-oo, 3) + Interval.open({R}, oo)", "INCORRECT"),
    # an endpoint pair that cannot be decided is not read, whatever the notation
    (_dom("1/(x - 3)"), f"Interval.open(-oo, 3) + Interval.open({R_NEAR}, oo)", "UNKNOWN"),
    # right answers written with + and -
    (_dom("1/(x - 3)"), f"Interval.open(-oo, {R}) + Interval.open(3, oo)", "CORRECT"),
    (_dom("1/(x - 3)"), "Reals - FiniteSet(3)", "CORRECT"),
    (_dom("1/(x - 3)"), f"Reals - FiniteSet({R})", "CORRECT"),
    (_dom("x + 1"), f"Interval.open(-oo, {R}) + Interval(3, oo)", "CORRECT"),
    (_dom("x + 1"), "Reals - EmptySet", "CORRECT"),
    # the point taken out and put back written two ways: the whole line (only S names the set here)
    (_dom("x + 1"), f"(S.Reals - {{3}}) + {{{R}}}", "CORRECT"),
    (_dom("sqrt(x)"), "Interval.Ropen(0, 1) + Interval(1, oo)", "CORRECT"),
    (_dom("sqrt(x)"), "Interval.Ropen(0, 1) + Interval.open(1, oo)", "INCORRECT"),
])
def test_set_arithmetic_verdicts(ir, claim, verdict):
    kind = "interval" if ir["answer_shape"] == "interval" else "set"
    assert verify(ir, _sol(claim, kind)).verdict == verdict


def test_set_arithmetic_unifies_endpoints():
    s = parse_set_str(f"Interval.open(-oo, {R}) + Interval.open(3, oo)", _ns())
    assert s != sp.S.Reals and s.contains(3) is not sp.true
    assert parse_set_str(f"Reals - Interval({R}, 3)", _ns()).contains(3) is not sp.true
    with pytest.raises(ParseError):
        parse_set_str(f"Interval.open(-oo, 3) + Interval.open({R_NEAR}, oo)", _ns())


def test_arithmetic_that_is_no_set_operation_is_unchanged():
    x = sp.Symbol("x", real=True)
    ns = _ns(x=x)
    assert parse_expr_str("x + 1 - 2", ns) == x - 1
    # a long sum inside a set: the rewrite does not recurse (ast.unparse did at 500 terms)
    assert parse_set_str("FiniteSet(" + " + ".join(["1"] * 600) + ")", ns) == sp.FiniteSet(600)
    # a set and a number are not added, as before
    with pytest.raises(ParseError):
        parse_expr_str("Interval(0, 1) + 2", ns)
    with pytest.raises(ParseError):
        parse_expr_str("2 - Interval(0, 1)", ns)
    # a Python set operand becomes a FiniteSet of values only: SymPy's own conversion put the tuple
    # (1, 2) in a set of reals (principle 13: no container is sympified)
    for text in ("Interval(0, 1) + {(1, 2)}", "Interval(0, 1) - {(1, 2)}"):
        with pytest.raises(ParseError):
            parse_set_str(text, ns)
    assert parse_set_str(f"Interval.open(3, 5) + {{{R}}}", ns) == sp.Interval.Ropen(3, 5)


def test_what_names_a_set():
    from mathverify.normalize.parse import _names_a_set
    ns = _ns(x=sp.Symbol("x"))
    assert all(_names_a_set(ns[n]) for n in ("S", "Reals", "EmptySet", "Integers", "Interval", "FiniteSet",
                                             "Union", "Intersection", "Complement", "ImageSet", "Range"))
    assert not any(_names_a_set(ns[n]) for n in ("sqrt", "pi", "oo", "Sum", "Abs", "Lambda", "x"))


def test_the_reading_as_written_is_not_evaluated():
    from mathverify.normalize.parse import _TRANSFORMS, guarded_parse_expr
    x = sp.Symbol("x", real=True)
    ns = _ns(x=x)
    assert x in parse_as_written("x/x + S(1)", ns).free_symbols     # x/x kept: its undefined point is read
    # evaluation off is parse_expr's own, whatever the caller's context
    e = guarded_parse_expr("x/x + S(1)", local_dict=dict(ns, Add=sp.Add, Mul=sp.Mul, Pow=sp.Pow), global_dict={},
                           transformations=_TRANSFORMS, evaluate=False)
    assert x in e.free_symbols


# ---------------------------------------------------------------------------- (2) exact interval order
E40 = sp.Rational(1, 10**40)
Q = sp.sqrt(2)


@pytest.mark.parametrize("a,b", [
    (sp.Interval.Ropen(Q - 2 * E40, Q - E40), sp.Interval.open(Q, 5)),
    (sp.Interval.Ropen(Q, Q + E40), sp.Interval.open(Q + 2 * E40, 5)),
])
def test_normalize_set_orders_intervals_exactly(a, b):
    ivs, pts = normalize_set(sp.Union(a, b))
    assert ivs == sorted([a, b], key=lambda i: i.inf - Q) and pts == []


def test_an_unordered_start_is_not_guessed():
    a = sp.Symbol("a", real=True)
    assert normalize_set(sp.Union(sp.Interval(a, 1), sp.Interval(2, 3))) is None


@pytest.mark.parametrize("expr,claim,verdict", [
    ("1/sqrt((x - sqrt(2))*(5 - x))", "[sqrt(2) - 2*10**(-40), sqrt(2) - 10**(-40)) U (sqrt(2), 5)", "INCORRECT"),
    ("1/sqrt((x - sqrt(2) - 2*10**(-40))*(5 - x))",
     "[sqrt(2), sqrt(2) + 10**(-40)) U (sqrt(2) + 2*10**(-40), 5)", "INCORRECT"),
    ("1/sqrt((x - sqrt(2))*(5 - x))", "(sqrt(2), 5)", "CORRECT"),
])
def test_close_starts_verdicts(expr, claim, verdict):
    assert verify(_dom(expr), _sol(claim, "set")).verdict == verdict


# ---------------------------------------------------------------------------- (3) constant bounds
@pytest.mark.parametrize("expr,claim", [
    ("floor(Sum(k, (k, 3, sqrt(1))))", "-2"), ("ceiling(Sum(k, (k, 3, sqrt(1))))", "-2"),
    ("floor(Sum(k, (k, 3, sqrt(4) - 1)))", "-2"), ("floor(Sum(k, (k, sqrt(9), 1)))", "-2"),
    ("floor(Sum(k, (k, 3, exp(0))))", "-2"), ("floor(Sum(k, (k, 3, log(E))))", "-2"),
    ("floor(Product(k, (k, 3, sqrt(1))))", "0"),
    # limits that are not an integer apart
    ("floor(Sum(k, (k, 1, sqrt(1)/2)))", "0"), ("floor(Sum(k, (k, 1, sqrt(2))))", "1"),
    (r"\left\lfloor \sum_{k=3}^{\sqrt{1}} k \right\rfloor", "-2"),
    (r"\left\lfloor \sum_{k=\sqrt{9}}^{1} k \right\rfloor", "-2"),
])
def test_a_constant_bound_that_reverses_the_range_is_not_read(expr, claim):
    assert verify(_ir("evaluate", {"expr": expr}, KI), _sol(claim)).verdict == "UNKNOWN"


def test_a_step_with_a_constant_reversed_bound_is_not_verified():
    ir = _ir("evaluate", {"expr": "x**2"}, [{"name": "x", "domain": "real"}], ["x = 2"])
    r = verify(ir, _sol("4", steps=[{"id": "s1", "kind": "compute", "claim": "floor(Sum(k, (k, 3, sqrt(1)))) = -2",
                                     "from": []}]))
    lay = next(l for l in r.layers if l.layer == "steps.refute")
    assert lay.evidence["steps"][0]["status"] != "verified"


@pytest.mark.parametrize("expr,claim,verdict", [
    ("floor(Sum(k, (k, 1, sqrt(9))))", "6", "CORRECT"), ("floor(Sum(k/2, (k, 1, sqrt(4))))", "1", "CORRECT"),
    ("floor(Sum(k/2, (k, 1, sqrt(4))))", "2", "INCORRECT"), ("Sum(k, (k, 1, sqrt(9)))", "6", "CORRECT"),
    ("Sum(1/2**k, (k, 1, oo))", "1", "CORRECT"), (r"\sum_{k=1}^{\sqrt{9}} k", "6", "CORRECT"),
])
def test_a_constant_bound_the_right_way_round_is_read(expr, claim, verdict):
    assert verify(_ir("evaluate", {"expr": expr}, KI), _sol(claim)).verdict == verdict


# ---------------------------------------------------------------------------- (4) symbolic bounds
# A symbolic bound took the value its given puts in: Σ_{k=1}^{n} k with n = -2 is SymPy's Karr sum 1, and
# Σ_{k=1}^{n/2} k with n = 7 steps from 1 (63/8). Both were CORRECT, while the same sums written with
# numbers are not read (see (3) and normalize.parse._refuse_reversed_ranges). The range as written now
# needs hi - lo + 1 >= 0 (hi = lo - 1 is the empty sum) and, for finite bounds, hi - lo an integer.
KN = [{"name": "k", "domain": "integer"}, {"name": "n", "domain": "integer"}]
KPN = [{"name": "k", "domain": "integer"}, {"name": "n", "domain": "positive_integer"}]
KUN = [{"name": "k", "domain": "integer"}, {"name": "n"}]
KRM = [{"name": "k", "domain": "integer"}, {"name": "m", "domain": "real"}]


def _ev(expr, givens=(), vars_=KN):
    return _ir("evaluate", {"expr": expr}, vars_, givens)


@pytest.mark.parametrize("ir,claim", [
    (_ev("Sum(k, (k, 1, n))", ["n = -2"]), "1"),                    # Karr
    (_ev("Sum(k, (k, 1, n))", ["n = -2"]), "0"),                    # the empty sum: no convention either
    (_ev("Sum(k, (k, 1, n))", ["n = -2"], KUN), "1"),
    (_ev("Sum(k, (k, n, 1))", ["n = 4"]), "-5"),
    (_ev("floor(Sum(k, (k, 3, n)))", ["n = 1"]), "-2"),
    (_ev("Product(k, (k, 3, n))", ["n = 0"]), "1/2"),
    (_ev("Sum(k, (k, 1, n + 1))", ["n = -4"]), "3"),
    (_ev("Sum(k, (k, 1, n))", ["n + 2 = 0"]), "1"),
    (_ev("Sum(k, (k, 1, n))", ["n = -1"]), "0"),                    # hi = lo - 2: Karr's 0 is its formula's
    (_ev("Sum(k, (k, 1, 2*n))", ["n = -1"]), "1"),
    (_ev("Sum(k, (k, n, 3))", ["n = 5"]), "-4"),
    (_ev("Sum(k, (k, n, 3))", ["n = 5"]), "0"),
    (_ev(r"\sum_{k=1}^{n} k", ["n = -2"]), "1"),
    (_ev(r"\prod_{k=3}^{n} k", ["n = 0"]), "1/2"),
    # bounds not an integer apart
    (_ev("Sum(k, (k, 1, n/2))", ["n = 7"]), "63/8"),
    (_ev("Sum(k, (k, 1, n/2))", ["n = 7"]), "6"),
    (_ev("Sum(k, (k, 1, m))", ["m = 5/2"], KRM), "35/8"),
])
def test_a_given_that_reverses_a_symbolic_range_is_no_value(ir, claim):
    assert verify(ir, _sol(claim)).verdict == "UNKNOWN"


@pytest.mark.parametrize("ir,claim,verdict", [
    (_ev("Sum(k, (k, 1, n))", ["n = 3"]), "6", "CORRECT"),
    (_ev("Sum(k, (k, 1, n))", ["n = 3"]), "5", "INCORRECT"),
    (_ev("Sum(k, (k, 1, n))", ["n = 0"]), "0", "CORRECT"),          # hi = lo - 1: the empty sum
    (_ev("Sum(k, (k, 1, n))", ["n = 0"]), "1", "INCORRECT"),
    (_ev("Product(k, (k, 3, n))", ["n = 2"]), "1", "CORRECT"),      # the empty product
    (_ev("Sum(k, (k, n, 3))", ["n = 4"]), "0", "CORRECT"),
    (_ev("Sum(k, (k, 1, n))", ["n = 3"], KPN), "6", "CORRECT"),
    (_ev("Sum(k, (k, 1, n))", ["n = 3"], KUN), "6", "CORRECT"),
    (_ev("Sum(k, (k, n, n + 2))", ["n = -5"]), "-12", "CORRECT"),   # never reversed: no condition
    (_ev("Sum(k, (k, n, n + 2))", ["n = -5"]), "-11", "INCORRECT"),
    (_ev("Sum(k, (k, 1, n/2))", ["n = 6"]), "6", "CORRECT"),
    (_ev("Sum(k, (k, 1, 2*n))", ["n = 2"]), "10", "CORRECT"),
    (_ev("Sum(k, (k, 1, n**2))", ["n = -2"]), "10", "CORRECT"),
    (_ev("Sum(2**k, (k, -oo, n))", ["n = 0"]), "2", "CORRECT"),
    (_ev(r"\sum_{k=1}^{n} k", ["n = 3"]), "6", "CORRECT"),
    (_ev("Sum(k, (k, 1, n))"), "n*(n + 1)/2", "CORRECT"),
    (_ev("Sum(k, (k, 1, n))"), "n**2/2", "INCORRECT"),
    (_ev("Sum(k, (k, 1, n))", (), KUN), "n*(n + 1)/2", "CORRECT"),
    (_ev("Sum(k, (k, 1, n))", ["n**2 = 4", "n > 0"]), "3", "CORRECT"),
])
def test_a_symbolic_range_the_right_way_round_is_read(ir, claim, verdict):
    assert verify(ir, _sol(claim)).verdict == verdict


@pytest.mark.parametrize("ir,claim,verdict", [
    # n = -2 reverses the range. It was first dropped like a point where the expression is undefined, and
    # 3 was CORRECT, 1 INCORRECT; but the value there is a convention (Karr's 1, the empty sum's 0), so
    # the solution is neither kept nor dropped (DECISIONS §80; tests/test_parca9_ters_aralik.py)
    (_ev("Sum(k, (k, 1, n))", ["n**2 = 4"]), "3", "UNKNOWN"),
    (_ev("Sum(k, (k, 1, n))", ["n**2 = 4"]), "1", "UNKNOWN"),
    # -4 is a root of Karr's n(n + 1)/2 = 6 only (the empty sum is 0 there)
    (_ir("solve_equation", {"var": "n", "equation": "Sum(k, (k, 1, n)) = 6"}, KN, shape="set"), "{-4, 3}",
     "UNKNOWN"),
    (_ir("solve_equation", {"var": "n", "equation": "Sum(k, (k, 1, n)) = 0"}, KN, shape="set"), "{-1, 0}",
     "UNKNOWN"),
])
def test_a_reversed_range_decides_no_solution(ir, claim, verdict):
    kind = "set" if ir["answer_shape"] == "set" else "value"
    assert verify(ir, _sol(claim, kind)).verdict == verdict


def test_the_range_conditions():
    from mathverify.certify.domain import DEFINEDNESS_UNDECIDED, FORWARD_SPANS, definedness_conditions

    def fwd(span):
        # hi - lo + 1 >= 0, undecided where the range is reversed (DECISIONS §80)
        return sp.Contains(span, FORWARD_SPANS)

    n = sp.Symbol("n", integer=True)
    m = sp.Symbol("m", real=True)
    p = sp.Symbol("n", integer=True, positive=True)
    k, j = sp.Symbol("k", integer=True), sp.Symbol("j", integer=True)
    with sp.evaluate(False):
        exprs = [sp.Sum(k, (k, 1, n)), sp.Sum(k, (k, 1, p)), sp.Sum(k, (k, 1, m)), sp.Product(k, (k, 3, n)),
                 sp.Sum(k, (k, n, n + 2)), sp.Sum(k, (k, 1, n / 2)), sp.Sum(2 ** k, (k, -sp.oo, n)),
                 sp.Sum(sp.Sum(1, (j, k, 2)), (k, 1, 5)), sp.Sum(sp.Sum(1, (j, 1, k)), (k, 1, 5)),
                 sp.Sum(sp.Sum(1, (j, 1, n - k)), (k, 1, 3))]
    got = [definedness_conditions(e, None) for e in exprs]
    assert got[0] == [fwd(n)]
    assert got[1] == []
    assert got[2] == [fwd(m), sp.Contains(m, sp.S.Integers)]
    assert got[3] == [fwd(n - 2)]
    assert got[4] == []
    assert got[5] == [fwd(n / 2), sp.Contains(n / 2, sp.S.Integers)]
    assert got[6] == []
    # an inner range an outer index reverses: not read (`false` would make it defined nowhere)
    assert got[7] == [DEFINEDNESS_UNDECIDED] and sp.false not in got[7]
    assert got[8] == []
    assert got[9] == [fwd(n - 1), fwd(n - 2), fwd(n - 3)]


def test_a_nested_range_an_outer_index_reverses_is_not_defined_nowhere():
    """Σ_{k=1}^{5} Σ_{j=k}^{2} 1 runs Karr's sum at k = 4, 5: undecided, so no task reads it as having
    no value (the empty solution set of x + that = 0 is not certified)."""
    eq = _ir("solve_equation", {"var": "x", "equation": "x + Sum(Sum(1, (j, k, 2)), (k, 1, 5)) = 0"},
             [{"name": "x"}, {"name": "k", "domain": "integer"}, {"name": "j", "domain": "integer"}], shape="set")
    for claim in ("EmptySet", "{0}", "{-3}"):
        assert verify(eq, _sol(claim, "set")).verdict == "UNKNOWN"


# ---------------------------------------------------------------------------- (5) gcd in a list payload
EQ12 =_ir("solve_equation", {"var": "x", "equation": "x - 12 = 0"}, X, shape="set")


@pytest.mark.parametrize("payload", [["gcd(84, 120)"], ["gcd(120, 84)"], ["igcd(84, 120)"], [r"\gcd(84, 120)"],
                                     ["lcm(4, 6)"], [r"\operatorname{lcm}(4, 6)"]])
def test_a_gcd_in_a_list_payload_is_not_a_value(payload):
    r = verify(EQ12, _sol(payload, "set"))
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in r.flags


@pytest.mark.parametrize("payload,verdict", [(["12"], "CORRECT"), (["13"], "INCORRECT")])
def test_a_list_payload_of_values_is_read(payload, verdict):
    assert verify(EQ12, _sol(payload, "set")).verdict == verdict


# ---------------------------------------------------------------------------- (6) the size limit
def test_the_set_size_limit_counts_rationals():
    assert len(parse_set_str("{" + ", ".join(str(i) for i in range(300)) + "}", _ns())) == 300
    for text in ("{" + ", ".join(str(i) for i in range(301)) + "}",
                 " U ".join(f"({2 * i}/3, {2 * i + 1}/3)" for i in range(151))):
        with pytest.raises(ParseError, match="more than 300 constants"):
            parse_set_str(text, _ns())
