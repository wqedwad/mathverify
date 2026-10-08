"""Round 9 of part d4b (8 Oct 2026): the review of round 8 (attack d4b8, ten findings).

YO-1: an exact intersection that raised (two endpoints neither proved equal nor certainly ordered) dropped a
declared constraint in `Ctx.domain_for`: {-2, 2} was certified for x**2 = 4 under x <= log(8)/log(2) +
exp(-exp(10)), x >= 3; `certified_sign` read the sum one way only, so the order of the constraints decided.
YO-4: a jump function (ceiling, floor, sign, frac, Mod, Heaviside, a Piecewise of constant conditions) of an
exact zero no test proves (Z = 2*atan(tanh(1/2)) - atan(sinh(1)) = gd(1) - gd(1)) was read off rounding noise:
in the parse, by simplify, by SymPy's relations. SymPy's evaluation precision had no ceiling: one verify ran past
90 s in the main process. RK-1 to RK-6: coverage and determinism (a cell's zero written another way, the sampler
blind where an unsolved written condition fails, 300 points and more, factorial and Mod on a finite domain, the
origin convention of atan2/arg under givens, a sampling time set by PYTHONHASHSEED).

The tests marked "56cec1d" fail on the code before the fix (measured: see the commit message).
"""
from __future__ import annotations

import time

import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
x = sp.Symbol("x", real=True)
S = sp.S

NEAR = "log(8)/log(2) + exp(-exp(10))"          # 3 + e^(-e^10)
FAR = "3 + 2*atan(tanh(1/2)) - atan(sinh(1))"     # exactly 3, no exact test proves it
HUGE = "log(8)/log(2) + exp(-exp(exp(5)))"       # 3 + e^(-e^148)
Z = "2*atan(tanh(1/2)) - atan(sinh(1))"          # exactly 0


def V(name="x", dom="real", cons=None):
    v = {"name": name, "domain": dom}
    if cons:
        v["constraints"] = list(cons)
    return v


def _ir(kind, params, vars_=(X,), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def _run(ir, payload, kind="value"):
    return verify(ir, {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []})


def _eq(e, vars_=(X,), givens=(), dod=None):
    return _ir("solve_equation", {"equation": e, "var": "x"}, vars_, givens, "set", dod)


def _ineq(e, vars_=(X,), givens=(), dod=None):
    return _ir("solve_inequality", {"inequality": e, "var": "x"}, vars_, givens, "set", dod)


def _ev(e):
    return _ir("evaluate", {"expr": e})


# --- YO-1 ------------------------------------------------------------------------------------------------------

def test_certified_sign_reads_a_sum_both_ways():                                      # 56cec1d
    from mathverify.equiv.numeric import certified_sign, exact_equal
    a = sp.sympify(NEAR)
    assert certified_sign(a - 3) == 1 and certified_sign(3 - a) == -1
    assert exact_equal(a, 3) is False and exact_equal(3, a) is False


def test_an_unprovable_equal_pair_stays_undecided_both_ways():
    from mathverify.equiv.numeric import certified_sign, exact_equal
    f = sp.sympify(FAR)
    assert certified_sign(f - 3) is None and certified_sign(3 - f) is None
    assert exact_equal(f, 3) is None and exact_equal(3, f) is None


@pytest.mark.parametrize("cons", [[f"x <= {NEAR}", "x >= 3"], ["x >= 3", f"x <= {NEAR}"]])
@pytest.mark.parametrize("ir,claim,kind,bad", [
    (_eq("x**2 = 4"), "{-2, 2}", "set", "CORRECT"),
    (_eq("x**2 = 4"), "EmptySet", "set", "INCORRECT"),
    (_ir("extremum", {"f": "-x**2", "var": "x", "which": "max"}), "0", "value", "CORRECT"),
    (_ir("extremum", {"f": "-x**2", "var": "x", "which": "max"}), "-9", "value", "INCORRECT"),
    (_ineq("x < 5"), f"Interval(-oo, {NEAR})", "interval", "CORRECT"),
    (_ir("count_roots", {"expr": "x**2 - 4", "var": "x"}, shape="count"), "2", "count", "CORRECT"),
])
def test_a_constraint_is_never_dropped(cons, ir, claim, kind, bad):                  # 56cec1d (first order)
    ir = dict(ir, vars=[V("x", "real", cons)])
    assert _run(ir, claim, kind).verdict != bad


@pytest.mark.parametrize("cons", [[f"x <= {FAR}", "x >= 3"], ["x >= 3", f"x <= {FAR}"]])
def test_an_intersection_that_raises_abstains(cons):
    ir = dict(_eq("x**2 = 9"), vars=[V("x", "real", cons)])
    r = _run(ir, "{-3, 3}", "set")
    assert r.verdict == "UNKNOWN"
    assert any("constraint_not_applied" in str((la.evidence or {}).get("reason", "")) for la in r.layers)


def test_constraints_not_applied_lists_the_failed_one():                             # 56cec1d
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(dict(_eq("x**2 = 9"), vars=[V("x", "real", [f"x <= {FAR}", "x >= 3"])])))
    assert ctx.constraints_not_applied() == ["x >= 3"]
    ctx = make_ctx(ProblemIR.from_dict(dict(_eq("x**2 = 9"), vars=[V("x", "real", ["x >= 3", "x <= 5"])])))
    assert ctx.constraints_not_applied() == []


