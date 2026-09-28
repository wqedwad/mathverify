"""Three unjust refutations of correct steps found by the first real-solver run (K4, Muse Spark 1.3,
28 Sep 2026; DECISIONS §63), and the refutations that must survive their fixes.

(A) The task's own interval was not a premise: "x = pi/3" from tan x = sqrt(3) on [0, pi) was
    refuted with x = 4*pi/3 (ayt-trig-004/-013/-017).
(B) An assignment whose symbols only their domains constrain was treated as a consequence:
    "n = 20" (the 20th term) was refuted with {k: 109, n: 50} (11 ayt-diz solutions).
(C) The curve of a tangent-line task written as `y = x**2` became a premise, and the tangent
    `y = 2*x - 1` was refuted with a point of the curve (ayt-tur-003/-010/-013).
The steps below are the solver's own, from reports/arsiv/2026-09-28/solver_meta_progress_partial.jsonl.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import sympy as sp

from mathverify.verifier import verify

ROOT = Path(__file__).resolve().parents[1]


def _ir(item_id):
    it = json.loads((ROOT / "evalset" / "items" / f"{item_id}.json").read_text(encoding="utf-8"))
    return it["problem_ir"]


def _sol(payload, kind, steps, option=None):
    return {"claimed_answer": {"kind": kind, "payload": payload, "option": option},
            "steps": [{"id": f"s{i}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps, start=1)]}


def _steps(r):
    layer = next(l for l in r.layers if l.layer == "steps.refute")
    return {e["id"]: (e["status"], e.get("reason") or (e.get("evidence") or {}).get("reason"))
            for e in layer.evidence["steps"]}


# ------------------------------------------------------------------ (A) the task's interval
TRIG = [("eq", "tan(x) = sqrt(3)"), ("assert", "0 <= x"), ("assert", "x < pi"), ("assert", "x != pi/2"),
        ("compute", "tan(pi/3) = sqrt(3)")]


def test_a_root_inside_the_tasks_interval_is_a_consequence():
    r = verify(_ir("ayt-trig-004"), _sol("{pi/3}", "set", TRIG + [("eq", "x = pi/3")], option="B"))
    assert r.verdict == "CORRECT", r.decision_trace
    assert _steps(r)["s6"][0] == "verified"


@pytest.mark.parametrize("claim", ["x = 4*pi/3", "x = pi/6", "x > pi/2"])
def test_a_wrong_step_is_still_refuted_inside_the_interval(claim):
    r = verify(_ir("ayt-trig-004"), _sol("{pi/3}", "set", TRIG + [("eq", claim)], option="B"))
    assert r.verdict == "INCORRECT" and _steps(r)["s6"][0] == "refuted", _steps(r)


def test_the_interval_binds_no_symbol():
    """The window only narrows the search: an inequality about a variable no premise mentions stays
    definitional (the extremum's `2*x - 4 > 0` is the solver's case, not a consequence of [-2, 3])."""
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.steps.deterministic import _check_eq, _task_window
    ir = load_problem_ir(_ir("ayt-tur-001"))
    ctx = make_ctx(ir)
    x = ctx.ns["x"]
    window = _task_window(ir, ctx)
    assert set(window) == {sp.Le(-2, x), sp.Le(x, 3)}
    status, ev = _check_eq(sp.Gt(2 * x - 4, 0), [], ctx, ctx.var_constraints(), window)
    assert status == "skipped" and ev["reason"] == "definitional_claim_introduces_unconstrained_symbols"


def test_the_window_joins_only_when_its_variable_is_in_play():
    """A window on x among premises about `a` alone left every sampled point undecided (x unset),
    and the wrong "a > 5" under the given "a > 1" became unknown instead of refuted."""
    ir = {"task": {"kind": "extremum", "params": {"f": "x**2 - a*x", "var": "x", "interval": "[0, 3]", "which": "min"}},
          "vars": [{"name": "x"}, {"name": "a"}], "givens": ["a > 1"]}
    assert _steps(verify(ir, _sol("0", "value", [("eq", "a > 5")])))["s1"][0] == "refuted"
    assert _steps(verify(ir, _sol("0", "value", [("eq", "a > 0")])))["s1"][0] == "verified"


@pytest.mark.parametrize("interval,expected", [("[0, 2*pi)", 2), ("(0, oo)", 1), ("Reals", 0), ("[1, 0]", 0),
                                               ("not a set", 0)])
def test_the_window_reads_the_interval_or_nothing(interval, expected):
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.steps.deterministic import _task_window
    d = _ir("ayt-trig-004")
    d["task"]["params"]["interval"] = interval
    ir = load_problem_ir(d)
    assert len(_task_window(ir, make_ctx(ir))) == expected


# ------------------------------------------------------------------ (A') a window the premises miss
def _extremum(f, interval, which="max"):
    return {"task": {"kind": "extremum", "params": {"f": f, "var": "x", "interval": interval, "which": which}},
            "vars": [{"name": "x"}], "givens": [], "answer_shape": "scalar"}


def _trig(equation, interval):
    return {"task": {"kind": "trig_solve", "params": {"equation": equation, "var": "x", "interval": interval}},
            "vars": [{"name": "x"}], "givens": [], "answer_shape": "set"}


@pytest.mark.parametrize("ir,answer,kind,steps,bad", [
    # critical points +-1 lie outside [2, 4]: "x = 3" held vacuously and the right maximum 52 was CORRECT
    (_extremum("x**3 - 3*x", "[2, 4]"), "52", "value",
     [("compute", "diff(x**3 - 3*x, x) = 3*x**2 - 3"), ("eq", "3*x**2 - 3 = 0"), ("eq", "x = 3"),
      ("compute", "at(x**3 - 3*x, x, 4) = 52")], "s3"),
    (_extremum("x**2 - 6*x", "[0, 2]", "min"), "-8", "value",
     [("compute", "diff(x**2 - 6*x, x) = 2*x - 6"), ("eq", "2*x - 6 = 0"), ("eq", "x = 1"),
      ("compute", "at(x**2 - 6*x, x, 2) = -8")], "s3"),
    # cos x = -1 has no root in [0, pi): the answer {} is right, "x = 0" is not
    (_trig("cos(x) = -1", "[0, pi)"), "{}", "set", [("eq", "cos(x) = -1"), ("eq", "x = 0")], "s2"),
])
def test_a_wrong_step_is_refuted_when_the_premises_have_no_instance_in_the_window(ir, answer, kind, steps, bad):
    """Probe of 28 Sep 2026: all three were INCORRECT before the window existed and CORRECT with it."""
    r = verify(ir, _sol(answer, kind, steps))
    assert r.verdict == "INCORRECT" and _steps(r)[bad][0] == "refuted", (r.verdict, _steps(r))
    layer = next(l for l in r.layers if l.layer == "steps.refute")
    ev = next(e for e in layer.evidence["steps"] if e["id"] == bad)["evidence"]
    assert ev["window_dropped"] == "no_premise_instance_inside_the_task_interval"


def test_the_right_roots_outside_the_window_are_still_a_consequence():
    steps = [("compute", "diff(x**3 - 3*x, x) = 3*x**2 - 3"), ("eq", "3*x**2 - 3 = 0"), ("eq", "x in {-1, 1}"),
             ("compute", "at(x**3 - 3*x, x, 4) = 52")]
    r = verify(_extremum("x**3 - 3*x", "[2, 4]"), _sol("52", "value", steps))
    assert r.verdict == "CORRECT" and _steps(r)["s3"][0] == "verified", _steps(r)


def _ctx2():
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    ir = load_problem_ir({"task": {"kind": "extremum", "params": {"f": "x**2 - a*x", "var": "x", "interval": "[3, 5]",
                                                                  "which": "min"}},
                          "vars": [{"name": "x"}, {"name": "a"}], "givens": [], "answer_shape": "scalar"})
    ctx = make_ctx(ir)
    return ctx, ctx.ns["x"], ctx.ns["a"]


def test_a_solved_system_outside_the_window_drops_the_window():
    """Two unknowns: the solved premises give x = 1 only, outside [3, 5]."""
    from mathverify.steps.deterministic import _check_eq
    ctx, x, a = _ctx2()
    prem, window = [sp.Eq(a, 2), sp.Eq(2 * x - a, 0)], [sp.Le(3, x), sp.Le(x, 5)]
    status, ev = _check_eq(sp.Eq(x + a, 4), prem, ctx, [], window)
    assert status == "refuted" and ev["window_dropped"], ev
    assert _check_eq(sp.Eq(x + a, 3), prem, ctx, [], window)[0] == "verified"


def test_a_thin_premise_set_outside_the_window_drops_it_on_the_set_route():
    """x = sqrt(2) written as two inequalities: no sample and no grid point lands on it, so only the
    premise-set route can tell that the window [0, 1] leaves no instance."""
    from mathverify.steps.deterministic import _check_eq
    ctx, x, _ = _ctx2()
    prem, window = [sp.Ge(x, sp.sqrt(2)), sp.Le(x, sp.sqrt(2))], [sp.Le(0, x), sp.Le(x, 1)]
    status, ev = _check_eq(sp.Eq(x, 2), prem, ctx, [], window)
    assert status == "refuted" and ev["window_dropped"] and ev["route"] == "premise_set", ev


def test_sampling_draws_the_windows_variable_from_the_window():
    """No equations: sampled. A window far from the samples' usual range is still met, so a claim
    true on it is not refuted outside it; a window the premises cannot meet is dropped."""
    from mathverify.steps.deterministic import _check_eq
    ctx, x, a = _ctx2()
    prem = [sp.Gt(a, 0), sp.Gt(x, a)]
    far = [sp.Le(1000, x), sp.Le(x, 1001)]
    status, ev = _check_eq(sp.Gt(x, 500), prem, ctx, [], far)
    assert status == "unknown" and "window_dropped" not in ev, ev
    assert _check_eq(sp.Lt(x, a), prem, ctx, [], far)[0] == "refuted"
    missed = [sp.Le(-5, x), sp.Le(x, -4)]
    status, ev = _check_eq(sp.Lt(x, a), prem, ctx, [], missed)
    assert status == "refuted" and ev["window_dropped"], ev


# ------------------------------------------------------------------ (B) assignments
DIZ =[("eq", "n = 20"), ("eq", "k = 5 + (n - 1)*3"), ("eq", "k = 5 + (20 - 1)*3"), ("compute", "5 + (20 - 1)*3 = 62")]


def test_an_assignment_bound_only_by_domains_is_a_definition():
    r = verify(_ir("ayt-diz-002"), _sol("62", "value", DIZ, option="C"))
    assert r.verdict == "CORRECT", r.decision_trace
    st = _steps(r)
    assert st["s1"] == ("skipped", "definitional_claim_introduces_unconstrained_symbols")
    assert st["s2"] == ("skipped", "definitional_claim_introduces_unconstrained_symbols")
    assert st["s3"][0] == "verified"                      # follows from the two definitions


@pytest.mark.parametrize("bad", ["k = 5 + (20 - 1)*4", "k = 63", "n = 21"])
def test_a_wrong_consequence_of_the_definitions_is_still_refuted(bad):
    """Once `n = 20` and the general term are stated they are premises: a wrong substitution, a
    wrong value or a second, different assignment of n contradicts them."""
    r = verify(_ir("ayt-diz-002"), _sol("62", "value", DIZ[:2] + [("eq", bad)], option="C"))
    assert r.verdict == "INCORRECT" and _steps(r)["s3"][0] == "refuted", _steps(r)


def test_a_finite_choice_is_an_assignment_too():
    """`n in {20, 21}` parses to an Or of equations; `n in {20}` to the equation itself."""
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.steps.deterministic import _check_eq, _parse_claim
    ir = load_problem_ir(_ir("ayt-diz-002"))
    ctx = make_ctx(ir)
    choice = _parse_claim("n in {20, 21}", ctx.ns)
    assert isinstance(choice, sp.Or)
    assert _check_eq(choice, [], ctx, ctx.var_constraints())[0] == "skipped"
    r = verify(_ir("ayt-diz-002"), _sol("62", "value", [("eq", "n in {20}")] + DIZ[1:], option="C"))
    assert _steps(r)["s1"] == ("skipped", "definitional_claim_introduces_unconstrained_symbols")
    assert r.verdict == "CORRECT", r.decision_trace


_FORCED = {"task": {"kind": "evaluate", "params": {"expr": "n + 1"}},
           "vars": [{"name": "n", "domain": "positive_integer", "constraints": ["n <= 1"]}], "givens": []}
_SIMP = {"task": {"kind": "simplify_expression", "params": {"expr": "(x**2 - 9)/(x - 3)"}},
         "vars": [{"name": "x"}], "givens": [], "answer_shape": "expression"}
_SIMP_STEP = ("compute", "(x**2 - 9)/(x - 3) = x + 3")


@pytest.mark.parametrize("ir,answer,kind,steps", [
    (_ir("ayt-diz-002"), "62", "value", [("eq", "n = 0"), ("compute", "5 + (20 - 1)*3 = 62")]),  # n > 0
    (_FORCED, "2", "value", [("eq", "n = 2"), ("compute", "1 + 1 = 2")]),                 # constraints leave n = 1
    (_SIMP, "x + 3", "expression", [("eq", "x = 3"), _SIMP_STEP]),                         # written x != 3
])
def test_an_assignment_no_value_of_the_domain_satisfies_is_refuted(ir, answer, kind, steps):
    """Probe of 28 Sep 2026: all three were INCORRECT before #11 and CORRECT after it (definitional)."""
    r = verify(ir, _sol(answer, kind, steps))
    assert r.verdict == "INCORRECT" and _steps(r)["s1"][0] == "refuted", (r.verdict, _steps(r))


