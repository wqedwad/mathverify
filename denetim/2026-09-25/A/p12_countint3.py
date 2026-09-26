from common import *
import sympy as sp
from p03b_countint import ci
import json
from mathverify.verifier import verify

def brute(pred, lo=-100, hi=100):
    return sum(1 for k in range(lo, hi + 1) if pred(k))

if __name__ == "__main__":
    X = sp.Symbol("x", real=True)
    tests = [("2**Abs(x) < 8", lambda k: 2**abs(k) < 8), ("2**Abs(x) <= 8", lambda k: 2**abs(k) <= 8),
             ("3**(x**2) < 81", lambda k: 3**(k*k) < 81), ("3**(x**2) <= 81", lambda k: 3**(k*k) <= 81),
             ("4**x < 64", lambda k: 4**k < 64 if k >= 0 else True),
             ("2**(x**2 - 1) < 8", lambda k: 2**(k*k) < 16),
             ("(1/2)**Abs(x) > 1/8", lambda k: abs(k) < 3),
             ("9**Abs(x) < 3**5", lambda k: 2*abs(k) < 5),
             ("2**x = 8", lambda k: k == 3), ("2**(2*x) = 64", lambda k: k == 3),
             ("x*log(2) < log(8)", None)]
    for g, pred in tests:
        s = sp.solveset(sp.sympify(g.replace("x", "X"), locals={"X": X}), X, sp.S.Reals)
        print("sympy solveset:", g, "->", s)
        if pred is None: continue
        t = brute(pred)
        ci([g], t, True, dom="integer")
        ci([g], t + 2, False, dom="integer"); ci([g], t - 2, False, dom="integer")
        ci([g], t + 1, False, dom="integer"); ci([g], t - 1, False, dom="integer")
    r = verify(ir("count_integers", {"var": "x"}, vars_=[{"name": "x", "domain": "nonneg_integer"}], givens=["x*log(2) < log(8)"], shape="count"), sol("count", 3))
    for l in r.layers: print(l.layer, l.verdict, json.dumps(l.evidence, default=str)[:800])
    summary()
