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


def test_claim_family_met_with_the_region_exactly():
    E = "expression"
    assert _v(_der("x**2", None, ["x > 10"]), "2*x + 0*cot(4*x)", E) != "CORRECT"
    assert _v(_der("x**2", None, ["x < -10"]), "2*x + 0*cot(x)", E) != "CORRECT"
    assert _v(_der("x**2", None, ["x > 10", "x < 11"]), "2*x + 0*cot(4*x)", E) != "CORRECT"
    assert _v(_der("log(x - 20)", None, ["x > 30"]), "cot(x)*tan(x)/(x - 20)", E) != "CORRECT"
    assert _v(_der("x**2", None, ["x > 10", "x < 51/5"]), "2*x + 0*cot(4*x)", E) == "CORRECT"     # control: no pole


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
    from mathverify.certify.domain import written_definedness
    x = sp.Symbol("x", real=True)
    ns = {"x": x, "Piecewise": sp.Piecewise, "Eq": sp.Eq, "Ne": sp.Ne, "Abs": sp.Abs}
    assert written_definedness("Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", ns)[0] == []
    assert written_definedness("Piecewise((x**2, x < 0), (x**2, x > 0))", ns)[0] == [sp.Ne(x, 0)]
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
    q = _ir("solve_inequality", {"var": "x", "inequality": "Piecewise((x**2, x < 0), (x**2, x > 0)) >= 0"}, (), None, "set")
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
    assert _v(_der("sqrt(1 + sin(x))"), "-cos(x)/(2*sqrt(1 + sin(x)))", E) == "INCORRECT"
    # a value at a zero where f has no derivative: a convention
    assert _v(_der("Abs(x - cos(x))"), "(1 + sin(x))*sign(x - cos(x))", E) == "UNKNOWN"
    # f has a derivative at the zeros of its root's base: the claim undefined there is never certified
    q = _der("sqrt(1 + sin(x))*cos(x)")
    assert _v(q, "cos(x)**2/(2*sqrt(1 + sin(x))) - sin(x)*sqrt(1 + sin(x))", E) != "CORRECT"


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
    assert _v(_der("log(x)/a", None, (), [X, AR]), "1/(a*x)", E) == "CORRECT"
    assert _v(_der("log(x)/log(a)", None, ["a != 1"], [X, AP]), "1/(x*log(a))", E) == "CORRECT"
    assert _v(_der("atan(x/a)", None, ["a != 0"], [X, AR]), "a/(a**2 + x**2) + 1", E) == "INCORRECT"
    # the plain path (f's condition on a half-line): a condition of the claim free of x, on the parameter's region
    assert _v(_der("sqrt(x - a)", None, ["a != 0"], [X, AR]), "1/(2*sqrt(x - a)) + 0/a", E) == "CORRECT"


def test_cell_proof_budget_keeps_one_verify_short():
    U2, U3 = "x**4 - 10*x**2 + 1", "x**3 - 3*x + 1"
    t0 = time.time()
    v = _v(_der(f"Abs({U2})*Abs({U3})"),
           f"(4*x**3 - 20*x)*({U2})*Abs({U3})/Abs({U2}) + (3*x**2 - 3)*({U3})*Abs({U2})/Abs({U3})", "expression")
    assert v != "INCORRECT" and time.time() - t0 < 60


def test_kink_controls_stay_correct():
    E = "expression"
    for f, c in (("Piecewise((exp(x), x > 0), (1 + x, x <= 0))", "Piecewise((exp(x), x > 0), (1, x <= 0))"),
                 ("Max(x, -x)*Max(x, -x)", "2*x"), ("Max(x**3, -x**3)", "3*x**2*sign(x)"),
                 ("x*Max(x, -x)", "2*Max(x, -x)"), ("Max(x, -x)**(1/2)", "sign(x)/(2*sqrt(Abs(x)))")):
        assert _v(_der(f), c, E) == "CORRECT", f
