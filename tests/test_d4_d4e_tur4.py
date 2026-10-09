"""Fourth audit, part d4e, round 4 (8 Oct 2026): the attack on round 3 (`denetim/2026-10-01/d4/saldiri/d4e3/`) and the
main session's decisions (`d4e3/kararlar_tur4.txt`). Each assertion below failed on a0a0829 (src = d342778) unless it
is marked as a control.

* YO-4 = RK-2: a SymPy limit for a generic value of a declared-sign parameter was a proof of convergence:
  ∫_1^oo dt/((x - 1)**2*t**2 + 1), divergent at x = 1, made x**2 + 0*∫ differentiable at 1 and 1 a root.
* YO-2: the claim's undefined family was tried at n = 0, ±1, 2 only: 2*x + 0*cot(4*x) for (x**2)' under x > 10.
* YO-3: a constraint, domain of discourse or limit given whose written definedness is undecided was dropped.
* YO-5 + YO-3-EK1: an extremum over an interval read the givens, constraints and domain of discourse after SymPy's fold.
* YO-6, YO-7: a Piecewise's written definedness read every branch everywhere, and a gap no branch covers had a value.
* RK-1, RK-6: a fractional power was analytic at its base's zero (sqrt(x**2 + x**4)); a root's base with zeros no
  exact class solves left the textbook derivative undecided (sqrt(x - cos(x))).
* RK-3: a value fixed in another form (2*a = 4) was not read by the calculus certificates.
* RK-4: series_sum abstained on decidable definedness (1/k!, 1/(k + a) with a > 0, (-1)**(k*(k + 1)/2)).
* RK-5: the claim's condition on a parameter ignored the parameter's region (a != 0 given).
* RK-7: Dirichlet's test with a declared-positive parameter (sin(t)/(t + a)).
* RK-9: one verify of |x**4 - 10*x**2 + 1|*|x**3 - 3*x + 1|' took over 60 s.
* RK-8, RK-10: Max(sin(x), 0)**2 (C1) and the second derivative of |x(x - 1)(x - 2)(x - 3)| were left undecided.
"""
import time

