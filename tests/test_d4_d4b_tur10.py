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

@pytest.mark.parametrize("e", [f"asin({Q})", f"sinh({L})", f"tanh({P})", f"erf({Q})", f"atan2({Q}, 1)",
                               f"Max(sin({Q}), 0)", f"acot({Q}) - pi/2", f"cosh({Q}) - 1", f"asinh({L})", f"atanh({P})"])
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
    with mp.workdps(50):
        want = mp.mpf(sp.N(v, 50)._mpf_) if v != 0 else mp.mpf(0)
        got = mp.mpf(v.evalf(30, strict=True)._mpf_)
        assert abs(got - want) <= mp.mpf(10) ** -25 * (1 + abs(want))


@pytest.mark.parametrize("e", ["log(-1 + I*log(6) - I*log(2) - I*log(3))",     # i*pi or -i*pi by the noise's sign
                               "sqrt(-1 + I*log(6) - I*log(2) - I*log(3))",    # i or -i
                               "sin(pi + I*log(6) - I*log(2) - I*log(3))"])    # an imaginary part of noise
def test_a_complex_argument_on_a_branch_cut_decides_nothing(e):                              # fecc2be
    with pytest.raises(PrecisionExhausted):
        sp.sympify(e).evalf(30, strict=True)
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(sp.im(sp.sympify(e)), 20) in (0, None)


def test_a_quadrature_is_no_strict_evaluation():                                              # fecc2be
    with pytest.raises(PrecisionExhausted):
        sp.Integral(x, (x, 0, 1)).evalf(30, strict=True)


def test_no_untracked_fallback_inside_a_strict_evaluation():                                   # fecc2be
    # SymPy's evaluator of a Piecewise raises NotImplementedError; EvalfMixin.evalf then evaluated the whole
    # expression without accuracy tracking (asin of noise) and "checked" the rounded number
    with pytest.raises(PrecisionExhausted):
        sp.Piecewise((sp.asin(sp.sympify(Q)), True), evaluate=False).evalf(30, strict=True)
    # a condition no evaluation decides (Q <= 0 holds: Q is exactly 0): the fallback evaluated both pieces, 1 + e**-200
    # and 1 rounded alike, merged them, and P - 1 came out 0
    pw = sp.Piecewise((1 + sp.exp(-200), sp.Le(sp.sympify(Q), 0)), (1, True))
    with pytest.raises(PrecisionExhausted):
        (pw - 1).evalf(15, strict=True)


def test_a_rewritten_node_has_room_for_its_own_cancellation():
    from mathverify.equiv.numeric import certified_sign
    # asin(tanh(486)): 1 - tanh(486)**2 = 4e^(-972), a cancellation past SymPy's 332 bits of evalf(30)
    assert certified_sign(sp.asin(sp.tanh(sp.Integer(486)))) == 1
    assert certified_sign(sp.acos(sp.tanh(sp.Integer(486)))) == 1
    # the merged state reads those two signs off the argument (numeric._monotone_sign); a difference still needs the
    # value: asin(tanh 486) = pi/2 - 2e^(-486) > 1, acos(tanh 486) = 2e^(-486) < 1/1000 (V39, V46 lived without it)
    assert certified_sign(sp.asin(sp.tanh(sp.Integer(486))) - 1) == 1
    assert certified_sign(sp.acos(sp.tanh(sp.Integer(486))) - sp.Rational(1, 1000)) == -1


def test_complex_numbers_read_off_the_cut():
    from mathverify.equiv.numeric import NONREAL, certified_sign
    t = sp.Symbol("t")
    signs = sorted(certified_sign(r_) for r_ in sp.roots(t ** 3 - 3 * t + 1, t))   # Cardano: complex radicals
    assert signs == [-1, 1, 1]
    assert certified_sign(2 * sp.atan(1 - sp.sqrt(2) * sp.I)) == NONREAL           # a complex root of sin - cos = 2


def test_log_near_one_is_read_from_u_minus_one():                                               # fecc2be
    from mathverify.equiv.numeric import certified_sign
    e = sp.exp(-200)
    assert sp.log(1 + e).evalf(30, strict=True) > 0
    assert certified_sign(sp.log(1 + e) - e / 2) in (1, None)          # log(1 + e) - e/2 = e/2 - e**2/2 + ...


def test_a_finite_sum_is_written_out():
    k = sp.Symbol("k", integer=True)
    assert abs(sp.Sum(k, (k, 1, 3)).evalf(30, strict=True) - 6) < 1e-25
    with pytest.raises(PrecisionExhausted):
        sp.Sum(1 / k ** 2, (k, 1, sp.oo)).evalf(30, strict=True)


