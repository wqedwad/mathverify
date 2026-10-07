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

Round 2 (the review of d4f, 7 Oct 2026), each measured wrong on eedd182: YO-1 a text the as-written reading does
not take was read as "no condition" (x**2/x + Σ_{k=√1}^{3} k = 6 -> {0} CORRECT); YO-2 det/eigmax computed as written
folded √x·√x; YO-3 a bound not declared an integer dropped the non-integer points (3n + 3 + sin(πn) CORRECT); YO-4 a
sequence undefined at every odd index had a limit; YO-5, YO-6 the claim read without its pins, its relation form or
its option, the problem's list parameters and membership givens; YO-7 ∞⁰ = 1; RK-F1 {7/3} refuted at a non-integer
bound; RK-F2 Γ's open condition blocked every limit, integral and derivative; RK-F3 over ℂ sqrt(-4) was no value;
RK-F4 LaTeX \\frac{1}{0} folded to zoo.
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
    # as a convention (RK-F1): holds at an integer, undecided elsewhere, never false
    from mathverify.certify.domain import INTEGER_BOUND, _one_range_conditions
    n = sp.Symbol("n", real=True)
    assert _one_range_conditions(n, n + 2) == [sp.Contains(n, INTEGER_BOUND)]
    assert sp.Contains(sp.Integer(3), INTEGER_BOUND) is sp.true
    assert sp.Contains(sp.Rational(7, 3), INTEGER_BOUND) not in (sp.true, sp.false)
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


# === round 2: the review of d4f (`denetim/2026-10-01/d4/saldiri/d4f/`), each case measured wrong on eedd182 =========

R1 = "Sum(k, (k, sqrt(1), 3))"                                         # = 6
DET = "det(Matrix([[sqrt(x), 1], [-1, sqrt(x)]]))"                     # = x + 1 on x >= 0
NR = {"name": "n", "domain": "real"}


def _solve(eq, vars_=None, givens=()):
    return _ir("solve_equation", {"var": "x", "equation": eq}, givens, vars_, shape="set")


def _status(r):
    return next(la for la in r.layers if la.layer == "steps.refute").evidence["steps"][-1]["status"]


# --- YO-1: a text the as-written reading does not take is not proved defined --------------------------------------

@pytest.mark.parametrize("ir,payload,kind", [
    (_solve(f"x**2/x + {R1} = 6", [X, K]), "{0}", "set"),              # {} is the answer: 0 is no point of x**2/x
    (_solve(f"sqrt(x)**2 + {R1} = 5", [X, K]), "{-1}", "set"),
    (_solve(r"\frac{x^2}{x} + \sum_{k=\sqrt{1}}^{3} k = 6", [X, K]), "{0}", "set"),
    (_ev(f"x/x + {R1}", ["x = 0"], [X, K]), "7", "value"),
    (_ev(f"1/factorial(-1) + {R1}", vars_=[K]), "6", "value"),
])
def test_yo1_an_unread_text_is_not_proved_defined(ir, payload, kind):
    assert _run(ir, payload, kind).verdict != "CORRECT"


def test_yo1_a_bound_is_read_with_exact_simplification():
    assert _run(_ev(R1, vars_=[K]), "6").verdict == "CORRECT"
    assert _run(_ev("Sum(k, (k, 1, log(8, 2)))", vars_=[K]), "6").verdict == "CORRECT"
    c = "sqrt(2) + sqrt(3) - sqrt(5 + 2*sqrt(6)) + 1/2"                # = 1/2: not an integer, TAN-10
    for v in ("9/2", "3"):
        assert _run(_ev(f"Sum(k, (k, {c}, {c} + 2))", vars_=[K]), v).verdict == "UNKNOWN"


def test_yo1_a_step_the_as_written_reading_does_not_take_is_not_verified():
    r = _run(_ev("x", ["x = 0"], [X, K]), "0", steps=[("compute", f"x/x + {R1} = 7")])
    assert _status(r) != "verified"


