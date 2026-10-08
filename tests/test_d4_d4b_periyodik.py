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


def test_a_root_solveset_loses_is_found_by_the_combination_class():
    """sqrt(3) sin x - cos x = 1 has x = pi too; SymPy gives {pi/3} on [0, 2*pi] (158c220: {pi/3}).
    Class (v): 2 sin(x - pi/6) = 1, both progressions (round 4)."""
    from mathverify.sandbox.exactsets import exact_solveset
    s_ = exact_solveset(sp.Eq(sp.sqrt(3) * sp.sin(x) - sp.cos(x), 1), x, sp.Interval(0, 2 * sp.pi))
    assert s_ == sp.FiniteSet(sp.pi / 3, sp.pi), s_
    r = exact_solveset(sp.Eq(sp.sqrt(3) * sp.sin(x) - sp.cos(x), 1), x, S.Reals)
    assert r.contains(sp.pi) is sp.true and r.contains(sp.pi / 3 + 2 * sp.pi) is sp.true
    assert r.contains(-sp.pi) is sp.true and r.contains(0) is not sp.true


def test_equations_keep_their_exact_sets():
    from mathverify.sandbox.exactsets import exact_solveset
    assert exact_solveset(sp.Eq(sp.tan(x), 1), x, sp.Interval.Ropen(0, 10)) == sp.FiniteSet(
        sp.pi / 4, 5 * sp.pi / 4, 9 * sp.pi / 4)
    z = exact_solveset(sp.Eq(sp.sin(x), 0), x, S.Reals)
    assert z.contains(2 * sp.pi) is sp.true and z.contains(1) is not sp.true
    assert exact_solveset(sp.sin(x) > 2, x, S.Reals) is S.EmptySet
    assert exact_solveset(sp.Ne(sp.cos(x) + 2, 0), x, S.Reals) == S.Reals
    # not one of the exact classes (the argument is not linear): unsolved, SymPy's own set is no proof
    assert isinstance(exact_solveset(sp.Ne(sp.sin(sp.acot(x) + sp.acot(2)), 0), x, S.Reals), sp.ConditionSet)
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


Q = sp.sqrt(3) * sp.sin(x) - sp.cos(x) - 1            # its zeros on [0, 7]: pi/3 and pi


def test_only_the_exact_classes_give_a_set():
    """A set is exact only when its zeros and poles are known in closed form (a polynomial, a polynomial
    in one trigonometric function or in a same-frequency sin/cos combination or in one strictly monotone
    function, of a linear argument; products and quotients of these). SymPy's set of Q = 0 misses pi, of
    x*Q = 0 too, and a numeric root search misses the triple root of Q**3 (review of 2 Oct 2026, B1, B2:
    {0, pi/3} and {pi/3} were CORRECT on 0ed77e2; on 3872bcd they were unsolved, now class (v), with pi)."""
    from mathverify.sandbox.exactsets import exact_solveset, period
    W = sp.Interval(0, 7)
    both = sp.FiniteSet(sp.pi / 3, sp.pi)
    for e in ((x + 1) * Q, sp.exp(x) * Q, Q ** 3, Q / x):
        assert exact_solveset(sp.Eq(e, 0), x, W) == both, e
    assert exact_solveset(sp.Eq(x * Q, 0), x, W) == sp.FiniteSet(0, sp.pi / 3, sp.pi)
    r2 = sp.sqrt(2) * sp.pi / 2
    assert exact_solveset(sp.Eq(Q * sp.sin(sp.sqrt(2) * x), 0), x, W) == sp.FiniteSet(
        0, sp.pi / 3, sp.pi, r2, 2 * r2, 3 * r2)
    assert exact_solveset(Q ** 3 > 0, x, W) == sp.Interval.open(sp.pi / 3, sp.pi)
    # not a class: a sum of a polynomial and a trigonometric function, two frequencies, sin*cos, exp and
    # a polynomial, a root
    for e in (sp.sin(x) + x, sp.sin(x) + sp.cos(2 * x), sp.sin(x) * sp.cos(x) - sp.Rational(1, 4),
              sp.exp(x) - 3 * x, sp.sqrt(x) - 1 + sp.sin(x)):
        assert isinstance(exact_solveset(sp.Eq(e, 0), x, W), sp.ConditionSet), e
    # the classes
    assert exact_solveset(sp.Eq(x * sp.sin(x), 0), x, W) == sp.FiniteSet(0, sp.pi, 2 * sp.pi)
    assert exact_solveset(sp.Eq((x - 1) ** 3 * sp.cos(x) ** 3, 0), x, W) == sp.FiniteSet(
        1, sp.pi / 2, 3 * sp.pi / 2)
    assert exact_solveset(sp.sin(x) ** 3 > 0, x, W) == sp.Union(sp.Interval.open(0, sp.pi), sp.Interval.Lopen(2 * sp.pi, 7))
    assert exact_solveset(sp.Eq(4 * sp.sin(x) ** 2, 1), x, sp.Interval.Ropen(0, 2 * sp.pi)) == sp.FiniteSet(
        sp.pi / 6, 5 * sp.pi / 6, 7 * sp.pi / 6, 11 * sp.pi / 6)
    assert period(sp.tan(x) - 1, x) == sp.pi and period(Q, x) == 2 * sp.pi and period(x * sp.sin(x), x) is None
    # no real solution of sin(x) = +-2; the zeros of a denominator and the poles of tan are no zeros
    assert exact_solveset(sp.Eq(sp.sin(x) ** 2, 4), x, W) is S.EmptySet
    assert exact_solveset(sp.Eq(sp.sin(x) / (x - sp.pi), 0), x, W) == sp.FiniteSet(0, 2 * sp.pi)
    tc = exact_solveset(sp.Eq(sp.tan(x) * sp.cos(x), 0), x, S.Reals)
    assert tc.contains(sp.pi) is sp.true and tc.contains(sp.pi / 2) is not sp.true


def test_the_work_of_one_call_is_bounded():
    """sin(1000x) > 0 on [0, 30] (9549 zeros) took over 20 minutes in one call (B6): now unsolved."""
    import time
    from mathverify.sandbox.exactsets import exact_solveset
    t0 = time.time()
    assert isinstance(exact_solveset(sp.sin(1000 * x) > 0, x, sp.Interval(0, 30)), sp.ConditionSet)
    assert isinstance(exact_solveset(sp.Eq(sp.sin(100000 * x), 0), x, sp.Interval(0, 30)), sp.ConditionSet)
    assert isinstance(exact_solveset(Q ** 2 + sp.sin(x) ** 2 > 0, x, sp.Interval(0, 7)), sp.ConditionSet)
    assert time.time() - t0 < 30


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


def test_a_wrong_zero_of_a_non_periodic_condition_is_not_trusted():
    """SymPy reads cos(atan(x) + atan(2)) = 0 as x = -2 (the cosine is 1 there; the zero is 1/2, where
    acot(1/2) + acot(2) = pi/2 makes the tan undefined). Its set is not used, and membership in the
    unsolved condition is decided by certified comparisons (SymPy's own contains took 1/2 for inside).
    158c220: {1/2} CORRECT, {} INCORRECT."""
    ir = _eq("x + tan(acot(x) + acot(2)) - tan(acot(x) + acot(2)) = 1/2")
    assert _run(ir, "{1/2}").verdict == "INCORRECT"
    assert _run(ir, "{}").verdict == "CORRECT"


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
    # exp(x) = 2 is class (iv) (round 4; UNKNOWN on 3872bcd), a non-class equation is not
    assert _run(_ev("x", ["exp(x) = 2"]), "log(2)", "value").verdict == "CORRECT"
    assert _run(_ev("x", ["exp(x) = 2"]), "log(3)", "value").verdict == "INCORRECT"
    assert _run(_ev("x", ["exp(x) = 3*x", "x < 1"]), "LambertW(-1/3)*(-1)", "value").verdict == "UNKNOWN"


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


QS = "(sqrt(3)*sin(x) - cos(x) - 1)"


