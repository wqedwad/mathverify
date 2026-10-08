import sys
from ortak import *

DIR = "Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo))"      # converges iff x != 0 (Dirichlet), diverges at x = 0
XT = [X, T_]


def cases():
    out = []
    # 1) Dirichlet test with the task variable in the integrand (round 3 RK-4 lifted _integrand_on's sign check)
    out.append(("DIR derivative x + 0*I(x) at 0: 1 [f undefined at 0]", der(f"x + 0*{DIR}", "0", [], XT), sol("1"), NOTOK, None))
    out.append(("DIR tangent x + 0*I(x) at 0: y = x [f undefined at 0]", tan(f"x + 0*{DIR}", "0", [], XT),
                sol("y = x", "equation"), NOTOK, None))
    out.append(("DIR min x**2 + 0*I(x) on [-1, 1]: 0 [not attained]", ext(f"x**2 + 0*{DIR}", "min", "[-1, 1]", [], XT),
                sol("0"), NOTOK, None))
    q = ir("solve_equation", {"var": "x", "equation": f"x**2 + 0*{DIR} = 0"}, [], XT)
    out.append(("DIR solve x**2 + 0*I(x) = 0: {0} [0 outside the domain]", q, sol("{0}", "set"), NOTOK, None))
    q = ir("evaluate", {"expr": f"x + 1 + 0*{DIR}"}, ["x = 0"], XT, shape="scalar")
    out.append(("DIR evaluate x + 1 + 0*I(x), x = 0: 1 [undefined]", q, sol("1"), NOTOK, None))
    q = ir("evaluate", {"expr": "0*Integral(t*sin(t)/(a**2*t**2 + 1), (t, 1, oo)) + 1"}, [], [A_, T_], shape="scalar")
    out.append(("DIR evaluate 0*I(a) + 1, a real free: 1 [undefined at a = 0]", q, sol("1"), NOTOK, None))
    out.append(("DIR derivative x + 0*I(x): 1 (expr)", der(f"x + 0*{DIR}", None, [], XT), sol("1", "expression"), NOTNO, None))
    out.append(("DIR derivative x**2 + 0*I(x) at 0: 0 [undefined]", der(f"x**2 + 0*{DIR}", "0", [], XT), sol("0"), NOTOK, None))
    # 2) the claim's undefined family checked at n = 0, 1, -1, 2 only
    for g, v, d, w in ((["x > 10"], [X], None, "given"), ([], [xc("x > 10")], None, "constraint"), ([], [X], "x > 10", "dod")):
        out.append((f"FAM derivative x**2, {w} x > 10: 2*x*sin(x)/sin(x) [undefined at 4pi]", der("x**2", None, g, v, d),
                    sol("2*x*sin(x)/sin(x)", "expression"), NOTOK, None))
        out.append((f"FAM derivative x**2, {w} x > 10: 2*x + 0*cot(x) [undefined at 4pi]", der("x**2", None, g, v, d),
                    sol("2*x + 0*cot(x)", "expression"), NOTOK, None))
        out.append((f"FAM derivative x**2, {w} x > 10: 2*x + 0*tan(x) [undefined at 7pi/2]", der("x**2", None, g, v, d),
                    sol("2*x + 0*tan(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative log(x - 20): 1/(x - 20) + 0*cot(x) [undefined at 7pi]", der("log(x - 20)"),
                sol("1/(x - 20) + 0*cot(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative sqrt(x - 20): 1/(2*sqrt(x - 20))*sin(x)/sin(x)", der("sqrt(x - 20)"),
                sol("sin(x)/(2*sqrt(x - 20)*sin(x))", "expression"), NOTOK, None))
    out.append(("FAM ctrl derivative x**2: 2*x*sin(x)/sin(x) [undefined at 0]", der("x**2"),
                sol("2*x*sin(x)/sin(x)", "expression"), NOTOK, None))
    out.append(("FAM ctrl derivative x**2, given x > 10: 2*x", der("x**2", None, ["x > 10"]), sol("2*x", "expression"), OK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
