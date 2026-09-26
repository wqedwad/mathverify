from common import *
from p04_solveeq import se
from p05_ineq import si
from p03b_countint import ci

if __name__ == "__main__":
    # real cube-root convention (Turkish curriculum: x^(2/3) = cbrt(x^2), defined on all R)
    se("x**(2/3) = 4", "{8}", False, name="x^(2/3)=4 -> {8}")
    se("x**(2/3) = 4", "{-8, 8}", True, name="x^(2/3)=4 -> {-8,8}")
    se("cbrt(x**2) = 4", "{8}", False, name="cbrt(x^2)=4 -> {8}")
    se("cbrt(x**2) = 4", "{-8, 8}", True, name="cbrt(x^2)=4 -> {-8,8}")
    se("x**(4/3) = 16", "{8}", False, name="x^(4/3)=16 -> {8}")
    se("cbrt(x) = x", "{0, 1}", False, name="cbrt(x)=x -> {0,1}")
    se("cbrt(x) = x", "{-1, 0, 1}", True, name="cbrt(x)=x -> {-1,0,1}")
    se("x**(1/3) + 2 = 0", "{}", False, name="x^(1/3)+2=0 -> {}")
    si("x**(1/3) < 1", "[0, 1)", False, name="x^(1/3)<1 -> [0,1)")
    si("x**(1/3) < 1", "(-oo, 1)", True, name="x^(1/3)<1 -> (-oo,1)")
    ci(["x**(1/3) <= 1", "x >= -5"], 7, True, name="cbrt count") if False else None
    ci(["cbrt(x) > -2"], None, None) if False else None
    run("count_roots cbrt(x)-x", ir("count_roots", {"expr": "x**3 - x", "var": "x"}), sol("count", 3), True)
    summary()