def test_acot_of_an_exact_zero_is_not_read_through_its_normalization():
    from mathverify.equiv.numeric import certified_sign
    # SymPy writes acot(Q) as -acot(-Q); acot(0) is pi/2, so -acot(-0) would read -pi/2
    assert certified_sign(sp.sympify(f"acot({Q})")) in (1, None)


def test_certified_integer_and_floor_of_an_untracked_node():                                   # fecc2be
    from mathverify.equiv.numeric import certified_floor, certified_integer
    c = sp.asin(sp.sympify(Q)) + 2
    assert certified_integer(c) == (True, 2)
    assert certified_floor(c) == 2
    assert certified_floor(c + sp.Rational(1, 2)) == 2                 # no integer: certified_integer cannot answer it


@pytest.mark.parametrize("e,s", [(f"asin({Q})", 0), (f"asin({Q}) - 1", -1), (f"tanh({P})", 0), (f"sinh({L})**2", 0),
                                 (f"erf({Q})", 0), (f"cosh({Q})", 1), (f"cosh({Q}) - 1", 0), (f"atan2({Q}, -1) - pi", 0),
                                 (f"Max(sin({Q}), 0) - 1", -1), (f"Min(sin({Q}), 0) + 1", 1), (f"2 + tanh({P}) - 2", 0)])
def test_certified_sign_reads_an_untracked_node_at_its_exact_zero(e, s):                     # fecc2be
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(sp.sympify(e), 20) == s


def test_floor_and_ceiling_of_a_number_are_not_formed_from_noise():                             # fecc2be
    # SymPy forms floor/ceiling of a number at construction with a non-strict evaluation: ceiling(Z**2) was 1
    z = sp.sympify(Z)
    assert not isinstance(sp.ceiling(z ** 2), sp.Integer) or sp.ceiling(z ** 2) == 0
    assert not isinstance(sp.floor(z), sp.Integer) or sp.floor(z) == 0
    assert sp.ceiling(sp.sqrt(2)) == 2 and sp.floor(-sp.pi) == -4 and sp.floor(sp.exp(10)) == 22026
    # the round 9 attack's e9 S2: the true step y = ceiling(x**2) at x = Z, y = 0 was refuted (and y = 1 not)
    xy = (X, V("y"))
    assert _run(_ev("y + 1", [f"x = {Z}", "y = 0"], xy), "1", steps=[("eq", "y = ceiling(x**2)")]).verdict != "INCORRECT"
    r = _run(_ev("y + 1", [f"x = {Z}", "y = 1"], xy), "2", steps=[("eq", "y = ceiling(x**2)")])
    steps = next(la for la in r.layers if la.layer == "steps.refute").evidence["steps"]
    assert steps[0]["status"] != "verified"                         # ceiling(0) = 0: the step is false


def test_a_special_function_of_exact_arguments():
    # erf(1), gamma(1/3): no argument to read off noise; mpmath's value where two working precisions agree. Without it
    # d4c's narrow peak (the integral of x**2 + exp(-10**8*(x - 1/3)**2), sqrt(pi)*erf(...)/20000 above 1/3) lost its
    # INCORRECT
    from mathverify.equiv.numeric import certified_floor, certified_sign
    R = sp.Rational
    assert certified_sign(sp.erf(1) - R(84, 100)) == 1 and certified_sign(sp.erf(1) - R(85, 100)) == -1
    assert certified_floor(10 * sp.erf(1)) == 8
    assert certified_sign(sp.gamma(R(1, 3)) - R(268, 100)) == -1
    assert certified_sign(sp.erf(sp.sympify(Q)) + 1) == 1          # an argument written as an exact 0: f(0)
    dint = _ir("definite_integral", {"integrand": "x**2 + exp(-10**8*(x - 1/3)**2)", "var": "x", "a": "0", "b": "1"})
    assert _run(dint, "1/3").verdict == "INCORRECT"


@pytest.mark.parametrize("e", [f"asin({A})", f"sinh({A})", f"tanh(2*atan(1/3) - atan(3/4)) + 0*{A}"])
def test_certified_sign_never_reads_noise(e):
    from mathverify.equiv.numeric import certified_sign
    assert certified_sign(sp.sympify(e), 20) in (0, None)


def test_jump_values_of_untracked_nodes():                                                     # fecc2be
    from mathverify.equiv.numeric import certified_sign, jump_value
    assert jump_value(sp.ceiling(sp.sympify(f"asin({Q})"), evaluate=False)) == 0
    assert jump_value(sp.sign(sp.sympify(f"asin({L})"), evaluate=False)) == 0
    assert certified_sign(jump_value(sp.Mod(sp.sympify(f"tanh({P}) + 5"), 5, evaluate=False))) == 0


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