import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XPOS = {"name": "x", "domain": "positive_real"}
T_ = {"name": "t", "domain": "real"}
AR = {"name": "a", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
K_ = {"name": "k", "domain": "integer"}
DNE = "DNE"


def xc(*cs):
    return {"name": "x", "domain": "real", "constraints": list(cs)}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    return d


def _v(ir, payload, kind="value"):
    if payload == DNE:
        return verify(ir, {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}).verdict
    return verify(ir, {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}).verdict


def _der(f, at=None, givens=(), vars_=None, order=None, dod=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    if order:
        p["order"] = order
    return _ir("derivative", p, givens, vars_, "scalar" if at is not None else "expression", dod)


def _ext(f, which, interval, givens=(), vars_=None, dod=None):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return _ir("extremum", p, givens, vars_, "scalar", dod)


def _solve(eq, vars_=None):
    return _ir("solve_equation", {"var": "x", "equation": eq}, (), vars_, "set")


def _ss(term, lo, hi, vars_):
    return _ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, (), vars_)


A1 = "Integral(1/((x - 1)**2*t**2 + 1), (t, 1, oo))"


def test_convergence_for_every_value_of_a_declared_sign_parameter():
    V = [XPOS, T_]
    assert _v(_der(f"x**2 + 0*{A1}", "1", (), V), "2") != "CORRECT"
    assert _v(_der("x**2 + 0*Integral(1/(1 + (x - 1)**2*t**4), (t, 1, oo))", "1", (), V), "2") != "CORRECT"
    q = _solve(f"x**2 - 1 + 0*{A1} = 0", V)
    assert _v(q, "{1}", "set") != "CORRECT" and _v(q, "EmptySet", "set") != "INCORRECT"
    q = _ir("solve_inequality", {"var": "x", "inequality": f"x + 0*{A1} >= 1"}, (), V, "set")
    assert _v(q, "Interval(1, oo)", "interval") != "CORRECT"
    assert _v(q, "Interval.open(1, oo)", "interval") != "INCORRECT"
    assert _v(_ext(f"-(x - 1)**2 + 0*{A1}", "max", "[1/2, 2]", (), V), "0") != "CORRECT"
    # controls: a bound for every value stands (R7, round 3 RK-4)
    q = _der("Integral(exp(-a*t), (t, x, oo))", None, (), [X, T_, AP])
    assert _v(q, "-exp(-a*x)", "expression") == "CORRECT"
    q = _der("Integral(1/(t + a)**2, (t, x, oo))", None, (), [XPOS, T_, AP])
    assert _v(q, "-1/(x + a)**2", "expression") == "CORRECT"


def test_majorant_terms_are_parameter_free():
    from mathverify.certify.domain import decays_at, integrable_near
    t = sp.Dummy("t", real=True)
    x = sp.Symbol("x", positive=True)
    a = sp.Symbol("a", positive=True)
    for g in (1 / ((x - 1) ** 2 * t ** 2 + 1), sp.cos(t) ** 2 / ((x - 1) ** 2 * t ** 2 + 1), sp.exp(-a * t) * sp.exp(t),
              1 / (sp.Abs(x - 1) * t ** 2 + 1), t * sp.sin(t) / ((a - 1) ** 2 * t ** 2 + 1), sp.exp(-(x - 1) ** 2 * t),
              1 / ((a - 1) * t ** 2)):
        assert decays_at(g, t, sp.oo) is False, g
    for g in (sp.exp(-a * t) * t ** 3, sp.sin(t) / (t + a), a * sp.sin(t) / t, 1 / (t + a) ** 2):
        assert decays_at(g, t, sp.oo) is True, g
    # a denominator whose leading term is a positive number times t**k: (c/2)*t**k from some t on, for every value
    xr = sp.Symbol("x", real=True)
    assert decays_at(1 / (t ** 2 - xr ** 2), t, sp.oo) is True
    assert decays_at(1 / (t ** 2 * (xr - 1) + 1), t, sp.oo) is False
    assert integrable_near(1 / (t + (x - 1) ** 2 * sp.sqrt(t)), t, 0, "+") is False
    # e**(-a*log(t)) = t**(-a) grows at 0+: an exponential of negative rate bounds nothing where its r -> -oo
    assert integrable_near(sp.exp(t - a * sp.log(t)), t, 0, "+") is False
    assert integrable_near(a / sp.sqrt(t), t, 0, "+") is True


def test_dirichlet_with_a_parameter_for_every_value():
    q = _ir("evaluate", {"expr": "0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1"}, (), [T_, AP])
    assert _v(q, "1") == "CORRECT"
    q = _der("Integral(sin(t)/(t + a), (t, x, oo))", None, (), [XPOS, T_, AP])
    assert _v(q, "-sin(x)/(x + a)", "expression") == "CORRECT"
    assert _v(q, "sin(x)/(x + a)", "expression") == "INCORRECT"
    q = _ir("evaluate", {"expr": "0*Integral(t*sin(t)/((a - 1)**2*t**2 + 1), (t, 1, oo)) + 1"}, (), [T_, AP])
    assert _v(q, "1") != "CORRECT"
    # h = a + 1/t is nonnegative and nonincreasing but tends to a, not 0: the integral diverges for every a > 0
    q = _ir("evaluate", {"expr": "0*Integral(sin(t)*(a + 1/t), (t, 1, oo)) + 1"}, (), [T_, AP])
    assert _v(q, "1") != "CORRECT"
    q = _der("Integral(sin(t)*(a + 1/t), (t, x, oo))", None, (), [XPOS, T_, AP])
    assert _v(q, "-sin(x)*(a + 1/x)", "expression") != "CORRECT"


def test_claim_family_met_with_the_region_exactly():
    E = "expression"
    assert _v(_der("x**2", None, ["x > 10"]), "2*x + 0*cot(4*x)", E) != "CORRECT"
    assert _v(_der("x**2", None, ["x < -10"]), "2*x + 0*cot(x)", E) != "CORRECT"
    assert _v(_der("x**2", None, ["x > 10", "x < 11"]), "2*x + 0*cot(4*x)", E) != "CORRECT"
    assert _v(_der("log(x - 20)", None, ["x > 30"]), "cot(x)*tan(x)/(x - 20)", E) != "CORRECT"
    assert _v(_der("x**2", None, ["x > 10", "x < 51/5"]), "2*x + 0*cot(4*x)", E) == "CORRECT"     # control: no pole
    # the first members k*pi of the family fail sin(x) + x/100 > 1, 32*pi and others past them hold it: a family
    # listed in part never certifies the claim
    G = ["x > 0", "sin(x) + x/100 > 1"]
    assert _v(_der("x**2", None, G), "2*x + 0/sin(x)", E) != "CORRECT"
    assert _v(_der("x**2", None, G), "2*x", E) == "CORRECT"                                       # control
    # pi is an end of sqrt(sin(x))'s domain, no point of the comparison's open part: the claim may lack a value there
    assert _v(_der("sqrt(sin(x))**3"), "3*cos(x)*sin(x)/(2*sqrt(sin(x))) + 0/(x - pi)", E) == "CORRECT"


def test_undecided_written_constraint_dod_and_limit_given():
    G1 = "0*Integral(1/t, (t, x, 1)) >= 0"
    G3 = "x + 0*tan(acot(2) + acot(1/2)) > 0"
    q = _solve("x**2 = 1/4", [xc(G1), T_])
    assert _v(q, "{-1/2, 1/2}", "set") == "UNKNOWN" and _v(q, "{1/2}", "set") == "UNKNOWN"
    assert _v(_solve("x**2 = 1/4", [xc(G3)]), "{1/2}", "set") == "UNKNOWN"
    q = _ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, [G1], [X, T_])
    assert _v(q, DNE) == "UNKNOWN" and _v(q, "1") == "UNKNOWN"
    assert _v(_ext("x", "min", "[-1, 1]", (), [X, T_], G1), "-1") == "UNKNOWN"


