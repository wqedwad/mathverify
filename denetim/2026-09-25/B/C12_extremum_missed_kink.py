"""C12 extremum: kinks where f' is nonzero on both sides (|x-1| with a slope added) are neither
derivative zeros nor singularities, so they never become candidates. The EVT route then 'proves'
completeness from the derivative zeros alone and certifies a wrong MAXIMUM VALUE; the local
first-derivative test misclassifies around the kink. Ground truth: monotonicity pieces below."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    f = sp.exp(x)/100 - sp.Abs(x - 1)
    # f' = 1 + e^x/100 > 0 on (0,1); f' = e^x/100 - 1 < 0 on (1, ln 100); so f(1) = e/100 > f(0), f(ln100), f(5)
    assert all(sp.N(f.subs(x, 1) - f.subs(x, t)) > 0 for t in (0, sp.log(100), 5))
    E = lambda g, iv, w: IR("extremum", dict({"f": g, "var": "x", "which": w}, **({"interval": iv} if iv else {})))
    check("max of e^x/100 - |x-1| on [0,5] = -99/100", E("exp(x)/100 - Abs(x - 1)", "[0, 5]", "max"), SOL("value", "-99/100"), "CORRECT")
    check("argmax of e^x/100 - |x-1| on [0,5] = 0", E("exp(x)/100 - Abs(x - 1)", "[0, 5]", "argmax"), SOL("value", "0"), "CORRECT")
    check("max of e^x/100 - |x-1| on [0,5] = e/100 (right answer)", E("exp(x)/100 - Abs(x - 1)", "[0, 5]", "max"), SOL("value", "E/100"), "INCORRECT")
    g = x**2 - 4*sp.Abs(x - 1)
    # local minima: x=-2 (g=-8) and x=2 (g=0, g' = 2x-4 changes sign - to +); local max: kink x=1 (slopes 6, -2)
    print("   g(-2), g(2), g(1):", g.subs(x, -2), g.subs(x, 2), g.subs(x, 1))
    check("local_min of x^2-4|x-1| = -8 (two local minima: -8 and 0)", E("x**2 - 4*Abs(x - 1)", None, "local_min"), SOL("value", "-8"), "CORRECT")
    check("local_argmin of x^2-4|x-1| = -2 (argmins -2 and 2)", E("x**2 - 4*Abs(x - 1)", None, "local_argmin"), SOL("value", "-2"), "CORRECT")
    check("local_max of x^2-4|x-1| = 1 (right answer)", E("x**2 - 4*Abs(x - 1)", None, "local_max"), SOL("value", "1"), "INCORRECT")
