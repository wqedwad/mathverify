"""The parser's reading of three notations whose SymPy default is not the mathematics of the problem
(V14, 29 Sep 2026). Each case was measured wrong before: a wrong answer certified or a right one
refuted, because (1) SymPy's gcd/lcm are the polynomial gcd/lcm (`gcd(n, 4)` = 1), (2) the index of
a Sum/Product and the variable of a definite integral took the IR's assumptions for the same name
(k positive: `Sum(Abs(k), (k, -2, 2))` = 0), (3) `arccot` was SymPy's `acot`, valued in
(-pi/2, pi/2] where AYT reads (0, pi).
"""
import pickle

import pytest
import sympy as sp

from mathverify.ir import ProblemIR
from mathverify.normalize.parse import ParseError, build_namespace, parse_as_written, parse_expr_str
from mathverify.verifier import verify


def _ns(*vars_):
    ir = ProblemIR.from_dict({"task": {"kind": "evaluate", "params": {"expr": "1"}}, "givens": [],
                              "vars": [{"name": n, "domain": d} for n, d in vars_], "answer_shape": "scalar"})
    return build_namespace(ir)


NS = _ns(("k", "positive_integer"), ("n", "positive_integer"), ("x", "positive_real"), ("y", "real"))


def _ir(expr, vars_=(), givens=()):
    return {"task": {"kind": "evaluate", "params": {"expr": expr}}, "givens": list(givens),
            "vars": [{"name": n, "domain": d} for n, d in vars_], "answer_shape": "scalar"}


def _verdict(ir, payload, steps=()):
    sol = {"claimed_answer": {"kind": "value", "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": kind, "claim": c, "from": [], "text": ""}
                     for i, (kind, c) in enumerate(steps)]}
    return verify(ir, sol)


# --- (1) gcd / lcm ---------------------------------------------------------------------------

@pytest.mark.parametrize("src,value", [
    ("gcd(84, 120)", 12), ("lcm(4, 6)", 12), ("gcd(84, 120) + lcm(4, 6)", 24), ("gcd(12, 18, 24)", 6),
    ("lcm(4, 6, 10)", 60),                     # SymPy's lcm read the third argument as a generator: 12
    ("gcd(-4, 6)", 2), ("lcm(-4, 6)", 12), ("gcd(0, 0)", 0), ("lcm(0, 5)", 0),
    ("gcd(1/2, 1/3)", sp.Rational(1, 6)), ("lcm(1/2, 1/3)", 1),    # fractions: the school rule, as before
])
def test_gcd_and_lcm_of_numbers(src, value):
    assert parse_expr_str(src, NS) == value


@pytest.mark.parametrize("src", ["gcd(n, 4)", "lcm(n, 2)", "gcd(2*n, n)", "lcm(n, n + 1)", "gcd(pi, 2)",
                                 "gcd(sqrt(2), 2)", "gcd(y**2 - 1, y - 1)"])
def test_gcd_and_lcm_are_not_polynomial_operations(src):
    """The polynomial gcd gave gcd(n, 4) = 1, lcm(n, 2) = 2*n, gcd(pi, 2) = 1."""
    assert type(parse_expr_str(src, NS)).__name__ in ("gcd", "lcm")        # left unevaluated


def test_gcd_and_lcm_evaluate_once_the_arguments_are_numbers():
    n = NS["n"]
    assert parse_expr_str("gcd(n, 4)", NS).subs(n, 12) == 4
    assert parse_expr_str("gcd(n, 2)", NS).subs(n, 6) == 2          # the polynomial gcd said 1
    assert parse_expr_str("lcm(n, 2)", NS).subs(n, 6) == 6          # ... and 2*n = 12
    assert parse_expr_str("lcm(n, 2)", NS).subs(n, 7) == 14


def test_gcd_and_lcm_know_they_are_integers_only_of_integers():
    assert parse_expr_str("gcd(n, 4)", NS).is_integer is True
    assert parse_expr_str("lcm(n, 4)", NS).is_nonnegative is True
    assert parse_expr_str("gcd(y, 4)", NS).is_integer is None


def test_gcd_and_lcm_read_back_and_cross_the_sandbox():
    for src in ("gcd(n, 4)", "lcm(n, 2) + 1"):
        e = parse_expr_str(src, NS)
        assert parse_expr_str(str(e), NS) == e
        assert pickle.loads(pickle.dumps(e)) == e


def test_the_list_form_of_gcd_and_lcm():
    assert parse_expr_str("gcd([84, 120])", NS) == 12
    assert parse_expr_str("lcm([4, 6, 10])", NS) == 60


def test_gcd_needs_two_arguments():
    with pytest.raises(ParseError):
        parse_expr_str("gcd(4)", NS)


