"""Fourth audit, part d4e, round 5 (15 Oct 2026): the attack on round 4 (`denetim/2026-10-01/d4/saldiri/d4e4/`) and the
main session's decisions (`d4e4/kararlar_tur5.txt`). Each assertion below failed on 8025acb unless it is marked as a
control.

* YO-1: the claim's u > 0 was dropped at the zeros of |u| as at a root's base: |x - cos(x)|' + 0*log(x - cos(x)).
* YO-2: a zero of a root's base where f has a derivative (r*m > 1) was skipped as a zero of a family's u.
* YO-3: a touching zero of an unsolved g >= 0 of f was no point of the claim's written definedness (x*sin(x) at 0).
* RK-1: a right claim was refuted where SymPy's derivative formula alone has no value ((1 - cos(x))**(3/4) at 0).
* U2: a Piecewise with closed conditions (f(2) for a piecewise f) was undecided.
* U3: a family listed in a wide region built the whole integer range (MemoryError, OverflowError).
* U4: each hole of `_value_holes` called derivative_at_point outside the reading's budget.
* U5: an exponent declared an integer gave its base the condition > 0: (x**2)**n' = 2*n*x**(2*n - 1) refuted.
* Merge (wip/birlesik-a): SymPy's `equals` False overruled an exact cell proof (Max(x**3, -x**3)' = 3*x**2*sign(x)).
  The last test's assertions other than its controls fail on the merged 5e88d41 and hold on 8025acb.
"""
import time

import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
A_ = {"name": "a", "domain": "real"}
U = "x - cos(x)"
TB = f"(1 + sin(x))*({U})/Abs({U})"
E = "expression"


def xc(*cs):
    return {"name": "x", "domain": "real", "constraints": list(cs)}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _v(ir, payload, kind="value"):
    return verify(ir, {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}).verdict


def _der(f, givens=(), vars_=None):
    return _ir("derivative", {"f": f, "var": "x"}, givens, vars_, "expression")


def test_abs_switch_claim_condition_read_on_both_halves():
    # x = 0: x - cos(x) = -1, log(-1) has no real value, and |x - cos(x)| has the derivative -1 there
    assert _v(_der(f"Abs({U})"), f"{TB} + 0*log({U})", E) == "INCORRECT"
    assert _v(_der(f"3*Abs({U})"), f"3*{TB} + 0*log(3*({U}))", E) == "INCORRECT"
    assert _v(_der("Abs(x + exp(x))"), "(1 + exp(x))*(x + exp(x))/Abs(x + exp(x)) + 0*log(x + exp(x))",
              E) == "INCORRECT"
    assert _v(_der(f"Abs({U})", vars_=[xc("x < 0")]), f"-(1 + sin(x)) + 0*log({U})", E) == "INCORRECT"
    # u > 0 on the region, not solved: no witness, no proof
    assert _v(_der(f"Abs({U})", vars_=[xc("x > 1")]), f"{TB} + 0*log({U})", E) == "UNKNOWN"
    # controls: the textbook claim, a claim undefined at the corners alone, a root's base (u >= 0 its own)
    assert _v(_der(f"Abs({U})"), TB, E) == "CORRECT"
    assert _v(_der(f"Abs({U})"), f"{TB} + 0/({U})", E) == "CORRECT"
    assert _v(_der(f"sqrt({U})"), f"(1 + sin(x))/(2*sqrt({U})) + 0*log({U})", E) == "CORRECT"


def test_value_point_of_a_root_base_is_no_kink():
    from mathverify.certify import calculus as C
    ue = "(x**2 - x + 1/4)*sin(pi*x)"
    claim = f"3*((2*x - 1)*sin(pi*x) + pi*(x**2 - x + 1/4)*cos(pi*x))/(4*({ue})**(1/4))"
    # f'(1/2) = 0 (a double zero, r*m = 3/2), the claim is 0/0 there
    assert _v(_der(f"({ue})**(3/4)"), claim, E) == "INCORRECT"
    x, n = sp.Symbol("x", real=True), sp.Dummy("n", integer=True)
    u = sp.sympify(ue, locals={"x": x})
    kr = {"values": [sp.S.Half], "kinks": [], "families": [(u, [2 * n])]}
    assert C._no_derivative_at(kr, x, sp.S.Half) is False
    assert C._no_derivative_at(kr, x, 2 * n) is True                 # the corners 2n: 1/2 is none of them
    assert C._no_derivative_at(kr, x, n / 2) is False                # a family holding 1/2
    # controls: r*m <= 1 proved (a corner at each zero)
    assert _v(_der("sqrt(x**2 + x**4)"), "(x + 2*x**3)/sqrt(x**2 + x**4)", E) == "CORRECT"
    assert _v(_der("sqrt(1 + sin(x))"), "cos(x)/(2*sqrt(1 + sin(x)))", E) == "CORRECT"
    assert _v(_der("sqrt(1 + cos(x))"), "-sin(x)/(2*sqrt(1 + cos(x)))", E) == "CORRECT"
    assert _v(_der("sqrt(sin(x))"), "cos(x)/(2*sqrt(sin(x)))", E) == "CORRECT"
    assert _v(_der("(x**4)**(1/3)"), "4*sign(x)*Abs(x)**(1/3)/3", E) == "CORRECT"


