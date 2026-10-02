"""The step refuter after the fourth audit (part d4g, 2 Oct 2026; `steps.deterministic`).

* D4-ADIM-A: agreement at random points verified a wrong step on the premises' region (asin(sin(x)) = x on
  0 < x < 1.58, log(x**2) = 2*log(x) on x > -1/1000, binomial(n, 200) = 0 for n > 5, a Product on 21
  integers). Now only expressions analytic off a discrete set, compared on sets with interior, are verified
  by sampling (`_agreement_proves`); a proof of the comparison itself (cells, a period) still counts.
* D4-ADIM-B: a refutation was withdrawn whenever the claim had a Sum whose range may run backwards and the
  point did not fix it. Now it is withdrawn only when the refutation depends on the reading of that range
  (`_refuted_where_backwards`, `_refuted_in_both_readings`).
* D4-ADIM-E: the task's interval is a premise of compute steps; a refutation without a point is re-checked
  on the region.
* D4-ADIM-F: a step's re-check has a time budget, and a region SymPy left unevaluated is not sampled.
* D4-ADIM-H: a Sum identity verified only with Karr's value where the range runs backwards is unknown.
* D4-ADIM-J: a point where the claim, read as written, has no value is no counterexample.
* D4-ADIM-D, TAN-11: a step not proved defined on the set the premises leave (a Range, two symbols, one
  symbol pinned and another free) is not verified.

The tests marked "21c1698" fail there (measured: see the commit message).
"""
from __future__ import annotations

import time

import pytest
import sympy as sp

from mathverify.steps import deterministic as D
from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
N = {"name": "n", "domain": "integer"}
NP = {"name": "n", "domain": "positive_integer"}
K = {"name": "k", "domain": "integer"}
M = {"name": "m", "domain": "integer"}
J = {"name": "j", "domain": "integer"}


def _ir(expr, vars_, givens=(), kind="evaluate", params=None):
    return {"task": {"kind": kind, "params": params or {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": "scalar"}


def _run(ir, payload, steps, kind="value"):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""} for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _step(r):
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return layer.evidence["steps"][-1]


def _status(ir, payload, kind, claim):
    return _step(_run(ir, payload, [(kind, claim)]))["status"]


# --- D4-ADIM-A ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("givens, claim, vars_", [
    (["x > 0", "x < 1.58"], "asin(sin(x)) = x", [X]),                    # 21c1698
    (["x > -1/1000"], "log(x**2) = 2*log(x)", [X]),                       # 21c1698
    (["n > 5"], "binomial(n, 200) = 0", [N]),                             # 21c1698
    (["n >= 1", "n <= 21"], "Product(n - k, (k, 1, 20)) = 0", [N, K]),    # 21c1698
    (["x > 0", "x < 1.6"], "atan(tan(x)) = x", [X]),
])
def test_region_sample_agreement_verifies_nothing(givens, claim, vars_):
    assert _status(_ir("2 + 2", vars_, givens), "4", "compute", claim) != "verified"


def test_integer_sample_agreement_verifies_nothing():
    # 21c1698: verified on the positive integers by sampling (C(n, 200) is 0 at n = 1..199)
    assert _status(_ir("2 + 2", [NP]), "4", "compute", "binomial(n, 200) = 0") != "verified"


def test_region_controls_still_decide():
    assert _status(_ir("2 + 2", [X], ["x > 0"]), "4", "compute", "x**2 = x") == "refuted"
    assert _status(_ir("2 + 2", [X], ["x > 0"]), "4", "compute", "Abs(x) = x") == "verified"
    assert _status(_ir("2 + 2", [NP, K]), "4", "compute", "Sum(k, (k, 1, n)) = n*(n + 1)/2") == "verified"


