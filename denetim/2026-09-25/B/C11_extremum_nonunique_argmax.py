"""C11 extremum argmax/argmin: extremisers that form a continuum (or are a kink that is not a
candidate) are invisible, so a non-unique argmax is certified as if unique. Ground truth below."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    assert sp.floor(sp.Rational(1, 2)) == sp.floor(sp.Rational(3, 4)) == 0          # argmin of floor on [1/2,3] is [1/2,1)
    assert sp.floor(sp.Rational(5, 2)) == sp.floor(2) == 2                           # argmax on [0,5/2] is [2,5/2]
    assert sp.Min(2, 1) == sp.Min(sp.Rational(3, 2), 1) == 1                        # argmax of Min(x,1) on [0,2] is [1,2]
    f = x**2 - 4*sp.Abs(x - 1)
    assert f.subs(x, 1) == f.subs(x, 3) == 1                                         # max 1 attained at 1 AND 3
    E = lambda g, iv, w: IR("extremum", {"f": g, "var": "x", "interval": iv, "which": w})
    check("argmin floor(x) on [1/2,3] = 1/2", E("floor(x)", "[1/2, 3]", "argmin"), SOL("value", "1/2"), "CORRECT")
    check("argmax floor(x) on [0,5/2] = 5/2", E("floor(x)", "[0, 5/2]", "argmax"), SOL("value", "5/2"), "CORRECT")
    check("argmax Min(x,1) on [0,2] = 2", E("Min(x, 1)", "[0, 2]", "argmax"), SOL("value", "2"), "CORRECT")
    check("argmax 5 on (0,1] = 1", E("5 + 0*x", "(0, 1]", "argmax"), SOL("value", "1"), "CORRECT")
    check("argmax x^2-4|x-1| on [-3,3] = 3", E("x**2 - 4*Abs(x - 1)", "[-3, 3]", "argmax"), SOL("value", "3"), "CORRECT")
