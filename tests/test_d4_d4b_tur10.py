"""Round 10 of part d4b (9 Oct 2026): the attack on round 9 (d4b9, six findings).

YO-1: SymPy's strict evalf checks the accuracy of the nodes it has an evaluator for (Add, Mul, Pow, exp, log, sin,
cos, tan, atan, Abs, re, im, ...); asin, sinh, tanh, erf, atan2, Max, ... are evaluated with their argument read
without accuracy tracking and reported at full precision, so the sign of an exact 0 (asin(log 6 - log 2 - log 3))
was certified and ceiling(asin(Q)) = 1 CORRECT. YO-2: SymPy decided a relation of numbers through the assumption
system's non-strict fallback (sin(Z)**2 > 0 True for Z = gd(1) - gd(1) = 0). RK-1: the interval rule base > 0 of
x**x and x**sqrt(2) read at a point dropped (-2)**(-2) and 0**sqrt(2). RK-2: the precision budget raised out of
non-strict evaluations (Abs, Max, Interval of a number 86396 bits from 3 did not parse). RK-3: SymPy joins the
intervals of a union pair by pair (160 of them took 170 s). RK-4: a dropped constraint that alone refutes a claim.

The tests marked "fecc2be" fail on the code before the fix (measured: see the commit message).
"""
from __future__ import annotations

import time

import pytest
import sympy as sp
from sympy.core.evalf import PrecisionExhausted

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
x = sp.Symbol("x", real=True)
S = sp.S

Q = "(log(6) - log(2) - log(3))"                  # exactly 0
A = "(atan(1/2) + atan(1/3) - pi/4)"               # exactly 0
P = "(log(4) - 2*log(2))"                          # exactly 0
L = "(log(8)/log(2) - 3)"                          # exactly 0
Z = "(2*atan(tanh(1/2)) - atan(sinh(1)))"          # exactly 0 (gd(1) twice)
E11 = "log(8)/log(2) + exp(-exp(11))"              # 3 + e^(-e^11), 86396 bits from 3
E12 = "log(8)/log(2) + exp(-exp(12))"              # past the precision budget
FAR = "3 + 2*atan(tanh(1/2)) - atan(sinh(1))"      # exactly 3, no exact test proves it
D7 = "{-3, -2, -1, 0, 1, 2, 3}"


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


