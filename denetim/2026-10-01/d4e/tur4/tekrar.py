"""Round 4 of d4e (8 Oct 2026): the repros of the attack on round 3 (`d4/saldiri/d4e3/bulgular.json`), the independent
validators' variants and controls, and the cases the main session's decisions (`d4e3/kararlar_tur4.txt`) name. Each case
is (label, ir, solution, accepted verdicts, accepted step statuses); see ../sonda.py, group W."""
from ortak import (DNE, NO, NOTNO, NOTOK, OK, UNK, X, XP, Y, T_, A_, K_, anti, der, ev1, ext, ir, lim, sol, ss, tan,
                   xc)

ANY = {"CORRECT", "UNKNOWN", "INCORRECT"}
XPOS = {"name": "x", "domain": "positive_real"}
AP = {"name": "a", "domain": "positive_real"}
AR = {"name": "a", "domain": "real"}
NPI = {"name": "n", "domain": "positive_integer"}
B_ = {"name": "b", "domain": "real"}


def E(p):
    return sol(p, "expression")


def yo4():
    """YO-4 = RK-2: a SymPy limit for a generic value of a declared-sign parameter is no proof of convergence."""
    out = []
    A = "Integral(1/((x - 1)**2*t**2 + 1), (t, 1, oo))"
    AC = "Integral(cos(t)**2/((x - 1)**2*t**2 + 1), (t, 1, oo))"
    I1 = "Integral(1/(1 + (x - 1)**2*t**2), (t, 0, oo))"
    I4 = "Integral(1/(1 + (x - 1)**2*t**4), (t, 1, oo))"
    V = [XPOS, T_]
    out.append(("YO-4 der x**2 + 0*A at 1, x > 0: 2", der(f"x**2 + 0*{A}", "1", vars_=V), sol("2"), NOTOK, None))
    out.append(("YO-4 der x**2 + 0*AC at 1, x > 0: 2", der(f"x**2 + 0*{AC}", "1", vars_=V), sol("2"), NOTOK, None))
    out.append(("YO-4 der x**2 + 0*I4 at 1, x > 0: 2", der(f"x**2 + 0*{I4}", "1", vars_=V), sol("2"), NOTOK, None))
    out.append(("YO-4 tangent x**2 + 0*A at 1: y = 2x - 1", tan(f"x**2 + 0*{A}", "1", vars_=V),
                sol("y = 2*x - 1", "equation"), NOTOK, None))
    for eq, wrong, right in ((f"x**2 - 1 + 0*{A} = 0", "{1}", "EmptySet"), (f"x - 1 + 0*{I1} = 0", "{1}", "EmptySet"),
                             (f"x**2 - 1 + 0*{I4} = 0", "{1}", "EmptySet")):
        q = ir("solve_equation", {"var": "x", "equation": eq}, vars_=V)
        out.append((f"YO-4 solve {eq}: {wrong} [1 is no point of the domain]", q, sol(wrong, "set"), NOTOK, None))
        out.append((f"YO-4 mirror solve {eq}: {right}", q, sol(right, "set"), NOTNO, None))
    q = ir("solve_inequality", {"var": "x", "inequality": f"x + 0*{A} >= 1"}, vars_=V)
    out.append(("YO-4 solve x + 0*A >= 1: [1, oo)", q, sol("Interval(1, oo)", "interval"), NOTOK, None))
    out.append(("YO-4 mirror solve x + 0*A >= 1: (1, oo)", q, sol("Interval.open(1, oo)", "interval"), NOTNO, None))
    out.append(("YO-4 max -(x - 1)**2 + 0*A on [1/2, 2]: 0 [not attained]",
                ext(f"-(x - 1)**2 + 0*{A}", "max", "[1/2, 2]", vars_=V), sol("0"), NOTOK, None))
    out.append(("YO-4 min (x - 1)**2 + 0*I1 on [1/2, 2]: 0 [not attained]",
                ext(f"(x - 1)**2 + 0*{I1}", "min", "[1/2, 2]", vars_=V), sol("0"), NOTOK, None))
    out.append(("YO-4 der x + 0*I1 at 1, x > 0: 1", der(f"x + 0*{I1}", "1", vars_=V), sol("1"), NOTOK, None))
    out.append(("YO-4 der x**2 + 0*A at 1, x real: 2 [ctrl]", der(f"x**2 + 0*{A}", "1", vars_=[X, T_]), sol("2"),
                NOTOK, None))
    # evaluate: the project's convention accepts an isolated written undefinedness (0/(a - 1) + a is a): either verdict
    out.append(("YO-4 evaluate 0*Integral(1/((a-1)**2*t**2+1),(t,1,oo)) + a, a > 0: a",
                ev1("0*Integral(1/((a - 1)**2*t**2 + 1), (t, 1, oo)) + a", vars_=[AP, T_]), sol("a"), NOTNO, None))
    out.append(("YO-4 evaluate 0*Integral(1/((n-1)**2*t**2+1),(t,1,oo)) + 1, n positive integer: 1",
                ev1("0*Integral(1/((n - 1)**2*t**2 + 1), (t, 1, oo)) + 1", vars_=[NPI, T_]), sol("1"), NOTNO, None))
    out.append(("YO-4 evaluate 0*Integral(1/(1 + (a - 1)**2*t**2), (t, 0, oo)) + 1, a > 0: 1",
                ev1("0*Integral(1/(1 + (a - 1)**2*t**2), (t, 0, oo)) + 1", vars_=[T_, AP]), sol("1"), NOTNO, None))
    # the validator's controls: the same tasks with an elementary written singularity at the same point
    out.append(("YO-4 ctrl der x**2 + 0/(x - 1) at 1, x > 0: 2", der("x**2 + 0/(x - 1)", "1", vars_=V), sol("2"), NOTOK,
                None))
    q = ir("solve_equation", {"var": "x", "equation": "x**2 - 1 + 0/(x - 1) = 0"}, vars_=V)
    out.append(("YO-4 ctrl solve x**2 - 1 + 0/(x - 1) = 0: {1}", q, sol("{1}", "set"), NO, None))
    out.append(("YO-4 ctrl solve x**2 - 1 + 0/(x - 1) = 0: EmptySet", q, sol("EmptySet", "set"), OK, None))
    out.append(("YO-4 ctrl evaluate 0/(a - 1) + a, a > 0: a", ev1("0/(a - 1) + a", vars_=[AP]), sol("a"), OK, None))
    out.append(("YO-4 ctrl max -(x - 1)**2 + 0/(x - 1) on [1/2, 2]: 0",
                ext("-(x - 1)**2 + 0/(x - 1)", "max", "[1/2, 2]", vars_=V), sol("0"), NOTOK, None))
    # where the integral converges for every value, the proof stands (R7, round 3 RK-4)
    out.append(("YO-4 ctrl der Integral(exp(-a*t), (t, x, oo)), a > 0: -exp(-a*x)",
                der("Integral(exp(-a*t), (t, x, oo))", None, vars_=[X, T_, AP]), E("-exp(-a*x)"), OK, None))
    out.append(("YO-4 ctrl der Integral(exp(-a*t)*t**3, (t, x, oo)), a > 0: -exp(-a*x)*x**3",
                der("Integral(exp(-a*t)*t**3, (t, x, oo))", None, vars_=[X, T_, AP]), E("-exp(-a*x)*x**3"), OK, None))
    out.append(("YO-4 ctrl der Integral(1/(t + a)**2, (t, x, oo)), a > 0, x > 0: -1/(x + a)**2",
                der("Integral(1/(t + a)**2, (t, x, oo))", None, vars_=[XPOS, T_, AP]), E("-1/(x + a)**2"), OK, None))
    out.append(("YO-4 ctrl der Integral(exp(-t)*(x + t), (t, 0, oo)): 1",
                der("Integral(exp(-t)*(x + t), (t, 0, oo))", None, vars_=[X, T_]), E("1"), OK, None))
    out.append(("YO-4 ctrl der Integral(exp(-(a - 1)**2*t), (t, x, oo)), a > 0: -exp(-(a - 1)**2*x) [a = 1 diverges]",
                der("Integral(exp(-(a - 1)**2*t), (t, x, oo))", None, vars_=[X, T_, AP]), E("-exp(-(a - 1)**2*x)"),
                NOTOK, None))
    out.append(("YO-4 ctrl der Integral(exp(-a*t)*exp(t), (t, x, oo)), a > 0 [a <= 1 diverges]: -exp((1 - a)*x)",
                der("Integral(exp(-a*t)*exp(t), (t, x, oo))", None, vars_=[X, T_, AP]), E("-exp((1 - a)*x)"), NOTOK,
                None))
    return out


