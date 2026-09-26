"""solve_equation: an identity (every real x solves it) is certified to have the EMPTY solution set."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    for eq, lhs, rhs in [("(x + 1)**2 = x**2 + 2*x + 1", (x + 1)**2, x**2 + 2*x + 1), ("2*(x + 3) = 2*x + 6", 2*(x + 3), 2*x + 6),
                         ("(x**2 - 1)/(x - 1) = x + 1", (x**2 - 1)/(x - 1), x + 1), ("x/x = 1", sp.Symbol("t"), sp.Symbol("t"))]:
        print("GT:", eq, "solveset ->", sp.solveset(sp.Eq(lhs, rhs, evaluate=False), x, sp.S.Reals) if eq != "x/x = 1" else "R \\ {0} (x/x = 1 for every x != 0)")
        show(f"{eq} has no solution", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": [eq]},
             {"claimed_answer": {"kind": "set", "payload": "{}"}, "steps": []}, False)
    show("2*(x + 3) = 2*x + 6 -> R (right answer)", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["2*(x + 3) = 2*x + 6"]},
         {"claimed_answer": {"kind": "set", "payload": "Reals"}, "steps": []}, True)
