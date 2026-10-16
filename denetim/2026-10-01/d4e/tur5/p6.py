"""p6: YO-3 siblings: a problem function called in a constraint, a limit's given, a domain of discourse."""
import sys
from ortak import *

G0 = [{"name": "g", "args": ["x"], "expr": "0*sqrt(x)"}]          # defined for x >= 0 only, value 0
G1 = [{"name": "g", "args": ["x"], "expr": "x + 0*sqrt(x - 1/2)"}]  # x >= 1/2 as written


def solve(eq, vars_=None, givens=(), functions=None, dod=None):
    return ir("solve_equation", {"var": "x", "equation": eq}, givens=givens, vars_=vars_, functions=functions, dod=dod)


def cases():
    out = []
    # limit with a given that calls g
    out.append(("lim |x|/x at 0, given g(x) >= 0 (g = 0*sqrt x): DNE", ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"},
                givens=["g(x) >= 0"], shape="scalar", functions=G0), DNE, NOTOK, None))
    out.append(("ctrl lim |x|/x at 0, given 0*sqrt(x) >= 0: DNE", lim("Abs(x)/x", "0", givens=["0*sqrt(x) >= 0"]), DNE,
                NOTOK, None))
    out.append(("lim |x|/x at 0, given g(x) >= 0 (g = 0*sqrt x): 1", ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"},
                givens=["g(x) >= 0"], shape="scalar", functions=G0), sol("1"), NOTNO, None))
    # constraint calling g
    out.append(("solve x^2 = 1/4, constraint g(x) >= 0: {-1/2,1/2}", solve("x**2 = 1/4", vars_=[xc("g(x) >= 0")], functions=G0),
                sol("{-1/2, 1/2}", "set"), NOTOK, None))
    out.append(("ctrl solve x^2 = 1/4, constraint 0*sqrt(x) >= 0: {-1/2,1/2}", solve("x**2 = 1/4", vars_=[xc("0*sqrt(x) >= 0")]),
                sol("{-1/2, 1/2}", "set"), NOTOK, None))
    out.append(("solve x^2 = 1/4, given g(x) >= 0: {-1/2,1/2}", solve("x**2 = 1/4", givens=["g(x) >= 0"], functions=G0),
                sol("{-1/2, 1/2}", "set"), NOTOK, None))
    out.append(("solve x^2 = 1, given g(x) > 0 (g=x+0*sqrt(x-1/2)): {-1,1}", solve("x**2 = 1", givens=["g(x) > 0"], functions=G1),
                sol("{-1, 1}", "set"), NOTOK, None))
    out.append(("ext min x^2 on [-1,1], given g(x) >= 0 (g=0*sqrt x): 0 ctrl-ok", ext("x**2", "min", "[-1, 1]", givens=["g(x) >= 0"]) | {"functions": G0},
                sol("0"), NOTNO, None))
    out.append(("ext min x on [-1,1], given g(x) >= 0 (g=0*sqrt x): -1", ext("x", "min", "[-1, 1]", givens=["g(x) >= 0"]) | {"functions": G0},
                sol("-1"), NOTOK, None))
    out.append(("ext min x on [-1,1], constraint g(x) >= 0: -1", ext("x", "min", "[-1, 1]", vars_=[xc("g(x) >= 0")]) | {"functions": G0},
                sol("-1"), NOTOK, None))
    out.append(("der |x| constraint g(x)>=0 (x>=0): x/|x| ... claim -1?", der("Abs(x)", vars_=[xc("g(x) > -1")]) | {"functions": G0},
                sol("-1", "expression"), NOTOK, None))
    out.append(("ineq x^2 > 1/4 constraint g(x) >= 0: x<-1/2 or x>1/2",
                ir("solve_inequality", {"var": "x", "inequality": "x**2 > 1/4"}, vars_=[xc("g(x) >= 0")], functions=G0),
                sol("Union(Interval.open(-oo, -1/2), Interval.open(1/2, oo))", "interval"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
