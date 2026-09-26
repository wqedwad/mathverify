"""Same 1e-70 relative tolerance inside solve_equation's root guard and set comparison: a claimed root that is
off by 10**-80 is accepted as the exact root."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    r = sp.sqrt(2) + sp.Rational(1, 10**80)
    print("GT: (sqrt(2) + 10**-80)**2 - 2 =", sp.expand(r**2 - 2), "!= 0 -> not a root of x**2 = 2")
    show("x**2 = 2 -> {-sqrt(2), sqrt(2) + 10**(-80)}", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 = 2"]},
         {"claimed_answer": {"kind": "set", "payload": "{-sqrt(2), sqrt(2) + 10**(-80)}"}, "steps": []}, False)
    show("x**2 < 2 -> (-sqrt(2), sqrt(2) + 10**(-80))", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 < 2"]},
         {"claimed_answer": {"kind": "interval", "payload": "(-sqrt(2), sqrt(2) + 10**(-80))"}, "steps": []}, False)
    show("domain sqrt(2 - x**2) -> [-sqrt(2), sqrt(2) - 10**(-80)]", {"task": {"kind": "domain_of", "params": {"expr": "sqrt(2 - x**2)", "var": "x"}}, "vars": [{"name": "x"}], "givens": []},
         {"claimed_answer": {"kind": "interval", "payload": "[-sqrt(2), sqrt(2) - 10**(-80)]"}, "steps": []}, False)