@pytest.mark.parametrize("e,claim", [
    (f"x*{QS} = 0", "{0, pi/3}"), (f"(x + 1)*{QS} = 0", "{pi/3}"), (f"exp(x)*{QS} = 0", "{pi/3}"),
    ("sqrt(3)*x*sin(x) - x*cos(x) = x", "{0, pi/3}"), (f"{QS}**3 = 0", "{pi/3}"), (f"{QS} = 0", "{pi/3}"),
])
def test_an_incomplete_set_of_a_non_class_equation_is_not_certified(e, claim):
    """Review of 2 Oct 2026, B1/B2 (0ed77e2: CORRECT for the first five; pi is a root too). 3872bcd left
    them UNKNOWN (no class); with class (v) (round 4) the missing pi is found: INCORRECT."""
    assert _run(_eq(e, ["x >= 0", "x <= 2*pi"]), claim).verdict == "INCORRECT"


def test_review_b3_b4_b5():
    """B3: x**2 = 4 with Q**3 > 0 on [0, 7] ({} was CORRECT, {2} INCORRECT; Q(2) > 0); trig_solve Q**3 = 0
    gave {pi/3}; B4: x with (x + 1)Q = 0, 0 < x < 4 gave pi/3; B5: the maximum 0 of -(x - pi)**2 +
    (x + 1)Q/((x + 1)Q) - 1 on [2, 4], undefined at pi."""
    ir = _eq("x**2 = 4", [f"{QS}**3 > 0", "x >= 0", "x <= 7"])
    assert _run(ir, "{}").verdict != "CORRECT" and _run(ir, "{2}").verdict != "INCORRECT"
    # a domain of discourse that opens with a bracket is a relation, not the set {relation}
    ir = _eq("x**2 = 4", ["x >= 0", "x <= 7"], dod=f"{QS}**3 > 0")
    assert _run(ir, "{}").verdict == "INCORRECT" and _run(ir, "{2}").verdict == "CORRECT"
    assert _run(_trig([f"{QS}**3 = 0"], "[0, 7]"), "{pi/3}").verdict != "CORRECT"
    assert _run(_ev("x", [f"(x + 1)*{QS} = 0", "x > 0", "x < 4"]), "pi/3", "value").verdict != "CORRECT"
    ir = _ir("extremum", {"f": f"-(x - pi)**2 + (x + 1)*{QS}/((x + 1)*{QS}) - 1", "var": "x", "which": "max",
                          "interval": "[2, 4]"})
    assert _run(ir, "0", "value").verdict != "CORRECT"


def test_a_fast_oscillating_side_condition_is_neither_slow_nor_a_rejection():
    """x**2 = 4 with sin(1000x) > 0 on [0, 30]: over 20 minutes on 0ed77e2; never INCORRECT (sin 2000 > 0)."""
    import time
    t0 = time.time()
    r = _run(_eq("x**2 = 4", ["sin(1000*x) > 0", "x >= 0", "x <= 30"]), "{2}")
    assert r.verdict != "INCORRECT" and time.time() - t0 < 60


# ------------------------------------------------------------------------------------------------
# Round 4: the classes (iv) one strictly monotone function, (v) a same-frequency sin/cos combination,
# (vi) their products; a rational system in several unknowns only with a proof of completeness
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rel,want", [
    (sp.Eq(sp.exp(x), 2), sp.FiniteSet(sp.log(2))),
    (sp.Eq(4 ** x - 3 * 2 ** x + 2, 0), sp.FiniteSet(0, 1)),
    (sp.Eq(2 ** (2 * x) - 3 * 2 ** x + 2, 0), sp.FiniteSet(0, 1)),
    (sp.Eq(sp.exp(x) + sp.exp(-x), 2), sp.FiniteSet(0)),
    (sp.Eq(sp.log(x) ** 2 - sp.log(x), 0), sp.FiniteSet(1, sp.E)),
    (sp.Eq(sp.log(x - 1), 0), sp.FiniteSet(2)),
    (sp.Eq(sp.atan(x), 1), sp.FiniteSet(sp.tan(1))),
    (sp.Eq(sp.atan(x), 2), S.EmptySet),                      # 2 > pi/2: out of the range of atan
    (sp.Eq(sp.exp(2 * x) - sp.exp(x) - 2, 0), sp.FiniteSet(sp.log(2))),   # the root -1 of t**2 - t - 2: exp > 0
    (sp.Eq(sp.sinh(x), 1), sp.FiniteSet(sp.asinh(1))),
    (sp.Eq((x - 1) * sp.exp(x), 0), sp.FiniteSet(1)),
    (sp.exp(x) > 2, sp.Interval.open(sp.log(2), sp.oo)),
    (sp.exp(2 * x) - 3 * sp.exp(x) + 2 < 0, sp.Interval.open(0, sp.log(2))),
    (sp.log(x) < 1, sp.Interval.open(0, sp.E)),             # log's domain x > 0: nothing at x <= 0
    (sp.log(x) ** 2 >= 0, sp.Interval.open(0, sp.oo)),
    (sp.log(x) > 0, sp.Interval.open(1, sp.oo)),
    # log(x)**2 is the real -pi**2 at x = -1 (not real at x = -2): a sign read at one point of x < 0 says
    # nothing; the log is cut off there by its argument (round 4, found by mutation K20)
    (sp.log(x) ** 2 <= 0, sp.FiniteSet(1)),
    (sp.Eq((x + 1) * sp.log(x), 0), sp.FiniteSet(1)),                 # x = -1: log(-1) is not real
    (sp.Eq(sp.sin(x) - sp.cos(x), 0), None),
])
def test_monotone_class_sets(rel, want):
    """SymPy's own sets of these were no proof (3872bcd: unsolved); each is a closed-form inverse."""
    from mathverify.sandbox.exactsets import class_solveset
    got = class_solveset(rel, x, S.Reals)
    if want is None:                                         # periodic: on a window
        got = class_solveset(rel, x, sp.Interval(0, 7))
        want = sp.FiniteSet(sp.pi / 4, 5 * sp.pi / 4)
    assert got == want, (rel, got)


def test_the_classes_reject_what_they_cannot_prove():
    """a**x with a = 1 or a < 0, x**x, two bases with an irrational log ratio, a non-linear argument,
    sin x cos x: no set."""
    from mathverify.sandbox.exactsets import class_solveset, _mono_parts, _combo_parts
    assert class_solveset(sp.Eq(3 ** x, x), x) is None                # (round 5: 3**x = 2**x is class (vii))
    assert class_solveset(sp.Eq(x ** x, 2), x) is None
    assert class_solveset(sp.Eq(sp.exp(x ** 2), 2), x) is None
    assert class_solveset(sp.Eq(sp.exp(x) - 3 * x, 0), x) is None
    assert _mono_parts(sp.Pow(-2, x, evaluate=False) - 4, x) is None
    assert _mono_parts(sp.Pow(1, x, evaluate=False) - 1, x) is None
    assert _combo_parts(sp.sin(x) * sp.cos(x) - sp.Rational(1, 4), x) is None
    assert _combo_parts(sp.sin(x) + sp.cos(2 * x), x) is None


def test_the_combination_reading_is_checked():
    """R sin(u + phi) + D must equal the expression: phi = atan2(B, A), not atan(B/A) (A < 0)."""
    from mathverify.sandbox.exactsets import _combo_parts
    f, a, b, g = _combo_parts(-sp.sin(x) - sp.cos(x), x)
    t = g.gens[0]
    back = g.as_expr().subs(t, f(a * x + b))
    assert sp.simplify(sp.expand_trig(back) + sp.sin(x) + sp.cos(x)) == 0
    from mathverify.sandbox.exactsets import class_solveset
    assert class_solveset(sp.Eq(-sp.sin(x) - sp.cos(x), 1), x, sp.Interval(0, 7)) == sp.FiniteSet(
        sp.pi, 3 * sp.pi / 2)


@pytest.mark.parametrize("e,good,bad", [
    ("sin(x) = cos(x)", "{pi/4, 5*pi/4}", "{pi/4}"),
    ("sqrt(3)*sin(x) - cos(x) = 1", "{pi/3, pi}", "{pi/3}"),
    (f"x*{QS} = 0", "{0, pi/3, pi}", "{0, pi/3}"),
    (f"{QS}**3 = 0", "{pi/3, pi}", "{pi/3}"),
    ("4**x - 3*2**x + 2 = 0", "{0, 1}", "{1}"),
    ("log(x)**2 - log(x) = 0", "{1, E}", "{0, 1, E}"),
    ("exp(2*x) - exp(x) - 2 = 0", "{log(2)}", "{log(2), I*pi}"),
    ("atan(x) = 2", "{}", "{tan(2)}"),
])
def test_solve_equation_in_the_new_classes(e, good, bad):
    ir = _eq(e, ["x >= 0", "x <= 2*pi"])
    assert _run(ir, good).verdict == "CORRECT", e
    assert _run(ir, bad).verdict == "INCORRECT", e


