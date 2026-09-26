"""eq steps under inequality premises are checked only on ~60 random points: wrong endpoint strictness and
near-boundary bounds are never refuted (D-cell: wrong step, right answer -> CORRECT)."""
from _r import show
if __name__ == "__main__":
    st = lambda i, c: {"id": f"s{i}", "kind": "eq", "claim": c, "from": [], "text": ""}
    print("GT: x=-2 satisfies x**2-5x-14<=0 but not '-2 < x';  x=3 satisfies x-3>=0 but not 'x-3>0';  x=1.41 satisfies x**2<2 but not 'x<1.4';  x=3 is in (-2,3] so 'x != 3' is false there")
    show("step '-2 < x' for x**2-5x-14 <= 0", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 - 5*x - 14 <= 0"]},
         {"claimed_answer": {"kind": "interval", "payload": "[-2, 7]"}, "steps": [st(1, "-2 < x"), st(2, "x <= 7")]}, False)
    show("step 'x - 3 > 0' for domain of sqrt(x-3)", {"task": {"kind": "domain_of", "params": {"expr": "sqrt(x - 3)", "var": "x"}}, "vars": [{"name": "x"}], "givens": []},
         {"claimed_answer": {"kind": "interval", "payload": "[3, oo)"}, "steps": [st(1, "x - 3 > 0")]}, False)
    show("step 'x < 1.4' for x**2 < 2", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["x**2 < 2"]},
         {"claimed_answer": {"kind": "interval", "payload": "(-sqrt(2), sqrt(2))"}, "steps": [st(1, "x < 1.4")]}, False)
    show("step 'x != 3' for (x-3)/(x+2) <= 0", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["(x - 3)/(x + 2) <= 0"]},
         {"claimed_answer": {"kind": "interval", "payload": "(-2, 3]"}, "steps": [st(1, "x != 3")]}, False)
