"""ir.functions bodies are parsed with SymPy auto-simplification and are NOT part of the written-definedness
sources (Ctx.written_conditions), so x**2/x, sqrt(x)**2, x/x, log(x)-log(x) lose their undefined points."""
from _r import show
if __name__ == "__main__":
    F = lambda body: [{"name": "f", "expr": body, "args": ["x"], "params": []}]
    print("GT: f(x)=x**2/x is undefined at 0 and equals x elsewhere -> f(x)=0 has NO solution; domain R\\{0}; f(0) undefined")
    print("GT: f(x)=x/x equals 1 for x != 0 -> f(x) > 0 on R\\{0}; f(x)=sqrt(x)**2 needs x>=0 -> f(x)=-1 has no solution")
    base = lambda kind, params, fb, givens=(): {"task": {"kind": kind, "params": params}, "vars": [{"name": "x"}], "givens": list(givens), "functions": F(fb)}
    S = lambda k, p: {"claimed_answer": {"kind": k, "payload": p}, "steps": []}
    show("solve f(x)=0, f=x**2/x -> {0}", base("solve_equation", {"var": "x"}, "x**2/x", ["f(x) = 0"]), S("set", "{0}"), False)
    show("solve f(x)=0, f=x**2/x -> {} (right)", base("solve_equation", {"var": "x"}, "x**2/x", ["f(x) = 0"]), S("set", "{}"), True)
    show("solve f(x)=-1, f=sqrt(x)**2 -> {-1}", base("solve_equation", {"var": "x"}, "sqrt(x)**2", ["f(x) = -1"]), S("set", "{-1}"), False)
    show("ineq f(x)>0, f=x/x -> R", base("solve_inequality", {"var": "x"}, "x/x", ["f(x) > 0"]), S("interval", "(-oo, oo)"), False)
    show("domain of f, f=x**2/x -> R", base("domain_of", {"expr": "f(x)", "var": "x"}, "x**2/x"), S("interval", "(-oo, oo)"), False)
    show("domain of f, f=x**2/x -> R\\{0} (right)", base("domain_of", {"expr": "f(x)", "var": "x"}, "x**2/x"), S("interval", "(-oo, 0) U (0, oo)"), True)
    show("count_roots f, f=x**2/x -> 1", base("count_roots", {"expr": "f(x)", "var": "x"}, "x**2/x"), S("count", 1), False)
    show("evaluate f(0), f=x**2/x -> 0", {"task": {"kind": "evaluate", "params": {"expr": "f(0)"}}, "vars": [], "givens": [], "functions": F("x**2/x")}, S("value", "0"), False)
    show("evaluate f(-1), f=log(x)-log(x)+x -> -1", {"task": {"kind": "evaluate", "params": {"expr": "f(-1)"}}, "vars": [], "givens": [], "functions": F("log(x) - log(x) + x")}, S("value", "-1"), False)