def test_gcd_of_a_symbol_decides_the_answer():
    ir = _ir("gcd(n, 4)", [("n", "positive_integer")], ["n = 12"])
    assert _verdict(ir, "4").verdict == "CORRECT"          # was INCORRECT
    assert _verdict(ir, "1").verdict == "INCORRECT"        # was CORRECT


def test_a_polynomial_lcm_step_is_refuted():
    ir = _ir("lcm(n, 2)", [("n", "positive_integer")], ["n = 6"])
    r = _verdict(ir, "6", [("eq", "lcm(n, 2) = 2*n"), ("compute", "lcm(6, 2) = 6")])
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1


# --- (2) the variable of a range binder ------------------------------------------------------

@pytest.mark.parametrize("src,value", [
    ("Sum(Abs(k), (k, -2, 2))", 6),            # k positive made Abs(k) = k: 0
    ("Sum(0**k, (k, 0, 3))", 1),               # ... and 0**k = 0 before the sum was built: 0
    ("Sum(sqrt(k**2), (k, -3, -1))", 6),       # InconsistentAssumptions
    ("Product(sign(k), (k, -1, -1))", -1),     # InconsistentAssumptions
    ("Integral(Abs(x), (x, -1, 1))", 1),       # x positive: 0
    ("Integral(sign(x), (x, -2, 1))", -1),     # x positive: 3
    ("integrate(Abs(x), (x, -1, 1))", 1),
    ("Sum(k*n, (n, 1, k), (k, 1, 3))", 25),    # the second limit binds the first one's bounds
    ("Sum(Sum(k*n, (n, 1, k)), (k, 1, 3))", 25),
    ("Sum(Abs(k), [k, -2, 2])", 6),            # a list limit is a limit
    # an integer assumption would be wrong here: SymPy sums at 1/2, 3/2, 5/2
    ("Sum(sin(pi*k), (k, 1/2, 5/2))", 1),
    # what the data uses is unchanged
    ("Sum(1/(k*(k + 1)), (k, 1, oo))", 1), ("Sum(k, (k, 1, 10))", 55), ("Sum(1/factorial(k), (k, 0, oo))", sp.E),
])
def test_a_bound_variable_does_not_take_the_declared_assumptions(src, value):
    assert sp.simplify(parse_expr_str(src, NS).doit() - value) == 0


def test_the_bound_variable_is_a_fresh_symbol_only_inside_the_binder():
    e = parse_expr_str("Sum(k, (k, 1, 3)) + k", NS)
    assert e.free_symbols == {NS["k"]}                       # the free k is the declared one
    s = next(a for a in e.args if isinstance(a, sp.Sum))
    # an integer, since its limits are (the sum runs over integers), and not declared positive
    assert s.limits[0][0] == sp.Symbol("k", integer=True) and s.limits[0][0].is_positive is None
    assert e.doit() == NS["k"] + 6


def test_symbolic_sums_are_read_as_before():
    n = NS["n"]
    assert sp.simplify(parse_expr_str("Sum(1/k - 1/(k + 1), (k, 1, n))", NS).doit() - (1 - 1 / (n + 1))) == 0
    assert parse_expr_str("Sum((-1)**(2*k), (k, 1, n))", NS).doit() == n


def test_a_symbolic_sum_from_zero_keeps_its_first_term():
    assert sp.simplify(parse_expr_str("Sum(0**k, (k, 0, n))", NS).doit()) == 1     # k positive: 0


@pytest.mark.parametrize("src", [
    "Sum(Sum(k, (k, 1, 3)), (k, 1, 2))",        # SymPy flattens it and evaluates |k| + 1 to 0, not 10
    "Sum(Sum(Abs(k) + 1, (k, -1, 1)), (k, 1, 2))",
    "integrate(y**2, y, (y, 0, 1))",            # the bare y was the IR symbol, the tuple's the dummy
    "Integral(1, y, (y, 0, 1))",
    "Sum(k, (k, 3, 1))",                        # Karr: -2; the school reading differs
    "Product(k, (k, 3, 1))",
    # floor evaluates the Sum while the text is read: only the check of the written bounds sees the
    # range (read, it was -2; part 11, 1 Oct 2026)
    "floor(Sum(k, (k, 3, 1)))",
    r"\lfloor \sum_{k=3}^{1} k \rfloor",
    "Sum(k, (k, 1, 7/2))",                      # SymPy: 63/8; stepping from 1: 1 + 2 + 3
    "Sum(pi, (pi, 1, 3))",                      # not a variable
    "Sum(k, (S, 1, 3))",
])
def test_a_binder_that_cannot_be_read_faithfully_is_refused(src):
    with pytest.raises(ParseError):
        parse_expr_str(src, NS)


