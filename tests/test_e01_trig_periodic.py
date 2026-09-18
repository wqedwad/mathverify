"""E1 — SymPy cannot decide equality of infinite trig solution sets.

Measured (SymPy 1.14.0): solveset(cos(2x)=1/2, Reals) is a Union of ImageSets;
`== candidate` is False (structural), `is_subset` is None (undecided).
Rule: reduce to one period and compare finite sets.
"""
import sympy as sp
from sympy import S, cos, pi, Union, ImageSet, Lambda, Interval, FiniteSet, Mod, Eq

from mathverify.certify.trig import periodic_solution_set_equal, detect_period

x = sp.Symbol("x", real=True)
n = sp.Symbol("n", integer=True)


def _candidate():
    return Union(ImageSet(Lambda(n, n * pi + pi / 6), S.Integers),
                 ImageSet(Lambda(n, n * pi - pi / 6), S.Integers))


def test_raw_library_trap_structural_eq_is_false():
    ss = sp.solveset(Eq(cos(2 * x), S.Half), x, S.Reals)
    assert isinstance(ss, Union)
    assert (ss == _candidate()) is False          # structural comparison, not set equality


def test_raw_library_trap_is_subset_is_undecided_or_hash_dependent():
    """Handoff measured None. Our measurement (SymPy 1.14.0, Python 3.14): the result
    depends on PYTHONHASHSEED — seeds 0,1,2,4,5 -> None; seeds 3,6,7 -> True. It is
    never False, but it is not a reliable decision procedure (docs/E1-E10-measurement.md)."""
    ss = sp.solveset(Eq(cos(2 * x), S.Half), x, S.Reals)
    r = ss.is_subset(_candidate())
    assert r in (None, True)
    assert _candidate().is_subset(ss) is None     # reverse direction: undecided in all seeds


def test_period_detection():
    assert detect_period(cos(2 * x), x) == pi
    assert detect_period(sp.sin(x) + sp.cos(3 * x), x) == 2 * pi
    assert detect_period(sp.tan(x / 2), x) == 2 * pi


def test_window_reduction_both_sides_give_pi6_5pi6():
    ok, ev = periodic_solution_set_equal(Eq(cos(2 * x), S.Half), x, _candidate())
    assert ok is True
    assert ev["period"] == pi
    assert FiniteSet(*ev["true_window"]) == FiniteSet(pi / 6, 5 * pi / 6)
    assert FiniteSet(*ev["candidate_window"]) == FiniteSet(pi / 6, 5 * pi / 6)


def test_wrong_candidate_is_rejected():
    bad = Union(ImageSet(Lambda(n, n * pi + pi / 3), S.Integers),
                ImageSet(Lambda(n, n * pi - pi / 3), S.Integers))
    ok, ev = periodic_solution_set_equal(Eq(cos(2 * x), S.Half), x, bad)
    assert ok is False


def test_candidate_missing_a_branch_is_rejected():
    partial = ImageSet(Lambda(n, n * pi + pi / 6), S.Integers)
    ok, ev = periodic_solution_set_equal(Eq(cos(2 * x), S.Half), x, partial)
    assert ok is False


def test_candidate_written_with_2pi_period_still_accepted():
    # x = pi/6 + 2k*pi, 5pi/6 + 2k*pi, 7pi/6 + 2k*pi, 11pi/6 + 2k*pi  (same set, coarser period)
    cand = Union(*[ImageSet(Lambda(n, 2 * n * pi + c), S.Integers)
                   for c in (pi / 6, 5 * pi / 6, 7 * pi / 6, 11 * pi / 6)])
    ok, ev = periodic_solution_set_equal(Eq(cos(2 * x), S.Half), x, cand)
    assert ok is True


def test_finite_interval_solution_set():
    # on [0, 2pi): {pi/6, 5pi/6, 7pi/6, 11pi/6}
    ok, ev = periodic_solution_set_equal(Eq(cos(2 * x), S.Half), x,
                                         FiniteSet(pi / 6, 5 * pi / 6, 7 * pi / 6, 11 * pi / 6),
                                         window=Interval.Ropen(0, 2 * pi))
    assert ok is True
    ok, ev = periodic_solution_set_equal(Eq(cos(2 * x), S.Half), x,
                                         FiniteSet(pi / 6, 5 * pi / 6),
                                         window=Interval.Ropen(0, 2 * pi))
    assert ok is False
