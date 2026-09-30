"""Findings of the adversarial audit of the V14 fix (29 Sep 2026): the parser's gcd/lcm, bound
variables and arccot, and the paths they touched. Each case was measured wrong before its fix, on
the V14 commit itself (5fca95f) or on the code before it (35af293): a wrong answer or step accepted,
a right one refuted, or text read as something else.
"""
import random

import pytest
import sympy as sp

from mathverify.normalize.parse import ParseError, check_claim_is_value, parse_relation, _SAFE_NAMES
from mathverify.verifier import verify

XR = [{"name": "x", "domain": "real"}]
XP = [{"name": "x", "domain": "positive_real"}]
NN = [{"name": "n", "domain": "positive_integer"}]
KP = [{"name": "k", "domain": "positive_integer"}]


def _ir(kind, params, vars_=XR, givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _run(ir, payload, steps=(), kind="value"):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _steps(r):
    for layer in r.layers:
        if layer.layer == "steps.refute":
            return [s["status"] for s in layer.evidence.get("steps", [])]
    return []


# --- the bound-variable rewrite ------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["compute", "eq"])
def test_a_wrong_integral_step_is_refuted_whatever_the_step_kind(kind):
    """The step namespace wraps Integral in its own function; compute claims were not rebound, so
    x positive folded |x| to x and the false step "= 0" was verified (verdict CORRECT)."""
    r = _run(_ir("evaluate", {"expr": "Integral(Abs(x), (x, -1, 1))"}, XP), "1",
             [(kind, "Integral(Abs(x), (x, -1, 1)) = 0")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]
    r = _run(_ir("evaluate", {"expr": "Integral(Abs(x), (x, -1, 1))"}, XP), "1",
             [(kind, "Integral(Abs(x), (x, -1, 1)) = 1")])
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"]


def test_steps_about_the_integration_variable_keep_the_integrands_conditions():
    """Read as written, the conditions of an integral's body stay on the variable of that name:
    moved to the dummy, the false step x**2 + 1 = 0 went unchecked (CORRECT) and the true
    log(x**2) = 2*log(x) on [1, e] was refuted."""
    r = _run(_ir("evaluate", {"expr": "Integral(1/x, (x, 1, 2))"}), "log(2)",
             [("eq", "x**2 + 1 = 0"), ("compute", "log(2) - log(1) = log(2)")])
    assert r.verdict == "INCORRECT" and _steps(r)[0] == "refuted"
    r = _run(_ir("evaluate", {"expr": "Integral(log(x), (x, 1, E))"}), "1",
             [("eq", "log(x**2) = 2*log(x)"), ("compute", "E - E + 1 = 1")])
    assert r.verdict == "CORRECT"


def test_a_latex_relation_that_cannot_be_read_is_a_parse_error():
    with pytest.raises(ParseError):
        parse_relation(r"\frac{x}{", dict(_SAFE_NAMES, x=sp.Symbol("x", real=True)))


@pytest.mark.parametrize("claim", [r"\sum_{k=1}^{2} k", r"\int_{0}^{1} x dx", r"\prod_{k=1}^{3} k",
                                   r"\lim_{x \to 0} x", [r"\int_{0}^{1} t dt"]])
def test_a_subscripted_latex_binder_is_a_computation_not_a_value(claim):
    from mathverify.normalize.parse import ClaimNotAValue
    with pytest.raises(ClaimNotAValue):
        check_claim_is_value(claim)


# --- gcd / lcm ------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr,claim", [("gcd(n, n + 1)", "1"), ("gcd(n, 1)", "1"), ("lcm(n, n + 1)", "n*(n + 1)"),
                                        ("gcd(n, 2*n)", "n"), ("gcd(n, 4)*lcm(n, 4)", "4*n")])
def test_a_true_gcd_identity_is_not_refuted(expr, claim):
    """The random-point check could not evaluate the class and read that as a counterexample."""
    assert _run(_ir("evaluate", {"expr": expr}, NN), claim).verdict != "INCORRECT"


@pytest.mark.parametrize("expr,claim", [("gcd(n, 4)", "4"), ("gcd(n, 6)", "1"), ("gcd(n, n + 1)", "2")])
def test_a_false_gcd_identity_is_still_refuted(expr, claim):
    assert _run(_ir("evaluate", {"expr": expr}, NN), claim).verdict == "INCORRECT"


def test_agreement_at_sampled_integers_proves_no_gcd_identity():
    """gcd(n, 1000003) and 1 agree at every small integer; only n = 1000003k tells them apart."""
    assert _run(_ir("evaluate", {"expr": "gcd(n, 1000003)"}, NN), "1").verdict != "CORRECT"


@pytest.mark.parametrize("expr,to,claim", [("gcd(x, 4)", "0", "4"), ("gcd(x, 6)/x", "2", "1"), ("lcm(x, 2)", "1", "2")])
def test_a_limit_nothing_numeric_corroborates_is_not_certified(expr, to, claim):
    """SymPy substitutes into a function it does not know; lim_{x->0} gcd(x, 4) = 4 was CORRECT."""
    r = _run(_ir("limit", {"expr": expr, "var": "x", "to": to}), claim)
    assert r.verdict == "UNKNOWN"