def test_analytic_whitelist():
    x, n = sp.symbols("x n")
    assert D._analytic_off_discrete(sp.exp(x) * sp.sin(x) ** 2 + 1 / (x - 1) + sp.tan(x) + 2 ** x)
    for e in (sp.asin(sp.sin(x)), sp.log(x), sp.sqrt(x), sp.atan(x), sp.Abs(x), sp.binomial(n, 3),
              sp.factorial(n), sp.gamma(x), x ** n, (-1) ** x, sp.floor(x), sp.Max(x, 1)):
        assert not D._analytic_off_discrete(e), e
    assert D._has_interior(sp.S.Reals) and D._has_interior(sp.Interval(0, 1))
    assert D._has_interior(sp.Complement(sp.S.Reals, sp.FiniteSet(0)))
    for s_ in (sp.S.Integers, sp.Range(1, 22), sp.FiniteSet(1, 2), sp.FiniteSet(sp.sqrt(2)), sp.Interval(1, 1)):
        assert not D._has_interior(s_), s_


def test_agreement_proves_reads_the_comparison():
    x = sp.Symbol("x")
    rp = {"method": "random_point", "random_point": {}}
    assert D._agreement_proves(x ** 2, x * x, {x: sp.S.Reals}, rp)
    assert not D._agreement_proves(sp.log(x ** 2), 2 * sp.log(x), {x: sp.Interval(0, 1)}, rp)
    assert not D._agreement_proves(x ** 2, x * x, {x: sp.S.Integers}, rp)
    assert D._agreement_proves(sp.log(x), sp.log(x), {x: sp.S.Integers}, {"method": "symbolic"})
    cells = {"method": "random_point", "random_point": {"nonsmooth_proof": "cells_proved(2)"}}
    assert D._agreement_proves(sp.Abs(x), x, {x: sp.Interval(0, 1)}, cells)


# --- D4-ADIM-B ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("ir, payload, claim", [
    (_ir("Sum(k, (k, 1, 10))", [NP, K]), "55", "10*11/2 + Sum(0, (k, 1, n - 5)) = 56"),               # 21c1698
    (_ir("2 + 3", [X, NP, K]), "5", "Integral(cos(x), x) = -sin(x) + Sum(0, (k, 1, n - 5))"),         # 21c1698
    (_ir("Sum(j**2, (j, 1, 4))", [{"name": "m", "domain": "integer", "constraints": ["m >= 10"]}, J]),
     "30", "1 + 4 + 9 + 16 + Sum(0, (j, 1, m)) = 31"),                                                  # 21c1698
    (_ir("2 + 3", [X, M, J]), "5", "(x + 1)**2 = x**2 + 1 + Sum(0, (j, 1, m))"),                       # 21c1698
    (_ir("2 + 2", [N, J]), "4", "2 + 2 + Sum(1, (j, 1, n)) - n = 5"),                                   # 21c1698
])
def test_refutation_not_depending_on_the_reading_stands(ir, payload, claim):
    r = _run(ir, payload, [("compute", claim)])
    assert _step(r)["status"] == "refuted" and r.verdict == "INCORRECT"


def test_refutation_depending_on_the_reading_is_withdrawn():
    # Karr: Sum(1, (j, 1, -1)) = -1 != 0 = Max(-1, 0); the empty sum: 0 = 0
    assert _status(_ir("2 + 2", [N, J]), "4", "compute", "Sum(1, (j, 1, n)) = Max(n, 0)") != "refuted"
    # part 11 stays: Karr's -2 at the given n = 1
    r = _run(_ir("x + 1", [X, K, N], ["x = 5", "n = 1"]), "6", [("eq", "Sum(k, (k, 3, n)) = 0")])
    assert _step(r)["status"] != "refuted" and r.verdict != "INCORRECT"


def test_backward_point_where_both_readings_refute():
    # 21c1698: withdrawn at a random n < 0, where Sum(0, ...) is 0 under both readings
    r = _run(_ir("x + 1", [X, K, N], ["n < 0"]), "x + 1", [("compute", "Sum(0, (k, 1, n)) + x = x + 1")],
             kind="expression")
    assert _step(r)["status"] == "refuted"
    # pinned to n = -3 the parser does not read the reversed range: unknown, as before
    r = _run(_ir("x + 1", [X, K, N], ["x = 5", "n = -3"]), "6", [("compute", "Sum(0, (k, 1, n)) + 1 = 2")])
    assert _step(r)["status"] == "unknown"


