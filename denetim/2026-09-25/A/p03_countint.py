from common import *
import sympy as sp

def ci(givens, claim, truth_ok, dom="integer", dod=None, name="", var="x"):
    vs = [{"name": var, "domain": dom}] if dom else [{"name": var}]
    return run(f"count_integers[{name or givens}|{dom}|{dod}]={claim}", ir("count_integers", {"var": var}, vars_=vs, givens=givens, shape="count", dod=dod),
               sol("count", claim), truth_ok)

def brute(pred, lo=-200, hi=200):
    c = 0
    for k in range(lo, hi + 1):
        try:
            if pred(k): c += 1
        except (ZeroDivisionError, ValueError):
            pass
    return c

if __name__ == "__main__":
    # written definedness: x/x + x**2 <= 5 -> x != 0 -> {-2,-1,1,2} = 4
    ci(["x/x + x**2 <= 5"], 4, True); ci(["x/x + x**2 <= 5"], 5, False)
    ci(["x**2/x <= 3", "x >= -3"], 6, True, name="x2/x<=3,x>=-3")  # -3..3 minus 0 -> 6
    ci(["x**2/x <= 3", "x >= -3"], 7, False, name="x2/x<=3,x>=-3")
    # positive integer domain: x^2 < 10 -> 1,2,3
    ci(["x**2 < 10"], 3, True, dom="positive_integer"); ci(["x**2 < 10"], 6, False, dom="positive_integer"); ci(["x**2 < 10"], 7, False, dom="positive_integer")
    ci(["x**2 < 10"], 7, True, dom="integer")
    ci(["x**2 < 10"], 4, True, dom="nonneg_integer"); ci(["x**2 < 10"], 7, False, dom="nonneg_integer")
    # union solution sets with positive_integer
    ci(["(x - 2)*(x - 5) > 0", "x < 9"], 6, True, dom="positive_integer", name="(x-2)(x-5)>0,x<9")  # 1,6,7,8 -> wait
    # ground truth for above
    print("gt (x-2)(x-5)>0,x<9, x>=1:", brute(lambda k: (k-2)*(k-5) > 0 and k < 9 and k >= 1))
    ci(["(x - 2)*(x - 5) > 0", "x < 9"], 4, True, dom="positive_integer", name="(x-2)(x-5)>0,x<9")
    ci(["(x - 2)*(x - 5) > 0", "x < 9", "x > -4"], 8, True, dom="integer", name="(x-2)(x-5)>0,-4<x<9")
    print("gt:", brute(lambda k: (k-2)*(k-5) > 0 and -4 < k < 9))
    # union + positive_integer where Intersection may stay unevaluated
    ci(["Abs(x - 3) > 1", "x < 10"], 7, True, dom="positive_integer", name="|x-3|>1,x<10 N")
    print("gt:", brute(lambda k: abs(k-3) > 1 and k < 10 and k >= 1))
    ci(["Abs(x - 3) > 1", "x < 10"], 8, False, dom="positive_integer", name="|x-3|>1,x<10 N")
    ci(["Abs(x - 3) > 1", "x < 10"], 11, False, dom="positive_integer", name="|x-3|>1,x<10 N")
    # log inequality
    ci(["log(x - 1) < 1"], 2, True, name="log(x-1)<1")  # 1<x<1+e -> 2,3 -> 2
    print("gt:", brute(lambda k: k > 1 and k - 1 < 2.718281828))
    ci(["log(x - 1) < 1"], 3, False, name="log(x-1)<1")
    # sqrt
    ci(["sqrt(x + 3) < 2"], 4, True)  # -3<=x<1 -> -3,-2,-1,0 -> 4
    ci(["sqrt(x + 3) < 2"], 5, False)
    ci(["sqrt(x + 3) <= 2"], 5, True)
    # rational inequality
    ci(["(x - 3)/(x + 2) <= 0"], 5, True)  # -2 < x <= 3 -> -1..3 = 5
    ci(["(x - 3)/(x + 2) <= 0"], 6, False)
    # strictness at irrational endpoints
    ci(["x**2 < 17"], 9, True)  # -4..4
    ci(["x**2 <= 16"], 9, True); ci(["x**2 < 16"], 7, True); ci(["x**2 < 16"], 9, False)
    # infinite
    ci(["x > 3"], 100, False)
    # domain of discourse
    ci(["x**2 < 10"], 3, True, dom="integer", dod="x > 0")
    ci(["x**2 < 10"], 7, False, dom="integer", dod="x > 0")
    # no domain declared (Reals) but counting integers
    ci(["x**2 < 10"], 7, True, dom=None)
    # abs double
    ci(["Abs(x) + Abs(x - 4) <= 6"], 7, True)  # -1..5 -> 7
    print("gt:", brute(lambda k: abs(k) + abs(k-4) <= 6))
    ci(["Abs(x) + Abs(x - 4) <= 6"], 6, False)
    # floor
    ci(["floor(x/2) = 3"], 2, True, name="floor(x/2)=3")
    ci(["floor(x/2) = 3"], 1, False, name="floor(x/2)=3")
    # Written: sqrt(x)**2 < 4 -> x in [0,4) -> 0,1,2,3 = 4; auto-simplified x < 4 infinite
    ci(["sqrt(x)**2 < 4"], 4, True, name="sqrt(x)**2<4")
    ci(["(x**2 - 4)/(x - 2) < 5"], None, None, name="dummy") if False else None
    # (x**2-4)/(x-2) <= 5 and x >= 0 -> x+2 <= 5, x != 2 -> 0,1,3 -> 3
    ci(["(x**2 - 4)/(x - 2) <= 5", "x >= 0"], 3, True, name="(x2-4)/(x-2)<=5,x>=0")
    ci(["(x**2 - 4)/(x - 2) <= 5", "x >= 0"], 4, False, name="(x2-4)/(x-2)<=5,x>=0")
    # nonneg with union
    ci(["x**2 - 5*x + 4 > 0", "x <= 8"], 6, True, dom="nonneg_integer", name="x2-5x+4>0,x<=8 N0")
    print("gt:", brute(lambda k: k*k - 5*k + 4 > 0 and k <= 8 and k >= 0))
    summary()