def test_gcd_is_symmetric():
    ir = _ir("evaluate", {"expr": "gcd(n, 4)"}, NN, shape="expression")
    assert _run(ir, "gcd(4, n)", kind="expression").verdict == "CORRECT"


def test_the_lean_series_statement_reads_the_index_over_its_range():
    """k declared positive folded Abs(k) to k: the goal "∑_{k=-2}^{2} k = 0" is true in Lean for the
    wrong claim 0 (the sum of |k| is 6)."""
    from mathverify.formal.statement import build_statement
    ir = _ir("series_sum", {"term": "Abs(k)", "var": "k", "lo": "-2", "hi": "2"}, KP)
    st = build_statement(ir, {"kind": "value", "payload": "0", "option": None})
    assert st is None or "|" in st.goal


def test_latex_gcd_is_the_integer_gcd():
    """latex2sympy computes \\gcd with SymPy's polynomial gcd: n = 12, \\gcd(n, 4) certified 1."""
    ir = _ir("evaluate", {"expr": r"\gcd(n, 4)"}, NN, ["n = 12"])
    assert _run(ir, "4").verdict == "CORRECT"
    assert _run(ir, "1").verdict == "INCORRECT"


@pytest.mark.parametrize("step", [r"\gcd(84, 120) = 7", r"\operatorname{lcm}(4, 6) = 7", r"50\% = 1/3"])
def test_a_false_closed_latex_step_is_refuted(step):
    """UnevaluatedExpr kept the relation from evaluating and the set route called it proved."""
    r = _run(_ir("evaluate", {"expr": "n"}, NN, ["n = 12"]), "12", [("eq", step), ("eq", "n = 12")])
    assert r.verdict == "INCORRECT" and _steps(r)[0] == "refuted"


def test_nothing_is_certified_about_the_gcd_of_irrational_numbers():
    assert _run(_ir("evaluate", {"expr": "gcd(pi, 2)"}, []), "1").verdict == "UNKNOWN"
    r = _run(_ir("evaluate", {"expr": "x"}, XR, ["x = 1"]), "1", [("eq", "gcd(pi, 2) != 1"), ("eq", "x = 1")])
    assert _steps(r)[0] != "verified"


def test_an_unbounded_range_is_sampled():
    from mathverify.equiv.random_point import _sample_one
    rng = random.Random(0)
    vals = [_sample_one(sp.Range(2, sp.oo), rng) for _ in range(20)]
    assert all(v is not None and v >= 2 for v in vals)
    assert all(v <= 5 for v in (_sample_one(sp.Range(-sp.oo, 6), rng) for _ in range(20)))


def test_a_closed_gcd_read_as_written_has_its_value_in_a_domain():
    r = _run(_ir("domain_of", {"expr": "sqrt(x - lcm(-4, 6))", "var": "x"}, shape="set"), "[12, oo)", kind="interval")
    assert r.verdict == "CORRECT"


# --- arccot ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr,claim,want", [
    ("1/sin(arccot(x)+arccot(2))", "Complement(Reals, {-2})", "CORRECT"),
    ("1/sin(arccot(x)+arccot(2))", "EmptySet", "INCORRECT"),     # 5fca95f: CORRECT (sin of the nest -> 0)
    ("1/sin(arccot(x)+pi/2)", "Complement(Reals, {0})", "CORRECT"),
    ("log(sin(arccot(x)+arccot(2)))", "Interval.open(-2, oo)", "CORRECT"),
])
def test_arccot_read_as_written_is_one_function(expr, claim, want):
    r = _run(_ir("domain_of", {"expr": expr, "var": "x"}, shape="set"), claim, kind="set")
    assert r.verdict == want


@pytest.mark.parametrize("kind,rel,claim", [
    ("solve_equation", "1/sin(arccot(x)+arccot(2)) = sqrt(2)", "{}"),
    ("solve_inequality", "1/sin(arccot(x)+arccot(2)) > 0", "{}"),
])
def test_arccot_sums_do_not_empty_a_solution_set(kind, rel, claim):
    r = _run(_ir(kind, {"var": "x"}, XR, [rel], shape="set"), claim, kind="set")
    assert r.verdict == "INCORRECT"


@pytest.mark.parametrize("step", [r"\cot^{-1}(-1) = -\frac{\pi}{4}", r"\operatorname{arccot}(-1) = -\frac{\pi}{4}"])
def test_a_false_latex_arccot_step_stays_a_relation_and_is_refuted(step):
    r = _run(_ir("evaluate", {"expr": "arccot(-1)"}, []), "3*pi/4",
             [("compute", step), ("compute", "pi - pi/4 = 3*pi/4")])
    assert r.verdict == "INCORRECT" and _steps(r)[0] == "refuted"


