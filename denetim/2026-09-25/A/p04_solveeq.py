from common import *
import sympy as sp

def se(eq, claim, truth_ok, kind="set", var="x", dom=None, dod=None, name="", steps=None, params_eq=False):
    v = {"name": var}
    if dom: v["domain"] = dom
    p = {"var": var}
    if params_eq:
        p["equation"] = eq; g = []
    else:
        g = [eq]
    return run(f"solve_eq[{name or eq}|{dom}|{dod}]={claim}", ir("solve_equation", p, vars_=[v], givens=g, dod=dod, shape="set"),
               sol(kind, claim, steps), truth_ok)

if __name__ == "__main__":
    # extraneous roots
    se("sqrt(x + 4) = x - 2", "{5}", True); se("sqrt(x + 4) = x - 2", "{0, 5}", False); se("sqrt(x + 4) = x - 2", "{0}", False)
    se("sqrt(2*x + 3) = x", "{3}", True); se("sqrt(2*x + 3) = x", "{-1, 3}", False)
    se("sqrt(x) = -2", "{}", True); se("sqrt(x) = -2", "{4}", False)
    se("sqrt(x - 3) + sqrt(x) = 3", "{4}", True); se("sqrt(x - 3) + sqrt(x) = 3", "{}", False)
    # log
    se("log(x - 1) + log(x - 3) = log(3)", "{4}", True); se("log(x - 1) + log(x - 3) = log(3)", "{0, 4}", False)
    se("log(x**2) = 2*log(3)", "{-3, 3}", True); se("log(x**2) = 2*log(3)", "{3}", False)
    se("2*log(x) = log(9)", "{3}", True); se("2*log(x) = log(9)", "{-3, 3}", False)
    se("log(x, 2) + log(x - 2, 2) = 3", "{4}", True); se("log(x, 2) + log(x - 2, 2) = 3", "{-2, 4}", False)
    # rational
    se("x/(x - 3) = 3/(x - 3) + 2", "{}", True); se("x/(x - 3) = 3/(x - 3) + 2", "{3}", False)
    se("(x**2 - 1)/(x - 1) = 2", "{}", True); se("(x**2 - 1)/(x - 1) = 2", "{1}", False)
    se("x**2/x = 0", "{}", True); se("x**2/x = 0", "{0}", False)
    se("x*(x - 1)/(x - 1) = 1", "{}", True); se("x*(x - 1)/(x - 1) = 1", "{1}", False)
    se("(x - 2)**2/(x - 2) = 0", "{}", True); se("(x - 2)**2/(x - 2) = 0", "{2}", False)
    se("sqrt(x)**2 = -1", "{}", True); se("sqrt(x)**2 = -1", "{-1}", False)
    se("x/x = 1", "{}", None, name="x/x=1 (inf)")  # infinitely many solutions -> {} wrong
    se("x/x = 1", "{1}", False, name="x/x=1 (inf)")
    # abs
    se("Abs(x - 1) = 3", "{-2, 4}", True); se("Abs(x - 1) = 3", "{4}", False)
    se("Abs(2*x - 3) = x", "{1, 3}", True); se("Abs(2*x - 3) = x", "{3}", False)
    se("Abs(x - 1) + Abs(x - 3) = 2", "{1, 3}", False)   # truth: [1,3]
    se("Abs(x - 1) + Abs(x - 3) = 2", "[1, 3]", True, kind="interval")
    se("Abs(x) = -1", "{}", True)
    # exponential
    se("2**x = 8", "{3}", True); se("2**x = 8", "{3, -3}", False)
    se("4**x - 3*2**x + 2 = 0", "{0, 1}", True); se("4**x - 3*2**x + 2 = 0", "{1}", False)
    se("2**x = x**2", "{2, 4}", False)   # third root ~ -0.7667
    se("exp(x) = x + 1", "{0}", True); se("exp(x) = x + 2", "{}", False)
    se("x**x = 4", "{2}", True)  # x>0 only? x^x for real x defined x>0 ; also negative integers? (-2)^(-2)=1/4
    # polynomial
    se("x**3 - 6*x**2 + 11*x - 6 = 0", "{1, 2, 3}", True); se("x**3 - 6*x**2 + 11*x - 6 = 0", "{1, 2}", False)
    se("x**4 - 5*x**2 + 4 = 0", "{-2, -1, 1, 2}", True); se("x**4 - 5*x**2 + 4 = 0", "{1, 2}", False)
    se("x**2 = 2", "{-sqrt(2), sqrt(2)}", True); se("x**2 = 2", "{sqrt(2)}", False)
    se("x**2 = 2", "{-1.41421356237310, 1.41421356237310}", False, name="x^2=2 decimals15")
    se("x**2 = 2", "{-1.4142135623730950488016887242097, 1.4142135623730950488016887242097}", False, name="x^2=2 decimals32")
    se("x**2 = 2", "{-2/sqrt(2), 2/sqrt(2)}", True, name="x^2=2 unrationalized")
    se("x**2 = 2", "{-sqrt(8)/2, sqrt(8)/2}", True, name="x^2=2 sqrt8/2")
    se("x**3 - 3*x + 1 = 0", "{2*cos(2*pi/9), 2*cos(4*pi/9), 2*cos(8*pi/9)}", True, name="casus irreducibilis")
    se("x**3 - 3*x + 1 = 0", "{2*cos(2*pi/9), 2*cos(4*pi/9)}", False, name="casus irreducibilis missing")
    se("x**9 - x = 0", "{-1, 0, 1}", True); se("x**9 - x = 0", "{0, 1}", False)
    se("x**10 - 2 = 0", "{-2**(1/10), 2**(1/10)}", True); se("x**10 - 2 = 0", "{2**(1/10)}", False)
    se("x**11 - x - 1 = 0", "{}", False, name="deg11 one real root")
    se("x**2 + 1 = 0", "{}", True); se("x**2 + 1 = 0", "{I, -I}", False)
    se("(x - 1)**2 = 0", "{1}", True); se("(x - 1)**2 = 0", "{1, 1}", True, name="dup")
    se("x**2 - 5*x + 6 = 0", "2", False, kind="value"); se("x**2 - 5*x + 6 = 0", "[2, 3]", True, kind="set", name="list-bracket")
    se("x**2 - 5*x + 6 = 0", ["2", "3"], True, name="json-list")
    # identity -> infinitely many
    se("x + 1 = x + 1", "{}", False, name="identity {}")
    se("(x + 1)**2 = x**2 + 2*x + 1", "{0}", False, name="identity {0}")
    se("x + 1 = x + 2", "{}", True, name="contradiction")
    # trig in solve_equation
    se("sin(x) = 0", "{0}", False); se("sin(x) = 0", "{0, pi}", False)
    # domain
    se("x**2 = 4", "{2}", True, dod="x > 0"); se("x**2 = 4", "{-2, 2}", False, dod="x > 0")
    se("x**2 = 4", "{2}", True, dom="positive_integer"); se("x**2 = 4", "{-2, 2}", False, dom="positive_integer")
    se("2*x = 3", "{}", True, dom="integer"); se("2*x = 3", "{3/2}", False, dom="integer")
    se("x**2 = 4", "{-2, 2}", True, dom="integer")
    se("x**3 = x", "{0, 1}", True, dod="x >= 0"); se("x**3 = x", "{1}", False, dod="x >= 0")
    se("x**3 = x", "{1}", True, dod="x > 0")
    # floor / piecewise
    se("floor(x) = 2", "{2}", False)
    se("Max(x, 2) = 2", "{2}", False)  # truth (-oo, 2]
    se("Min(x, 1) + x = 3", "{2}", True)
    summary()
