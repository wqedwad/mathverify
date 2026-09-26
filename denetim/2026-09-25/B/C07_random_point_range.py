"""C07 random-point equality samples only |x| <= 1000 (Reals: uniform(-scale, scale), scale <= 1000),
so a claim that differs only for x > 1000 is certified (conf 0.97). Ground truth: at x = 6000 the
claimed derivative differs from the true one."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    F = x**2/2 + sp.Max(x - 5000, 0)
    print("   F'(6000) - 6000 =", sp.diff(F, x).subs(x, 6000) - 6000)
    check("int x dx = x^2/2 + Max(x-5000, 0)", IR("antiderivative", {"integrand": "x", "var": "x"}), SOL("expression", "x**2/2 + Max(x - 5000, 0)"), "CORRECT")
    check("d/dx x^2 = 2x + Max(x-1500, 0)", IR("derivative", {"f": "x**2", "var": "x"}), SOL("expression", "2*x + Max(x - 1500, 0)"), "CORRECT")