def test_a_domain_solveset_gets_wrong_is_not_certified():
    """solveset reads cos(atan(x) + atan(2)) != 0 as x != -2 (the root is 1/2)."""
    ir = _ir("domain_of", {"expr": "tan(arccot(x)+arccot(2))", "var": "x"}, shape="set")
    assert _run(ir, "Complement(Reals, {-2})", kind="set").verdict != "CORRECT"


@pytest.mark.parametrize("claim", ["oo", "-oo"])
def test_tan_of_pi_over_2_written_with_arccot_has_no_value(claim):
    r = _run(_ir("evaluate", {"expr": "tan(arccot(2)+arccot(1/2))"}, []), claim)
    assert r.verdict != "CORRECT"


@pytest.mark.parametrize("expr", ["arccot(x) - atan(1/x)", "pi/2 - atan(x) - atan(1/x)"])
def test_an_identity_is_not_refuted_by_a_rounding_residue(expr):
    """A residue of 2e-31 was a counterexample; only an exact check makes one."""
    assert _run(_ir("evaluate", {"expr": expr}, XP), "0", kind="expression").verdict != "INCORRECT"


@pytest.mark.parametrize("latex", [r"\text{arccot}(-1)", r"\textrm{arccot}(-1)", r"\mathrm{acot}(-1)"])
def test_latex_spellings_of_arccot(latex):
    assert _run(_ir("evaluate", {"expr": latex}, []), "3*pi/4").verdict == "CORRECT"


@pytest.mark.parametrize("latex", [r"\text{oo} + 1", r"\mathrm{dist} + 1"])
def test_a_latex_name_the_namespace_gives_to_a_function_or_constant_is_no_symbol(latex):
    """latex2sympy makes a symbol "oo" or "dist" of these; they passed as declared because the name
    is in the namespace, though not as a symbol (\\text{arccot}(-1) was the symbol arccot times -1)."""
    from mathverify.normalize.parse import parse_expr_str
    with pytest.raises(ParseError, match="undeclared symbol"):
        parse_expr_str(latex, dict(_SAFE_NAMES))


def test_a_false_closed_inequality_step_is_refuted():
    r = _run(_ir("evaluate", {"expr": "sin(pi/6)"}, []), "1/2", [("compute", "sin(pi/6) < 0"),
                                                                ("compute", "sin(pi/6) = 1/2")])
    assert r.verdict == "INCORRECT" and _steps(r)[0] == "refuted"


# --- SymPy's value of a closed integral is confirmed by numbers ----------------------------------

def test_sympys_wrong_integral_certifies_nothing():
    """SymPy integrates |cos x| over [-1, 1] to 0; the value is 2 sin 1."""
    ir = _ir("evaluate", {"expr": "Integral(Abs(cos(x)), (x, -1, 1))"})
    assert _run(ir, "0").verdict != "CORRECT"
    r = _run(ir, "2*sin(1)", [("compute", "Integral(Abs(cos(x)), (x, -1, 1)) = 0")])
    assert _steps(r) != ["verified"]
    r = _run(ir, "2*sin(1)", [("eq", "Integral(Abs(cos(x)), (x, -1, 1)) = 2*sin(1)")])
    assert _steps(r) != ["refuted"]


@pytest.mark.parametrize("expr,claim", [("Sum(cos(pi*k)/k**2, (k, 1, oo))", "-pi**2/12"),
                                        ("Sum(sin(pi*k)/k**2, (k, 1, oo))", "0"),
                                        ("Sum(cos(pi*k)/k, (k, 1, oo))", "-log(2)")])
def test_an_oscillating_series_over_an_integer_index_is_closed(expr, claim):
    """An assumption-free index left these unclosed, and the numeric fallback (Euler-Maclaurin) is
    wrong for oscillating terms: the right answers were INCORRECT."""
    assert _run(_ir("evaluate", {"expr": expr}, KP), claim).verdict == "CORRECT"


def test_a_series_sympy_cannot_close_is_not_refuted_by_its_numeric_fallback():
    """Σ sin(πk/2)/k = π/4 (Leibniz); SymPy's numeric evaluation of the unevaluated sum gives -2."""
    ir = _ir("evaluate", {"expr": "1"}, KP)
    r = _run(ir, "1", [("eq", "Sum(sin(pi*k/2)/k, (k, 1, oo)) = pi/4")])
    assert r.verdict != "INCORRECT" and _steps(r) != ["refuted"]
    assert _run(_ir("evaluate", {"expr": "Sum(sin(pi*k/2)/k, (k, 1, oo))"}, KP), "pi/4").verdict != "INCORRECT"


def test_a_closed_claim_about_a_limit_is_not_decided_from_the_right():
    """Outside a compute claim SymPy reads Limit from the right: |x|/x -> 1 would be verified."""
    r = _run(_ir("evaluate", {"expr": "x"}, XR, ["x > 0"]), "1", [("eq", "Limit(Abs(x)/x, x, 0) = 1")])
    assert _steps(r) != ["verified"]