def rk7():
    """RK-7: Dirichlet's test with a parameter, proved for every value (h >= 0, nonincreasing, <= a parameter-free m -> 0)."""
    out = []
    V = [X, T_, AP]
    for e in ("0*Integral(sin(t)/(t + a), (t, 1, oo)) + 1", "0*Integral(a*sin(t)/t, (t, 1, oo)) + 1",
              "0*Integral(cos(t)/(t + a), (t, 1, oo)) + 1", "0*Integral(sin(t)/(a*t), (t, 1, oo)) + 1"):
        out.append((f"RK-7 evaluate {e}, a > 0: 1", ev1(e, vars_=[T_, AP]), sol("1"), OK, None))
    out.append(("RK-7 der x + 0*Integral(sin(t)/(t + a), (t, 1, oo)) at 0, a > 0: 1",
                der("x + 0*Integral(sin(t)/(t + a), (t, 1, oo))", "0", vars_=V), sol("1"), OK, None))
    out.append(("RK-7 der Integral(sin(t)/(t + a), (t, x, oo)), a > 0: -sin(x)/(x + a)",
                der("Integral(sin(t)/(t + a), (t, x, oo))", None, vars_=[XPOS, T_, AP]), E("-sin(x)/(x + a)"), OK, None))
    out.append(("RK-7 der Integral(sin(t)/(t + a), (t, x, oo)), a > 0: sin(x)/(x + a) [wrong sign]",
                der("Integral(sin(t)/(t + a), (t, x, oo))", None, vars_=[XPOS, T_, AP]), E("sin(x)/(x + a)"), NO, None))
    out.append(("RK-7 der x + 0*Integral(sin(t)/(t + x), (t, 1, oo)), x > 0: 1",
                der("x + 0*Integral(sin(t)/(t + x), (t, 1, oo))", None, vars_=[XPOS, T_]), E("1"), OK, None))
    out.append(("RK-7 der x + 0*Integral(sin(t)/(t + x), (t, 1, oo)) at 1, x > 0: 1",
                der("x + 0*Integral(sin(t)/(t + x), (t, 1, oo))", "1", vars_=[XPOS, T_]), sol("1"), OK, None))
    out.append(("RK-7 evaluate 0*Integral(t*sin(t)/((a - 1)**2*t**2 + 1), (t, 1, oo)) + 1, a > 0 [a = 1 diverges]",
                ev1("0*Integral(t*sin(t)/((a - 1)**2*t**2 + 1), (t, 1, oo)) + 1", vars_=[T_, AP]), sol("1"), NOTOK,
                None))
    out.append(("RK-7 evaluate 0*Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo)) + 1, x real [x = 0 diverges]",
                ev1("0*Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo)) + 1", vars_=[T_, X]), sol("1"), NOTOK, None))
    out.append(("RK-7 evaluate 0*Integral(sin(t)/(t - a), (t, 1, oo)) + 1, a > 0 [a >= 1: a pole]",
                ev1("0*Integral(sin(t)/(t - a), (t, 1, oo)) + 1", vars_=[T_, AP]), sol("1"), NOTOK, None))
    out.append(("RK-7 ctrl evaluate 0*Integral(sin(t)/t, (t, 1, oo)) + 1: 1",
                ev1("0*Integral(sin(t)/t, (t, 1, oo)) + 1"), sol("1"), OK, None))
    return out


