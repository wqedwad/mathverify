"""Odd roots of negatives: definedness_conditions (and z3) treat x**(1/3) as defined for x < 0 (real cube
root), but values are computed with SymPy's principal complex branch. Result: x**(1/3) + 2 = 0 is certified to
have no solution, and the school answers cbrt(-8) = -2, x**(1/3) < 1 <=> x < 1 are refuted."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    print("GT (real cube root, TR curriculum): cbrt(-8) =", sp.real_root(-8, 3), "; x^(1/3) + 2 = 0 <=> x = -8; x^(1/3) < 1 <=> x < 1")
    print("   SymPy principal: (-8)**(1/3) =", sp.N((-8)**sp.Rational(1, 3)))
    S = lambda k, p: {"claimed_answer": {"kind": k, "payload": p}, "steps": []}
    show("x**(1/3) + 2 = 0 -> {}", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**(1/3) + 2 = 0"]}, S("set", "{}"), False)
    show("evaluate cbrt(-8) = -2 (right)", {"task": {"kind": "evaluate", "params": {"expr": "cbrt(-8)"}}, "vars": [], "givens": []}, S("value", "-2"), True)
    show("x**(1/3) < 1 -> (-oo, 1) (right)", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**(1/3) < 1"]}, S("interval", "(-oo, 1)"), True)
    show("cbrt(x) < -1 -> (-oo, -1) (right)", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["cbrt(x) < -1"]}, S("interval", "(-oo, -1)"), True)
