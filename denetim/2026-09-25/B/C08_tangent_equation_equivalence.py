"""C08 tangent_line: equation equivalence solves both equations for x only (y a parameter), so a
factor that depends only on y disappears. Ground truth: (y-2x+1)(y-5)=0 contains the point (0,5),
which is not on the tangent y = 2x - 1 to x^2 at 1."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x, y = sp.symbols("x y", real=True)
    assert ((y - 2*x + 1)*(y - 5)).subs({x: 0, y: 5}) == 0 and (y - (2*x - 1)).subs({x: 0, y: 5}) != 0
    T = IR("tangent_line", {"f": "x**2", "var": "x", "at": "1"}, vars_=("x", "y"))
    check("tangent: (y - 2x + 1)*(y - 5) = 0", T, SOL("equation", "(y - 2*x + 1)*(y - 5) = 0"), "CORRECT")
    check("tangent: y*(y - 2x + 1) = 0", T, SOL("equation", "y*(y - 2*x + 1) = 0"), "CORRECT")
    check("tangent: y*Abs(y - 2x + 1) = 0", T, SOL("equation", "y*Abs(y - 2*x + 1) = 0"), "CORRECT")
