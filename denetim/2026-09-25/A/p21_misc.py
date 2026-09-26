from common import *

def st(i, kind, claim, frm=None):
    return {"id": f"s{i}", "kind": kind, "claim": claim, "from": frm or [], "text": ""}

if __name__ == "__main__":
    run("ineq system x>1,x<5 -> (1,5)", ir("solve_inequality", {"var": "x"}, givens=["x > 1", "x < 5"]), sol("interval", "(1, 5)"), True)
    run("ineq system x>1,x<5 -> [1,5)", ir("solve_inequality", {"var": "x"}, givens=["x > 1", "x < 5"]), sol("interval", "[1, 5)"), False)
    run("ineq chained 1 < x < 5 -> (1,5)", ir("solve_inequality", {"var": "x"}, givens=["1 < x < 5"]), sol("interval", "(1, 5)"), True)
    run("ineq chained -> [1,5]", ir("solve_inequality", {"var": "x"}, givens=["1 < x < 5"]), sol("interval", "[1, 5]"), False)
    # D-cell: wrong strictness in domain_of step
    run("D-domain step x-3>0 (wrong) answer [3,oo)", ir("domain_of", {"expr": "sqrt(x - 3)", "var": "x"}), sol("interval", "[3, oo)", [st(1, "eq", "x - 3 > 0")]), False)
    run("D-domain step x-3>=0 (right)", ir("domain_of", {"expr": "sqrt(x - 3)", "var": "x"}), sol("interval", "[3, oo)", [st(1, "eq", "x - 3 >= 0")]), True)
    run("D-ineq step -2<x (wrong strictness) for <=0", ir("solve_inequality", {"var": "x"}, givens=["x**2 - 5*x - 14 <= 0"]), sol("interval", "[-2, 7]", [st(1, "eq", "-2 < x"), st(2, "eq", "x <= 7")]), False)
    # evaluate expression-shaped with thin exception
    run("evaluate expr floor(x)+floor(-x) = -1", ir("evaluate", {"expr": "floor(x) + floor(-x)"}), sol("value", "-1"), False)
    # count_integers with a system of givens (coverage)
    run("count_integers system 1<x<5", ir("count_integers", {"var": "x"}, vars_=[{"name": "x", "domain": "integer"}], givens=["x > 1", "x < 5"]), sol("count", 3), True)
    summary()