def _run(ir, payload, kind="value", steps=()):
    return verify(ir, {"claimed_answer": {"kind": kind, "payload": payload},
                       "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                                 for i, (k, c) in enumerate(steps)]})


def _ev(e, givens=(), vars_=(X,)):
    return _ir("evaluate", {"expr": e}, vars_, givens)


def _eq(e, vars_=(X,), givens=(), dod=None):
    return _ir("solve_equation", {"equation": e, "var": "x"}, vars_, givens, "set", dod)


def _step_status(r):
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    steps = layer.evidence.get("steps", []) if layer is not None else []
    return steps[-1].get("status") if steps else None


def _pw(u):
    return f"Piecewise((1, {u} > 0), (0, {u} <= 0))"


# --- YO-1: strict evalf at a node SymPy does not track ------------------------------------------------------------

@pytest.mark.parametrize("e", [f"asin({Q})", f"sinh({L})", f"tanh({P})", f"erf({Q})", f"atan2({Q}, 1)", f"Max({Q}, 0)",
                               f"acot({Q}) - pi/2", f"cosh({Q}) - 1", f"asinh({L})", f"atanh({P})"])
def test_strict_evalf_of_an_untracked_node_of_an_exact_zero_decides_nothing(e):            # fecc2be
    with pytest.raises(PrecisionExhausted):
        sp.sympify(e).evalf(30, strict=True)


@pytest.mark.parametrize("e", ["asin(1/3)", "acos(1/3)", "sinh(2) - 3", "cosh(1/2)", "tanh(3)", "coth(2)", "sech(1)",
                               "csch(1)", "asinh(-5)", "acosh(3)", "atanh(1/2)", "acoth(3)", "acot(-2)", "asec(3)",
                               "acsc(-3)", "atan2(1, -1)", "atan2(-1, -1)", "atan2(1, 0)", "sec(1)", "csc(1)", "cot(1)",
                               "Max(1, sqrt(2))", "Min(1, sqrt(2), 3/2)", "asin(1)", "acos(-1)"])
def test_strict_evalf_keeps_its_value_where_the_argument_is_certain(e):
    import mpmath as mp
    v = sp.sympify(e)
    with mp.workdps(40):
        want = mp.mpf(sp.N(v, 40))
    got = v.evalf(30, strict=True)
    assert abs(mp.mpf(got) - want) <= mp.mpf(10) ** -25 * (1 + abs(want))


def test_a_complex_trig_argument_and_an_untracked_sum_decide_nothing():                    # fecc2be
    with pytest.raises(PrecisionExhausted):
        sp.sympify(f"log(-1 + I*{Q})").evalf(30, strict=True)        # ±i*pi by the sign of the noise
    with pytest.raises(PrecisionExhausted):
        sp.Integral(x, (x, 0, 1)).evalf(30, strict=True)            # no strict evaluation of a quadrature
    with pytest.raises(PrecisionExhausted):
        sp.sympify(f"sin(1 + I*{Q})").evalf(30, strict=True)


@pytest.mark.parametrize("e,s", [(f"asin({Q})", 0), (f"asin({Q}) - 1", -1), (f"tanh({P})", 0), (f"sinh({L})**2", 0),
                                 (f"erf({Q})", 0), (f"acot({Q})", 1), (f"cosh({Q}) - 1", 0), (f"atan2({Q}, -1) - pi", 0),
                                 (f"Max({Q}, 0)", 0), (f"2 + tanh({P}) - 2", 0)])
def test_certified_sign_reads_an_untracked_node_at_its_exact_zero(e, s):                     # fecc2be
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(sp.sympify(e), 20) == s


@pytest.mark.parametrize("e", [f"asin({A})", f"sinh({A})", f"tanh(2*atan(1/3) - atan(3/4)) + 0*{A}"])
def test_certified_sign_never_reads_noise(e):
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(sp.sympify(e), 20) in (0, None)


def test_jump_values_of_untracked_nodes():                                                     # fecc2be
    from mathverify.equiv.numeric import jump_value
    assert jump_value(sp.ceiling(sp.sympify(f"asin({Q})"), evaluate=False)) == 0
    assert jump_value(sp.sign(sp.sympify(f"asin({L})"), evaluate=False)) == 0
    assert jump_value(sp.Mod(sp.sympify(f"tanh({P}) + 5"), 5, evaluate=False)) == 0


@pytest.mark.parametrize("e,good,bad", [
    (f"ceiling(asin({Q}))", "0", "1"), (f"floor(-sinh({A}))", None, "-1"), (f"sign(asin({Q}))", "0", "1"),
    (f"ceiling(sinh({L})**2)", "0", "1"), (f"Mod(tanh({P}) + 5, 5)", "0", f"5 + tanh({P})"),
    (f"floor(asin({Q})) + ceiling(asin({Q}))", "0", "1"), (f"sign(asin({L}))", "0", "-1"),
    (f"atan2(-tan({L}**2), -1)", "pi", "-pi"), (f"ceiling(acot({Q}))", "2", "1")])
def test_jumps_of_an_untracked_node_at_an_exact_zero(e, good, bad):                          # fecc2be
    assert _run(_ev(e), bad).verdict != "CORRECT"
    if good is not None:
        assert _run(_ev(e), good).verdict != "INCORRECT"


def test_a_constraint_at_an_exact_zero_of_tanh():                                              # fecc2be
    vs = (V("x", "real", [f"x > 2 + tanh({P})"]),)
    assert _run(_eq("x**2 = 4", vs), "{2}", "set").verdict != "CORRECT"
    assert _run(_eq("x**2 = 4", vs), "EmptySet", "set").verdict != "INCORRECT"
    vs = (V("x", "real", [f"x > 3 + sinh({L})"]),)
    assert _run(_eq("x**2 = 9", vs), "{3}", "set").verdict != "CORRECT"


def test_an_equation_and_a_step_through_an_untracked_node():                                   # fecc2be
    assert _run(_eq(f"x = ceiling(asin({Q})) + 2"), "{3}", "set").verdict != "CORRECT"
    assert _run(_eq(f"x = ceiling(asin({Q})) + 2"), "{2}", "set").verdict != "INCORRECT"
    r = _run(_ev("x + 1", ["x = 2"]), "3", steps=[("compute", f"sign(asin({Q})) = 1")])
    assert _step_status(r) != "verified"
    r = _ev("ceiling(y)", [f"y = asin({Q})"], (V("y"),))
    assert _run(r, "1").verdict != "CORRECT"


def test_a_polynomial_whose_leading_coefficient_may_be_zero():                                 # fecc2be
    from mathverify.sandbox.exactsets import certified_degree
    with pytest.raises(ValueError):
        certified_degree(sp.Poly(x * sp.asin(sp.sympify(Q)), x))
    assert certified_degree(sp.Poly(sp.sqrt(2) * x - 1, x)).degree() == 1
    assert _run(_eq(f"x*asin({Q}) = 0"), "{0}", "set").verdict != "CORRECT"
    assert _run(_eq(f"x*asin({Q}) = 0"), "Reals", "set").verdict != "INCORRECT"
    cr = _ir("count_roots", {"expr": f"x*tanh({P})", "var": "x"}, (X,), (), "count")
    assert _run(cr, "1", "count").verdict != "CORRECT"


def test_latex_jumps_of_an_untracked_node():                                                   # fecc2be
    s = r"\lceil \sinh(\frac{\ln 8}{\ln 2} - 3)^2 \rceil"
    assert _run(_ev(s), "1").verdict != "CORRECT"
    assert _run(_ev(s), "0").verdict != "INCORRECT"


def test_the_controls_keep_their_verdicts():
    assert _run(_ev("ceiling(10*asin(1/2))"), "6").verdict == "CORRECT"
    assert _run(_ev("floor(acosh(3))"), "1").verdict == "CORRECT"
    assert _run(_ev("sign(Max(1, sqrt(2)) - 1)"), "1").verdict == "CORRECT"
    assert _run(_eq("x**2 = 4", (V("x", "real", ["x > 2 + tanh(1)"]),)), "EmptySet", "set").verdict == "CORRECT"


# --- YO-2: relations of numbers ---------------------------------------------------------------------------------

@pytest.mark.parametrize("u", [f"sin({Z})**2", f"atan({Z})**2", f"sin({Z}**2)", f"tan({L}**2)", f"{Z}**2",
                               f"cosh({Q}) - 1", f"asin({Q})"])
def test_a_relation_of_an_exact_zero_stays_unevaluated(u):                                    # fecc2be
    import sympy.core.relational as R
    e = sp.sympify(u)
    assert isinstance(sp.Gt(e, 0), sp.core.relational.Relational)
    assert e.is_extended_positive is not True
    assert R._n2(e, S.Zero) is None
    assert sp.simplify(sp.Gt(e, 0)) is not sp.true


@pytest.mark.parametrize("u", [f"sin({Z})**2", f"atan({Z})**2", f"tan({L}**2)"])
def test_a_piecewise_of_an_exact_zero(u):                                                    # fecc2be
    assert _run(_ev(_pw(u)), "1").verdict != "CORRECT"
    assert _run(_ev(_pw(u)), "0").verdict != "INCORRECT"


def test_a_piecewise_step_and_its_equation():                                                  # fecc2be
    pw = _pw(f"sin({Z})**2")
    assert _step_status(_run(_ev("x + 1", ["x = 2"]), "3", steps=[("compute", f"{pw} = 1")])) != "verified"
    assert _run(_ev(f"5*{pw} + 2"), "7").verdict != "CORRECT"
    assert _run(_eq(f"x = {pw}"), "{1}", "set").verdict != "CORRECT"


def test_an_interval_ending_at_an_exact_zero_is_not_empty():                                  # fecc2be
    assert not sp.Interval(0, -sp.tan(sp.sympify(L) ** 2)).is_empty
    assert _run(_eq("x**2 + 1 = 0"), f"Interval(0, -tan({L}**2))", "interval").verdict != "CORRECT"
    assert _run(_eq("x**2 + 1 = 0"), f"Interval(0, asin({Q}))", "interval").verdict != "CORRECT"


def test_equals_does_not_call_an_exact_zero_nonzero():                                        # fecc2be
    assert sp.sympify(f"asin({Q})").equals(0) is not False


def test_relations_of_numbers_still_decide():
    assert sp.Gt(sp.sqrt(2), 1) is sp.true
    assert sp.Lt(sp.pi, sp.Rational(22, 7)) is sp.true
    assert sp.Interval(0, sp.Rational(-1, 2)) is S.EmptySet
    assert (sp.sqrt(2) - 1).is_positive is True
    assert sp.Abs(1 - sp.sqrt(2)) == sp.sqrt(2) - 1
    assert sp.Max(sp.pi, 3) == sp.pi


# --- RK-1: definedness at a point -------------------------------------------------------------------------------

def test_the_real_power_convention_at_points():                                                # fecc2be
    from mathverify.certify.domain import REAL_POWER, definedness_conditions
    assert sp.Contains(sp.Tuple(-2, -2), REAL_POWER) is sp.true
    assert sp.Contains(sp.Tuple(0, 2), REAL_POWER) is sp.true
    assert sp.Contains(sp.Tuple(0, 0), REAL_POWER) is not sp.true           # 0**0
    assert sp.Contains(sp.Tuple(-2, sp.Rational(1, 3)), REAL_POWER) is not sp.true
    assert sp.Contains(sp.Tuple(x, x), REAL_POWER) in definedness_conditions(x ** x, x)


def test_points_read_before_the_power_is_formed():                                             # fecc2be
    from mathverify.sandbox.exactsets import _on_points
    e = x ** x * (2 + sp.sin(x))
    assert _on_points(sp.Gt(e, 0), x, sp.FiniteSet(-2, -1, 1, 2)) == [-2, 1, 2]
    assert _on_points(sp.Gt(e, 0), x, sp.FiniteSet(-2, 0, 2)) is None           # 0**0
    assert _on_points(sp.Ge(x ** sp.sqrt(2) * (2 + sp.sin(x)), 0), x, sp.FiniteSet(-2, -1, 0, 1, 2)) is None


@pytest.mark.parametrize("e,given,dod,right,wrong", [
    ("(x + 2)*(x - 2) = 0", "x**x*(2 + sin(x)) > 0", D7, "{-2, 2}", "{2}"),
    ("(x + 1)*(x - 1) = 0", "x**x*(2 + sin(x)) < 0", D7, "{-1}", "EmptySet"),
    ("(x - 2)*(x - 5) = 0", "(x - 4)**x*factorial(x)*(2 + sin(x)) > 0", "{1, 2, 3, 4, 5, 6}", "{2, 5}", "{5}"),
    ("x*(x - 2) = 0", "x**sqrt(2)*(2 + sin(x)) >= 0", "{0, 1, 2, 3}", "{0, 2}", "{2}"),
    ("(x + 1)*(x - 3) = 0", "Abs(x - 3)**sqrt(2)*(2 + sin(x)) >= 0", "{-1, 0, 1, 2, 3}", "{-1, 3}", "{-1}"),
    ("(x + 2)*(x - 3) = 0", "(x - 3)**(x + 4)*cos(pi*x) > 0", D7, "{-2}", "EmptySet")])
def test_a_finite_domain_with_a_real_power(e, given, dod, right, wrong):                       # fecc2be
    ir = _eq(e, givens=[given], dod=dod)
    assert _run(ir, right, "set").verdict != "INCORRECT"
    assert _run(ir, wrong, "set").verdict != "CORRECT"


def test_zero_to_the_zero_is_undecided():                                                      # fecc2be
    ir = _eq("x*(x - 2) = 0", givens=["x**x*(2 + sin(x)) > 0"], dod="{0, 1, 2, 3}")
    assert _run(ir, "{2}", "set").verdict == "UNKNOWN"
    assert _run(ir, "{0, 2}", "set").verdict == "UNKNOWN"
    ci = _ir("count_integers", {"var": "x"}, (V("x", "integer"),), ["x**x*(2 + sin(x)) > 0", "x >= -3", "x <= 3"], "count")
    for c in ("3", "4", "5"):
        assert _run(ci, c, "count").verdict == "UNKNOWN"
    si = _ir("solve_inequality", {"inequality": "x**sqrt(2)*(2 + sin(x)) >= 0", "var": "x"}, (X,), (), "set", "{0, 1, 2, 3}")
    assert _run(si, "{0, 1, 2, 3}", "set").verdict != "INCORRECT"
    assert _run(si, "{1, 2, 3}", "set").verdict != "CORRECT"


def test_a_root_at_a_negative_integer_on_the_line():                                           # fecc2be
    assert _run(_eq("x**x = 1/4"), "{-2}", "set").verdict != "INCORRECT"
    assert _run(_eq("x**x = 1/4"), "EmptySet", "set").verdict != "CORRECT"
    assert _run(_eq("x**x = -1"), "{-1}", "set").verdict != "INCORRECT"
    assert _run(_eq("x**sqrt(2) = 0"), "{0}", "set").verdict == "UNKNOWN"


def test_real_powers_away_from_their_convention_points():
    assert _run(_ir("derivative", {"f": "x**x", "var": "x", "at": "1"}), "1").verdict == "CORRECT"
    assert _run(_ir("derivative", {"f": "x**sqrt(2)", "var": "x", "at": "1"}), "sqrt(2)").verdict == "CORRECT"
    assert _run(_ev("x**x", ["x = 2"]), "4").verdict == "CORRECT"
    assert _run(_ev("x**x", ["x = 0"]), "1").verdict == "UNKNOWN"


# --- RK-2: the precision budget ---------------------------------------------------------------------------------

def test_a_non_strict_evaluation_past_the_budget_raises_nothing():                              # fecc2be
    e = sp.sympify(E12) - 3
    sp.N(e, 5)
    assert isinstance(sp.Abs(e), sp.Abs)
    sp.Max(3, sp.sympify(E12))
    sp.Interval(3, sp.sympify(E12))
    with pytest.raises(PrecisionExhausted):
        e.evalf(30, strict=True)
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(e) is None


def test_a_number_within_the_budget_is_decided():                                             # fecc2be
    ab = f"Abs({E11} - 3)"
    assert _run(_ir("evaluate", {"expr": ab}, ()), "exp(-exp(11))").verdict == "CORRECT"
    assert _run(_ir("evaluate", {"expr": ab}, ()), "1").verdict == "INCORRECT"
    assert _run(_ir("evaluate", {"expr": f"Max(3, {E11})"}, ()), "4").verdict == "INCORRECT"
    assert _run(_ev("x + 1", [f"x = {ab}"]), "1").verdict == "INCORRECT"
    assert _run(_eq("x**2 = 4", (V("x", "real", [f"x >= {ab}"]),)), "{2}", "set").verdict == "CORRECT"


# --- RK-3: the cost of set operations ---------------------------------------------------------------------------

def test_a_union_of_many_intervals_is_left_unsolved_fast():                                    # fecc2be (> 100 s)
    from mathverify.sandbox.exactsets import SET_PIECES, exact_intersection, exact_solveset
    t = time.time()
    s = exact_solveset(sp.Gt(sp.sin(x), 0), x, sp.Interval(0, 1000))
    assert isinstance(s, sp.ConditionSet)
    assert time.time() - t < 30
    s = exact_solveset(sp.Gt(sp.sin(x), 0), x, sp.Interval(0, 100))
    assert isinstance(s, sp.Union) and len(s.args) == 16
    many = sp.Union(*[sp.Interval(2 * k, 2 * k + 1) for k in range(SET_PIECES + 1)])
    with pytest.raises(TypeError):
        exact_intersection(many, sp.Interval(0, 10))


def test_the_joined_cells_are_the_union():
    from mathverify.sandbox.exactsets import exact_solveset
    s = exact_solveset(sp.Ge(sp.sin(x) * sp.cos(x), 0), x, sp.Interval(0, 2 * sp.pi))
    want = sp.Union(sp.Interval(0, sp.pi / 2), sp.Interval(sp.pi, 3 * sp.pi / 2), sp.FiniteSet(2 * sp.pi))
    assert sp.Complement(s, want) is S.EmptySet and sp.Complement(want, s) is S.EmptySet


def test_a_given_with_160_intervals_answers_in_time():                                         # fecc2be (> 100 s)
    t = time.time()
    ir = _ir("solve_equation", {"equation": "cos(x) = 0", "var": "x"}, (V("x", "real", ["x >= 0", "x <= 1000"]),),
             ["sin(x) > 0"], "set")
    assert _run(ir, "{pi/2}", "set").verdict != "CORRECT"
    assert time.time() - t < 60


# --- RK-4: a constraint that could not be applied -----------------------------------------------------------------

@pytest.mark.parametrize("cons", [[f"x <= {FAR}", "x >= 3"], ["x >= 3", f"x <= {FAR}"]])
def test_a_claimed_root_outside_a_constraint_read_alone(cons):                                  # fecc2be
    vs = (V("x", "real", cons),)
    assert _run(_eq("x**2 = 9", vs), "{-3, 3}", "set").verdict == "INCORRECT"
    assert _run(_eq("x + 1 = 0", vs), "{-1}", "set").verdict == "INCORRECT"
    assert _run(_eq("x**2 = 9", vs), "{3}", "set").verdict != "INCORRECT"