def test_a_wrong_integral_step_stays_refuted_where_sympys_closed_form_is_wrong():
    """The integrator's converged value (2 sin 1, not SymPy's 0) refutes "= 0"."""
    ir = _ir("evaluate", {"expr": "x"}, XR, ["x = 1"])
    for kind in ("eq", "compute"):
        r = _run(ir, "1", [(kind, "Integral(Abs(cos(x)), (x, -1, 1)) = 0"), ("eq", "x = 1")])
        assert r.verdict == "INCORRECT" and _steps(r)[0] == "refuted"


def test_a_true_integral_step_is_not_refuted_by_sympys_wrong_value():
    """simplify(a - b) evaluates the integral: SymPy's ∫_0^{2π} |sin 2x| dx is 2, the value is 4, so
    the exact comparison refuted the true step unless numbers confirm SymPy's value first."""
    ir = _ir("evaluate", {"expr": "x"}, XR, ["x = 1"])
    r = _run(ir, "1", [("eq", "Integral(Abs(sin(2*x)), (x, 0, 2*pi)) = 4"), ("eq", "x = 1")])
    assert _steps(r)[0] != "refuted" and r.verdict != "INCORRECT"
    # and the false step that agrees with SymPy's value is refuted, not verified (simplify gives 0)
    r = _run(ir, "1", [("eq", "Integral(Abs(sin(2*x)), (x, 0, 2*pi)) = 2"), ("eq", "x = 1")])
    assert _steps(r)[0] == "refuted" and r.verdict == "INCORRECT"


def test_a_true_series_step_is_not_refuted_by_euler_maclaurin():
    """SymPy's numeric value of Σ cos(πk/4)/k² is 0.565345; the sum is 11π²/192 = 0.565446."""
    r = _run(_ir("evaluate", {"expr": "1"}, KP), "1", [("eq", "Sum(cos(pi*k/4)/k**2, (k, 1, oo)) = 11*pi**2/192")])
    assert r.verdict != "INCORRECT" and _steps(r) != ["refuted"]


_X = sp.Symbol("x", real=True)


@pytest.mark.parametrize("form", [sp.Integral(sp.Abs(sp.cos(_X)), (_X, -1, 1)), sp.Limit(_X * sp.sin(sp.pi / _X), _X, sp.oo)])
def test_no_number_is_read_off_an_unconfirmed_form(form):
    from mathverify.equiv.numeric import to_mp
    with pytest.raises(ValueError):
        to_mp(form, 30)


def test_a_closed_latex_relation_stays_a_relation():
    """Converting acot inside it re-evaluated it: the false step became False and was skipped."""
    rel = parse_relation(r"\cot^{-1}(-1) = -\frac{\pi}{4}", dict(_SAFE_NAMES))
    assert isinstance(rel, sp.Eq)


def test_a_definite_integral_task_integrates_over_the_interval():
    ir = _ir("definite_integral", {"integrand": "Abs(x)", "var": "x", "a": "-1", "b": "1"}, XP)
    assert _run(ir, "0").verdict == "INCORRECT"
    assert _run(ir, "1").verdict == "CORRECT"


@pytest.mark.parametrize("vars_", [KP, [{"name": "k", "domain": "integer"}]])
def test_a_sum_with_an_undefined_term_is_undefined(vars_):
    """k/k read as 1: Σ_{k=-1}^{1} k/k = 3 was certified."""
    assert _run(_ir("evaluate", {"expr": "Sum(k/k, (k, -1, 1))"}, vars_), "3").verdict == "UNKNOWN"


# --- limits, points of derivatives, series and products (the unevaluated-forms lens) -------------

@pytest.mark.parametrize("expr,claim", [("Limit(Abs(x)/x, x, 0)", "1"), ("limit(1/x, x, 0)", "oo")])
def test_a_limit_without_a_direction_is_two_sided(expr, claim):
    """SymPy reads Limit(e, x, a) from the right; the compute steps already read it two-sided (E6)."""
    assert _run(_ir("evaluate", {"expr": expr}), claim).verdict != "CORRECT"


def test_a_derivative_at_a_corner_has_no_value():
    """diff(Abs(x), x) is sign(x), and sign(0) = 0 certified "d|x|/dx at 0 is 0"."""
    assert _run(_ir("evaluate", {"expr": "at(diff(Abs(x), x), x, 0)"}), "0").verdict != "CORRECT"
    r = _run(_ir("evaluate", {"expr": "2 + 2"}), "4", [("eq", "at(diff(Abs(x), x), x, 0) = 0")])
    assert _steps(r) != ["verified"]


def test_a_closed_limit_is_decided_two_sided_with_numbers():
    assert _run(_ir("evaluate", {"expr": "Limit(sin(x)/x, x, 0)"}), "1").verdict == "CORRECT"
    assert _run(_ir("evaluate", {"expr": "Limit(sin(x)/x, x, 0)"}), "2").verdict == "INCORRECT"


