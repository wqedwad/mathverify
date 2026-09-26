from common import *
import sympy as sp, math

def ci(givens, claim, truth_ok, dom="integer", dod=None, name="", var="x", cons=None):
    v = {"name": var}
    if dom: v["domain"] = dom
    if cons: v["constraints"] = cons
    return run(f"count_integers[{name or givens}|{dom}|{dod}|{cons}]={claim}", ir("count_integers", {"var": var}, vars_=[v], givens=givens, shape="count", dod=dod),
               sol("count", claim), truth_ok)

def brute(pred, lo=-300, hi=300):
    c = 0
    for k in range(lo, hi + 1):
        try:
            if pred(k): c += 1
        except (ZeroDivisionError, ValueError):
            pass
    return c

if __name__ == "__main__":
    g = brute(lambda k: (k-2)*(k-5) > 0 and 1 <= k < 9); print("gt", g)
    for c in (g, 6, 7, 8):
        ci(["(x - 2)*(x - 5) > 0"], c, c == g, dom="positive_integer", dod="x < 9")
    g = brute(lambda k: abs(k-3) > 1 and 0 <= k <= 10); print("gt", g)
    for c in (g, g + 1, 9, 11):
        ci(["Abs(x - 3) > 1"], c, c == g, dom="nonneg_integer", cons=["x <= 10"])
    # var constraints path
    g = brute(lambda k: k*k < 50 and k > 0 and k % 1 == 0); print("gt", g)
    ci(["x**2 < 50"], g, True, dom="positive_integer")
    ci(["x**2 < 50"], 2*g+1, False, dom="positive_integer")
    # irrational endpoints union
    g = brute(lambda k: k*k > 2 and k*k < 30 and k > 0); print("gt", g)
    for c in (g, 2*g, 2*g+1):
        ci(["(x**2 - 2)*(x**2 - 30) < 0"], c, c == g, dom="positive_integer")
    # dod as interval with real var
    g = brute(lambda k: k*k < 30 and k >= 0); print("gt", g)
    for c in (g, 11):
        ci(["x**2 < 30"], c, c == g, dom=None, dod="x >= 0")
    # dod excluding a point
    g = brute(lambda k: k*k < 30 and k != 0); print("gt", g)
    for c in (g, 11):
        ci(["x**2 < 30"], c, c == g, dom="integer", dod="x != 0")
    # constraint excluding points
    g = brute(lambda k: k*k < 30 and k != 2); print("gt", g)
    for c in (g, 11):
        ci(["x**2 < 30"], c, c == g, dom="integer", cons=["x != 2"])
    # union result with nonneg integer
    g = brute(lambda k: (k-1)*(k-3)*(k-6) < 0 and k >= 0); print("gt", g)
    for c in (g, g+1, g+2):
        ci(["(x - 1)*(x - 3)*(x - 6) < 0"], c, c == g, dom="nonneg_integer")
    g = brute(lambda k: (k-1)*(k-3)*(k-6) < 0 and k >= 1); print("gt", g)
    for c in (g, g+1, g+2):
        ci(["(x - 1)*(x - 3)*(x - 6) < 0"], c, c == g, dom="positive_integer")
    # (x-1)(x-3)(x-6) > 0 infinite -> any claim wrong
    ci(["(x - 1)*(x - 3)*(x - 6) > 0"], 2, False, dom="integer")
    # equation (finite set) counting
    g = 2
    ci(["x**2 = 4"], 2, True); ci(["x**2 = 4"], 1, False, dom="positive_integer")
    ci(["x**2 = 2"], 0, True); ci(["x**2 = 2"], 2, False)
    ci(["x**3 = 8"], 1, True)
    # piecewise-ish: Abs equation
    ci(["Abs(x - 1) = 2"], 2, True); ci(["Abs(x - 1) = 2"], 1, True, dom="positive_integer")
    ci(["Abs(x - 1) = 2"], 2, False, dom="positive_integer")
    # empty
    ci(["x**2 < 0"], 0, True); ci(["x**2 < 0"], 1, False)
    ci(["x**2 <= 0"], 1, True); ci(["x**2 <= 0"], 0, False)
    # count with "exp"
    g = brute(lambda k: 2**k < 100 and k >= 0); print("gt", g)
    ci(["2**x < 100"], g, True, dom="nonneg_integer")
    ci(["2**x < 100"], g+1, False, dom="nonneg_integer")
    # huge endpoints near integers: x < 10**20 + 1/10**30 etc.
    ci(["x**2 < 10**40 + 1", "x > 0"], None, None, name="skip") if False else None
    # interval near integer: x^2 < 16 + 1/10**40 -> -4..4 = 9 (strict, 16+eps > 16 so 4 included)
    ci(["x**2 < 16 + 1/10**40"], 9, True, name="x^2<16+eps")
    ci(["x**2 < 16 + 1/10**40"], 7, False, name="x^2<16+eps")
    ci(["x**2 < 16 - 1/10**40"], 7, True, name="x^2<16-eps")
    ci(["x**2 < 16 - 1/10**40"], 9, False, name="x^2<16-eps")
    summary()
