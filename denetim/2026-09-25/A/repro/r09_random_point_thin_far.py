"""Expression equivalence by random points: samples |x| <= 1000 (integers in [-60, 60]) with 6-decimal
rationals, so measure-zero exceptions (integers) and far regions (x > 1000) are never visited."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    print("GT: floor(2)+floor(-2) =", sp.floor(2) + sp.floor(-2), "(not -1);  ceiling(3)-floor(3) =", sp.ceiling(3) - sp.floor(3), ";  sign(0)**2 =", sp.sign(0)**2)
    print("GT: |x-2025|+|x+2025| at x=3000:", abs(3000 - 2025) + abs(3000 + 2025), "(not 4050);  Max(5000,1001) = 5000")
    SX = lambda e, v=None: {"task": {"kind": "simplify_expression", "params": {"expr": e}}, "vars": v or [{"name": "x"}], "givens": []}
    S = lambda p: {"claimed_answer": {"kind": "expression", "payload": p}, "steps": []}
    show("floor(x) + floor(-x) = -1", SX("floor(x) + floor(-x)"), S("-1"), False)
    show("ceiling(x) - floor(x) = 1", SX("ceiling(x) - floor(x)"), S("1"), False)
    show("sign(x)**2 = 1", SX("sign(x)**2"), S("1"), False)
    show("|x - 2025| + |x + 2025| = 4050", SX("Abs(x - 2025) + Abs(x + 2025)"), S("4050"), False)
    show("Max(x, 1001) = 1001", SX("Max(x, 1001)"), S("1001"), False)
    show("Min(n, 100) = n (n integer)", SX("Min(n, 100)", [{"name": "n", "domain": "integer"}]), S("n"), False)
    st = {"id": "s1", "kind": "compute", "claim": "Abs(x - 2025) + Abs(x + 2025) = 4050", "from": [], "text": ""}
    show("D-cell: compute step |x-2025|+|x+2025| = 4050", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 - 5*x + 6 = 0"]},
         {"claimed_answer": {"kind": "set", "payload": "{2, 3}"}, "steps": [st]}, False)