def test_sympys_wrong_sequence_limit_certifies_nothing():
    """With n an integer SymPy says lim n·sin(π/n) = 0; it is π."""
    ir = _ir("evaluate", {"expr": "Limit(n*sin(pi/n), n, oo)"}, NN)
    assert _run(ir, "0").verdict != "CORRECT"
    assert _run(ir, "pi").verdict != "INCORRECT"


def test_an_oscillating_factor_on_a_diverging_quantity_is_no_dne():
    """x(2 + sin x) >= x tends to oo; the spread of its values was read as oscillation (DNE)."""
    ir = _ir("limit", {"expr": "x*(2 + sin(x))", "var": "x", "to": "oo"})
    assert _run(ir, "", kind="dne").verdict != "CORRECT"
    assert _run(ir, "oo").verdict != "INCORRECT"


def test_one_nsum_value_does_not_refute_a_series():
    """nsum gives 263/315 for Σ sin(πk/2)/k at every precision (the zero terms stop it); it is π/4."""
    ir = _ir("series_sum", {"term": "sin(pi*k/2)/k", "var": "k", "lo": "1", "hi": "oo"}, KP)
    assert _run(ir, "pi/4").verdict != "INCORRECT"


@pytest.mark.parametrize("expr,claim", [("Sum(sin(k)/k, (k, 1, oo))", "(pi - 1)/2"),
                                        ("Product(1 - 1/k**2, (k, 2, oo))", "1/2")])
def test_a_true_value_is_not_refuted_through_sympys_numeric_evaluation_of_a_form(expr, claim):
    """sp.N of an unevaluated oscillating sum or of a product is wrong: the right answers were INCORRECT."""
    assert _run(_ir("evaluate", {"expr": expr}, KP), claim).verdict != "INCORRECT"


def test_a_closed_integral_inside_a_larger_expression_is_confirmed_too():
    ir = _ir("evaluate", {"expr": "x*Integral(Abs(cos(t)), (t, -pi, pi))"},
             [{"name": "x", "domain": "real"}, {"name": "t", "domain": "real"}], shape="expression")
    assert _run(ir, "2*x", kind="expression").verdict != "CORRECT"      # SymPy's 2; the integral is 4


# --- second recheck: computing notation and the problem's functions --------------------------------

@pytest.mark.parametrize("expr,vars_,wrong,right", [
    ("integrate(Abs(cos(x)), (x, -1, 1))", XR, "0", "2*sin(1)"),
    ("limit(n*tan(pi/n), n, oo)", NN, "0", "pi"),
])
def test_a_closed_integrate_or_limit_is_a_form_not_sympys_value(expr, vars_, wrong, right):
    """`integrate` and `limit` computed while parsing, so SymPy's wrong value was the task's value:
    0 was certified for both (the values are 2 sin 1 and pi) and the right answers refuted."""
    assert _run(_ir("evaluate", {"expr": expr}, vars_), wrong).verdict != "CORRECT"
    assert _run(_ir("evaluate", {"expr": expr}, vars_), right).verdict != "INCORRECT"
    from mathverify.normalize.parse import build_namespace, parse_expr_str
    from mathverify.intake.structured import load_problem_ir
    parsed = parse_expr_str(expr, build_namespace(load_problem_ir(_ir("evaluate", {"expr": expr}, vars_))))
    assert isinstance(parsed, (sp.Integral, sp.Limit))


def test_an_antiderivative_and_a_limit_with_a_parameter_are_still_computed():
    from mathverify.normalize.parse import build_namespace, parse_expr_str
    a, x, n = sp.Symbol("a"), sp.Symbol("x"), sp.Symbol("n", positive=True, integer=True)
    ns = build_namespace(None, {"a": a, "x": x, "n": n})
    assert sp.simplify(parse_expr_str("integrate(2*x, x)", ns) - x**2) == 0
    assert parse_expr_str("limit((1 + a/n)**n, n, oo)", ns) == sp.exp(a)


FP = {"vars": [{"name": "x", "domain": "positive_real"}, {"name": "k", "domain": "positive_integer"}],
      "functions": [{"name": "f", "expr": "sqrt(x**2) + x", "args": ["x"], "params": []}]}


@pytest.mark.parametrize("expr,wrong,right", [("Sum(f(k), (k, -2, 2))", "0", "6"),
                                              ("Integral(f(x), (x, -1, 1))", "0", "1"),
                                              ("f(-1)", "-2", "0")])
def test_a_functions_argument_is_not_the_problem_variable_of_that_name(expr, wrong, right):
    """With x declared positive, f(x) = sqrt(x**2) + x was parsed as 2x: f(-1) was -2 and the sum of
    f(k) over -2..2 was 0 (it is 6). The formal argument is the function's own real variable."""
    ir = dict(_ir("evaluate", {"expr": expr}), **FP)
    assert _run(ir, wrong).verdict == "INCORRECT"
    assert _run(ir, right).verdict == "CORRECT"


def test_a_call_at_the_problem_variable_still_uses_its_domain():
    ir = dict(_ir("simplify_expression", {"expr": "f(x)"}, shape="expression"), **FP)
    assert _run(ir, "2*x").verdict == "CORRECT"