# --- the evaluation budget --------------------------------------------------------------------------------------

def test_evalf_precision_has_a_ceiling():                                             # 56cec1d (hangs)
    from sympy.core.evalf import PrecisionExhausted
    from mathverify.equiv.numeric import certified_sign
    e = sp.sympify(HUGE) - 3
    t = time.time()
    with pytest.raises(PrecisionExhausted):
        e.evalf(30, strict=True)
    assert certified_sign(e) is None
    assert time.time() - t < 30


def test_relations_of_numbers_need_significant_digits():                             # 56cec1d
    z2 = sp.sympify(Z) ** 2
    assert not isinstance(sp.Gt(z2, 0), sp.logic.boolalg.BooleanAtom)
    assert not isinstance(sp.Eq(z2, 0), sp.logic.boolalg.BooleanAtom)
    n = sp.sympify(NEAR)
    assert sp.Gt(n, 3) is sp.true and sp.Le(n, 3) is sp.false and sp.Lt(3, n) is sp.true
    assert sp.Gt(sp.pi, 3) is sp.true and sp.Lt(sp.sqrt(2), sp.Rational(3, 2)) is sp.true


@pytest.mark.parametrize("ir,claim,kind,bad", [
    (dict(_eq("x**2 = 4"), vars=[V("x", "real", [f"x <= {HUGE}", "x >= 3"])]), "{-2, 2}", "set", "CORRECT"),
    (_ev(HUGE), "3", "value", "CORRECT"),
])
def test_a_huge_cancellation_is_bounded(ir, claim, kind, bad):                       # 56cec1d (hangs)
    t = time.time()
    r = _run(ir, claim, kind)
    assert r.verdict != bad and time.time() - t < 60


# --- YO-4 --------------------------------------------------------------------------------------------------------

def test_the_parse_holds_a_jump_of_an_unproved_zero():                                # 56cec1d
    from mathverify.normalize.parse import parse_expr_str
    from mathverify.equiv.numeric import jump_value, undecided_jumps
    e = parse_expr_str(f"ceiling(({Z})**2)")
    assert isinstance(e, sp.ceiling)
    assert jump_value(sp.ceiling(sp.sympify(Z) ** 2, evaluate=False)) is None
    assert undecided_jumps(e) and not undecided_jumps(parse_expr_str("ceiling(pi)"))
    assert parse_expr_str("ceiling(pi)") == 4 and parse_expr_str("floor(log(8)/log(2))") == 3
    assert parse_expr_str("Mod(pi, 3)") == sp.pi - 3 and parse_expr_str("sign(log(8)/log(2) - 3)") == 0


def test_a_piecewise_of_numbers_is_a_jump():                                          # 56cec1d
    from mathverify.equiv.numeric import certified_sign, jump_value
    z2 = sp.sympify(Z) ** 2
    pw = sp.Piecewise((1, sp.Gt(z2, 0)), (0, sp.Le(z2, 0)))
    assert certified_sign(pw - 1) is None
    held = sp.Piecewise((7, sp.Gt(sp.pi, 3, evaluate=False)), (0, True), evaluate=False)
    assert jump_value(held) == 7


def test_sign_of_an_undecided_abs_is_undecided():                                    # 56cec1d
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(sp.sign(sp.Abs(sp.sympify(Z)), evaluate=False)) is None


