import sys
from ortak import *

XT = [X, T_]
AN = {"name": "a", "domain": "nonneg_real"}


def cases():
    out = []
    # Dirichlet test with a symbol of undeclared (or half-declared) sign
    out.append(("DIR series k + 0*I(k), k=-1..1: 0 [term undefined at k = 0]",
                ss("k + 0*Integral(t*sin(t)/(k**2*t**2 + 1), (t, 1, oo))", -1, 1, [], [K_, T_]), sol("0"), NOTOK, None))
    q = ir("evaluate", {"expr": "0*Integral(t*sin(t)/(a*t**2 + 1), (t, 1, oo)) + 1"}, [], [AN, T_], shape="scalar")
    out.append(("DIR evaluate 0*I(a) + 1, a >= 0 declared: 1 [undefined at a = 0]", q, sol("1"), NOTOK, None))
    q = ir("evaluate", {"expr": "0*Integral(t*sin(t)/(a*t**2 + 1), (t, 1, oo)) + 1"}, ["a >= 0"], [A_, T_], shape="scalar")
    out.append(("DIR evaluate 0*I(a) + 1, given a >= 0: 1 [undefined at a = 0]", q, sol("1"), NOTOK, None))
    D2 = "Integral(t*cos(t)/(x**2*t**2 + 1), (t, -oo, -1))"
    out.append(("DIR derivative x + 0*I2(x) at 0 [-oo end]: 1", der(f"x + 0*{D2}", "0", [], XT), sol("1"), NOTOK, None))
    D3 = "Integral(sin(2*t + 1)*t**3/(x**4*t**4 + 1), (t, 0, oo))"
    out.append(("DIR derivative x**2 + 0*I3(x) at 0: 0", der(f"x**2 + 0*{D3}", "0", [], XT), sol("0"), NOTOK, None))
    D4 = "Integral(sin(t)*(x**2*t + 1)/(x**2*t**2 + 1), (t, 1, oo))"
    out.append(("DIR max -x**2 + 0*I4(x) on [-1, 1]: 0 [not attained]", ext(f"-x**2 + 0*{D4}", "max", "[-1, 1]", [], XT),
                sol("0"), NOTOK, None))
    D5 = "Integral(sin(t)*t/((x - 1)**2*t**2 + 1), (t, 1, oo))"
    out.append(("DIR derivative x**3 + 0*I5(x) at 1: 3 [undefined at 1]", der(f"x**3 + 0*{D5}", "1", [], XT), sol("3"),
                NOTOK, None))
    out.append(("DIR tangent x**3 + 0*I5(x) at 1: y = 3*x - 2", tan(f"x**3 + 0*{D5}", "1", [], XT),
                sol("y = 3*x - 2", "equation"), NOTOK, None))
    q = ir("solve_equation", {"var": "x", "equation": f"x**2 - 1 + 0*{D5} = 0"}, [], XT)
    out.append(("DIR solve x**2 - 1 + 0*I5(x) = 0: {-1, 1} [1 undefined]", q, sol("{-1, 1}", "set"), NOTOK, None))
    q = ir("solve_inequality", {"var": "x", "inequality": f"x**2 + 0*{D5} <= 1"}, [], XT)
    out.append(("DIR solve x**2 + 0*I5(x) <= 1: [-1, 1] [1 undefined]", q, sol("Interval(-1, 1)", "interval"), NOTOK, None))
    # controls: convergent for every x
    out.append(("DIR ctrl derivative x + 0*Integral(sin(t)/t, (t, 1, oo)) at 0: 1",
                der("x + 0*Integral(sin(t)/t, (t, 1, oo))", "0", [], XT), sol("1"), NOTNO, None))
    # series pins
    for label, g in (("a + 0*sqrt(a - 3) = 2", ["a + 0*sqrt(a - 3) = 2"]), ("a*sqrt(a - 3)/sqrt(a - 3) = 2", ["a*sqrt(a - 3)/sqrt(a - 3) = 2"]),
                     ("sqrt(a - 3)**2 = -1", ["sqrt(a - 3)**2 = -1"])):
        out.append((f"PIN series a*k, k=1..3, given {label}: 6*a value [no a as written]", ss("a*k", 1, 3, g),
                    sol("12" if "= 2" in label else "-6"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a**2 = 4: 3", ss("(k - a)/(k - a)", 1, 3, ["a**2 = 4"]), sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a = b: 3", ss("(k - a)/(k - a)", 1, 3, ["a = b"],
                                                                      [K_, A_, {"name": "b", "domain": "real"}]), sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a**2 = 4, a > -3: 3", ss("(k - a)/(k - a)", 1, 3, ["a**2 = 4", "a > -3"]),
                sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a**2 = 4, a**3 > -9: 3", ss("(k - a)/(k - a)", 1, 3, ["a**2 = 4", "a**3 > -9"]),
                sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, abs(a) = 2: 3", ss("(k - a)/(k - a)", 1, 3, ["abs(a) = 2"]),
                sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, floor(a) = 2: 3", ss("(k - a)/(k - a)", 1, 3, ["floor(a) = 2"]),
                sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a**2 <= 4, a >= 2: 3 [a = 2]", ss("(k - a)/(k - a)", 1, 3, ["a**2 <= 4", "a >= 2"]),
                sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a*(a - 2) = 0, a > -1, a != 0: 3",
                ss("(k - a)/(k - a)", 1, 3, ["a*(a - 2) = 0", "a > -1", "a != 0"]), sol("3"), NOTOK, None))
    AI = {"name": "a", "domain": "positive_integer"}
    out.append(("PIN series (k - a)/(k - a), k=1..3, a positive integer, a**2 < 5, a > 1: 3",
                ss("(k - a)/(k - a)", 1, 3, ["a**2 < 5", "a > 1"], [K_, AI]), sol("3"), NOTOK, None))
    out.append(("PIN series (k - a)/(k - a), k=1..3, a positive integer, a < 3, a > 1: 3",
                ss("(k - a)/(k - a)", 1, 3, ["a < 3", "a > 1"], [K_, AI]), sol("3"), NOTOK, None))
    out.append(("PIN series 1/(k - a), k=1..3, given 2*a = 3: -2/... ", ss("1/(k - a)", 1, 3, ["2*a = 3"]), sol("-2/3"), NOTOK, None))
    # functions: a constraint calling f
    F = [{"name": "f", "args": ["x"], "expr": "x + 0*sqrt(x - 1)"}]
    q = ir("limit", {"expr": "Abs(x - 1)/(x - 1)", "var": "x", "to": "1"}, ["f(x) > 0"], [X], shape="scalar", functions=F)
    out.append(("FN limit |x-1|/(x-1) at 1, given f(x) > 0, f = x + 0*sqrt(x - 1): DNE [x >= 1]", q, DNE, NOTOK, None))
    q = ir("limit", {"expr": "Abs(x - 1)/(x - 1)", "var": "x", "to": "1"}, [], [xc("f(x) > 0")], shape="scalar", functions=F)
    out.append(("FN limit |x-1|/(x-1) at 1, constraint f(x) > 0: DNE [x >= 1]", q, DNE, NOTOK, None))
    q = ir("limit", {"expr": "Abs(x - 1)/(x - 1)", "var": "x", "to": "1"}, [], [X], shape="scalar", functions=F, dod="f(x) > 0")
    out.append(("FN limit |x-1|/(x-1) at 1, dod f(x) > 0: DNE [x >= 1]", q, DNE, NOTOK, None))
    q = ir("limit", {"expr": "Abs(x - 1)/(x - 1)", "var": "x", "to": "1"}, ["y = sqrt(x - 1)"], [X, Y], shape="scalar")
    out.append(("FN limit |x-1|/(x-1) at 1, given y = sqrt(x - 1): DNE [x >= 1]", q, DNE, NOTOK, None))
    q = ir("limit", {"expr": "Abs(x - 1)/(x - 1)", "var": "x", "to": "1"}, ["log(x - 1) - log(x - 1) = 0"], [X], shape="scalar")
    out.append(("FN limit |x-1|/(x-1) at 1, given log(x-1) - log(x-1) = 0: DNE [x > 1]", q, DNE, NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