def test_a_form_inside_an_integrand_gives_no_numeric_value():
    """The inner ∫|cos t| over [-pi, pi] was computed by its own quadrature at every point:
    3.99999920... at 30 and at 50 digits, "converged", so the true value 4 was refuted."""
    ir = _ir("definite_integral", {"integrand": "integrate(Abs(cos(t)), (t, -pi, pi))", "var": "x",
                                   "a": "0", "b": "1"}, XR + [{"name": "t", "domain": "real"}])
    assert _run(ir, "4").verdict != "INCORRECT"
    assert _run(ir, "2").verdict != "CORRECT"


# --- the critic's angle: the as-written reading of computing notation --------------------------------

F3 = [{"name": "f", "args": ["x"], "expr": "x**3 - 3*x"}]


@pytest.mark.parametrize("kind,params,shape,wrong,right,functions", [
    ("solve_equation", {"equation": "diff(f(x), x) = 0", "var": "x"}, "set", "{1}", "{-1, 1}", F3),
    ("solve_inequality", {"inequality": "diff(f(x), x) < 0", "var": "x"}, "interval", "(0, 1)", "(-1, 1)", F3),
    ("solve_equation", {"equation": "diff(x**2, x) = 0", "var": "x"}, "set", "EmptySet", "{0}", None),
])
def test_a_derivative_read_as_written_adds_no_condition_of_the_raw_power_rule(kind, params, shape, wrong,
                                                                            right, functions):
    """With evaluation off SymPy differentiated x**3 into x**3*(0*log(x) + 3/x): the conditions
    x > 0 and x != 0 were the problem's, so the half-line answers were certified."""
    ir = _ir(kind, params, shape=shape)
    if functions:
        ir["functions"] = functions
    assert _run(ir, wrong, kind=shape).verdict == "INCORRECT"
    assert _run(ir, right, kind=shape).verdict == "CORRECT"


def test_a_derivative_read_as_written_keeps_its_operands_conditions():
    from mathverify.normalize.parse import build_namespace, parse_as_written
    x = sp.Symbol("x", real=True)
    ns = build_namespace(None, {"x": x})
    from mathverify.certify.domain import definedness_conditions
    conds = definedness_conditions(parse_as_written("diff(x**2/x, x)", ns), None)
    assert sp.Ne(x, 0) in conds
    assert not any(c.has(sp.log) for c in conds)


@pytest.mark.parametrize("p,c,right,wrong", [(-1, -3, "35", "-35"), (-2, 0, "16", "15")])
def test_a_critical_point_at_a_negative_abscissa(p, c, right, wrong):
    """ayt-tur-007 at p < 0: the raw derivative's log(x) made x = p undefined, so the right a*b was
    UNKNOWN."""
    ir = {"task": {"kind": "evaluate", "params": {"expr": "a*b"}}, "vars": [{"name": "a"}, {"name": "b"}],
          "functions": [{"name": "f", "expr": "x**3 + a*x**2 + b*x", "args": ["x"], "params": ["a", "b"]}],
          "givens": [f"at(diff(f(x), x), x, {p}) = 0", f"f({p}) = {c}"], "answer_shape": "scalar"}
    assert _run(ir, right).verdict == "CORRECT"
    assert _run(ir, wrong).verdict == "INCORRECT"


def test_an_integral_with_a_parameter_bound_keeps_the_texts_conditions():
    """Read as written, integrate(x, (x, 0, y)) raised and every condition of the text was lost:
    the domain of integrate(x, (x, 0, y)) + y/y was certified to be R."""
    ir = _ir("domain_of", {"expr": "integrate(x, (x, 0, y)) + y/y", "var": "y"},
             XR + [{"name": "y", "domain": "real"}], shape="interval")
    assert _run(ir, "(-oo, oo)", kind="interval").verdict != "CORRECT"


@pytest.mark.parametrize("body,expr,claim,at2", [("x/x", "f(0)", "1", "1"), ("sqrt(x)**2", "f(-1)", "-1", "2"),
                                                 ("x**2/x", "f(0) + 1", "1", "2")])
def test_a_call_outside_the_declared_domain_keeps_the_bodys_written_conditions(body, expr, claim, at2):
    """x declared positive: the body's written conditions (x != 0, x >= 0) were read on the declared
    symbol, where SymPy folds them to True, so f(0) = 1 for f(x) = x/x was certified (on 35af293 too)."""
    ir = dict(_ir("evaluate", {"expr": expr}), vars=XP, functions=[{"name": "f", "expr": body, "args": ["x"]}])
    assert _run(ir, claim).verdict != "CORRECT"
    ok = dict(_ir("evaluate", {"expr": "f(2)"}), vars=XP, functions=[{"name": "f", "expr": body, "args": ["x"]}])
    assert _run(ok, at2).verdict == "CORRECT"


