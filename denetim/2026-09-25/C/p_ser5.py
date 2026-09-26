from h import *
def CF(rec, initial, **kw):
    p = {"recurrence": rec, "initial": initial, "var": "n"}; p.update(kw)
    return ir("closed_form", p, vars=[{"name": "n", "domain": "positive_integer"}], answer_shape="expression")
if __name__ == "__main__":
    c = CF("a(n) = 2*a(n-1)", {"1": "3"})
    run("cf_tiny_exp", c, sol("3*2**(n-1) + (n-1)*exp(-100*n)", "expression"), "INCORRECT", show=True)
    c2 = CF("a(n) = a(n-1) + a(n-2)", {"1": "1", "2": "1"})
    run("fib_binet_ok", c2, sol("(((1+sqrt(5))/2)**n - ((1-sqrt(5))/2)**n)/sqrt(5)", "expression"), "CORRECT", show=True)
    # Binet with a tiny perturbation vanishing at n=1,2
    run("fib_binet_tiny", c2, sol("(((1+sqrt(5))/2)**n - ((1-sqrt(5))/2)**n)/sqrt(5) + (n-1)*(n-2)*exp(-80*n)", "expression"), "INCORRECT", show=True)
    # rounding formula: round(phi^n/sqrt5) is correct Fibonacci
    run("fib_floor_formula", c2, sol("floor(((1+sqrt(5))/2)**n/sqrt(5) + 1/2)", "expression"), "CORRECT", show=True)
