import sys
from ortak import *

XT = [X, T_]


def cases():
    out = []
    for c in ("2*x + 0*Integral(1/t, (t, x, 1))", "2*x + 0*Integral(1/t, (t, 0, 1))", "2*x + 0*tan(acot(2) + acot(1/2))",
              "2*x + 0*Integral(1/(t - x), (t, 0, 1))", "2*x + 0*Integral(1/sqrt(t), (t, x, 1))",
              "2*x + 0*Sum(1/(k - x), (k, 1, 3))", "2*x + 0*Integral(t*sin(t)/(x**2*t**2 + 1), (t, 1, oo))",
              "2*x + 0*Integral(exp(x*t), (t, 0, oo))", "2*x + 0*Integral(1/t, (t, 1, oo))",
              "2*x + 0*Limit(1/(x*y), y, 0)", "2*x + 0*at(diff(sqrt(x), x), x, x)"):
        out.append((f"CW derivative x**2: {c} [claim undefined where f' exists]", der("x**2", None, [], XT),
                    sol(c, "expression"), NOTOK, None))
    for c in ("x**2 + 0*Integral(1/t, (t, x, 1))", "x**2 + 0*Integral(exp(x*t), (t, 0, oo))"):
        out.append((f"CW anti 2*x: {c}", anti("2*x", [], XT), sol(c, "expression"), NOTOK, None))
    for c in ("x + 1 + 0*Integral(1/t, (t, x, 1))", "x + 1 + 0*Integral(exp(x*t), (t, 0, oo))"):
        out.append((f"CW simplify x + 1: {c}", ir("simplify_expression", {"expr": "x + 1"}, [], XT, shape="expression"),
                    sol(c, "expression"), NOTOK, None))
    out.append(("CW ctrl derivative x**2: 2*x + 0*sqrt(x)", der("x**2", None, [], XT), sol("2*x + 0*sqrt(x)", "expression"),
                NOTOK, None))
    out.append(("CW ctrl simplify x + 1: x + 1 + 0*sqrt(x)", ir("simplify_expression", {"expr": "x + 1"}, [], XT,
                                                                   shape="expression"),
                sol("x + 1 + 0*sqrt(x)", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