def test_an_unevaluated_atan2_on_an_axis():
    # as written (parse_as_written) an atan2 of an exact 0 stays a node: on an axis its value is exact
    from mathverify.equiv.numeric import certified_sign
    q = sp.sympify(Q)
    assert certified_sign(sp.atan2(q, -1, evaluate=False)) == 1                          # pi
    assert certified_sign(sp.atan2(1, q, evaluate=False)) == 1                           # pi/2
    assert certified_sign(sp.atan2(-1, q, evaluate=False)) == -1                         # -pi/2
    assert certified_sign(sp.atan2(q, q, evaluate=False)) is None                        # atan2(0, 0): undefined


def test_trig_index_range_of_an_exact_zero_phase():                                             # fecc2be
    # SymPy read ceiling(-asin(Q)/pi) = 1 and floor(-asin(Q)/pi) = 0 for one exact 0: the solution 0 was lost
    from mathverify.certify.trig import _enumerate_on_window, _enumerate_window_of_interval
    c = sp.asin(sp.sympify(Q))
    for ph in (c, -c):
        assert _enumerate_on_window([(ph, sp.pi)], 2 * sp.pi) == sp.FiniteSet(0, sp.pi)
        assert _enumerate_window_of_interval([(ph, sp.pi)], sp.Interval(0, 2 * sp.pi)) == sp.FiniteSet(0, sp.pi, 2 * sp.pi)


def test_a_polynomial_whose_leading_coefficient_may_be_zero():                                 # fecc2be
    from mathverify.sandbox.exactsets import certified_degree
    with pytest.raises(ValueError):
        certified_degree(sp.Poly(x * sp.asin(sp.sympify(Q)), x))
    assert certified_degree(sp.Poly(sp.sqrt(2) * x - 1, x)).degree() == 1
    assert _run(_eq(f"x*asin({Q}) = 0"), "{0}", "set").verdict != "CORRECT"
    assert _run(_eq(f"x*asin({Q}) = 0"), "Reals", "set").verdict != "INCORRECT"
    cr = _ir("count_roots", {"expr": f"x*tanh({P})", "var": "x"}, (X,), (), "count")
    assert _run(cr, "1", "count").verdict != "CORRECT"
    cr = _ir("count_roots", {"expr": f"x*asin({Q})", "var": "x"}, (X,), (), "count")       # every x is a root
    assert _run(cr, "1", "count").verdict != "CORRECT"
    # sqrt(x**2) = x holds on [0, oo): the radical's resultant -x*asin(Q) is no polynomial of degree 1 (fecc2be: {0})
    assert _run(_eq(f"sqrt(x**2 - x*asin({Q})) = x"), "{0}", "set").verdict != "CORRECT"


def test_a_linear_argument_whose_coefficient_may_be_zero():                                    # fecc2be
    from mathverify.sandbox.exactsets import exact_solveset
    xr = sp.Symbol("x", real=True)
    q = sp.sympify(Q)
    # exp(x*Q) = 1 holds for every x (Q is exactly 0); Poly read x*Q as degree 1 and the class solved it {0}
    for lhs in (sp.exp(xr * q), 2 ** (xr * q), sp.exp(xr * sp.asin(q))):
        assert exact_solveset(sp.Eq(lhs, 1), xr, S.Reals) != sp.FiniteSet(0)
    assert not exact_solveset(sp.Eq(sp.sin(xr * sp.asin(q)), 0), xr, S.Reals).has(sp.ImageSet)   # no period 2*pi/0
    for e in (f"exp(x*{Q}) = 1", f"2**(x*{Q}) = 1", f"exp(x*asin({Q})) = 1"):
        assert _run(_eq(e), "{0}", "set").verdict != "CORRECT"
        assert _run(_eq(e), "Reals", "set").verdict != "INCORRECT"
    assert _run(_eq("exp(2*x) = 1"), "{0}", "set").verdict == "CORRECT"


def test_latex_jumps_of_an_untracked_node():                                                   # fecc2be
    s = r"\lceil \sinh(\frac{\ln 8}{\ln 2} - 3)^2 \rceil"
    assert _run(_ev(s), "1").verdict != "CORRECT"
    assert _run(_ev(s), "0").verdict != "INCORRECT"


def test_the_controls_keep_their_verdicts():
    assert _run(_ev("ceiling(10*asin(1/2))"), "6").verdict == "CORRECT"
    assert _run(_ev("floor(sinh(2))"), "3").verdict == "CORRECT"
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
    assert sp.sympify(f"sinh({A})").equals(0) is not False


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


def test_every_point_of_a_finite_domain_read_exactly():                                        # fecc2be
    # (x - 3)**(x + 4) on {-3, ..., 3}: an integer exponent at every point, a zero base at 3 with exponent 7
    ir = _eq("(x + 2)*(x - 3) = 0", givens=["(x - 3)**(x + 4)*cos(pi*x) > 0"], dod=D7)
    assert _run(ir, "{-2}", "set").verdict == "CORRECT"
    assert _run(ir, "EmptySet", "set").verdict == "INCORRECT"


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