def test_empty_reading_and_span_state():
    n, k = sp.symbols("n k")
    s = sp.Sum(k, (k, 1, n))
    claim = sp.Eq(s, n * (n + 1) / 2)
    nodes = D._symbolic_range_nodes(claim)
    assert nodes == [s]
    assert D._empty_reading(claim, nodes, {n: sp.Integer(-3)}) == sp.Eq(0, n * (n + 1) / 2)
    assert D._empty_reading(claim, nodes, {n: sp.Integer(4)}) == claim
    ranges = [c for c in D._range_spans(claim)]
    assert D._span_state(ranges, {n: sp.Integer(5)}) == "forward"
    assert D._span_state(ranges, {n: sp.Integer(0)}) == "forward"          # the empty sum
    assert D._span_state(ranges, {n: sp.Integer(-2)}) == "backward"
    assert D._span_state(ranges, {}) is None


# --- D4-ADIM-E ---------------------------------------------------------------------------------------------

EX = _ir(None, [{"name": "x"}], kind="extremum",
         params={"f": "Abs(x) + x**2", "var": "x", "interval": "[1, 3]", "which": "max"})
DI = _ir(None, [{"name": "x"}], kind="definite_integral", params={"integrand": "Abs(x)", "var": "x", "a": "0", "b": "2"})


@pytest.mark.parametrize("ir, payload, claim", [
    (EX, "12", "diff(Abs(x) + x**2, x) = 1 + 2*x"),          # 21c1698
    (DI, "2", "Abs(x) = x"),                                 # 21c1698
    (DI, "2", "Integral(Abs(x), x) = x**2/2"),               # 21c1698
])
def test_task_interval_is_a_premise_of_compute_steps(ir, payload, claim):
    r = _run(ir, payload, [("compute", claim)])
    assert _step(r)["status"] != "refuted" and r.verdict != "INCORRECT"


@pytest.mark.parametrize("ir, payload, claim", [
    (EX, "12", "diff(Abs(x) + x**2, x) = 2*x"),
    (DI, "2", "Abs(x) = -x"),
    (DI, "2", "Integral(Abs(x), x) = x**3"),
])
def test_wrong_inside_the_task_interval_still_refuted(ir, payload, claim):
    assert _status(ir, payload, "compute", claim) == "refuted"


# --- D4-ADIM-F ---------------------------------------------------------------------------------------------

def test_cubic_premise_is_quick():
    # 21c1698: 120 s here (166-390 s measured by the audit)
    t = time.time()
    st = _status(_ir("x**3 - 3*x", [X], ["x**3 - 3*x + 1 = 0"]), "-1", "compute", "x**3 - 3*x = -1")
    assert st in ("verified", "unknown") and time.time() - t < 60


def test_step_budget_makes_the_step_unknown(monkeypatch):
    monkeypatch.setattr(D, "_STEP_BUDGET", -1.0)
    st = _step(_run(_ir("2 + 2", [X], ["x > 0"]), "4", [("compute", "Abs(x) = -x")]))
    assert st["status"] == "unknown" and st["evidence"]["reason"] == "step_time_budget_exceeded"


def test_closed_form_sets():
    assert D._closed_form_set(sp.Interval(0, 1)) and D._closed_form_set(sp.Range(1, 5))
    assert D._closed_form_set(sp.FiniteSet(1, sp.sqrt(2)))
    assert D._closed_form_set(sp.Complement(sp.S.Reals, sp.FiniteSet(0)))
    x = sp.Symbol("x")
    assert not D._closed_form_set(sp.solveset(x ** 3 - 3 * x + 1, x, sp.S.Reals))
    assert not D._closed_form_set(sp.ConditionSet(x, sp.Eq(sp.sin(x), x), sp.S.Reals))


# --- D4-ADIM-H ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("vars_, givens, claim", [
    ([N, K], ["n < 0", "n > -4"], "Sum(k, (k, 1, n)) = n*(n + 1)/2"),      # 21c1698
    ([N, K], [], "Sum(k, (k, 1, n)) = n*(n + 1)/2"),                        # 21c1698
    ([N, K], [], "Product(2, (k, 1, n)) = 2**n"),                           # 21c1698
])
def test_karr_only_identity_is_not_verified(vars_, givens, claim):
    assert _step(_run(_ir("n", vars_, givens), "n", [("compute", claim)], kind="expression"))["status"] == "unknown"


