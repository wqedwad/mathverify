"""harness.soundness_fuzz: a missed broken step carries the reason the step layer measured.

The report used to print one fixed explanation for every miss. The classification below is
what the `nedeni açıklanmayan kaçırılan bozuk adım` gate in scripts/check.py reads."""
import json
from pathlib import Path
from types import SimpleNamespace as NS

from harness.soundness_fuzz import ACCEPTED_MISS_REASONS, _missed_step_reason, step_perturbations

ITEMS = Path(__file__).resolve().parents[1] / "evalset" / "items"


def _res(*entries):
    return NS(layers=[NS(layer="certify.algebra", evidence={}),
                      NS(layer="steps.refute", evidence={"steps": list(entries)})])


def test_an_undeclared_symbol_is_named():
    e = {"id": "s2", "status": "skipped",
         "reason": "undeclared_symbol: unknown identifier(s) ['u'] in 'u ' (declare them in the IR)"}
    assert _missed_step_reason(_res(e), "s2", lambda: False) == {
        "status": "skipped", "reason": "undeclared_symbol", "detail": "u"}


def test_unsolved_premises_are_accepted_only_when_the_answer_is_the_empty_set():
    e = {"id": "s2", "status": "unknown", "evidence": {"reason": "premises_inconsistent_or_unsolved"}}
    assert _missed_step_reason(_res(e), "s2", lambda: True)["reason"] == "premises_have_no_solution"
    # a solver that merely failed to solve must not pass as "no solution"
    r = _missed_step_reason(_res(e), "s2", lambda: False)
    assert r["reason"] == "premises_inconsistent_or_unsolved" and r["reason"] not in ACCEPTED_MISS_REASONS


def test_a_verified_or_refuted_broken_step_is_never_an_accepted_miss():
    for status in ("verified", "refuted"):
        r = _missed_step_reason(_res({"id": "s1", "status": status, "evidence": {}}), "s1", lambda: True)
        assert r["reason"] == status and r["reason"] not in ACCEPTED_MISS_REASONS
    assert _missed_step_reason(_res(), "s1", lambda: True)["reason"] == "step_not_in_evidence"
    assert _missed_step_reason(NS(layers=[]), "s1", lambda: True)["reason"] == "steps_layer_absent"


def test_real_misses_are_classified_from_the_step_layer():
    items = [json.loads((ITEMS / f"{i}.json").read_text(encoding="utf-8"))
             for i in ("tyt-den-003", "tyt-den-007")]
    out = step_perturbations(items)
    got = {m["id"]: (m["reason"], m["detail"], m["accepted"]) for m in out["missed_breaks"]}
    assert got == {"tyt-den-003": ("premises_have_no_solution", "", True),
                   "tyt-den-007": ("undeclared_symbol", "u", True)}


# ------------------------------------------------------------------ a difference proved at a point
import pytest  # noqa: E402
import sympy as sp  # noqa: E402

from harness.soundness_fuzz import _differs, _equal, _points, _real_value  # noqa: E402

_n = sp.Symbol("n", integer=True, positive=True)
_x = sp.Symbol("x", real=True)


@pytest.mark.parametrize("a,b,mod_c", [
    (3 ** _n, 3 * 2 ** (_n - 1), False),                            # SymPy's is_zero cannot decide these
    (1 / (_x ** 2 + 1), 2 * _x / (_x ** 2 + 1), False),
    (sp.log(_x) / _x, _x * sp.log(_x) - _x, True),
    (_x ** 3 / 3, _x ** 3 / 3 + _x, True),
])
def test_a_difference_is_proved_by_exact_evaluation_at_a_point(a, b, mod_c):
    """29 Sep 2026: the K4 labeller left 26 wrong options of the dataset `undecided` and this sweep
    dropped 9 wrong variants, because only SymPy's is_zero could prove a difference."""
    assert _differs(a, b, mod_constant=mod_c, var=_x if mod_c else None)


@pytest.mark.parametrize("a,b,mod_c", [
    ((_x ** 2 - 9) / (_x - 3), _x + 3, False),                      # equal wherever both are defined
    (sp.sqrt(_x ** 2), sp.Abs(_x), False),
    (sp.sin(_x) ** 2 + sp.cos(_x) ** 2, sp.Integer(1), False),
    ((-1) ** _n, sp.cos(sp.pi * _n), False),                        # equal on the integers
    (2 ** (_n + 1), 2 * 2 ** _n, False),
    (sp.sqrt(3 + 2 * sp.sqrt(2)) * _x, (1 + sp.sqrt(2)) * _x, False),
    (sp.log(2 * _x), sp.log(_x), True),                             # a constant apart
    (sp.sin(_x) ** 2, -sp.cos(_x) ** 2, True),
])
def test_equal_answers_are_never_proved_different(a, b, mod_c):
    assert not _differs(a, b, mod_constant=mod_c, var=_x if mod_c else None)