def test_extremum_interval_reads_conditions_as_written():
    G = "x**2 + 0*sqrt(x - 1/2) >= 0"
    for g, v, d in (([G], [X], None), ([], [xc(G)], None), ([], [X], G)):
        assert _v(_ext("x**2", "min", "[-1, 1]", g, v, d), "0") != "CORRECT"
        assert _v(_ext("x**2", "min", "[-1, 1]", g, v, d), "1/4") != "INCORRECT"
        assert _v(_ext("x", "max", "[-1, 1/4]", g, v, d), "1/4") == "UNKNOWN"
    for G2 in ("x/x > 0", "x**2 + 0*log(x) >= 0", "0*log(x) >= 0"):
        assert _v(_ext("x**2", "min", "[-1, 1]", [G2]), "0") != "CORRECT"
    assert _v(_ext("x", "min", "[-1, 1]", ["0*log(x) >= 0"]), "-1") != "CORRECT"
    assert _v(_ext("x**2", "min", "[-1, 1]", ["x >= 1/2"]), "1/4") == "CORRECT"                     # control


def test_piecewise_branches_and_gaps():
    from mathverify.certify.base import make_ctx
    from mathverify.certify.domain import written_definedness
    from mathverify.ir import ProblemIR
    ctx = make_ctx(ProblemIR.from_dict(_der("Abs(x)")))
    ns = ctx.claim_ns()
    assert written_definedness("Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", ns)[0] == []
    assert written_definedness("Piecewise((x**2, x < 0), (x**2, x > 0))", ns)[0] == [sp.Ne(ctx.sym("x"), 0)]
    E = "expression"
    assert _v(_der("Abs(x)"), "Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", E) == "UNKNOWN"
    assert _v(_der("Abs(x)"), "Piecewise((7, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", E) != "CORRECT"
    assert _v(_der("x**2"), "Piecewise((2*x**2/x, Ne(x, 0)), (0, Eq(x, 0)))", E) == "CORRECT"
    assert _v(_der("Abs(x)"), "Piecewise((1, x > 0), (-1, x < 0))", E) == "CORRECT"                 # control (R8)
    for eq, wrong, right in (("Piecewise((x**2, x < 0), (x**2, x > 0)) = 0", "{0}", "EmptySet"),
                             ("Piecewise((x**2 - 1, x < 1), (x**2 - 1, x > 1)) = 0", "{-1, 1}", "{-1}"),
                             ("x*Piecewise((1, x < 0), (1, x > 0)) = 0", "{0}", "EmptySet")):
        assert _v(_solve(eq), wrong, "set") != "CORRECT", eq
        assert _v(_solve(eq), right, "set") != "INCORRECT", eq
    q = _ir("solve_inequality", {"var": "x", "inequality": "Piecewise((x**2, x < 0), (x**2, x > 0)) >= 0"}, (), None,
            "set")
    assert _v(q, "Reals", "set") != "CORRECT"
    q = _ir("evaluate", {"expr": "Piecewise((t**2, t < 0), (t**2, t > 0))"}, ["t = 0"], [T_])
    assert _v(q, "0") != "CORRECT"


