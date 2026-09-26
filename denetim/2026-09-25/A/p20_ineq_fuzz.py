"""Independent check of SymPy solveset on inequalities: exact evaluation on a dense rational grid.
Any mismatch where the verifier then certifies SymPy's (wrong) set as CORRECT is a false CORRECT."""
from common import *
import sympy as sp, mpmath as mp
from sympy import Rational as Q

X = sp.Symbol("x", real=True)

def holds_exact(rel, v):
    try:
        l = rel.lhs.subs(X, v); r = rel.rhs.subs(X, v)
        with mp.workdps(60):
            a = sp.N(l, 60); b = sp.N(r, 60)
        if not (a.is_real and b.is_real):
            return None
        d = sp.N(l - r, 60)
        if abs(d) < 1e-40:
            return None  # too close to call
        return bool(type(rel)(a, b))
    except Exception:
        return None

def check(ineq_s):
    rel = sp.sympify(ineq_s, locals={"x": X})
    try:
        s = sp.solveset(rel, X, sp.S.Reals)
    except Exception as e:
        return None, f"EXC {e}"
    bad = []
    for k in range(-400, 401):
        v = Q(k, 40) + Q(1, 997)
        h = holds_exact(rel, v)
        if h is None: continue
        inside = s.contains(v)
        if inside not in (sp.true, sp.false): continue
        if bool(inside) != h:
            bad.append((str(v), h))
    return s, bad

if __name__ == "__main__":
    cands = ["Abs(x - 1) + Abs(x + 1) < 3", "Abs(Abs(x) - 2) < 1", "sqrt(x + 2) > x", "sqrt(4 - x**2) >= x", "(x**2 - 1)/(x**2 - 4) < 0",
             "x/(x - 1) > 2", "Abs(x**2 - 4) < 3*x", "sqrt(x**2 - 1) < x + 1", "floor(x) < 2", "Max(x, 1) < 3", "Min(x, 2) > x**2 - 2",
             "x**(1/3) < x", "log(x**2 - 1) < 1", "log(Abs(x)) < 1", "exp(x) > x + 2", "2**x < x**2", "sin(x) > 0", "Abs(x - 1) > Abs(x + 2)",
             "sqrt(x) + sqrt(1 - x) > 1", "(x - 1)**(2/3) < 1", "Abs(2*x - 1) <= x + 3", "1/Abs(x - 1) > 2", "x**2*Abs(x) > 8", "(x - 2)/sqrt(x) > 0",
             "log(x - 1)/log(3 - x) > 0", "x**3 - 3*x**2 + 3*x - 1 > 0", "(x**2 - 3*x + 2)/(x**2 + 1) >= 0", "Abs(x) + Abs(x - 1) + Abs(x - 2) < 3"]
    for c in cands:
        s, bad = check(c)
        print(f"{c}: solveset={s} mismatches={bad[:5] if isinstance(bad, list) else bad}")
        if isinstance(bad, list) and bad and isinstance(s, sp.Set) and not isinstance(s, sp.ConditionSet):
            run(f"ineq_fuzz[{c}] claim=sympy set", ir("solve_inequality", {"var": "x"}, givens=[c]), sol("interval", str(s)), False)
    summary()
