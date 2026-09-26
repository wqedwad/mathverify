from h import *
def CF(rec, initial, **kw):
    p = {"recurrence": rec, "initial": initial, "var": "n"}; p.update(kw)
    return ir("closed_form", p, vars=[{"name": "n", "domain": "positive_integer"}], answer_shape="expression")
if __name__ == "__main__":
    c = CF("a(n) = a(n-1) + 3", {"1": "2"})
    run("arith_ok", c, sol("3*n - 1", "expression"), "CORRECT", show=True)
    run("arith_ok2", c, sol("3*(n-1) + 2", "expression"), "CORRECT")
    c2 = CF("a(n) = a(n-1) + n", {"1": "1"})
    run("tri_ok", c2, sol("n*(n+1)/2", "expression"), "CORRECT", show=True)
    c3 = CF("a(n) = 2*a(n-1)", {"1": "3"})
    run("geo_ok", c3, sol("3*2**(n-1)", "expression"), "CORRECT", show=True)
    # no vars declared
    c4 = ir("closed_form", {"recurrence": "a(n) = a(n-1) + 3", "initial": {"1": "2"}, "var": "n"}, answer_shape="expression")
    run("arith_novars", c4, sol("3*n - 1", "expression"), "CORRECT", show=True)
    # wrong closed form from n = 22 on: via Mod
    run("arith_mod", c, sol("3*n - 1 + 3*floor(n/22)", "expression"), "INCORRECT", show=True)
    c5 = CF("a(n) = 2*a(n-1)", {"1": "3"})
    run("geo_floor", c5, sol("3*2**(n-1) + floor(n/23)", "expression"), "INCORRECT", show=True)
