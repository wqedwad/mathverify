from common import *
import sympy as sp, mpmath as mp
from p06_evaluate import ev
from p09_simplify_domain import sx

if __name__ == "__main__":
    # independent ground truth: exact inequality proven by sympy
    print("GT sqrt(10**100+1) != 10**50:", sp.sqrt(10**100 + 1) - 10**50 != 0, " (square: 10**100+1 vs 10**100)")
    ev("sqrt(10**100 + 1)", "10**50", False, name="sqrt(10^100+1)=10^50")
    ev("sqrt(10**40 + 1)", "10**20", False, name="sqrt(10^40+1)=10^20")
    ev("sqrt(10**20 + 1)", "10**10", False, name="sqrt(10^20+1)=10^10")
    ev("2**300 + sqrt(2)", "2**300 + sqrt(2) + 1", False, name="2^300+sqrt2 off by 1")
    ev("10**80*pi", "10**80*pi + 1", False, name="1e80*pi off by 1")
    ev("factorial(60)*sqrt(2)", "factorial(60)*sqrt(2) + 1", False, name="60!*sqrt2 off by 1")
    ev("sqrt(factorial(100))", "sqrt(factorial(100) + 1)", False, name="sqrt(100!) vs sqrt(100!+1)")
    ev("log(10**100 + 1)", "100*log(10)", False, name="log(10^100+1)")
    ev("exp(-200)", "0", False, name="exp(-200)=0")
    ev("exp(-100)", "0", False, name="exp(-100)=0")
    ev("tanh(100)", "1", False, name="tanh(100)=1")
    ev("atan(10**80)", "pi/2", False, name="atan(1e80)=pi/2")
    pi75 = mp.nstr(mp.mpf(1), 1)
    with mp.workdps(90):
        p75 = mp.nstr(+mp.pi, 75, strip_zeros=False)
        s80 = mp.nstr(mp.sqrt(2), 76, strip_zeros=False)
    print("pi75:", p75)
    ev("pi", p75, False, name="pi 75 digits")
    ev("sqrt(2)", s80, False, name="sqrt2 76 digits")
    # with givens (solve_system path)
    ev("a", "10**50", False, givens=["a**2 = 10**100 + 1", "a > 0"], vars_=[{"name": "a"}], name="a^2=10^100+1")
    # ---- simplify: exceptions on thin/far sets
    sx("floor(x) + floor(-x)", "-1", False, name="floor(x)+floor(-x)")
    sx("ceiling(x) - floor(x)", "1", False, name="ceil-floor")
    sx("sign(x)**2", "1", False, name="sign^2")
    sx("Abs(sign(x))", "1", False, name="|sign|")
    sx("Abs(x - 2025) + Abs(x + 2025)", "4050", False, name="|x-2025|+|x+2025|")
    sx("Abs(x - 1500) - Abs(x + 1500)", "-2*x", False, name="|x-1500|-|x+1500|")
    sx("Max(x, 1001)", "1001", False, name="Max(x,1001)")
    sx("Min(x, 2000)", "x", False, name="Min(x,2000)")
    sx("Abs(n - 61) + n", "61", False, vars_=[{"name": "n", "domain": "integer"}], name="|n-61|+n int")
    sx("Min(n, 100)", "n", False, vars_=[{"name": "n", "domain": "integer"}], name="Min(n,100) int")
    sx("Min(n, 200)", "n", False, vars_=[{"name": "n", "domain": "positive_integer"}], name="Min(n,200) N")
    sx("x**0", "1", None, name="x**0")
    summary()