@pytest.mark.parametrize("e,claim,bad", [
    (f"ceiling(({Z})**2)", "1", "CORRECT"), (f"ceiling(({Z})**2)", "0", "INCORRECT"),
    (f"sign(({Z})**2)", "1", "CORRECT"), (f"sign(({Z})**2)", "0", "INCORRECT"),
    (f"ceiling(sqrt(Abs({Z})))", "1", "CORRECT"), (f"floor(-({Z})**2)", "-1", "CORRECT"),
    (f"floor(-({Z})**2)", "0", "INCORRECT"), (f"sign(Abs({Z}))", "0", "INCORRECT"),
    (f"Piecewise((1, ({Z})**2 > 0), (0, ({Z})**2 <= 0))", "1", "CORRECT"),
    (f"Piecewise((1, ({Z})**2 > 0), (0, ({Z})**2 <= 0))", "0", "INCORRECT"),
])
def test_jumps_of_an_unproved_zero(e, claim, bad):                                   # 56cec1d
    assert _run(_ev(e), claim).verdict != bad


@pytest.mark.parametrize("e,claim,want", [
    ("floor(pi)", "3", "CORRECT"), ("ceiling(log(8)/log(2))", "3", "CORRECT"), ("ceiling(log(8)/log(2))", "4", "INCORRECT"),
    ("Mod(7, 3)", "1", "CORRECT"), ("frac(pi)", "pi - 3", "CORRECT"), ("Piecewise((7, pi > 3), (0, pi <= 3))", "7", "CORRECT"),
])
def test_exact_jumps_keep_their_verdicts(e, claim, want):
    assert _run(_ev(e), claim).verdict == want


# --- RK-1 --------------------------------------------------------------------------------------------------------

def test_a_cell_zero_written_another_way():                                           # 56cec1d
    from mathverify.equiv.sets import set_equal
    from mathverify.sandbox.exactsets import exact_solveset
    got = exact_solveset(sp.Le(sp.Abs(x - 3) * (2 ** x - 8), 0), x, S.Reals)
    assert set_equal(got, sp.Interval(-sp.oo, 3))[0] is True


@pytest.mark.parametrize("e,claim,want", [
    ("Abs(x - 3)*(2**x - 8) <= 0", "Interval(-oo, 3)", "CORRECT"),
    ("Abs(x - 3)*(2**x - 8) <= 0", "Interval.open(-oo, 3)", "INCORRECT"),
    ("sign(x - 3)*(2**x - 8) >= 0", "Reals", "CORRECT"),
    ("Max(x, 3)*(2**x - 8) <= 0", "Interval(-oo, 3)", "CORRECT"),
])
def test_rk1_verdicts(e, claim, want):                                                # 56cec1d (CORRECT ones)
    assert _run(_ineq(e), claim, "interval").verdict == want


def test_rk1_count_integers():                                                        # 56cec1d
    ir = _ir("count_integers", {"var": "x"}, [V("x", "integer")], ["Abs(x - 3)*(2**x - 8) <= 0", "x >= -5", "x <= 10"],
             "count")
    assert _run(ir, "9", "count").verdict == "CORRECT"
    assert _run(ir, "8", "count").verdict == "INCORRECT"


# --- RK-2 and RK-6 -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("e,claim", [
    ("sqrt(2**x - x - 1) >= 0", "Reals"), ("acos(x + atan(x)) >= 0", "Reals"), ("acos(2**x + x - 2) >= 0", "Interval(0, 2)"),
])
def test_a_claim_over_an_unsolved_condition_is_refuted(e, claim):                    # 56cec1d
    assert _run(_ineq(e), claim, "interval").verdict == "INCORRECT"


def test_a_right_claim_over_an_unsolved_condition_is_not_refuted():
    assert _run(_ineq("acos(2**x + x - 2) >= 0"), "Interval(0, 1)", "interval").verdict != "INCORRECT"


def test_a_declared_constraint_stays_a_condition_of_the_sample():
    # inside the claim only the written definedness is left to the relation; a point off a declared (or given)
    # condition is no point of the problem: sin(x) > 0 under sin(x) > 0 is refuted nowhere in [-4, 4]
    from mathverify.certify.algebra import _sample_inequality
    c = sp.Gt(sp.sin(x), 0)
    dom = sp.Intersection(sp.Interval(-4, 4), sp.ConditionSet(x, c, S.Reals))
    ok, ev = _sample_inequality(c, x, sp.Interval(-4, 4), dom, 7, written=[])
    assert ok is not False, ev
    ok, ev = _sample_inequality(c, x, sp.Interval(-4, 4), dom, 7, written=[c])
    assert ok is False and ev["counterexample"][0] == "inside_but_false"