def test_touching_zero_of_an_unsolved_condition():
    from mathverify.certify import calculus as C
    for f, vars_, givens in (("x**2 + 0*sqrt(x*sin(x))", None, ()), ("x**2", [xc("x*sin(x) >= 0")], ()),
                             ("x**2", None, ["x*sin(x) >= 0"])):
        assert _v(_der(f, givens, vars_), "2*x + 0/x", E) != "CORRECT"
    # 0 is a strict minimum of x*sin(x) (an interior point of the region) where x**2 has the derivative 0
    assert _v(_der("x**2", vars_=[xc("x*sin(x) >= 0")]), "2*x + 0/x", E) == "INCORRECT"
    assert _v(_der("(x*sin(x))**(3/2)"), "3*(x*sin(x))**(3/2)*(sin(x) + x*cos(x))/(2*x*sin(x))", E) != "CORRECT"
    # the touching zeros n*pi (n >= 1) of sin(x)**2*(x - cos(x)) >= 0, a family
    assert _v(_der(f"x**2 + 0*sqrt(sin(x)**2*({U}))"), "2*x + 0*cot(x)", E) != "CORRECT"
    # controls: no touching zero (g' = 1 + sin(x) != 0 where g = 0), an isolated zero (g'' < 0), the right claims
    assert _v(_der(f"sqrt({U})"), f"(1 + sin(x))/(2*sqrt({U}))", E) == "CORRECT"
    assert _v(_der(f"x**2 + 0*sqrt({U})"), "2*x + 0/x", E) == "CORRECT"
    assert _v(_der(f"x**2 + 0*sqrt(x**2*({U}))"), "2*x + 0/x", E) == "CORRECT"
    assert _v(_der("x**2 + 0*sqrt(x*sin(x))"), "2*x", E) == "CORRECT"
    x = sp.Symbol("x", real=True)
    assert C._loose_zero(x * sp.sin(x) >= 0, x, sp.S.Zero) == "inside"
    assert C._loose_zero(x ** 2 * (x - sp.cos(x)) >= 0, x, sp.S.Zero) == "end"
    assert C._loose_zero(x - sp.cos(x) >= 0, x, sp.S.Zero) == "end"
    # g''(0) = 1 by SymPy's formula, but g is no analytic function at 0 (x**2*(2 - 3*H(x)) < 0 on x > 0)
    assert C._loose_zero(x ** 2 * (2 - 3 * sp.Heaviside(x)) >= 0, x, sp.S.Zero) is None


def test_formula_hole_refutation_softened():
    from mathverify.certify import calculus as C
    x = sp.Symbol("x", real=True)
    fa = (1 - sp.cos(x)) ** sp.Rational(3, 4)

    def cev(point="0", lhs="0", rhs="nan", exact="defined_on_one_side_only"):
        return {"method": "random_point", "random_point": {"counterexample": {
            "point": {"x": point}, "lhs": lhs, "rhs": rhs, "exact": exact}}}
    assert C._formula_hole_refutation(cev(), fa, x) is True
    assert C._formula_hole_refutation(cev(lhs="nan", rhs="0"), fa, x) is False         # the claim has no value
    assert C._formula_hole_refutation(cev(lhs="nan", rhs="0"), fa, x, side="lhs") is True
    assert C._formula_hole_refutation(cev(point="1"), fa, x) is False                    # no zero of the base
    assert C._formula_hole_refutation(cev(exact="values_differ"), fa, x) is False
    f = "(1 - cos(x))**(3/4)"
    right = "3*2**(3/4)*sign(sin(x/2))*sqrt(Abs(sin(x/2)))*cos(x/2)/4"
    assert _v(_der(f), right, E) == "UNKNOWN"
    assert _v(_der(f), right.replace("3*2", "2*2"), E) == "INCORRECT"                       # control: wrong factor
    assert _v(_der(f), "3*sin(x)/(4*(1 - cos(x))**(1/4))", E) == "INCORRECT"                # control: RK-8
    assert _v(_der("(1 - cos(x))**(5/4)"), "5*(1 - cos(x))**(1/4)*sin(x)/4", E) == "CORRECT"  # control
    # the same for a primitive: F's derivative formula is 0/0 at 0
    anti = _ir("antiderivative", {"integrand": right, "var": "x"}, shape="expression")
    assert _v(anti, f, E) == "UNKNOWN"
    assert _v(anti, f + " + x", E) == "INCORRECT"                                            # control


