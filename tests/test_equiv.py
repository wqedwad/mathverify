"""equiv/ — equivalent-form pairs must be accepted (recall), non-equivalent pairs rejected (FP=0).
Handoff §7: rule-based recall >= 0.95 on equivalent-form pairs, FP = 0."""
import pytest
import sympy as sp
from sympy import pi, sqrt, log, exp, I, Rational, Interval, FiniteSet, Union, S, oo

from mathverify.equiv import answers_equivalent
from mathverify.normalize.parse import parse_expr_str, parse_set_str, parse_answer

x = sp.Symbol("x", real=True)

EQUIVALENT_SCALARS = [
    ("0.5*pi", "90°"), ("pi/2", "90 derece"), ("sqrt(8)", "2*sqrt(2)"), ("1/2", "0.5"),
    ("log(8)/log(2)", "3"), ("exp(log(7))", "7"), ("sin(pi/6)", "1/2"), ("(1+sqrt(5))/2", "0.5+sqrt(5)/2"),
    ("2**10", "1024"), ("\\frac{3}{4}", "0.75"), ("\\sqrt{2}", "2**(1/2)"), ("tan(pi/4)", "1"),
    ("log(x**2)", "2*log(x)"),   # expression on x>0 only (tested separately)
    ("1e3", "1000"), ("3!", "6"), ("binomial(5,2)", "10"), ("gcd(84,120)", "12"), ("lcm(4,6)", "12"),
    ("(3+4*I)*(3-4*I)", "25"), ("cos(pi/3)+I*sin(pi/3)", "exp(I*pi/3)"), ("\\frac{\\pi}{6}", "30°"),
    ("Rational(22,7)", "22/7"), ("sqrt(x**2)", "Abs(x)"), ("(x**2-1)/(x-1)", "x+1"),
]
NON_EQUIVALENT_SCALARS = [
    ("pi/3", "90°"), ("sqrt(8)", "2*sqrt(3)"), ("1/3", "0.33"), ("22/7", "pi"), ("3.14", "pi"),
    ("log(2)", "log(3)"), ("2**10", "1000"), ("sin(pi/6)", "sqrt(3)/2"), ("0", "1e-13"),
    ("exp(1)", "2.718281828"), ("(1+I)**2", "2"), ("x+1", "x-1"),
]


from mathverify.normalize.parse import build_namespace  # noqa: E402

_NS = build_namespace(extra={"x": x})


def _p(s):
    return parse_expr_str(s, _NS)


@pytest.mark.parametrize("a,b", EQUIVALENT_SCALARS)
def test_equivalent_pairs_accepted(a, b):
    ea, eb = _p(a), _p(b)
    free = ea.free_symbols | eb.free_symbols
    if free:
        dom = {s_: Interval.open(0, oo) if "log" in a or "x-1" in a else S.Reals for s_ in free}
        if "x-1" in a:
            dom = {s_: sp.Complement(S.Reals, FiniteSet(1)) for s_ in free}
        ok, ev = answers_equivalent(ea, eb, shape="expression", domain=dom)
    else:
        ok, ev = answers_equivalent(ea, eb, shape="scalar")
    assert ok is True, (a, b, ev.get("method"), ev)


@pytest.mark.parametrize("a,b", NON_EQUIVALENT_SCALARS)
def test_non_equivalent_pairs_rejected(a, b):
    ea, eb = _p(a), _p(b)
    free = ea.free_symbols | eb.free_symbols
    if free:
        ok, ev = answers_equivalent(ea, eb, shape="expression", domain=S.Reals)
    else:
        ok, ev = answers_equivalent(ea, eb, shape="scalar")
    assert ok is False, (a, b, ev)


def test_sets_and_intervals():
    assert answers_equivalent(parse_set_str("{1, 2}"), FiniteSet(2, 1), shape="set")[0] is True
    assert answers_equivalent(parse_set_str("{sqrt(4), 2*1}"), FiniteSet(2), shape="set")[0] is True   # both collapse to {2}
    assert answers_equivalent(parse_set_str("{2, 3}"), FiniteSet(2), shape="set")[0] is False
    assert answers_equivalent(parse_set_str("(-2, 7)"), Interval.open(-2, 7), shape="interval")[0] is True
    assert answers_equivalent(parse_set_str("[-2, 7)"), Interval.open(-2, 7), shape="interval")[0] is False
    assert answers_equivalent(parse_set_str("(-oo, 1) U (1, oo)"), sp.Complement(S.Reals, FiniteSet(1)), shape="set")[0] is True
    assert answers_equivalent(parse_set_str("(-oo, -2) U (7, oo)"), Interval.open(-2, 7), shape="interval")[0] is False
    assert answers_equivalent(parse_set_str("{}"), S.EmptySet, shape="set")[0] is True
    assert answers_equivalent(parse_set_str("(1, 3]"), Interval.Lopen(1, 3), shape="interval")[0] is True


def test_domain_dependence_is_explicit():
    a, b = log(x ** 2), 2 * log(x)
    assert answers_equivalent(a, b, shape="expression", domain=Interval.open(0, oo))[0] is True
    assert answers_equivalent(a, b, shape="expression", domain=S.Reals)[0] is False


def test_equation_equivalence():
    y = sp.Symbol("y", real=True)
    e1 = sp.Eq(2 * x - y + 3, 0)
    e2 = sp.Eq(y, 2 * x + 3)
    e3 = sp.Eq(4 * x - 2 * y, -6)
    e4 = sp.Eq(y, 2 * x - 3)
    assert answers_equivalent(e1, e2, shape="equation", var=x)[0] is True
    assert answers_equivalent(e3, e2, shape="equation", var=x)[0] is True
    assert answers_equivalent(e4, e2, shape="equation", var=x)[0] is False


def test_tolerance_declared_by_problem():
    ok, _ = answers_equivalent(sp.Float("3.14"), pi, shape="scalar", abs_tol=0.005)
    assert ok is True
    ok, _ = answers_equivalent(sp.Float("3.14"), pi, shape="scalar")
    assert ok is False


def test_parse_answer_kinds():
    assert parse_answer("count", 8) == 8
    assert parse_answer("set", ["1", "2"]) == FiniteSet(1, 2)
    assert parse_answer("interval", "(-2, 7)") == Interval.open(-2, 7)
    assert str(parse_answer("dne", None)) == "DNE"