def test_the_sampler_never_asks_sympy_for_a_conditionset_member(monkeypatch):        # 56cec1d
    from sympy.sets.conditionset import ConditionSet
    from mathverify.certify.algebra import _sample_inequality

    def boom(self, other):
        raise AssertionError("ConditionSet membership asked")
    monkeypatch.setattr(ConditionSet, "_contains", boom)
    cond = sp.Le(2 ** x + x - 2, 1)
    dom = sp.Intersection(sp.Interval(0, sp.oo), sp.ConditionSet(x, cond, S.Reals))
    rel = sp.Le((sp.Abs(x) - x) * sp.acos(2 ** x + x - 2), 0)
    ok, ev = _sample_inequality(rel, x, sp.Interval(0, sp.oo), dom, 7, written=[cond])
    assert ok is False and ev["counterexample"][0] == "inside_but_false"


def test_rk6_is_quick():
    ir = _ineq("(Abs(x) - x)*(acos(2**x + x - 2) + asin(x + atan(x)) + acos(x*exp(x)) + asin(3**x + x - 2)) <= 0",
               vars_=[V("x", "real", ["x >= 0"])])
    t = time.time()
    assert _run(ir, "Interval(0, oo)", "interval").verdict != "CORRECT"
    assert time.time() - t < 30


# --- RK-3 --------------------------------------------------------------------------------------------------------

def test_endpoints_apart():
    from mathverify.equiv.sets import endpoints_apart
    pts = sp.FiniteSet(*[k * sp.pi for k in range(300)])
    assert endpoints_apart([pts, sp.Interval(0, 940)], 1000)
    assert not endpoints_apart([sp.FiniteSet(3, sp.log(8) / sp.log(2))], 1000)
    assert not endpoints_apart([pts], 100)
    assert endpoints_apart([sp.FiniteSet(*range(500))], 1000)


@pytest.mark.parametrize("e,hi,claim,want", [
    ("sin(x)", "940", "300", "CORRECT"), ("sin(x)", "940", "299", "INCORRECT"), ("cos(x)", "1000", "318", "CORRECT"),
    ("sin(pi*x)", "300", "301", "CORRECT"),
])
def test_many_points_are_counted(e, hi, claim, want):                                # 56cec1d
    ir = _ir("count_roots", {"expr": e, "var": "x", "lo": "0", "hi": hi}, shape="count")
    assert _run(ir, claim, "count").verdict == want


# --- RK-4 --------------------------------------------------------------------------------------------------------

def test_on_points_reads_factorial_and_mod():                                         # 56cec1d
    from mathverify.sandbox.exactsets import _on_points
    pts = sp.FiniteSet(1, 2, 3, 4, 5, 6)
    assert _on_points(sp.Ne(sp.sin(sp.pi * x / 2) * sp.factorial(x), 0), x, pts) == [1, 3, 5]
    assert _on_points(sp.Gt(sp.cos(sp.pi * x) * sp.Mod(x, 4), 0), x, pts) == [2, 6]
    # a convention at a point: undecided (Mod by a negative number)
    assert _on_points(sp.Gt(sp.Mod(x, x - 3), 0), x, pts) is None


@pytest.mark.parametrize("kind,key,e,given,claim,want", [
    ("solve_equation", "equation", "x**2 - 5*x + 6 = 0", "sin(pi*x/2)*factorial(x) != 0", "{3}", "CORRECT"),
    ("solve_equation", "equation", "x**2 - 5*x + 6 = 0", "sin(pi*x/2)*factorial(x) != 0", "{2, 3}", "INCORRECT"),
    ("solve_equation", "equation", "x**2 - 5*x + 6 = 0", "cos(pi*x)*Mod(x, 4) > 0", "{2}", "CORRECT"),
    ("solve_inequality", "inequality", "x**2 < 20", "sin(x)*factorial(x) > 0", "{1, 2, 3}", "CORRECT"),
])
def test_rk4_verdicts(kind, key, e, given, claim, want):                               # 56cec1d (CORRECT ones)
    ir = _ir(kind, {key: e, "var": "x"}, (X,), [given], "set", "{1, 2, 3, 4, 5, 6}")
    assert _run(ir, claim, "set").verdict == want


# --- RK-5 --------------------------------------------------------------------------------------------------------

XY = (X, V("y"))


@pytest.mark.parametrize("ir,claim,want", [
    (_ir("derivative", {"f": "atan2(y, x)", "var": "x", "at": "0"}, XY, ["y = 2"]), "-1/2", "CORRECT"),
    (_ir("derivative", {"f": "atan2(y, x)", "var": "x", "at": "0"}, XY, ["y = 2"]), "1/2", "INCORRECT"),
    (_ir("derivative", {"f": "atan2(y, x)", "var": "x"}, XY, ["y = 2"], "expression"), "-2/(x**2 + 4)", "CORRECT"),
    (_ir("extremum", {"f": "atan2(x, y)", "var": "x", "which": "max", "interval": "[0, 1]"}, XY, ["y = 1"]), "pi/4", "CORRECT"),
    (_ir("limit", {"expr": "atan2(y, x)", "var": "x", "to": "0"}, XY, ["y = 1"]), "pi/2", "CORRECT"),
    (_ir("derivative", {"f": "atan2(x - 1, 0)", "var": "x", "at": "2"}), "0", "CORRECT"),
])
def test_rk5_verdicts(ir, claim, want):                                                # 56cec1d (CORRECT ones)
    assert _run(ir, claim).verdict == want