@pytest.mark.parametrize("vars_, givens, claim", [
    ([NP, K], [], "Sum(k, (k, 1, n)) = n*(n + 1)/2"),
    ([N, K], ["n > 0"], "Sum(k, (k, 1, n)) = n*(n + 1)/2"),
    ([N, K], [], "Sum(0, (k, 1, n)) = 0"),
])
def test_identity_on_forward_points_still_verified(vars_, givens, claim):
    assert _step(_run(_ir("n", vars_, givens), "n", [("compute", claim)], kind="expression"))["status"] == "verified"


# --- D4-ADIM-J ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("givens, claim", [
    (["x**2 = 4"], "sqrt(x**3) = x*sqrt(x)"),      # 21c1698
    (["x**2 = 1"], "log(x**2) = 2*log(x)"),
    ([], "sqrt(x**3) = x*sqrt(x)"),
])
def test_point_where_the_claim_is_undefined_refutes_nothing(givens, claim):
    for kind in ("compute", "eq"):
        r = _run(_ir("x", [X], givens), "x", [(kind, claim)])
        assert _step(r)["status"] != "refuted", kind


@pytest.mark.parametrize("givens, claim", [
    (["x**2 = 4"], "sqrt(x**2) = x"),
    (["x**2 = 1"], "log(x**2) = 2*log(x) + 1"),
    ([], "log(x**2) = 2*log(x) + 1"),
])
def test_defined_counterexample_still_refutes(givens, claim):
    assert _status(_ir("x", [X], givens), "x", "compute", claim) == "refuted"


# --- D4-ADIM-D, TAN-11 -------------------------------------------------------------------------------------

@pytest.mark.parametrize("ir, kind, claim", [
    (_ir("x", [{"name": "x", "domain": "integer"}], ["x >= -1", "x <= 10"]), "compute", "x/x = 1"),       # 21c1698
    (_ir("x", [X, Y], ["x**2 = 4", "y**2 = 1"]), "eq", "sqrt(x)**2 + sqrt(y)**2 = x + y"),               # 21c1698
    (_ir("x + 1", [{"name": "x"}, {"name": "y"}], ["x = 0"]), "eq", "x/x + sqrt(y) - sqrt(y) = 1"),       # 21c1698
    (_ir("x", [{"name": "x", "domain": "integer"}], ["x >= -1000", "x <= 1000"]), "eq", "x/x = 1"),       # 21c1698
])
def test_undefined_where_the_premises_allow_is_not_verified(ir, kind, claim):
    st = _step(_run(ir, "1", [(kind, claim)]))
    assert st["status"] == "unknown" and st["reason"] == "claim_undefined_at_the_premises_point"


@pytest.mark.parametrize("ir, kind, claim", [
    (_ir("x", [{"name": "x", "domain": "integer"}], ["x >= 1", "x <= 10"]), "eq", "x/x = 1"),
    (_ir("x", [X], ["x > 0"]), "eq", "sqrt(x)**2 = x"),
    (_ir("x", [X]), "eq", "x/x = 1"),
])
def test_defined_where_the_premises_allow_still_verified(ir, kind, claim):
    assert _step(_run(ir, "1", [(kind, claim)]))["status"] == "verified"


def test_pinned_symbol_where_defined_is_not_flagged():
    # x = 2 pinned, y free: x/x is defined there (the eq route leaves the step unknown, before too)
    st = _step(_run(_ir("x + 1", [{"name": "x"}, {"name": "y"}], ["x = 2"]), "3", [("eq", "x/x + y = 1 + y")]))
    assert st["status"] != "refuted" and st.get("reason") != "claim_undefined_at_the_premises_point"


def test_defined_on_finite_points_of_two_symbols():
    # x*y + 3 >= 1 at each of the four points: read point by point, not as a condition on two symbols
    ir = _ir("x", [X, Y], ["x**2 = 4", "y**2 = 1"])
    assert _step(_run(ir, "1", [("eq", "(x*y + 3)/(x*y + 3) = 1")]))["status"] == "verified"


