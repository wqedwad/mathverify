"""H02 definite_integral: a numeric value that did NOT converge (evidence converged=False, rel_err up
to 0.8) still produces a hard 0.99 refutation, even when SymPy's exact integral equals the claim.
Ground truth: exact antiderivatives below."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    assert sp.integrate(x**sp.Rational(-999, 1000), (x, 0, 1)) == 1000
    assert sp.simplify(sp.integrate(2*x*sp.sin(x**2), (x, 0, 100)) - (1 - sp.cos(10000))) == 0
    assert sp.simplify(sp.diff(x**2*sp.sin(1/x), x) - (2*x*sp.sin(1/x) - sp.cos(1/x))) == 0   # int_0^1 = sin(1)
    DI = lambda g, a, b: IR("definite_integral", {"integrand": g, "var": "x", "a": a, "b": b})
    check("int_0^1 x^(-999/1000) = 1000", DI("x**(-999/1000)", "0", "1"), SOL("value", "1000"), "INCORRECT")
    check("int_0^100 2x sin(x^2) = 1 - cos(10000)", DI("2*x*sin(x**2)", "0", "100"), SOL("value", "1 - cos(10000)"), "INCORRECT")
    check("int_0^1 (2x sin(1/x) - cos(1/x)) = sin(1)", DI("2*x*sin(1/x) - cos(1/x)", "0", "1"), SOL("value", "sin(1)"), "INCORRECT")
    check("int_0^1 1/x = oo (diverges to +oo)", DI("1/x", "0", "1"), SOL("value", "oo"), "INCORRECT")
