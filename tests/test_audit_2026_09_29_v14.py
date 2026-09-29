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


@pytest.mark.parametrize("expr,to,claim", [("gcd(x, 4)", "0", "4"), ("gcd(x, 6)/x", "2", "1"), ("lcm(x, 2)", "1", "2")])
def test_a_limit_nothing_numeric_corroborates_is_not_certified(expr, to, claim):
    """SymPy substitutes into a function it does not know; lim_{x->0} gcd(x, 4) = 4 was CORRECT."""
    r = _run(_ir("limit", {"expr": expr, "var": "x", "to": to}), claim)
    assert r.verdict == "UNKNOWN"


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


def test_a_definite_integral_task_integrates_over_the_interval():
    ir = _ir("definite_integral", {"integrand": "Abs(x)", "var": "x", "a": "-1", "b": "1"}, XP)
    assert _run(ir, "0").verdict == "INCORRECT"
    assert _run(ir, "1").verdict == "CORRECT"


@pytest.mark.parametrize("vars_", [KP, [{"name": "k", "domain": "integer"}]])
def test_a_sum_with_an_undefined_term_is_undefined(vars_):
    """k/k read as 1: Σ_{k=-1}^{1} k/k = 3 was certified."""
    assert _run(_ir("evaluate", {"expr": "Sum(k/k, (k, -1, 1))"}, vars_), "3").verdict == "UNKNOWN"
