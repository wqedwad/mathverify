"""Round 5 of d4e (15 Oct 2026): the repros of the attack on round 4 (`d4/saldiri/d4e4/bulgular.json`), their variants and
the controls the main session's decisions (`d4e4/kararlar_tur5.txt`) name. Each case is (label, ir, solution, accepted
verdicts, accepted step statuses); see ../sonda.py, group Z."""
from ortak import NO, NOTNO, NOTOK, OK, UNK, X, anti, der, ir, sol, xc

ANY = {"CORRECT", "UNKNOWN", "INCORRECT"}
NPI = {"name": "n", "domain": "positive_integer"}
NNI = {"name": "n", "domain": "nonneg_integer"}
NI = {"name": "n", "domain": "integer"}
NR = {"name": "n", "domain": "real"}
A_ = {"name": "a", "domain": "real"}


def E(p):
    return sol(p, "expression")


U = "x - cos(x)"
TB = f"(1 + sin(x))*({U})/Abs({U})"


def controls():
    """The decisions' controls: CORRECT before and after."""
    out = []
    out.append(("CTRL |sin x|' = cos x sin x/|sin x|", der("Abs(sin(x))"), E("cos(x)*sin(x)/Abs(sin(x))"), OK, None))
    out.append(("CTRL sqrt(sin x)'", der("sqrt(sin(x))"), E("cos(x)/(2*sqrt(sin(x)))"), OK, None))
    out.append(("CTRL sqrt(1 + sin x)'", der("sqrt(1 + sin(x))"), E("cos(x)/(2*sqrt(1 + sin(x)))"), OK, None))
    out.append(("CTRL sqrt(1 + cos x)'", der("sqrt(1 + cos(x))"), E("-sin(x)/(2*sqrt(1 + cos(x)))"), OK, None))
    out.append(("CTRL sqrt(x - cos x)'", der(f"sqrt({U})"), E(f"(1 + sin(x))/(2*sqrt({U}))"), OK, None))
    out.append(("CTRL |x - cos x|' textbook", der(f"Abs({U})"), E(TB), OK, None))
    out.append(("CTRL (x**4)**(1/3)' = 4 sign(x)|x|**(1/3)/3", der("(x**4)**(1/3)"),
                E("4*sign(x)*Abs(x)**(1/3)/3"), NOTNO, None))
    out.append(("CTRL (x**4)**(1/3)' chain rule, undefined at 0 where f'(0) = 0", der("(x**4)**(1/3)"),
                E("4*x**3/(3*(x**4)**(2/3))"), NOTOK, None))
    out.append(("CTRL (x**3)**(1/3)' x > 0", der("(x**3)**(1/3)", vars_=[{"name": "x", "domain": "positive_real"}]),
                E("1"), OK, None))
    return out