def test_the_lean_function_gate_reads_the_body_with_the_functions_own_argument():
    """The gate compares the body as written with the body as parsed; both are read with the formal
    argument. Read with the declared positive integer k, 1/k**2 was refused and k/k (whose parse lost
    k != 0) passed."""
    from mathverify.formal.statement import build_statement

    def st(body):
        ir = {"task": {"kind": "series_sum", "params": {"term": "f(k)", "var": "k", "lo": "1", "hi": "10"}},
              "vars": KP, "givens": [], "answer_shape": "scalar", "functions": [{"name": "f", "expr": body, "args": ["k"]}]}
        return build_statement(ir, {"kind": "value", "payload": "55"})
    assert st("1/k**2") is not None
    assert st("k/k") is None


def test_an_excluded_point_whose_realness_sympy_cannot_decide_is_still_checked():
    """arccot(2) + arccot(3) = pi/4, so 1/sin(arccot(x) + arccot(2) + arccot(3)) is undefined only at
    x = -1. solveset excludes -tan(atan(2) + atan(3)) = 1 instead; is_real is None there, the guard
    skipped the point, and the true domain was refuted."""
    ir = _ir("domain_of", {"expr": "1/sin(arccot(x) + arccot(2) + arccot(3))", "var": "x"}, shape="interval")
    assert _run(ir, "(-oo, -1) U (-1, oo)", kind="interval").verdict != "INCORRECT"
    assert _run(ir, "(-oo, 1) U (1, oo)", kind="interval").verdict != "CORRECT"


@pytest.mark.parametrize("kind,params,givens,shape,claim", [
    ("extremum", {"f": "x + 0*tan(arccot(2) + arccot(1/2))", "var": "x", "interval": "[0, 1]", "which": "max"},
     [], "scalar", "1"),
    ("solve_equation", {"var": "x"}, ["x + tan(arccot(2) + arccot(1/2)) - tan(arccot(2) + arccot(1/2)) = 1"],
     "set", "{1}"),
])
def test_a_closed_condition_no_check_proves_is_not_dropped_beside_a_variable(kind, params, givens, shape, claim):
    """arccot(2) + arccot(1/2) = pi/2: tan of it is undefined, but its condition cos(...) != 0 stayed
    symbolic, had no free symbol, and was dropped; both problems were certified (on 35af293 too)."""
    ir = _ir(kind, params, givens=givens, shape=shape)
    assert _run(ir, claim, kind="set" if shape == "set" else "value").verdict != "CORRECT"


# --- the second audit: a problem function read as written ---------------------------------------------

FR = [{"name": "f", "expr": "(x - 1)**2/(x - 1)", "args": ["x"]}]


@pytest.mark.parametrize("kind,params,shape,claim,ok_params,ok_claim", [
    ("derivative", {"f": "f(x)", "var": "x", "at": "1"}, "value", "1", {"f": "f(x)", "var": "x", "at": "2"}, "1"),
    ("extremum", {"f": "f(x)", "var": "x", "interval": "[1, 3]", "which": "min"}, "value", "0",
     {"f": "f(x)", "var": "x", "interval": "[2, 3]", "which": "min"}, "1"),
    ("tangent_line", {"f": "f(x)", "var": "x", "at": "1", "dep": "y"}, "equation", "y = x - 1", None, None),
])
def test_a_functions_written_conditions_reach_the_calculus_tasks(kind, params, shape, claim, ok_params, ok_claim):
    """f(x) = (x - 1)**2/(x - 1) is undefined at 1; called through f, its derivative there, its minimum
    on [1, 3] and its tangent at 1 were certified (the same text without f was UNKNOWN)."""
    ir = dict(_ir(kind, params, shape="scalar" if shape == "value" else shape), functions=FR)
    assert _run(ir, claim, kind=shape).verdict != "CORRECT"
    if ok_params:
        assert _run(dict(_ir(kind, ok_params), functions=FR), ok_claim).verdict == "CORRECT"


@pytest.mark.parametrize("expr,body,claim", [("Sum(f(k), (k, -1, 1))", "x/x", "3"),
                                             ("Sum(f(k), (k, -2, 1))", "log(x + 1) - log(x + 1)", "0")])
def test_a_sum_over_a_functions_undefined_terms_is_undefined(expr, body, claim):
    ir = dict(_ir("evaluate", {"expr": expr}, [{"name": "k", "domain": "integer"}]),
              functions=[{"name": "f", "expr": body, "args": ["x"]}])
    assert _run(ir, claim).verdict != "CORRECT"


def test_a_series_term_through_a_function_keeps_its_conditions():
    fn = [{"name": "a", "expr": "(n - 2)**2/(n - 2)", "args": ["n"]}]
    V = KP + [{"name": "n", "domain": "positive_integer"}]
    ir = dict(_ir("series_sum", {"term": "a(k)", "var": "k", "lo": "1", "hi": "4"}, V), functions=fn)
    assert _run(ir, "2").verdict != "CORRECT"
    ok = dict(_ir("series_sum", {"term": "a(k)", "var": "k", "lo": "3", "hi": "4"}, V), functions=fn)
    assert _run(ok, "3").verdict == "CORRECT"