@pytest.mark.parametrize("value", ["9/2", "3"])
def test_yo1_a_step_the_as_written_reading_refuses_is_neither_verified_nor_refuted(value):
    # the bounds are 1/2 in nested roots: refused as written (TAN-10), SymPy's value steps to 9/2
    c = "sqrt(2) + sqrt(3) - sqrt(5 + 2*sqrt(6)) + 1/2"
    r = _run(_ev("x", ["x = 1"], [X, K]), "1", steps=[("compute", f"Sum(k, (k, {c}, {c} + 2)) = {value}")])
    assert _status(r) not in ("verified", "refuted") and r.verdict != "INCORRECT"


def test_yo6_a_closed_list_parameter_without_a_value_is_undefined():
    q = _ir("count_solutions", {"bounds": {"x": ["1/(1/0)", "3"], "y": ["0", "3"]}}, ["x + y = 2"],
            [{"name": "x", "domain": "nonneg_integer"}, {"name": "y", "domain": "nonneg_integer"}], shape="count")
    r = _run(q, 3, "count")
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in _flags(r)


@pytest.mark.parametrize("steps", [
    [("compute", "factor(x**2 - 4) = (x - 2)*(x + 2)")],
    [("compute", "det(Matrix([[30, 1], [88, 4]]))/det(Matrix([[1, 1], [2, 4]])) = 16")],
])
def test_yo1_what_the_as_written_reading_still_takes(steps):
    assert _status(_run(_ev("x", ["x = 1"]), "1", steps=steps)) == "verified"


def test_yo1_a_membership_step_is_read_part_by_part():
    r = _run(_solve("x**2 - 4*x = 0"), "{0, 4}", "set", steps=[("eq", "x**2 - 4*x = 0"), ("eq", "x in {0, 4}")])
    assert r.verdict == "CORRECT" and _status(r) == "verified"


def test_yo1_a_compound_text_is_read_part_by_part():
    from mathverify.normalize.parse import build_namespace, parse_set_as_written
    ns = build_namespace(None, {"x": sp.Symbol("x")})
    for txt in ("x = 1 or x = 2", "x < -1 or x > 3", "x > 0 and x < 3", "(x > 0) & (x < 3)", r"0 < x \le 3",
                r"x \notin (-3, 3)", "x in {0, 4}"):
        assert parse_set_as_written(txt, ns) is not None, txt
    for given, verdict in (("x > 0 and x < 3", "CORRECT"), ("x > 1/(1 - 1) and x < 3", "UNKNOWN")):
        q = _ir("solve_inequality", {"var": "x", "inequality": "x**2 < 4"}, [given], shape="interval")
        assert _run(q, "Interval.open(0, 2)", "interval").verdict == verdict, given


def test_yo1_an_unread_text_is_never_read_as_no_condition(monkeypatch):
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.steps.deterministic import _convention_as_written, _undefined_as_written
    ctx = make_ctx(ProblemIR.from_dict(_ev("x")))
    assert ctx._unread("x + 1") == "undecided" and ctx._unread("((") is None
    assert _undefined_as_written("x + 1 = 2", ctx.ns, unread=True) is False
    assert _convention_as_written("x + 1 = 2", ctx.ns) is False
    # a text the as-written reading does not take: not proved defined, and SymPy's value refutes nothing
    monkeypatch.setattr("mathverify.normalize.parse.parse_set_as_written", lambda *a, **k: None)
    assert _undefined_as_written("x + 1 = 2", ctx.ns, unread=True) is True
    assert _undefined_as_written("x + 1 = 2", ctx.ns, unread=False) is False
    assert _convention_as_written("x + 1 = 2", ctx.ns) is True


def test_yo1_an_unread_claim_text_is_flagged(monkeypatch):
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.solution import Solution
    from mathverify.verifier import _claim_without_value
    ctx = make_ctx(ProblemIR.from_dict(_ev("0")))
    sol = Solution.from_dict({"claimed_answer": {"kind": "value", "payload": "0"}, "steps": []})
    assert _claim_without_value(sol, ctx) == []
    monkeypatch.setattr("mathverify.normalize.parse.parse_set_as_written", lambda *a, **k: None)
    assert _claim_without_value(sol, ctx) == ["0"]