def test_z3_piecewise_side_conditions_where_taken():
    from mathverify.certify._z3bridge import check_sat
    x = sp.Symbol("x", real=True)
    info = {"x": "real"}
    pw = sp.Piecewise((x ** 2 - 1, x < 1), (x ** 2 - 1, x > 1))
    assert check_sat([sp.Eq(pw, 0), sp.Eq(x, 1)], info, [])[0] == "unsat"      # the gap 1 is no solution
    assert check_sat([sp.Eq(pw, 0), sp.Eq(x, -1)], info, [])[0] == "sat"
    pw2 = sp.Piecewise((1 / x, x > 1), (x, True))
    # 1/x's side condition x != 0 holds only where its branch is taken: x = 0 takes the other one
    assert check_sat([sp.Eq(pw2, 0), sp.Eq(x, 0)], info, [])[0] == "sat"


def test_root_base_zero_classified_as_a_kink():
    E = "expression"
    S4 = "sqrt(x**2 + x**4)"
    assert _v(_der(S4), f"(x + 2*x**3)/{S4}", E) == "CORRECT"
    # the claim's own condition x**2 + x**4 > 0 fails at 0 alone, where f has no derivative
    assert _v(_der(S4), "(x + 2*x**3)*(x**2 + x**4)**(-1/2)", E) == "CORRECT"
    assert _v(_der("(x**2 + x**4)**(1/3)"), "(2*x + 4*x**3)/(3*(x**2 + x**4)**(2/3))", E) == "CORRECT"
    # four corners classified by the exact rule, past the budget of `derivative_at_point` calls
    x = sp.Symbol("x")
    u = sp.expand(((x ** 2 - 1) * (x ** 2 - 4)) ** 2 * (1 + x ** 2))
    assert _v(_der(f"sqrt({u})"), str(sp.diff(u, x) / (2 * sp.sqrt(u))), E) == "CORRECT"
    assert _v(_der(S4), "sign(x)*(1 + 2*x**2)/sqrt(1 + x**2)", E) == "UNKNOWN"
    assert _v(_der(f"Abs(x) - {S4}"), f"x/Abs(x) - (x + 2*x**3)/{S4}", E) != "CORRECT"
    assert _v(_der("sqrt(x**4 + x**6)"), "(2*x**3 + 3*x**5)/sqrt(x**4 + x**6)", E) == "INCORRECT"   # control
    q = _der(f"sqrt(a**2 - x**2) + {S4}", None, (), [X, AP])
    assert _v(q, f"-x/sqrt(a**2 - x**2) + (x + 2*x**3)/{S4}", E) != "INCORRECT"


def test_root_base_zeros_without_derivative_proved_at_once():
    E = "expression"
    for f, c in (("sqrt(x - cos(x))", "(1 + sin(x))/(2*sqrt(x - cos(x)))"),
                 ("sqrt(1 + sin(x))", "cos(x)/(2*sqrt(1 + sin(x)))"),
                 ("sqrt(exp(x) - 1 - x)", "(exp(x) - 1)/(2*sqrt(exp(x) - 1 - x))"),
                 ("1/sqrt(x - cos(x))", "-(1 + sin(x))/(2*(x - cos(x))**(3/2))"),
                 ("Abs(x - cos(x))", "(1 + sin(x))*(x - cos(x))/Abs(x - cos(x))")):
        assert _v(_der(f), c, E) == "CORRECT", f
    # the claim's condition x - cos(x) > 0 fails at the base's zero alone, an end of f's domain
    assert _v(_der("sqrt(x - cos(x))"), "(1 + sin(x))*(x - cos(x))**(-1/2)/2", E) == "CORRECT"
    assert _v(_der("sqrt(1 + sin(x))"), "-cos(x)/(2*sqrt(1 + sin(x)))", E) == "INCORRECT"
    # zeros not solved one by one, a counterexample at an analytic point between them (cos(x) < x < 1)
    assert _v(_der("Abs(x - cos(x)) + Abs(x - 1)"), "1 + sin(x) + 1", E) == "INCORRECT"
    # a value at a zero where f has no derivative: a convention
    assert _v(_der("Abs(x - cos(x))"), "(1 + sin(x))*sign(x - cos(x))", E) == "UNKNOWN"
    # f has a derivative at the zeros of its root's base: the claim undefined there is never certified
    q = _der("sqrt(1 + sin(x))*cos(x)")
    assert _v(q, "cos(x)**2/(2*sqrt(1 + sin(x))) - sin(x)*sqrt(1 + sin(x))", E) != "CORRECT"


