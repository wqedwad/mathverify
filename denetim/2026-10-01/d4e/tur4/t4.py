import sys
from ortak import *

AR = {"name": "a", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}


def d(f, claim, label, exp=NOTOK, givens=(), vars_=None, at=None):
    return (label, der(f, at, givens=givens, vars_=vars_), sol(claim, "expression" if at is None else "value"), exp, None)


def cases():
    out = []
    for c in ["2*x + 0*log(-1)", "2*x + 0*sqrt(-1)", "2*x + 0*acos(2)", "2*x + 0*log(0)", "2*x + 0*asin(3)",
              "2*x + 0*tan(pi/2)", "2*x + 0*cot(0)", "2*x + 0*(-8)**(1/3)", "2*x + 0*log(1 - E)",
              "2*x + 0*sqrt(1 - pi)", "2*x + 0*acosh(0)", "2*x + 0*atanh(1)", "2*x + 0*log(cos(pi))",
              "2*x + 0*sqrt(sin(4))", "2*x + 0*sqrt(-x**2 - 1)", "2*x + 0*log(-Abs(x) - 1)"]:
        out.append(d("x**2", c, f"CN (x^2)' = {c} [claim undefined everywhere]"))
    out.append(d("x**2", "2*x + 0*sqrt(-a**2 - 1)", "CNa (x^2)' = 2x + 0 sqrt(-a^2-1), a real", vars_=[X, AR]))
    out.append(d("x**2", "2*x + 0*sqrt(-a)", "CNa (x^2)' = 2x + 0 sqrt(-a), a>0", vars_=[X, AP]))
    out.append(d("x**2", "2*x + 0*log(-a)", "CNa (x^2)' = 2x + 0 log(-a), a>0", vars_=[X, AP]))
    out.append(d("log(a*x)", "1/x + 0*sqrt(-a)", "CNp (log(ax))' = 1/x + 0 sqrt(-a), a>0 [for_every_parameter]", vars_=[X, AP]))
    out.append(d("log(a*x)", "1/x + 0*log(-1)", "CNp (log(ax))' = 1/x + 0 log(-1), a>0", vars_=[X, AP]))
    out.append(d("log(a*x)", "1/x + 0*sqrt(-x**2 - a)", "CNp (log(ax))' = 1/x + 0 sqrt(-x^2-a), a>0", vars_=[X, AP]))
    out.append(d("x**2", "0*log(-1) + 2", "CNv (x^2)' at 1 = 2 + 0 log(-1)", at="1"))
    out.append(("CNi antiderivative 2x: x**2 + 0*log(-1)", anti("2*x"), sol("x**2 + 0*log(-1)", "expression"), NOTOK, None))
    out.append(("CNs simplify 2x/2: x + 0*log(-1)", ir("simplify", {"expr": "2*x/2"}, shape="expression"), sol("x + 0*log(-1)", "expression"), NOTOK, None))
    out.append(("CNl limit x at 1: 1 + 0*log(-1)", lim("x", "1"), sol("1 + 0*log(-1)"), NOTOK, None))
    out.append(("CNt tangent x**2 at 1: y = 2x - 1 + 0*log(-1)", tan("x**2", "1"), sol("y = 2*x - 1 + 0*log(-1)", "equation"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
