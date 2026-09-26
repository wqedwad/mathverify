from common import *

def R(name, kind, params, claim_kind, payload, truth_ok, givens=None):
    return run(name, ir(kind, params, givens=givens or []), sol(claim_kind, payload), truth_ok)

if __name__ == "__main__":
    R("latex domain x/x -> R", "domain_of", {"expr": "\\frac{x}{x}", "var": "x"}, "interval", "(-oo, oo)", False)
    R("latex domain x/x -> R\\{0}", "domain_of", {"expr": "\\frac{x}{x}", "var": "x"}, "interval", "(-oo, 0) U (0, oo)", True)
    R("latex domain x^2/x -> R", "domain_of", {"expr": "\\frac{x^{2}}{x}", "var": "x"}, "interval", "(-oo, oo)", False)
    R("latex domain sqrt(x)^2 -> R", "domain_of", {"expr": "\\left(\\sqrt{x}\\right)^{2}", "var": "x"}, "interval", "(-oo, oo)", False)
    R("latex solve x^2/x=0 -> {0}", "solve_equation", {"var": "x"}, "set", "{0}", False, ["\\frac{x^{2}}{x} = 0"])
    R("latex solve x^2/x=0 -> {}", "solve_equation", {"var": "x"}, "set", "{}", True, ["\\frac{x^{2}}{x} = 0"])
    R("latex solve (sqrt x)^2=-1 -> {-1}", "solve_equation", {"var": "x"}, "set", "{-1}", False, ["\\left(\\sqrt{x}\\right)^{2} = -1"])
    R("latex ineq x/x>0 -> R", "solve_inequality", {"var": "x"}, "interval", "(-oo, oo)", False, ["\\frac{x}{x} > 0"])
    R("latex evaluate x/x at 0", "evaluate", {"expr": "\\frac{x}{x}"}, "value", "1", False, ["x = 0"])
    R("latex count_roots x^3/x", "count_roots", {"expr": "\\frac{x^{3}}{x}", "var": "x"}, "count", 1, False)
    R("latex solve sqrt ok", "solve_equation", {"var": "x"}, "set", "{5}", True, ["\\sqrt{x+4} = x - 2"])
    R("latex solve sqrt extraneous", "solve_equation", {"var": "x"}, "set", "{0, 5}", False, ["\\sqrt{x+4} = x - 2"])
    summary()
