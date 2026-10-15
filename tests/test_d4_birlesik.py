"""Merged state of the fourth audit's fixes (A+, 15 Oct 2026; DECISIONS §89): interactions of the parts.

d4b round 10 trusts strict evalf only on the nodes SymPy tracks the accuracy of, and d4c round 3 checks each significant
reading again at a higher precision. Merged, asin(tanh x) at a large x had no sign (tanh x within the working precision
of 1), and the true identity asin(tanh x) = atan(sinh x) on x > 0 fell to UNKNOWN. The sign of an odd increasing function
of a real argument is the argument's sign (exact facts, `numeric._monotone_sign`)."""
import pytest
import sympy as sp

from mathverify.equiv import numeric
from mathverify.equiv.numeric import NONREAL, certified_sign
from mathverify.equiv.random_point import random_point_equal

C = sp.Rational(982817908, 1000033)                     # tanh C = 1 - 2e-854
Q = sp.log(6) - sp.log(2) - sp.log(3)                   # exactly 0
x = sp.Symbol("x", real=True)


@pytest.mark.parametrize("e, s", [
    (sp.asin(sp.tanh(C)), 1), (sp.asin(sp.tanh(-C)), -1), (sp.acos(sp.tanh(C)), 1), (sp.atanh(sp.tanh(C)), 1),
    (sp.erf(C), 1), (sp.erf(-C), -1), (sp.sinh(C), 1), (sp.cosh(-C), 1), (-2 * sp.pi * sp.asin(sp.tanh(C)), -1),
    (sp.asin(Q), 0), (sp.sinh(Q), 0), (sp.asin(sp.tanh(Q)), 0), (Q * sp.pi, 0),
])
def test_monotone_functions_take_their_arguments_sign(e, s):
    assert certified_sign(e) == s


def test_monotone_rule_reads_nothing_off_a_domain_it_cannot_prove():
    assert numeric._monotone_sign(sp.asin(2), 5.0) is None and certified_sign(sp.asin(2)) == NONREAL
    assert numeric._monotone_sign(sp.atanh(sp.cos(0, evaluate=False)), 5.0) is None    # cos 0 = 1: not inside (-1, 1)
    assert numeric._monotone_sign(sp.acos(sp.cos(sp.Rational(1, 7)) / 3), 5.0) == 1     # |cos(1/7)/3| < 1, certified
    assert numeric._monotone_sign(sp.I * sp.pi, 5.0) is None                               # a nonreal factor: no product


def test_the_gudermann_identity_holds_on_the_positive_reals():
    ok, ev = random_point_equal(sp.asin(sp.tanh(x)), sp.atan(sp.sinh(x)), x, sp.Interval.open(0, sp.oo))
    assert ok is True, ev
    ok, ev = random_point_equal(sp.asin(sp.tanh(x)), sp.atan(sp.sinh(x)) + sp.Rational(1, 10**30), x,
                                sp.Interval.open(0, sp.oo))
    assert ok is False
