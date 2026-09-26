from h import *
def R(rec, initial, index, **kw):
    p = {"recurrence": rec, "initial": initial, "index": index, "var": "n"}; p.update(kw)
    return ir("recurrence_term", p, vars=[{"name": "n", "domain": "positive_integer"}])
def CF(rec, initial, **kw):
    p = {"recurrence": rec, "initial": initial, "var": "n"}; p.update(kw)
    return ir("closed_form", p, vars=[{"name": "n", "domain": "positive_integer"}], answer_shape="expression")
if __name__ == "__main__":
    r = R("a(n) = a(n-1) + 2*a(n-2)", {"1": "1", "2": "3"}, 6)
    run("rt_ok", r, sol("43"), "CORRECT")
    run("rt_wrong", r, sol("21"), "INCORRECT")
    r0 = R("a(n) = a(n-1) + a(n-2)", {"0": "0", "1": "1"}, 10)
    run("fib10", r0, sol("55"), "CORRECT")
    run("fib10_off", r0, sol("34"), "INCORRECT")
    # forward-shift form (common): a(n+1) = 2 a(n) + 1, a(1) = 1 -> a(5) = 31
    rf = R("a(n+1) = 2*a(n) + 1", {"1": "1"}, 5)
    run("fwd_shift", rf, sol("31"), "CORRECT", show=True)
    # nonlinear: a(n)^2 = 4 a(n-1), a(1)=4 : positive branch a(n)=4 always
    rn = R("a(n)**2 = 4*a(n-1)", {"1": "4"}, 3)
    run("nonlin_pos", rn, sol("4"), None, show=True)
    run("nonlin_neg", rn, sol("-4*I"), None, show=True)
    # written-undefined recurrence: (n-3)/(n-3) cancels at parse time; a(3) does not exist as written
    ru = R("a(n) = a(n-1)*(n-3)/(n-3) + 1", {"1": "1"}, 5)
    run("undef_written", ru, sol("5"), "UNKNOWN", show=True)
    ru2 = R("a(n) = a(n-1) + 1/(n-3)", {"1": "1"}, 5)
    run("undef_zoo", ru2, sol("5"), "UNKNOWN", show=True)
    # closed form: correct
    c = CF("a(n) = a(n-1) + 2", {"1": "2"})
    run("cf_ok", c, sol("2*n", "expression"), "CORRECT")
    run("cf_wrong", c, sol("2*n + 1", "expression"), "INCORRECT")
    # closed form wrong only from n=22 on (binomial vanishes for n-1<21)
    run("cf_binom21", c, sol("2*n + binomial(n - 1, 21)", "expression"), "INCORRECT", show=True)
    run("cf_floor25", c, sol("2*n + floor(n/25)", "expression"), "INCORRECT", show=True)
    run("cf_prod", c, sol("2*n + factorial(n-1)*0", "expression"), "CORRECT")
    run("cf_poly22", c, sol("2*n + " + "*".join(f"(n-{j})" for j in range(1, 22)), "expression"), "INCORRECT", show=True)
    # recurrence valid from n>=3 only, a(2) given explicitly (does not follow recurrence)
    c3 = CF("a(n) = a(n-1) + 2", {"1": "1", "2": "5"})
    run("cf_piecewise_true", c3, sol("Piecewise((1, Eq(n, 1)), (2*n + 1, True))", "expression"), None, show=True)