def test_the_reviewed_cases_are_now_decided():
    """B3/B4 of the review (2 Oct 2026): on 3872bcd unsolved, now class (v)."""
    ir = _eq("x**2 = 4", [f"{QS}**3 > 0", "x >= 0", "x <= 7"])
    assert _run(ir, "{}").verdict == "INCORRECT" and _run(ir, "{2}").verdict == "CORRECT"
    ev = _ev("x", [f"(x + 1)*{QS} = 0", "x > 0", "x < 2"])
    assert _run(ev, "pi/3", "value").verdict == "CORRECT"
    ev = _ev("x", [f"(x + 1)*{QS} = 0", "x > 0", "x < 4"])
    assert _run(ev, "pi/3", "value").verdict != "CORRECT"          # pi is a solution too


def test_polynomial_system_completeness():
    """`solve`'s list of a system in several unknowns is accepted only with a proof (zero-dimensional
    ideal, as many distinct solutions as its radical's quotient dimension)."""
    from mathverify.certify.algebra import _polynomial_system_worker as W
    y = sp.Symbol("y", real=True)
    assert W([sp.Eq(x + y, 5), sp.Eq(x * y, 6)], [x, y])[0] == [{x: 2, y: 3}, {x: 3, y: 2}]
    assert W([sp.Eq((x - 1) ** 2, 0), sp.Eq(y, 2)], [x, y])[0] == [{x: 1, y: 2}]       # a double root
    assert W([sp.Eq(x ** 2, y), sp.Eq(y ** 2, x)], [x, y])[0] == [{x: 0, y: 0}, {x: 1, y: 1}]   # 2 non-real
    assert W([sp.Eq(1 / x + 1 / y, 1), sp.Eq(x * y, 4)], [x, y])[0] == [{x: 2, y: 2}]
    assert W([sp.Eq(x ** 2 - 1, 0), sp.Eq(y * (x - 1), 1)], [x, y])[0] == [{x: -1, y: -sp.Rational(1, 2)}]
    assert W([sp.Eq(x * y, 1)], [x, y])[0] is None                                     # a curve
    assert W([sp.Eq(x ** 2 + y ** 2, 0)], [x, y])[0] is None
    assert W([sp.Eq(x + y, 1), sp.Eq(2 * x + 2 * y, 3)], [x, y]) == ([], "linear_system")


def test_polynomial_system_with_solutions_solve_misses_is_not_certified(monkeypatch):
    """A list `solve` gives without one of the solutions must not be accepted."""
    from mathverify.certify import algebra
    y = sp.Symbol("y", real=True)
    real_solve = sp.solve
    monkeypatch.setattr(sp, "solve", lambda *a, **k: real_solve(*a, **k)[:1])
    out, how = algebra._polynomial_system_worker([sp.Eq(x + y, 5), sp.Eq(x * y, 6)], [x, y])
    assert out is None and how.startswith("solve_found_1_of_2"), how


def test_evaluate_on_a_polynomial_system():
    y = V("y")
    assert _run(_ev("x*y", ["x + y = 5", "x**2 + y**2 = 13"], [X, y]), "6", "value").verdict == "CORRECT"
    assert _run(_ev("x", ["x + y = 5", "x*y = 6", "x > y"], [X, y]), "3", "value").verdict == "CORRECT"
    assert _run(_ev("x", ["x + y = 5", "x*y = 6"], [X, y]), "3", "value").verdict != "CORRECT"
    assert _run(_ev("x + y", ["x*y = 1"], [X, y]), "2", "value").verdict != "CORRECT"


def test_polynomial_system_solve_list_with_a_repeated_or_false_point(monkeypatch):
    """A repeated point must not stand in for a missing one, a point that is no solution must not count."""
    from mathverify.certify import algebra
    y = sp.Symbol("y", real=True)
    real_solve = sp.solve
    monkeypatch.setattr(sp, "solve", lambda *a, **k: real_solve(*a, **k)[:1] * 2)
    assert algebra._polynomial_system_worker([sp.Eq(x + y, 5), sp.Eq(x * y, 6)], [x, y])[0] is None

    def fake(*a, **k):
        s_ = real_solve(*a, **k)
        k0 = list(s_[0])
        return s_[:1] + [{k0[0]: sp.Integer(7), k0[1]: sp.Integer(-2)}]
    monkeypatch.setattr(sp, "solve", fake)
    assert algebra._polynomial_system_worker([sp.Eq(x + y, 5), sp.Eq(x * y, 6)], [x, y])[0] is None


def test_complete_solutions_does_not_take_the_solver_list():
    """`_complete_solutions` proves its own list; the solver's (here missing (3, 2), or the principal
    roots of a non-class equation) is not taken."""
    from mathverify.certify.algebra import _complete_solutions
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(_ev("x", ["x + y = 5", "x*y = 6"], [X, V("y")])))
    xs, ys = ctx.sym("x"), ctx.sym("y")
    out, how = _complete_solutions([sp.Eq(xs + ys, 5), sp.Eq(xs * ys, 6)], [], [xs, ys], [{xs: 2, ys: 3}], ctx)
    assert out is not None and len(out) == 2, (out, how)
    ctx = make_ctx(ProblemIR.from_dict(_ev("x", ["sin(2*x) = sin(x)"])))
    xs = ctx.sym("x")
    out, how = _complete_solutions([sp.Eq(sp.sin(2 * xs), sp.sin(xs))], [], [xs], [{xs: sp.pi / 3}], ctx)
    assert out is None, (out, how)


def test_evaluate_with_a_non_class_equation_keeps_unknown():
    """sin 2x = sin x on (1/2, 7/2): pi/3 and pi; `solve` gives 0, -pi/3, pi/3 (no pi)."""
    ir = _ev("x", ["sin(2*x) = sin(x)", "x > 1/2", "x < 7/2"])
    assert _run(ir, "pi/3", "value").verdict == "UNKNOWN"


def test_solve_guarded_uses_the_classes_on_the_reals():
    """(1/2)**x = 4: the solvers' -2 and -log(4)/log(2) did not agree as written (UNKNOWN on 3872bcd);
    sin x - cos x = 2 has no real solution (the solvers gave two complex ones)."""
    assert _run(_eq("(1/2)**x = 4"), "{-2}").verdict == "CORRECT"
    assert _run(_eq("(1/2)**x = 4"), "{2}").verdict == "INCORRECT"
    assert _run(_eq("sin(x) - cos(x) = 2"), "{}").verdict == "CORRECT"


def test_mono_zeros_keep_to_the_range():
    """exp takes no value <= 0, atan none outside (-pi/2, pi/2): such a root of g gives no zero."""
    from mathverify.sandbox.exactsets import _mono_zeros
    t = sp.Symbol("t")
    zeros, poles = _mono_zeros(sp.exp, 1, 0, sp.Poly(t ** 2 - t - 2, t))
    assert zeros == [(sp.log(2), 0)] and poles == []
    zeros, _ = _mono_zeros(sp.atan, 1, 0, sp.Poly((t - 1) * (t - 2), t))
    assert zeros == [(sp.tan(1), 0)]
    zeros, poles = _mono_zeros(sp.log, 1, 0, sp.Poly(t + 1, t))
    assert zeros == [(sp.exp(-1), 0)] and poles == []      # log(0): an edge from `_breaks` (round 5)


def test_a_definedness_condition_out_of_the_classes_is_not_taken_as_defined():
    """B5 with R = sin x + cos 2x (two frequencies, no class): undefined at pi/2, where the maximum 0 of
    -(x - pi/2)**2 + R/R - 1 on [1, 2] would be."""
    R = "(sin(x) + cos(2*x))"
    ir = _ir("extremum", {"f": f"-(x - pi/2)**2 + {R}/{R} - 1", "var": "x", "which": "max", "interval": "[1, 2]"})
    assert _run(ir, "0", "value").verdict != "CORRECT"


