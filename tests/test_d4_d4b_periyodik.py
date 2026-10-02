"""Periodic conditions and solver completeness (fourth audit, part d4b, 1 Oct 2026).

SymPy 1.14 solves an inequality or a `!=` with a trigonometric function on ONE period ([0, P)) and returns
that as the answer, also on a bounded domain (measured: solveset(sin(x) > 0, x, Reals) = (0, pi), the same on
Interval(-10, 10); Ne(cos(x), 0) gave [0, 2*pi) minus two points; Ne(x*cos(x), 0) gave (-oo, 0) ∪ (0, oo)),
and its equation sets lose roots (sqrt(3)*sin(x) - cos(x) = 1: 2*n*pi + pi/3 only, x = pi lost). Every caller
took those sets for the answer: the domain of log(sin x) was certified (0, pi), {} the solutions of x**2 = 49
with sin x > 0, 3 the integers of [0, 10] with sin x > 0, and the right {pi/4, 5*pi/4, 9*pi/4} of tan x = 1
on [0, 10) was refuted (G2); the step layer read x on one period of tan's domain and verified Abs(x) = x
(D4-ADIM-G). `evaluate` trusted `solve`'s principal roots (G5: -1 for cos x with sin x = 0, 3 < x < 7).
`trig_solve` read no condition on the variable but its interval (G3), nor an equation defined nowhere as
written (TAN-08), and count_solutions ignored a condition defined nowhere.

Now: `sandbox.exactsets.exact_solveset` (behind `ops.solveset_in` and every direct call), `Ctx.domain_for`
solving trigonometric conditions last on what the others leave (`unsolved_conditions`, `cut_by`),
`algebra._complete_solutions`, `trig._region`, and the abstentions `condition_unsolved` / `given_not_applied`.

The tests marked "158c220" fail on the code before the fix (measured: see the commit message).
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
x = sp.Symbol("x", real=True)
S = sp.S


def V(name="x", dom="real", cons=None):
    v = {"name": name, "domain": dom}
    if cons:
        v["constraints"] = list(cons)
    return v


def _ir(kind, params, vars_=(X,), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def _run(ir, payload, kind="set", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""} for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _eq(e, givens=(), vars_=(X,), dod=None):
    return _ir("solve_equation", {"equation": e, "var": "x"}, vars_, givens, "set", dod)


def _trig(givens, interval=None, vars_=(X,), dod=None, equation=None):
    p = {"var": "x"}
    if interval:
        p["interval"] = interval
    if equation:
        p["equation"] = equation
    return _ir("trig_solve", p, vars_, givens, "set", dod)


def _ev(expr, givens, vars_=(X,)):
    return _ir("evaluate", {"expr": expr}, vars_, givens, "scalar")


# ------------------------------------------------------------------------------------------------
# sandbox.exactsets: the guarded solveset
# ------------------------------------------------------------------------------------------------
def test_an_inequality_on_the_reals_is_not_one_period():
    """158c220: (0, pi)."""
    from mathverify.sandbox.ops import solveset_in
    s_ = solveset_in(sp.sin(x) > 0, x, S.Reals)
    assert isinstance(s_, sp.ConditionSet)
    assert s_.contains(7) is sp.true and s_.contains(-7) is sp.false


def test_a_bounded_domain_is_rebuilt_on_every_period():
    """158c220: (0, pi) on [-10, 10]; [0, 2*pi) minus two points; (pi/4, pi/2)."""
    from mathverify.sandbox.exactsets import exact_solveset
    pi = sp.pi
    assert exact_solveset(sp.sin(x) > 0, x, sp.Interval(-10, 10)) == sp.Union(
        sp.Interval.Ropen(-10, -3 * pi), sp.Interval.open(-2 * pi, -pi), sp.Interval.open(0, pi),
        sp.Interval.open(2 * pi, 3 * pi))
    nc = exact_solveset(sp.Ne(sp.cos(x), 0), x, sp.Interval(-10, 10))
    assert all(nc.contains(p) is sp.false for p in (-5 * pi / 2, -pi / 2, 5 * pi / 2))
    assert nc.contains(-3) is sp.true and nc.contains(9) is sp.true
    t = exact_solveset(sp.tan(x) > 1, x, sp.Interval(0, 10))
    assert t.contains(9 * pi / 4 + sp.Rational(1, 10)) is sp.true and t.contains(5 * pi / 2) is sp.false
    assert exact_solveset(sp.cos(x) >= 0, x, sp.Interval(5, 8)) == sp.Interval(5, 5 * pi / 2)
    assert set(exact_solveset(sp.sin(x) > 0, x, sp.Range(0, 11))) == {1, 2, 3, 7, 8, 9}


def test_a_progression_dropped_by_the_inequality_solver():
    """158c220: Ne(x*cos(x), 0) was (-oo, 0) ∪ (0, oo), pi/2 inside."""
    from mathverify.sandbox.exactsets import exact_solveset
    s_ = exact_solveset(sp.Ne(x * sp.cos(x), 0), x, S.Reals)
    assert s_.contains(sp.pi / 2) is not sp.true
    b = exact_solveset(sp.Ne(x * sp.cos(x), 0), x, sp.Interval(-5, 5))
    assert b.contains(sp.pi / 2) is sp.false and b.contains(0) is sp.false and b.contains(1) is sp.true


def test_a_root_solveset_loses_makes_the_set_unsolved():
    """sqrt(3) sin x - cos x = 1 has x = pi too; SymPy gives {pi/3} on [0, 2*pi] (158c220: {pi/3})."""
    from mathverify.sandbox.exactsets import exact_solveset
    for dom in (sp.Interval(0, 2 * sp.pi), S.Reals):
        s_ = exact_solveset(sp.Eq(sp.sqrt(3) * sp.sin(x) - sp.cos(x), 1), x, dom)
        assert isinstance(s_, sp.ConditionSet), s_


def test_equations_keep_their_exact_sets():
    from mathverify.sandbox.exactsets import exact_solveset
    assert exact_solveset(sp.Eq(sp.tan(x), 1), x, sp.Interval.Ropen(0, 10)) == sp.FiniteSet(
        sp.pi / 4, 5 * sp.pi / 4, 9 * sp.pi / 4)
    z = exact_solveset(sp.Eq(sp.sin(x), 0), x, S.Reals)
    assert z.contains(2 * sp.pi) is sp.true and z.contains(1) is not sp.true
    assert exact_solveset(sp.sin(x) > 2, x, S.Reals) is S.EmptySet
    assert exact_solveset(sp.Ne(sp.cos(x) + 2, 0), x, S.Reals) == S.Reals
    # not periodic, finitely many zeros and poles: SymPy's own set
    assert exact_solveset(sp.Ne(sp.sin(sp.acot(x) + sp.acot(2)), 0), x, S.Reals) == sp.Complement(S.Reals, {-2})
    # point by point, a pole is no point
    assert exact_solveset(sp.Ne(sp.tan(x), 1), x, sp.FiniteSet(0, sp.pi / 4, sp.pi / 2)) == sp.FiniteSet(0)
    assert exact_solveset(sp.sin(x) > 0, x, sp.FiniteSet(7)) == sp.FiniteSet(7)
    assert exact_solveset(sp.Ne(sp.tan(x), 1), x, sp.FiniteSet(sp.pi / 2)) is S.EmptySet


def test_a_set_of_points_repeating_with_a_period():
    from mathverify.sandbox.exactsets import exact_solveset, set_is_empty
    n = sp.Dummy("n", integer=True)
    prog = sp.ImageSet(sp.Lambda(n, n * sp.pi + sp.pi / 3), S.Integers)
    dom = sp.Intersection(sp.ConditionSet(x, sp.Ne(sp.cos(x), 0), S.Reals), prog)
    assert exact_solveset(sp.Ne(sp.tan(x), sp.sqrt(3)), x, dom) is S.EmptySet
    zc = exact_solveset(sp.Eq(sp.cos(x), 0), x, S.Reals)
    zs = exact_solveset(sp.Eq(sp.sin(x), 0), x, S.Reals)
    assert set_is_empty(sp.Complement(zc, exact_solveset(sp.Eq(sp.cos(2 * x), -1), x, S.Reals))) is True
    assert set_is_empty(sp.Complement(zs, zc)) is False


def test_a_period_and_the_zeros_are_confirmed(monkeypatch):
    """What SymPy returns is checked: a wrong period (pi for sin x) and a point that is no zero are not
    used (the guard against a wrong `periodicity` or `solveset`, simulated here)."""
    import sympy.calculus.util as su
    from mathverify.sandbox import exactsets
    assert exactsets.period(sp.tan(x) - 1, x) == sp.pi
    monkeypatch.setattr(su, "periodicity", lambda e, v: sp.pi)
    assert exactsets.period(sp.sin(x), x) is None
    monkeypatch.undo()
    real = sp.solveset
    monkeypatch.setattr(sp, "solveset", lambda r, v, d: sp.FiniteSet(sp.pi, 1) if r == sp.Eq(sp.sin(x), 0) else real(r, v, d))
    assert exactsets._zeros_on(sp.sin(x), x, sp.Rational(1, 2), 4) is None


def test_continuous_domain_of_a_trigonometric_expression():
    """158c220: log(x*cos(x)) on [2, 3] (undefined everywhere there) was continuous on all of it."""
    from mathverify.sandbox.ops import continuous_domain
    with pytest.raises(ValueError):
        continuous_domain(sp.log(x * sp.cos(x)), x, sp.Interval(2, 3))
    assert continuous_domain(sp.tan(x), x, sp.Interval(4, 5)).contains(3 * sp.pi / 2) is sp.false
    assert continuous_domain(sp.sin(x), x, sp.Interval(0, sp.pi)) == sp.Interval(0, sp.pi)


def test_the_exact_check_probes_every_piece_more_than_once():
    """A set cut to one period passed the old one-point probe of each piece (158c220: False)."""
    from mathverify.certify.domain import _solveset_contradicted
    assert _solveset_contradicted(sp.sin(x) > 0, x, sp.Interval.open(0, sp.pi)) is True
    assert _solveset_contradicted(x > 1, x, sp.Interval.open(1, sp.oo)) is False


def test_written_undefined_on_an_interval_past_the_first_period():
    """sin x < 0 on all of [10, 12]: sqrt(sin x) is undefined there (158c220: False)."""
    from mathverify.certify.base import make_ctx
    from mathverify.certify.domain import written_undefined_in
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(_ir("extremum", {"f": "sqrt(sin(x)) + x", "var": "x", "which": "max"})))
    assert written_undefined_in("sqrt(sin(x)) + x", ctx.ns, ctx.sym("x"), sp.Interval(10, 12)) is True
    assert written_undefined_in("sqrt(sin(x)) + x", ctx.ns, ctx.sym("x"), sp.Interval(7, 8)) is False


def test_lean_regions_and_violations_of_a_periodic_condition():
    """The Lean statement read sin(x) >= 0 on [10, 12] as violated nowhere, and the region of sin(x) > 0
    as (0, pi) (158c220)."""
    from mathverify.formal.statement import LeanPrintError, _solve_region, _violation_set
    v = _violation_set(sp.sin(x) >= 0, x, sp.Interval(10, 12))
    assert v is not None and v != S.EmptySet
    with pytest.raises(LeanPrintError):
        _solve_region([sp.sin(x) > 0], x)


def test_series_index_conditions_past_the_first_period():
    """sin(k) < 0 at k = 10: the indices from 7 are not all good (158c220: False, none bad)."""
    from mathverify.certify.series import _bad_indices
    k = sp.Symbol("k", integer=True)
    assert _bad_indices([sp.sin(k) >= 0], 7) is not False


def test_membership_in_an_unsolved_condition():
    from mathverify.certify.domain import _in_set_certified
    cs = sp.ConditionSet(x, sp.sin(x) > 0, S.Reals)
    assert _in_set_certified(cs, sp.Integer(7)) is True
    assert _in_set_certified(cs, sp.Integer(-7)) is False
    assert _in_set_certified(sp.ConditionSet(x, sp.sin(x) > 0, sp.Interval(0, 5)), sp.Integer(7)) is False


# ------------------------------------------------------------------------------------------------
# G2 / D4-ADIM-G through the verifier
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("expr,claim", [
    ("log(sin(x))", "Interval.open(0, pi)"),
    ("sqrt(sin(x))", "Interval(0, pi)"),
    ("tan(x)", "Union(Interval.Ropen(0, pi/2), Interval.open(pi/2, 3*pi/2), Interval.open(3*pi/2, 2*pi))"),
])
def test_domain_of_one_period_is_not_certified(expr, claim):
    """158c220: CORRECT."""
    r = _run(_ir("domain_of", {"expr": expr, "var": "x"}, shape="set"), claim, "interval")
    assert r.verdict != "CORRECT"


def test_a_constraint_with_a_period_cuts_the_domain_point_by_point():
    """158c220: {} CORRECT, {7} INCORRECT (sin 7 > 0)."""
    ir = _eq("x**2 = 49", vars_=[V("x", "real", ["sin(x) > 0"])])
    assert _run(ir, "{7}").verdict == "CORRECT"
    assert _run(ir, "{}").verdict == "INCORRECT"
    ir = _ir("count_roots", {"expr": "x**2 - 49", "var": "x"}, [V("x", "real", ["sin(x) > 0"])], (), "count")
    assert _run(ir, "1", "count").verdict == "CORRECT"


def test_an_equation_given_with_a_periodic_given():
    """The givens solved as a system (no equation in params). 158c220: {7} INCORRECT."""
    ir = _ir("solve_equation", {"var": "x"}, [X], ["x**2 = 49", "sin(x) > 0"], "set")
    assert _run(ir, "{7}").verdict == "CORRECT"
    assert _run(ir, "{-7, 7}").verdict == "INCORRECT"


def test_a_side_condition_with_a_period_is_not_applied():
    """Next to the task's own relation, sin(x) > 0 is solved on what the rest leaves; on ℝ it stays
    unsolved and the verifier abstains (given_not_applied). 158c220: {} CORRECT."""
    r = _run(_eq("x**2 = 49", ["sin(x) > 0"]), "{}")
    assert r.verdict == "UNKNOWN" and "given_not_applied" in r.flags
    ir = _eq("x**2 = 49", ["sin(x) > 0", "x > 0", "x < 10"])
    assert _run(ir, "{7}").verdict == "CORRECT"


def test_a_domain_of_discourse_with_a_period():
    """158c220: {} CORRECT."""
    assert _run(_eq("x**2 = 49", dod="sin(x) > 0"), "{}").verdict != "CORRECT"


def test_written_conditions_of_tan_and_log_sin():
    """158c220: {2} CORRECT, {-2, 2} INCORRECT; {} CORRECT, {7} INCORRECT."""
    assert _run(_eq("x**2 + tan(x) - tan(x) = 4"), "{-2, 2}").verdict == "CORRECT"
    assert _run(_eq("x**2 + tan(x) - tan(x) = 4"), "{2}").verdict == "INCORRECT"
    assert _run(_eq("x + log(sin(x)) - log(sin(x)) = 7"), "{7}").verdict == "CORRECT"


def test_tan_on_a_bounded_window_is_not_refuted():
    """The right answer was INCORRECT (9*pi/4 outside one period of tan's domain) on 158c220."""
    ir = _eq("tan(x) = 1", ["x >= 0", "x < 10"])
    assert _run(ir, "{pi/4, 5*pi/4, 9*pi/4}").verdict == "CORRECT"
    assert _run(ir, "{pi/4, 5*pi/4}").verdict == "INCORRECT"


def test_count_integers_with_a_periodic_given():
    """158c220: 3 CORRECT, 6 INCORRECT."""
    ir = _ir("count_integers", {"var": "x"}, [X], ["x >= 0", "x <= 10", "sin(x) > 0"], "count")
    assert _run(ir, "6", "count").verdict == "CORRECT"
    assert _run(ir, "3", "count").verdict == "INCORRECT"


def test_solve_inequality_system_with_a_periodic_given():
    """158c220: (0, pi) CORRECT for x**2 < 100 with sin x > 0."""
    ir = _ir("solve_inequality", {"var": "x"}, [X], ["x**2 < 64", "sin(x) > 0"], "interval")
    right = "Union(Interval.open(-2*pi, -pi), Interval.open(0, pi), Interval.open(2*pi, 8))"
    assert _run(ir, right, "interval").verdict == "CORRECT"
    assert _run(ir, "Interval.open(0, pi)", "interval").verdict == "INCORRECT"


def test_an_inequality_under_an_unsolved_domain_abstains():
    r = _run(_ir("solve_inequality", {"inequality": "x**2 + tan(x) - tan(x) < 4", "var": "x"}, shape="set"),
             "Union(Interval.open(-2, -pi/2), Interval.open(-pi/2, pi/2), Interval.open(pi/2, 2))", "interval")
    assert r.verdict == "UNKNOWN" and "condition_unsolved" in r.flags


def test_extremum_under_periodic_conditions():
    """158c220: the right max 0 under sin x >= 0 on [0, 10] INCORRECT; sin(7) as the max of sin on [7, 8]."""
    ir = _ir("extremum", {"f": "-(x - 7)**2", "var": "x", "which": "max", "interval": "[0, 10]"},
             [V("x", "real", ["sin(x) >= 0"])])
    assert _run(ir, "0", "value").verdict != "INCORRECT"
    ir = _ir("extremum", {"f": "-(x - 1)**2", "var": "x", "which": "max", "interval": "[0, 3]"},
             [V("x", "real", ["sin(x) >= 0"])])
    assert _run(ir, "0", "value").verdict == "CORRECT"
    ir = _ir("extremum", {"f": "sin(x)", "var": "x", "which": "max", "interval": "[7, 8]"})
    assert _run(ir, "sin(7)", "value").verdict == "INCORRECT"
    r = _run(_ir("extremum", {"f": "-(x - 7)**2", "var": "x", "which": "max"}, givens=["sin(x) > 0"]), "0", "value")
    assert r.verdict == "UNKNOWN"


def test_the_step_layer_reads_the_whole_domain_of_tan():
    """D4-ADIM-G, 158c220: Abs(x) = x verified, the solution CORRECT."""
    r = _run(_ir("simplify_expression", {"expr": "tan(x)*cos(x)"}, shape="expression"), "sin(x)", "expression",
             [("compute", "Abs(x) = x")])
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    assert layer.evidence["steps"][-1]["status"] == "refuted" and r.verdict == "INCORRECT"


def test_steps_on_tan_with_its_window_stay_verified():
    """The written cos(x) != 0 of tan x = sqrt(3) is solved on the window the premises leave."""
    ir = _trig(["tan(x) = sqrt(3)"], "[0, pi)")
    r = _run(ir, "{pi/3}", "set", [("eq", "tan(x) = sqrt(3)"), ("assert", "0 <= x"), ("assert", "x < pi"),
                                   ("eq", "x = pi/3")])
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    st = {s["id"]: s["status"] for s in layer.evidence["steps"]}
    assert st["s1"] == "verified" and r.verdict == "CORRECT"


# ------------------------------------------------------------------------------------------------
# G5: evaluate under given equations
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("expr,givens,claim", [
    ("cos(x)", ["sin(x) = 0", "x > 3", "x < 7"], "-1"),       # x = pi or 2*pi
    ("x", ["tan(x) = 1", "x > 0", "x < 4"], "pi/4"),           # 5*pi/4 < 4 too
    ("x", ["cos(x) = 1", "x > 1", "x < 13"], "2*pi"),          # 4*pi too
    ("sin(x)", ["tan(x) = 1"], "sqrt(2)/2"),                   # -sqrt(2)/2 too
])
def test_evaluate_needs_a_complete_solution_set(expr, givens, claim):
    """158c220: CORRECT (solve's principal roots)."""
    assert _run(_ev(expr, givens), claim, "value").verdict == "UNKNOWN"


def test_evaluate_with_a_proved_complete_set():
    assert _run(_ev("x", ["sin(x) = 0", "x > 4", "x < 7"]), "2*pi", "value").verdict == "CORRECT"
    assert _run(_ev("x", ["sin(x) = 1/2", "x > 6", "x < 7"]), "13*pi/6", "value").verdict == "CORRECT"
    assert _run(_ev("x", ["x + y = 5", "x - y = 1"], [X, V("y")]), "3", "value").verdict == "CORRECT"
    assert _run(_ev("x", ["exp(x) = 2"]), "log(2)", "value").verdict == "CORRECT"


# ------------------------------------------------------------------------------------------------
# G3 / TAN-08: trig_solve reads every condition on the variable
# ------------------------------------------------------------------------------------------------
ALL4 = "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}"


@pytest.mark.parametrize("ir", [
    _trig(["cos(2*x) = 1/2", "x > pi"], "[0, 2*pi)"),
    _trig(["cos(2*x) = 1/2"], "[0, 2*pi)", [V("x", "real", ["x > pi"])]),
    _trig(["cos(2*x) = 1/2"], "[0, 2*pi)", dod="x > pi"),
    _trig(["cos(2*x) = 1/2", "x > b", "b = pi"], "[0, 2*pi)", [X, V("b")]),
])
def test_trig_solve_applies_the_other_conditions(ir):
    """158c220: all four roots CORRECT, the right two INCORRECT."""
    assert _run(ir, ALL4).verdict == "INCORRECT"
    assert _run(ir, "{7*pi/6, 11*pi/6}").verdict == "CORRECT"


def test_trig_solve_with_a_free_bound_or_a_general_solution_on_a_restricted_variable():
    """158c220: CORRECT."""
    r = _run(_trig(["cos(2*x) = 1/2", "x > b"], "[0, 2*pi)", [X, V("b")]), ALL4)
    assert r.verdict == "UNKNOWN" and "condition_not_applied" in r.flags
    for ir in (_trig(["sin(x) = 0"], None, [V("x", "positive_real")]),
               _trig(["sin(x) = 0"], None, [V("x", "real", ["0 < x < 4"])]),
               _trig(["sin(x) = 0"], None, [V("x", "integer")])):
        assert _run(ir, "{n*pi}").verdict != "CORRECT"
    assert _run(_trig(["sin(x) = 0"], None, [V("x", "real", ["0 < x < 4"])]), "{pi}").verdict == "CORRECT"


def test_trig_solve_with_a_second_equation():
    """158c220: {n*pi} CORRECT, {2*n*pi} INCORRECT for sin x = 0 with cos x = 1."""
    ir = _trig(["sin(x) = 0", "cos(x) = 1"])
    assert _run(ir, "{2*n*pi}").verdict == "CORRECT"
    assert _run(ir, "{n*pi}").verdict == "INCORRECT"
    ir = _trig(["x != 0"], "[0, 2*pi]", equation="sin(x) = 0")
    assert _run(ir, "{0, pi, 2*pi}").verdict == "INCORRECT"
    assert _run(ir, "{pi, 2*pi}").verdict == "CORRECT"
    ir = _trig(["cos(2*x) = 1/2", "sin(x) > 0"], "[0, 2*pi)")
    assert _run(ir, "{pi/6, 5*pi/6}").verdict == "CORRECT"


G = "sin(x) + log(-1 - x**2) - log(-1 - x**2) = 0"


@pytest.mark.parametrize("ir,claim", [
    (_trig([G], "[0, 2*pi)"), "{0, pi}"),
    (_trig([G]), "{n*pi}"),
    (_trig([], "[0, 2*pi)", equation=G), "{0, pi}"),
])
def test_trig_solve_of_an_equation_defined_nowhere(ir, claim):
    """TAN-08, 158c220: CORRECT."""
    assert _run(ir, claim).verdict == "INCORRECT"
    assert _run(ir, "{}").verdict == "CORRECT"


def test_count_solutions_with_a_condition_defined_nowhere():
    """TAN-08: sqrt(-x) with x a positive integer. 158c220: 3 CORRECT."""
    ir = _ir("count_solutions", {"bounds": {"x": ["1", "3"], "y": ["1", "3"]}},
             [V("x", "positive_integer"), V("y", "positive_integer")], ["x + y + sqrt(-x) - sqrt(-x) = 4"], "count")
    assert _run(ir, "3", "count").verdict == "INCORRECT"
    assert _run(ir, "0", "count").verdict == "CORRECT"


def test_trig_solve_controls():
    assert _run(_trig(["cos(2*x) = 1/2"], "[0, 2*pi)"), ALL4).verdict == "CORRECT"
    assert _run(_trig(["tan(x) = 1"]), "{pi/4 + n*pi}").verdict == "CORRECT"
    assert _run(_trig(["tan(x) = 1"]), "{pi/4 + 2*n*pi}").verdict == "INCORRECT"


def test_steps_under_a_periodic_premise_on_a_bounded_window():
    """0 < x < 10 with sin x > 0 is (0, pi) ∪ (2*pi, 3*pi): x < 3*pi holds on all of it, x < 4 does not."""
    ir = _ir("evaluate", {"expr": "x**2"}, [X], ["x > 0", "x < 10", "sin(x) > 0"])
    for claim, status in (("x < 3*pi", "verified"), ("x < 4", "refuted")):
        r = _run(ir, "1", "value", [("eq", claim)])
        layer = next(la for la in r.layers if la.layer == "steps.refute")
        assert layer.evidence["steps"][-1]["status"] == status, claim


def test_domain_of_under_a_periodic_condition_solved_on_a_bounded_domain():
    """The domain of discourse sin(x) > 0 is solved on what the constraints leave; on ℝ it is unsolved and
    the certificate abstains (condition_unsolved)."""
    ir = _ir("domain_of", {"expr": "x", "var": "x"}, [V("x", "real", ["x > 0", "x < 10"])], (), "set",
             dod="sin(x) > 0")
    assert _run(ir, "Union(Interval.open(0, pi), Interval.open(2*pi, 3*pi))", "interval").verdict == "CORRECT"
    ir = _ir("domain_of", {"expr": "log(sin(x))", "var": "x"}, [V("x", "real", ["x > 0", "x < 10"])], (), "set")
    assert _run(ir, "Union(Interval.open(0, pi), Interval.open(2*pi, 3*pi))", "interval").verdict == "CORRECT"
    r = _run(_ir("domain_of", {"expr": "x", "var": "x"}, [V("x", "real", ["sin(x) > 0"])], (), "set"),
             "Interval.open(0, pi)", "interval")
    assert r.verdict == "UNKNOWN" and "condition_unsolved" in r.flags


def test_limit_side_of_a_periodic_condition_is_not_solved():
    """sqrt(sin x) is not real on a whole neighbourhood of oo: one period read it as defined there."""
    from mathverify.certify.limits import _side_status
    assert _side_status([sp.sin(x) >= 0], x, sp.oo, None) is None
