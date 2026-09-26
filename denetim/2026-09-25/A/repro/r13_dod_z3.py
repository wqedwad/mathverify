"""solve_equation with domain_of_discourse: certify.wordproblem (z3) ignores ir.domain_of_discourse and reports
'missing_root' for roots outside it; certify.algebra's Sturm count uses the CLOSED [inf, sup] of an open domain
and cannot certify completeness when a root sits on the open end -> the correct answer is refuted."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    print("GT: x**3 = x on x > 0:", sp.solveset(sp.Eq(x**3, x), x, sp.Interval.open(0, sp.oo)), "; x**2 = 4 on x > 0:", sp.solveset(sp.Eq(x**2, 4), x, sp.Interval.open(0, sp.oo)))
    base = lambda eq, dod: {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": [eq], "domain_of_discourse": dod}
    S = lambda p: {"claimed_answer": {"kind": "set", "payload": p}, "steps": []}
    show("x**3 = x, x > 0 -> {1} (right)", base("x**3 = x", "x > 0"), S("{1}"), True)
    show("x**2 = 4, x > 0 -> {2} (right)", base("x**2 = 4", "x > 0"), S("{2}"), True)
    show("x**3 = x, x >= 0 -> {0, 1} (right)", base("x**3 = x", "x >= 0"), S("{0, 1}"), True)
