"""C01 limit: values of a real function OUTSIDE its real domain are accepted (SymPy works over C).
Ground truth: sqrt(x-1) is not real for x < 1, so no real limit exists at 0; sqrt/log are undefined
left of 0; asin is undefined right of 1."""
from _r import IR, SOL, check
import sympy as sp

if __name__ == "__main__":
    x = sp.Symbol("x", real=True)
    assert sp.sqrt(sp.Rational(-1, 2)).is_real is False and sp.asin(sp.Rational(3, 2)).is_real is False
    L = lambda e, to, side=None: IR("limit", dict({"expr": e, "var": "x", "to": to}, **({"side": side} if side else {})))
    check("lim_{x->0} sqrt(x-1) = I", L("sqrt(x - 1)", "0"), SOL("value", "I"), "CORRECT")
    check("lim_{x->0-} sqrt(x) = 0", L("sqrt(x)", "0", "-"), SOL("value", "0"), "CORRECT")
    check("lim_{x->0-} log(x) = -oo", L("log(x)", "0", "-"), SOL("infinite", "-oo"), "CORRECT")
    check("lim_{x->1+} asin(x) = pi/2", L("asin(x)", "1", "+"), SOL("value", "pi/2"), "CORRECT")
    check("lim_{x->-1} log(x) = I*pi", L("log(x)", "-1"), SOL("value", "I*pi"), "CORRECT")
    # the right answer is refuted
    check("lim_{x->0-} sqrt(x) does not exist", L("sqrt(x)", "0", "-"), SOL("dne", None), "INCORRECT")
    check("lim_{x->0} sqrt(x-1) does not exist", L("sqrt(x - 1)", "0"), SOL("dne", None), "INCORRECT")