def yo1():
    """D4E4-YO-1: the claim's u > 0 is dropped at the zeros of a root's base only, never of |u|: on u < 0, |u| has a
    derivative and a claim with no value there is wrong (RK-8)."""
    out = []
    out.append(("YO-1 |x - cos x|' tb + 0*log(u): no value at 0 (u = -1), f'(0) = -1", der(f"Abs({U})"),
                E(f"{TB} + 0*log({U})"), NO, None))
    out.append(("YO-1 |x - cos x|' tb + 0*sqrt(u)", der(f"Abs({U})"), E(f"{TB} + 0*sqrt({U})"), NOTOK, None))
    out.append(("YO-1 |x - cos x|' tb + 0*sqrt(-u): no value on u > 0", der(f"Abs({U})"),
                E(f"{TB} + 0*sqrt(-({U}))"), NOTOK, None))
    out.append(("YO-1 |x - cos x|' tb + 0*log(-u)", der(f"Abs({U})"), E(f"{TB} + 0*log(-({U}))"), NOTOK, None))
    out.append(("YO-1 |x - cos x|' tb + 0/u: no value at the zeros only (corners)", der(f"Abs({U})"),
                E(f"{TB} + 0/({U})"), NOTNO, None))
    out.append(("YO-1 3|x - cos x|' 3tb + 0*log(3u)", der(f"3*Abs({U})"), E(f"3*{TB} + 0*log(3*({U}))"), NOTOK, None))
    out.append(("YO-1 |x + exp x|' tb + 0*log(u)", der("Abs(x + exp(x))"),
                E("(1 + exp(x))*(x + exp(x))/Abs(x + exp(x)) + 0*log(x + exp(x))"), NOTOK, None))
    out.append(("YO-1 |x - cos x|' x < 0: -(1 + sin x) + 0*log(u)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                E(f"-(1 + sin(x)) + 0*log({U})"), NOTOK, None))
    out.append(("YO-1 |x - cos x|' x > 1: tb + 0*log(u) (u > 0 on the region)", der(f"Abs({U})", vars_=[xc("x > 1")]),
                E(f"{TB} + 0*log({U})"), NOTNO, None))
    out.append(("YO-1 |x - cos x|' x < 0 ctrl: -(1 + sin x)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                E("-(1 + sin(x))"), NOTNO, None))
    out.append(("YO-1 Max(x, cos x)' tb + 0*log(u)", der("Max(x, cos(x))"),
                E(f"(1 - sin(x))/2 + (1 + sin(x))*({U})/(2*Abs({U})) + 0*log({U})"), NOTOK, None))
    out.append(("YO-1 sqrt(x - cos x)' tb + 0*log(u) (u >= 0 its own: fails at the zeros only)", der(f"sqrt({U})"),
                E(f"(1 + sin(x))/(2*sqrt({U})) + 0*log({U})"), NOTNO, None))
    out.append(("YO-1 (x - cos x)**(1/3)' tb + 0*log(u)", der(f"({U})**(1/3)"),
                E(f"(1 + sin(x))/(3*({U})**(2/3)) + 0*log({U})"), NOTNO, None))
    out.append(("YO-1 |x - cos x| + sqrt(x - cos x) ' + 0*log(u)", der(f"Abs({U}) + sqrt({U})"),
                E(f"{TB} + (1 + sin(x))/(2*sqrt({U})) + 0*log({U})"), NOTNO, None))
    return out


def yo2():
    """D4E4-YO-2: a zero x0 of a root's base u**r with multiplicity m, r*m > 1: f has the derivative 0 there and a claim
    with no value there is not certified (INCORRECT when x0 is found exactly, UNKNOWN otherwise)."""
    out = []
    u = "(x - 1/2)**2*sin(pi*x)"
    du = "(2*(x - 1/2)*sin(pi*x) + pi*(x - 1/2)**2*cos(pi*x))"
    out.append(("YO-2 ((x - 1/2)**2 sin(pi x))**(3/4)' textbook (0/0 at 1/2, f'(1/2) = 0)", der(f"({u})**(3/4)"),
                E(f"3*{du}/(4*({u})**(1/4))"), NOTOK, None))
    ue = "(x**2 - x + 1/4)*sin(pi*x)"
    out.append(("YO-2 expanded base, textbook", der(f"({ue})**(3/4)"),
                E(f"3*((2*x - 1)*sin(pi*x) + pi*(x**2 - x + 1/4)*cos(pi*x))/(4*({ue})**(1/4))"), NOTOK, None))
    out.append(("YO-2 (x**2)**(3/4)' textbook, undefined at 0", der("(x**2)**(3/4)"),
                E("3*x/(2*(x**2)**(1/4))"), NOTOK, None))
    out.append(("YO-2 (x**2)**(3/4)' = 3 sign(x) sqrt|x|/2 [true]", der("(x**2)**(3/4)"),
                E("3*sign(x)*sqrt(Abs(x))/2"), NOTNO, None))
    out.append(("YO-2 ((x - 1)**2*(x + 3))**(3/4)' textbook (0/0 at 1)", der("((x - 1)**2*(x + 3))**(3/4)"),
                E("3*(2*(x - 1)*(x + 3) + (x - 1)**2)/(4*((x - 1)**2*(x + 3))**(1/4))"), NOTOK, None))
    out.append(("YO-2 (x**2*(x - cos x))**(3/4)' textbook (0/0 at 0, zero of x**2)",
                der(f"(x**2*({U}))**(3/4)"),
                E(f"3*(2*x*({U}) + x**2*(1 + sin(x)))/(4*(x**2*({U}))**(1/4))"), NOTOK, None))
    out.append(("YO-2 ((x - cos x)**2)**(3/4)' textbook (unsolved double zero)", der(f"(({U})**2)**(3/4)"),
                E(f"3*(1 + sin(x))*({U})/(2*(({U})**2)**(1/4))"), NOTOK, None))
    out.append(("YO-2 (sin(x)**2)**(3/4)' textbook (double zeros n pi)", der("(sin(x)**2)**(3/4)"),
                E("3*sin(x)*cos(x)/(2*(sin(x)**2)**(1/4))"), NOTOK, None))
    out.append(("YO-2 (x**4)**(1/3)' textbook (m = 4, r m = 4/3)", der("(x**4)**(1/3)"),
                E("4*x**3/(3*(x**4)**(2/3))"), NOTOK, None))
    out.append(("YO-2 ctrl sqrt(x**2 + x**4)' textbook (r m = 1: corner)", der("sqrt(x**2 + x**4)"),
                E("(x + 2*x**3)/sqrt(x**2 + x**4)"), NOTNO, None))
    out.append(("YO-2 ctrl (x**2)**(1/2)' = x/|x| (r m = 1)", der("(x**2)**(1/2)"), E("x/Abs(x)"), NOTNO, None))
    out.append(("YO-2 ctrl sqrt(sin x)' (m = 1)", der("sqrt(sin(x))"), E("cos(x)/(2*sqrt(sin(x)))"), OK, None))
    out.append(("YO-2 ctrl sqrt(1 + sin x)' (m = 2, r m = 1)", der("sqrt(1 + sin(x))"),
                E("cos(x)/(2*sqrt(1 + sin(x)))"), OK, None))
    out.append(("YO-2 ctrl (x**3)**(1/3)' x/|x|-free claim, x > 0", der("(x**3)**(1/3)", vars_=[xc("x > 0")]),
                E("1"), NOTNO, None))
    return out


def yo3():
    """D4E4-YO-3: a touching zero (g = g' = 0) of an unsolved condition g >= 0 of f is a point of the claim's written
    definedness check; none (proved) leaves the reading as it was."""
    out = []
    out.append(("YO-3 (x**2 + 0*sqrt(x sin x))' = 2x + 0/x (f'(0) = 0, claim no value at 0)",
                der("x**2 + 0*sqrt(x*sin(x))"), E("2*x + 0/x"), NOTOK, None))
    out.append(("YO-3 (x**2 + 0*sqrt(x sin x))' = 2x [true]", der("x**2 + 0*sqrt(x*sin(x))"), E("2*x"), NOTNO, None))
    out.append(("YO-3 constraint x sin x >= 0: (x**2)' = 2x + 0/x", der("x**2", vars_=[xc("x*sin(x) >= 0")]),
                E("2*x + 0/x"), NOTOK, None))
    out.append(("YO-3 given x sin x >= 0: (x**2)' = 2x + 0/x", der("x**2", givens=["x*sin(x) >= 0"]),
                E("2*x + 0/x"), NOTOK, None))
    out.append(("YO-3 ((x sin x)**(3/2))' = 3 (x sin x)**(3/2) (sin x + x cos x)/(2 x sin x)",
                der("(x*sin(x))**(3/2)"), E("3*(x*sin(x))**(3/2)*(sin(x) + x*cos(x))/(2*x*sin(x))"), NOTOK, None))
    out.append(("YO-3 ((x sin x)**(3/2))' textbook [true, value 0 at 0]", der("(x*sin(x))**(3/2)"),
                E("3*sqrt(x*sin(x))*(sin(x) + x*cos(x))/2"), NOTNO, None))
    out.append(("YO-3 (x**2 + 0*sqrt(x**2 - x**3 cos x))' = 2x + 0/x", der("x**2 + 0*sqrt(x**2 - x**3*cos(x))"),
                E("2*x + 0/x"), NOTOK, None))
    out.append(("YO-3 touching family n pi (n >= 1): (x**2 + 0*sqrt(sin(x)**2 (x - cos x)))' = 2x + 0*cot(x)",
                der(f"x**2 + 0*sqrt(sin(x)**2*({U}))"), E("2*x + 0*cot(x)"), NOTOK, None))
    out.append(("YO-3 touching family: (x**2 + 0*sqrt(sin(x)**2 (x - cos x)))' = 2x [true]",
                der(f"x**2 + 0*sqrt(sin(x)**2*({U}))"), E("2*x"), NOTNO, None))
    out.append(("YO-3 antiderivative of 2x + 0*sqrt(x sin x): x**2 + 0/x", anti("2*x + 0*sqrt(x*sin(x))"),
                E("x**2 + 0/x"), NOTOK, None))
    out.append(("YO-3 antiderivative of 2x + 0*sqrt(x sin x): x**2 [true]", anti("2*x + 0*sqrt(x*sin(x))"),
                E("x**2"), NOTNO, None))
    out.append(("YO-3 isolated zero 0 of x**2 (x - cos x) >= 0: (x**2 + 0*sqrt(...))' = 2x + 0/x [true]",
                der(f"x**2 + 0*sqrt(x**2*({U}))"), E("2*x + 0/x"), NOTNO, None))
    out.append(("YO-3 ctrl (x**2 + 0*sqrt(x - cos x))' = 2x", der(f"x**2 + 0*sqrt({U})"), E("2*x"), NOTNO, None))
    out.append(("YO-3 ctrl (x**2 + 0*sqrt(x - cos x))' = 2x + 0/x (0 is no point of the domain)",
                der(f"x**2 + 0*sqrt({U})"), E("2*x + 0/x"), NOTNO, None))
    out.append(("YO-3 ctrl sqrt(x - cos x)' (no touching zero)", der(f"sqrt({U})"), E(f"(1 + sin(x))/(2*sqrt({U}))"),
                OK, None))
    return out


def rk1():
    """D4E4-RK-1: a rejection resting only on random_point's defined_on_one_side_only at a base zero where SymPy's
    formula is nan is no rejection."""
    out = []
    tr = "3*2**(3/4)*sign(sin(x/2))*sqrt(Abs(sin(x/2)))*cos(x/2)/4"
    out.append(("RK-1 (1 - cos x)**(3/4)' everywhere defined [true]", der("(1 - cos(x))**(3/4)"), E(tr), NOTNO, None))
    out.append(("RK-1 (1 - cos x)**(3/4)' everywhere defined, wrong factor", der("(1 - cos(x))**(3/4)"),
                E(tr.replace("3*2", "2*2")), NOTOK, None))
    out.append(("RK-1 (1 - cos x)**(3/4)' chain rule (no value at 2k pi, f' = 0 there)", der("(1 - cos(x))**(3/4)"),
                E("3*sin(x)/(4*(1 - cos(x))**(1/4))"), NOTOK, None))
    out.append(("RK-1 (1 - cos x)**(5/4)' = 5 (1 - cos x)**(1/4) sin x/4 [true]", der("(1 - cos(x))**(5/4)"),
                E("5*(1 - cos(x))**(1/4)*sin(x)/4"), NOTNO, None))
    out.append(("RK-1 sibling: antiderivative of the everywhere defined derivative is (1 - cos x)**(3/4) [true]",
                anti(tr), E("(1 - cos(x))**(3/4)"), NOTNO, None))
    out.append(("RK-1 sibling: antiderivative, (1 - cos x)**(3/4) + x [false]", anti(tr), E("(1 - cos(x))**(3/4) + x"),
                NOTOK, None))
    out.append(("RK-1 sibling: antiderivative of 3 sign(x) sqrt|x|/2 is (x**2)**(3/4) [true]",
                anti("3*sign(x)*sqrt(Abs(x))/2"), E("(x**2)**(3/4)"), NOTNO, None))
    out.append(("RK-1 (x**2)**(3/4)' = 3 sign(x) sqrt|x|/2 [true]", der("(x**2)**(3/4)"),
                E("3*sign(x)*sqrt(Abs(x))/2"), NOTNO, None))
    out.append(("RK-1 (x**2)**(3/4)' = 3 sign(x) sqrt|x| [false]", der("(x**2)**(3/4)"),
                E("3*sign(x)*sqrt(Abs(x))"), NOTOK, None))
    return out


PW = "Piecewise((x**2, x < 1), (2*x, x >= 1))"


def _f(expr):
    return [{"name": "f", "expr": expr, "args": ["x"], "params": []}]


def u2():
    """D4E4-U2: a closed Piecewise (no free symbol once substituted) is read by the exact sign of its conditions."""
    out = []
    ev = lambda e, g=(), v=None, fn=None: ir("evaluate", {"expr": e}, g, v or [X], "scalar", functions=fn)  # noqa: E731
    out.append(("U2 evaluate f(2), f piecewise -> 4", ev("f(2)", fn=_f(PW)), sol("4"), OK, None))
    out.append(("U2 evaluate f(2), f piecewise -> 3", ev("f(2)", fn=_f(PW)), sol("3"), NO, None))
    out.append(("U2 evaluate f(0), f piecewise -> 0", ev("f(0)", fn=_f(PW)), sol("0"), OK, None))
    out.append(("U2 evaluate f(1), f piecewise -> 2 (second branch)", ev("f(1)", fn=_f(PW)), sol("2"), OK, None))
    out.append(("U2 evaluate f(1), f piecewise -> 1", ev("f(1)", fn=_f(PW)), sol("1"), NO, None))
    out.append(("U2 evaluate PW, given x = 2 -> 4", ev(PW, ["x = 2"]), sol("4"), OK, None))
    out.append(("U2 evaluate PW, given x = 2 -> 3", ev(PW, ["x = 2"]), sol("3"), NO, None))
    out.append(("U2 evaluate PW with a, given x = 2, a = 3 -> 5",
                ev("Piecewise((a*x, x < 1), (x + a, x >= 1))", ["x = 2", "a = 3"], [X, A_]), sol("5"), OK, None))
    out.append(("U2 evaluate PW with a, given x = 2, a = 3 -> 6",
                ev("Piecewise((a*x, x < 1), (x + a, x >= 1))", ["x = 2", "a = 3"], [X, A_]), sol("6"), NO, None))
    out.append(("U2 evaluate f(2), chosen branch undefined (1/(x - 2))",
                ev("f(2)", fn=_f("Piecewise((x**2, x < 1), (1/(x - 2), x >= 1))")), sol("0"), NOTOK, None))
    out.append(("U2 evaluate f(2), an earlier condition undefined (log(x - 3) > 0)",
                ev("f(2)", fn=_f("Piecewise((1, log(x - 3) > 0), (2, log(x - 3) <= 0))")), sol("2"), NOTOK, None))
    out.append(("U2 evaluate f(2), the chosen branch's condition undefined (sqrt(x - 3) < 1)",
                ev("f(2)", fn=_f("Piecewise((1, x > 5), (2, sqrt(x - 3) < 1), (3, x <= 5))")), sol("2"), NOTOK, None))
    out.append(("U2 evaluate f(355/113), x < pi false -> 2",
                ev("f(355/113)", fn=_f("Piecewise((1, x < pi), (2, x >= pi))")), sol("2"), OK, None))
    out.append(("U2 evaluate f(355/113), x < pi false -> 1",
                ev("f(355/113)", fn=_f("Piecewise((1, x < pi), (2, x >= pi))")), sol("1"), NO, None))
    out.append(("U2 evaluate f(1), sin**2 + cos**2 < 1 (exactly false) -> 2",
                ev("f(1)", fn=_f("Piecewise((1, sin(x)**2 + cos(x)**2 < 1), (2, sin(x)**2 + cos(x)**2 >= 1))")), sol("2"), NOTNO, None))
    out.append(("U2 evaluate f(1), sin**2 + cos**2 < 1 (exactly false) -> 1",
                ev("f(1)", fn=_f("Piecewise((1, sin(x)**2 + cos(x)**2 < 1), (2, sin(x)**2 + cos(x)**2 >= 1))")), sol("1"), NOTOK, None))
    out.append(("U2 evaluate f(2), gap at 2 (no branch)",
                ev("f(2)", fn=_f("Piecewise((x, x < 2), (x + 1, x > 2))")), sol("2"), NOTOK, None))
    out.append(("U2 evaluate f(2), gap at 2 -> 3", ev("f(2)", fn=_f("Piecewise((x, x < 2), (x + 1, x > 2))")),
                sol("3"), NOTOK, None))
    out.append(("U2 evaluate f(2), True as the last condition (not read as written)",
                ev("f(2)", fn=_f("Piecewise((x**2, x < 1), (2*x, True))")), sol("4"), NOTNO, None))
    out.append(("U2 evaluate f(1/2), x**2 < 1/4 false, x**2 >= 1/4 -> 1/2 + 1",
                ev("f(1/2)", fn=_f("Piecewise((x, x**2 < 1/4), (x + 1, x**2 >= 1/4))")), sol("3/2"), OK, None))
    out.append(("U2 limit PW at 2 -> 4", ir("limit", {"expr": PW, "var": "x", "to": "2"}, shape="scalar"), sol("4"),
                OK, None))
    out.append(("U2 solve PW = 4 -> {-2, 2}", ir("solve_equation", {"var": "x", "equation": PW + " = 4"}),
                sol("{-2, 2}", "set"), OK, None))
    return out


def u3():
    """D4E4-U3: a family listed in a wide bounded region is cut at the limit before the range is built."""
    out = []
    out.append(("U3 1 < x < 10**12: (x**2)' = 2x + 0*cot(x) (pi in the region)",
                der("x**2", vars_=[xc("x > 1", "x < 10**12")]), E("2*x + 0*cot(x)"), NOTOK, None))
    out.append(("U3 1 < x < 10**100: (x**2)' = 2x + 0*cot(x)",
                der("x**2", vars_=[xc("x > 1", "x < 10**100")]), E("2*x + 0*cot(x)"), NOTOK, None))
    out.append(("U3 -10**100 < x < -1: (x**2)' = 2x + 0*cot(x)",
                der("x**2", vars_=[xc("x > -10**100", "x < -1")]), E("2*x + 0*cot(x)"), NOTOK, None))
    out.append(("U3 1 < x < 10**12: (x**2)' = 2x [true]", der("x**2", vars_=[xc("x > 1", "x < 10**12")]), E("2*x"),
                NOTNO, None))
    out.append(("U3 1 < x < 3: (x**2)' = 2x + 0*cot(x) (pi outside)", der("x**2", vars_=[xc("x > 1", "x < 3")]),
                E("2*x + 0*cot(x)"), NOTNO, None))
    return out


def u4():
    """D4E4-U4: `_value_holes` spends the reading's budget of derivative_at_point calls (a hole: a zero where f has a
    derivative and SymPy's formula 3*(2*x - 2*k)/(4*(x**2 - 2*k*x + k**2)**(1/4)) is 0/0)."""
    out = []
    f6 = " + ".join(f"(x**2 - {2 * k}*x + {k * k})**(3/4)" for k in range(1, 7))
    c6 = " + ".join(f"3*sign(x - {k})*sqrt(Abs(x - {k}))/2" for k in range(1, 7))
    out.append(("U4 six value holes, true claim", der(f6), E(c6), NOTNO, None))
    out.append(("U4 six value holes, wrong claim", der(f6), E(c6.replace("3*sign", "5*sign", 1)), NOTOK, None))
    f2 = " + ".join(f"(x**2 - {2 * k}*x + {k * k})**(3/4)" for k in range(1, 3))
    c2 = " + ".join(f"3*sign(x - {k})*sqrt(Abs(x - {k}))/2" for k in range(1, 3))
    out.append(("U4 two value holes, true claim (within the budget)", der(f2), E(c2), NOTNO, None))
    out.append(("U4 two value holes, wrong value at 1", der(f2), E(c2 + " + 1 - sign(Abs(x - 1))"), NOTOK, None))
    return out


def u5():
    """D4E4-U5: an exponent declared an integer is no reason for base > 0 in the written domain."""
    out = []
    out.append(("U5 n Z+: (x**2)**n' = 2n x**(2n - 1)", der("(x**2)**n", vars_=[X, NPI]), E("2*n*x**(2*n - 1)"), NOTNO,
                None))
    out.append(("U5 n Z+: (x**2)**n' = 2n x**(2n)", der("(x**2)**n", vars_=[X, NPI]), E("2*n*x**(2*n)"), NOTOK, None))
    out.append(("U5 ctrl n Z+: (x**n)' = n x**(n - 1)", der("x**n", vars_=[X, NPI]), E("n*x**(n - 1)"), OK, None))
    out.append(("U5 n Z: (x**2)**n' = 2n x**(2n - 1)", der("(x**2)**n", vars_=[X, NI]), E("2*n*x**(2*n - 1)"), NOTNO,
                None))
    out.append(("U5 n Z: (x**n)' = n x**(n - 1)", der("x**n", vars_=[X, NI]), E("n*x**(n - 1)"), NOTNO, None))
    out.append(("U5 n N0: (x**2)**n' = 2n x**(2n - 1) (n = 0: no value at 0 where f' = 0)",
                der("(x**2)**n", vars_=[X, NNI]), E("2*n*x**(2*n - 1)"), NOTOK, None))
    out.append(("U5 n real: (x**2)**n' = 2n x**(2n - 1) (no value on x < 0)", der("(x**2)**n", vars_=[X, NR]),
                E("2*n*x**(2*n - 1)"), NOTOK, None))
    out.append(("U5 n Z+: evaluate (x**2)**n at x = -1, n = 2 -> 1",
                ir("evaluate", {"expr": "(x**2)**n"}, ["x = -1", "n = 2"], [X, NPI], "scalar"), sol("1"), OK, None))
    out.append(("U5 n Z+: x**n/x at x = 0 has no value",
                ir("evaluate", {"expr": "x**n/x"}, ["x = 0", "n = 2"], [X, NPI], "scalar"), sol("0"), NOTOK, None))
    return out


def cases():
    return controls() + yo1() + yo2() + yo3() + rk1() + u2() + u3() + u4() + u5()