@pytest.mark.parametrize("expr,givens", [("x/x + {S}", ["x = 0"]), ("1/factorial(-1) + {S}", [])])
def test_yo1_the_text_around_an_undecided_bound_is_still_read(expr, givens):
    c = "sqrt(2) + sqrt(3) - sqrt(5 + 2*sqrt(6)) + 1/2"
    r = _run(_ev(expr.format(S=f"Sum(k, (k, {c}, {c} + 2))"), givens, [X, K]), "11/2")
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in _flags(r)


def test_yo1_a_step_wrong_under_every_reading_is_still_refuted():
    # 0**0 is 1 or undefined, 4/(-2)! is 0 under 1/Γ or undefined: neither is 5, nor 1
    assert _status(_run(_ev("x", ["x = 1"]), "1", steps=[("compute", "0**0 = 5")])) == "refuted"
    assert _status(_run(_ev("x", ["x = 1"]), "1", steps=[("compute", "4/factorial(-2) = 1")])) == "refuted"


def test_yo1_a_latex_matrix_parameter_is_read_as_written():
    ir = _ir("linalg", {"op": "inverse", "matrix": r"\begin{bmatrix}1&2\\3&4\end{bmatrix}"}, vars_=[], shape="expression")
    assert _run(ir, "Matrix([[-2, 1], [3/2, -1/2]])", "expression").verdict == "CORRECT"


def test_yo1_a_dne_claim_and_its_option_text_carry_no_value_to_read():
    ir = dict(_ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}),
              options={"A": "-1", "B": "0", "C": "1", "D": "2", "E": "limit yoktur"})
    sol = {"claimed_answer": {"kind": "dne", "payload": None, "option": "E"}, "steps": []}
    assert verify(ir, sol).verdict == "CORRECT"


@pytest.mark.parametrize("given", [r"0 < x \le 3", r"0 \lt x \lt 3"])
def test_yo1_a_latex_chain_given_is_read_as_written(given):
    q = _ir("solve_inequality", {"var": "x", "inequality": "x**2 < 4"}, [given], shape="interval")
    assert _run(q, "Interval.open(0, 2)", "interval").verdict == "CORRECT"


# --- YO-2: no matrix operation is computed as written -------------------------------------------------------------

@pytest.mark.parametrize("eq,payload", [(f"{DET} = -2", "{-3}"),
                                        (r"\begin{vmatrix} \sqrt{x} & 1 \\ -1 & \sqrt{x} \end{vmatrix} = -2", "{-3}"),
                                        ("eigmax(Matrix([[sqrt(x)**2, 0], [0, -5]])) = -1", "{-1}")])
def test_yo2_a_matrix_entry_keeps_its_condition(eq, payload):
    assert _run(_solve(eq), payload, "set").verdict != "CORRECT"


def test_yo2_controls():
    assert _run(_solve("det(Matrix([[x, 1], [1, x]])) = 0"), "{-1, 1}", "set").verdict == "CORRECT"
    assert _run(_ev("det(Matrix([[2, 1], [1, 3]]))", vars_=[]), "5").verdict == "CORRECT"


def test_yo2_latex_matrix_functions_are_not_computed_as_written():
    m = r"\begin{pmatrix}\sqrt{x}&1\\-1&\sqrt{x}\end{pmatrix}"
    t = r"\begin{pmatrix}\sqrt{x}^2&0\\0&1\end{pmatrix}"
    assert _run(_solve(rf"\det {m} = -2"), "{-3}", "set").verdict != "CORRECT"            # was CORRECT on eedd182
    assert _run(_solve(rf"\operatorname{{tr}} {t} = 0"), "{-1}", "set").verdict != "CORRECT"
    assert _run(_ev(r"\det \begin{pmatrix}1&2\\3&4\end{pmatrix}", vars_=[]), "-2").verdict == "CORRECT"
    assert _run(_solve(r"\det \begin{pmatrix}x&1\\1&x\end{pmatrix} = 0"), "{-1, 1}", "set").verdict == "CORRECT"


