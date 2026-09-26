"""H01 SymPy derivatives of Abs/sign contain DiracDelta, which lambdify cannot evaluate; random-point
equality treats that side as undefined and REFUTES a correct expression.
Ground truth: d2/dx2 (x|x|) = 2 sign(x) for x != 0; d/dx(-1/x + sign(x)) = 1/x^2 for x != 0."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    for t in (sp.Rational(-3, 2), sp.Rational(7, 5)):
        assert sp.diff(x*sp.Abs(x), x, 2).subs(x, t) == 2*sp.sign(t)
    check("d2/dx2 x|x| = 2*sign(x)", IR("derivative", {"f": "x*Abs(x)", "var": "x", "order": 2}), SOL("expression", "2*sign(x)"), "INCORRECT")
    check("int 1/x^2 dx = -1/x + sign(x)", IR("antiderivative", {"integrand": "1/x**2", "var": "x"}), SOL("expression", "-1/x + sign(x)"), "INCORRECT")
