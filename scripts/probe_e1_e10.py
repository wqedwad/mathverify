"""Raw measurement probe for handoff §6 (E1–E10).

Runs each claim literally against the installed SymPy/mpmath/z3 and prints
what actually happens. This is NOT the test-suite; it is the evidence used to
write the test-suite. Differences from the handoff are reported, not hidden.
"""
import time, sys
import sympy as sp
from sympy import (symbols, cos, sin, log, sqrt, Abs, pi, S, oo, I, Interval,
                   solveset, solve, Union, ImageSet, Lambda, Mod, FiniteSet,
                   Poly, limit, simplify, diff, N, expand_complex, Rational,
                   Integral, integrate, AccumBounds, nsimplify)
import mpmath as mp
import z3

x, n = symbols('x n')
def t():
    return time.perf_counter()

print("versions:", sp.__version__, mp.__version__, z3.get_version_string(), sys.version.split()[0])

# ---------------- E1 ----------------
print("\n=== E1: cos(2x)=1/2 ===")
t0 = t()
ss = solveset(sp.Eq(cos(2*x), S.Half), x, S.Reals)
print("solveset:", ss, " type:", type(ss).__name__, f"[{(t()-t0)*1000:.0f} ms]")
cand = Union(ImageSet(Lambda(n, n*pi + pi/6), S.Integers),
             ImageSet(Lambda(n, n*pi - pi/6), S.Integers))
print("candidate:", cand)
print("ss == cand :", ss == cand)
print("ss.is_subset(cand):", ss.is_subset(cand))
print("cand.is_subset(ss):", cand.is_subset(ss))
# period reduction
t0 = t()
P = pi
win = solveset(sp.Eq(cos(2*x), S.Half), x, Interval.Ropen(0, P))
reps = FiniteSet(*[sp.simplify(Mod(v, P)) for v in [pi/6, -pi/6]])
print("window solve:", win, " reps:", reps, " equal:", win == reps, f"[{(t()-t0)*1000:.0f} ms]")

# ---------------- E2 ----------------
print("\n=== E2: log(x-1)+log(x-3)=log 3 ===")
eq = log(x-1) + log(x-3) - log(3)
t0 = t()
print("solve   :", solve(eq, x))
print("solveset:", solveset(eq, x, S.Reals), f"[{(t()-t0)*1000:.0f} ms]")
eq2 = sqrt(x+4) - (x-2)
print("sqrt(x+4)=x-2 naive squaring solve:", solve((x+4) - (x-2)**2, x))
print("sqrt(x+4)=x-2 solve:", solve(eq2, x), " solveset:", solveset(eq2, x, S.Reals))

# ---------------- E3 ----------------
print("\n=== E3: integrals ===")
t0 = t()
try:
    r = integrate(log(x)/sqrt(x), (x, 0, 1))
    print("sympy integrate ln x/sqrt x:", r, f"[{(t()-t0):.1f} s]")
except Exception as e:
    print("sympy integrate raised:", type(e).__name__, e, f"[{(t()-t0):.1f} s]")
mp.mp.dps = 15
t0 = t()
v = mp.quad(lambda u: mp.log(u)/mp.sqrt(u), [0, 1])
print("naive mp.quad dps15:", v, f"[{(t()-t0)*1000:.0f} ms]")
mp.mp.dps = 40
t0 = t()
v = mp.quad(lambda u: mp.log(u)/mp.sqrt(u), [0, 1], method='tanh-sinh')
print("tanh-sinh dps40:", mp.nstr(v, 20), f"[{(t()-t0)*1000:.0f} ms]")
mp.mp.dps = 15
f2 = lambda u: abs(u-1) + abs(u+2)
t0 = t()
print("naive |x-1|+|x+2| on [-3,3]:", mp.quad(f2, [-3, 3]), f"[{(t()-t0)*1000:.0f} ms]")
t0 = t()
print("with breakpoints [-3,-2,1,3]:", mp.quad(f2, [-3, -2, 1, 3]), f"[{(t()-t0)*1000:.0f} ms]")

