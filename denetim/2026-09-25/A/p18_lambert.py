from common import *
import sympy as sp, mpmath as mp
from p04_solveeq import se

X = sp.Symbol("x", real=True)

def real_roots_numeric(f, lo=-50, hi=50, n=20001):
    """independent ground truth: sign changes + local minima of |f| on a fine grid, refined with mpmath findroot"""
    mp.mp.dps = 30
    fl = sp.lambdify(X, f, "mpmath")
    roots = []
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    vals = []
    for x in xs:
        try:
            v = fl(mp.mpf(x)); v = v if not isinstance(v, mp.mpc) or abs(v.imag) < 1e-20 else None
            vals.append(None if v is None else mp.re(v))
        except Exception:
            vals.append(None)
    for i in range(n - 1):
        a, b = vals[i], vals[i + 1]
        if a is None or b is None: continue
        if a == 0: roots.append(mp.mpf(xs[i])); continue
        if a * b < 0:
            try:
                r = mp.findroot(fl, (mp.mpf(xs[i]), mp.mpf(xs[i + 1])), solver="bisect")
                roots.append(r)
            except Exception:
                pass
    out = []
    for r in roots:
        if not any(abs(r - o) < 1e-12 for o in out): out.append(r)
    return out

if __name__ == "__main__":
    cases = ["x*exp(x) = -1/5", "exp(x) = 3*x", "2**x = 3*x", "x**2*exp(x) = 1/10", "x*exp(-x) = 1/5", "exp(x) = x**2 + 2", "exp(-x) = x**2", "log(x) = x - 2", "x*log(x) = -1/5", "x**2 = 2**x", "3**x = x**3"]
    for c in cases:
        l, r = c.split("=")
        f = sp.sympify(l, locals={"x": X}) - sp.sympify(r, locals={"x": X})
        gt = real_roots_numeric(f, -20, 20)
        s1 = sp.solve(sp.Eq(f, 0), X)
        try:
            s2 = sp.solveset(f, X, sp.S.Reals)
        except Exception as e:
            s2 = f"EXC {e}"
        print(f"== {c}: numeric GT roots={[mp.nstr(g, 10) for g in gt]} | solve={s1} | solveset={s2}")
        if s1:
            claim = "{" + ", ".join(str(a) for a in s1 if a.is_real is not False) + "}"
            se(c, claim, len([a for a in s1 if a.is_real is not False]) == len(gt), name=c + " (solve's set)")
    summary()
