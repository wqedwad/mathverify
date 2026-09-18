"""E5 — extremum certificates are two-sided: the candidate must be attained AND
nothing better may exist ({f > claim} on the interval is empty).
"""
import sympy as sp
from sympy import S, Interval

from mathverify.certify.extremum import certify_extremum

x = sp.Symbol("x", real=True)
f = x ** 3 - 3 * x


def test_raw_candidates_and_emptiness():
    crit = [c for c in sp.solve(sp.diff(f, x), x) if -2 <= c <= 3]
    vals = {p: f.subs(x, p) for p in crit + [-2, 3]}
    assert max(vals.values()) == 18
    assert sp.solveset(f > 18, x, Interval(-2, 3)) == S.EmptySet


def test_max_18_certified():
    ok, ev = certify_extremum(f, x, Interval(-2, 3), "max", 18)
    assert ok is True
    assert ev["attained_at"] == [3]
    assert ev["superlevel_empty"] is True


def test_local_max_2_is_rejected_as_global_max():
    ok, ev = certify_extremum(f, x, Interval(-2, 3), "max", 2)
    assert ok is False
    assert ev["reason"] == "better_value_exists"


def test_unattained_value_is_rejected():
    ok, ev = certify_extremum(f, x, Interval(-2, 3), "max", 20)
    assert ok is False
    assert ev["reason"] == "not_attained"


def test_min_certified():
    ok, ev = certify_extremum(f, x, Interval(-2, 3), "min", -2)
    assert ok is True
    assert set(ev["attained_at"]) == {-2, 1}


def test_open_interval_supremum_not_attained_is_unknown_or_false():
    # f(x)=x on (0,1): no maximum; a claim "max = 1" must not be certified
    ok, ev = certify_extremum(x, x, Interval.open(0, 1), "max", 1)
    assert ok is not True


def test_argument_of_extremum():
    ok, ev = certify_extremum(f, x, Interval(-2, 3), "argmax", 3)
    assert ok is True
    ok, ev = certify_extremum(f, x, Interval(-2, 3), "argmin", -2)
    assert ok is not True  # min is attained at both -2 and 1; single arg claim incomplete