def test_value_convention_condition_left_to_its_rules():
    # Mod's divisor condition is a convention (part d4a), not proved on the infinite set n > 1 here
    assert _step(_run(_ir("n", [N], ["n > 1"]), "n", [("eq", "Mod(n, n) = 0")]))["status"] == "verified"


def test_reading_dependent_backward_points_refute_nothing():
    # n < -1: every range runs backwards; Sum(1, (j, 1, n)) is n (Karr) or 0 (empty): no refutation, while
    # at the forward n = 0, which the premise excludes, the claim is false
    st = _step(_run(_ir("2 + 2", [N, J], ["n < -1"]), "4", [("compute", "2 + Sum(1, (j, 1, n)) - n = 3")]))
    assert st["status"] != "refuted"


def test_undefined_instance_skipped_defined_one_refutes():
    # instances -2 (both sides non-real) and 3 (3*sqrt(3) != 3*sqrt(3) + 1): refuted at 3
    r = _run(_ir("x", [X], ["(x + 2)*(x - 3) = 0"]), "x", [("compute", "sqrt(x**3) = x*sqrt(x) + 1")])
    assert _step(r)["status"] == "refuted"


def test_identity_verified_only_where_defined_is_unknown():
    # value Abs(x) = x, written with log(x): refuted at x < 0, where the claim has no value; on x > 0 it holds,
    # but only where the claim is defined: unknown, not verified
    assert _status(_ir("x", [X]), "x", "compute", "Abs(x) = x + log(x) - log(x)") == "unknown"


def test_branch_functions_analytic_on_the_interval():
    # log's arguments are positive on x > 3: agreement on the interval proves the identity there (K4 tyt-den)
    assert _status(_ir("2 + 2", [{"name": "x", "domain": "real", "constraints": ["x > 3"]}]), "4", "compute",
                   "log(x - 1) + log(x - 3) = log((x - 1)*(x - 3))") == "verified"
    # not on x > -1/1000, where x and x**2 reach 0
    assert _status(_ir("2 + 2", [{"name": "x", "domain": "real", "constraints": ["x > -1/1000"]}]), "4", "compute",
                   "log(x**2) = 2*log(x)") != "verified"


def test_readable_backward_point_with_a_reading_free_range_refutes():
    # every n < -1 runs the range backwards; Sum(0, ...) is 0 under both readings: the random point refutes
    ir = _ir("2 + 2", [{"name": "n", "domain": "integer", "constraints": ["n < -1"]}, K])
    st = _step(_run(ir, "4", [("compute", "Sum(0, (k, 1, n)) + n**2 = n**2 + 1")]))
    assert st["status"] == "refuted"


def test_counterexample_searched_where_the_claim_is_defined():
    # the identity check's point x < 0 leaves both sides non-real; on x >= 0 the claim is false
    assert _status(_ir("x", [X]), "x", "compute", "sqrt(x**3) = x*sqrt(x) + 1") == "refuted"


def test_condition_on_two_symbols_over_infinite_sets_not_proved():
    # x > 0, y > 0 allow x < y, where sqrt(x - y) is not real
    st = _step(_run(_ir("x", [X, Y], ["x > 0", "y > 0"]), "1", [("eq", "sqrt(x - y)**2 = x - y")]))
    assert st["status"] == "unknown" and st["reason"] == "claim_undefined_at_the_premises_point"


def test_premise_leaving_the_whole_domain_narrows_nothing():
    # K4 ayt-lim-006: the proved eq step x*log(x) = log(x)/(1/x) holds on all of R as SymPy reads it; it does
    # not narrow x, and diff(log(x), x) = 1/x stays verified
    ir = _ir(None, [{"name": "x"}], kind="limit", params={"expr": "x*log(x)", "var": "x", "to": "0", "side": "+"})
    r = _run(ir, "0", [("eq", "x*log(x) = log(x)/(1/x)"), ("compute", "diff(log(x), x) = 1/x")])
    assert _step(r)["status"] == "verified"