def test_closed_piecewise_read_exactly():
    from mathverify.certify import domain as D
    pw = "Piecewise((x**2, x < 1), (2*x, x >= 1))"

    def ev(e, givens=(), vars_=None, f=None):
        fn = [{"name": "f", "expr": f, "args": ["x"], "params": []}] if f else None
        return _ir("evaluate", {"expr": e}, givens, vars_, functions=fn)
    assert _v(ev("f(2)", f=pw), "4") == "CORRECT"
    assert _v(ev("f(2)", f=pw), "3") == "INCORRECT"
    assert _v(ev("f(1)", f=pw), "2") == "CORRECT"
    assert _v(ev(pw, ["x = 2"]), "4") == "CORRECT"
    assert _v(ev("Piecewise((a*x, x < 1), (x + a, x >= 1))", ["x = 2", "a = 3"], [X, A_]), "5") == "CORRECT"
    assert _v(ev("f(355/113)", f="Piecewise((1, x < pi), (2, x >= pi))"), "2") == "CORRECT"
    assert _v(ev("f(355/113)", f="Piecewise((1, x < pi), (2, x >= pi))"), "1") == "INCORRECT"
    # no value: the branch taken, a condition before it, a gap
    for f in ("Piecewise((x**2, x < 1), (1/(x - 2), x >= 1))", "Piecewise((1, log(x - 3) > 0), (2, log(x - 3) <= 0))",
              "Piecewise((x, x < 2), (x + 1, x > 2))"):
        assert _v(ev("f(2)", f=f), "2") == "UNKNOWN"
    # the exact sign, never SymPy's evaluation: sin(1)**2 + cos(1)**2 - 1 is 0
    with sp.evaluate(False):
        c = sp.StrictLessThan(sp.sin(1) ** 2 + sp.cos(1) ** 2, 1)
    assert D._closed_truth(c) is False
    assert _v(ev("f(1)", f="Piecewise((1, sin(x)**2 + cos(x)**2 < 1), (2, sin(x)**2 + cos(x)**2 >= 1))"),
              "2") == "CORRECT"
    assert D._closed_truth(sp.And(sp.Lt(1, 2, evaluate=False), sp.Lt(sp.pi, 3, evaluate=False))) is False
    assert D._closed_truth(sp.Or(sp.Lt(1, 2, evaluate=False), sp.Lt(sp.pi, 3, evaluate=False))) is True
    assert D._closed_truth(sp.Not(sp.Lt(sp.pi, 3, evaluate=False))) is True
    assert D._closed_truth(sp.Eq(sp.sqrt(2) ** 2, 2, evaluate=False)) is True
    x = sp.Symbol("x", real=True)
    g13, b = sp.gamma(sp.Rational(1, 3)) * sp.gamma(sp.Rational(2, 3)), 2 * sp.pi / sp.sqrt(3)   # equal, unproved
    with sp.evaluate(False):
        taken_undefined = sp.Piecewise((x ** 2, sp.Lt(2, 1)), (1 / (2 - sp.Integer(2)), sp.Ge(2, 1)))
        gap = sp.Piecewise((2, sp.Lt(2, 2)), (3, sp.Gt(2, 2)))
        cond_no_value = sp.Piecewise((1, sp.Gt(sp.log(-1), 0)), (2, sp.Le(sp.log(-1), 0)))
        undecided = sp.Piecewise((1, sp.Lt(g13, b)), (2, sp.Ge(g13, b)))
        free_value = sp.Piecewise((x, sp.Lt(2, 1)), (x ** 2 + 1 / x, sp.Ge(2, 1)))
    for pw in (taken_undefined, gap, cond_no_value):
        assert sp.false in D.definedness_conditions(pw, None)
    assert D.definedness_conditions(undecided, None) == [D.DEFINEDNESS_UNDECIDED]
    assert D.definedness_conditions(free_value, None) == [sp.Ne(x, 0)]


