"""E6 — limits: always compute both one-sided limits; SymPy's default is from the right.

Measured (SymPy 1.14.0): limit(|x|/x, x, 0) -> 1 (misleading); one-sided (1, -1).
limit(sin(1/x), x, 0) -> AccumBounds(-1, 1).
"""
import sympy as sp
from sympy import Abs, sin, oo, AccumBounds, exp

from mathverify.certify.limits import classify_limit

x = sp.Symbol("x", real=True)


def test_raw_default_limit_is_right_sided_and_misleading():
    assert sp.limit(Abs(x) / x, x, 0) == 1
    assert sp.limit(Abs(x) / x, x, 0, "+") == 1
    assert sp.limit(Abs(x) / x, x, 0, "-") == -1


def test_raw_oscillation_gives_accumbounds():
    assert isinstance(sp.limit(sin(1 / x), x, 0), AccumBounds)


def test_classify_dne_from_mismatched_sides():
    r = classify_limit(Abs(x) / x, x, 0)
    assert r["kind"] == "DNE"
    assert (r["right"], r["left"]) == (1, -1)


def test_classify_dne_from_oscillation():
    r = classify_limit(sin(1 / x), x, 0)
    assert r["kind"] == "DNE"


def test_classify_inf():
    r = classify_limit(1 / x ** 2, x, 0)
    assert r["kind"] == "INF"
    assert r["value"] == oo
    r = classify_limit(1 / x, x, 0)
    assert r["kind"] == "DNE"          # +oo from right, -oo from left


def test_classify_var():
    r = classify_limit((x ** 2 - 4) / (x - 2), x, 2)
    assert r["kind"] == "VAR"
    assert r["value"] == 4
    r = classify_limit(sin(3 * x) / x, x, 0)
    assert r["kind"] == "VAR" and r["value"] == 3


def test_limit_at_infinity_is_one_sided_by_nature():
    r = classify_limit((2 * x ** 2 + 1) / (x ** 2 - 5), x, oo)
    assert r["kind"] == "VAR" and r["value"] == 2
    r = classify_limit(exp(-x), x, oo)
    assert r["kind"] == "VAR" and r["value"] == 0


def test_explicit_one_sided_request():
    r = classify_limit(Abs(x) / x, x, 0, side="+")
    assert r["kind"] == "VAR" and r["value"] == 1