def test_a_log_factor_with_a_progression_on_the_reals():
    """log(x)*sin(x) = 0 on the reals: the zeros k*pi with k <= 0 are no zeros (log not real there); the
    union of the progressions is no answer, the set stays unsolved; on a window it is exact."""
    from mathverify.sandbox.exactsets import class_solveset
    assert class_solveset(sp.Eq(sp.log(x) * sp.sin(x), 0), x, S.Reals) is None
    assert class_solveset(sp.Eq(sp.log(x) * sp.sin(x), 0), x, sp.Interval(-4, 4)) == sp.FiniteSet(1, sp.pi)
    # on a window too: x = -1 is no zero of (x + 1)*log(x)
    assert class_solveset(sp.Eq((x + 1) * sp.log(x), 0), x, sp.Interval(-3, 3)) == sp.FiniteSet(1)



# ------------------------------------------------------------------------------------------------
# Round 5: no complete set out of the classes (two solvers agreeing is no proof); the classes (vii)
# exponent ratio, (viii) Abs/sign piecewise, (ix) one radical, (x) a sum of logs, identities as written
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rel,want", [
    (sp.Eq(3 ** x, 2 ** x), sp.FiniteSet(0)),
    (sp.Eq(2 * 3 ** x, 5 * 2 ** x), sp.FiniteSet(sp.log(sp.Rational(5, 2)) / sp.log(sp.Rational(3, 2)))),
    (3 ** x > 2 ** x, sp.Interval.open(0, sp.oo)),
    (sp.Eq(sp.Abs(2 * x - 3), 5), sp.FiniteSet(-1, 4)),
    (sp.Abs(x - 3) < 2, sp.Interval.open(1, 5)),
    (sp.Eq(sp.Abs(2 * x - 3), 2 * x - 3), sp.Interval(sp.Rational(3, 2), sp.oo)),
    (sp.Eq(sp.Abs(x) + sp.Abs(x - 1), 1), sp.Interval(0, 1)),
    (sp.Eq(sp.Abs(x ** 2 - 4), 3 * x), sp.FiniteSet(1, 4)),
    (sp.Eq(sp.sign(x) * sp.Abs(x) ** sp.Rational(1, 3), x), sp.FiniteSet(-1, 0, 1)),   # the real cube root
    (sp.Eq(sp.sqrt(x + 4), x - 2), sp.FiniteSet(5)),
    (sp.sqrt(x + 4) > x - 2, sp.Interval.Ropen(-4, 5)),
    (sp.Eq(sp.sqrt(x), -1), S.EmptySet),
    (sp.Eq(sp.log(x - 1) + sp.log(x - 3), sp.log(3)), sp.FiniteSet(4)),               # x = 0 is outside
    (sp.log(x - 1) + sp.log(x - 3) < sp.log(3), sp.Interval.open(3, 4)),
    (sp.Eq(sp.log(x ** 2), sp.log(4)), sp.FiniteSet(-2, 2)),
    (sp.Eq(x ** 2 - 5 * x - 14, (x - 7) * (x + 2)), S.Reals),
    (sp.Eq((sp.sqrt(x) - 1) / (x - 1), 1 / (sp.sqrt(x) + 1)),
     sp.Union(sp.Interval.Ropen(0, 1), sp.Interval.open(1, sp.oo))),
])
def test_round5_class_sets(rel, want):
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(rel, x, S.Reals)
    if isinstance(want, sp.FiniteSet) and isinstance(got, sp.FiniteSet) and len(got) == len(want) == 1:
        assert sp.simplify(sp.expand_log(got.args[0] - want.args[0], force=True)) == 0, (rel, got)
    else:
        assert got == want, (rel, got)


def test_an_identity_keeps_its_written_poles():
    """(2x**2 + 1)/(x**2 - 5) = (2 + 1/x**2)/(1 - 5/x**2) is 0 = 0 over one denominator; as written it is
    undefined at 0 and +-sqrt(5)."""
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(sp.Eq((2 * x ** 2 + 1) / (x ** 2 - 5), (2 + 1 / x ** 2) / (1 - 5 / x ** 2)), x, S.Reals)
    assert got.contains(0) is sp.false and got.contains(sp.sqrt(5)) is sp.false and got.contains(1) is sp.true


@pytest.mark.parametrize("rel", [
    sp.Eq(sp.exp(x), 3 * x), sp.Eq(sp.floor(x), 2), sp.Eq(x ** x, 4), sp.Eq(sp.log(x), x - 1),
    sp.exp(x) > x + 1, sp.Eq(2 ** x, x ** 2), sp.Eq(sp.Abs(sp.Abs(x) - 1), 1 + x ** 3 * sp.exp(x)),
])
def test_out_of_the_classes_no_set(rel):
    """SymPy's own set is no proof: out of the classes, a ConditionSet."""
    from mathverify.sandbox.exactsets import exact_solveset
    assert isinstance(exact_solveset(rel, x, S.Reals), sp.ConditionSet)


@pytest.mark.parametrize("e,claim,want", [
    ("3**x = 2**x", "{0}", "CORRECT"),
    ("3**x = 2**x", "{0, 1}", "INCORRECT"),
    ("exp(x) + x = 1", "{0}", "UNKNOWN"),            # x = 0 is the only root, but no class proves it
    ("exp(x) + x = 1", "{1}", "INCORRECT"),          # 1 is no root
    ("log(x) = x - 1", "{1}", "UNKNOWN"),
    ("x**x = 4", "{2}", "UNKNOWN"),
    ("exp(x) = 3*x", "{}", "UNKNOWN"),               # roots exist (LambertW), none proved one by one here
    ("2**x = x**2", "{2, 4}", "UNKNOWN"),            # the third root -2*LambertW(log(2)/2)/log(2), unproved
    ("2**x = x**2", "{2, 4, 5}", "INCORRECT"),       # 5 is no root
    ("sqrt(x + 4) = x - 2", "{5}", "CORRECT"),
    ("sqrt(x + 4) = x - 2", "{0, 5}", "INCORRECT"),
    ("Abs(2*x - 3) = 5", "{-1, 4}", "CORRECT"),
    ("Abs(2*x - 3) = 5", "{4}", "INCORRECT"),
    ("log(x - 1) + log(x - 3) = log(3)", "{4}", "CORRECT"),
    ("log(x - 1) + log(x - 3) = log(3)", "{0, 4}", "INCORRECT"),
    ("3**x + 2**x = 0", "{}", "CORRECT"),            # SymPy's relation is False in the sandbox worker
])
def test_round5_solve_equation(e, claim, want):
    assert _run(_eq(e), claim).verdict == want, e


def test_solver_agreement_is_no_completeness():
    """`solve_guarded` gives no complete list out of the classes, also when solve and solveset agree."""
    from mathverify.certify.algebra import solve_guarded
    kept, ev = solve_guarded(sp.Eq(sp.exp(x) + x, 1), x)
    assert ev["complete"] is None and ev["completeness_method"].startswith("none")
    kept, ev = solve_guarded(sp.Eq(3 ** x, 2 ** x), x)
    assert ev["complete"] is True and ev["completeness_method"] == "exact_class"


def test_count_roots_of_a_class():
    ir = _ir("count_roots", {"expr": "exp(2*x) - 3*exp(x) + 2", "var": "x"}, shape="count")
    assert _run(ir, "2", "count").verdict == "CORRECT"
    assert _run(ir, "1", "count").verdict == "INCORRECT"
    ir = _ir("count_roots", {"expr": "exp(x) - 3*x", "var": "x"}, shape="count")
    assert _run(ir, "2", "count").verdict == "UNKNOWN"


def test_step_completeness_needs_a_proof(monkeypatch):
    """`_proved_points` takes no list `solve` gives; `_proved_on_system` reads explicit definitions or a
    proved complete system only."""
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.steps import deterministic as det
    ctx = make_ctx(ProblemIR.from_dict(_ev("x", ["x + y = 5", "x*y = 6"], [X, V("y")])))
    xs, ys = ctx.sym("x"), ctx.sym("y")
    pts = det._proved_points([sp.Eq(xs + ys, 5), sp.Eq(xs * ys, 6)], [xs, ys], ctx)
    assert pts is not None and len(pts) == 2
    assert det._proved_points([sp.Eq(xs * ys, 1)], [xs, ys], ctx) is None
    # `solve` gives no point of x**5 - x - 1 = 0, y = x**2 (one real solution): no proof, no list
    assert det._proved_points([sp.Eq(xs ** 5 - xs - 1, 0), sp.Eq(ys, xs ** 2)], [xs, ys], ctx) is None
    # y = x**2: y >= 0 at the explicit definition
    assert det._proved_on_system(ys >= 0, [sp.Eq(ys, xs ** 2)], {}, ctx) is True
    assert det._proved_on_system(ys >= 1, [sp.Eq(ys, xs ** 2)], {}, ctx) is False