def test_a_real_power_on_a_positive_or_finite_domain():
    # x*x**x = x**(x + 1) wherever both have a value: on x > 0 (the base's sign splits the line), and at the integers
    # -3, -2, -1 (Range(-3, 0), each point read: fecc2be CORRECT, lost when only a FiniteSet was read)
    for var in (V("x", "integer", ["x >= -3", "x <= -1"]), V("x", "real", ["x > 0"])):
        ir = _ir("simplify_expression", {"expr": "x*x**x"}, (var,), shape="expression")
        assert _run(ir, "x**(x + 1)", "expression").verdict == "CORRECT"
    ir = _ir("simplify_expression", {"expr": "x**x"}, (V("x", "integer", ["x >= -3", "x <= -1"]),), shape="expression")
    assert _run(ir, "Abs(x)**x", "expression").verdict == "INCORRECT"            # -1 and 1 at x = -1


def test_real_powers_away_from_their_convention_points():
    for f in ("x + 0*x**x", "x + 0*x**sqrt(2)", "x + 0*(x - 1)**x"):
        assert _run(_ir("extremum", {"f": f, "var": "x", "which": "max", "interval": "[2, 3]"}), "3").verdict == "CORRECT"
        assert _run(_ir("limit", {"expr": f, "var": "x", "to": "2"}), "2").verdict == "CORRECT"
    assert _run(_ir("simplify_expression", {"expr": "x**sqrt(2)*x"}, shape="expression"), "x**(1 + sqrt(2))",
                "expression").verdict == "CORRECT"
    assert _run(_ir("derivative", {"f": "x**x", "var": "x", "at": "1"}), "1").verdict == "CORRECT"
    # around -1 the power x**x has no real value but at the integers: no limit
    assert _run(_ir("limit", {"expr": "x + 0*x**x", "var": "x", "to": "-1"}), "-1").verdict != "CORRECT"
    # |x|**x is x**x on x > 0 only: at -1 they are 1 and -1
    assert _run(_ir("simplify_expression", {"expr": "x**x"}, shape="expression"), "Abs(x)**x",
                "expression").verdict != "CORRECT"
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


def test_cells_are_joined_in_one_pass():
    # 160 intervals with edges k*pi: SymPy's Union joins them pair by pair (about 40 s here), the pass along the edges
    # does not
    from mathverify.sandbox.exactsets import _joined
    n = 321
    t = time.time()
    u = _joined([k * sp.pi for k in range(n)], [k % 2 == 0 for k in range(n - 1)], [False] * n)
    assert len(u.args) == 160 and time.time() - t < 5


def test_a_given_with_160_intervals_answers_in_time():                                         # fecc2be (> 100 s)
    t = time.time()
    ir = _ir("solve_equation", {"equation": "cos(x) = 0", "var": "x"}, (V("x", "real", ["x >= 0", "x <= 1000"]),),
             ["sin(x) > 0"], "set")
    assert _run(ir, "{pi/2}", "set").verdict != "CORRECT"
    assert time.time() - t < 60


# --- RK-4: a constraint that could not be applied -----------------------------------------------------------------

def test_a_convention_point_is_not_refuted_by_a_dropped_constraint():
    neg = "-10 + 2*atan(tanh(1/2)) - atan(sinh(1))"          # exactly -10
    for cons in ([f"x >= {neg}", "x >= -10"], ["x >= -10", f"x >= {neg}"]):
        # (-8)**(1/3): the real root -2 or the principal value: -8 is neither kept nor dropped
        assert _run(_eq("x**(1/3) = -2", (V("x", "real", cons),)), "{-8}", "set").verdict != "INCORRECT"


def test_a_complement_with_many_points_is_budgeted():
    from mathverify.sandbox.exactsets import exact_complement
    with pytest.raises(TypeError):
        exact_complement(sp.Interval(0, 100), sp.FiniteSet(*range(1, 40)))
    assert exact_complement(sp.Interval(0, 10), sp.FiniteSet(1, 2)) == sp.Union(
        sp.Interval.Ropen(0, 1), sp.Interval.open(1, 2), sp.Interval.Lopen(2, 10))


@pytest.mark.parametrize("cons", [[f"x <= {FAR}", "x >= 3"], ["x >= 3", f"x <= {FAR}"]])
def test_a_claimed_root_outside_a_constraint_read_alone(cons):                                  # fecc2be
    vs = (V("x", "real", cons),)
    assert _run(_eq("x**2 = 9", vs), "{-3, 3}", "set").verdict == "INCORRECT"
    assert _run(_eq("x + 1 = 0", vs), "{-1}", "set").verdict == "INCORRECT"
    assert _run(_eq("x**2 = 9", vs), "{3}", "set").verdict != "INCORRECT"
