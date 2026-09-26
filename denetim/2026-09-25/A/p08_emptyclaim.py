from common import *
import sympy as sp
from p04_solveeq import se

X = sp.Symbol("x", real=True)
def truth(eqs):
    l, r = eqs.split("=")
    return sp.solveset(sp.sympify(l.replace("x", "X"), locals={"X": X}) - sp.sympify(r.replace("x", "X"), locals={"X": X}), X, sp.S.Reals)

if __name__ == "__main__":
    cases = ["sqrt(x**2 - 2*x - 1) = 0",
             "sqrt(x**2 - 4*x + 1) + sqrt(4*x - x**2 - 1) = 0",
             "sqrt(x**2 + x - 1) = 0",
             "sqrt(x**2 - 2*x - 2) = 0",
             "sqrt(x**2 - 6*x + 7) = 0",
             "sqrt(x**2 - 4*x - 1) = 0",
             "sqrt(x**2 - 2*x - 1) = x**2 - 2*x - 1",
             "sqrt(x**2 - 2*x - 1)*(x - 5) = 0",
             "(x**2 - 2*x - 1)**(1/4) = 0"]
    for c in cases:
        t = truth(c)
        print("sympy truth", c, "->", t)
        se(c, "{}", t == sp.S.EmptySet, name=c + " {}")
        if isinstance(t, sp.FiniteSet):
            se(c, "{" + ", ".join(str(a) for a in t) + "}", True, name=c + " truth")
    summary()