def test_family_members_bounded():
    from mathverify.certify import calculus as C
    n = sp.Dummy("n", integer=True)
    t0 = time.time()
    members, complete = C._family_members(n * sp.pi, sp.Interval.open(1, 10 ** 100))
    assert members == [n_ * sp.pi for n_ in range(1, 7)] and complete is False and time.time() - t0 < 5
    members, complete = C._family_members(n * sp.pi, sp.Interval.open(-10 ** 100, -1))
    assert len(members) == 6 and complete is False
    assert C._family_members(n * sp.pi, sp.Interval.open(1, 3 * sp.pi + 1)) == ([sp.pi, 2 * sp.pi, 3 * sp.pi], True)
    assert _v(_der("x**2", vars_=[xc("x > 1", "x < 10**100")]), "2*x + 0*cot(x)", E) == "INCORRECT"
    assert _v(_der("x**2", vars_=[xc("x > 1", "x < 3")]), "2*x + 0*cot(x)", E) == "CORRECT"   # control


def test_value_holes_spend_the_reading_budget(monkeypatch):
    from mathverify.certify import calculus as C
    calls = []
    plain = C.derivative_at_point

    def counted(*a, **k):
        calls.append(1)
        return plain(*a, **k)
    monkeypatch.setattr(C, "derivative_at_point", counted)
    f6 = " + ".join(f"(x**2 - {2 * k}*x + {k * k})**(3/4)" for k in range(1, 7))
    c6 = " + ".join(f"3*sign(x - {k})*sqrt(Abs(x - {k}))/2" for k in range(1, 7))
    assert _v(_der(f6), c6, E) == "UNKNOWN" and len(calls) <= C._KINK_BUDGET                # six holes: 6 calls
    calls.clear()
    f2 = " + ".join(f"(x**2 - {2 * k}*x + {k * k})**(3/4)" for k in (1, 2))
    c2 = " + ".join(f"3*sign(x - {k})*sqrt(Abs(x - {k}))/2" for k in (1, 2))
    # control: two holes within the budget, the claim's wrong value at 1 read there
    assert _v(_der(f2), c2 + " + 1 - sign(Abs(x - 1))", E) == "INCORRECT" and 0 < len(calls) <= C._KINK_BUDGET
    # a hole classified by derivative_at_point is read once: |x| - sqrt(x**2 + x**4) at 0
    calls.clear()
    assert _v(_der("Abs(x) - sqrt(x**2 + x**4)"), "sign(x)*(1 - (1 + 2*x**2)/sqrt(1 + x**2))", E) == "CORRECT"
    assert len(calls) == 1


def test_integer_exponent_written_domain():
    from mathverify.certify.domain import definedness_conditions
    x = sp.Symbol("x", real=True)
    npos, nint, nreal = (sp.Symbol("n", integer=True, positive=True), sp.Symbol("n", integer=True),
                         sp.Symbol("n", real=True))
    with sp.evaluate(False):
        assert definedness_conditions(sp.Pow(x ** 2, npos), None) == []
        assert definedness_conditions(sp.Pow(x, 2 * npos - 1), None) == []      # n - 1 unevaluated, as written
        assert definedness_conditions(sp.Pow(x, npos - 1), None) == []
        assert definedness_conditions(sp.Pow(x, nint), None) == [sp.Ne(x, 0)]
        assert definedness_conditions(sp.Pow(x, nreal), None) == [x > 0]                   # control
    NP, NI, NR = ({"name": "n", "domain": d} for d in ("positive_integer", "integer", "real"))
    assert _v(_der("(x**2)**n", vars_=[X, NP]), "2*n*x**(2*n - 1)", E) == "CORRECT"
    assert _v(_der("(x**2)**n", vars_=[X, NI]), "2*n*x**(2*n - 1)", E) == "CORRECT"
    assert _v(_der("(x**2)**n", vars_=[X, NP]), "2*n*x**(2*n)", E) == "INCORRECT"         # control
    assert _v(_der("x**n", vars_=[X, NP]), "n*x**(n - 1)", E) == "CORRECT"                # control
    assert _v(_der("(x**2)**n", vars_=[X, NR]), "2*n*x**(2*n - 1)", E) != "CORRECT"       # control


def test_exact_cell_proof_is_not_overruled_by_equals():
    # merge of d4c round 4 (SymPy's `equals` False against agreement at points) with d4e round 4: an identity proved
    # exactly on each cell of sign(x) stands; SymPy reads x as complex, and sign(x**3) != sign(x) there
    assert _v(_der("Max(x**3, -x**3)"), "3*x**2*sign(x)", E) == "CORRECT"
    assert _v(_der("x**2"), "Piecewise((2*x**2/x, Ne(x, 0)), (0, Eq(x, 0)))", E) == "CORRECT"
    anti = _ir("antiderivative", {"integrand": "3*x**2*sign(x)", "var": "x"}, shape="expression")
    assert _v(anti, "Max(x**3, -x**3)", E) == "CORRECT"
    assert _v(anti, "Max(x**3, -x**3) + x", E) == "INCORRECT"                               # control
    assert _v(_der("Max(x**3, -x**3)"), "3*x**2", E) != "CORRECT"                            # control
