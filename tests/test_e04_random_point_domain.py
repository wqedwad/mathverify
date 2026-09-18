"""E4 — random-point equivalence testing must be domain-aware; the domain comes from
the problem IR, never from the expressions.

Measured: sqrt(x^2) vs x passes 30 positive-only points; fails with negatives.
log(x^2) vs 2 log x are equal on the intersection of their own domains (x>0) but
NOT on the reals — the verdict depends on the declared domain.
"""
import random

import pytest
import sympy as sp
from sympy import S, sqrt, log, Interval, oo

from mathverify.equiv.random_point import random_point_equal

x = sp.Symbol("x", real=True)


def test_raw_positive_only_sampling_is_fooled():
    random.seed(0)
    d = sqrt(x ** 2) - x
    assert all(abs(float(d.subs(x, random.uniform(0.1, 10)))) < 1e-9 for _ in range(30))
    random.seed(0)
    assert not all(abs(float(d.subs(x, random.uniform(-10, 10)))) < 1e-9 for _ in range(30))


def test_domain_is_mandatory():
    with pytest.raises(ValueError):
        random_point_equal(sqrt(x ** 2), x, x, None)


def test_sqrt_x2_vs_x_on_positive_domain_equal():
    ok, ev = random_point_equal(sqrt(x ** 2), x, x, Interval.open(0, oo), seed=0, n=30)
    assert ok is True


def test_sqrt_x2_vs_x_on_reals_not_equal_with_counterexample():
    ok, ev = random_point_equal(sqrt(x ** 2), x, x, S.Reals, seed=0, n=30)
    assert ok is False
    assert ev["counterexample"] is not None
    assert sp.sympify(ev["counterexample"]["point"]["x"]) < 0     # samples are exact rationals


def test_log_x2_vs_2logx_depends_on_declared_domain():
    ok_pos, _ = random_point_equal(log(x ** 2), 2 * log(x), x, Interval.open(0, oo), seed=1)
    assert ok_pos is True
    ok_real, ev = random_point_equal(log(x ** 2), 2 * log(x), x, S.Reals, seed=1)
    assert ok_real is False      # 2 log x is undefined / complex for x<0


def test_deterministic_under_seed():
    a, _ = random_point_equal(sqrt(x ** 2), x, x, S.Reals, seed=7)
    b, ev = random_point_equal(sqrt(x ** 2), x, x, S.Reals, seed=7)
    assert a == b
    assert ev["seed"] == 7


def test_integer_domain_sampling():
    n = sp.Symbol("n", integer=True)
    ok, ev = random_point_equal(sp.Mod(n ** 2, 2), sp.Mod(n, 2), n, S.Integers, seed=3)
    assert ok is True
