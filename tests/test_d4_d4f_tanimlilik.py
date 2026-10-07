"""Fourth audit (1 Oct 2026), part d4f: definedness (`denetim/2026-10-01/d4f/`).

Each case was measured wrong on 9c6fbdb:

* CAP-F1: a pole of n! ((-1)!, (-2)!) inside a written expression: building the condition Ne((-1)!, 0) raised
  "gamma function pole", the callers read the exception as "defined", and SymPy's 1/zoo = 0 was certified:
  1/(-1)! = 0, 5!/(-2)! = 0, x + 1/(-1)! = 2 -> {2}, the step "1/factorial(-1) = 0" verified. 1/zoo is no value on
  any path: a given, a function body, a point, a bound or an interval of the task, the claim (1/factorial(-1),
  1/zoo, 1/(1/0) for 0), LaTeX \\Gamma(0). An equation around such a pole is not "defined nowhere" either: 1/Γ is
  entire and gives 1/(-1)! = 0, so neither {2} nor {} is checked.
* TAN-10, C1: Sum/Product limits an integer apart but not integers (Σ_{k=1/2}^{5/2} k): 9/2 stepping from the lower
  limit (SymPy), 3 over the integers between them; 9/2 was CORRECT and 3 INCORRECT, the step "= 3" refuted.
* B1: a LaTeX reversed constant range was read when the index was \\alpha, k_{1}, \\mathrm{k} or the `=` spaced
  (k\\,=\\,3): \\lfloor \\sum_{\\alpha=3}^{\\sqrt{1}} \\alpha \\rfloor = -2 (Karr) CORRECT. The range is checked on the
  tree latex2sympy builds with evaluation off.
* TAN-12: an inner range naming the outer index with the outer bound fixed by a given (n = 3): Π_{k=1}^{n}
  Σ_{j=1}^{k} 1 = 6 was UNKNOWN "problem_undefined_as_written"; an undecided range is no undefined problem.
* G14: lim_{x->oo} (x - 2)!/x^x with x a positive integer: (x - 2)! has its value from x = 2 on, and the limit
  reads only that tail; 0 was UNKNOWN.
"""
import pytest
import sympy as sp

from mathverify.certify.domain import definedness_conditions
from mathverify.normalize.parse import _SAFE_NAMES, ParseError, parse_as_written, parse_expr_str
from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_integer"}
XI = {"name": "x", "domain": "integer"}
K = {"name": "k", "domain": "integer"}
N = {"name": "n", "domain": "integer"}
J = {"name": "j", "domain": "integer"}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _run(ir, payload, kind="value", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _flags(r):
    return {f for la in r.layers for f in (la.flags or [])} | set(r.flags)


def _ev(expr, givens=(), vars_=None, functions=None):
    return _ir("evaluate", {"expr": expr}, givens, vars_, functions=functions)


def _step(claim, kind="compute", vars_=None):
    r = _run(_ev("x", ["x = 1"], vars_), "1", steps=[(kind, claim)])
    return r, next(la for la in r.layers if la.layer == "steps.refute").evidence["steps"][0]["status"]


# --- CAP-F1 -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr,value", [
    ("1/factorial(-1)", "0"), (r"\frac{5!}{(-2)!}", "0"), ("factorial(4)/factorial(-1)", "0"), ("7 - 2/factorial(-2)", "7"),
    ("1/sqrt(factorial(-2))", "0"), ("asin(1/factorial(-1))", "0"), ("tan(1/factorial(-1))", "0"),
    ("log(2 + 1/factorial(-1))", "log(2)"), ("(1/factorial(-1))**0", "1"), ("Mod(5, 2 + 1/factorial(-1))", "1"),
    ("1/zoo", "0"), (r"\frac{1}{\Gamma(0)}", "0"), (r"\frac{1}{\gamma(0)}", "0"), ("P(2, 3)", "0"),
    ("1/binomial(-1, 1/2)", "0"), ("Integral(x/factorial(-1) + 1, (x, 0, 1))", "1"),
])
def test_cap_f1_a_closed_pole_is_undefined_as_written(expr, value):
    r = _run(_ev(expr), value)
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in _flags(r)


