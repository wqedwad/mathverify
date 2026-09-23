"""E10 — root/integer counting is exact and cheap (Sturm sequences, interval counting).

Measured: x^5-3x^3+x+1 has 3 real roots (count_roots == len(real_roots) == 3, ~ms).
x^2-5x-14<0 -> (-2, 7) containing 8 integers.
"""
import sympy as sp
from sympy import S, Interval, oo, Union, FiniteSet

from mathverify.certify.counting import count_real_roots, count_integers_in

x = sp.Symbol("x", real=True)


def test_raw_sturm_count_matches_real_roots():
    p = sp.Poly(x ** 5 - 3 * x ** 3 + x + 1, x)
    assert p.count_roots() == 3
    assert len(p.real_roots()) == 3


def test_raw_inequality_interval_and_count():
    iv = sp.solveset(x ** 2 - 5 * x - 14 < 0, x, S.Reals)
    assert iv == Interval.open(-2, 7)


def test_module_count_real_roots():
    assert count_real_roots(x ** 5 - 3 * x ** 3 + x + 1, x) == 3
    assert count_real_roots(x ** 2 + 1, x) == 0
    # measured: roots at x=1, x≈1.51 (positive) and one in (-2,-1)
    assert count_real_roots(x ** 5 - 3 * x ** 3 + x + 1, x, lo=0, hi=oo) == 2
    assert count_real_roots(x ** 5 - 3 * x ** 3 + x + 1, x, lo=-oo, hi=0) == 1
    assert count_real_roots((x - 1) ** 2 * (x + 2), x) == 2                    # distinct
    assert count_real_roots((x - 1) ** 2 * (x + 2), x, distinct=False) == 3     # with multiplicity


def test_module_count_integers_in_sets():
    assert count_integers_in(Interval.open(-2, 7)) == 8
    assert count_integers_in(Interval(-2, 7)) == 10
    assert count_integers_in(Interval.Lopen(-2, 7)) == 9
    assert count_integers_in(Union(Interval.open(0, 3), Interval(5, 6))) == 4
    assert count_integers_in(FiniteSet(1, 2, sp.Rational(5, 2))) == 2
    assert count_integers_in(S.EmptySet) == 0
    assert count_integers_in(Interval(0, oo)) is None    # infinite -> not a count


def test_module_count_from_inequality():
    iv = sp.solveset(x ** 2 - 5 * x - 14 < 0, x, S.Reals)
    assert count_integers_in(iv) == 8


def test_non_polynomial_rejected():
    import pytest
    with pytest.raises(ValueError):
        count_real_roots(sp.sin(x) - x / 2, x)


def test_inexact_polynomial_is_refused_not_snapped():
    """nsimplify used to snap Float coefficients to (x − 1/3)², a double root, and count 1 root
    for a polynomial whose discriminant is −4.2e-17 (no real root as written)."""
    import pytest
    e = x ** 2 - sp.Float("0.6666666666666666") * x + sp.Float("0.1111111111111111")
    assert sp.discriminant(e, x) < 0
    with pytest.raises(ValueError, match="inexact"):
        count_real_roots(e, x)
    # the verifier's own path is exact: the parser turns decimals into rationals
    exact = x ** 2 - sp.Rational("0.6666666666666666") * x + sp.Rational("0.1111111111111111")
    assert count_real_roots(exact, x) == 0