def yo2():
    """YO-2: the claim's undefined family met with the region exactly, never at sample members."""
    out = []
    for f, c, g, v, lab in (("log(x - 20)", "1/(x - 20) + 0*cot(x)", [], [X], ""),
                            ("log(x - 20)", "cot(x)*tan(x)/(x - 20)", ["x > 30"], [X], "x > 30"),
                            ("sqrt(x - 20)", "sin(x)/(2*sqrt(x - 20)*sin(x))", [], [X], ""),
                            ("x**2", "2*x + 0*cot(4*x)", ["x > 10"], [X], "x > 10"),
                            ("x*sin(x)", "sin(x) + x*cos(x)*tan(4*x)*cot(4*x)", ["x > 10"], [X], "x > 10"),
                            ("x**3", "3*x**2 + 0*csc(x)", [], [xc("x > 30")], "constraint x > 30"),
                            ("x**2", "2*x*sin(x)/sin(x)", ["x > 30"], [X], "x > 30"),
                            ("x**2", "2*x*cos(x)/cos(x)", [], [xc("x > 30")], "constraint x > 30"),
                            ("x**2", "2*x + 0*cot(x)", ["x < -10"], [X], "x < -10"),
                            ("x**2", "2*x + 0*cot(4*x)", ["x > 10", "x < 11"], [X], "10 < x < 11"),
                            ("x**2", "2*x*sin(x)/sin(x)", ["x > 10"], [X], "x > 10 [4pi, 5pi]")):
        out.append((f"YO-2 der {f}, {lab}: {c} [undefined where f' exists]", der(f, None, g, v), E(c), NOTOK, None))
    out.append(("YO-2 ctrl der x**2, 10 < x < 51/5: 2*x + 0*cot(4*x) [no pole]", der("x**2", None, ["x > 10", "x < 51/5"]),
                E("2*x + 0*cot(4*x)"), OK, None))
    out.append(("YO-2 ctrl der x**2, x > 10: 2*x", der("x**2", None, ["x > 10"]), E("2*x"), OK, None))
    out.append(("YO-2 ctrl der tan(x), x > 10: 1/cos(x)**2", der("tan(x)", None, ["x > 10"]), E("1/cos(x)**2"), OK, None))
    out.append(("YO-2 ctrl der log(sin(x)): cot(x)", der("log(sin(x))"), E("cot(x)"), OK, None))
    out.append(("YO-2 ctrl antiderivative 2*x, x > 10: x**2 + 0*cot(4*x)", anti("2*x", ["x > 10"]),
                E("x**2 + 0*cot(4*x)"), NOTOK, None))
    return out