def test_ratio_of_two_positive_terms_has_no_zero():
    from mathverify.sandbox.exactsets import _ratio_zeros
    assert _ratio_zeros(3 ** x + 2 ** x, x) == []
    assert _ratio_zeros(3 ** x - 2 ** x, x) == [(0, 0)]



# ------------------------------------------------------------------------------------------------
# The review of round 5 (2 Oct 2026): B1 a positive generator for log/sinh/atan, B2 sign(0) lost on
# closed cells, B3 a folded cell keeping the undefined points; the odd-root convention of part d4a
# ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rel,want", [
    (sp.Eq(sp.Max(sp.log(x), 0), 0), sp.Interval.Lopen(0, 1)),                      # B1: was {1}
    (sp.Eq(sp.Max(sp.sinh(x), 0), 0), sp.Interval(-sp.oo, 0)),                      # B1: was {0}
    (sp.Eq(sp.sqrt(sp.log(x) ** 2), 1), sp.FiniteSet(sp.E, sp.exp(-1))),             # B1: was {E}
    (sp.Eq(sp.Abs(sp.log(x)), 1), sp.FiniteSet(sp.E, sp.exp(-1))),
    (sp.Eq(sp.Min(sp.sinh(x), 0), -1), sp.FiniteSet(-sp.asinh(1))),
    (sp.Eq(sp.sign(x), 0), sp.FiniteSet(0)),                                         # B2: was {}
    (sp.Eq(sp.sign(x ** 2 - 4), 0), sp.FiniteSet(-2, 2)),
    (sp.Eq(sp.sign(x) + sp.Abs(x), 0), sp.FiniteSet(-1, 0)),                          # B2: was {-1}
    (sp.Eq(sp.sign(x), 1), sp.Interval.open(0, sp.oo)),                              # was [0, oo)
    (sp.sign(x) + 1 > 0, sp.Interval(0, sp.oo)),
    (sp.Eq(sp.Abs(x) / x, 1), sp.Interval.open(0, sp.oo)),                           # B3: was [0, oo)
    (sp.Eq(sp.Abs(x) * sp.log(x), x * sp.log(x)), sp.Interval.open(0, sp.oo)),       # B3: was [0, oo)
])
def test_review_of_round5_sets(rel, want):
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(rel, x, S.Reals)
    if isinstance(want, sp.FiniteSet) and isinstance(got, sp.FiniteSet):
        assert len(got) == len(want) and all(any(sp.simplify(g - w) == 0 for w in want) for g in got), (rel, got)
    else:
        assert got == want, (rel, got)


def test_a_folded_cell_keeps_out_the_poles_of_tan():
    """B3: |x| tan x = x tan x on [0, 3] holds where tan is defined only (pi/2 is no point of the set)."""
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(sp.Eq(sp.Abs(x) * sp.tan(x), x * sp.tan(x)), x, sp.Interval(0, 3))
    assert got.contains(sp.pi / 2) is sp.false and got.contains(1) is sp.true and got.contains(0) is sp.true


def test_the_generator_of_log_carries_no_sign():
    """B1: the reading of log/sinh/atan is a polynomial in a generator with no assumption, checked by
    substituting back; Max(t, 0) and sqrt(t**2) are no polynomials."""
    from mathverify.sandbox.exactsets import _mono_parts
    assert _mono_parts(sp.Max(sp.log(x), 0), x) is None
    assert _mono_parts(sp.sqrt(sp.log(x) ** 2) - 1, x) is None
    assert _mono_parts(sp.log(x) ** 2 - 1, x) is not None


@pytest.mark.parametrize("rel", [
    sp.Eq(x ** sp.Rational(2, 3), 1), sp.Eq(x ** sp.Rational(1, 3), x), x ** sp.Rational(1, 3) > x,
])
def test_a_written_odd_root_of_a_negative_number_is_a_convention(rel):
    """x**(2/3) = 1: {1} reads the principal root, {-1, 1} the real one (part d4a): no set."""
    from mathverify.sandbox.exactsets import exact_solveset
    assert isinstance(exact_solveset(rel, x, S.Reals), sp.ConditionSet)
    # on x >= 0 there is no convention
    assert not isinstance(exact_solveset(rel, x, sp.Interval(0, 5)), sp.ConditionSet)


@pytest.mark.parametrize("ir,claim,kind,want", [
    (_eq("sign(x) = 0"), "{}", "set", "INCORRECT"),
    (_eq("sign(x) = 0"), "{0}", "set", "CORRECT"),
    (_ir("count_roots", {"expr": "sign(x)", "var": "x"}, shape="count"), "0", "count", "INCORRECT"),
    # (0, 1]: "1" is wrong; INCORRECT is no false rejection (round 7, RK5)
    (_ir("count_roots", {"expr": "Max(log(x), 0)", "var": "x"}, shape="count"), "1", "count", {"INCORRECT", "UNKNOWN"}),
    (_eq("sqrt(log(x)**2) = 1"), "{E}", "set", "INCORRECT"),
    (_eq("sqrt(log(x)**2) = 1"), "{E, exp(-1)}", "set", "CORRECT"),
    (_eq("Max(log(x), 0) = 0"), "{1}", "set", "INCORRECT"),
    (_eq("Max(sinh(x), 0) = 0"), "{0}", "set", "INCORRECT"),      # (-oo, 0]: measure oo, not "positive"
])
def test_review_of_round5_verdicts(ir, claim, kind, want):
    v = _run(ir, claim, kind).verdict
    assert v == want if isinstance(want, str) else v in want


# ------------------------------------------------------------------------------------------------
# Round 6 (6 Oct 2026): one number written two ways at an interval's end. The polynomial class reads
# x > log(8)/log(2) as (3, oo) (sp.Poly writes log(8) as 3*log(2)); `Ctx.domain_for` keeps the given as
# written, (log(8)/log(2), oo); SymPy's Intersection cannot order 3 and log(8)/log(2) and raised TypeError,
# so the certificate died (UNKNOWN) where the merge with part d4d expected CORRECT
# ------------------------------------------------------------------------------------------------
L8 = "log(8)/log(2)"


@pytest.mark.parametrize("ir,claim,want", [
    (_eq("x**2 = 4", [f"x > {L8}"]), "{}", "CORRECT"),
    (_eq("x**2 = 9", [f"x >= {L8}"]), "{3}", "CORRECT"),
    (_eq("x**2 = 9", [f"x >= {L8}"]), "{-3, 3}", "INCORRECT"),
    (_eq("x**2 = 4", ["x > a", f"a = {L8}"], (X, V("a"))), "{}", "CORRECT"),
    (_eq(f"log(x - {L8}) = 0", [f"x > {L8}"]), "{4}", "CORRECT"),
    (_eq(f"sqrt(x - {L8}) = 1", [f"x >= {L8}"]), "{4}", "CORRECT"),
])
def test_one_endpoint_written_two_ways(ir, claim, want):
    assert _run(ir, claim).verdict == want


def test_exact_intersection_writes_one_way_only_what_is_proved_equal():
    from mathverify.certify.base import exact_intersection
    L = sp.log(8) / sp.log(2)
    assert exact_intersection(sp.Interval.open(L, sp.oo), sp.Interval.open(3, sp.oo)) in (
        sp.Interval.open(3, sp.oo), sp.Interval.open(L, sp.oo))           # one writing (the first seen, round 8)
    assert exact_intersection(sp.Interval(L, 5), sp.Interval(3, 4)) in (sp.Interval(3, 4), sp.Interval(L, 4))
    # 3 + e^(-e^10) is no 3: no proof writes them one way. SymPy could not order them (it read the difference one
    # way only); a certified difference orders them now (round 9, mathverify._sympy_guards)
    near = L + sp.exp(-sp.exp(10))
    assert exact_intersection(sp.Interval.open(near, sp.oo), sp.Interval.open(3, sp.oo)) == sp.Interval.open(near, sp.oo)
    # 3 + gd(1) - gd(1) is exactly 3, and no exact test proves it: not ordered, not merged
    far = 3 + 2 * sp.atan(sp.tanh(S.Half)) - sp.atan(sp.sinh(1))
    with pytest.raises(TypeError):
        exact_intersection(sp.Interval.open(far, sp.oo), sp.Interval.open(3, sp.oo))



