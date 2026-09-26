"""C02 limit: SymPy's AccumBounds arithmetic loses correlation, so an expression that is
identically constant is classified DNE. Ground truth: sin^2+cos^2 == 1, sin x cos x - sin(2x)/2 == 0,
floor(x) - x + frac(x) == 0 for every real x (checked below)."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    assert sp.simplify(sp.sin(x)**2 + sp.cos(x)**2 - 1) == 0
    assert sp.simplify(sp.sin(x)*sp.cos(x) - sp.sin(2*x)/2) == 0
    assert all(sp.floor(t) - t + sp.frac(t) == 0 for t in (sp.Rational(7, 3), sp.Rational(-5, 2), sp.pi, 10**6 + sp.Rational(1, 7)))
    L = lambda e, to: IR("limit", {"expr": e, "var": "x", "to": to})
    check("lim_{x->oo} sin^2+cos^2 'does not exist'", L("sin(x)**2 + cos(x)**2", "oo"), SOL("dne", None), "CORRECT")
    check("lim_{x->0} sin(1/x)^2+cos(1/x)^2 'does not exist'", L("sin(1/x)*sin(1/x) + cos(1/x)**2", "0"), SOL("dne", None), "CORRECT")
    check("lim_{x->oo} floor(x)-x+frac(x) 'does not exist'", L("floor(x) - x + frac(x)", "oo"), SOL("dne", None), "CORRECT")
    check("lim_{x->oo} sin(x)cos(x)-sin(2x)/2 'does not exist'", L("sin(x)*cos(x) - sin(2*x)/2", "oo"), SOL("dne", None), "CORRECT")
    # right answers refuted
    check("lim_{x->oo} sin^2+cos^2 = 1", L("sin(x)**2 + cos(x)**2", "oo"), SOL("value", "1"), "INCORRECT")
    # sign(AccumBounds) is treated as a finite VALUE: the right 'dne' is refuted
    check("lim_{x->oo} sign(sin x) does not exist", L("sign(sin(x))", "oo"), SOL("dne", None), "INCORRECT")
    check("lim_{x->oo} floor(sin x) does not exist", L("floor(sin(x))", "oo"), SOL("dne", None), "INCORRECT")
