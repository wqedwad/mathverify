"""p10: YO-3 siblings: closed undecided conditions inside a problem FUNCTION body, a constraint calling it."""
import sys
from ortak import *

UND = "0*tan(acot(2) + acot(1/2))"          # acot 2 + acot 1/2 = pi/2: tan has no value; SymPy cannot decide it
G = [{"name": "g", "args": ["x"], "expr": f"x + {UND}"}]
H = [{"name": "h", "args": ["x"], "expr": f"x**2 + {UND}"}]


def cases():
    out = []
    out.append(("ctrl direct: solve x + UND = 1: {1}", ir("solve_equation", {"var": "x", "equation": f"x + {UND} = 1"}),
                sol("{1}", "set"), NOTOK, None))
    out.append(("fn: solve g(x) = 1: {1}", ir("solve_equation", {"var": "x", "equation": "g(x) = 1"}, functions=G),
                sol("{1}", "set"), NOTOK, None))
    out.append(("fn: ineq g(x) > 0: (0,oo)", ir("solve_inequality", {"var": "x", "inequality": "g(x) > 0"}, functions=G),
                sol("Interval.open(0, oo)", "interval"), NOTOK, None))
    out.append(("fn: der h(x) = 2x", der("h(x)") | {"functions": H}, sol("2*x", "expression"), NOTOK, None))
    out.append(("fn: der h at 1 = 2", der("h(x)", "1") | {"functions": H}, sol("2"), NOTOK, None))
    out.append(("fn: lim h(x) x->1 = 1", lim("h(x)", "1") | {"functions": H}, sol("1"), NOTOK, None))
    out.append(("fn: min h on [-1,1] = 0", ext("h(x)", "min", "[-1, 1]") | {"functions": H}, sol("0"), NOTOK, None))
    out.append(("fn: evaluate g(1) = 1", ir("evaluate", {"expr": "g(1)"}, functions=G, shape="scalar"), sol("1"), NOTOK, None))
    out.append(("fn: constraint g(x) > 0 solve x^2 = 1: {1}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1"},
                vars_=[xc("g(x) > 0")], functions=G), sol("{1}", "set"), NOTOK, None))
    out.append(("fn: given g(x) > 0, lim |x|/x at 0 = 1", ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"},
                givens=["g(x) > 0"], shape="scalar", functions=G), sol("1"), NOTOK, None))
    out.append(("fn: antideriv h' = h", anti("2*x + 0*h(x)") | {"functions": H}, sol("x**2", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