# ------------------------------------------------------------------------------------------------
# Round 7 (6 Oct 2026), the review of round 6: a cell of `_piecewise` was dropped whole when its MIDPOINT
# was outside the domain of a log or an even root (YO-1, RK1); a cell folded to True kept a written odd root
# of a negative number (YO-2); the measure of a finite set was a Python 0 (RK2); a one-sided domain was
# solved on the whole line (RK3); a denominator with Abs or sign in it left the whole set unsolved (RK4); the
# sampler of solve_inequality met two writings of one endpoint (RK6)
# ------------------------------------------------------------------------------------------------
_A, _L, _R = sp.Abs, sp.log, sp.sqrt
_Q = sp.Rational


@pytest.mark.parametrize("rel,dom,want", [
    (sp.Eq(_A(x) * _L(x - 1), 0), S.Reals, sp.FiniteSet(2)),                                 # was {}
    (sp.Eq(_R(x - 2) + _A(x), 4), S.Reals, sp.FiniteSet(3)),                                 # was {}
    (sp.Eq(_A(x ** 2 - 4 * x) * _L(x - 2), 0), S.Reals, sp.FiniteSet(3, 4)),                 # was {4}
    (sp.Eq((_A(x) - x) * _L(x - 1), 0), S.Reals, sp.Interval.open(1, sp.oo)),                # was {}
    (_A(x) * _L(x - 1) >= 0, S.Reals, sp.Interval(2, sp.oo)),
    (sp.Eq(_A(x), _R(2 * x + 1)), S.Reals, sp.FiniteSet(1 - sp.sqrt(2), 1 + sp.sqrt(2))),     # was {1 + sqrt(2)}
    (_A(x - 2) * _L(x - 1) < 0, S.Reals, sp.Interval.open(1, 2)),                            # was {}
    (sp.Eq((_A(x - 3) - _Q(1, 2)) * _L(x - 2), 0), S.Reals, sp.FiniteSet(_Q(5, 2), 3, _Q(7, 2))),
    (sp.Eq((_A(x) + _A(x - 10) - 10) * _L(x - 6), 0), S.Reals, sp.Interval.Lopen(6, 10)),
    (sp.Eq(_L(_A(x) - 1), 0), S.Reals, sp.FiniteSet(-2, 2)),                                 # an argument with |x|
    (sp.Eq(x / sp.sign(x), 2), S.Reals, sp.FiniteSet(-2, 2)),                                 # RK4
    (sp.Eq(1 / (x - _A(x)), -_Q(1, 2)), S.Reals, sp.FiniteSet(-1)),                           # RK4
    (sp.Eq(_A(x) / sp.sign(x - 1), 2), S.Reals, sp.FiniteSet(2)),
    (sp.Eq(x / sp.sign(x), 0), S.Reals, S.EmptySet),                                          # 0 is no root
    (sp.Eq(x / _A(x), 1), S.Reals, sp.Interval.open(0, sp.oo)),
    (1 / (x - _A(x)) < 0, S.Reals, sp.Interval.open(-sp.oo, 0)),                             # undefined on [0, oo)
    (x ** _Q(1, 3) < 1, sp.Interval.open(0, sp.oo), sp.Interval.open(0, 1)),                 # RK3
    (x ** _Q(1, 3) >= 2, sp.Interval.open(0, sp.oo), sp.Interval(8, sp.oo)),
    (x ** _Q(2, 3) <= 4, sp.Interval.open(0, sp.oo), sp.Interval.Lopen(0, 8)),
    (sp.Eq((x + _A(x)) * x ** _Q(1, 3), 0), sp.Interval(0, 5), sp.FiniteSet(0)),             # no x < 0 there
    # a denominator 0 inside a cell whose relation folds to True: 1 is no point
    (sp.Eq((x - 1) / (_A(x) - 1), 1), S.Reals, sp.Union(sp.Interval.Ropen(0, 1), sp.Interval.open(1, sp.oo))),
])
def test_round7_sets(rel, dom, want):
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(rel, x, dom)
    if isinstance(want, sp.FiniteSet) and isinstance(got, sp.FiniteSet):
        assert len(got) == len(want) and all(any(sp.simplify(g - w) == 0 for w in want) for g in got), (rel, got)
    else:
        assert got == want, (rel, got)


@pytest.mark.parametrize("rel,dom", [
    (sp.Eq(_A(x) + _L(x ** 2 - 1), 0), S.Reals),                     # two irrational roots: out of the classes
    (sp.Eq(_A(x) * _A(x + 5) * _L(sp.sin(x)), 0), sp.Interval(-5, 0)),  # an argument that is no polynomial
    (sp.Eq((x + _A(x)) * x ** _Q(1, 3), 0), S.Reals),                  # YO-2: (-oo, 0] or {0} by the reading
    (sp.Eq(sp.Max(x, 0) * x ** _Q(1, 3), 0), S.Reals),
    (sp.Eq((sp.sign(x) + 1) * x ** _Q(1, 3), 0), S.Reals),
    ((x + _A(x)) * x ** _Q(1, 3) >= 0, S.Reals),
    (x ** _Q(1, 3) < 1, S.Reals),                                     # x < 0 is there: a convention
    # a log argument with |x| that is no polynomial on its cell, on a folded cell: the truth is (1.106..., oo)
    (sp.Eq((_A(x) - x) * _L(_A(x) - 2 + sp.sin(x)), 0), sp.Interval(0, sp.oo)),
])
def test_round7_no_set(rel, dom):
    from mathverify.sandbox.exactsets import exact_solveset
    assert isinstance(exact_solveset(rel, x, dom), sp.ConditionSet)


def test_round7_principal_reading_of_a_folded_cell():
    from mathverify.sandbox.exactsets import principal_solveset
    assert principal_solveset(sp.Eq((x + _A(x)) * x ** _Q(1, 3), 0), x) == sp.FiniteSet(0)


def test_round7_the_sign_of_the_variable_bounds_its_window():
    """A positive integer x of count_integers: x**(1/3) < 2 has no convention there (was left unsolved)."""
    from mathverify.sandbox.exactsets import exact_solveset
    n = sp.Symbol("x", integer=True, positive=True)
    assert exact_solveset(n ** _Q(1, 3) < 2, n, S.Reals) == sp.Interval.open(0, 8)


def _croots(e, givens=()):
    return _ir("count_roots", {"expr": e, "var": "x"}, (X,), givens, "count")


def _cint(givens, vars_=(X,)):
    return _ir("count_integers", {"var": "x"}, vars_, givens, "count")


def _ineq(e, givens=(), vars_=(X,)):
    return _ir("solve_inequality", {"inequality": e, "var": "x"}, vars_, givens, "set")


XP = V("x", "positive_real")
R7 = "Abs(x**2 - 4*x)*log(x - 2) = 0"
C7 = "(Abs(x) + Abs(x - 10) - 10)*log(x - 6) = 0"


