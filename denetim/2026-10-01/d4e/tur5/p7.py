"""p7: Piecewise gaps that are intervals or families (Contains(x, D)) in every task kind."""
import sys
from ortak import *

GI = "Piecewise((x**2, x < 0), (x**2, x > 1))"              # gap [0, 1]
GP = "Piecewise((x, sin(x) > 0), (x, sin(x) < 0))"          # gap at n*pi


def solve(eq, vars_=None):
    return ir("solve_equation", {"var": "x", "equation": eq}, vars_=vars_)


def ineq(s, vars_=None):
    return ir("solve_inequality", {"var": "x", "inequality": s}, vars_=vars_)


def cases():
    out = []
    out.append(("der GI at 1/2: 1", der(GI, "1/2"), sol("1"), NOTOK, None))
    out.append(("tan GI at 1/2: y = x - 1/4", tan(GI, "1/2"), sol("y = x - 1/4", "equation"), NOTOK, None))
    out.append(("ext min GI on [-1,2]: 0", ext(GI, "min", "[-1, 2]"), sol("0"), NOTOK, None))
    out.append(("ext min GI on [-1,2]: 1", ext(GI, "min", "[-1, 2]"), sol("1"), NOTOK, None))
    out.append(("ext max GI on [0,1]: (empty) 1", ext(GI, "max", "[0, 1]"), sol("1"), NOTOK, None))
    out.append(("ext min GI no interval: 0", ext(GI, "min", None), sol("0"), NOTOK, None))
    out.append(("solve GI = 1/4: {-1/2, 1/2}", solve(f"{GI} = 1/4"), sol("{-1/2, 1/2}", "set"), NOTOK, None))
    out.append(("solve GI = 1/4: {-1/2} ctrl", solve(f"{GI} = 1/4"), sol("{-1/2}", "set"), NOTNO, None))
    out.append(("ineq GI >= 0: Reals", ineq(f"{GI} >= 0"), sol("Reals", "interval"), NOTOK, None))
    out.append(("ineq GI < 1/4: (-1/2, 1/2)", ineq(f"{GI} < 1/4"), sol("Interval.open(-1/2, 1/2)", "interval"), NOTOK, None))
    out.append(("solve GP = pi: {pi}", solve(f"{GP} = pi"), sol("{pi}", "set"), NOTOK, None))
    out.append(("der GP at pi: 1", der(GP, "pi"), sol("1"), NOTOK, None))
    out.append(("(x)' claim GP-like PW (gap n*pi): 1", der("x"), sol("Piecewise((1, sin(x) > 0), (1, sin(x) < 0))", "expression"),
                NOTOK, None))
    out.append(("(x^2)' claim PW gap [0,1] at 2x", der("x**2"), sol("Piecewise((2*x, x < 0), (2*x, x > 1))", "expression"),
                NOTOK, None))
    out.append(("evaluate GI at x=1/2 (given)", ir("evaluate", {"expr": GI}, givens=["x = 1/2"], shape="scalar"), sol("1/4"),
                NOTOK, None))
    out.append(("evaluate Piecewise((1, x < 0), (2, x > 0)) given x = 0: 1", ir("evaluate", {"expr": "Piecewise((1, x < 0), (2, x > 0))"},
                givens=["x = 0"], shape="scalar"), sol("1"), NOTOK, None))
    out.append(("lim x->0 of PW((1, x<0),(1, x>1)) : 1", lim("Piecewise((1, x < 0), (1, x > 1))", "0"), sol("1"), NOTOK, None))
    out.append(("lim x->0- of PW((1, x<0),(1, x>1)) : 1 ctrl", lim("Piecewise((1, x < 0), (1, x > 1))", "0", side="-"), sol("1"), NOTNO, None))
    out.append(("antideriv of PW((2x, x<0),(2x,x>1)) = x^2", anti("Piecewise((2*x, x < 0), (2*x, x > 1))"), sol("x**2", "expression"),
                NOTNO, None))
    out.append(("definite integral GI over [-1, 2]: 1/3 + 7/3", ir("definite_integral", {"integrand": GI, "var": "x", "lo": "-1", "hi": "2"},
                shape="scalar"), sol("8/3"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
