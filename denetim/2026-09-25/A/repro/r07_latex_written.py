"""LaTeX-written problem expressions: parse_as_written returns None for LaTeX, so no written-definedness is
added and latex2sympy's auto-simplified expression is used (x/x -> 1, x^2/x -> x, (sqrt x)^2 -> x)."""
from _r import show
if __name__ == "__main__":
    print("GT: x/x and x^2/x are undefined at 0 (domain R\\{0}); x^2/x = 0 has no solution; (sqrt x)^2 = -1 has no real solution")
    S = lambda k, p: {"claimed_answer": {"kind": k, "payload": p}, "steps": []}
    show("domain \\frac{x}{x} -> R", {"task": {"kind": "domain_of", "params": {"expr": "\\frac{x}{x}", "var": "x"}}, "vars": [{"name": "x"}], "givens": []}, S("interval", "(-oo, oo)"), False)
    show("domain \\frac{x}{x} -> R\\{0} (right)", {"task": {"kind": "domain_of", "params": {"expr": "\\frac{x}{x}", "var": "x"}}, "vars": [{"name": "x"}], "givens": []}, S("interval", "(-oo, 0) U (0, oo)"), True)
    show("solve \\frac{x^{2}}{x} = 0 -> {0}", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["\\frac{x^{2}}{x} = 0"]}, S("set", "{0}"), False)
    show("solve (\\sqrt{x})^2 = -1 -> {-1}", {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["\\left(\\sqrt{x}\\right)^{2} = -1"]}, S("set", "{-1}"), False)
    show("ineq \\frac{x}{x} > 0 -> R", {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": ["\\frac{x}{x} > 0"]}, S("interval", "(-oo, oo)"), False)
    show("evaluate \\frac{x}{x} with x = 0 -> 1", {"task": {"kind": "evaluate", "params": {"expr": "\\frac{x}{x}"}}, "vars": [{"name": "x"}], "givens": ["x = 0"]}, S("value", "1"), False)
    show("count_roots \\frac{x^{3}}{x} -> 1", {"task": {"kind": "count_roots", "params": {"expr": "\\frac{x^{3}}{x}", "var": "x"}}, "vars": [{"name": "x"}], "givens": []}, S("count", 1), False)