def test_asin_acos_at_an_attained_end_are_not_analytic():
    # SymPy proves 1 - 2*x**2 <= 1 and drops it; acos(1 - 2*x**2) = 2*asin(|x|) has a corner at 0, where the
    # textbook derivative has no value: never refuted for that (found in round 4 beside RK-1, same rule)
    E = "expression"
    q = _der("acos(1 - 2*x**2)")
    assert _v(q, "4*x/sqrt(1 - (1 - 2*x**2)**2)", E) != "INCORRECT"
    assert _v(q, "2*x/(Abs(x)*sqrt(1 - x**2))", E) != "INCORRECT"
    assert _v(q, "2/sqrt(1 - x**2)", E) == "INCORRECT"                                               # control
    assert _v(_der("asin(1 - x**2)"), "-2*x/sqrt(1 - (1 - x**2)**2)", E) != "INCORRECT"
    assert _v(_der("acos(1 - 2*x**2)", "0"), DNE) != "INCORRECT"
    assert _v(_der("acos(1 - 2*x**2)", "0"), "0") != "CORRECT"
    # the parameter path: 1 - 2*x**2/a**2 = 1 at x = 0 for every a
    q = _der("acos(1 - 2*x**2/a**2)", None, (), [X, AP])
    assert _v(q, "4*x/(a**2*sqrt(1 - (1 - 2*x**2/a**2)**2))", E) != "INCORRECT"
    assert _v(_der("asin(x/2)"), "1/sqrt(4 - x**2)", E) == "CORRECT"                                  # control
    assert _v(_der("acos(x/a)", None, (), [X, AP]), "-1/sqrt(a**2 - x**2)", E) == "CORRECT"           # control


def test_parameter_fixed_in_another_form_read_by_calculus():
    E = "expression"
    for g in (["2*a = 4"], ["a - 2 = 0"], ["a**2 = 4", "a > 0"]):
        assert _v(_der("a*x**2", None, g, [X, AR]), "4*x", E) == "CORRECT", g
        assert _v(_der("a*x**2", None, g, [X, AR]), "6*x", E) == "INCORRECT", g
    assert _v(_der("a*x**2", None, ["sqrt(a) = 2"], [X, AR]), "8*x", E) == "CORRECT"
    assert _v(_ext("a*x", "max", "[0, 1]", ["2*a = 4"], [X, AR]), "2") == "CORRECT"
    assert _v(_ir("limit", {"expr": "a*x", "var": "x", "to": "1"}, ["2*a = 4"], [X, AR]), "2") == "CORRECT"
    assert _v(_ir("antiderivative", {"integrand": "a*x", "var": "x"}, ["2*a = 4"], [X, AR], "expression"), "x**2",
              E) == "CORRECT"
    Y = {"name": "y", "domain": "real"}
    q = _ir("tangent_line", {"f": "a*x**2", "var": "x", "at": "1", "dep": "y"}, ["2*a = 4"], [X, AR, Y], "equation")
    assert _v(q, "y = 4*x - 2", "equation") == "CORRECT"
    B = {"name": "b", "domain": "real"}
    assert _v(_der("a*x**2", None, ["a = b"], [X, AR, B]), "4*x", E) != "INCORRECT"
    # refuted at an allowed value (a = 1): INCORRECT stands
    assert _v(_der("a*x**2", None, ["a > 0"], [X, AR]), "4*x", E) == "INCORRECT"