@pytest.mark.parametrize("ir,payload,kind", [
    (_ev("x + 1/factorial(-1)", ["x = 3"]), "3", "value"),
    (_ev("n + 1", ["n = 1/factorial(-1)"], [{"name": "n"}]), "1", "value"),
    (_ir("solve_equation", {"var": "x", "equation": "x + 1/factorial(-1) = 2"}, shape="set"), "{2}", "set"),
    # not "defined nowhere" either: 1/Γ is entire, and {2} is the answer under it
    (_ir("solve_equation", {"var": "x", "equation": "x + 1/factorial(-1) = 2"}, shape="set"), "EmptySet", "set"),
    (_ir("solve_inequality", {"var": "x", "inequality": "x - 1/factorial(-1) > 1"}, shape="interval"), "(1, oo)",
     "interval"),
    (_ir("simplify_expression", {"expr": "x + 1/factorial(-1)"}, shape="expression"), "x", "expression"),
    (_ir("count_roots", {"expr": "x**2 - 1 + 1/factorial(-1)", "var": "x"}, shape="count"), 2, "count"),
    (_ir("derivative", {"f": "x**2 + 1/factorial(-1)", "var": "x", "at": "1"}), "2", "value"),
    (_ir("limit", {"expr": "x + 1/factorial(-1)", "var": "x", "to": "2"}), "2", "value"),
    (_ir("solve_equation", {"var": "x", "equation": "x + Sum(1/factorial(k - 3), (k, 1, 4)) = 2"}, vars_=[X, K],
         shape="set"), "EmptySet", "set"),
    (_ev("f(2)", functions=[{"name": "f", "args": ["x"], "expr": "x + 1/factorial(-1)"}]), "2", "value"),
    # every other text of the task: a point, a bound, an interval, a constraint
    (_ir("derivative", {"f": "x**2", "var": "x", "at": "1/factorial(-1)"}), "0", "value"),
    (_ir("limit", {"expr": "x + 1", "var": "x", "to": "1/factorial(-1)"}), "1", "value"),
    (_ir("definite_integral", {"integrand": "1", "var": "x", "a": "1/factorial(-1)", "b": "1"}), "1", "value"),
    (_ir("series_sum", {"term": "k", "var": "k", "lo": "1 + 1/factorial(-1)", "hi": "3"}, vars_=[K]), "6", "value"),
    (_ir("extremum", {"f": "x", "var": "x", "interval": "[1/(1/0), 1]", "which": "min"}), "0", "value"),
    (_ir("extremum", {"f": "x", "var": "x", "interval": "[1/(1/0), 1)", "which": "min"}), "0", "value"),
    (_ir("extremum", {"f": "x", "var": "x", "interval": "Interval(1/factorial(-1), 1)", "which": "min"}), "0", "value"),
    (dict(_ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, shape="set"),
          domain_of_discourse="Interval.open(1/factorial(-1), oo)"), "{2}", "set"),
    (_ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, vars_=[{"name": "x", "constraints": ["x > 1/factorial(-1)"]}],
         shape="set"), "{2}", "set"),
])
def test_cap_f1_every_path_abstains(ir, payload, kind):
    r = _run(ir, payload, kind)
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in _flags(r)


@pytest.mark.parametrize("claim", ["1/factorial(-1)", "1/zoo", "1/(1/0)", r"\frac{1}{(-1)!}", "0*factorial(-1)**(-1)"])
def test_cap_f1_a_claim_without_value_is_never_correct(claim):
    r = _run(_ev("0"), claim)
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in _flags(r)


@pytest.mark.parametrize("claim", ["Interval(1/factorial(-1), 2)", "[1/factorial(-1), 2]",
                                   "Union(Interval(1/zoo, 1), Interval(1, 2))", "[1/(1/0), 1] U [1, 2]"])
def test_cap_f1_a_set_claim_with_an_end_without_value_is_never_correct(claim):
    q = _ir("solve_inequality", {"inequality": "x*(x - 2) <= 0", "var": "x"}, shape="interval")
    r = _run(q, claim, "interval")
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in _flags(r)
    assert _run(q, "Interval(0, 2)", "interval").verdict == "CORRECT"
    assert _run(q, "[0, 2]", "interval").verdict == "CORRECT"


