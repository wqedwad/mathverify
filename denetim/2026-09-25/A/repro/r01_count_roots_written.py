"""count_roots ignores the problem expression's written definedness (and counts 0 for the zero polynomial)."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    # ground truth: as written, x**3/x is undefined at 0, and x**3/x = x**2 vanishes only at 0 -> no real root
    num, den = sp.Symbol("n"), None
    print("GT: roots of x**2 (simplified) =", sp.solveset(x**2, x, sp.S.Reals), "; x=0 makes the written denominator x zero -> 0 roots")
    show("x**3/x has 1 root", {"task": {"kind": "count_roots", "params": {"expr": "x**3/x", "var": "x"}}, "vars": [{"name": "x"}], "givens": []},
         {"claimed_answer": {"kind": "count", "payload": 1}, "steps": []}, False)
    show("x**3/x has 0 roots", {"task": {"kind": "count_roots", "params": {"expr": "x**3/x", "var": "x"}}, "vars": [{"name": "x"}], "givens": []},
         {"claimed_answer": {"kind": "count", "payload": 0}, "steps": []}, True)
    print("GT: (x+2)**2/(x+2): only candidate -2 kills the denominator -> 0 roots; sqrt(x)**2+1: candidate -1 has sqrt(-1) -> 0 roots")
    for e in ["(x + 2)**2/(x + 2)", "sqrt(x)**2 + 1"]:
        show(f"{e} has 1 root", {"task": {"kind": "count_roots", "params": {"expr": e, "var": "x"}}, "vars": [{"name": "x"}], "givens": []},
             {"claimed_answer": {"kind": "count", "payload": 1}, "steps": []}, False)
    e = "(x + 1)**2 - x**2 - 2*x - 1"
    print("GT:", e, "expands to", sp.expand((x + 1)**2 - x**2 - 2*x - 1), "-> every real x is a root (infinitely many)")
    show("identically-zero expression has 0 roots", {"task": {"kind": "count_roots", "params": {"expr": e, "var": "x"}}, "vars": [{"name": "x"}], "givens": []},
         {"claimed_answer": {"kind": "count", "payload": 0}, "steps": []}, False)
