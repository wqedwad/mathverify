from common import *

F_x2x = [{"name": "f", "expr": "x**2/x", "args": ["x"], "params": []}]
F_sq = [{"name": "f", "expr": "sqrt(x)**2", "args": ["x"], "params": []}]
F_xx = [{"name": "f", "expr": "x/x", "args": ["x"], "params": []}]
F_rat = [{"name": "f", "expr": "(x**2 - 1)/(x - 1)", "args": ["x"], "params": []}]
F_log = [{"name": "f", "expr": "log(x) - log(x) + x", "args": ["x"], "params": []}]
F_ok = [{"name": "f", "expr": "(2*x + 3)/(x - 1)", "args": ["x"], "params": []}]

def R(name, kind, params, functions, claim_kind, payload, truth_ok, givens=None):
    return run(name, ir(kind, params, functions=functions, givens=givens or []), sol(claim_kind, payload), truth_ok)

if __name__ == "__main__":
    # solve_equation with the problem's own function
    R("fn solve f=x^2/x: f(x)=0 -> {0}", "solve_equation", {"var": "x"}, F_x2x, "set", "{0}", False, ["f(x) = 0"])
    R("fn solve f=x^2/x: f(x)=0 -> {}", "solve_equation", {"var": "x"}, F_x2x, "set", "{}", True, ["f(x) = 0"])
    R("fn solve f=sqrt(x)^2: f(x)=-1 -> {-1}", "solve_equation", {"var": "x"}, F_sq, "set", "{-1}", False, ["f(x) = -1"])
    R("fn solve f=(x2-1)/(x-1): f(x)=2 -> {1}", "solve_equation", {"var": "x"}, F_rat, "set", "{1}", False, ["f(x) = 2"])
    R("fn solve f=(x2-1)/(x-1): f(x)=2 -> {}", "solve_equation", {"var": "x"}, F_rat, "set", "{}", True, ["f(x) = 2"])
    R("fn solve f=log-log+x: f(x)=-1 -> {-1}", "solve_equation", {"var": "x"}, F_log, "set", "{-1}", False, ["f(x) = -1"])
    # inequality
    R("fn ineq f=x/x: f(x)>0 -> R", "solve_inequality", {"var": "x"}, F_xx, "interval", "(-oo, oo)", False, ["f(x) > 0"])
    R("fn ineq f=sqrt(x)^2: f(x)<1 -> (-oo,1)", "solve_inequality", {"var": "x"}, F_sq, "interval", "(-oo, 1)", False, ["f(x) < 1"])
    R("fn ineq f=sqrt(x)^2: f(x)<1 -> [0,1)", "solve_inequality", {"var": "x"}, F_sq, "interval", "[0, 1)", True, ["f(x) < 1"])
    # domain_of
    R("fn domain f=x^2/x: R", "domain_of", {"expr": "f(x)", "var": "x"}, F_x2x, "interval", "(-oo, oo)", False)
    R("fn domain f=x^2/x: R\\{0}", "domain_of", {"expr": "f(x)", "var": "x"}, F_x2x, "interval", "(-oo, 0) U (0, oo)", True)
    R("fn domain f=(2x+3)/(x-1): R\\{1}", "domain_of", {"expr": "f(x)", "var": "x"}, F_ok, "interval", "(-oo, 1) U (1, oo)", True)
    R("fn domain f=sqrt(x)^2: R", "domain_of", {"expr": "f(x)", "var": "x"}, F_sq, "interval", "(-oo, oo)", False)
    # count_roots
    R("fn count_roots f=x^2/x: 1", "count_roots", {"expr": "f(x)", "var": "x"}, F_x2x, "count", 1, False)
    # evaluate
    R("fn evaluate f=(x2-1)/(x-1): f(1)=2", "evaluate", {"expr": "f(1)"}, F_rat, "value", "2", False)
    R("fn evaluate f=log-log+x: f(-1)=-1", "evaluate", {"expr": "f(-1)"}, F_log, "value", "-1", False)
    R("fn evaluate f=log-log+x: f(2)=2", "evaluate", {"expr": "f(2)"}, F_log, "value", "2", True)
    # simplify
    R("fn simplify f(x)=x^2/x -> x", "simplify_expression", {"expr": "f(x)"}, F_x2x, "expression", "x", True)
    summary()
