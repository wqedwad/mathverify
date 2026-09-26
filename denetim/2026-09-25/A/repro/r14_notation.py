"""Equivalent notations refuted: relation form, 'x ∈ S' (Python `in` evaluates to False), bare 'a, b',
Turkish decimal comma, and the Turkish option text 'Çözüm yok' for an empty solution set."""
from _r import show
if __name__ == "__main__":
    SE = lambda eq, opts=None: dict({"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": [eq]}, **({"options": opts} if opts else {}))
    SI = lambda q: {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}], "givens": [q]}
    S = lambda k, p, o=None: {"claimed_answer": dict({"kind": k, "payload": p}, **({"option": o} if o else {})), "steps": []}
    print("GT: log(x-1)+log(x-3)=log 3 -> {4};  x**2-5x+6=0 -> {2,3};  x**2-5x-14<0 -> (-2,7);  x>=3 -> [3,oo);  5/2 = 2,5 (TR decimal comma)")
    show("'x ∈ {4}'", SE("log(x - 1) + log(x - 3) = log(3)"), S("set", "x ∈ {4}"), True)
    show("'2, 3'", SE("x**2 - 5*x + 6 = 0"), S("set", "2, 3"), True)
    show("'x ∈ (-2, 7)'", SI("x**2 - 5*x - 14 < 0"), S("interval", "x ∈ (-2, 7)"), True)
    show("'x >= 3' (interval)", SI("x >= 3"), S("interval", "x >= 3"), True)
    show("'x >= 3' (condition)", SI("x >= 3"), S("condition", "x >= 3"), True)
    show("domain sqrt(x): 'x >= 0'", {"task": {"kind": "domain_of", "params": {"expr": "sqrt(x)", "var": "x"}}, "vars": [{"name": "x"}], "givens": []}, S("interval", "x >= 0"), True)
    show("evaluate 5/2 = '2,5'", {"task": {"kind": "evaluate", "params": {"expr": "5/2"}}, "vars": [], "givens": []}, S("value", "2,5"), True)
    opts = {"A": "{1}", "B": "{2}", "C": "{1, 2}", "D": "{3}", "E": "Çözüm yok"}
    show("∅ with option E 'Çözüm yok'", SE("x/(x - 3) = 3/(x - 3) + 2", opts), S("set", "{}", "E"), True)
    show("kind none with option E 'Çözüm yok'", SE("x/(x - 3) = 3/(x - 3) + 2", opts), S("none", None, "E"), True)
