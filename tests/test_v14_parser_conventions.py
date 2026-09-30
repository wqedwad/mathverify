"""V14 (30 Sep 2026): the parser's conventions that decided a different question than the one written.

(a) gcd/lcm were SymPy's POLYNOMIAL operations: lcm(n, 2) = 2n, gcd(n, 2) = 1 for an integer n, and a
    third argument was a polynomial generator (lcm(4, 6, 10) = 12, true 60).
(b) arccot was SymPy's acot, range (-pi/2, pi/2]; the curriculum's is (0, pi): arccot(-1) = 3pi/4.
(c) a bound variable (Sum index, Integral/Limit variable, at/Subs point, ConditionSet variable, a
    problem function's argument) took the assumptions of the IR variable it is named after:
    with k > 0, Sum(0**k, (k, 0, n)) was 0; with x > 0, the integral of sqrt(x**2) over [-1, 1] was 0.
    The certificates that bind the task's variable themselves had the same leak, and the Lean series
    template proved the false "sum of |k| over -2..2 = 0".
(d) SymPy compares two endpoints by VALUE when ordering them but by STRUCTURE when testing equality,
    so (-oo, R) U (3, oo) with R = sqrt(11 + 6*sqrt(2)) - sqrt(2) (= 3) became the whole line.
Measured on the code before the change (35af293): 77 of these 93 tests fail; the other 16 are controls
(values both conventions agree on, verdicts that were already right).
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.normalize.parse import (ParseError, _SAFE_NAMES, parse_as_written,
                                        parse_expr_str, parse_set_str)
from mathverify.verifier import verify


def _ns(**syms):
    return dict(_SAFE_NAMES, **syms)


K = sp.Symbol("k", integer=True, positive=True)
N = sp.Symbol("n", integer=True, positive=True)
XP = sp.Symbol("x", real=True, positive=True)
XR = sp.Symbol("x", real=True)


def _ir(kind, params, vars_=(), givens=(), shape="scalar", options=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if options:
        d["options"] = options
    return d


def _sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [dict(s, text=s.get("text", "")) for s in steps]}


def _verdict(ir, sol):
    return verify(ir, sol).verdict


def _step(i, kind, claim, frm=()):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": list(frm)}


# ---------------------------------------------------------------------------- (a) gcd / lcm
@pytest.mark.parametrize("text,value", [
    ("lcm(4, 6, 10)", 60), ("gcd(12, 18, 4)", 2), ("gcd(8, 12, 20, 6)", 2), ("lcm(2, 3, 5, 7)", 210),
    ("gcd(84, 120)", 12), ("lcm(4, 6)", 12), ("gcd(-4, 6)", 2), ("lcm(-4, 6)", 12), ("lcm(0, 5)", 0),
    ("igcd(12, 18)", 6), (r"\gcd(84, 120)", 12), (r"\operatorname{lcm}(4, 6, 10)", 60)])
def test_integer_gcd_lcm_values(text, value):
    assert parse_expr_str(text, _ns()) == value


@pytest.mark.parametrize("text", ["gcd(n, 2)", "lcm(n, 2)", "igcd(n, 2)", r"\gcd(n, 2)", r"\operatorname{lcm}(n, 2)"])
def test_gcd_lcm_of_a_symbol_has_no_value_until_it_is_substituted(text):
    e = parse_expr_str(text, _ns(n=N))
    assert e.free_symbols == {N} and e not in (1, 2 * N)
    assert e.subs(N, 6) in (2, 6)
    assert e.subs(N, 7) in (1, 14)


def test_gcd_of_non_integers_stays_unevaluated_and_is_not_a_value():
    # sharp's convention (DECISIONS §72, tests/test_parse_conventions.py): fractions take the school
    # rule gcd(a/b, c/d) = gcd(a, c)/lcm(b, d); only a number that is not rational has no value
    from mathverify.equiv.numeric import certified_sign, num_equal
    e = parse_expr_str("gcd(1/2, 1/3)", _ns())
    assert e == sp.Rational(1, 6) and certified_sign(e) == 1 and num_equal(e, sp.Rational(1, 6))[0] is True
    w = parse_as_written("gcd(1/2, 1/3)", _ns())
    assert len(w) == 1 and type(w[0]).__name__ == "gcd"            # was (1,): the written form disagreed
    p = parse_expr_str("gcd(pi, 2)", _ns())
    assert type(p).__name__ == "gcd" and certified_sign(p) is None
    with pytest.raises(ParseError):                 # the integer spelling takes no fraction rule
        parse_expr_str("igcd(1/2, 1/3)", _ns())


def test_random_points_never_refute_a_true_gcd_identity():
    from mathverify.equiv.random_point import random_point_equal
    gcd, lcm = _SAFE_NAMES["gcd"], _SAFE_NAMES["lcm"]
    n, x = sp.Symbol("n", integer=True), sp.Symbol("x", real=True)
    assert random_point_equal(gcd(n, 2) * lcm(n, 2), 2 * sp.Abs(n), n, sp.S.Integers)[0] is not False
    # sharp: gcd/lcm have values on the rationals, where gcd(x, 2)*lcm(x, 2) = 2|x|; 2x is refuted at a
    # negative rational (a true counterexample), the true identity 2|x| is not
    assert random_point_equal(gcd(x, 2) * lcm(x, 2), 2 * x, x, sp.S.Reals)[0] is False
    assert random_point_equal(gcd(x, 2) * lcm(x, 2), 2 * sp.Abs(x), x, sp.S.Reals)[0] is not False
    assert random_point_equal(gcd(n, 2), 1, n, sp.S.Integers)[0] is False      # n = 2 is a counterexample


N6 = dict(vars_=[{"name": "n", "domain": "positive_integer"}], givens=["n = 6"])


@pytest.mark.parametrize("ir,claim,verdict", [
    (_ir("evaluate", {"expr": "lcm(4, 6, 10)"}), "60", "CORRECT"),
    (_ir("evaluate", {"expr": "lcm(4, 6, 10)"}), "12", "INCORRECT"),
    (_ir("evaluate", {"expr": "gcd(12, 18, 4)"}), "6", "INCORRECT"),
    (_ir("evaluate", {"expr": "lcm(n, 4)"}, **N6), "12", "CORRECT"),
    (_ir("evaluate", {"expr": "lcm(n, 4)"}, **N6), "24", "INCORRECT"),
    (_ir("evaluate", {"expr": "gcd(n, 4)"}, **N6), "1", "INCORRECT"),
    (_ir("evaluate", {"expr": r"\gcd(n, 4)"}, **N6), "1", "INCORRECT"),
    (_ir("evaluate", {"expr": r"\gcd(n, 4)"}, **N6), "2", "CORRECT"),
    (_ir("evaluate", {"expr": "gcd(1/2, 1/3)"}), "1/6", "CORRECT"),      # sharp: the school rule on fractions
    (_ir("evaluate", {"expr": "lcm(1/2, 1/3)"}), "1/6", "INCORRECT"),    # lcm(1, 1)/gcd(2, 3) = 1
    (_ir("evaluate", {"expr": "igcd(n, 4)"}, **N6), "2", "CORRECT"),     # igcd of a symbol was unreadable
    (_ir("evaluate", {"expr": "ilcm(n, 4)"}, **N6), "24", "INCORRECT"),
])
def test_gcd_lcm_verdicts(ir, claim, verdict):
    assert _verdict(ir, _sol(claim)) == verdict


@pytest.mark.parametrize("claim,verdict", [
    ("gcd(n, 2) = 1", "INCORRECT"), ("lcm(n, 2) = 2*n", "INCORRECT"),
    ("lcm(n, 2) = n", "CORRECT"), ("gcd(n, 2)*lcm(n, 2) = 2*n", "CORRECT")])
def test_gcd_lcm_steps(claim, verdict):
    ir = _ir("evaluate", {"expr": "n + 1"}, **N6)
    sol = _sol("7", steps=[_step(1, "eq", claim), _step(2, "eq", "n + 1 = 7", ["s1"])])
    assert _verdict(ir, sol) == verdict


def test_the_latex_override_is_in_place():
    """The integer gcd/lcm and the two-sided limit of the LaTeX reader override a private class of
    latex2sympy2_extended (pinned): an upgrade that renames it must fail here, not silently."""
    from latex2sympy2_extended.latex2sympy2 import _Latex2Sympy
    assert hasattr(_Latex2Sympy, "handle_gcd_lcm") and hasattr(_Latex2Sympy, "handle_limit")
    assert type(parse_expr_str(r"\gcd(n, 2)", _ns(n=N))).__name__ == "gcd"


# ---------------------------------------------------------------------------- (b) arccot
@pytest.mark.parametrize("text,value", [
    ("arccot(-1)", 3 * sp.pi / 4), ("acot(-1)", 3 * sp.pi / 4), ("arccot(0)", sp.pi / 2), ("arccot(1)", sp.pi / 4),
    ("arccot(-sqrt(3))", 5 * sp.pi / 6), ("arccot(-oo)", sp.pi), ("arccot(oo)", 0),
    (r"\cot^{-1}(-1)", 3 * sp.pi / 4), (r"\arccot(-1)", 3 * sp.pi / 4), (r"\operatorname{arccot}(-1)", 3 * sp.pi / 4),
    (r"\mathrm{arccot}(-1)", 3 * sp.pi / 4), (r"\text{acot}(-1)", 3 * sp.pi / 4)])
def test_arccot_is_the_curriculum_function(text, value):
    assert sp.simplify(parse_expr_str(text, _ns()) - value) == 0


def test_arccot_as_written_and_everywhere_defined():
    from mathverify.certify.domain import written_definedness
    for text in ("arccot(x)", "acot(x)", r"\cot^{-1}(x)"):
        w = parse_as_written(text, _ns(x=XR))
        assert w is not None and len(w) == 1
        assert written_definedness(text, _ns(x=XR)) == ([], set())


def test_a_latex_name_is_no_declared_symbol():
    # `\mathrm{foo}` / `\frac{E}{2}` gave free symbols named like a function or a constant of the
    # namespace, and they passed the declared-symbol check
    with pytest.raises(ParseError):
        parse_expr_str(r"\frac{E}{2}", _ns())


@pytest.mark.parametrize("ir,sol,verdict", [
    (_ir("evaluate", {"expr": "arccot(-1)"}), _sol("-pi/4"), "INCORRECT"),
    (_ir("evaluate", {"expr": "arccot(-1)"}), _sol("3*pi/4"), "CORRECT"),
    (_ir("evaluate", {"expr": "-pi/4"}), _sol(r"\mathrm{arccot}(-1)"), "INCORRECT"),
    (_ir("solve_equation", {"var": "x"}, [{"name": "x"}], ["arccot(x) = -pi/4"], "set"), _sol("{-1}", "set"),
     "INCORRECT"),
    (_ir("limit", {"expr": "arccot(x)", "var": "x", "to": "0", "side": "-"}, [{"name": "x"}]), _sol("-pi/2"),
     "INCORRECT"),
    (_ir("definite_integral", {"integrand": "arccot(x)", "var": "x", "a": "-1", "b": "0"}, [{"name": "x"}]),
     _sol("3*pi/4 - log(2)/2"), "CORRECT"),
    (_ir("evaluate", {"expr": "arccot(-1)"}, [{"name": "x"}]),
     _sol("3*pi/4", steps=[_step(1, "eq", "arccot(-x) = pi - arccot(x)")]), "CORRECT"),
])
def test_arccot_verdicts(ir, sol, verdict):
    assert _verdict(ir, sol) == verdict


# ---------------------------------------------------------------------------- (c) bound variables
@pytest.mark.parametrize("text,value", [
    ("Sum(0**k, (k, 0, 3))", 1), ("Sum(sqrt(k**2), (k, -3, 3))", 12), ("Product(Abs(k), (k, -2, -1))", 2),
    ("Sum(k/Abs(k), (k, -3, -1))", -3), ("Integral(sqrt(x**2), (x, -1, 1))", 1), ("integrate(Abs(x), (x, -1, 1))", 1),
    ("Limit(sqrt(x**2)/x, x, -oo)", -1), ("limit(sqrt(x**2)/x, x, -oo)", -1), ("Limit(Abs(x)/x, x, 0, '-')", -1),
    ("at(diff(sqrt(x**2), x), x, -1)", -1), ("at(sqrt(x**2), x, -1)", 1),
    ("Integral(x*n, (x, 0, n), (n, 0, 1))", sp.Rational(1, 8)),
])
def test_a_bound_variable_has_the_facts_of_its_range(text, value):
    e = parse_expr_str(text, _ns(k=K, n=N, x=XP))
    assert sp.simplify(e.doit() - value) == 0


def test_a_binder_inside_a_binder_of_the_same_name_is_not_read():
    # sharp's convention (DECISIONS §72 b): SymPy flattens nested sums of one name, so the text is
    # refused instead of shadowed (franklin reads it as 22)
    with pytest.raises(ParseError):
        parse_expr_str("Sum(Sum(1, (k, 1, 2)), (k, -5, 5))", _ns(k=K, n=N, x=XP))


def test_scopes():
    ns = _ns(k=K, n=N, x=XP)
    # the free k outside the sum and the upper bound of its own sum are the problem's k
    e = parse_expr_str("k*Sum(k, (k, 1, n))", ns)
    assert K in e.free_symbols
    assert sp.expand(parse_expr_str("Sum(k, (k, 1, k))", ns).doit() - K * (K + 1) / 2) == 0
    # a sequence limit over an integer n stays one; a bound variable is never the problem's symbol,
    # and two readings of one binder are the same expression
    assert parse_expr_str("Limit(sin(pi*n), n, oo)", ns).doit() == 0
    e = parse_expr_str("Integral(sqrt(x**2), (x, 1, 2))", ns)
    assert XP not in e.atoms(sp.Symbol) and e == parse_expr_str("Integral(sqrt(x**2), (x, 1, 2))", ns)
    assert e.doit() == sp.Rational(3, 2)
    lim = parse_expr_str("Limit(Abs(x)/x, x, 0)", _ns(x=XR))
    assert str(lim.args[3]) == "+-" and lim.subs(XR, 5) == lim        # a substitution of x misses it
    # an index that is not a symbol is refused by SymPy, as before
    with pytest.raises(ParseError):
        parse_expr_str("Sum(pi, (pi, 1, 3))", ns)
    # ConditionSet's variable
    assert parse_expr_str("ConditionSet(x, x < 0, Reals)", ns) != sp.S.EmptySet


def test_latex_limits():
    ns = _ns(x=XP)
    two = parse_expr_str(r"\lim_{x\to 0} \frac{|x|}{x}", _ns(x=XR))
    assert isinstance(two, sp.Limit) and str(two.args[3]) == "+-"            # no side written: two-sided
    assert str(parse_expr_str(r"\lim_{x \to 0^{-}} \frac{|x|}{x}", _ns(x=XR)).args[3]) == "-"
    assert parse_expr_str(r"x\cdot\lim_{x\to -\infty} \frac{\sqrt{x^2}}{x}", ns).doit() == -XP
    assert parse_expr_str(r"\sum_{k=0}^{3} 0^{k}", _ns(k=K)).doit() == 1


KP = [{"name": "k", "domain": "positive_integer"}]
XPV = [{"name": "x", "domain": "positive_real"}]


@pytest.mark.parametrize("ir,sol,verdict", [
    (_ir("evaluate", {"expr": "Sum(0**k, (k, 0, 3))"}, KP), _sol("0"), "INCORRECT"),
    (_ir("evaluate", {"expr": "Sum(0**k, (k, 0, 3))"}, KP), _sol("1"), "CORRECT"),
    # a task on the problem's own variable keeps its declared domain: leaving it is no question
    (_ir("limit", {"expr": "sqrt(x**2)/x", "var": "x", "to": "-oo"}, XPV), _sol("1"), "UNKNOWN"),
    (_ir("limit", {"expr": "sqrt(x**2)/x", "var": "x", "to": "-oo"}, XPV), _sol("-1"), "UNKNOWN"),
    (_ir("limit", {"expr": "x*log(x)", "var": "x", "to": "0"}, XPV), _sol("0"), "CORRECT"),     # from the right
    (_ir("limit", {"expr": "x*log(x)", "var": "x", "to": "0", "side": "-"}, XPV), _sol("0"), "UNKNOWN"),
    # sharp's convention: the integral's variable is bound and runs over [a, b], not the declared domain
    # (DECISIONS §72 (b), test_audit_2026_09_29_v14); the value is 1, so 0 is refuted
    (_ir("definite_integral", {"integrand": "Abs(x)", "var": "x", "a": "-1", "b": "1"}, XPV), _sol("0"), "INCORRECT"),
    (_ir("definite_integral", {"integrand": "1/sqrt(x)", "var": "x", "a": "0", "b": "1"}, XPV), _sol("2"), "CORRECT"),
    (_ir("derivative", {"f": "sqrt(x**2)", "var": "x", "at": "-1"}, XPV), _sol("1"), "UNKNOWN"),
    (_ir("derivative", {"f": "sin(pi*n)", "var": "n", "at": "1"}, [{"name": "n", "domain": "positive_integer"}]),
     _sol("0"), "UNKNOWN"),
    (_ir("tangent_line", {"f": "sqrt(x**2)", "var": "x", "at": "-1"}, XPV + [{"name": "y"}]),
     _sol("y = x", "equation"), "UNKNOWN"),
    (dict(_ir("evaluate", {"expr": "f(-1)"}, XPV), functions=[{"name": "f", "args": ["x"], "expr": "sqrt(x**2)"}]),
     _sol("-1"), "INCORRECT"),
    (_ir("evaluate", {"expr": "k + 1"}, KP, ["k = 5"]),
     _sol("6", steps=[_step(1, "compute", "Sum(0**k, (k, 0, 2)) = 0")]), "INCORRECT"),
    (_ir("evaluate", {"expr": "k + 1"}, KP, ["k = 5"]),
     _sol("6", steps=[_step(1, "compute", "Sum(Abs(k), (k, -2, 2)) = 6")]), "CORRECT"),
    (_ir("evaluate", {"expr": "x"}, XPV, ["x = 2"]), _sol("ConditionSet(x, x < 0, Reals)"), "UNKNOWN"),
    # undefined as written at an index value: "3" and "1/2" were certified
    (_ir("evaluate", {"expr": "Sum(k/k, (k, -1, 1))"}, KP), _sol("3"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Sum(1/(k - 2), (k, 0, 3))"}, KP), _sol("1/2"), "UNKNOWN"),
])
def test_bound_variable_verdicts(ir, sol, verdict):
    assert _verdict(ir, sol) == verdict


# Limit, limit, at and Subs bind their variable too. Measured on 9ee5df9 (the Limit kept the declared
# symbol, at() read its body with it): each wrong answer below was CORRECT and each wrong step verified.
@pytest.mark.parametrize("expr,wrong,right", [
    ("Limit(sqrt(x**2)/x, x, -oo)", "1", "-1"), ("limit(sqrt(x**2)/x, x, -oo)", "1", "-1"),
    ("Limit(Abs(x)/x, x, 0, '-')", "1", "-1"), ("at(sqrt(x**2), x, -1)", "-1", "1"),
    ("at(diff(sqrt(x**2), x), x, -1)", "1", "-1"),
    ("(Limit)(sqrt(x**2)/x, x, -oo)", "1", "-1"), ("(at)(sqrt(x**2), x, -1)", "-1", "1"),
])
def test_a_point_binder_does_not_take_the_declaration_of_its_variable(expr, wrong, right):
    ir = _ir("evaluate", {"expr": expr}, XPV)
    assert _verdict(ir, _sol(wrong)) == "INCORRECT"
    assert _verdict(ir, _sol(right)) == "CORRECT"


def _step_statuses(r):
    return [s["status"] for layer in r.layers if layer.layer == "steps.refute"
            for s in layer.evidence.get("steps", [])]


@pytest.mark.parametrize("claim", ["Limit(sqrt(x**2)/x, x, -oo) = 1", "at(sqrt(x**2), x, -1) = -1",
                                   "Subs(sqrt(x**2), x, -1) = -1", "Subs(Derivative(sqrt(x**2), x), x, -1) = 1",
                                   "(Limit)(sqrt(x**2)/x, x, -oo) = 1"])
def test_a_wrong_point_binder_step_is_refuted(claim):
    r = verify(_ir("evaluate", {"expr": "x + 1"}, XPV, ["x = 2"]), _sol("3", steps=[_step(1, "compute", claim)]))
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1


def test_a_substitution_does_not_reach_a_limits_variable():
    # Limit(Abs(x)/x, x, 0).subs(x, 5) is Limit(1, 5, 0): the step was verified at the premises' x = 5
    r = verify(_ir("solve_equation", {"var": "x"}, [{"name": "x"}], ["x - 5 = 0"], "set"),
               _sol("{5}", "set", steps=[_step(1, "eq", "x*Limit(Abs(x)/x, x, 0) = x")]))
    assert _step_statuses(r) and _step_statuses(r)[0] != "verified"


def test_point_binder_scopes():
    ns = _ns(k=K, x=XP)
    for nested in ("Limit(at(x**2, x, 2)*x, x, 1)", "at(x + Limit(x/(x + 1), x, 5), x, 7)",
                   "(at)(x + (Limit)(x/(x + 1), x, 5), x, 7)"):
        with pytest.raises(ParseError):                    # one name bound inside a binder of that name
            parse_expr_str(nested, ns)
    # the binder's name in parentheses is the same call (it went past a text prefilter)
    assert parse_expr_str("(Limit)(sqrt(x**2)/x, x, -oo)", ns).doit() == -1
    assert parse_expr_str("(at)(sqrt(x**2), x, -1)", ns) == 1
    assert parse_expr_str("Sum(at(sqrt(x**2), x, k), (k, -2, 2))", ns).doit() == 6   # the point is the sum's k
    assert parse_expr_str("at(x**2, x, x + 1)", ns) == (XP + 1) ** 2                  # the point is read outside
    e = parse_expr_str("x + Limit(sqrt(x**2)/x, x, -oo)", ns)
    assert XP in e.free_symbols and e.doit() == XP - 1
    assert parse_expr_str("at(sqrt(x**2), x, I)", ns) == sp.I                         # no real fact at I
    for text in ("Limit(Abs(x)/x, z=x, z0=0)", "Limit(sqrt(x**2)/x, Symbol('x'), -oo)",
                 "at(sqrt(x**2), -x, -1)", "at(sqrt(x**2), pi, 1)"):
        with pytest.raises(ParseError):
            parse_expr_str(text, ns)


NPV = [{"name": "n", "domain": "positive_integer"}]


@pytest.mark.parametrize("ir,sol,verdict", [
    # the approach leaves the declared domain: each wrong claim was CORRECT on 9ee5df9
    (_ir("limit", {"expr": "sqrt(x**2)", "var": "x", "to": "-1"}, XPV), _sol("-1"), "UNKNOWN"),
    (_ir("limit", {"expr": "sqrt(x**2)/x", "var": "x", "to": "-oo"}, [{"name": "x", "domain": "nonneg_real"}]),
     _sol("1"), "UNKNOWN"),
    (_ir("limit", {"expr": "sin(pi*n)/(n - 1)", "var": "n", "to": "1"}, NPV), _sol("0"), "UNKNOWN"),
    # controls: a sequence limit at oo, a left limit inside the domain, the closed end read from inside
    (_ir("limit", {"expr": "sin(pi*n)", "var": "n", "to": "oo"}, NPV), _sol("0"), "CORRECT"),
    (_ir("limit", {"expr": "sqrt(x**2)/x", "var": "x", "to": "2", "side": "-"}, XPV), _sol("1"), "CORRECT"),
    (_ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, XPV), _sol("1"), "CORRECT"),
    # was INCORRECT: the left side was computed with the positive symbol at negative points
    (_ir("limit", {"expr": "floor(x)", "var": "x", "to": "0"}, XPV), _sol("0"), "CORRECT"),
    # a derivative, tangent, antiderivative or extremum in an integer variable: sin(pi*n) folded to 0
    (_ir("derivative", {"f": "sin(pi*n)", "var": "n", "at": "1"}, [{"name": "n", "domain": "integer"}]),
     _sol("0"), "UNKNOWN"),
    (_ir("derivative", {"f": "sin(pi*n)", "var": "n"}, NPV), _sol("0", "expression"), "UNKNOWN"),
    (_ir("derivative", {"f": "sin(pi*n)", "var": "n"}, NPV), _sol("pi*cos(pi*n)", "expression"), "UNKNOWN"),
    (_ir("tangent_line", {"f": "sin(pi*n)", "var": "n", "at": "1"}, NPV + [{"name": "y"}]),
     _sol("y = 0", "equation"), "UNKNOWN"),
    (_ir("antiderivative", {"integrand": "sin(pi*n)", "var": "n"}, NPV), _sol("7", "expression"), "UNKNOWN"),
    (_ir("extremum", {"f": "-(n - 3/2)**2", "var": "n", "interval": "[0, 3]", "which": "max"}, NPV),
     _sol("0"), "UNKNOWN"),
])
def test_a_task_variable_keeps_its_declared_domain(ir, sol, verdict):
    """30 Sep 2026: the task's own variable keeps its declared assumptions, so a limit that
    approaches outside them, or calculus in a variable declared an integer, is no question."""
    assert _verdict(ir, sol) == verdict


def test_the_lean_series_template_binds_its_index_over_the_range():
    from mathverify.formal.statement import build_statement
    ir = _ir("series_sum", {"term": "Abs(k)", "var": "k", "lo": "-2", "hi": "2"}, KP)
    st = build_statement(ir, {"kind": "value", "payload": "0"})
    # was `(∑ k ∈ Finset.Icc (-2) 2, (k : ℤ)) = 0`, which Lean proved
    assert st is not None and "|k|" in st.goal


def test_definedness_inside_a_sum_is_decided_over_the_index_range():
    from mathverify.certify.domain import definedness_conditions, written_definedness
    ns = _ns(k=K, x=XR)
    assert sp.false in definedness_conditions(parse_as_written("Sum(k/k, (k, -1, 1))", ns), None)
    assert sp.false in definedness_conditions(parse_as_written("Sum(1/(k - 5), (k, 1, oo))", ns), None)
    assert written_definedness("Sum(x/k, (k, -1, 1))", ns) == ([], {XR})
    # a condition that holds on the whole range says nothing about the problem's own k
    assert written_definedness("Sum(1/(k*(k + 1)), (k, 1, oo))", ns) == ([], set())
    assert written_definedness("Sum(1/(k - x), (k, 1, 3))", ns)[0] == [sp.Ne(1 - XR, 0), sp.Ne(2 - XR, 0),
                                                                        sp.Ne(3 - XR, 0)]


# ---------------------------------------------------------------------------- (d) set endpoints
R = "(sqrt(11 + 6*sqrt(2)) - sqrt(2))"          # = 3
Q, QD = "sqrt(2 + sqrt(3))", "((sqrt(6) + sqrt(2))/2)"     # the same number


def test_an_endpoint_written_two_ways_is_one_point():
    s = parse_set_str(f"(-oo, {R}) U (3, oo)", _ns())
    assert s.contains(3) is not sp.true and s != sp.S.Reals
    assert parse_set_str(f"(-oo, 3) U ({R}, oo)", _ns()).contains(3) is not sp.true
    from mathverify.equiv.sets import set_equal
    assert set_equal(sp.Interval(3, parse_expr_str(R, _ns())), sp.FiniteSet(3))[0] is True


@pytest.mark.parametrize("ir,claim,verdict", [
    (_ir("domain_of", {"expr": "x + 1", "var": "x"}, [{"name": "x"}], shape="set"), f"(-oo, {R}) U (3, oo)",
     "INCORRECT"),
    (_ir("domain_of", {"expr": "sqrt(x)*sqrt(5 - x)", "var": "x"}, [{"name": "x"}], shape="set"),
     f"[0, {R}) U (3, 5]", "INCORRECT"),
    (_ir("solve_inequality", {"var": "x"}, [{"name": "x"}], ["x**2 + 1 > 0"], "interval"), f"(-oo, 3) U ({R}, oo)",
     "INCORRECT"),
    (_ir("domain_of", {"expr": "1/(x**2 + 1)", "var": "x"}, [{"name": "x"}], shape="set"), f"(-oo, {Q}) U ({QD}, oo)",
     "INCORRECT"),
    (_ir("domain_of", {"expr": "1/(x - 3)", "var": "x"}, [{"name": "x"}], shape="set"), f"(-oo, {R}) U (3, oo)",
     "CORRECT"),
    (_ir("domain_of", {"expr": "1/(x**2 - 2 - sqrt(3))", "var": "x"}, [{"name": "x"}], shape="set"),
     f"(-oo, -{Q}) U (-{QD}, {QD}) U ({Q}, oo)", "CORRECT"),
])
def test_set_endpoint_verdicts(ir, claim, verdict):
    kind = "interval" if ir["answer_shape"] == "interval" else "set"
    assert _verdict(ir, _sol(claim, kind)) == verdict


def test_a_step_that_drops_a_point_written_two_ways_is_refuted():
    ir = _ir("solve_inequality", {"var": "x"}, [{"name": "x"}], ["x > 0"], "interval")
    sol = _sol("(0, oo)", "interval", steps=[_step(1, "eq", f"Or(x < {R}, x > 3)")])
    r = verify(ir, sol)
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1


# ---------------------------------------------------------------------------- audit of V14 (30 Sep 2026)
# An adversarial audit of the change found these; each one's reproduction is kept.
KI = [{"name": "k", "domain": "integer"}]


@pytest.mark.parametrize("text", ["Sum(0**k, (+k, 0, 3))", "Sum(0**k, [k, 0, 3])", "Limit(sqrt(x**2)/x, +x, -oo)"])
def test_a_binder_variable_written_otherwise_is_still_bound(text):
    e = parse_expr_str(text, _ns(k=K, x=XP))
    assert e.doit() in (1, -1)


@pytest.mark.parametrize("text", ["Sum(0**k, (k,) + (0, 3))", "Subs(Derivative(sqrt(x**2), x), (x,), (-1,))",
                                  "at(x**2, 2*x, 1)",
                                  # 1*k and k**1 are k again: the IR's k > 0 made 0**k zero (sharp, 30 Sep)
                                  "Sum(0**k, (1*k, 0, 3))", "Sum(0**k, (k**1, 0, 3))",
                                  "Product(k, [k, 1, 3] + [])"])
def test_a_binder_variable_that_is_not_a_name_is_refused(text):
    from mathverify.steps.deterministic import _step_namespace
    with pytest.raises(ParseError):
        parse_expr_str(text, _step_namespace(_ns(k=K, x=XP)))


def test_an_undirected_limit_is_two_sided_everywhere():
    for text in ("Limit(Abs(x - 4)/(x - 4), x, 4)", r"\lim_{x \to 2^{3}} \frac{|x-8|}{x-8}",
                 r"\lim_{x \to e^{2}} x"):
        assert str(parse_expr_str(text, _ns(x=XR)).args[3]) == "+-"
    assert str(parse_expr_str(r"\lim_{x \to 0^{+}} x", _ns(x=XR)).args[3]) == "+"


@pytest.mark.parametrize("ir,sol,verdict", [
    # undefined terms outside what the first V14 decided: an infinite range from -oo, > 200 terms,
    # an infinite range with an inequality, a symbolic bound, an integral, a limit
    (_ir("evaluate", {"expr": "Sum(k/k*2**k, (k, -oo, 0))"}, KP), _sol("2"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Sum(k/k, (k, -1, 1000))"}, KI), _sol("1002"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Sum(sqrt(k - 3)**2/3**k, (k, 0, oo))"}, KI), _sol("-15/4"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Sum(k/k, (k, -1, n))"}, KP + [{"name": "n", "domain": "positive_integer"}],
         ["n = 3"]), _sol("5"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Integral(sqrt(x)**2, (x, -1, 1))"}, [{"name": "x"}]), _sol("0"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Limit(sqrt(x)**2/x, x, -oo)"}, [{"name": "x"}]), _sol("1"), "UNKNOWN"),
    # a bound variable's conditions are not the unknown's: the root -3/2 is not "outside the domain"
    (_ir("solve_equation", {"var": "x", "equation": "x + Integral(sqrt(x)**2, (x, 0, 1)) = -1"}, [{"name": "x"}],
         shape="set"), _sol("{-3/2}", "set"), "NOT_INCORRECT"),
    # an undirected limit that does not exist
    (_ir("evaluate", {"expr": "Limit(Abs(x - 4)/(x - 4), x, 4)"}, [{"name": "x"}]), _sol("1"), "NOT_CORRECT"),
    (_ir("evaluate", {"expr": r"\lim_{x \to 2^{3}} \frac{|x-8|}{x-8}"}, [{"name": "x"}]), _sol("1"), "NOT_CORRECT"),
    # an index from -oo is still an integer: sin(pi*k) = 0
    (_ir("evaluate", {"expr": "Sum(sin(pi*k)/k**2, (k, -oo, -1))"}, KI), _sol("0"), "CORRECT"),
    # a function's variable named like a constant is its variable
    (dict(_ir("evaluate", {"expr": "h(3)"}), functions=[{"name": "h", "args": ["i"], "expr": "i**2"}]),
     _sol("-1"), "INCORRECT"),
    (dict(_ir("evaluate", {"expr": "h(3)"}), functions=[{"name": "h", "args": ["i"], "expr": "i**2"}]),
     _sol("9"), "CORRECT"),
    # reversed bounds: SymPy's Karr sum (1) and the empty sum (0) are both conventions the
    # curriculum does not have, so no task certifies either
    (_ir("evaluate", {"expr": "Sum(k, (k, 1, -2))"}, KP), _sol("1"), "UNKNOWN"),
    (_ir("series_sum", {"term": "k", "var": "k", "lo": "1", "hi": "-2"}, KI), _sol("0"), "UNKNOWN"),
    (_ir("evaluate", {"expr": "Product(1/k, (k, 1, -2))"}, KP), _sol("0"), "UNKNOWN"),
    # a sequence limit over an integer n reads the same in LaTeX as in text
    (_ir("evaluate", {"expr": r"\lim_{n \to \infty} \cos(2 \pi n)"}, [{"name": "n", "domain": "positive_integer"}]),
     _sol("1"), "CORRECT"),
])
def test_audit_verdicts(ir, sol, verdict):
    got = _verdict(ir, sol)
    if verdict == "NOT_INCORRECT":
        assert got != "INCORRECT"
    elif verdict == "NOT_CORRECT":
        assert got != "CORRECT"
    else:
        assert got == verdict


def _step_status(ir, claim, kind="eq", payload="6"):
    r = verify(ir, _sol(payload, steps=[_step(1, kind, claim)]))
    lay = next(l for l in r.layers if l.layer == "steps.refute")
    return lay.evidence["steps"][0]["status"], r.verdict


def test_a_limit_step_is_not_substituted_through_its_variable():
    # SymPy's Limit.subs rewrote the bound x: checked at the premises' x = 5, the eq step
    # "Limit(Abs(x)/x, x, 0) = 1" became Limit(1, 5, 0) = 1 and was verified
    ir = _ir("evaluate", {"expr": "x + 1"}, [{"name": "x"}], ["x = 5"])
    assert _step_status(ir, "Limit(Abs(x)/x, x, 0) = 1")[0] != "verified"


def test_a_step_undefined_as_written_is_not_verified():
    ir = _ir("evaluate", {"expr": "x + 1"}, [{"name": "x"}], ["x = 5"])
    status, verdict = _step_status(ir, "Sum(j/j, (j, -1, 1)) = 3", kind="compute")
    assert status == "unknown" and verdict == "CORRECT"          # not verified, not a refutation


def test_unevaluated_sums_are_evaluated_under_a_time_limit():
    import time
    t0 = time.perf_counter()
    r = verify(_ir("evaluate", {"expr": "Sum((1/2)**Abs(k), (k, -oo, oo))"}, KI), _sol("3"))
    assert time.perf_counter() - t0 < 120 and r.verdict in ("CORRECT", "UNKNOWN")


NP = [{"name": "n", "domain": "positive_integer"}]


@pytest.mark.parametrize("ir,claim,verdict", [
    # random points: gcd(3**109, 2) rounded at 30 digits was 2, and a true identity was refuted
    (_ir("simplify_expression", {"expr": "gcd(3**n, 2)"}, NP, shape="expression"), "1", "NOT_INCORRECT"),
    (_ir("evaluate", {"expr": "lcm(3**n, 2)/3**n"}, NP), "2", "NOT_INCORRECT"),
    # LaTeX arguments are exact integers too
    (_ir("evaluate", {"expr": r"\gcd(2^{2}, 6)"}), "4", "INCORRECT"),
    (_ir("evaluate", {"expr": r"\operatorname{lcm}(2^{2}, 6)"}), "12", "CORRECT"),
    # gcd off the RATIONALS has no value: nothing built on it is certified (sharp: at x = 1/2 the
    # school rule gives gcd(1/2, 2) = 1/2, so the value 1/2 is right; x = sqrt(2) is the case)
    (_ir("evaluate", {"expr": "x + gcd(x, 2) - gcd(2, x)"}, [{"name": "x"}], ["x = 1/2"]), "1/2", "CORRECT"),
    (_ir("simplify_expression", {"expr": "x"}, [{"name": "x"}], shape="expression"), "x + gcd(x, 2) - gcd(2, x)",
     "NOT_CORRECT"),
    # the question's gcd written back in another form is not a value
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), "gcd(120, 84)", "UNKNOWN"),
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), r"\gcd(84, 120)", "UNKNOWN"),
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), "igcd(84, 120)", "UNKNOWN"),
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), "12", "CORRECT"),
    # arccot is unary
    (_ir("evaluate", {"expr": "pi/2 - atan(2)"}), "acot(2, 9)", "UNKNOWN"),
    # (30 Sep 2026) gcd of an irrational number: the expression does not exist at x = sqrt(2)
    (_ir("evaluate", {"expr": "x + gcd(x, 2) - gcd(2, x)"}, [{"name": "x"}], ["x = sqrt(2)"]), "sqrt(2)",
     "NOT_CORRECT"),
])
def test_notation_audit_verdicts(ir, claim, verdict):
    kind = "expression" if ir["answer_shape"] == "expression" else "value"
    test_audit_verdicts(ir, _sol(claim, kind), verdict)


XV = [{"name": "x"}]


@pytest.mark.parametrize("ir,claim,kind,verdict", [
    # 30 Sep 2026, measured on 9ee5df9: the written form's gcd/lcm (rational arguments) and factorial
    # (a natural number) gave no definedness condition, so an expression that cancels them was
    # certified where it does not exist; each NOT_ verdict below was the opposite one before
    (_ir("solve_equation", {"var": "x", "equation": "(x - 1/2)*(x - sqrt(2)) = gcd(x, 2) - gcd(2, x)"}, XV,
         shape="set"), "{1/2, sqrt(2)}", "set", "NOT_CORRECT"),
    (_ir("solve_equation", {"var": "x", "equation": "(x - 1/2)*(x - sqrt(2)) = gcd(x, 2) - gcd(2, x)"}, XV,
         shape="set"), "{1/2}", "set", "NOT_INCORRECT"),
    (_ir("solve_inequality", {"var": "x", "inequality": "x + gcd(x, 2) - gcd(2, x) < 1/2"}, XV, shape="set"),
     "(-oo, 1/2)", "interval", "NOT_CORRECT"),
    (_ir("simplify_expression", {"expr": "x"}, XV, shape="expression"), "x + gcd(x, 2)*0", "expression",
     "NOT_CORRECT"),
    (_ir("evaluate", {"expr": "x + factorial(x) - factorial(x)"}, XV, ["x = -3"]), "-3", "value", "NOT_CORRECT"),
    (_ir("evaluate", {"expr": "x + factorial(x) - factorial(x)"}, XV, ["x = 1/2"]), "1/2", "value", "NOT_CORRECT"),
    (_ir("solve_equation", {"var": "x", "equation": "(x + 3)*(x - 2) = factorial(x) - factorial(x)"}, XV,
         shape="set"), "{-3, 2}", "set", "NOT_CORRECT"),
    (_ir("solve_equation", {"var": "x", "equation": "(x + 3)*(x - 2) = factorial(x) - factorial(x)"}, XV,
         shape="set"), "{2}", "set", "NOT_INCORRECT"),
    (_ir("simplify_expression", {"expr": "x"}, XV, shape="expression"), "x + factorial(x) - factorial(x)",
     "expression", "NOT_CORRECT"),
    # controls: where the arguments are in the set, the value stands
    (_ir("evaluate", {"expr": "x + factorial(x) - factorial(x)"}, XV, ["x = 3"]), "3", "value", "CORRECT"),
    (_ir("evaluate", {"expr": "gcd(a, b)"}, [{"name": "a"}, {"name": "b"}], ["a = 12", "b = 18"]), "6", "value",
     "CORRECT"),
    (_ir("evaluate", {"expr": "gcd(a, b)"}, [{"name": "a"}, {"name": "b"}], ["a = 12", "b = 18"]), "3", "value",
     "INCORRECT"),
    (_ir("evaluate", {"expr": "factorial(n)/factorial(n - 3)"}, [{"name": "n"}], ["n = 6"]), "120", "value",
     "CORRECT"),
])
def test_gcd_and_factorial_arguments_are_definedness_conditions(ir, claim, kind, verdict):
    test_audit_verdicts(ir, _sol(claim, kind), verdict)


@pytest.mark.parametrize("ir,claim,kind,verdict", [
    # a gcd/lcm of numbers in the claim is computed by the parser: the verifier would produce the answer
    # (principle 2; GCD-10 of the V14 audit: these were CORRECT)
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), "gcd(84, 120)*1", "value", "UNKNOWN"),
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), "gcd(84, 120) + 0", "value", "UNKNOWN"),
    (_ir("evaluate", {"expr": "gcd(84, 120)"}), r"\operatorname{lcm}(4, 3)", "value", "UNKNOWN"),
    (_ir("evaluate", {"expr": "gcd(n, 4)"}, **N6), "gcd(6, 4)", "value", "UNKNOWN"),
    # a gcd of the problem's own symbol is a value (tests/test_audit_2026_09_29_v14.py::test_gcd_is_symmetric)
    (_ir("evaluate", {"expr": "gcd(n, 4)"}, [{"name": "n", "domain": "positive_integer"}], shape="expression"),
     "gcd(4, n)", "expression", "CORRECT"),
])
def test_a_claim_that_computes_a_gcd_is_not_a_value(ir, claim, kind, verdict):
    test_audit_verdicts(ir, _sol(claim, kind), verdict)


def test_arccot_takes_one_argument():
    with pytest.raises(ParseError):
        parse_expr_str("arccot(x, 2)", _ns(x=XR))


def test_nested_bounds_parse_in_linear_time():
    # SymPy's assumptions of a Sum rebuild it: bounds nested five deep took 104 s (audit of V14)
    import time
    s = "1"
    for _ in range(8):
        s = f"Sum(k, (k, -1, {s}))"
    t0 = time.perf_counter()
    # sharp refuses a Sum whose limit is itself an operation (whether the range is reversed cannot
    # be asked of it cheaply); the refusal, not a value, is what must come in time
    with pytest.raises(ParseError):
        parse_expr_str(s, _ns(k=K))
    assert parse_as_written(s, _ns(k=K)) is None
    with pytest.raises(ParseError):
        parse_expr_str(r"\sum_{k=-1}^{\sum_{k=-1}^{\sum_{k=-1}^{\sum_{k=-1}^{1} k} k} k} k", _ns(k=K))
    assert time.perf_counter() - t0 < 10


def test_a_sum_over_undefined_terms_is_not_certified():
    # sharp before this change: "n + 2" and "2" were CORRECT (the index's k != 0 was dropped)
    NP = [{"name": "n", "domain": "positive_integer"}]
    assert _verdict(_ir("evaluate", {"expr": "Sum(k/k, (k, -1, n))"}, KP + NP), _sol("n + 2")) == "UNKNOWN"
    assert _verdict(_ir("evaluate", {"expr": "Sum(k/k*2**k, (k, -oo, 0))"}, KP), _sol("2")) == "UNKNOWN"
    # a condition that holds on the whole range decides nothing: these stay certified
    assert _verdict(_ir("evaluate", {"expr": "Sum(1/(k*(k + 1)), (k, 1, n))"}, KP + NP), _sol("n/(n + 1)")) \
        == "CORRECT"
    assert _verdict(_ir("evaluate", {"expr": "Sum(1/factorial(k), (k, 0, oo))"}, KP), _sol("E")) == "CORRECT"


def test_a_binder_variable_written_with_a_plus_is_bound_in_verdicts():
    # sharp before this change: "0" was CORRECT and "1" INCORRECT (0**k read with the IR's k > 0)
    ir = _ir("evaluate", {"expr": "Sum(0**k, (+k, 0, 3))"}, KP)
    assert _verdict(ir, _sol("1")) == "CORRECT" and _verdict(ir, _sol("0")) == "INCORRECT"


def test_a_closed_undecided_condition_is_not_an_empty_solution_set():
    from mathverify.certify.domain import DEFINEDNESS_UNDECIDED
    from mathverify.sandbox.ops import solveset_in
    for c in (DEFINEDNESS_UNDECIDED, sp.Ne(sp.cos(sp.acot(2) + sp.acot(sp.Rational(1, 2))), 0)):
        assert isinstance(solveset_in(c, XR, sp.S.Reals), sp.ConditionSet)     # was EmptySet


def test_set_endpoints_are_compared_pairwise_only_when_near():
    import time
    many = "{" + ", ".join(f"sqrt({k})" for k in range(2, 302)) + "}"
    t0 = time.perf_counter()
    parse_set_str(many, _ns())
    assert time.perf_counter() - t0 < 20                    # 1000 elements took 90 s
    with pytest.raises(ParseError):                         # beyond the limit a set is not read
        parse_set_str("{" + ", ".join(f"sqrt({k})" for k in range(2, 402)) + "}", _ns())


@pytest.mark.parametrize("text", ["Integral(sqrt(x**2), (x, 1))", "Sum(0**k, (k, 0))", "Integral(x, (x, 0, 1, 2))",
                                  # sharp before this change: 1/2 with x > 0 (true -1/2), and 2
                                  "Integral(sqrt(x**2), (x, -1))", "integrate(x, (x, 0, 1, 2))"])
def test_limits_other_than_variable_lower_upper_are_refused(text):
    with pytest.raises(ParseError):
        parse_expr_str(text, _ns(k=K, x=XP))


@pytest.mark.parametrize("ir,claim,verdict", [
    # SymPy's own Union syntax: the endpoints are made one spelling before SymPy merges them
    (_ir("domain_of", {"expr": "x + 1", "var": "x"}, [{"name": "x"}], shape="set"),
     f"Union(Interval.open(-oo, {R}), Interval.open(3, oo))", "INCORRECT"),
    (_ir("solve_inequality", {"var": "x"}, [{"name": "x"}], ["x**2 + 1 > 0"], "interval"),
     f"Union(Interval.open(-oo, 3), Interval.open({R}, oo))", "INCORRECT"),
    (_ir("domain_of", {"expr": "1/(x - 3)", "var": "x"}, [{"name": "x"}], shape="set"),
     f"Union(Interval.open(-oo, {R}), Interval.open(3, oo))", "CORRECT"),
])
def test_set_constructor_verdicts(ir, claim, verdict):
    kind = "interval" if ir["answer_shape"] == "interval" else "set"
    assert _verdict(ir, _sol(claim, kind)) == verdict


def test_index_facts_of_infinite_ranges_and_symbolic_bounds():
    from mathverify.certify.domain import definedness_conditions, is_undecided
    from mathverify.steps.deterministic import _step_namespace
    ns = _step_namespace(_ns(k=sp.Symbol("k"), n=N))
    # k >= 0 on [0, oo): factorial(k) is nonzero there (the first V14 lost the fact: oo is not
    # "nonnegative" in SymPy, only extended nonnegative)
    assert definedness_conditions(parse_as_written("Sum(1/factorial(k), (k, 0, oo))", ns), None) == []
    # a symbolic bound decides a condition that holds on the whole superset, not one that fails in it
    assert definedness_conditions(parse_as_written("Sum(1/(k*(k + 1)), (k, 1, n))", ns), None) == []
    c = definedness_conditions(parse_as_written("Sum(k/k, (k, -1, n))", ns), None)
    assert any(is_undecided(x) for x in c) and sp.false not in c


def test_a_step_undefined_as_written_is_still_refuted_when_proved_false():
    # the limit does not exist in the reals: the limit checker's refutation stands
    ir = _ir("limit", {"expr": "(x**2 - 4)/(x - 2)", "var": "x", "to": "2"}, [{"name": "x"}])
    sol = _sol("4", steps=[_step(1, "compute", "Limit(log(x), x, -1) = I*pi"),
                           _step(2, "compute", "Limit(x + 2, x, 2) = 4")])
    assert verify(ir, sol).verdict == "INCORRECT"