_a = sp.Symbol("a", real=True)


@pytest.mark.parametrize("a,b,mod_c", [
    # every part must be real at the point: sqrt(-3)*sqrt(-1) is real, its factors are not
    (sp.sqrt(_x - 1) * sp.sqrt(_x + 1), sp.sqrt(_x ** 2 - 1), False),
    ((_x + _a) ** 3 / 3, _x ** 3 / 3 + _a * _x ** 2 + _a ** 2 * _x, True),   # a**3/3 apart: a constant in x
    (sp.log(sp.Abs(_x)) + sp.sign(_x), sp.log(sp.Abs(_x)), True),        # a constant on each piece
    (sp.oo, sp.oo, False),                                                # oo - oo is nan, it read as "nonzero"
    (sp.Integer(-8) ** sp.Rational(1, 3), sp.Integer(-2), False),         # the real cube root
    (sp.true, _x, False),                                                 # no difference at all: no exception
])
def test_the_auditors_false_differences_are_gone(a, b, mod_c):
    """Adversarial audit of 29 Sep 2026 (DECISIONS §70): each of these was proved "different"."""
    assert not _differs(a, b, mod_constant=mod_c, var=_x if mod_c else None)


def test_the_point_must_be_in_the_problems_domain():
    """x and |x| are the same answer where the problem says x > 0; the grid's x = -1/2 is not a point
    of that problem. Read from the IR: the domain of discourse, a constraint, a given."""
    from harness.soundness_fuzz import admissible_points
    base = {"task": {"kind": "simplify_expression", "params": {"expr": "sqrt(x**2)"}}, "vars": [{"name": "x"}]}
    assert _differs(_x, sp.Abs(_x), admissible=admissible_points(base))
    for ir in (dict(base, domain_of_discourse="x > 0"), dict(base, vars=[{"name": "x", "constraints": ["x > 0"]}]),
               dict(base, givens=["x > 0"])):
        adm = admissible_points(ir)
        assert not _differs(_x, sp.Abs(_x), admissible=adm), ir
        assert _differs(2 * _x, sp.Abs(_x), admissible=adm), ir          # a wrong answer stays wrong
    written = {"task": {"kind": "simplify_expression", "params": {"expr": "sqrt(x)*sqrt(4*x)"}}, "vars": [{"name": "x"}]}
    assert not _differs(2 * sp.Abs(_x), 2 * _x, admissible=admissible_points(written))   # written x >= 0
    seq = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = a(n-1) + 1", "initial": {"2": "0"},
                                                      "var": "n"}}, "vars": [{"name": "n", "domain": "positive_integer"}]}
    assert not _differs(sp.Abs(_n - 2), _n - 2, admissible=admissible_points(seq))      # the sequence starts at 2


def test_the_points_follow_the_symbols_assumptions():
    assert [p[_n] for p in _points({_n})] == [1, 2, 3, 4, 5]
    assert any(p[_x] < 0 for p in _points({_x}))
    y = sp.Symbol("y", positive=True)
    assert all(p[y] > 0 for p in _points({y}))
    assert len(_points({_x, y, sp.Symbol("z", real=True)})) == 64


def test_a_side_undefined_at_the_point_gives_no_value():
    assert _real_value(1 / (_x - sp.Rational(1, 2)), {_x: sp.Rational(1, 2)}) is None
    assert _real_value(sp.log(_x), {_x: -2}) is None
    assert _real_value(sp.sqrt(_x), {_x: -2}) is None
    assert _real_value(sp.log(_x), {_x: 2}) == sp.log(2)


def test_an_infinity_differs_from_a_finite_value_and_from_the_other_infinity():
    """Guarding oo - oo (nan) must not stop oo - 1 (oo) from being nonzero: the first version of the
    guard left the ∞ options of five questions `undecided` (29 Sep 2026)."""
    assert _differs(sp.oo, sp.Integer(1)) and _differs(-sp.oo, sp.oo) and _differs(sp.zoo, sp.Integer(0))
    assert not _differs(sp.oo, sp.oo) and not _differs(-sp.oo, -sp.oo)


# ------------------------------------------------------------------ the oracle's own soundness (audit of 29 Sep 2026)
@pytest.mark.parametrize("a,b", [
    (sp.Integer(10) ** -40, sp.Integer(0)),                                   # the old |N| < 1e-35 called these equal
    (sp.Rational(8, 3), sp.Float("2.666666666666666666666666666666666666667", 40)),
    (sp.E, sp.Float("2.718281828459045235360287471352662497757", 40)),
    (2 * sp.Integer(10) ** -36, sp.Integer(10) ** -36),
])
def test_exact_numbers_are_compared_exactly(a, b):
    assert _differs(a, b) and not _equal(a, b)