def test_series_definedness_decided_on_the_region():
    for t, lo, hi, v in (("1/factorial(k)", "0", "oo", "E"), ("1/factorial(k)", "0", "3", "8/3"),
                         ("1/factorial(2*k)", "0", "oo", "cosh(1)"), ("(-1)**(k*(k + 1)/2)", "0", "3", "0")):
        assert _v(_ss(t, lo, hi, [K_]), v) == "CORRECT", t
    assert _v(_ss("1/factorial(k)", "0", "oo", [K_]), "E + 1") == "INCORRECT"
    assert _v(_ss("1/(k + a)", "1", "3", [K_, AP]), "1/(a + 1) + 1/(a + 2) + 1/(a + 3)") == "CORRECT"
    assert _v(_ss("1/(k + a)", "1", "3", [K_, AP]), "3/(a + 2)") == "INCORRECT"
    assert _v(_ss("1/(k - a)", "1", "3", [K_, AP]), "0") != "CORRECT"                               # control


def test_integer_valued_polynomial_by_binomial_basis():
    from mathverify.certify.domain import _integer_valued
    k = sp.Symbol("k", integer=True)
    assert _integer_valued(k * (k + 1) / 2, k) and _integer_valued(k * (k - 1) * (k - 2) / 6, k)
    assert not _integer_valued(k / 2, k) and not _integer_valued(k ** 2 / 3, k)


def test_claim_condition_on_the_parameters_region():
    E = "expression"
    AC = {"name": "a", "domain": "real", "constraints": ["a != 0"]}
    assert _v(_der("atan(x/a)", None, ["a != 0"], [X, AR]), "a/(a**2 + x**2)", E) == "CORRECT"
    assert _v(_der("atan(x/a)", None, (), [X, AC]), "a/(a**2 + x**2)", E) == "CORRECT"
    assert _v(_der("log(x)/a", None, ["a != 0"], [X, AR]), "1/(a*x)", E) == "CORRECT"
    # with a free, the problem's own a != 0 is not proved on a's region: the verifier abstains before (d4d)
    assert _v(_der("log(x)/a", None, (), [X, AR]), "1/(a*x)", E) == "UNKNOWN"
    assert _v(_der("log(x)/log(a)", None, ["a != 1"], [X, AP]), "1/(x*log(a))", E) == "CORRECT"
    # the parameter path (f's condition -a < x < a): log(a) != 0 on a's region a > 0, a != 1
    assert _v(_der("asin(x/a)", None, ["a != 1"], [X, AP]), "1/sqrt(a**2 - x**2) + 0/log(a)", E) == "CORRECT"
    assert _v(_der("atan(x/a)", None, ["a != 0"], [X, AR]), "a/(a**2 + x**2) + 1", E) == "INCORRECT"
    # the plain path (f's condition on a half-line): a condition of the claim free of x, on the parameter's region
    assert _v(_der("sqrt(x - a)", None, ["a != 0"], [X, AR]), "1/(2*sqrt(x - a)) + 0/a", E) == "CORRECT"


def test_cell_proof_budget_keeps_one_verify_short():
    U2, U3 = "x**4 - 10*x**2 + 1", "x**3 - 3*x + 1"
    t0 = time.time()
    v = _v(_der(f"Abs({U2})*Abs({U3})"),
           f"(4*x**3 - 20*x)*({U2})*Abs({U3})/Abs({U2}) + (3*x**2 - 3)*({U3})*Abs({U2})/Abs({U3})", "expression")
    assert v == "CORRECT" and time.time() - t0 < 30          # 60.6 s on a0a0829, 6 s now (measured)


def test_cell_proof_spends_at_most_its_budget(monkeypatch):
    from mathverify.equiv import random_point, symbolic
    calls = []

    def first_attempt_fails(a, b, timeout=5.0):
        calls.append(1)
        return (True if len(calls) % 2 == 0 else None), {}
    monkeypatch.setattr(symbolic, "sym_equal", first_attempt_fails)
    x = sp.Symbol("x", real=True)
    e = sum(sp.Abs(x - k) for k in range(4))
    ev: dict = {}
    # each cell's first form fails and its other proves it: one failure per cell, five cells, a budget of three
    # (the third failure ends the proof before another attempt)
    assert random_point._cell_proof(e, e + 0 * x, x, sp.S.Reals, ev) is None
    assert ev["nonsmooth_proof"] == "cell_proof_budget" and len(calls) == 2 * random_point._CELL_FAILURES - 1
    monkeypatch.undo()
    # the form that proved a cell is tried first on the next: log(x**2) as 2*log(|x|) needs each cell's sign
    E = "expression"
    assert _v(_der("Abs(x**3 - x)*log(x**2)"), "(3*x**2 - 1)*sign(x**3 - x)*2*log(Abs(x)) + 2*Abs(x**3 - x)/x",
              E) == "CORRECT"


