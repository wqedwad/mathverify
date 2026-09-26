from common import *
import sympy as sp
x = sp.Symbol("x", real=True)

def cr(expr, claim, truth_ok, **extra):
    p = {"expr": expr, "var": "x"}; p.update(extra)
    return run(f"count_roots[{expr}|{extra}]={claim}", ir("count_roots", p, shape="count"), sol("count", claim), truth_ok)

if __name__ == "__main__":
    # --- count_roots: auto-simplified undefined points
    # x**3/x is undefined at 0; as written it has no real root (x^2 = 0 only at x = 0).
    cr("x**3/x", 1, False); cr("x**3/x", 0, True)
    # (x+2)**2/(x+2) -> x+2 ; root -2 undefined as written -> 0 roots
    cr("(x+2)**2/(x+2)", 1, False); cr("(x+2)**2/(x+2)", 0, True)
    # sqrt(x)**2 + 1 -> x + 1 ; root -1 but sqrt(-1) undefined -> 0 roots
    cr("sqrt(x)**2 + 1", 1, False); cr("sqrt(x)**2 + 1", 0, True)
    # (x-1)*(x-2)/(x-2): root 1 only (2 undefined); SymPy -> x-1: 1 root -> correct either way
    cr("(x-1)*(x-2)/(x-2)", 1, True)
    # x*(x-1)/x -> x-1 ; root 1 ; fine
    # x**2*(x-1)/x -> x*(x-1): roots 0,1 but 0 undefined -> 1 root
    cr("x**2*(x-1)/x", 2, False); cr("x**2*(x-1)/x", 1, True)
    # multiplicity
    cr("(x-1)**2*(x+1)", 2, True); cr("(x-1)**2*(x+1)", 3, False)
    cr("(x-1)**2*(x+1)", 3, True, distinct=False); cr("(x-1)**2*(x+1)", 2, False, distinct=False)
    # interval restriction
    cr("x**2 - 1", 1, True, lo="0", hi="oo"); cr("x**2 - 1", 2, False, lo="0", hi="oo")
    cr("x**3 - x", 3, True, lo="-1", hi="1")
    # non-integer claim
    cr("x**2-1", 2.0, True); cr("x**2-1", 2.5, False); cr("x**2-1", "2", True)
    # float claim 2.9999999999
    cr("x**2-1", 1.9999999999999999, False, note="") if False else None
    # log
    cr("log(x)", 1, True)
    # rational function
    cr("(x**2-1)/(x-1)", 1, True)
    cr("x**4 + 1", 0, True)
    cr("x**5 - 3*x**3 + x + 1", 3, True)
    cr("x**5 - 3*x**3 + x + 1", 2, False)
    # x/x - 1 : auto-simplified 0 -> Poly(0) -> count? as written: x/x - 1 = 0 for all x != 0 -> infinitely many
    cr("x/x - 1", 0, False)
    cr("x - x", 0, False)
    cr("0*x", 0, False)
    summary()