@pytest.mark.parametrize("claim", ["floor(Sum(k, (k, 3, 1))) = 0", r"\lfloor \sum_{k=3}^{1} k \rfloor = 0"])
def test_a_step_over_a_written_reversed_range_is_not_refuted(claim):
    """Read, the step was Karr's floor(-2) = 0 and refuted, though the empty-sum reading makes it true: a
    right solution was INCORRECT (part 11, 1 Oct 2026). Not read, the step is a malformed claim."""
    ir = {"task": {"kind": "evaluate", "params": {"expr": "x + 1"}}, "givens": ["x = 5"], "answer_shape": "scalar",
          "vars": [{"name": "x", "domain": "real"}, {"name": "k", "domain": "integer"}]}
    sol = {"claimed_answer": {"kind": "value", "payload": "6"},
           "steps": [{"id": "s1", "kind": "compute", "claim": claim, "from": [], "text": ""}]}
    r = verify(ir, sol)
    st = next(la for la in r.layers if la.layer == "steps.refute").evidence["steps"][0]
    assert st["status"] != "refuted", st
    assert r.verdict != "INCORRECT", (r.verdict, st)


def test_a_long_sum_of_terms_is_rebound_without_recursion():
    assert parse_expr_str("Sum(" + " + ".join(["k"] * 600) + ", (k, 1, 2))", NS).doit() == 1800


def test_a_limit_keeps_the_declared_symbol():
    """There the declaration is the range: n integer makes it the limit of a sequence."""
    assert parse_expr_str("Limit(sin(pi*n), n, oo)", NS).doit() == 0


def test_the_latex_reading_agrees():
    assert parse_expr_str(r"\sum_{k=0}^{3} 0^{k}", NS).doit() == 1
    assert parse_expr_str(r"\int_{-1}^{1} |x| dx", NS).doit() == 1


def test_the_as_written_reading_keeps_the_declared_symbol():
    """Definedness is read with the declared symbol inside the binder: a solver's steps about x in
    an integral over x are checked against the integrand's conditions on x (C1/C2 of the audit)."""
    t = parse_as_written("Sum(0**k, (k, 0, 3)) = 1", NS)
    assert isinstance(t[0], sp.Sum) and t[0].limits[0][0] == NS["k"]


def test_a_bound_variable_decides_the_answer():
    ir = _ir("Sum(Abs(k), (k, -2, 2))", [("k", "positive_integer")])
    assert _verdict(ir, "6").verdict == "CORRECT"          # was INCORRECT
    assert _verdict(ir, "0").verdict == "INCORRECT"        # was CORRECT
    ir = _ir("Sum(0**k, (k, 0, 5))", [("k", "positive_integer")])
    assert _verdict(ir, "1").verdict == "CORRECT"
    assert _verdict(ir, "0").verdict == "INCORRECT"


def test_a_wrong_step_over_a_bound_index_is_refuted():
    ir = _ir("Sum(1/(k*(k + 1)), (k, 1, oo))", [("k", "positive_integer"), ("n", "positive_integer")])
    r = _verdict(ir, "1", [("compute", "Sum(Abs(k), (k, -2, 2)) = 0"),
                           ("compute", "Sum(1/(k*(k + 1)), (k, 1, oo)) = 1")])
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1


# --- (3) arccot --------------------------------------------------------------------------------

@pytest.mark.parametrize("src,value", [
    ("arccot(-1)", 3 * sp.pi / 4), ("acot(-1)", 3 * sp.pi / 4), ("arccot(0)", sp.pi / 2),
    ("arccot(sqrt(3))", sp.pi / 6), ("arccot(-sqrt(3))", 5 * sp.pi / 6),
    (r"\operatorname{arccot}(-1)", 3 * sp.pi / 4), (r"\cot^{-1}(-1)", 3 * sp.pi / 4), (r"\arccot(-1)", 3 * sp.pi / 4),
    ("arctan(-1) + arccot(-1)", sp.pi / 2),
])
def test_arccot_takes_values_in_zero_pi(src, value):
    assert sp.simplify(parse_expr_str(src, NS) - value) == 0


def test_arccot_is_in_zero_pi_everywhere_and_total():
    f = parse_expr_str("arccot(y)", NS)
    for v in (-10**6, -3, -sp.Rational(1, 7), 0, sp.Rational(1, 7), 3, 10**6):
        assert 0 < f.subs(NS["y"], v).evalf(30) < sp.pi
    assert parse_as_written("arccot(y)", NS) is not None


def test_arccot_decides_the_answer():
    ir = _ir("arccot(-1)")
    assert _verdict(ir, "3*pi/4").verdict == "CORRECT"       # was INCORRECT
    assert _verdict(ir, "-pi/4").verdict == "INCORRECT"      # was CORRECT
    r = _verdict(ir, "3*pi/4", [("compute", "arccot(-1) = -pi/4"), ("compute", "-pi/4 + pi = 3*pi/4")])
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1
