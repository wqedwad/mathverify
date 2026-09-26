from common import *
import sympy as sp
from p03b_countint import ci

if __name__ == "__main__":
    X = sp.Symbol("x", real=True)
    for g in ["(x - 1)*log(2) < log(8)", "x*log(3) <= log(27)", "x*log(2) < log(8)", "2**x < 8", "3**x <= 27", "x < log(8)/log(2)"]:
        print("sympy solveset:", g, "->", sp.solveset(sp.sympify(g.replace("x", "X"), locals={"X": X}), X, sp.S.Reals))
    # truth by exact brute force: x in 0..20
    import math
    def exact(pred):
        return sum(1 for k in range(0, 50) if pred(k))
    t = exact(lambda k: (k - 1) < 3)  # (x-1)*log2 < log8 <=> x - 1 < 3
    ci(["(x - 1)*log(2) < log(8)"], t, True, dom="nonneg_integer"); ci(["(x - 1)*log(2) < log(8)"], t + 1, False, dom="nonneg_integer")
    t = exact(lambda k: k < 3)
    ci(["x*log(2) < log(8)"], t, True, dom="nonneg_integer"); ci(["x*log(2) < log(8)"], t + 1, False, dom="nonneg_integer")
    t = exact(lambda k: k <= 3)
    ci(["x*log(3) <= log(27)"], t, True, dom="nonneg_integer"); ci(["x*log(3) <= log(27)"], t - 1, False, dom="nonneg_integer")
    ci(["x*log(2) = log(8)"], 1, True, dom="integer"); ci(["x*log(2) = log(8)"], 0, False, dom="integer")
    ci(["x < log(8)/log(2)"], 3, True, dom="nonneg_integer"); ci(["x < log(8)/log(2)"], 4, False, dom="nonneg_integer")
    ci(["x <= log(8)/log(2)"], 4, True, dom="nonneg_integer"); ci(["x <= log(8)/log(2)"], 3, False, dom="nonneg_integer")
    ci(["x > log(8)/log(2) - 10", "x < 0"], None, None) if False else None
    ci(["Abs(x) < log(8)/log(2)"], 5, True, dom="integer"); ci(["Abs(x) < log(8)/log(2)"], 7, False, dom="integer")
    ci(["x**2 < 1 + 2*cos(pi/3)*4"], 5, True, dom="integer", name="x^2<5 via cos")
    ci(["x**2 < 4*sin(pi/6)**2*9"], 5, True, dom="integer", name="x^2 < 9 via sin")
    ci(["x**2 < 4*sin(pi/6)**2*9"], 7, False, dom="integer", name="x^2 < 9 via sin")
    summary()
