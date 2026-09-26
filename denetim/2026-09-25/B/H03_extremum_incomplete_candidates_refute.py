"""H03 extremum: when solveset cannot list the critical points, 'a better value exists' is measured
against the CANDIDATES' best, not against the claim, so the true maximum is refuted.
Ground truth: e^{-x^2} cos(50x) <= 1 with equality at 0; cos x cos(sqrt2 x) <= 1 with equality at 0;
x^2/4 - |x-1| on [0,5/2] has max 1/4 at the kink x = 1."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    g = x**2/4 - sp.Abs(x - 1)
    print("   x^2/4-|x-1| at 0,1,2,5/2:", [g.subs(x, t) for t in (0, 1, 2, sp.Rational(5, 2))])
    E = lambda f, iv, w: IR("extremum", {"f": f, "var": "x", "interval": iv, "which": w})
    check("max e^{-x^2} cos(50x) on [-1,1] = 1", E("exp(-x**2)*cos(50*x)", "[-1, 1]", "max"), SOL("value", "1"), "INCORRECT")
    check("max cos(x) cos(sqrt2 x) on [-1,1] = 1", E("cos(x)*cos(sqrt(2)*x)", "[-1, 1]", "max"), SOL("value", "1"), "INCORRECT")
    check("max x^2/4 - |x-1| on [0,5/2] = 1/4", E("x**2/4 - Abs(x - 1)", "[0, 5/2]", "max"), SOL("value", "1/4"), "INCORRECT")
    check("min |x|+|x-2| on (1,3] = 2", E("Abs(x) + Abs(x - 2)", "(1, 3]", "min"), SOL("value", "2"), "INCORRECT")