@pytest.mark.parametrize("ir,claim,kind,want", [
    # YO-1 / RK1
    (_croots("Abs(x)*log(x - 1)"), "1", "count", "CORRECT"),
    (_croots("Abs(x)*log(x - 1)"), "0", "count", "INCORRECT"),
    (_croots("sqrt(x - 2) + Abs(x) - 4"), "0", "count", "INCORRECT"),
    (_eq("x**2 = 9", ["Abs(x)*log(x - 1) >= 0"]), "{3}", "set", "CORRECT"),
    (_eq("x**2 = 9", ["Abs(x)*log(x - 1) >= 0"]), "{}", "set", "INCORRECT"),
    (_ev("x**2", [R7]), "16", "value", "UNKNOWN"),                       # x**2 is 9 or 16
    (_eq("Abs(x) + log(x**2 - 1) = 0"), "{}", "set", {"INCORRECT", "UNKNOWN"}),
    (_eq("(Abs(x) - x)*log(x - 1) = 0"), "{}", "set", "INCORRECT"),
    (_croots("Abs(x) - sqrt(2*x + 1)"), "2", "count", "CORRECT"),
    (_croots("Abs(x) - sqrt(2*x + 1)"), "1", "count", "INCORRECT"),
    (_croots("(Abs(x - 3) - 1/2)*log(x - 2)"), "3", "count", "CORRECT"),
    (_ineq("Abs(x - 2)*log(x - 1) < 0"), "Interval.open(1, 2)", "interval", "CORRECT"),
    (_ev("x", ["Abs(x) = sqrt(2*x + 1)", "x < 0"]), "1 - sqrt(2)", "value", "CORRECT"),
    (_cint([C7], [V("x", "integer")]), "4", "count", "CORRECT"),
    (_cint([C7], [V("x", "integer")]), "1", "count", "INCORRECT"),
    (_eq(C7), "{10}", "set", "INCORRECT"),
    # YO-2: the reading of a written odd root decides
    (_eq("(x + Abs(x))*x**(1/3) = 0"), "{0}", "set", "UNKNOWN"),
    # RK2: no layer_exception
    (_eq("Abs(x - 3) = 3 - x", ["x >= 3"]), "{3}", "set", "CORRECT"),
    (_eq("Abs(x) = x", ["x <= 0"]), "{0}", "set", "CORRECT"),
    (_eq("Max(x, 2) = 2", ["x >= 2"]), "{2}", "set", "CORRECT"),
    (_eq("Abs(x - 1) + Abs(x + 1) = 2", ["x >= 1"]), "{1}", "set", "CORRECT"),
    # RK3: x > 0, no convention
    (_ineq("x**(1/3) < 1", vars_=(XP,)), "Interval.open(0, 1)", "interval", "CORRECT"),
    (_ineq("x**(1/3) >= 2", vars_=(XP,)), "Interval(8, oo)", "interval", "CORRECT"),
    (_cint(["x**(1/3) < 2"], [V("x", "positive_integer")]), "7", "count", "CORRECT"),
    (_cint(["x**(1/3) < 2"], [V("x", "positive_integer")]), "8", "count", "INCORRECT"),
    (_ineq("x**(1/3) < 1"), "Interval.open(0, 1)", "interval", {"INCORRECT", "UNKNOWN"}),
    (_ir("domain_of", {"expr": "log(2 - x**(1/3))", "var": "x"}, (XP,), (), "interval"), "Interval.open(0, 8)",
     "interval", "CORRECT"),                                             # 0 is no value of a positive x
    # RK4
    (_croots("x/sign(x) - 2"), "2", "count", "CORRECT"),
    (_croots("1/(x - Abs(x)) + 1/2"), "1", "count", "CORRECT"),
    # RK6
    (_ineq("x**2 < 16", ["x > log(8)/log(2)"]), "Interval.open(3, 4)", "interval", "CORRECT"),
    (_ineq("x**2 < 16", ["x > log(8)/log(2)"]), "Interval.Lopen(3, 4)", "interval", "INCORRECT"),
    # an exact set the integers meet in finitely many points
    (_eq("Max(log(x), 0) = 0", ["x >= -5"], (V("x", "integer"),)), "{1}", "set", "CORRECT"),
])
def test_round7_verdicts(ir, claim, kind, want):
    v = _run(ir, claim, kind).verdict
    assert v == want if isinstance(want, str) else v in want


def test_round7_a_step_that_picks_one_of_two_roots():
    """x**2 - 7x + 12 = 0 with |x**2 - 4x| log(x - 2) = 0: both 3 and 4 are left, `x = 4` is no step."""
    r = _run(_eq("x**2 - 7*x + 12 = 0", [R7]), "{3, 4}", steps=[("eq", "x = 4")])
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    assert [st["status"] for st in layer.evidence["steps"]] != ["verified"]


def test_round7_a_periodic_equation_with_a_log_on_a_bounded_window():
    """sin(x)*log(x) = 0 on [1/2, 10]: {1, pi, 2*pi, 3*pi}. On the whole line a progression meets a log factor
    and no set is exact; the bounded hull of the domain gives it (mutation A06: the class set on the reals
    alone; the tan x = 1 case it named is now proved from the reals met with the domain too)."""
    ir = _eq("sin(x)*log(x) = 0", ["x >= 1/2", "x <= 10"])
    assert _run(ir, "{1, pi, 2*pi, 3*pi}").verdict == "CORRECT"
    assert _run(ir, "{1, pi, 2*pi}").verdict == "INCORRECT"



# ------------------------------------------------------------------------------------------------
# Round 8 (7 Oct 2026), the review of round 7: a folded cell kept the points where an acos, asin, atan2 or
# arg of the expression is not real (YO-1); a window end equal to a cut in another writing (RK-1, RK-3);
# the convention of an odd root read where the expression is undefined anyway (RK-2); two writings of one
# endpoint ordered by rounding (RK-4)
# ------------------------------------------------------------------------------------------------
L8_ = sp.log(8) / sp.log(2)
_P0 = sp.Interval(0, sp.oo)


def _same_set(a, b) -> bool:
    from mathverify.sandbox.exactsets import exact_complement
    return exact_complement(a, b) is S.EmptySet and exact_complement(b, a) is S.EmptySet


@pytest.mark.parametrize("rel,dom,want", [
    (sp.Le((_A(x) - x) * sp.acos(x / 2), 0), _P0, sp.Interval(0, 2)),                      # acos(x/2) cut
    (sp.Eq((_A(x) - x) * sp.acos(x / 2), 0), _P0, sp.Interval(0, 2)),
    (sp.sign(x - 3) > 0, sp.Interval(-sp.oo, L8_), S.EmptySet),                            # RK-1: was {L8}
    (sp.sign(3 - x) > 0, sp.Interval(L8_, sp.oo), S.EmptySet),
    (sp.sign(x - 2) > 0, sp.Interval(-sp.oo, sp.log(9) / sp.log(3)), S.EmptySet),
    (_A(x - 3) < 1, sp.Interval.open(L8_, sp.oo), sp.Interval.open(3, 4)),                 # RK-3: was no set
    (_A(x - 3) <= 1, sp.Interval(L8_, sp.oo), sp.Interval(3, 4)),
    (_A(x - 3) > 1, sp.Interval.open(L8_, sp.oo), sp.Interval.open(4, sp.oo)),
    (sp.Eq(sp.sin(x) * _A(x) * sp.sqrt(x) * (x ** _Q(1, 3) - 2), 0), sp.Interval(-1, 10),   # RK-2: was no set
     sp.FiniteSet(0, sp.pi, 2 * sp.pi, 3 * sp.pi, 8)),
    (sp.Eq(sp.sin(x) * _A(x - 1) * _L(x) * (x ** _Q(1, 3) - 1), 0), sp.Interval(-2, 7), sp.FiniteSet(1, sp.pi, 2 * sp.pi)),
    (sp.Eq(sp.cos(x) * sp.Max(x, 1) * sp.sqrt(x - 1) * (x ** _Q(1, 3) - 2), 0), sp.Interval(-3, 9),
     sp.FiniteSet(1, sp.pi / 2, 3 * sp.pi / 2, 5 * sp.pi / 2, 8)),
    ((_A(x) - x) * sp.acos(x / 2) >= 0, sp.FiniteSet(0, 1, 2, 3), sp.FiniteSet(0, 1, 2)),   # point by point
    ((_A(x) - x) * _L(x - 2) >= 0, sp.FiniteSet(1, 3), sp.FiniteSet(3)),                    # 0*log(-1) is no 0
    # an identity holds wherever defined: not where acos is not real
    (sp.Eq((x ** 2 - 1) * sp.acos(x) / (x - 1) - (x + 1) * sp.acos(x), 0), S.Reals, sp.Interval.Ropen(-1, 1)),
])
def test_round8_sets(rel, dom, want):
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(rel, x, dom)
    assert not isinstance(got, sp.ConditionSet) and _same_set(got, want), (rel, got)