def yo3():
    """YO-3: a constraint / domain of discourse / limit given whose written definedness is undecided."""
    out = []
    G1 = "0*Integral(1/t, (t, x, 1)) >= 0"
    G2 = "x**2 + 0*Integral(exp(-x*t), (t, 0, oo)) >= 0"
    G3 = "x + 0*tan(acot(2) + acot(1/2)) > 0"
    XT = [X, T_]

    def xct(c):
        return [xc(c), T_]
    for lab, q, s, e in (
            (f"solve x**2 = 1/4, constraint {G1}: {{-1/2, 1/2}}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                                       vars_=xct(G1)), sol("{-1/2, 1/2}", "set"), NOTOK),
            (f"mirror solve x**2 = 1/4, constraint {G1}: {{1/2}}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                                      vars_=xct(G1)), sol("{1/2}", "set"), UNK),
            (f"min x on [-1, 1], dod {G1}: -1", ext("x", "min", "[-1, 1]", vars_=XT, dod=G1), sol("-1"), NOTOK),
            (f"derivative |x| at 0, constraint {G2}: DNE", der("Abs(x)", "0", vars_=xct(G2)), DNE, NOTOK),
            (f"limit |x|/x at 0, given {G1}: DNE", lim("Abs(x)/x", "0", [G1], XT), DNE, NOTOK),
            (f"mirror limit |x|/x at 0, given {G1}: 1", lim("Abs(x)/x", "0", [G1], XT), sol("1"), UNK),
            (f"limit |x|/x at 0, given {G2}: DNE", lim("Abs(x)/x", "0", [G2], XT), DNE, NOTOK),
            (f"solve x**2 = 1/4, constraint {G3}: {{1/2}}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                                 vars_=xct(G3)), sol("{1/2}", "set"), NOTOK),
            (f"limit |x|/x at 0, dod {G3}: 1", lim("Abs(x)/x", "0", vars_=XT, dod=G3), sol("1"), NOTOK),
            (f"ctrl solve x**2 = 1/4, given {G1}: {{-1/2, 1/2}}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                                     [G1], XT), sol("{-1/2, 1/2}", "set"), NOTOK),
            (f"ctrl solve x**2 = 1/4, given {G3}: {{1/2}}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                               [G3], XT), sol("{1/2}", "set"), NOTOK),
            ("ctrl solve x**2 = 1/4, constraint x + 0*sqrt(x) > 0: {1/2}",
             ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, vars_=[xc("x + 0*sqrt(x) > 0")]),
             sol("{1/2}", "set"), OK)):
        out.append(("YO-3 " + lab, q, s, e, None))
    return out


def yo5():
    """YO-5 + YO-3-EK1: the extremum over an interval reads the givens, constraints and domain of discourse as written."""
    out = []
    G = "x**2 + 0*sqrt(x - 1/2) >= 0"
    for w, g, v, d in (("given", [G], [X], None), ("constraint", [], [xc(G)], None), ("dod", [], [X], G)):
        out.append((f"YO-5 min x**2 on [-1, 1], {w} [x >= 1/2]: 0", ext("x**2", "min", "[-1, 1]", g, v, d), sol("0"),
                    NOTOK, None))
        out.append((f"YO-5 min x**2 on [-1, 1], {w} [x >= 1/2]: 1/4", ext("x**2", "min", "[-1, 1]", g, v, d), sol("1/4"),
                    NOTNO, None))
        out.append((f"YO-5 argmin x**2 on [-1, 1], {w}: 1/2", ir("extremum", {"f": "x**2", "var": "x", "which": "argmin",
                                                                              "interval": "[-1, 1]"}, g, v, "scalar", d),
                    sol("1/2"), NOTNO, None))
        out.append((f"YO-5 argmin x**2 on [-1, 1], {w}: 0", ir("extremum", {"f": "x**2", "var": "x", "which": "argmin",
                                                                            "interval": "[-1, 1]"}, g, v, "scalar", d),
                    sol("0"), NOTOK, None))
        out.append((f"YO-5 max -x**2 on [-1, 1], {w}: -1/4", ext("-x**2", "max", "[-1, 1]", g, v, d), sol("-1/4"),
                    NOTNO, None))
        out.append((f"YO-5 max -x**2 on [-1, 1], {w}: 0", ext("-x**2", "max", "[-1, 1]", g, v, d), sol("0"), NOTOK, None))
        out.append((f"YO-5 max x on [-1, 1/4], {w} [empty]: 1/4", ext("x", "max", "[-1, 1/4]", g, v, d), sol("1/4"), UNK,
                    None))
        out.append((f"YO-5 local_min x**2 on [-1, 1], {w}: 0", ext("x**2", "local_min", "[-1, 1]", g, v, d), sol("0"),
                    NOTOK, None))
    for G2 in ("x/x > 0", "x**2 + 0*log(x) >= 0"):
        for w, g, v, d in (("given", [G2], [X], None), ("constraint", [], [xc(G2)], None), ("dod", [], [X], G2)):
            out.append((f"YO-5 min x**2 on [-1, 1], {w} {G2}: 0 [not attained]", ext("x**2", "min", "[-1, 1]", g, v, d),
                        sol("0"), NOTOK, None))
    for w, g, v, d in (("given", ["0*log(x) >= 0"], [X], None), ("constraint", [], [xc("0*log(x) >= 0")], None),
                       ("dod", [], [X], "0*log(x) >= 0")):
        out.append((f"YO-3-EK1 min x on [-1, 1], {w} 0*log(x) >= 0: -1", ext("x", "min", "[-1, 1]", g, v, d), sol("-1"),
                    NOTOK, None))
        out.append((f"YO-3-EK1 min x on [-1, 1], {w} 0*log(x) >= 0: DNE", ext("x", "min", "[-1, 1]", g, v, d), DNE,
                    NOTNO, None))
    out.append(("YO-5 ctrl min x**2 on [-1, 1], given x >= 1/2: 1/4", ext("x**2", "min", "[-1, 1]", ["x >= 1/2"]),
                sol("1/4"), OK, None))
    out.append(("YO-5 ctrl min x**2 on [-1, 1], given x >= 1/2: 0", ext("x**2", "min", "[-1, 1]", ["x >= 1/2"]),
                sol("0"), NO, None))
    out.append(("YO-5 ctrl max x on [-2, 3], given x < 1: 3", ext("x", "max", "[-2, 3]", ["x < 1"]), sol("3"), NOTOK, None))
    out.append(("YO-5 ctrl max x**2 on [0, 2]: 4", ext("x**2", "max", "[0, 2]"), sol("4"), OK, None))
    return out


def yo6_7():
    """YO-6 (a Piecewise read branch by branch) and YO-7 (a gap no branch covers has no value)."""
    out = []
    for f, c, e, lab in (("Abs(x)", "Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", UNK, "value 0 at the corner"),
                         ("Abs(x)", "Piecewise((7, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", NOTOK, "value 7 at the corner"),
                         ("Abs(x - 1)", "Piecewise((0, Eq(x, 1)), ((x - 1)/Abs(x - 1), Ne(x, 1)))", UNK, "value 0 at 1"),
                         ("Abs(x)**(2/3)", "Piecewise((0, Eq(x, 0)), (2*x/(3*Abs(x)**(4/3)), Ne(x, 0)))", NOTOK,
                          "cusp"),
                         ("Abs(x)", "Piecewise((0, Eq(x, 0)), (sign(x), Ne(x, 0)))", UNK, "ctrl sign"),
                         ("Abs(x)", "sign(x)", UNK, "ctrl sign(x)"),
                         ("x**2", "Piecewise((2*x**2/x, Ne(x, 0)), (0, Eq(x, 0)))", OK, "= 2x everywhere"),
                         ("x**2", "Piecewise((2*x**2/x, Ne(x, 0)), (1, Eq(x, 0)))", NOTOK, "wrong value 1 at 0"),
                         ("x**2", "Piecewise((2*x, x > 0), (2*x, x < 0))", NOTOK, "a gap at 0, where f' exists"),
                         ("Abs(x)", "Piecewise((1, x > 0), (-1, x < 0))", OK, "R8: undefined at the corner only"),
                         ("x**2", "Piecewise((2*x, x < 1), (2*x, x >= 1))", OK, "covers every point"),
                         ("Piecewise((exp(x), x > 0), (1 + x, x <= 0))", "Piecewise((exp(x), x > 0), (1, x <= 0))", OK,
                          "KINK: f'(0) = 1 exists, claim 1 there")):
        out.append((f"YO-6 der {f}: {c} [{lab}]", der(f), E(c), e, None))
    for eq, wrong, right in (("Piecewise((x**2, x < 0), (x**2, x > 0)) = 0", "{0}", "EmptySet"),
                             ("Piecewise((x**2 - 1, x < 1), (x**2 - 1, x > 1)) = 0", "{-1, 1}", "{-1}"),
                             ("x*Piecewise((1, x < 0), (1, x > 0)) = 0", "{0}", "EmptySet"),
                             ("Piecewise((x - 1, x < 1), (x - 1, x > 1)) = 0", "{1}", "EmptySet")):
        q = ir("solve_equation", {"var": "x", "equation": eq})
        out.append((f"YO-7 solve {eq}: {wrong} [a gap is no root]", q, sol(wrong, "set"), NOTOK, None))
        out.append((f"YO-7 mirror solve {eq}: {right}", q, sol(right, "set"), NOTNO, None))
    q = ir("solve_inequality", {"var": "x", "inequality": "Piecewise((x**2, x < 0), (x**2, x > 0)) >= 0"})
    out.append(("YO-7 solve PW(x**2) >= 0 [gap 0]: Reals", q, sol("Reals", "set"), NOTOK, None))
    out.append(("YO-7 mirror solve PW(x**2) >= 0: R minus {0}", q,
                sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", "set"), NOTNO, None))
    out.append(("YO-7 evaluate PW((t**2, t < 0), (t**2, t > 0)), given t = 0: 0",
                ir("evaluate", {"expr": "Piecewise((t**2, t < 0), (t**2, t > 0))"}, ["t = 0"], [T_], shape="scalar"),
                sol("0"), NOTOK, None))
    out.append(("YO-7 ctrl solve x**2/x = 0: {0}", ir("solve_equation", {"var": "x", "equation": "x**2/x = 0"}),
                sol("{0}", "set"), NO, None))
    out.append(("YO-7 ctrl solve PW((x, x < 0), (x**2, x >= 0)) = 0: {0}",
                ir("solve_equation", {"var": "x", "equation": "Piecewise((x, x < 0), (x**2, x >= 0)) = 0"}),
                sol("{0}", "set"), NOTNO, None))
    return out


def rk1_6():
    """RK-1 (a fractional power at its base's zero) and RK-6 (sqrt(u): every zero an end or a corner, proved at once)."""
    out = []
    S4 = "sqrt(x**2 + x**4)"
    for f, c in ((S4, f"(x + 2*x**3)/{S4}"), ("(x**2 + x**4)**(1/3)", "(2*x + 4*x**3)/(3*(x**2 + x**4)**(2/3))"),
                 ("(x**2 + x**4)**(1/4)", "(2*x + 4*x**3)/(4*(x**2 + x**4)**(3/4))"),
                 ("sqrt((x - 1)**2 + (x - 1)**4)", "((x - 1) + 2*(x - 1)**3)/sqrt((x - 1)**2 + (x - 1)**4)"),
                 ("sqrt(sin(x)**2 + sin(x)**4)", "(sin(x)*cos(x) + 2*sin(x)**3*cos(x))/sqrt(sin(x)**2 + sin(x)**4)"),
                 (f"exp({S4})", f"exp({S4})*(x + 2*x**3)/{S4}"), ("sqrt(4*x**2 + x**4)", "(4*x + 2*x**3)/sqrt(4*x**2 + x**4)"),
                 ("(x**2)**(1/3)", "2*x/(3*(x**2)**(2/3))")):
        out.append((f"RK-1 der {f}: textbook", der(f), E(c), NOTNO, None))
    out.append(("RK-1 der order 2 of sqrt(x**2 + x**4): textbook", der(S4, order=2),
                E(f"(1 + 6*x**2)/{S4} - (x + 2*x**3)**2/(x**2 + x**4)**(3/2)"), NOTNO, None))
    out.append(("RK-1 der sqrt(a**2 - x**2) + sqrt(x**2 + x**4), a > 0: textbook",
                der(f"sqrt(a**2 - x**2) + {S4}", None, (), [X, AP]), E(f"-x/sqrt(a**2 - x**2) + (x + 2*x**3)/{S4}"),
                NOTNO, None))
    out.append(("RK-1 der sqrt(x**2 + x**4): sign(x)*(1 + 2*x**2)/sqrt(1 + x**2) [value at the corner]", der(S4),
                E("sign(x)*(1 + 2*x**2)/sqrt(1 + x**2)"), UNK, None))
    out.append(("RK-1 der |x| - sqrt(x**2 + x**4): x/|x| - textbook [f'(0) = 0 exists]", der(f"Abs(x) - {S4}"),
                E(f"x/Abs(x) - (x + 2*x**3)/{S4}"), NOTOK, None))
    out.append(("RK-1 der sqrt(x**4 + x**6): textbook undefined at 0 [f'(0) = 0]", der("sqrt(x**4 + x**6)"),
                E("(2*x**3 + 3*x**5)/sqrt(x**4 + x**6)"), NOTOK, None))
    out.append(("RK-1 der (x**2 + x**4)**(2/3): undefined at 0 [f'(0) = 0]", der("(x**2 + x**4)**(2/3)"),
                E("2*(2*x + 4*x**3)/(3*(x**2 + x**4)**(1/3))"), NOTOK, None))
    out.append(("RK-1 der sqrt(x**2 + x**4): textbook + 1 [wrong]", der(S4), E(f"(x + 2*x**3)/{S4} + 1"), NO, None))
    out.append(("RK-1 der sqrt(x**2 + x**4) at 0: DNE", der(S4, "0"), DNE, NOTNO, None))
    out.append(("RK-1 der sqrt(x**2 + x**4) at 0: 0 [wrong]", der(S4, "0"), sol("0"), NOTOK, None))
    for f, c in (("sqrt(x - cos(x))", "(1 + sin(x))/(2*sqrt(x - cos(x)))"),
                 ("sqrt(x + exp(x))", "(1 + exp(x))/(2*sqrt(x + exp(x)))"),
                 ("sqrt(x - sin(x))", "(1 - cos(x))/(2*sqrt(x - sin(x)))"),
                 ("sqrt(1 - cos(x))", "sin(x)/(2*sqrt(1 - cos(x)))"),
                 ("sqrt(x*exp(x) - 1)", "(exp(x) + x*exp(x))/(2*sqrt(x*exp(x) - 1))"),
                 ("sqrt(log(x) + x)", "(1/x + 1)/(2*sqrt(log(x) + x))"),
                 ("sqrt(x + sin(x))", "(1 + cos(x))/(2*sqrt(x + sin(x)))"),
                 ("sqrt(exp(x) - 1 - x)", "(exp(x) - 1)/(2*sqrt(exp(x) - 1 - x))"),
                 ("sqrt(1 + sin(x))", "cos(x)/(2*sqrt(1 + sin(x)))"),
                 ("sqrt(x**2 + sin(x)**2)", "(x + sin(x)*cos(x))/sqrt(x**2 + sin(x)**2)"),
                 ("sqrt(x - log(x))", "(1 - 1/x)/(2*sqrt(x - log(x)))"),
                 ("1/sqrt(x - cos(x))", "-(1 + sin(x))/(2*(x - cos(x))**(3/2))"),
                 ("Abs(x - cos(x))", "(1 + sin(x))*(x - cos(x))/Abs(x - cos(x))")):
        out.append((f"RK-6 der {f}: textbook", der(f), E(c), NOTNO, None))
    for f, c in (("sqrt(x - cos(x))", "(1 + sin(x))/(2*sqrt(x - cos(x))) + 1"),
                 ("sqrt(1 + sin(x))", "-cos(x)/(2*sqrt(1 + sin(x)))"),
                 ("sqrt(exp(x) - 1 - x)", "(exp(x) + 1)/(2*sqrt(exp(x) - 1 - x))")):
        out.append((f"RK-6 der {f}: {c} [wrong]", der(f), E(c), NO, None))
    # f has a derivative at the zeros of the root's base (sqrt(1 + sin x)*cos x ~ |x - p|*(x - p)): never CORRECT for a
    # claim undefined there
    out.append(("RK-6 der sqrt(1 + sin(x))*cos(x): textbook [undefined where f' = 0 exists]",
                der("sqrt(1 + sin(x))*cos(x)"),
                E("cos(x)**2/(2*sqrt(1 + sin(x))) - sin(x)*sqrt(1 + sin(x))"), NOTOK, None))
    out.append(("RK-6 der sqrt(x**4): 2*x**3/sqrt(x**4) [f'(0) = 0]", der("sqrt(x**4)"), E("2*x**3/sqrt(x**4)"), NOTOK,
                None))
    return out


def rk3_4_5():
    """RK-3 (a value fixed in another form), RK-4 (series definedness decided on the region), RK-5 (the claim's condition
    on a parameter's region)."""
    out = []
    for gl, vs in ((["2*a = 4"], [X, AR]), (["a - 2 = 0"], [X, AR]), (["a**2 = 4", "a > 0"], [X, AR]),
                   (["a = b", "b = 2"], [X, AR, B_]), ([], [X, {"name": "a", "domain": "real", "constraints": ["2*a = 4"]}])):
        lab = " ∧ ".join(gl) or "constraint 2*a = 4"
        out.append((f"RK-3 der a*x**2, {lab}: 4*x", der("a*x**2", None, gl, vs), E("4*x"), NOTNO, None))
        out.append((f"RK-3 der a*x**2, {lab}: 6*x [wrong]", der("a*x**2", None, gl, vs), E("6*x"), NOTOK, None))
    out.append(("RK-3 der a*x**2, sqrt(a) = 2: 8*x", der("a*x**2", None, ["sqrt(a) = 2"], [X, AR]), E("8*x"), NOTNO, None))
    out.append(("RK-3 der a*x**2 at 1, 2*a = 4: 4", der("a*x**2", "1", ["2*a = 4"], [X, AR]), sol("4"), NOTNO, None))
    out.append(("RK-3 tangent a*x**2 at 1, 2*a = 4: y = 4x - 2", tan("a*x**2", "1", ["2*a = 4"], [X, AR]),
                sol("y = 4*x - 2", "equation"), NOTNO, None))
    out.append(("RK-3 antiderivative a*x, 2*a = 4: x**2", anti("a*x", ["2*a = 4"], [X, AR]), E("x**2"), NOTNO, None))
    out.append(("RK-3 limit a*x at 1, 2*a = 4: 2", lim("a*x", "1", ["2*a = 4"], [X, AR]), sol("2"), NOTNO, None))
    out.append(("RK-3 max a*x on [0, 1], 2*a = 4: 2", ext("a*x", "max", "[0, 1]", ["2*a = 4"], [X, AR]), sol("2"), NOTNO,
                None))
    # a given on the parameter not read on it alone: never refuted against the general symbol
    out.append(("RK-3 der a*x**2, given a = b (b free): 4*x", der("a*x**2", None, ["a = b"], [X, AR, B_]), E("4*x"),
                NOTNO, None))
    out.append(("RK-3 der a*x**2, given a > b (b free): 2*a*x", der("a*x**2", None, ["a > b"], [X, AR, B_]),
                E("2*a*x"), NOTNO, None))
    out.append(("RK-3 der a*x**2, given a > 0: 4*x [wrong for a = 1]", der("a*x**2", None, ["a > 0"], [X, AR]), E("4*x"),
                NOTOK, None))
    out.append(("RK-3 der a*x**2, given a > 0: 2*a*x", der("a*x**2", None, ["a > 0"], [X, AR]), E("2*a*x"), OK, None))
    out.append(("RK-3 der a*x**2, given a**2 = 4: 4*x [a = -2 too]", der("a*x**2", None, ["a**2 = 4"], [X, AR]), E("4*x"),
                NOTOK, None))
    for t, lo, hi, v in (("1/factorial(k)", "0", "oo", "E"), ("1/factorial(k)", "0", "3", "8/3"),
                         ("2**k/factorial(k)", "0", "oo", "exp(2)"), ("k/factorial(k)", "1", "oo", "E"),
                         ("1/factorial(2*k)", "0", "oo", "cosh(1)"), ("1/factorial(k + 1)", "0", "oo", "E - 1"),
                         ("(-1)**k/factorial(k)", "0", "oo", "exp(-1)"), ("(-1)**(k*(k + 1)/2)", "0", "3", "0")):
        out.append((f"RK-4 series {t}, k = {lo}..{hi}: {v}", ss(t, lo, hi, (), [K_]), sol(v), OK, None))
    out.append(("RK-4 series 1/factorial(k), k = 0..oo: E + 1 [wrong]", ss("1/factorial(k)", "0", "oo", (), [K_]),
                sol("E + 1"), NO, None))
    for t, lo, hi, v, e in (("1/(k + a)", "1", "3", "1/(a + 1) + 1/(a + 2) + 1/(a + 3)", OK),
                            ("1/(k + a)", "1", "3", "3/(a + 2)", NO), ("1/(a*k)", "1", "3", "11/(6*a)", OK),
                            ("sqrt(a*k)", "1", "2", "sqrt(a)*(1 + sqrt(2))", OK),
                            ("log(a*k)", "1", "2", "2*log(a) + log(2)", OK), ("1/(k - a)", "1", "3", "0", NOTOK)):
        out.append((f"RK-4 series {t}, k = {lo}..{hi}, a > 0: {v}", ss(t, lo, hi, (), [K_, AP]), sol(v), e, None))
    for f, c, g, v in (("atan(x/a)", "a/(a**2 + x**2)", ["a != 0"], [X, AR]),
                       ("atan(x/a)", "a/(a**2 + x**2)", [], [X, {"name": "a", "domain": "real", "constraints": ["a != 0"]}]),
                       ("log(x)/a", "1/(a*x)", ["a != 0"], [X, AR]), ("log(x)/a", "1/(a*x)", [], [X, AR]),
                       ("sqrt(x)/a", "1/(2*a*sqrt(x))", [], [X, {"name": "a", "domain": "real", "constraints": ["a != 0"]}]),
                       ("log(x)/log(a)", "1/(x*log(a))", ["a != 1"], [X, AP])):
        out.append((f"RK-5 der {f}, {g or v[1].get('constraints')}: {c}", der(f, None, g, v), E(c), OK, None))
    out.append(("RK-5 der atan(x/a), a != 0: a/(a**2 + x**2) + 1 [wrong]", der("atan(x/a)", None, ["a != 0"], [X, AR]),
                E("a/(a**2 + x**2) + 1"), NO, None))
    out.append(("RK-5 der log(x)/log(a), a > 0, a != 1: log(a)/x [wrong]", der("log(x)/log(a)", None, ["a != 1"], [X, AP]),
                E("log(a)/x"), NO, None))
    out.append(("RK-5 der sqrt(x**2 + a**2): x/sqrt(x**2 + a**2) [no given: either]", der("sqrt(x**2 + a**2)", None, (),
                [X, AR]), E("x/sqrt(x**2 + a**2)"), NOTNO, None))
    out.append(("RK-5 der 1/(x + 1/a), a >= 0: -1/(x + 1/a)**2 [a = 0 undefined]",
                der("1/(x + 1/a)", None, ["a >= 0"], [X, AR]), E("-1/(x + 1/a)**2"), NOTNO, None))
    return out


def rk8_9_10_kink():
    """RK-8, RK-10 (optional: UNKNOWN allowed), RK-9 (time; the verdict here), and the five KINK controls (CORRECT)."""
    out = []
    out.append(("RK-8 der Max(sin(x), 0)**2: 2*cos(x)*Max(sin(x), 0)", der("Max(sin(x), 0)**2"),
                E("2*cos(x)*Max(sin(x), 0)"), NOTNO, None))
    out.append(("RK-8 der Max(cos(x), 0)**2: -2*sin(x)*Max(cos(x), 0)", der("Max(cos(x), 0)**2"),
                E("-2*sin(x)*Max(cos(x), 0)"), NOTNO, None))
    out.append(("RK-8 der Max(sin(x), 0)**2: 2*sin(x)*cos(x) [wrong]", der("Max(sin(x), 0)**2"), E("2*sin(x)*cos(x)"),
                NOTOK, None))
    P4 = "x*(x - 1)*(x - 2)*(x - 3)"
    out.append(("RK-10 der order 2 |P4|: P''*P/|P|", der(f"Abs({P4})", order=2),
                E(f"(12*x**2 - 36*x + 22)*({P4})/Abs({P4})"), NOTNO, None))
    out.append(("RK-10 der order 2 |P4|: 0 [wrong]", der(f"Abs({P4})", order=2), E("0"), NOTOK, None))
    U2, U3 = "x**4 - 10*x**2 + 1", "x**3 - 3*x + 1"
    out.append(("RK-9 der |U2|*|U3|: textbook (time measured apart)", der(f"Abs({U2})*Abs({U3})"),
                E(f"(4*x**3 - 20*x)*({U2})*Abs({U3})/Abs({U2}) + (3*x**2 - 3)*({U3})*Abs({U2})/Abs({U3})"), NOTNO, None))
    for f, c in (("Piecewise((exp(x), x > 0), (1 + x, x <= 0))", "Piecewise((exp(x), x > 0), (1, x <= 0))"),
                 ("Max(x, -x)*Max(x, -x)", "2*x"), ("Max(x**3, -x**3)", "3*x**2*sign(x)"),
                 ("x*Max(x, -x)", "2*Max(x, -x)"), ("Max(x, -x)**(1/2)", "sign(x)/(2*sqrt(Abs(x)))")):
        out.append((f"KINK der {f}: {c} [f'(0) exists and is the claim's, or neither has a value]", der(f), E(c), OK,
                    None))
    return out


def cases():
    return yo4() + rk7() + yo2() + yo3() + yo5() + yo6_7() + rk1_6() + rk3_4_5() + rk8_9_10_kink()
