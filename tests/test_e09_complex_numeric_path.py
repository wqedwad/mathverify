"""E9 — complex numbers / branch cuts block the symbolic path; numeric is the main path.

Measured (SymPy 1.14.0): simplify(I**I) -> I**I, expand_complex -> I**I, N(I**I) -> 0.2078795763...
"""
import sympy as sp
from sympy import I, pi, exp, sqrt

from mathverify.equiv.numeric import num_equal
from mathverify.equiv import answers_equivalent

x = sp.Symbol("x", real=True)


def test_raw_symbolic_path_stalls():
    assert sp.simplify(I ** I) == I ** I
    assert sp.expand_complex(I ** I) == I ** I
    assert abs(float(sp.N(I ** I)) - 0.207879576350762) < 1e-12


def test_numeric_equivalence_decides():
    ok, ev = num_equal(I ** I, exp(-pi / 2))
    assert ok is True
    ok, ev = num_equal(I ** I, exp(-pi / 3))
    assert ok is False


def test_complex_valued_answers_compared_numerically():
    ok, ev = answers_equivalent((1 + I) ** 8, sp.Integer(16), shape="scalar")
    assert ok is True
    ok, ev = answers_equivalent(sqrt(-4), 2 * I, shape="scalar")
    assert ok is True
    ok, ev = answers_equivalent((1 + I) / (1 - I), I, shape="scalar")
    assert ok is True
    ok, ev = answers_equivalent((1 + I) / (1 - I), -I, shape="scalar")
    assert ok is False


def test_modulus_and_argument():
    z = 1 + sqrt(3) * I
    ok, _ = answers_equivalent(sp.Abs(z), 2, shape="scalar")
    assert ok is True
    ok, _ = answers_equivalent(sp.arg(z), pi / 3, shape="scalar")
    assert ok is True
