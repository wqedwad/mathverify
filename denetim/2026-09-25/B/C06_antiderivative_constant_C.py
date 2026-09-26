"""C06 antiderivative: the constant C is replaced by 0 before the certificate, so any family that
contains a correct antiderivative at C = 0 passes. Ground truth: d/dx(sin x + C x) = cos x + C,
d/dx sin(x + C) = cos(x + C), d/dx (1+C) sin x = (1+C) cos x; none equals cos x for C != 0."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x, C = sp.symbols("x C", real=True)
    for F in (sp.sin(x) + C*x, sp.sin(x + C), (1 + C)*sp.sin(x)):
        print("   d/dx", F, "- cos x at C=1:", sp.simplify((sp.diff(F, x) - sp.cos(x)).subs(C, 1)))
    A = IR("antiderivative", {"integrand": "cos(x)", "var": "x"})
    check("int cos = sin(x) + C*x", A, SOL("expression", "sin(x) + C*x"), "CORRECT")
    check("int cos = sin(x + C)", A, SOL("expression", "sin(x + C)"), "CORRECT")
    check("int cos = (1 + C)*sin(x)", A, SOL("expression", "(1 + C)*sin(x)"), "CORRECT")
