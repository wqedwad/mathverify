import sys
from ortak import *

AP = {"name": "a", "domain": "positive_real"}
D5 = "Integral(sin(t)*t/((x - 1)**2*t**2 + 1), (t, 1, oo))"


def cases():
    out = []
    XT = [XP, T_]
    out.append(("DIRP derivative x**3 + 0*I5(x) at 1, x positive_real: 3 [undefined at 1]", der(f"x**3 + 0*{D5}", "1", [], XT),
                sol("3"), NOTOK, None))
    out.append(("DIRP tangent x**3 + 0*I5(x) at 1, x positive_real: y = 3*x - 2", tan(f"x**3 + 0*{D5}", "1", [], XT),
                sol("y = 3*x - 2", "equation"), NOTOK, None))
    q = ir("solve_equation", {"var": "x", "equation": f"x**2 - 1 + 0*{D5} = 0"}, [], XT)
    out.append(("DIRP solve x**2 - 1 + 0*I5(x) = 0, x > 0 declared: {1} [1 undefined]", q, sol("{1}", "set"), NOTOK, None))
    out.append(("DIRP max -(x - 1)**2 + 0*I5(x) on [0, 2], x positive_real: 0", ext(f"-(x - 1)**2 + 0*{D5}", "max", "[0, 2]", [], XT),
                sol("0"), NOTOK, None))
    q = ir("evaluate", {"expr": "0*Integral(t*sin(t)/((a - 1)**2*t**2 + 1), (t, 1, oo)) + 1"}, [], [AP, T_], shape="scalar")
    out.append(("DIRP evaluate 0*I(a) + 1, a positive_real: 1 [undefined at a = 1]", q, sol("1"), NOTOK, None))
    out.append(("DIRP series k + 0*I(k), k=1..3, k positive integer: 6 [k = 1 undefined]",
                ss("k + 0*Integral(t*sin(t)/((k - 1)**2*t**2 + 1), (t, 1, oo))", 1, 3, [],
                   [{"name": "k", "domain": "positive_integer"}, T_]), sol("6"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