def test_rk5_the_convention_point_stays_undecided():
    assert _run(_ir("derivative", {"f": "atan2(x, 0)", "var": "x", "at": "0"}), "0").verdict == "UNKNOWN"


def test_origin_avoided():
    from mathverify.certify.limits import _origin_avoided, neighbourhoods
    assert _origin_avoided(x ** 2 + 4, x, [])
    assert _origin_avoided((x - 1) ** 2, x, neighbourhoods(sp.Integer(2)))
    assert not _origin_avoided((x - 1) ** 2, x, neighbourhoods(sp.Integer(1)))
    assert not _origin_avoided(x ** 2, x, [])


# --- the guards one by one ---------------------------------------------------------------------------------------

def test_two_readings_that_disagree_decide_nothing(monkeypatch):
    from mathverify.equiv import numeric
    one = (sp.Float(1, 30), sp.Integer(0), "value", "zero")
    monkeypatch.setattr(numeric, "_evalf_strict", lambda e: one)     # e and -e both read +1: a contradiction
    assert numeric._evalf_sign(sp.sympify("sqrt(2) - 1"), 5.0) is None


def test_a_rebuilt_jump_is_resolved_again_not_read_off_the_noise():                 # 56cec1d
    from mathverify.equiv.numeric import certified_sign
    z2 = sp.sympify(Z) ** 2
    inner = sp.floor(sp.pi, evaluate=False)
    assert certified_sign(sp.ceiling(z2 + inner - 3, evaluate=False) - 1) is None


def test_a_latex_jump_is_held_through_substitution():                                 # 56cec1d
    from mathverify.normalize.parse import _SAFE_NAMES, parse_expr_str
    xs = sp.Symbol("x", real=True)
    e = parse_expr_str(r"\lceil (2\arctan(\tanh(1/2)) - \arctan(\sinh(1)))^2 \cdot x \rceil", dict(_SAFE_NAMES, x=xs))
    assert e.subs(xs, 1) != 1


def test_an_equation_on_a_domain_written_another_way():                               # 56cec1d
    from mathverify.sandbox.exactsets import exact_solveset
    assert exact_solveset(sp.Eq(x ** 2, 9), x, sp.Interval(sp.log(8) / sp.log(2), sp.oo)) == sp.FiniteSet(3)


def test_endpoints_apart_refuses_complex_values():
    from mathverify.equiv.sets import endpoints_apart
    assert not endpoints_apart([sp.FiniteSet(sp.I * 10 ** 12, sp.Rational(1, 1000) + sp.I * 10 ** 12)], 100)


def test_on_points_drops_a_point_where_factorial_is_undefined():                     # 56cec1d
    from mathverify.sandbox.exactsets import _on_points
    assert _on_points(sp.Ge(x * sp.factorial(x - 3), 0), x, sp.FiniteSet(1, 2, 3, 4, 5, 6)) == [3, 4, 5, 6]


def test_extremum_away_from_the_origin_convention():                                 # 56cec1d
    ir = _ir("extremum", {"f": "x + 0*atan2(x - 1, 0)", "var": "x", "which": "max", "interval": "[2, 3]"})
    assert _run(ir, "3").verdict == "CORRECT"
    ir = _ir("extremum", {"f": "x + 0*atan2(x - 1, 0)", "var": "x", "which": "max", "interval": "[0, 3]"})
    assert _run(ir, "3").verdict == "UNKNOWN"             # the convention point 1 is in [0, 3]


def test_outside_the_claim_a_point_needs_every_condition():
    from mathverify.certify.algebra import _sample_inequality
    c = sp.Gt(sp.sin(x), 0)
    dom = sp.Intersection(sp.Interval(-4, 4), sp.ConditionSet(x, c, S.Reals))
    truth = sp.Union(sp.Interval.Ropen(-4, -sp.pi), sp.Interval.open(0, sp.pi))
    ok, ev = _sample_inequality(sp.Ge(x, -100), x, truth, dom, 7, written=[])
    assert ok is not False, ev
