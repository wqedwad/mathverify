from common import *
import sympy as sp

def si(ineq, claim, truth_ok, kind="interval", var="x", dom=None, dod=None, name="", param=False, steps=None):
    v = {"name": var}
    if dom: v["domain"] = dom
    p = {"var": var}
    g = [ineq] if not param else []
    if param: p["inequality"] = ineq
    return run(f"solve_ineq[{name or ineq}|{dom}|{dod}]={claim}", ir("solve_inequality", p, vars_=[v], givens=g, dod=dod, shape="interval"),
               sol(kind, claim, steps), truth_ok)

if __name__ == "__main__":
    si("x**2 - 5*x - 14 < 0", "(-2, 7)", True); si("x**2 - 5*x - 14 < 0", "[-2, 7]", False); si("x**2 - 5*x - 14 < 0", "(-2, 7]", False)
    si("x**2 - 5*x - 14 <= 0", "[-2, 7]", True); si("x**2 - 5*x - 14 <= 0", "(-2, 7)", False)
    si("x**2 - 5*x - 14 > 0", "(-oo, -2) U (7, oo)", True); si("x**2 - 5*x - 14 > 0", "(-oo, -2] U (7, oo)", False)
    si("x**2 - 5*x - 14 > 0", "(-oo, -2) ∪ (7, ∞)", True, name="unicode union")
    si("x**2 - 5*x - 14 > 0", "Union(Interval.open(-oo, -2), Interval.open(7, oo))", True, name="sympy union")
    si("x**2 - 5*x - 14 > 0", "Reals - [-2, 7]", True, name="complement text")
    si("x**2 - 5*x - 14 > 0", "Complement(Reals, Interval(-2, 7))", True, name="Complement")
    # rational
    si("(x - 3)/(x + 2) <= 0", "(-2, 3]", True); si("(x - 3)/(x + 2) <= 0", "[-2, 3]", False)
    si("(x - 3)/(x + 2) >= 0", "(-oo, -2) U [3, oo)", True); si("(x - 3)/(x + 2) >= 0", "(-oo, -2] U [3, oo)", False)
    si("1/x < 1", "(-oo, 0) U (1, oo)", True); si("1/x < 1", "(1, oo)", False); si("1/x < 1", "(-oo, 0] U (1, oo)", False)
    # removable
    si("x**2/x > 0", "(0, oo)", True); si("x**2/x >= 0", "(0, oo)", True); si("x**2/x >= 0", "[0, oo)", False)
    si("x/x > 0", "(-oo, 0) U (0, oo)", True); si("x/x > 0", "(-oo, oo)", False)
    si("(x**2 - 1)/(x - 1) > 0", "(-1, 1) U (1, oo)", True); si("(x**2 - 1)/(x - 1) > 0", "(-1, oo)", False)
    si("(x - 1)**2*(x + 2) >= 0", "[-2, oo)", True); si("(x - 1)**2*(x + 2) > 0", "(-2, 1) U (1, oo)", True)
    si("(x - 1)**2*(x + 2) > 0", "(-2, oo)", False)
    # sqrt
    si("sqrt(x + 3) < 2", "[-3, 1)", True); si("sqrt(x + 3) < 2", "(-oo, 1)", False); si("sqrt(x + 3) < 2", "(-3, 1)", False)
    si("sqrt(x) > x - 2", "[0, 4)", True); si("sqrt(x) > x - 2", "(0, 4)", False)
    si("sqrt(x - 1) >= 0", "[1, oo)", True); si("sqrt(x - 1) >= 0", "(-oo, oo)", False)
    si("sqrt(x)**2 >= 0", "[0, oo)", True, name="sqrt(x)**2>=0"); si("sqrt(x)**2 >= 0", "(-oo, oo)", False, name="sqrt(x)**2>=0")
    # log
    si("log(x - 1) < 1", "(1, 1 + E)", True); si("log(x - 1) < 1", "(-oo, 1 + E)", False); si("log(x - 1) < 1", "[1, 1 + E)", False)
    si("log(x) > 0", "(1, oo)", True)
    si("log(x - 1) < 1", "(1, 3.718281828459045)", False, name="log approx endpoint")
    si("log(x - 1) < 1", "(1, 1 + 2.718281828459045235360287471352662497757)", False, name="log approx endpoint40")
    # abs
    si("Abs(x - 3) < 2", "(1, 5)", True); si("Abs(x - 3) <= 2", "(1, 5)", False)
    si("Abs(x - 3) > 2", "(-oo, 1) U (5, oo)", True)
    si("Abs(x) + Abs(x - 2) <= 2", "[0, 2]", True); si("Abs(x) + Abs(x - 2) <= 2", "{0, 2}", False, kind="set")
    si("Abs(x) + Abs(x - 2) < 2", "{}", True, kind="set"); si("Abs(x) + Abs(x - 2) < 2", "(0, 2)", False)
    # isolated points
    si("(x - 1)**2 <= 0", "{1}", True, kind="set"); si("(x - 1)**2 <= 0", "{}", False, kind="set")
    si("(x - 1)**2*(x - 3) <= 0", "(-oo, 3]", True); si("(x - 1)**2*(x - 3) < 0", "(-oo, 1) U (1, 3)", True)
    si("(x - 1)**2*(x - 3) < 0", "(-oo, 3)", False)
    si("x**2*(x - 2)*(x+2) >= 0", "(-oo, -2] U {0} U [2, oo)", True, kind="set", name="isolated 0")
    si("x**2*(x - 2)*(x+2) >= 0", "(-oo, -2] U [2, oo)", False, name="isolated 0 missing")
    si("x**2*(x - 2)*(x+2) >= 0", "(-oo, -2] ∪ {0} ∪ [2, ∞)", True, kind="set", name="isolated 0 unicode")
    # irrational endpoints
    si("x**2 < 2", "(-sqrt(2), sqrt(2))", True); si("x**2 < 2", "(-1.414213562373095, 1.414213562373095)", False, name="x^2<2 approx")
    si("x**2 < 2", "(-1.41421356237309504880168872420969807857, 1.41421356237309504880168872420969807857)", False, name="x^2<2 approx40")
    si("x**2 - 2*x - 1 < 0", "(1 - sqrt(2), 1 + sqrt(2))", True)
    si("x**2 - 2*x - 1 < 0", "(1 - sqrt(2), 1 + sqrt(2)]", False)
    si("x**3 - 3*x + 1 > 0", "(2*cos(8*pi/9), 2*cos(4*pi/9)) U (2*cos(2*pi/9), oo)", True, name="cubic trig endpoints")
    si("x**3 - 3*x + 1 > 0", "(2*cos(8*pi/9), 2*cos(4*pi/9)) U [2*cos(2*pi/9), oo)", False, name="cubic trig endpoints closed")
    # exponential
    si("2**x > 8", "(3, oo)", True); si("2**x >= 8", "(3, oo)", False)
    si("(1/2)**x > 4", "(-oo, -2)", True); si("(1/2)**x > 4", "(-2, oo)", False)
    # domain
    si("x**2 < 9", "(0, 3)", True, dod="x > 0"); si("x**2 < 9", "(-3, 3)", False, dod="x > 0")
    si("x**2 < 9", "{-2, -1, 0, 1, 2}", True, kind="set", dom="integer"); si("x**2 < 9", "(-3, 3)", False, dom="integer")
    si("x**2 < 9", "{-2, -1, 1, 2}", False, kind="set", dom="integer")
    # always true / false
    si("x**2 + 1 > 0", "(-oo, oo)", True); si("x**2 + 1 > 0", "Reals", True, kind="set"); si("x**2 + 1 < 0", "{}", True, kind="set")
    si("x**2 + 1 > 0", "(0, oo)", False)
    # trig
    si("sin(x) > 2", "{}", True, kind="set")
    # sets with open at infinity closed bracket
    si("x > 3", "(3, oo]", None, name="closed at oo")
    si("x >= 3", "[3, oo)", True); si("x >= 3", "(3, oo)", False)
    si("x >= 3", "x >= 3", True, kind="interval", name="relation form")
    summary()
