import sys, json
from ortak import *


def cases():
    out = []
    for f, claim, lab in (("Piecewise((x**2, x < 0), (x**2, x > 0))", "{0}", "PWS gap at 0: {0} [true: empty]"),
                          ("Piecewise((x, x < 1), (x, x > 1)) - 1", "{1}", "PWS gap at 1: {1}"),
                          ("Piecewise((x**2 - 1, x < 1), (x**2 - 1, x > 1))", "{-1, 1}", "PWS gap at 1: {-1, 1} [true {-1}]"),
                          ("x*Piecewise((1, x < 0), (1, x > 0))", "{0}", "PWS x*PW gap: {0}"),
                          ("x**2/x", "{0}", "ctrl x^2/x = 0: {0}"),
                          ("x + log(x) - log(x)", "{0}", "ctrl x + log x - log x = 0: {0}")):
        q = ir("solve_equation", {"var": "x", "equation": f"{f} = 0"})
        out.append((lab, q, sol(claim, "set"), NOTOK, None))
    out.append(("PWS ineq PW(x^2) <= 0: {0}", ir("solve_inequality", {"var": "x", "inequality": "Piecewise((x**2, x < 0), (x**2, x > 0)) <= 0"}), sol("{0}", "set"), NOTOK, None))
    out.append(("PWS evaluate PW at 0", ir("evaluate", {"expr": "Piecewise((t**2, t < 0), (t**2, t > 0))"}, ["t = 0"], [T_], shape="scalar"), sol("0"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
