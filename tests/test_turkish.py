"""Turkish lexicon / number normalisation / classifier (handoff §8, failure mode #10)."""
import pytest
import sympy as sp

from mathverify.normalize.turkish import (normalize_numbers_tr, tr_to_canonical, extract_constraints_tr,
                                          classify_tr)
from mathverify.normalize.parse import parse_expr_str, preclean


def test_thousands_dot_and_decimal_comma():
    assert normalize_numbers_tr("10.000 TL") == "10000 TL"
    assert normalize_numbers_tr("3,5 saat") == "3.5 saat"
    assert normalize_numbers_tr("1.234.567,89") == "1234567.89"
    assert normalize_numbers_tr("0,25 ile 1.000") == "0.25 ile 1000"
    assert normalize_numbers_tr("x = 12") == "x = 12"
    assert normalize_numbers_tr("3.14") == "3.14"          # not a thousands group


def test_canonical_terms():
    t = tr_to_canonical("OBEB(12, 18) ve OKEK(4, 6) kaçtır?")
    assert "gcd(12, 18)" in t and "lcm(4, 6)" in t


def test_constraint_extraction():
    r = extract_constraints_tr("x ve y birbirinden farklı pozitif tam sayılardır.", ["x", "y"])
    assert r["domain"] == ["integer"]
    assert "x > 0" in r["constraints"] and "y > 0" in r["constraints"] and "x != y" in r["constraints"]
    r = extract_constraints_tr("a, b, c ardışık tek sayılardır", ["a", "b", "c"])
    assert "b = a + 1" in r["constraints"] and "Mod(a, 2) = 1" in r["constraints"]
    r = extract_constraints_tr("iki basamaklı bir doğal sayı", ["n"])
    assert "n >= 10" in r["constraints"] and "n <= 99" in r["constraints"]
    r = extract_constraints_tr("en az 3, en çok 8 kişi", ["k"])
    assert "k >= 3" in r["constraints"] and "k <= 8" in r["constraints"]


def test_classifier():
    assert classify_tr("f(x) = x³ - 3x fonksiyonunun [-2, 3] aralığındaki en büyük değeri kaçtır?")[0] == "türev"
    assert classify_tr("∫ ln x dx integralinin sonucu nedir?")[0] == "integral"
    assert classify_tr("lim x→0 |x|/x limiti kaçtır?")[0] == "limit"
    assert classify_tr("Bir işçi bir işi 6 saatte, diğeri 3 saatte bitiriyor. Birlikte kaç saatte bitirirler?")[0] == "problemler"
    assert classify_tr("OBEB(24, 36) kaçtır?")[0] == "sayılar"
    assert classify_tr("cos(2x) = 1/2 denkleminin [0, 2π) aralığındaki çözüm kümesi")[0] == "trigonometri"
    assert classify_tr("A(1,2) ve B(4,6) noktalarından geçen doğrunun denklemi")[0] == "analitik geometri"


def test_degree_and_percent_preclean():
    assert parse_expr_str("sin(30°)") == sp.Rational(1, 2)
    assert parse_expr_str("cos(60 derece)") == sp.Rational(1, 2)
    assert parse_expr_str("%25 * 80") == 20
    assert parse_expr_str("25% * 80") == 20
    assert parse_expr_str("2^10") == 1024
    assert parse_expr_str("√16 + π - pi") == 4
    assert preclean("x² − 5x") == "x**2 - 5x"


def test_unicode_and_ln():
    assert parse_expr_str("ln(E)") == 1
    assert parse_expr_str("3·4") == 12
    assert parse_expr_str("½ + ¼") == sp.Rational(3, 4)


# ------------------------------------------------------------------ LaTeX branch (B8)
def test_latex_obeys_the_same_identifier_allowlist_as_the_canonical_parser():
    """latex2sympy tokenises on its own and applies implicit multiplication, so an undeclared
    name does not fail — it silently becomes a product. Measured: `\frac{zzz}{2}` parsed as
    `z*z*z/2` while the canonical branch rejected `zzz`. A solver writing `\frac{ab}{2}` for a
    single unknown would have had its claim quietly rewritten into something else."""
    from mathverify.normalize.parse import parse_expr_str, build_namespace, ParseError
    ns = build_namespace()
    with pytest.raises(ParseError):
        parse_expr_str(r"\frac{zzz}{2}", ns)
    with pytest.raises(ParseError):
        parse_expr_str(r"\sqrt{qqq}", ns)


def test_latex_still_parses_what_the_problem_declares():
    import sympy as sp
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import parse_expr_str, build_namespace
    ns = build_namespace(ProblemIR.from_dict({"task": {"kind": "evaluate"}, "vars": [{"name": "x"}]}))
    # latex2sympy builds unevaluated Mul/Pow nodes, so compare mathematically, not structurally
    assert sp.simplify(parse_expr_str(r"\frac{\pi}{6}", ns) - sp.pi / 6) == 0
    assert sp.simplify(parse_expr_str(r"\frac{x}{2}", ns) - ns["x"] / 2) == 0
    assert sp.simplify(parse_expr_str(r"\sqrt{2}", ns) - sp.sqrt(2)) == 0


def test_interval_open_is_usable():
    """`open(` was on the forbidden-substring list, which also matched `Interval.open(...)` —
    a form `_ALLOWED_DOTTED` and SOLVER_FORMAT.md both advertise. It was unusable, silently,
    since Phase 1. A bare `open(` must still be refused."""
    import sympy as sp
    from mathverify.normalize.parse import parse_set_str, build_namespace, parse_expr_str, ParseError
    ns = build_namespace()
    assert parse_set_str("Interval.open(1, oo)", ns) == sp.Interval.open(1, sp.oo)
    assert parse_set_str("Interval.Ropen(0, 5)", ns) == sp.Interval.Ropen(0, 5)
    with pytest.raises(ParseError):
        parse_expr_str("open('x')", ns)