def test_cap_f1_a_set_text_is_read_by_its_parts():
    from mathverify.certify.domain import NO_VALUE
    from mathverify.normalize.parse import parse_set_as_written
    for t in ("(1/factorial(-1), 2]", "Interval.Lopen(1/factorial(-1), 2)", "{1, 2} U (1/zoo, 3)"):
        assert NO_VALUE in definedness_conditions(parse_set_as_written(t), None), t
    assert definedness_conditions(parse_set_as_written("(-oo, 0) U [2, oo)"), None) == []


def test_cap_f1_a_claim_without_value_is_still_refuted_where_every_reading_refutes_it():
    assert _run(_ev("5"), "1/factorial(-1)").verdict == "INCORRECT"


def test_cap_f1_a_claim_whose_convention_values_agree_is_not_a_claim_without_value():
    # an odd root of a negative number is read both ways (part d4a): 4 under each reading
    assert _run(_ev("4"), "(-8)**(2/3) - (-8)**(2/3) + 4").verdict == "CORRECT"


@pytest.mark.parametrize("claim,kind", [("1/factorial(-1) = 0", "compute"), ("4/factorial(-2) = 0", "compute"),
                                        ("1/factorial(-1) = 0", "eq"), ("1/zoo = 0", "compute"),
                                        (r"\frac{1}{\Gamma(0)} = 0", "compute")])
def test_cap_f1_a_step_on_a_pole_is_not_verified(claim, kind):
    r, status = _step(claim, kind)
    assert status == "unknown" and r.verdict == "CORRECT"


def test_cap_f1_a_step_wrong_under_every_reading_is_still_refuted():
    r, status = _step("4/factorial(-2) = 1")
    assert status == "refuted" and r.verdict == "INCORRECT"


def test_cap_f1_the_rules_fail_closed():
    from mathverify.certify.domain import NO_VALUE, is_no_value
    # the condition of the reciprocal raised; the pole's own rule decides, and NO_VALUE marks it
    with sp.evaluate(False):
        e = sp.Pow(sp.factorial(-1), -1)
    conds = definedness_conditions(e, None)
    assert sp.false in conds and any(is_no_value(c) for c in conds)
    # a rule that raises is never "no condition"
    w = parse_as_written("1/sqrt(factorial(-2))")
    assert NO_VALUE in definedness_conditions(w, None)


@pytest.mark.parametrize("src", ["[1/(1/0), 1]", "[1/factorial(-1), 1]"])
def test_cap_f1_a_bracketed_text_is_walked(src):
    assert sp.false in definedness_conditions(parse_as_written(src), None)


def test_cap_f1_the_factorial_family_has_its_poles():
    from mathverify.certify.domain import DEFINEDNESS_UNDECIDED, NO_VALUE
    half = sp.Rational(1, 2)
    with sp.evaluate(False):
        poles = [sp.factorial(-1), sp.factorial2(-2), sp.subfactorial(-1), sp.gamma(0), sp.gamma(-3),
                 sp.RisingFactorial(1, -2), sp.FallingFactorial(1, -2), sp.binomial(-1, half)]
        values = [sp.factorial(3), sp.factorial2(5), sp.subfactorial(3), sp.gamma(half), sp.gamma(5),
                  sp.RisingFactorial(-3, 2), sp.FallingFactorial(half, 2)]
    for e in poles:
        assert NO_VALUE in definedness_conditions(e, None), e
    for e in values:
        assert definedness_conditions(e, None) == [], e
    # a text no walk reads proves nothing
    assert definedness_conditions(object(), None) == [DEFINEDNESS_UNDECIDED]


@pytest.mark.parametrize("expr,value", [("1/factorial(2)", "1/2"), (r"\Gamma(5)", "24"), ("P(5, 2)", "20"),
                                        ("Sum(1/factorial(k), (k, 0, oo))", "E")])
