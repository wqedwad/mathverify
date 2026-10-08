import sys
from ortak import *

XT = [X, T_]


def cases():
    out = []
    for G in ("x + 0*tan(acot(2) + acot(1/2)) > 0", "x*tan(acot(2) + acot(1/2))/tan(acot(2) + acot(1/2)) > 0"):
        for w, g, v, d in (("given", [G], XT, None), ("constraint", [], [xc(G), T_], None), ("dod", [], XT, G)):
            q = ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, g, v, dod=d)
            out.append((f"CU solve x**2 = 1/4, {w} {G}: {{1/2}} [condition undefined as written]", q, sol("{1/2}", "set"), NOTOK, None))
            out.append((f"CU limit |x|/x at 0, {w} {G}: 1", lim("Abs(x)/x", "0", g, v, d), sol("1"), NOTOK, None))
    # the limit given with an undecided binder: same root, the limit task
    G = "0*Integral(1/t, (t, x, 1)) >= 0"
    out.append((f"GW limit |x - 1|/(x - 1)... ctrl given {G}: 1 [right]", lim("Abs(x)/x", "0", [G], XT), sol("1"), NOTNO, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