G2 = FR + [{"name": "g", "expr": "f(x) + 3", "args": ["x"]}]


@pytest.mark.parametrize("kind,params,shape,wrong,right", [
    ("solve_equation", {"equation": "g(x) = 3", "var": "x"}, "set", "{1}", "{}"),
    ("domain_of", {"expr": "g(x)", "var": "x"}, "interval", "Reals", "(-oo, 1) U (1, oo)"),
])
def test_a_function_calling_a_function_keeps_the_inner_conditions(kind, params, shape, wrong, right):
    """g(x) = f(x) + 3 lost f's condition x != 1: {1} and the domain R were certified, {} refuted."""
    ir = dict(_ir(kind, params, shape=shape), functions=G2)
    assert _run(ir, wrong, kind=shape).verdict == "INCORRECT"
    assert _run(ir, right, kind=shape).verdict == "CORRECT"
    assert _run(dict(_ir("evaluate", {"expr": "g(1)"}), functions=G2), "3").verdict != "CORRECT"


FDOM = [{"name": "f", "expr": "x**2 + 1", "args": ["x"], "domain": "x > 0"}]


@pytest.mark.parametrize("kind,params,shape,wrong,right", [
    ("solve_equation", {"equation": "f(x) = 5", "var": "x"}, "set", "{-2, 2}", "{2}"),
    ("solve_inequality", {"inequality": "f(x) < 5", "var": "x"}, "interval", "(-2, 2)", "(0, 2)"),
])
def test_a_functions_declared_domain_is_applied(kind, params, shape, wrong, right):
    """FunctionDef.domain was ignored: f(x) = x**2 + 1 on x > 0 gave {-2, 2} and f(-2) = 5; Lean
    proved f(-2) = 5."""
    ir = dict(_ir(kind, params, shape=shape), functions=FDOM)
    assert _run(ir, wrong, kind=shape).verdict == "INCORRECT"
    assert _run(ir, right, kind=shape).verdict == "CORRECT"
    ev = dict(_ir("evaluate", {"expr": "f(-2)"}), functions=FDOM)
    assert _run(ev, "5").verdict != "CORRECT"
    from mathverify.formal.statement import build_statement
    assert build_statement(ev, {"kind": "value", "payload": "5"}) is None


@pytest.mark.parametrize("body,wrong,right", [("Sum(cos(pi*k), (k, 1, 2*n))", "1", "0"),
                                             ("Sum(sqrt(k**2), (k, 1, n))", "n**2", "n*(n + 1)/2")])
def test_a_sum_in_a_function_body_gets_an_integer_index_at_the_call(body, wrong, right):
    """The formal n is real, so the body's index stayed plain and the wrong n**2 was UNKNOWN."""
    ir = dict(_ir("simplify_expression", {"expr": "S(n)"}, KP + [{"name": "n", "domain": "positive_integer"}],
                  shape="expression"),
              functions=[{"name": "S", "expr": body, "args": ["n"]}])
    assert _run(ir, wrong, kind="expression").verdict == "INCORRECT"
    assert _run(ir, right, kind="expression").verdict == "CORRECT"


def test_a_finite_sum_at_a_sample_point_is_written_out_not_strictly_evaluated():
    """Σ_{k=1}^{2n} sin²(πk/2) = n took 180-330 s: each exact check of a sample point ran strict evalf
    on the unevaluated sum in the verifier's own process."""
    import time
    from mathverify.equiv.random_point import _written_out
    k = sp.Symbol("k", integer=True)
    assert _written_out(sp.Sum(sp.sin(sp.pi * k / 2) ** 2, (k, 1, 6))) == 3
    assert _written_out(sp.Sum(1 / k ** 2, (k, 1, sp.oo))) is None
    ir = _ir("simplify_expression", {"expr": "Sum(sin(pi*k/2)**2, (k, 1, 2*n))"},
             NN + KP, shape="expression")
    t = time.time()
    assert _run(ir, "n", kind="expression").verdict == "CORRECT"
    assert time.time() - t < 120
    assert _run(ir, "2*n", kind="expression").verdict == "INCORRECT"


@pytest.mark.parametrize("kind,params,claim", [
    ("extremum", {"f": "Abs(x) - x**2", "var": "x", "interval": "[-1, 1]", "which": "min"}, "-2"),
    ("derivative", {"f": "x*Abs(x)", "var": "x", "at": "-1"}, "-2"),
])
def test_an_interval_or_point_outside_the_declared_domain_is_not_certified(kind, params, claim):
    """x declared positive folds |x| to x; on [-1, 1] the minimum -2 and at -1 the derivative -2
    were certified, values no reading of the problem gives."""
    assert _run(_ir(kind, params, XP), claim).verdict != "CORRECT"
    ok = dict(params, interval="[0, 2]") if kind == "extremum" else dict(params, at="1")
    assert _run(_ir(kind, ok, XP), "-2" if kind == "extremum" else "2").verdict == "CORRECT"