# ---------------- E4 ----------------
print("\n=== E4: domain-aware random points ===")
import random
random.seed(0)
e1, e2 = sqrt(x**2), x
pos_ok = all(abs(float((e1-e2).subs(x, random.uniform(0.1, 10)))) < 1e-9 for _ in range(30))
random.seed(0)
mixed_ok = all(abs(float((e1-e2).subs(x, random.uniform(-10, 10)))) < 1e-9 for _ in range(30))
print("sqrt(x^2) vs x — positive-only 30 pts 'equal':", pos_ok, " mixed:", mixed_ok)
e3, e4 = log(x**2), 2*log(x)
random.seed(0)
print("log(x^2) vs 2log(x) on x>0:", all(abs(complex((e3-e4).subs(x, random.uniform(0.1, 10)).evalf())) < 1e-9 for _ in range(30)))
from sympy.calculus.util import continuous_domain
t0 = t()
d = continuous_domain(log(x-1)+log(x-3), x, S.Reals)
print("continuous_domain(log(x-1)+log(x-3)):", d, f"[{(t()-t0):.2f} s]")
t0 = t()
d = continuous_domain(sqrt(x+4)/(x-2), x, S.Reals)
print("continuous_domain(sqrt(x+4)/(x-2)):", d, f"[{(t()-t0):.2f} s]")

# ---------------- E5 ----------------
print("\n=== E5: extremum ===")
t0 = t()
f = x**3 - 3*x
crit = [c for c in solve(diff(f, x), x) if c.is_real and -2 <= c <= 3]
pts = crit + [-2, 3]
vals = [(p, f.subs(x, p)) for p in pts]
print("candidates:", vals, " max:", max(v for _, v in vals))
empt = solveset(f > 18, x, Interval(-2, 3))
print("{f>18} on [-2,3]:", empt, " is EmptySet:", empt == S.EmptySet, f"[{(t()-t0)*1000:.0f} ms]")

# ---------------- E6 ----------------
print("\n=== E6: limits ===")
t0 = t()
print("limit(|x|/x, x, 0):", limit(Abs(x)/x, x, 0))
print("one-sided:", limit(Abs(x)/x, x, 0, '+'), limit(Abs(x)/x, x, 0, '-'))
print("limit(sin(1/x), x, 0):", limit(sin(1/x), x, 0), f"[{(t()-t0)*1000:.0f} ms]")

# ---------------- E7 ----------------
print("\n=== E7: z3 uniqueness ===")
t0 = t()
a, b = z3.Reals('a b')
s = z3.Solver(); s.add(a+b == 30, 2*a+4*b == 88, a > 0, b > 0)
print("sat?", s.check(), s.model() if s.check() == z3.sat else None)
s.add(a != 16)
print("with a!=16:", s.check(), f"[{(t()-t0)*1000:.0f} ms]")

# ---------------- E8 ----------------
print("\n=== E8: antiderivative certificate ===")
print("d/dx(x ln x - x) - ln x =", simplify(diff(x*log(x)-x, x) - log(x)))
print("d/dx(x ln x) - ln x =", simplify(diff(x*log(x), x) - log(x)))
print("d/dx(x ln x - x + 7) - ln x =", simplify(diff(x*log(x)-x+7, x) - log(x)))

# ---------------- E9 ----------------
print("\n=== E9: complex ===")
print("simplify(I**I):", simplify(I**I))
print("expand_complex(I**I):", expand_complex(I**I))
print("N(I**I):", N(I**I))

# ---------------- E10 ----------------
print("\n=== E10: counting ===")
t0 = t()
p = Poly(x**5 - 3*x**3 + x + 1, x)
print("count_roots:", p.count_roots(), " real_roots len:", len(p.real_roots()), f"[{(t()-t0)*1000:.0f} ms]")
iv = solveset(x**2 - 5*x - 14 < 0, x, S.Reals)
print("x^2-5x-14<0:", iv, " == Interval.open(-2,7):", iv == Interval.open(-2, 7))
from sympy import ceiling, floor
lo, hi = iv.inf, iv.sup
cnt = floor(hi - (1 if iv.right_open and (hi).is_integer else 0)) - ceiling(lo + (1 if iv.left_open and lo.is_integer else 0)) + 1
print("integers inside:", cnt)
