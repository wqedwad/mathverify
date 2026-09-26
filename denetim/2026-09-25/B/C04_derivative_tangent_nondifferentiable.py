"""C04 derivative / tangent_line at non-differentiable points: SymPy's sign(0)=0 and
Heaviside(0)=1/2 are read as derivative values. Ground truth: one-sided difference quotients differ."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True); h = sp.Symbol("h", positive=True)
    def slopes(f, a):
        return (sp.limit((f.subs(x, a - h) - f.subs(x, a)) / (-h), h, 0), sp.limit((f.subs(x, a + h) - f.subs(x, a)) / h, h, 0))
    for f, a in ((sp.Abs(x), 0), (sp.Max(x, 0), 0), (sp.Abs(x**2 - 1), 1), (sp.exp(sp.Abs(x)), 0)):
        l, r = slopes(f, a); assert l != r, (f, l, r); print("   ground truth one-sided slopes", f, "at", a, ":", l, r)
    D = lambda f, at, order=None: IR("derivative", dict({"f": f, "var": "x", "at": at}, **({"order": order} if order else {})))
    check("d/dx |x| at 0 = 0", D("Abs(x)", "0"), SOL("value", "0"), "CORRECT")
    check("d/dx Max(x,0) at 0 = 1/2", D("Max(x, 0)", "0"), SOL("value", "1/2"), "CORRECT")
    check("d/dx |x^2-1| at 1 = 0", D("Abs(x**2 - 1)", "1"), SOL("value", "0"), "CORRECT")
    check("d/dx e^|x| at 0 = 0", D("exp(Abs(x))", "0"), SOL("value", "0"), "CORRECT")
    check("d/dx Piecewise((x^2,x<1),(2x,x>=1)) at 1 = 2 (f jumps at 1)", D("Piecewise((x**2, x < 1), (2*x, x >= 1))", "1"), SOL("value", "2"), "CORRECT")
    check("d2/dx2 x|x| at 0 = 0 (f'=2|x| not differentiable at 0)", D("x*Abs(x)", "0", 2), SOL("value", "0"), "CORRECT")
    T = lambda f, at: IR("tangent_line", {"f": f, "var": "x", "at": at}, vars_=("x", "y"))
    check("tangent to |x| at 0: y = 0", T("Abs(x)", "0"), SOL("equation", "y = 0"), "CORRECT")
    check("tangent to Max(x,0) at 0: y = x/2", T("Max(x, 0)", "0"), SOL("equation", "y = x/2"), "CORRECT")
    # the right answer ('does not exist') is refuted: DNE is parsed as a free symbol
    check("d/dx |x| at 0 does not exist (right answer)", D("Abs(x)", "0"), SOL("dne", None), "INCORRECT")