# --- YO-3, RK-F1: a bound not declared an integer is held to the integers as a convention ---------------------------

@pytest.mark.parametrize("expr,claim,vars_", [
    ("Sum(k, (k, n, n + 2))", "3*n + 3 + sin(pi*n)", [NR, K]), ("Sum(1, (k, n, n + 2))", "3 + sin(pi*n)", [NR, K]),
    (r"\sum_{k=n}^{n+2} k", "3*n + 3 + sin(pi*n)", [NR, K]), ("Sum(k, (k, n, n + 2))", "3*n + 3", [NR, K]),
    ("Sum(k, (k, 1, n))", "n*(n + 1)/2", [K, {"name": "n"}]),
])
def test_yo3_no_claim_is_certified_where_a_bound_may_be_no_integer(expr, claim, vars_):
    assert _run(_ev(expr, vars_=vars_), claim).verdict == "UNKNOWN"


def test_yo3_a_step_whose_own_bound_may_be_no_integer_is_not_verified():
    step = [("compute", "Sum(k, (k, n, n + 2)) = 3*n + 3")]
    assert _status(_run(_ev("n", vars_=[NR, K]), "n", steps=step)) != "verified"
    assert _status(_run(_ev("n", vars_=[N, K]), "n", steps=step)) == "verified"


def test_yo3_controls():
    assert _run(_ev("Sum(k, (k, n, n + 2))", vars_=[NR, K]), "3*n + 4").verdict == "INCORRECT"   # wrong on ℤ
    assert _run(_ev("Sum(k, (k, n, n + 2))", vars_=[N, K]), "3*n + 3").verdict == "CORRECT"
    assert _run(_ev("Sum(k, (k, 1, n))", ["n = 4"], [NR, K]), "10").verdict == "CORRECT"


@pytest.mark.parametrize("eq,payload", [("Sum(k, (k, x, x + 2)) = 10", "{7/3}"), ("Sum(k, (k, x, x + 2)) = 10", "EmptySet"),
                                        ("Product(k, (k, x, x + 1)) = 15/4", "{-5/2, 3/2}"),
                                        ("x + Sum(1, (k, x, x + 2)) = 7/2", "{1/2}")])
def test_rkf1_a_root_at_a_non_integer_bound_is_neither_kept_nor_dropped(eq, payload):
    assert _run(_solve(eq, [X, K]), payload, "set").verdict == "UNKNOWN"


def test_rkf1_a_step_is_not_refuted_at_an_integer_the_bound_does_not_reach():
    r = _run(_solve("Sum(k, (k, x, x + 2)) = 10", [X, K]), "EmptySet", "set", steps=[("eq", "3*x + 3 = 10")])
    assert _status(r) != "refuted" and r.verdict != "INCORRECT"


def test_rkf1_the_condition_is_a_convention():
    from mathverify.certify.domain import INTEGER_BOUND, convention_split, is_integer_bound
    n = sp.Symbol("n", real=True)
    c = sp.Contains(n, INTEGER_BOUND)
    assert is_integer_bound(c)
    fwd, back = convention_split(c, n)
    assert fwd == sp.S.Integers and back.contains(sp.Rational(1, 2)) is sp.true
    fwd2, _ = convention_split(sp.Contains(n / 2, INTEGER_BOUND), n)
    assert fwd2.contains(4) is sp.true and fwd2.contains(3) is not sp.true


# --- YO-4: a sequence's limit reads a tail where every condition holds ----------------------------------------------

@pytest.mark.parametrize("expr", ["factorial(x - 2)/x**x + cos(pi*x/2)/cos(pi*x/2)",
                                  "factorial(x - 2)*x**2/factorial(x) + 0/sin(pi*x/3)",
                                  "factorial(x - 2)/factorial(x)*x**2 + 0/(1 - (-1)**x)", "cos(pi*x/2)/cos(pi*x/2)"])