@pytest.mark.parametrize("ir,answer,kind,steps", [
    (_FORCED, "2", "value", [("eq", "n = 1"), ("compute", "1 + 1 = 2")]),
    (_SIMP, "x + 3", "expression", [("eq", "x = 2"), _SIMP_STEP]),           # refuted before #11 as well
    # a choice: one option outside the domain, one inside. (On a positive-integer n SymPy drops the
    # option n = 0 while parsing, so "n in {0, 20}" is just n = 20 and would test nothing.)
    (_SIMP, "x + 3", "expression", [("eq", "x in {2, 3}"), _SIMP_STEP]),
])
def test_an_assignment_some_value_of_the_domain_satisfies_stays_a_definition(ir, answer, kind, steps):
    r = verify(ir, _sol(answer, kind, steps))
    assert _steps(r)["s1"] == ("skipped", "definitional_claim_introduces_unconstrained_symbols"), _steps(r)
    assert r.verdict == "CORRECT", r.decision_trace


def test_a_wrong_assignment_the_domain_allows_is_a_known_limit():
    """V12: "n = 21" where the task asks the 20th term. The IR's n is the recurrence's index, not the
    asked one (`index` is a parameter, no given binds n), so nothing refutes it. Before #11 it was
    refuted, but so was the right "n = 20": that detection did not discriminate."""
    r = verify(_ir("ayt-diz-002"), _sol("62", "value", [("eq", "n = 21")] + DIZ[2:], option="C"))
    assert _steps(r)["s1"] == ("skipped", "definitional_claim_introduces_unconstrained_symbols")
    assert r.verdict == "CORRECT", r.decision_trace


