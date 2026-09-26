"""C03 limit: SymPy returns 1 for lim_{x->oo} |sin x|^(1/x); the 10^12 numeric probe agrees.
Ground truth: f(k*pi) = 0 for every integer k (sin(k*pi) = 0 exactly) and f(k*pi + pi/2) = 1,
so the limit does not exist."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    k = sp.Symbol("k", integer=True, positive=True)
    assert sp.Abs(sp.sin(k*sp.pi))**(1/(k*sp.pi)) == 0
    assert sp.Abs(sp.sin(k*sp.pi + sp.pi/2))**(1/(k*sp.pi + sp.pi/2)) == 1
    check("lim_{x->oo} |sin x|^(1/x) = 1", IR("limit", {"expr": "Abs(sin(x))**(1/x)", "var": "x", "to": "oo"}), SOL("value", "1"), "CORRECT")
    check("lim_{x->0+} |sin(1/x)|^x = 1", IR("limit", {"expr": "Abs(sin(1/x))**x", "var": "x", "to": "0", "side": "+"}), SOL("value", "1"), "CORRECT")
    check("lim_{x->oo} |sin x|^(1/x) does not exist (right answer)", IR("limit", {"expr": "Abs(sin(x))**(1/x)", "var": "x", "to": "oo"}), SOL("dne", None), "INCORRECT")