def test_cap_f1_values_off_the_poles_stay(expr, value):
    assert _run(_ev(expr, vars_=[X, K]), value).verdict == "CORRECT"


def test_cap_f1_an_equation_defined_nowhere_keeps_its_empty_answer():
    r = _run(_ir("solve_equation", {"var": "x", "equation": "2*x = 4 + 1/(3 - 3)"}, shape="set"), "EmptySet", "set")
    assert r.verdict == "CORRECT"


# --- TAN-10, C1 -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr", ["Sum(k, (k, 1/2, 5/2))", r"\sum_{k=1/2}^{5/2} k", r"\sum_{k=0.5}^{2.5} k",
                                  "Sum(k, (k, 0.5, 2.5))", "Product(k, (k, 1/2, 5/2))", "Sum(k, (k, pi, pi + 1))",
                                  "Sum(k**2, (k, sqrt(2), sqrt(2) + 1))", "floor(Sum(k, (k, 1/2, 5/2)))",
                                  "Sum(1/k**2, (k, 1/2, oo))", "floor(Sum(k, (k, pi, pi + 1)))",
                                  "Sum(k, (k, 1/2 + 0*x, 5/2 + 0*x))"])
def test_tan10_limits_that_are_not_integers_are_not_read(expr):
    with pytest.raises(ParseError):
        parse_expr_str(expr, dict(_SAFE_NAMES, k=sp.Symbol("k", integer=True), x=sp.Symbol("x", real=True)))


@pytest.mark.parametrize("ir,payload", [
    (_ev("Sum(k, (k, 1/2, 5/2))", vars_=[K]), "9/2"),
    (_ev("Sum(k, (k, 1/2, 5/2))", vars_=[K]), "3"),
    (_ev("Sum(k, (k, a, a + 2))", ["a = 1/2"], [K, {"name": "a"}]), "9/2"),
    (_ev("Sum(k, (k, a, a + 2))", ["a = 1/2"], [K, {"name": "a"}]), "3"),
    (_ev("Sum(k, (k, m, n))", ["m = 1/2", "n = 5/2"], [K, {"name": "m"}, {"name": "n"}]), "9/2"),
    (_ev("Sum(k, (k, n, n + 2))", ["n = 1/2"], [K, {"name": "n", "domain": "real"}]), "9/2"),
    (_ir("limit", {"expr": "x + Sum(k, (k, 1/2, 5/2))", "var": "x", "to": "0"}, vars_=[X, K]), "9/2"),
])
def test_tan10_the_value_is_a_convention(ir, payload):
    assert _run(ir, payload).verdict == "UNKNOWN"


@pytest.mark.parametrize("claim", ["Sum(k, (k, 1/2, 5/2)) = 3", "Sum(k, (k, 1/2, 5/2)) = 9/2", r"\sum_{k=1/2}^{5/2} k = 3"])
def test_tan10_a_step_is_neither_verified_nor_refuted(claim):
    r, status = _step(claim, vars_=[X, K])
    assert status not in ("verified", "refuted") and r.verdict != "INCORRECT"


def test_tan10_an_open_bound_is_held_to_the_integers():
    from mathverify.certify.domain import _one_range_conditions
    n = sp.Symbol("n", real=True)
    assert _one_range_conditions(n, n + 2) == [sp.Contains(n, sp.S.Integers)]
    assert _one_range_conditions(sp.Rational(1, 2), sp.Rational(5, 2)) is None
    assert _one_range_conditions(sp.Rational(1, 2), sp.oo) is None
    assert _one_range_conditions(sp.Rational(1, 2), n) is None
    assert _one_range_conditions(sp.Integer(1), sp.Integer(3)) == []