@pytest.mark.parametrize("rel,dom", [
    (sp.Le((_A(x) - x) * sp.acos(2 ** x + x - 2), 0), _P0),          # YO-1: was [0, oo), the truth [0, 1]
    (sp.Le((_A(x) - x) * sp.asin(x + sp.atan(x)), 0), _P0),
    (sp.Le((_A(x) - x) * sp.acos(x * sp.exp(x)), 0), _P0),
    (sp.Ge((_A(x) - x) * sp.atan2(x - 1, 0), 0), _P0),                # atan2(0, 0): undefined or 0
    (sp.Ge((_A(x) - x) * sp.arg(x - 1), 0), _P0),
    (sp.Ge((_A(x) + x) * sp.asin(x + sp.atan(x)), 0), sp.Interval(-sp.oo, 0)),
    (sp.Eq(_A(x) * sp.sqrt(x + 8) * (x ** _Q(1, 3) + 1), 0), S.Reals),  # x = -1: a root of the real reading only
    # on a finite domain SymPy's own ConditionSet decided each point on the principal branch: {-1, 0}
    (sp.Eq((x + _A(x)) * x ** _Q(1, 3), 0), sp.FiniteSet(-1, 0, 1)),
])
def test_round8_no_set(rel, dom):
    from mathverify.sandbox.exactsets import exact_solveset
    assert exact_solveset(rel, x, dom).has(sp.ConditionSet)


def test_round8_certified_sign_of_a_jump():
    """sign() of an exact 0 written log(8)/log(2) - 3: strict evalf gave 1 (RK-1)."""
    from mathverify.equiv.numeric import certified_sign
    z = L8_ - 3
    assert certified_sign(sp.sign(z)) == 0 and certified_sign(sp.sign(-z)) == 0
    assert certified_sign(_A(z) - 1) == -1
    assert certified_sign(sp.sign(z) + 1) == 1
    assert certified_sign(sp.sign(sp.exp(-sp.exp(10)))) == 1


def test_round8_no_strip_between_two_writings():
    """(sqrt(3 + 2 sqrt 2), oo) minus (1 + sqrt 2, 2 + sqrt 2): SymPy kept a strip that holds no number (RK-4)."""
    from mathverify.sandbox.exactsets import exact_complement
    r2 = sp.sqrt(2)
    got = exact_complement(sp.Interval.open(sp.sqrt(3 + 2 * r2), sp.oo), sp.Interval.open(1 + r2, 2 + r2))
    assert got == sp.Interval(2 + r2, sp.oo)


def test_round8_a_written_condition_no_class_solves_is_listed_unsolved():
    """2**x + x - 2 <= 1 of an acos was dropped from the domain (Ctx.domain_for): now listed unsolved."""
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(_ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0")))
    assert ctx.unsolved_conditions(ctx.sym("x"))


def test_round8_a_side_undefined_at_a_point_holds_nothing():
    from mathverify.certify.domain import relation_holds_at
    assert relation_holds_at(sp.Le((_A(x) - x) * sp.acos(2 ** x + x - 2), 0), x, 2) is False
    assert relation_holds_at(sp.Le((_A(x) - x) * sp.acos(2 ** x + x - 2), 0), x, 0) is True


X0 = V("x", "real", ["x >= 0"])
_NOTOK = {"INCORRECT", "UNKNOWN"}
_NOTNO = {"CORRECT", "UNKNOWN"}
_R2 = "sqrt(3 + 2*sqrt(2))"


def _trig_w(eqn, interval):
    return _ir("trig_solve", {"var": "x", "interval": interval}, (X,), [eqn], "set")


@pytest.mark.parametrize("ir,claim,kind,want", [
    # YO-1
    (_ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", vars_=(X0,)), "Interval(0, oo)", "interval", _NOTOK),
    (_ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", ["x >= 0"]), "Interval(0, oo)", "interval", _NOTOK),
    (_ineq("(Abs(x) - x)*asin(x + atan(x)) <= 0", vars_=(X0,)), "Interval(0, oo)", "interval", _NOTOK),
    (_ineq("(Abs(x) - x)*acos(x*exp(x)) <= 0", vars_=(X0,)), "Interval(0, oo)", "interval", _NOTOK),
    (_ineq("(Abs(x) - x)*atan2(x - 1, 0) >= 0", vars_=(X0,)), "Interval(0, oo)", "interval", "UNKNOWN"),
    (_ineq("(Abs(x) - x)*arg(x - 1) >= 0", vars_=(X0,)), "Interval(0, oo)", "interval", "UNKNOWN"),
    (_ineq("(Abs(x) - x)*arg(x - 1) >= 0", vars_=(X0,)), "Union(Interval.Ropen(0, 1), Interval.open(1, oo))",
     "interval", "UNKNOWN"),
    (_ineq("(Abs(x) - x)*acos(x/2) <= 0", vars_=(X0,)), "Interval(0, oo)", "interval", "INCORRECT"),
    (_ineq("(Abs(x) - x)*acos(x/2) <= 0", vars_=(X0,)), "Interval(0, 2)", "interval", "CORRECT"),
    # atan2(0, 0), arg(0): undefined or 0 (a convention)
    (_ev("x", ["atan2(x - 1, 0) = 0"]), "1", "value", "UNKNOWN"),
    (_ev("x", ["arg(x - 1) = 0", "x <= 1"]), "1", "value", "UNKNOWN"),
    # RK-1
    (_ineq("sign(x - 3) > 0", ["x <= log(8)/log(2)"]), "EmptySet", "set", _NOTNO),
    (_ineq("sign(x - 3) > 0", ["x <= log(8)/log(2)"]), "{log(8)/log(2)}", "set", _NOTOK),
    (_ineq("sign(3 - x) > 0", ["x >= log(8)/log(2)"]), "EmptySet", "set", _NOTNO),
    (_ineq("sign(x - log(4)) > 0"), "Interval.open(log(4), oo)", "interval", _NOTNO),
    # RK-2
    (_trig_w("sin(x)*Abs(x)*sqrt(x)*(x**(1/3) - 2) = 0", "[-1, 10]"), "{0, pi, 2*pi, 3*pi, 8}", "set", "CORRECT"),
    (_trig_w("sin(x)*Abs(x)*sqrt(x)*(x**(1/3) - 2) = 0", "[-1, 10]"), "{0, pi, 2*pi, 3*pi}", "set", "INCORRECT"),
    (_trig_w("sin(x)*Abs(x - 1)*log(x)*(x**(1/3) - 1) = 0", "[-2, 7]"), "{1, pi, 2*pi}", "set", "CORRECT"),
    (_trig_w("sin(x)*Abs(x - 1)*log(x)*(x**(1/3) - 1) = 0", "[-2, 7]"), "{-1, 1, pi, 2*pi}", "set", "INCORRECT"),
    # RK-3
    (_ineq("Abs(x - 3) < 1", ["x > log(8)/log(2)"]), "Interval.open(log(8)/log(2), 4)", "interval", "CORRECT"),
    (_ineq("Abs(x - 3) <= 1", ["x >= log(8)/log(2)"]), "Interval(log(8)/log(2), 4)", "interval", "CORRECT"),
    (_ineq("Abs(x - 3) > 1", ["x > log(8)/log(2)"]), "Interval.open(4, oo)", "interval", "CORRECT"),
    (_ineq("sqrt(x - 3) < 1", ["x > log(8)/log(2)"]), "Interval.open(3, 4)", "interval", "CORRECT"),
    # RK-4
    (_ineq("Abs(x - 1 - sqrt(2)) < 1", [f"x > {_R2}"]), "Interval.open(1 + sqrt(2), 2 + sqrt(2))", "interval", _NOTNO),
    (_ineq("x**2 < 16", [f"x > {_R2}"]), "Interval.open(1 + sqrt(2), 4)", "interval", _NOTNO),
    (_ineq("x < 5", ["x >= sqrt(5 + 2*sqrt(6))"]), "Interval.Ropen(sqrt(2) + sqrt(3), 5)", "interval", _NOTNO),
])
def test_round8_verdicts(ir, claim, kind, want):
    v = _run(ir, claim, kind).verdict
    assert v == want if isinstance(want, str) else v in want


@pytest.mark.parametrize("eq,claim", [("(x - 2)*atan2(x - 1, 0) = 0", "{2}"), ("atan2(x - 1, 0) = 0", "{}"),
                                      ("(x - 2)*arg(x - 1) = 0", "{2}")])
def test_round8_atan2_and_arg_at_the_origin_are_a_convention(eq, claim):
    """atan2(0, 0) and arg(0): undefined, or 0 by some conventions (certify.domain ORIGIN): the point is a
    candidate neither kept nor dropped, and no set is certified."""
    r = _run(_eq(eq), claim)
    alg = next(la for la in r.layers if la.layer == "certify.algebra")
    assert r.verdict == "UNKNOWN" and alg.evidence.get("reason") == "convention_region_candidates"