def test_kink_controls_stay_correct():
    E = "expression"
    for f, c in (("Piecewise((exp(x), x > 0), (1 + x, x <= 0))", "Piecewise((exp(x), x > 0), (1, x <= 0))"),
                 ("Max(x, -x)*Max(x, -x)", "2*x"), ("Max(x**3, -x**3)", "3*x**2*sign(x)"),
                 ("x*Max(x, -x)", "2*Max(x, -x)"), ("Max(x, -x)**(1/2)", "sign(x)/(2*sqrt(Abs(x)))")):
        assert _v(_der(f), c, E) == "CORRECT", f
    # f's condition 2*x/(1 + x**2) <= 1 is tight at x = 1 (and >= -1 at -1), its corners: f is not analytic there,
    # and the claim's lack of a value is no counterexample
    assert _v(_der("asin(2*x/(1 + x**2))"), "2*(1 - x**2)/((1 + x**2)*Abs(1 - x**2))", E) != "INCORRECT"


def test_kink_rules_for_a_higher_order_and_h_plus_g_abs():
    E = "expression"
    P4 = "x*(x - 1)*(x - 2)*(x - 3)"
    assert _v(_der(f"Abs({P4})", None, (), None, 2), f"(12*x**2 - 36*x + 22)*({P4})/Abs({P4})", E) == "CORRECT"
    assert _v(_der("Max(sin(x), 0)**2"), "2*cos(x)*Max(sin(x), 0)", E) == "CORRECT"
    assert _v(_der("Max(sin(x), 0)**2"), "2*sin(x)*cos(x)", E) == "INCORRECT"
    # h has a corner of its own at 0, where f has no derivative: never refuted for being undefined there
    assert _v(_der("Abs(x) + Max(sin(x), 0)**2"), "x/Abs(x) + 2*cos(x)*Max(sin(x), 0)", E) != "INCORRECT"
    # h = asin(sin(x)) is not analytic where defined (corners at cos(x) = 0): the rule of h + g|u| is not applied
    assert _v(_der("asin(sin(x)) + Max(cos(x), 0)**2"),
              "cos(x)/sqrt(1 - sin(x)**2) - 2*sin(x)*Max(cos(x), 0)", E) != "INCORRECT"


def test_series_tasks_refute_at_an_allowed_value_only():
    C = {"name": "c", "domain": "real"}
    N = {"name": "n", "domain": "positive_integer"}
    q = _ir("series_sum", {"term": "a**2*k", "var": "k", "lo": "1", "hi": "3"}, ["a**2 = 4"], [K_, AR])
    assert _v(q, "24") != "INCORRECT" and _v(q, "12") == "INCORRECT"
    q = _ir("recurrence_term", {"recurrence": "a(n) = c*a(n - 1)", "initial": {"1": "1"}, "index": "3", "var": "n",
                                "name": "a"}, ["c**2 = 4"], [N, C])
    assert _v(q, "4") != "INCORRECT" and _v(q, "5") == "INCORRECT"
    q = _ir("closed_form", {"recurrence": "a(n) = c**2*a(n - 1)", "initial": {"1": "1"}, "var": "n", "name": "a"},
            ["c**2 = 4"], [N, C], "expression")
    assert _v(q, "4**(n - 1)", "expression") != "INCORRECT"
    assert _v(q, "3**(n - 1)", "expression") != "CORRECT"
    q = _ir("closed_form", {"recurrence": "a(n) = a(n - 1) + 1", "initial": {"1": "c**2"}, "var": "n", "name": "a"},
            ["c**2 = 4"], [N, C], "expression")
    assert _v(q, "n + 3", "expression") != "INCORRECT"


def test_a_kink_value_where_the_formula_has_none():
    E = "expression"
    f = "Abs(x) - sqrt(x**2 + x**4)"
    assert _v(_der(f), "sign(x)*(1 - (1 + 2*x**2)/sqrt(1 + x**2))", E) == "CORRECT"
    assert _v(_der(f), "sign(x)*(1 - (1 + 2*x**2)/sqrt(1 + x**2)) + 1 - sign(x)**2", E) != "CORRECT"
