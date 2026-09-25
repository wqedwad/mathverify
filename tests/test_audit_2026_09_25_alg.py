"""Audit of 25 Sep 2026 (algebra / counting / equivalence area): regression tests.

Every case below was measured on master before the fix; the comment on each group gives the
verdict that was observed then. The contract is the one of CLAUDE.md principles 2–5: a wrong
answer is never CORRECT, and where a check cannot be made sound the verifier abstains.
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.verifier import verify


def _v(kind, params, claim_kind, payload, givens=(), vars_=None, steps=(), functions=None,
       options=None, option=None, dod=None):
    ir = {"task": {"kind": kind, "params": params},
          "vars": vars_ if vars_ is not None else [{"name": "x"}], "givens": list(givens)}
    if functions:
        ir["functions"] = functions
    if options:
        ir["options"] = options
    if dod is not None:
        ir["domain_of_discourse"] = dod
    ca = {"kind": claim_kind, "payload": payload}
    if option:
        ca["option"] = option
    return verify(ir, {"claimed_answer": ca, "steps": list(steps)}).verdict


def _step(i, kind, claim):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": [], "text": ""}


def _solve(eq, payload, **kw):
    return _v("solve_equation", {"var": "x"}, "set", payload, givens=[eq], **kw)


def _ineq(q, payload, kind="interval", **kw):
    return _v("solve_inequality", {"var": "x"}, kind, payload, givens=[q], **kw)


def _eval(expr, payload, **kw):
    return _v("evaluate", {"expr": expr}, "value", payload, vars_=kw.pop("vars_", []), **kw)


# ---------------------------------------------------------------------------------------------
# C3 — a relation at a point where one side is EXACTLY zero was decided by rounding noise.
# Before: √(x²−2x−1) = 0 → ∅ was CORRECT; the right interval answers below were INCORRECT; the
# false step `x² − 2x − 1 < 0` was verified and the true step `≥ 0` refuted.
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("eq", ["sqrt(x**2 - 2*x - 1) = 0", "sqrt(x**2 + x - 1) = 0",
                                "(x**2 - 2*x - 1)**(1/4) = 0"])
def test_c3_radicand_zero_roots_are_not_dropped(eq):
    assert _solve(eq, "{}") == "INCORRECT"


def test_c3_radicand_zero_roots_right_answer():
    assert _solve("sqrt(x**2 - 2*x - 1) = 0", "{1 - sqrt(2), 1 + sqrt(2)}") == "CORRECT"


@pytest.mark.parametrize("q,ans", [
    ("x**2 - 2*x - 1 < 0", "(1 - sqrt(2), 1 + sqrt(2))"),
    ("x**2 - x - 1 < 0", "((1 - sqrt(5))/2, (1 + sqrt(5))/2)"),
    ("x**2 - 4*x - 1 < 0", "(2 - sqrt(5), 2 + sqrt(5))"),
    ("x**2 - 2*x - 1 >= 0", "(-oo, 1 - sqrt(2)] U [1 + sqrt(2), oo)"),
])
def test_c3_irrational_endpoints_right_answers_are_not_refuted(q, ans):
    assert _ineq(q, ans) == "CORRECT"


def test_c3_step_sign_at_exact_zero():
    bad = [_step(1, "eq", "x**2 - 2*x - 1 < 0"), _step(2, "eq", "x in {1 - sqrt(2), 1 + sqrt(2)}")]
    good = [_step(1, "eq", "x**2 - 2*x - 1 >= 0"), _step(2, "eq", "x in {1 - sqrt(2), 1 + sqrt(2)}")]
    assert _solve("x**2 - 2*x - 1 = 0", "{1 - sqrt(2), 1 + sqrt(2)}", steps=bad) == "INCORRECT"
    assert _solve("x**2 - 2*x - 1 = 0", "{1 - sqrt(2), 1 + sqrt(2)}", steps=good) == "CORRECT"


def test_c3_certified_sign_primitive():
    from mathverify.equiv.numeric import certified_sign, NONREAL
    r2 = sp.sqrt(2)
    assert certified_sign((1 + r2) ** 2 - 2 * (1 + r2) - 1) == 0
    assert certified_sign(sp.sqrt(10 ** 100 + 1) - 10 ** 50) == 1
    assert certified_sign(sp.tanh(100) - 1) == -1
    assert certified_sign(sp.sqrt(-4)) == NONREAL
    assert certified_sign(sp.log(8) / sp.log(2) - 3) == 0


# ---------------------------------------------------------------------------------------------
# C8 — the 80-digit rung accepted any relative gap below 1e-70 as equality. Before: all CORRECT.
# ---------------------------------------------------------------------------------------------
_PI75 = "3.14159265358979323846264338327950288419716939937510582097494459230781640629"


@pytest.mark.parametrize("expr,claim", [
    ("sqrt(10**100 + 1)", "10**50"), ("tanh(100)", "1"), ("atan(10**80)", "pi/2"),
    ("10**80*pi", "10**80*pi + 1"), ("pi", _PI75), ("log(10**100 + 1)", "100*log(10)"),
])
def test_c8_close_is_not_equal(expr, claim):
    assert _eval(expr, claim) != "CORRECT"


def test_c8_close_roots_and_endpoints():
    assert _solve("x**2 = 2", "{-sqrt(2), sqrt(2) + 10**(-80)}") != "CORRECT"
    assert _ineq("x**2 < 2", "(-sqrt(2), sqrt(2) + 10**(-80))") != "CORRECT"
    assert _v("domain_of", {"expr": "sqrt(2 - x**2)", "var": "x"}, "interval",
              "[-sqrt(2), sqrt(2) - 10**(-80)]") != "CORRECT"


def test_c8_compute_step_close_is_not_equal():
    st = [_step(1, "compute", "sqrt(10**100 + 1) = 10**50")]
    assert _solve("x**2 - 5*x + 6 = 0", "{2, 3}", steps=st) != "CORRECT"


def test_c8_exact_equalities_still_proved():
    from mathverify.equiv.numeric import num_equal
    assert num_equal(sp.cos(sp.pi / 5), (1 + sp.sqrt(5)) / 4)[0] is True
    assert num_equal(sp.log(8) / sp.log(2), 3)[0] is True
    assert num_equal(sp.sqrt(10 ** 100 + 1), 10 ** 50)[0] is False
    assert _eval("sqrt(5 + 2*sqrt(6))", "sqrt(2) + sqrt(3)") == "CORRECT"


# ---------------------------------------------------------------------------------------------
# C10 — odd roots are REAL roots (∛(−8) = −2), consistently with definedness and z3.
# Before: x^(1/3) + 2 = 0 → ∅ CORRECT; ∛(−8) = −2 and x^(1/3) < 1 ⇔ x < 1 INCORRECT.
# ---------------------------------------------------------------------------------------------
def test_c10_real_cube_root():
    assert _solve("x**(1/3) + 2 = 0", "{}") != "CORRECT"
    assert _eval("cbrt(-8)", "-2") == "CORRECT"
    assert _eval("root(-27, 3)", "-3") == "CORRECT"
    assert _ineq("x**(1/3) < 1", "(-oo, 1)") == "CORRECT"
    assert _ineq("x**(1/3) < 1", "[0, 1)") != "CORRECT"
    assert _ineq("cbrt(x) < -1", "(-oo, -1)") != "INCORRECT"


# ---------------------------------------------------------------------------------------------
# C1 — count_roots ignored the written definedness and counted 0 roots of the zero polynomial.
# Before: x³/x "has 1 root" CORRECT (and 0 INCORRECT); (x+2)²/(x+2) → 1, √x² + 1 → 1 CORRECT;
# (x+1)² − x² − 2x − 1 "has 0 roots" CORRECT.
# ---------------------------------------------------------------------------------------------
def _roots(expr, n, **params):
    return _v("count_roots", dict({"expr": expr, "var": "x"}, **params), "count", n)


@pytest.mark.parametrize("expr,wrong,right", [
    ("x**3/x", 1, 0), ("(x + 2)**2/(x + 2)", 1, 0), ("sqrt(x)**2 + 1", 1, 0),
    ("x**2*(x - 1)/x", 2, 1), ("(x**2 - 1)/(x - 1)", 2, 1),
])
def test_c1_roots_where_the_written_expression_is_undefined_do_not_count(expr, wrong, right):
    assert _roots(expr, wrong) == "INCORRECT"
    assert _roots(expr, right) == "CORRECT"


def test_c1_identically_zero_expression_is_not_zero_roots():
    assert _roots("(x + 1)**2 - x**2 - 2*x - 1", 0) != "CORRECT"
    assert _roots("x/x - 1", 0) != "CORRECT"


def test_c1_multiplicity_and_interval_still_exact():
    assert _roots("(x - 1)**2*(x + 1)", 2) == "CORRECT"
    assert _roots("(x - 1)**2*(x + 1)", 3, distinct=False) == "CORRECT"
    assert _roots("x**2 - 1", 1, lo="0", hi="oo") == "CORRECT"
    assert _roots("x**5 - 3*x**3 + x + 1", 3) == "CORRECT"


def test_c1_count_real_roots_refuses_zero_polynomial():
    from mathverify.certify.counting import count_real_roots
    x = sp.Symbol("x", real=True)
    with pytest.raises(ValueError, match="identically zero"):
        count_real_roots(sp.expand((x + 1) ** 2 - x ** 2 - 2 * x - 1), x)


# ---------------------------------------------------------------------------------------------
# C4 — count_solutions evaluated the givens in floating point. Before: 1/x + 1/y = 1/6 on 1..50
# counted 7 (truth 9), x/10 + y/10 = 3/10 counted 0 (truth 4), √x + √y = √18 counted 2 (truth 4).
# ---------------------------------------------------------------------------------------------
def _sols(givens, bounds, n, dom="nonneg_integer"):
    return _v("count_solutions", {"bounds": bounds}, "count", n, givens=givens,
              vars_=[{"name": k, "domain": dom} for k in bounds])


@pytest.mark.parametrize("givens,bounds,truth,wrong", [
    (["1/x + 1/y = 1/6"], {"x": ["1", "50"], "y": ["1", "50"]}, 9, 7),
    (["x/10 + y/10 = 3/10"], {"x": ["0", "3"], "y": ["0", "3"]}, 4, 0),
    (["0.1*x + 0.2*y = 0.3"], {"x": ["0", "5"], "y": ["0", "5"]}, 2, 1),
    (["sqrt(x) + sqrt(y) = sqrt(18)"], {"x": ["0", "18"], "y": ["0", "18"]}, 4, 2),
    (["1/x + 1/y + 1/z = 1"], {"x": ["1", "10"], "y": ["1", "10"], "z": ["1", "10"]}, 10, 8),
])
def test_c4_count_solutions_is_exact(givens, bounds, truth, wrong):
    assert _sols(givens, bounds, truth) == "CORRECT"
    assert _sols(givens, bounds, wrong) == "INCORRECT"


def test_c4_real_cube_root_in_count_solutions():
    # was a caught TypeError (complex <= int); ∛x ≤ 1 on −5..5 holds for x ≤ 1: 7 integers
    assert _sols(["cbrt(x) <= 1"], {"x": ["-5", "5"]}, 7, dom="integer") == "CORRECT"


# ---------------------------------------------------------------------------------------------
# C5 — count_integers: integrality and open endpoints decided exactly. Before: x·log 2 = log 8
# → 0 CORRECT (truth 1), |x| < log 8/log 2 → 7 CORRECT (truth 5).
# ---------------------------------------------------------------------------------------------
def _ints(givens, n, dom="integer"):
    return _v("count_integers", {"var": "x"}, "count", n, givens=givens,
              vars_=[{"name": "x", "domain": dom}])


@pytest.mark.parametrize("givens,truth,wrong,dom", [
    (["x*log(2) = log(8)"], 1, 0, "integer"),
    (["Abs(x) < log(8)/log(2)"], 5, 7, "integer"),
    (["x*log(2) < log(8)"], 3, 4, "nonneg_integer"),
    (["x/x + x**2 <= 5"], 4, 5, "integer"),
    (["(x - 2)*(x - 5) > 0", "x < 9", "x > -4"], 8, 10, "integer"),
    (["Abs(x - 3) > 1", "x < 10"], 6, 7, "positive_integer"),
])
def test_c5_count_integers_exact(givens, truth, wrong, dom):
    assert _ints(givens, truth, dom) == "CORRECT"
    assert _ints(givens, wrong, dom) == "INCORRECT"