def test_yo4_a_sequence_undefined_at_infinitely_many_indices_has_no_limit_to_read(expr):
    r = _run(_lim(expr), "1")
    assert r.verdict == "UNKNOWN" and "sequence_undefined_on_the_tail" in _flags(r)
    assert _run(_lim(expr), None, "dne").verdict == "UNKNOWN"


@pytest.mark.parametrize("expr,v,value", [("factorial(x - 2)*x**2/factorial(x) + 0/(x - 5)", XP, "1"),
                                          ("(1 + 1/x)**x", XP, "E"), ("x/(x**2 - 9)", XI, "0"), ("cos(x)/cos(x)", X, "1")])
def test_yo4_controls(expr, v, value):
    assert _run(_lim(expr, v=v), value).verdict == "CORRECT"


# --- YO-5, YO-6: no value on any path of the claim or the problem ---------------------------------------------------

A_ = [X, {"name": "a"}]


@pytest.mark.parametrize("ir,payload,kind", [
    (_ir("limit", {"expr": "a*x", "var": "x", "to": "0"}, ["a = 1"], A_), "1/factorial(-a)", "value"),
    (_ir("derivative", {"f": "a*x", "var": "x", "at": "1"}, ["a = 0"], A_), "a/a - 1", "value"),
    (_ir("solve_inequality", {"var": "x", "inequality": "x >= 0"}, shape="interval"), "x >= 1/(1/0)", "interval"),
    (_ir("solve_inequality", {"var": "x", "inequality": "x*(x - 2) < 0"}, shape="interval"), "1/factorial(-1) < x < 2",
     "interval"),
])
def test_yo5_the_claim_is_read_at_its_pins_and_as_written(ir, payload, kind):
    r = _run(ir, payload, kind)
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in _flags(r)


def test_yo5_the_option_text():
    ir = dict(_ev("0"), options={"A": "1/factorial(-1)", "B": "1"})
    sol = {"claimed_answer": {"kind": "value", "payload": "0", "option": "A"}, "steps": []}
    assert verify(ir, sol).verdict == "UNKNOWN"


@pytest.mark.parametrize("ir,payload,kind", [
    (_ir("equation_of", {"object": "line_points", "p1": ["1/factorial(-1)", "0"], "p2": ["1", "1"]},
         vars_=[{"name": "x"}, {"name": "y"}], shape="equation"), "y = x", "equation"),
    (_ir("recurrence_term", {"recurrence": "a(n) = a(n-1) + 1", "initial": {"1": "1/factorial(-1)"}, "index": 4,
                             "var": "n"}, vars_=[{"name": "n", "domain": "positive_integer"}]), "3", "value"),
    (_ir("extremum", {"f": "x", "var": "x", "which": "min"}, ["x ∈ [1/factorial(-1), 1]"]), "0", "value"),
])
def test_yo6_every_problem_text_is_read(ir, payload, kind):
    assert _run(ir, payload, kind).verdict == "UNKNOWN"


def test_yo6_a_sequence_step():
    ir = _ir("recurrence_term", {"recurrence": "a(n) = a(n-1) + 1", "initial": {"1": "1"}, "index": 4, "var": "n"},
             vars_=[{"name": "n", "domain": "positive_integer"}])
    assert _status(_run(ir, "4", steps=[("compute", "a(3) = 3 + 1/factorial(-1)")])) != "verified"


# --- YO-7: ∞⁰ is a convention -------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr", ["oo**0", r"\infty^{0}", "(-oo)**0", "oo**(1 - 1)"])
def test_yo7_infinity_to_the_zero(expr):
    assert _run(_ev(expr), "1").verdict == "UNKNOWN"


def test_yo7_claim_and_step():
    assert _run(_ev("1"), "oo**0").verdict == "UNKNOWN"
    assert _status(_run(_ev("x", ["x = 1"]), "1", steps=[("compute", "oo**0 = 1")])) != "verified"
    assert _run(_ev("2**0"), "1").verdict == "CORRECT"


