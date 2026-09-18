"""E8 — the integration-constant problem is solved automatically by the derivative
certificate: d/dx F - integrand == 0 accepts F + C for any constant C.
"""
import sympy as sp
from sympy import log, sin, cos, exp

from mathverify.certify.calculus import antiderivative_certificate

x = sp.Symbol("x", real=True)


def test_raw_derivative_differences():
    assert sp.simplify(sp.diff(x * log(x) - x, x) - log(x)) == 0
    assert sp.simplify(sp.diff(x * log(x), x) - log(x)) == 1
    assert sp.simplify(sp.diff(x * log(x) - x + 7, x) - log(x)) == 0


def test_correct_antiderivative_passes():
    ok, ev = antiderivative_certificate(x * log(x) - x, log(x), x)
    assert ok is True


def test_wrong_antiderivative_fails_with_nonzero_residual():
    ok, ev = antiderivative_certificate(x * log(x), log(x), x)
    assert ok is False
    assert ev["residual"] == 1


def test_constant_shift_is_not_an_error():
    ok, ev = antiderivative_certificate(x * log(x) - x + 7, log(x), x)
    assert ok is True
    C = sp.Symbol("C")
    ok, ev = antiderivative_certificate(x * log(x) - x + C, log(x), x)
    assert ok is True


def test_equivalent_forms_pass():
    # sin^2 x  vs  -cos^2 x  vs  -cos(2x)/2  are all antiderivatives of sin(2x)
    for F in (sin(x) ** 2, -cos(x) ** 2, -cos(2 * x) / 2):
        ok, ev = antiderivative_certificate(F, sin(2 * x), x)
        assert ok is True, F


def test_chain_rule_omission_is_caught():
    # claimed ∫ e^{2x} dx = e^{2x}  (missing 1/2)
    ok, ev = antiderivative_certificate(exp(2 * x), exp(2 * x), x)
    assert ok is False