def test_an_inequality_is_still_checked_against_the_domain_conditions():
    """The written condition x - 3 >= 0 of sqrt(x - 3) still binds a non-assignment: "x >= 4" is a
    refutable consequence (x = 3), "x >= 3" follows."""
    ir = _ir("tyt-kap-001")
    ok = verify(ir, _sol("[3, oo)", "interval", [("eq", "x >= 3")]))
    assert _steps(ok)["s1"][0] == "verified"
    bad = verify(ir, _sol("[3, oo)", "interval", [("eq", "x >= 4")]))
    assert _steps(bad)["s1"][0] == "refuted" and bad.verdict == "INCORRECT"


def test_a_domain_condition_of_two_variables_still_narrows_the_search():
    """sqrt(x - y) is defined only for x >= y; with x + y = 10 that makes x >= 5 a consequence.
    The restriction binds nothing for an assignment but it still narrows every search: as a premise
    and, point by point, through `_in_domains` (so dropping it from the premises alone changes
    nothing: an equivalent mutation, B05). Sampled, so not "verified": see below."""
    ir = {"task": {"kind": "evaluate", "params": {"expr": "sqrt(x - y)"}},
          "vars": [{"name": "x"}, {"name": "y"}], "givens": ["x + y = 10"]}
    assert _steps(verify(ir, _sol("0", "value", [("eq", "x >= 5")])))["s1"] == \
        ("unknown", "no_counterexample_at_sampled_points")
    assert _steps(verify(ir, _sol("0", "value", [("eq", "x >= 20")])))["s1"][0] == "refuted"


