from common import *
import sympy as sp
from p09_simplify_domain import do

if __name__ == "__main__":
    X = sp.Symbol("x", real=True)
    for c in [X - sp.sin(X) >= 0, 2**X - X - 1 >= 0, sp.exp(X) - X - 2 > 0, sp.Ne(X - sp.floor(X), 0)]:
        try:
            print("solveset", c, "->", sp.solveset(c, X, sp.S.Reals))
        except Exception as e:
            print("solveset", c, "EXC", e)
    do("sqrt(x - sin(x)) + floor(x)", "[0, oo)", True, name="sqrt(x-sin x)+floor(x) -> [0,oo)")
    do("sqrt(x - sin(x)) + floor(x)", "Complement(Interval(0, oo), Integers)", False, kind="set", name="... -> [0,oo) minus Z")
    do("1/(x - floor(x))", "Complement(Reals, Integers)", True, kind="set", name="1/(x-floor x) -> R minus Z")
    do("1/(x - floor(x))", "Reals", False, kind="set", name="1/(x-floor x) -> R")
    do("sqrt(exp(x) - x - 2) + Abs(x)", "Reals", False, kind="set", name="sqrt(e^x-x-2) -> R")
    do("sqrt(2**x - x - 1)", "Reals", False, kind="set", name="sqrt(2^x-x-1) -> R")
    summary()
