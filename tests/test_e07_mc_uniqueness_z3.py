"""E7 — multiple-choice uniqueness certificate with z3.

Measured: a+b=30 ∧ 2a+4b=88 ∧ a,b>0 -> sat (a=16,b=14); ∧ a≠16 -> unsat.
Interpretation: exactly 1 option sat -> certified; >=2 sat -> IR incomplete;
0 sat -> IR wrong or inconsistent question -> UNKNOWN + flag.
"""
import sympy as sp
import z3

from mathverify.certify.wordproblem import uniqueness_certificate

a, b = sp.symbols("a b", real=True)
GIVENS = [sp.Eq(a + b, 30), sp.Eq(2 * a + 4 * b, 88), a > 0, b > 0]
SYMS = {"a": "real", "b": "real"}


def test_raw_z3_sat_then_unsat():
    za, zb = z3.Reals("a b")
    s = z3.Solver()
    s.add(za + zb == 30, 2 * za + 4 * zb == 88, za > 0, zb > 0)
    assert s.check() == z3.sat
    m = s.model()
    assert m[za] == 16 and m[zb] == 14
    s.add(za != 16)
    assert s.check() == z3.unsat


def test_unique_option_certified():
    opts = {"A": sp.Integer(12), "B": sp.Integer(14), "C": sp.Integer(16), "D": sp.Integer(18), "E": sp.Integer(20)}
    r = uniqueness_certificate(GIVENS, a, SYMS, claimed_value=sp.Integer(16), options=opts)
    assert r["status"] == "certified"
    assert r["sat_options"] == ["C"]
    assert r["claim_sat"] is True and r["other_unsat"] is True


def test_wrong_claim_is_refuted():
    opts = {"A": sp.Integer(12), "B": sp.Integer(14), "C": sp.Integer(16), "D": sp.Integer(18), "E": sp.Integer(20)}
    r = uniqueness_certificate(GIVENS, a, SYMS, claimed_value=sp.Integer(14), options=opts)
    assert r["status"] == "refuted"
    assert r["claim_sat"] is False
    assert r["sat_options"] == ["C"]


def test_incomplete_ir_two_options_sat_is_flagged():
    givens = [sp.Eq(a + b, 30), a > 0, b > 0]      # missing constraint
    opts = {"A": sp.Integer(12), "B": sp.Integer(14), "C": sp.Integer(16)}
    r = uniqueness_certificate(givens, a, SYMS, claimed_value=sp.Integer(16), options=opts)
    assert r["status"] == "ir_incomplete"
    assert len(r["sat_options"]) >= 2


def test_inconsistent_question_zero_sat_is_flagged():
    givens = [sp.Eq(a + b, 30), sp.Eq(a + b, 31)]
    opts = {"A": sp.Integer(12), "B": sp.Integer(14)}
    r = uniqueness_certificate(givens, a, SYMS, claimed_value=sp.Integer(12), options=opts)
    assert r["status"] == "ir_inconsistent"


def test_open_ended_uniqueness_without_options():
    r = uniqueness_certificate(GIVENS, a, SYMS, claimed_value=sp.Integer(16), options=None)
    assert r["status"] == "certified"
    r = uniqueness_certificate(GIVENS, a, SYMS, claimed_value=sp.Integer(15), options=None)
    assert r["status"] == "refuted"


def test_integer_domain_matters():
    # x + y = 5, x*y = 6 over integers -> {2,3}; target x+y^2 ... use target x with claim 2 or 3 -> not unique
    xx, yy = sp.symbols("x y", integer=True)
    givens = [sp.Eq(xx + yy, 5), sp.Eq(xx * yy, 6), xx < yy]
    r = uniqueness_certificate(givens, xx, {"x": "int", "y": "int"}, claimed_value=sp.Integer(2), options=None)
    assert r["status"] == "certified"
