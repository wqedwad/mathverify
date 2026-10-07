import sys
from ortak import *

XT = [X, T_]


def cases():
    out = []
    for G in ("x + 0*Integral(1/t, (t, x, 1)) > 0", "x + 0*Integral(1/sqrt(t), (t, x, 1)) > -1",
              "0*Integral(1/t, (t, x, 1)) >= 0", "x**2 + 0*Integral(exp(-x*t), (t, 0, oo)) >= 0"):
        for w, g, v, d in (("given", [G], XT, None), ("constraint", [], [xc(G), T_], None), ("dod", [], XT, G)):
            q = lim("Abs(x)/x", "0", g, v, d)
            out.append((f"GW limit |x|/x at 0, {w} {G}: DNE [x > 0 as written]", q, DNE, NOTOK, None))
            out.append((f"GW limit |x|/x at 0, {w} {G}: -1 [x > 0 as written]", q, sol("-1"), NOTOK, None))
    G = "x + 0*Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo)) > -5"
    q = ir("solve_equation", {"var": "x", "equation": "x**2 = 0"}, [G], XT)
    out.append((f"GW solve x**2 = 0, given {G}: {{0}} [0 excluded]", q, sol("{0}", "set"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