# --- B1 ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr", [
    r"\lfloor \sum_{\alpha=3}^{\sqrt{1}} \alpha \rfloor", r"\lfloor \sum_{k_{1}=3}^{\sqrt{1}} k_{1} \rfloor",
    r"\lfloor \sum_{\mathrm{k}=3}^{\sqrt{1}} \mathrm{k} \rfloor", r"\lfloor \sum_{k\,=\,3}^{\sqrt{1}} k \rfloor",
    r"\lceil \sum_{\theta=\sqrt{9}}^{1} \theta \rceil", r"\left| \prod_{\theta=3}^{\sqrt{1}} \theta \right|",
    r"\lfloor \sum_{j_{0}=3}^{1} j_{0} \rfloor", r"\lfloor \sum_{k=3}^{\sum_{j=1}^{1} j} k \rfloor",
])
def test_b1_a_latex_reversed_range_is_refused_whatever_the_index(expr):
    r = _run(_ev(expr), "-2")
    assert r.verdict == "UNKNOWN" and "parse_error" in _flags(r)


@pytest.mark.parametrize("expr,value", [(r"\sum_{\alpha=1}^{3} \alpha", "6"), (r"\lfloor \sum_{k=1}^{\sqrt{9}} k \rfloor", "6"),
                                        (r"\sum_{k=1}^{\infty} \frac{1}{k^2}", "pi**2/6")])
def test_b1_forward_latex_ranges_are_read(expr, value):
    assert _run(_ev(expr), value).verdict == "CORRECT"


# --- TAN-12 -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr,givens,value", [
    ("Product(Sum(1, (j, 1, k)), (k, 1, n))", ["n = 3"], "6"), ("Sum(k*Sum(1, (j, 1, k)), (k, 1, n))", ["n = 3"], "14"),
    ("Sum(Product(j, (j, 1, k)), (k, 1, n))", ["n = 3"], "9"), ("Sum(2**k*Sum(1, (j, 1, k)), (k, 1, n))", ["n = 2"], "10"),
])
def test_tan12_an_inner_range_is_decided_at_each_outer_value(expr, givens, value):
    V = [K, N, J]
    assert _run(_ev(expr, givens, V), value).verdict == "CORRECT"
    assert _run(_ev(expr, givens, V), str(int(value) + 1)).verdict == "INCORRECT"


@pytest.mark.parametrize("expr,value", [("Product(Sum(1, (j, 1, k)), (k, 1, n))", "factorial(n)"),
                                        ("Product(Sum(1, (j, k, 2)), (k, 1, 5))", "0")])
def test_tan12_an_undecided_range_is_not_called_undefined(expr, value):
    r = _run(_ev(expr, vars_=[K, N, J]), value)
    assert r.verdict == "UNKNOWN"
    assert "problem_undefined_as_written" not in _flags(r) and "problem_definedness_undecided" in _flags(r)


# --- G14 --------------------------------------------------------------------------------------------------

def _lim(expr, to="oo", v=XP):
    return _ir("limit", {"expr": expr, "var": "x", "to": to}, vars_=[v])


@pytest.mark.parametrize("expr,v,value", [("factorial(x - 2)/x**x", XP, "0"), ("factorial(x - 2)/factorial(x)", XP, "0"),
                                          ("binomial(x, 3)/x**3", XP, "1/6"), ("factorial(x - 2)/x**x", XI, "0"),
                                          ("factorial(2*x - 3)/x**(2*x)", XP, "0")])
def test_g14_a_sequence_limit_reads_the_tail(expr, v, value):
    assert _run(_lim(expr, v=v), value).verdict == "CORRECT"
    assert _run(_lim(expr, v=v), "1").verdict == "INCORRECT"


@pytest.mark.parametrize("expr,to,v", [("factorial(x - 2)/x**x", "oo", X), ("factorial(x + 2)/x**x", "-oo", XI),
                                        ("factorial(x/2)/x**x", "oo", XP)])     # (x/2)! at every odd x
def test_g14_no_tail_no_value(expr, to, v):
    r = _run(_lim(expr, to, v), "0")
    assert r.verdict == "UNKNOWN" and "membership_condition" in _flags(r)


def test_the_undecided_flag_blocks_a_positive_verdict():
    from mathverify.certify.base import result, unknown
    from mathverify.fuse.rules import fuse
    layers = [unknown("intake.definedness", "x", flags=["problem_definedness_undecided"]),
              result("certify.x", "pass", 0.99, True, {}, 0.0, primary=True)]
    assert fuse(layers)["verdict"] != "CORRECT"