def test_an_assignment_with_a_given_behind_it_is_still_a_consequence():
    """The givens bind: "a = 14" in the chicken-and-rabbit problem is refuted, "a = 16" verified."""
    ir = {"task": {"kind": "evaluate", "params": {"expr": "a"}},
          "vars": [{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
          "givens": ["a + b = 30", "2*a + 4*b = 88"]}
    assert _steps(verify(ir, _sol("16", "value", [("eq", "a = 16")])))["s1"][0] == "verified"
    r = verify(ir, _sol("16", "value", [("eq", "a = 14")]))
    assert _steps(r)["s1"][0] == "refuted" and r.verdict == "INCORRECT"


# ------------------------------------------------------------------ (C) the task's own objects
TUR = [("eq", "y = x**2"), ("compute", "at(x**2, x, 1) = 1"), ("compute", "diff(x**2, x) = 2*x"),
       ("compute", "at(2*x, x, 1) = 2")]


def test_the_curve_of_a_tangent_task_is_no_premise_for_the_tangent():
    r = verify(_ir("ayt-tur-003"), _sol("y = 2*x - 1", "equation", TUR + [("eq", "y = 2*x - 1")], option="A"))
    assert r.verdict == "CORRECT", r.decision_trace
    st = _steps(r)
    assert st["s1"] == ("skipped", "states_a_task_object")
    assert st["s5"] == ("skipped", "definitional_claim_introduces_unconstrained_symbols")


@pytest.mark.parametrize("curve", ["y = x**2", "y - x**2 = 0", "2*y = 2*x**2", "x**2 = y"])
def test_the_curve_is_recognised_in_any_equivalent_form_and_never_refuted(curve):
    """Written after the tangent, the curve was refuted against it; now it is not checked at all."""
    steps = [("eq", "y - 1 = 2*(x - 1)"), ("eq", curve), ("eq", "y = 2*x - 1")]
    r = verify(_ir("ayt-tur-003"), _sol("y = 2*x - 1", "equation", steps, option="A"))
    st = _steps(r)
    assert st["s2"] == ("skipped", "states_a_task_object"), st
    assert st["s3"] == ("unknown", "no_counterexample_at_sampled_points"), st     # a line, sampled
    assert r.verdict == "CORRECT"


@pytest.mark.parametrize("wrong", ["y = 2*x + 1", "y = x - 1"])
def test_a_wrong_rewrite_of_the_tangent_is_still_refuted(wrong):
    steps = TUR + [("eq", "y - 1 = 2*(x - 1)"), ("eq", wrong)]
    r = verify(_ir("ayt-tur-003"), _sol("y = 2*x - 1", "equation", steps, option="A"))
    assert _steps(r)["s6"][0] == "refuted" and r.verdict == "INCORRECT"


_SLOPE = [("compute", "diff(x**2, x) = 2*x"), ("compute", "at(2*x, x, 1) = 2")]


@pytest.mark.parametrize("steps,flagged", [
    ([("eq", "y = x**2"), ("eq", "x = 1"), ("eq", "y = 2")] + _SLOPE + [("eq", "y = 2*x - 1")], "s6"),
    ([("eq", "x = 1"), ("eq", "y = 2")] + _SLOPE + [("eq", "y = 2*x - 1")], "s5"),
    ([("eq", "y = x**2")] + _SLOPE + [("eq", "y = 2*x + 1"), ("eq", "y = 2*x - 1")], "s5"),
])
def test_a_wrong_point_or_line_is_still_caught_without_the_curve_as_a_premise(steps, flagged):
    """Probe of 28 Sep 2026 (C): with the curve out of the premises, a wrong ordinate of the point of
    tangency ("y = 2", f(1) = 1) or a wrong line in the middle is a definition and is not refuted
    itself, but the right answer contradicts it: the solution stays INCORRECT, as before #11. The
    step flagged is the later, right one: a localization limit, not a false accept."""
    r = verify(_ir("ayt-tur-003"), _sol("y = 2*x - 1", "equation", steps, option="A"))
    assert r.verdict == "INCORRECT" and _steps(r)[flagged][0] == "refuted", _steps(r)


def test_a_point_chosen_on_a_stated_line_is_refuted_as_a_consequence():
    """V13, a false rejection in every version (before #11 too): the tangent's y-intercept written as
    "x = 0", "y = -1" after "y = 2*x - 1". The line in the pool binds x, so the chosen x = 0 is read as
    a consequence of it and refuted. Pinned here so that a fix is a visible change."""
    steps = _SLOPE + [("eq", "y = 2*x - 1"), ("eq", "x = 0"), ("eq", "y = -1")]
    r = verify(_ir("ayt-tur-003"), _sol("y = 2*x - 1", "equation", steps, option="A"))
    assert _steps(r)["s4"][0] == "refuted" and r.verdict == "INCORRECT", _steps(r)


@pytest.mark.parametrize("claim", ["y = x**2 + 1", "y = 2*x**2", "y**2 = x**2"])
def test_a_curve_that_is_not_the_tasks_is_checked_as_before(claim):
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import parse_relation
    from mathverify.steps.deterministic import _states_task_object, _task_objects
    ir = load_problem_ir(_ir("ayt-tur-003"))
    ctx = make_ctx(ir)
    assert not _states_task_object(parse_relation(claim, ctx.ns), _task_objects(ir, ctx), ctx)


def test_only_a_constant_factor_is_recognised():
    """(x**2 + 1)*(y - x**2) = 0 is the same curve over the reals, but the rule is the conservative
    one its docstring states: a nonzero CONSTANT factor. Anything else is checked as before."""
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.normalize.parse import parse_relation
    from mathverify.steps.deterministic import _states_task_object, _task_objects
    ir = load_problem_ir(_ir("ayt-tur-003"))
    ctx = make_ctx(ir)
    objs = _task_objects(ir, ctx)
    assert _states_task_object(parse_relation("3*y = 3*x**2", ctx.ns), objs, ctx)
    assert not _states_task_object(parse_relation("(x**2 + 1)*y = (x**2 + 1)*x**2", ctx.ns), objs, ctx)


def _eq_of(obj, **params):
    return {"task": {"kind": "equation_of", "params": {"object": obj, **params}},
            "vars": [{"name": "x"}, {"name": "y"}], "answer_shape": "equation"}


def test_the_given_line_of_a_parallel_line_task_is_no_premise():
    ir = _eq_of("line_point_parallel", p=["1", "5"], line="y = 2*x + 1")
    steps = [("eq", "y = 2*x + 1"), ("eq", "y - 5 = 2*(x - 1)"), ("eq", "y = 2*x + 3")]
    r = verify(ir, _sol("y = 2*x + 3", "equation", steps))
    assert _steps(r)["s1"] == ("skipped", "states_a_task_object") and r.verdict == "CORRECT", r.decision_trace
    bad = verify(ir, _sol("y = 2*x + 3", "equation", steps[:2] + [("eq", "y = 2*x + 4")]))
    assert _steps(bad)["s3"][0] == "refuted"
    # a wrong line in the middle, no point-slope form: the right answer contradicts it (probe C4)
    mid = verify(ir, _sol("y = 2*x + 3", "equation", [steps[0], ("eq", "y = 3*x + 2"), steps[2]]))
    assert mid.verdict == "INCORRECT" and _steps(mid)["s3"][0] == "refuted", _steps(mid)


def test_the_circle_of_a_tangent_to_circle_task_is_no_premise():
    ir = _eq_of("tangent_to_circle_at_point", center=["0", "0"], point=["3", "4"])
    steps = [("eq", "x**2 + y**2 = 25"), ("eq", "3*x + 4*y = 25")]
    r = verify(ir, _sol("3*x + 4*y = 25", "equation", steps))
    assert _steps(r)["s1"] == ("skipped", "states_a_task_object") and r.verdict == "CORRECT", r.decision_trace


# ------------------------------------------------------------------ "verified" means proved
def _one(ir, claim):
    return _steps(verify(ir, _sol("0", "value", [("eq", claim)])))["s1"]


def test_a_sampled_consequence_is_not_verified():
    """x >= 6 does not follow from x + y = 10 and x >= y (x = y = 5), but no sampled point of the
    line fell in y in (4, 5] and it was "verified" (28 Sep 2026). The only reader of "verified" is
    the L6 cross-check, which then overruled a critic that was right."""
    from mathverify.critic.critique import _deterministic_cross_check
    ir = {"task": {"kind": "evaluate", "params": {"expr": "sqrt(x - y)"}},
          "vars": [{"name": "x"}, {"name": "y"}], "givens": ["x + y = 10"]}
    r = verify(ir, _sol("0", "value", [("eq", "x >= 6")]))
    assert _steps(r)["s1"][0] != "verified"
    layer = next(l for l in r.layers if l.layer == "steps.refute")
    xc = _deterministic_cross_check(ir, {}, {"first_bad_step": "s1"}, layer.evidence)
    assert xc["flagged_step_status"] != "verified"


def test_a_wrong_choice_of_roots_is_refuted_on_the_premise_set():
    """ayt-trig-010's own wrong step: `x in {pi/6, 5*pi/6}` for cos 2x = 1/2 on [0, 2*pi). An Or never
    reached the premise-set route, and `solve`'s principal roots made it "verified"."""
    it = json.loads((ROOT / "evalset" / "items" / "ayt-trig-010.json").read_text(encoding="utf-8"))
    r = verify(it["problem_ir"], it["solution"])
    layer = next(l for l in r.layers if l.layer == "steps.refute")
    s2 = next(e for e in layer.evidence["steps"] if e["id"] == "s2")
    assert s2["status"] == "refuted" and s2["evidence"]["route"] == "premise_set", s2
    assert sp.sympify(s2["evidence"]["counterexample"]["x"]) in (7 * sp.pi / 6, 11 * sp.pi / 6)
    assert r.verdict == "INCORRECT"


@pytest.mark.parametrize("claim,expected", [("0 <= x < pi", "refuted"), ("x in {pi/6, 7*pi/6}", "refuted")])
def test_a_chain_or_a_choice_that_fails_on_part_of_the_premise_set_is_refuted(claim, expected):
    """A chain is the intersection of its parts, a choice their union."""
    st = _steps(verify(_ir("ayt-trig-010"), _sol("{pi/6}", "set", [("eq", claim)])))["s1"]
    assert st[0] == expected, st


def test_the_principal_roots_of_a_transcendental_equation_prove_nothing():
    """solve(sin x = 0) gives 0 and pi; cos(x/2) >= 0 holds at both and fails at 2*pi."""
    ir = {"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": [{"name": "x"}, {"name": "y"}],
          "givens": ["sin(x) = 0", "y = 1"]}
    assert _one(ir, "cos(x/2) >= 0") == ("unknown", "no_counterexample_at_sampled_points")


@pytest.mark.parametrize("claim", ["x in {pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "0 <= x < 2*pi"])
def test_a_right_and_or_claim_is_proved_on_the_premise_set(claim):
    ir = _ir("ayt-trig-010")
    st = _steps(verify(ir, _sol("{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "set", [("eq", claim)])))["s1"]
    assert st[0] == "verified", st


def test_a_single_root_is_proved_on_the_premise_set():
    r = verify(_ir("ayt-trig-004"), _sol("{pi/3}", "set", TRIG + [("eq", "x = pi/3")], option="B"))
    layer = next(l for l in r.layers if l.layer == "steps.refute")
    s6 = next(e for e in layer.evidence["steps"] if e["id"] == "s6")
    assert s6["status"] == "verified" and s6["evidence"]["route"] == "premise_set"


def test_inconsistent_premises_prove_nothing():
    ir = {"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": [{"name": "x"}],
          "givens": ["x > 2", "x < 1"]}
    assert _one(ir, "x > 5")[0] != "verified"


def test_a_polynomial_system_with_finitely_many_solutions_is_exhaustive():
    ir = {"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": [{"name": "x"}, {"name": "y"}],
          "givens": ["x + y = 5", "x*y = 6"]}
    assert _one(ir, "x**2 + y**2 = 13")[0] == "verified"
    assert _one(ir, "x**2 + y**2 = 14")[0] == "refuted"


def test_decide_reads_and_and_or():
    from mathverify.certify.base import make_ctx
    from mathverify.intake.structured import load_problem_ir
    from mathverify.steps.deterministic import _decide
    ctx = make_ctx(load_problem_ir({"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": [{"name": "x"}]}))
    x = ctx.ns["x"]
    pt = {x: sp.Integer(2)}
    assert _decide(sp.Or(sp.Eq(x, 1), sp.Eq(x, 2)), pt, ctx) is True
    assert _decide(sp.Or(sp.Eq(x, 1), sp.Eq(x, 3)), pt, ctx) is False
    assert _decide(sp.And(sp.Gt(x, 1), sp.Lt(x, 3)), pt, ctx) is True
    assert _decide(sp.And(sp.Gt(x, 1), sp.Lt(x, 2)), pt, ctx) is False