# --- RK-F2, RK-F3, RK-F4 ------------------------------------------------------------------------------------------

XPR = {"name": "x", "domain": "positive_real"}


@pytest.mark.parametrize("ir,right,wrong", [
    (_lim(r"x \Gamma(x)", "0", X), "1", "0"), (_lim(r"\Gamma(x)", "3", XPR), "2", "6"),
    (_lim(r"\frac{\Gamma(x + 1/2)}{\sqrt{x}\Gamma(x)}", "oo", X), "1", "2"),
    (_ir("definite_integral", {"integrand": r"x \frac{\Gamma(1+x)}{\Gamma(1+x)}", "var": "x", "a": "0", "b": "1"}), "1/2", "1"),
    (_ir("derivative", {"f": r"\frac{\Gamma(x+1)}{\Gamma(x)}", "var": "x", "at": "2"}, vars_=[XPR]), "1", "2"),
])
def test_rkf2_gamma_is_defined_where_the_task_reads_it(ir, right, wrong):
    assert _run(ir, right).verdict == "CORRECT"
    assert _run(ir, wrong).verdict == "INCORRECT"


@pytest.mark.parametrize("ir", [_ir("derivative", {"f": r"\Gamma(x)", "var": "x", "at": "0"}),
                                _ir("definite_integral", {"integrand": r"\Gamma(x)", "var": "x", "a": "-1/2", "b": "1/2"}),
                                _lim("factorial(x)", "3", X)])
def test_rkf2_not_where_a_pole_or_a_natural_number_condition_is(ir):
    assert _run(ir, "0").verdict != "CORRECT"


@pytest.mark.parametrize("ir,claim", [
    (_ir("definite_integral", {"integrand": r"x \frac{\Gamma(x)}{\Gamma(x)}", "var": "x", "a": "-1/2", "b": "1/2"}), "0"),
    (_ir("definite_integral", {"integrand": r"\frac{\Gamma(x+1)}{\Gamma(x+1)}", "var": "x", "a": "-3/2", "b": "-1/2"}), "1"),
    (_ir("derivative", {"f": r"\frac{\Gamma(x+1)}{\Gamma(x)}", "var": "x", "at": "0"}), "1"),
    (_ir("derivative", {"f": r"\frac{\Gamma(x+1)}{\Gamma(x)}", "var": "x", "at": "-2"}), "1"),
])
def test_rkf2_a_pole_the_value_parse_simplifies_away_is_still_read(ir, claim):
    assert _run(ir, claim).verdict != "CORRECT"


@pytest.mark.parametrize("expr,claim", [("2*I", "sqrt(-4)"), ("-6", "sqrt(-4)*sqrt(-9)"), (r"\sqrt{-25}", r"5\sqrt{-1}")])
def test_rkf3_over_c_a_principal_value_is_a_value(expr, claim):
    ir = dict(_ev(expr, vars_=[]), domain_of_discourse="complex")
    assert _run(ir, claim).verdict == "CORRECT"


def test_rkf3_no_value_stays_no_value_over_c():
    ir = dict(_ev("0", vars_=[]), domain_of_discourse="complex")
    assert _run(ir, "1/factorial(-1)").verdict == "UNKNOWN"


@pytest.mark.parametrize("eq", [r"x + \frac{1}{0} = 2", r"x + \frac{0}{0} = 1", r"2x = 4 + \frac{1}{0}", r"\frac{2}{0} = x"])
def test_rkf4_a_latex_division_by_zero_is_written(eq):
    assert _run(_solve(eq), "EmptySet", "set").verdict == "CORRECT"


def test_rkf4_controls():
    assert _run(_solve(r"x + \frac{1}{0} = 2"), "{2}", "set").verdict == "INCORRECT"
    assert _run(_solve(r"x + \frac{1}{\frac{1}{0}} = 2"), "{2}", "set").verdict != "CORRECT"
    assert _run(_solve(r"x + 0 \cdot \frac{1}{0} = 2"), "{2}", "set").verdict != "CORRECT"
