"""E3 — numeric integration must detect breakpoints/singularities; fixed absolute
tolerance produces false negatives.

Measured (mpmath 1.3.0): naive quad on ln x/sqrt x over [0,1] gives 8 digits;
tanh-sinh at dps=40 gives -4.0. |x-1|+|x+2| over [-3,3] naive gives 22.99946 (4 digits);
with breakpoints [-3,-2,1,3] gives 23.0.
"""
import mpmath as mp
import sympy as sp
from sympy import log, sqrt, Abs, Rational

from mathverify.certify.calculus import definite_integral_numeric, find_breakpoints
from mathverify.equiv.numeric import num_equal

x = sp.Symbol("x", real=True)


def test_raw_naive_quad_only_8_digits_on_log_singularity():
    mp.mp.dps = 15
    v = mp.quad(lambda u: mp.log(u) / mp.sqrt(u), [0, 1])
    assert abs(v + 4) > 1e-9          # NOT accurate to 1e-12
    assert abs(v + 4) < 1e-7


def test_raw_naive_quad_only_4_digits_on_abs_kinks():
    mp.mp.dps = 15
    v = mp.quad(lambda u: abs(u - 1) + abs(u + 2), [-3, 3])
    assert abs(v - 23) > 1e-4
    assert abs(v - 23) < 1e-2


def test_raw_breakpoints_fix_abs_integral():
    mp.mp.dps = 15
    v = mp.quad(lambda u: abs(u - 1) + abs(u + 2), [-3, -2, 1, 3])
    assert abs(v - 23) < 1e-12


def test_breakpoints_detected_for_abs():
    pts = find_breakpoints(Abs(x - 1) + Abs(x + 2), x, -3, 3)
    assert set(pts) == {-2, 1}


def test_module_integral_abs_exact_to_many_digits():
    val, ev = definite_integral_numeric(Abs(x - 1) + Abs(x + 2), x, -3, 3)
    assert num_equal(val, 23, rel_tol=1e-20)[0] is True
    assert ev["breakpoints"] == [-2, 1]


def test_module_integral_log_singularity():
    val, ev = definite_integral_numeric(log(x) / sqrt(x), x, 0, 1)
    assert num_equal(val, -4, rel_tol=1e-20)[0] is True


def test_module_rejects_wrong_value():
    val, ev = definite_integral_numeric(Abs(x - 1) + Abs(x + 2), x, -3, 3)
    assert num_equal(val, 22, rel_tol=1e-12)[0] is False


def test_relative_tolerance_not_fixed_1e12():
    # a true value of 1e6*pi compared to 1e6*pi computed at 15 digits must still pass
    a = sp.Float("3141592.6535897932", 17)
    assert num_equal(a, 10 ** 6 * sp.pi, rel_tol=1e-12)[0] is True
    # and a genuinely different value must fail
    assert num_equal(a, 10 ** 6 * sp.pi + Rational(1, 1000), rel_tol=1e-12)[0] is False
