"""Relations are evaluated numerically at points where one side is EXACTLY zero; the tiny evalf residue
(+-1e-192) decides the sign. Correct roots are dropped (empty claim certified), correct inequality answers
with irrational endpoints are refuted, and a false step is verified."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    for c in [1 + sp.sqrt(2), 1 - sp.sqrt(2)]:
        print("GT: x**2-2x-1 at", c, "=", sp.expand((c)**2 - 2*c - 1), "(exactly zero)")
    print("GT: sqrt(x**2-2x-1)=0 solveset:", sp.solveset(sp.sqrt(x**2 - 2*x - 1), x, sp.S.Reals))
    print("GT: sqrt(x**2+x-1)=0 solveset:", sp.solveset(sp.sqrt(x**2 + x - 1), x, sp.S.Reals))
    for eq in ["sqrt(x**2 - 2*x - 1) = 0", "sqrt(x**2 + x - 1) = 0", "(x**2 - 2*x - 1)**(1/4) = 0"]:
        show(f"{eq} -> empty set", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": [eq]},
             {"claimed_answer": {"kind": "set", "payload": "{}"}, "steps": []}, False)
    show("sqrt(x**2 - 2*x - 1) = 0 -> {1-sqrt(2), 1+sqrt(2)} (right)", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["sqrt(x**2 - 2*x - 1) = 0"]},
         {"claimed_answer": {"kind": "set", "payload": "{1 - sqrt(2), 1 + sqrt(2)}"}, "steps": []}, True)
    for ineq, ans in [("x**2 - 2*x - 1 < 0", "(1 - sqrt(2), 1 + sqrt(2))"), ("x**2 - x - 1 < 0", "((1 - sqrt(5))/2, (1 + sqrt(5))/2)"),
                      ("x**2 - 4*x - 1 < 0", "(2 - sqrt(5), 2 + sqrt(5))"), ("x**2 - 2*x - 1 >= 0", "(-oo, 1 - sqrt(2)] U [1 + sqrt(2), oo)")]:
        rel = sp.sympify(ineq, locals={"x": x})
        print("GT:", ineq, "solveset ->", sp.solveset(rel, x, sp.S.Reals))
        show(f"{ineq} -> {ans} (right)", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": [ineq]},
             {"claimed_answer": {"kind": "interval", "payload": ans}, "steps": []}, True)
    step = lambda i, c: {"id": f"s{i}", "kind": "eq", "claim": c, "from": [], "text": ""}
    show("D-cell: false step 'x**2 - 2*x - 1 < 0' under x**2-2x-1=0", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 - 2*x - 1 = 0"]},
         {"claimed_answer": {"kind": "set", "payload": "{1 - sqrt(2), 1 + sqrt(2)}"}, "steps": [step(1, "x**2 - 2*x - 1 < 0"), step(2, "x in {1 - sqrt(2), 1 + sqrt(2)}")]}, False)
    show("true step 'x**2 - 2*x - 1 >= 0' under x**2-2x-1=0", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 - 2*x - 1 = 0"]},
         {"claimed_answer": {"kind": "set", "payload": "{1 - sqrt(2), 1 + sqrt(2)}"}, "steps": [step(1, "x**2 - 2*x - 1 >= 0"), step(2, "x in {1 - sqrt(2), 1 + sqrt(2)}")]}, True)
