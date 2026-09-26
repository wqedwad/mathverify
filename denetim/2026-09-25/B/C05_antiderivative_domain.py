"""C05 antiderivative: the derivative certificate accepts F with F' = f symbolically even when F is
not real on part of f's domain, or jumps inside it. Ground truth: log(-1) is not real; the jumps of
-atan(1/x) at 0, atan(tan x) at pi/2 and the Weierstrass form at pi are nonzero (computed)."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    assert sp.log(sp.Integer(-1)).is_real is False
    jump = lambda F, a: sp.limit(F, x, a, "+") - sp.limit(F, x, a, "-")
    print("   jump -atan(1/x) at 0:", jump(-sp.atan(1/x), 0))
    print("   jump atan(tan x) at pi/2:", jump(sp.atan(sp.tan(x)), sp.pi/2))
    W = 2*sp.atan(sp.tan(x/2)/sp.sqrt(3))/sp.sqrt(3)
    print("   jump Weierstrass at pi:", sp.simplify(jump(W, sp.pi)))
    A = lambda g: IR("antiderivative", {"integrand": g, "var": "x"})
    check("int 1/x dx = log(x) + C", A("1/x"), SOL("expression", "log(x) + C"), "CORRECT")
    check("int tan x dx = -log(cos x) + C", A("tan(x)"), SOL("expression", "-log(cos(x)) + C"), "CORRECT")
    check("int 1/(x^2-1) dx = log((x-1)/(x+1))/2 + C", A("1/(x**2 - 1)"), SOL("expression", "log((x - 1)/(x + 1))/2 + C"), "CORRECT")
    check("int 1/(x log x) dx = log(log x) + C", A("1/(x*log(x))"), SOL("expression", "log(log(x)) + C"), "CORRECT")
    check("int 1/(1+x^2) dx = -atan(1/x) + C", A("1/(1 + x**2)"), SOL("expression", "-atan(1/x) + C"), "CORRECT")
    check("int 1 dx = atan(tan x) + C", A("1"), SOL("expression", "atan(tan(x)) + C"), "CORRECT")
    check("int 1/(2+cos x) dx = 2/sqrt3 atan(tan(x/2)/sqrt3) + C", A("1/(2 + cos(x))"), SOL("expression", "2*atan(tan(x/2)/sqrt(3))/sqrt(3) + C"), "CORRECT")