def test_a_decimal_is_the_number_it_prints():
    assert _equal(sp.Rational(1, 10), sp.Float("0.1")) and _equal(sp.Rational(3, 8), sp.Float(0.375))


_R = 8 * sp.cos(sp.pi / 9) * sp.cos(2 * sp.pi / 9) * sp.cos(4 * sp.pi / 9)      # exactly 1, SymPy cannot tell


@pytest.mark.parametrize("a,b", [
    (sp.sign(_R - 1), sp.Integer(0)),                                         # N() flips the sign with the precision
    (sp.FiniteSet(4, _R - 2), sp.FiniteSet(-1, 4)),                           # an unevaluated complement
    (sp.Interval(sp.sqrt(11 + 6 * sp.sqrt(2)) - sp.sqrt(2), sp.oo), sp.Interval(3, sp.oo)),
    (sp.FiniteSet(sp.pi / 6 + 2 * sp.Symbol("k", integer=True) * sp.pi),      # the same set over k in Z
     sp.FiniteSet(13 * sp.pi / 6 + 2 * sp.Symbol("k", integer=True) * sp.pi)),
    (sp.Eq(sp.sqrt((_x - 2) ** 2 + (_a + 1) ** 2), 3), sp.Eq((_x - 2) ** 2 + (_a + 1) ** 2, 9)),
])
def test_what_sympy_cannot_reduce_is_no_difference(a, b):
    assert not _differs(a, b)


def test_a_curve_differs_by_a_point_on_it():
    y = sp.Symbol("y", real=True)
    assert _differs(sp.Eq(y, 2 * _x - 1), sp.Eq(y, 2 * _x + 1))
    assert _differs(sp.Eq((_x - 2) ** 2 + (y + 1) ** 2, 9), sp.Eq((_x - 2) ** 2 + (y + 1) ** 2, 3))
    assert not _differs(sp.Eq(y, 2 * _x - 1), sp.Eq(2 * y, 4 * _x - 2))


def test_an_empty_range_is_not_a_point():
    """Sum(1, (k, 1, n - 2)) at n = 1 is -1 under SymPy's Karr convention and 0 read as an empty sum."""
    k = sp.Symbol("k", integer=True, positive=True)
    assert not _differs(sp.Sum(1, (k, 1, _n - 2)), sp.Max(_n - 2, 0))


def test_a_simplification_that_does_not_end_is_cut_off():
    """simplify() of this difference did not return in 120 s; now the sandbox stops it (no decision)."""
    import time
    k = sp.Symbol("k", integer=True, positive=True)
    t = time.time()
    assert not _differs(sp.Sum(1 / sp.factorial(_n - k), (k, 0, _n)), sp.Sum(1 / sp.factorial(k), (k, 0, _n)))
    assert time.time() - t < 90


def test_plus_x_adds_the_tasks_variable_not_the_first_symbol_by_name():
    """With a parameter named a, `plus_x` of an antiderivative was gold + a: a constant apart, not wrong."""
    from harness.soundness_fuzz import variants
    gold = _x ** 2 / 2 + _a * _x
    wrong, _ = variants(gold, "expression", "antiderivative", {"x": _x, "a": _a}, var=_x)
    assert dict(wrong)["plus_x"] == gold + _x


def test_a_parameters_constant_is_no_difference_even_when_sympy_can_tell_it_is_nonzero():
    """d/da (sin(x) + a - sin(x)) = 1 is provably nonzero: differentiating in every symbol called a
    right antiderivative different. Only the variable of integration counts."""
    assert not _differs(sp.sin(_x) + _a, sp.sin(_x), mod_constant=True, var=_x)


def test_a_decimal_truncation_is_not_the_fraction():
    """A Float of 8/3 at double precision subtracts from 8/3 to 0; read as the decimal it prints
    (2.66666666666667), it is not 8/3. The first version exactified the difference, already 0."""
    for f in (sp.Float(8 / 3), sp.Float("2.666666666666666666", 15)):
        assert sp.Rational(8, 3) - f == 0                                # SymPy's own arithmetic
        assert _differs(sp.Rational(8, 3), f) and not _equal(sp.Rational(8, 3), f)
        assert _differs(sp.Matrix([[sp.Rational(8, 3)]]), sp.Matrix([[f]]))


def test_a_tiny_difference_sympy_cannot_decide_is_found_by_the_ladder():
    v = sp.atan(sp.Rational(1, 2)) + sp.atan(sp.Rational(1, 3)) + sp.Integer(10) ** -40
    assert _differs(v, sp.pi / 4) and not _equal(v, sp.pi / 4)


def test_a_sum_is_evaluated_at_a_point():
    k = sp.Symbol("k", integer=True, positive=True)
    assert _differs(sp.Sum(k, (k, 1, _n)), _n ** 2)                      # 3 against 4 at n = 2
    assert not _differs(sp.Sum(k, (k, 1, _n)), _n * (_n + 1) / 2)
