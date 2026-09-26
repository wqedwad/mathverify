"""C09 definite_integral: the claim is compared with the tanh-sinh value at rel_tol >= 1e-25 even when
the value is exact, so near-equal constants pass (rule 4). Ground truth: exact integrals below."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    exact = sp.integrate(sp.exp(x), (x, 0, sp.pi*sp.sqrt(163)))
    print("   exact int_0^{pi sqrt163} e^x dx - 262537412640768743 =", sp.N(exact - 262537412640768743, 20))
    assert sp.integrate(x**2, (x, 0, 1)) != sp.Rational(1, 3) + sp.Rational(1, 10**30)
    DI = lambda g, a, b: IR("definite_integral", {"integrand": g, "var": "x", "a": a, "b": b})
    check("int_0^{pi sqrt163} e^x dx = 262537412640768743", DI("exp(x)", "0", "pi*sqrt(163)"), SOL("value", "262537412640768743"), "CORRECT")
    check("int_0^1 x^2 dx = 1/3 + 10^-30", DI("x**2", "0", "1"), SOL("value", "1/3 + 10**(-30)"), "CORRECT")
