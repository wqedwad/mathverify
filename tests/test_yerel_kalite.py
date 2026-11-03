"""Local quality after the fourth audit (16 Oct 2026; DECISIONS §91).

* A Sum/Product index is an integer of its range. The term a**k read on a real index asked a > 0, a
  condition on the problem's symbol that no index needs: the root -1/2 of Σ_{n>=0} x**n = 2/3 was dropped
  and {-1/2} refuted, x + x**2 + x**3 = -1 written as a Sum refuted {-1}, and with a**2 = 1/4 only a = 1/2
  was left, so Σ a**k = 2 was certified (preexisting, found while closing V16).
* 0**0 inside a range stays a convention (part d4a): read on an integer index the term a**k has no
  condition left, so the base of a power whose exponent vanishes at an index of the range is a
  zero_power point.
* V16 (DECISIONS §79): a compute step SymPy cannot close while a symbol is free is re-checked where the
  premises pin it: with a = 1/2 given, "Sum(a**k, (k, 0, oo)) = 3" stayed unknown.
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.certify.domain import ZERO_POWER_BASE, definedness_conditions
from mathverify.verifier import verify

a = sp.Symbol("a", real=True)
x = sp.Symbol("x", real=True)
k = sp.Symbol("k", integer=True, nonnegative=True)


def _run(ir, payload, kind="value", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": kk, "claim": c, "from": [], "text": ""}
                     for i, (kk, c) in enumerate(steps)]}
    return verify(ir, sol)


def _steps(r):
    return [s["status"] for layer in r.layers if layer.layer == "steps.refute"
            for s in layer.evidence.get("steps", [])]


# --- the index of a range is an integer --------------------------------------------------------

@pytest.mark.parametrize("expr", [sp.Sum(a ** k, (k, 0, 5)), sp.Sum(a ** k, (k, 0, sp.oo)),
                                  sp.Sum(a ** k, (k, 1, sp.oo)), sp.Product(a ** k, (k, 1, 3))])
def test_an_integer_index_asks_no_positive_base(expr):
    conds = definedness_conditions(expr, None)
    assert (a > 0) not in conds and sp.Ne(a, 0) not in conds, conds


def test_a_power_that_vanishes_at_an_index_of_the_range_is_a_zero_power_point():
    # k = 0 is in [0, 5] and in [0, oo): 0**0 there; from k = 1 the exponent never vanishes
    assert sp.Contains(a, ZERO_POWER_BASE) in definedness_conditions(sp.Sum(a ** k, (k, 0, 5)), None)
    assert sp.Contains(a, ZERO_POWER_BASE) in definedness_conditions(sp.Sum(a ** k, (k, 0, sp.oo)), None)
    assert sp.Contains(a - 1, ZERO_POWER_BASE) in definedness_conditions(
        sp.Sum((a - 1) ** k, (k, 0, sp.oo)), None)
    assert sp.Contains(a, ZERO_POWER_BASE) not in definedness_conditions(sp.Sum(a ** k, (k, 1, sp.oo)), None)
    # k - 1 vanishes at k = 1, below the range [3, oo)
    assert sp.Contains(a, ZERO_POWER_BASE) not in definedness_conditions(sp.Sum(a ** (k - 1), (k, 3, sp.oo)), None)
    # the exponent k - 3 vanishes at k = 3, outside [0, 2]; at k = 0 it is negative: a != 0
    conds = definedness_conditions(sp.Sum(a ** (k - 3), (k, 0, 2)), None)
    assert sp.Ne(a, 0) in conds and sp.Contains(a, ZERO_POWER_BASE) not in conds, conds


def test_a_negative_exponent_in_the_range_still_asks_a_nonzero_base():
    assert sp.Ne(a, 0) in definedness_conditions(sp.Sum(a ** (k - 1), (k, 0, sp.oo)), None)


def test_an_index_below_zero_is_negative():
    j = sp.Symbol("j", integer=True)
    # j <= -1: a**(-j) has a positive exponent (no condition), a**j a negative one (a != 0)
    assert definedness_conditions(sp.Sum(a ** (-j), (j, -sp.oo, -1)), None) == []
    assert sp.Ne(a, 0) in definedness_conditions(sp.Sum(a ** j, (j, -sp.oo, -1)), None)


def test_an_integral_variable_is_still_a_real_number():
    t = sp.Symbol("t", real=True)
    assert (a > 0) in definedness_conditions(sp.Integral(a ** t, (t, 0, 1)), None)


X = [{"name": "x"}, {"name": "n", "domain": "nonneg_integer"}]
A = [{"name": "a"}, {"name": "k", "domain": "nonneg_integer"}]


def _solve(eq):
    return {"task": {"kind": "solve_equation", "params": {"equation": eq, "var": "x"}}, "vars": X,
            "answer_shape": "set"}


def _ev(expr, givens):
    return {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": A, "givens": givens,
            "answer_shape": "scalar"}


@pytest.mark.parametrize("ir,claim", [
    (_solve("Sum(x**n, (n, 0, oo)) = 2/3"), "{-1/2}"),          # 1/(1 - x) = 2/3
    (_solve("Sum(x**n, (n, 1, 3)) = -1"), "{-1}"),              # (x + 1)(x**2 + 1) = 0
    (_solve("Sum(n*x**(n - 1), (n, 1, oo)) = 4/9"), "{-1/2}"),   # 1/(1 - x)**2 = 4/9, |x| < 1
    (_solve("Sum(x**(2*n), (n, 0, oo)) = 4/3"), "{-1/2, 1/2}"),  # 1/(1 - x**2) = 4/3
])
def test_a_negative_root_of_a_series_equation_is_not_refuted(ir, claim):
    assert _run(ir, claim, "set").verdict != "INCORRECT"


def test_two_instances_of_the_parameter_give_no_certificate():
    # a = 1/2: 2; a = -1/2: 2/3
    assert _run(_ev("Sum(a**k, (k, 0, oo))", ["a**2 = 1/4"]), "2").verdict != "CORRECT"


@pytest.mark.parametrize("givens,claim,verdict", [
    (["a = -1/2"], "2/3", "CORRECT"), (["a = -1/2"], "2", "INCORRECT"),
])
def test_a_negative_ratio_is_read(givens, claim, verdict):
    assert _run(_ev("Sum(a**k, (k, 0, oo))", givens), claim).verdict == verdict


@pytest.mark.parametrize("expr,claim", [("Sum(a**k, (k, 0, oo))", "1"), ("Sum(a**k, (k, 0, 3))", "1")])
def test_zero_to_the_zero_in_a_range_is_not_certified(expr, claim):
    assert _run(_ev(expr, ["a = 0"]), claim).verdict != "CORRECT"


# --- V16: an undecided identity check is re-checked where the premises pin the symbols -------------

G = _ev("Sum(a**k, (k, 0, oo))", ["a = 1/2"])


@pytest.mark.parametrize("step,status,verdict", [
    ("Sum(a**k, (k, 0, oo)) = 3", "refuted", "INCORRECT"),
    ("Sum(a**k, (k, 0, oo)) = 2", "verified", "CORRECT"),
    ("Sum(a**k, (k, 0, oo)) = 1/(1 - a)", "verified", "CORRECT"),
    ("Sum(a**k, (k, 0, oo)) = 1/(1 + a)", "refuted", "INCORRECT"),
])
def test_a_series_step_is_checked_at_the_given_value(step, status, verdict):
    r = _run(G, "2", steps=[("compute", step)])
    assert _steps(r) == [status] and r.verdict == verdict


def test_a_series_step_in_a_free_parameter_stays_undecided():
    r = _run(_ev("Sum(a**k, (k, 0, oo))", []), "1/(1 - a)", "expression",
             steps=[("compute", "Sum(a**k, (k, 0, oo)) = 1/(1 + a)")])
    assert _steps(r) == ["unknown"]


# --- the attack on these changes (16 Oct 2026): Y1, Y2, Y3 ------------------------------------------

V = [{"name": "a"}, {"name": "x"}, {"name": "k", "domain": "nonneg_integer"}]


def _expr(expr, claim, task="evaluate"):
    ir = {"task": {"kind": task, "params": {"expr": expr}}, "vars": V, "answer_shape": "expression"}
    return _run(ir, claim, "expression")


@pytest.mark.parametrize("expr,claim", [
    ("Sum(x**k/factorial(k), (k, 0, oo))", "exp(x)"),
    ("Sum(binomial(3, k)*a**k, (k, 0, 3))", "(1 + a)**3"),
    ("Sum(a**k, (k, 0, 3))", "1 + a + a**2 + a**3"),
    ("Sum(k*a**(k - 1), (k, 1, 3))", "1 + 2*a + 3*a**2"),
    ("Sum(a**(k - 1), (k, 1, 4))", "1 + a + a**2 + a**3"),
    ("x**0 + x", "1 + x"),
])
def test_a_claim_right_under_both_readings_of_zero_to_the_zero_is_certified(expr, claim):
    """Y1: at a 0**0 point the claim, defined there, has the value 0**0 = 1 gives; under the other reading it
    extends the expression where it has no value, as x/x + x -> 1 + x."""
    assert _expr(expr, claim).verdict == "CORRECT"


@pytest.mark.parametrize("expr,claim,verdict", [
    ("x**0 + x", "x/x + x", "UNKNOWN"),                          # undefined where 0**0 = 1 gives a value
    ("Sum(a**k, (k, 0, 3))", "a + a**2 + a**3", "INCORRECT"),
    ("Sum(a**k, (k, 0, 3))", "a + a**2 + a**3 + 1 + 0**a", "INCORRECT"),  # undefined for a < 0
    ("Sum(x**k/factorial(k), (k, 0, oo))", "exp(x) - 1", "INCORRECT"),
])
def test_a_claim_that_differs_at_the_zero_to_the_zero_point_is_not_certified(expr, claim, verdict):
    assert _expr(expr, claim).verdict == verdict


@pytest.mark.parametrize("expr,claim,task", [
    ("Sum(x**k, (k, 0, oo))", "1/(1 - x)", "evaluate"),
    ("Sum(x**k, (k, 0, oo))", "1/(1 - x)", "simplify_expression"),
    ("Sum(a**k, (k, 1, oo))", "a/(1 - a)", "evaluate"),
    ("Sum(a**k/k, (k, 1, oo))", "-log(1 - a)", "evaluate"),
    ("Sum(k*a**k, (k, 1, oo))", "a/(1 - a)**2", "evaluate"),
])
def test_a_series_claim_undefined_only_where_the_series_diverges_is_not_refuted(expr, claim, task):
    """Y3 (preexisting): 1/(1 - x) is undefined at x = 1, where Σ x**k diverges and has no value either."""
    assert _expr(expr, claim, task).verdict != "INCORRECT"


@pytest.mark.parametrize("expr,claim", [
    ("Sum(x**k, (k, 0, oo))", "1/(1 - x) + 0/(2*x - 1)"),       # undefined at 1/2, where the series is 2
    ("Sum(x**k, (k, 0, oo))", "1/(1 + x)"),
    ("Sum(x**k, (k, 0, oo))", "x/(1 - x)"),
])
def test_a_series_claim_undefined_where_the_series_converges_is_refuted(expr, claim):
    assert _expr(expr, claim).verdict == "INCORRECT"


def test_the_variable_of_an_inner_binder_is_no_zero_power_point():
    """Y2: t of Σ_k ∫_1^2 t**k dt is bound by the integral."""
    t = sp.Symbol("t", real=True)
    j = sp.Symbol("j", integer=True)
    assert definedness_conditions(sp.Sum(sp.Integral(t ** j, (t, 1, 2)), (j, 0, 3)), None) == []


@pytest.mark.parametrize("vars_,expr,claim", [
    # 2 - sign(a)**2 is 1 off 0 and 2 at 0, where 0**0 = 1 gives 1: right only under the other reading
    (V, "Sum(a**k, (k, 0, 3))", "2 + a + a**2 + a**3 - sign(a)**2"),
    # n = -2, -1 run the range backwards (Karr's value or the empty sum: another value), n = 0 is 0**0
    ([{"name": "n", "domain": "integer", "constraints": ["n**2 <= 4"]}, {"name": "k", "domain": "integer"}],
     "Sum(k, (k, 1, n)) + n**0", "n*(n + 1)/2 + 1"),
])
def test_only_a_point_whose_other_reading_is_undefined_is_read_with_sympys_value(vars_, expr, claim):
    ir = {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": vars_, "answer_shape": "expression"}
    assert _run(ir, claim, "expression").verdict == "UNKNOWN"


def test_a_geometric_series_diverges_at_one_and_converges_at_a_half():
    from mathverify.certify.algebra import _converges_somewhere
    from mathverify.certify.base import Ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import build_namespace
    ir = {"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": V, "answer_shape": "expression"}
    obj = load_problem_ir(ir)
    ctx = Ctx(obj, build_namespace(obj))
    j = sp.Symbol("j", integer=True)
    series = sp.Sum(x ** j, (j, 0, sp.oo))
    assert _converges_somewhere(series, x, sp.FiniteSet(1), ctx) is False
    assert _converges_somewhere(series, x, sp.FiniteSet(1, sp.Rational(1, 2)), ctx) is True
    assert _converges_somewhere(series, x, sp.Interval(1, 2), ctx) is None
