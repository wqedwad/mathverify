"""A verdict does not depend on what an earlier verify asked SymPy (16 Oct 2026; DECISIONS §90).

SymPy 1.14's Mul._eval_is_even said False for an unevaluated 0*x (a reading as written builds such products), so
asking is_even first made the cached 0*x nonzero; `_sympy_guards` answers it as 0's."""
import pytest
import sympy as sp

from mathverify._sympy_guards import install

install()                                   # idempotent: importing mathverify installs the guards already

x = sp.Symbol("x", real=True)
n = sp.Symbol("n", integer=True)
z = sp.Symbol("z")


@pytest.mark.parametrize("f", [x, n, sp.log(sp.Symbol("p", positive=True)), sp.sin(x)])
def test_a_written_zero_product_stays_zero_whatever_is_asked_first(f):
    sp.core.cache.clear_cache()
    m = sp.Mul(0, f, evaluate=False)
    assert m.is_even is True
    assert m.is_zero is True and m.is_odd is not True


def test_a_zero_product_with_a_factor_that_may_be_infinite_is_not_decided():
    sp.core.cache.clear_cache()
    assert sp.Mul(0, z, evaluate=False).is_even is None
    assert sp.Mul(0, sp.oo, evaluate=False).is_even is None


def test_an_evaluated_product_keeps_sympys_answer():
    assert (2 * n).is_even is True and (n + 1).is_even is None and sp.Mul(3, 5).is_even is False
    sp.core.cache.clear_cache()
    assert sp.Mul(3, 5, evaluate=False).is_even is False and (n * x).is_even is None
