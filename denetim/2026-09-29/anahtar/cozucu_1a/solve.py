import json
import itertools
import math
import sympy as sp
import mpmath as mp
from sympy.parsing.sympy_parser import parse_expr

IN = "/tmp/claude-0/-home-user-asd/aa4a1d71-7b24-5272-b084-980d72fce676/scratchpad/anahtar/grup1.json"
data = {q["qid"]: q for q in json.load(open(IN, encoding="utf-8"))}

x, y, n = sp.symbols("x y n")
LOC = {"x": x, "y": y, "n": n, "Matrix": sp.Matrix, "sqrt": sp.sqrt, "pi": sp.pi,
       "log": sp.log, "oo": sp.oo}
res = {}


def P(s):
    return parse_expr(s, local_dict=LOC)


def match_scalar(qid, val):
    out = []
    for k, v in data[qid]["options"].items():
        try:
            e = P(v)
        except Exception:
            continue
        if sp.simplify(e - val) == 0:
            out.append(k)
    return out


# Q01: line through A(1,2), B(4,8)
m = sp.Rational(8 - 2, 4 - 1)
line = sp.Eq(y, sp.expand(2 + m * (x - 1)))
# independent check: solve linear system a*1+b=2, a*4+b=8
a, b = sp.symbols("a b")
sol = sp.solve([a * 1 + b - 2, a * 4 + b - 8], [a, b])
assert sp.Eq(y, sol[a] * x + sol[b]) == line
opts = []
for k, v in data["Q01"]["options"].items():
    l, r = v.split("=")
    f = P(r) - y + 0
    rr = P(r)
    ok = all(sp.simplify(rr.subs(x, px) - py) == 0 for px, py in [(1, 2), (4, 8)])
    if ok:
        opts.append(k)
res["Q01"] = (line, opts)

# Q05: triangle area
pts = [(0, 0), (4, 0), (0, 3)]
shoelace = sp.Abs(sum(sp.Integer(pts[i][0]) * pts[(i + 1) % 3][1] - pts[(i + 1) % 3][0] * pts[i][1] for i in range(3))) / 2
det_area = sp.Abs(sp.Matrix([[4, 0], [0, 3]]).det()) / 2
assert shoelace == det_area == 6
res["Q05"] = (shoelace, match_scalar("Q05", shoelace))

# Q09: Fibonacci general term, check options against brute force n=1..30
fib = [None, 1, 1]
for i in range(3, 31):
    fib.append(fib[-1] + fib[-2])
opts = []
for k, v in data["Q09"]["options"].items():
    e = P(v)
    ok = all(sp.nsimplify(sp.N(e.subs(n, i), 60)) == fib[i] and abs(sp.N(e.subs(n, i), 60) - fib[i]) < 1e-40 for i in range(1, 31))
    if ok:
        opts.append(k)
# also symbolic: rsolve
a_ = sp.Function("a")
rs = sp.rsolve(a_(n) - a_(n - 1) - a_(n - 2), a_(n), {a_(1): 1, a_(2): 1})
assert all(sp.simplify(rs.subs(n, i) - fib[i]) == 0 for i in range(1, 15))
res["Q09"] = (P(data["Q09"]["options"]["A"]), opts, rs)

# Q13: integral of |x-1|+|x+2| from -3 to 3
I = sp.integrate(sp.Abs(x - 1) + sp.Abs(x + 2), (x, -3, 3))
I_pw = (sp.integrate(-(x - 1) - (x + 2), (x, -3, -2)) + sp.integrate(-(x - 1) + (x + 2), (x, -2, 1))
        + sp.integrate((x - 1) + (x + 2), (x, 1, 3)))
I_num = mp.quad(lambda t: abs(t - 1) + abs(t + 2), [-3, -2, 1, 3])
assert I == I_pw == 23 and abs(I_num - 23) < 1e-20
res["Q13"] = (I, match_scalar("Q13", I), I_num)

# Q17: lim sin(3x)/x
L17 = sp.limit(sp.sin(3 * x) / x, x, 0)
num17 = [mp.sin(3 * t) / t for t in (mp.mpf("1e-8"), mp.mpf("-1e-8"))]
assert L17 == 3
res["Q17"] = (L17, match_scalar("Q17", L17), num17)

# Q21: lim_{x->0+} x ln x
L21 = sp.limit(x * sp.log(x), x, 0, "+")
num21 = [t * mp.log(t) for t in (mp.mpf("1e-10"), mp.mpf("1e-50"))]
assert L21 == 0
res["Q21"] = (L21, match_scalar("Q21", L21), num21)

# Q25: tan x = sqrt(3) on [0, pi)
S25 = sp.solveset(sp.tan(x) - sp.sqrt(3), x, sp.Interval.Ropen(0, sp.pi))
# numeric scan for sign change of tan - sqrt3 (excluding pole)
roots = [mp.findroot(lambda t: mp.tan(t) - mp.sqrt(3), g) for g in (1.0,)]
res["Q25"] = (S25, match_scalar("Q25", sp.pi / 3), roots)

# Q29: derivative ln(x^2+1)
d29 = sp.diff(sp.log(x ** 2 + 1), x)
numd = [mp.diff(lambda t: mp.log(t ** 2 + 1), t0) - 2 * t0 / (t0 ** 2 + 1) for t0 in (0.3, 1.7, -2.5)]
res["Q29"] = (d29, match_scalar("Q29", d29), numd)

# Q33: log(x-1)+log(x-3)=log3; domain x>3
cand = sp.solve(sp.expand((x - 1) * (x - 3)) - 3, x)
S33 = {c for c in cand if c - 1 > 0 and c - 3 > 0}
# brute: check numerically the original equation for candidates
chk33 = {c: (c > 3) and abs(mp.log(float(c - 1)) + mp.log(float(c - 3)) - mp.log(3)) < 1e-12 if c > 3 else "undefined" for c in cand}
opts = []
for k, v in data["Q33"]["options"].items():
    s = v.strip()
    inner = s[1:-1].strip()
    st = set() if inner == "" else {sp.Integer(int(t)) for t in inner.split(",")}
    if st == S33:
        opts.append(k)
res["Q33"] = (S33, opts, chk33)

# Q37: double root
m_ = sp.symbols("m")
ms = sp.solve((m_ + 1) ** 2 - 16, m_)
mpos = [v for v in ms if v > 0]
# check: substitute m=3 -> x^2 - 4x + 4 = (x-2)^2
assert sp.factor(x ** 2 - (3 + 1) * x + 4) == (x - 2) ** 2
res["Q37"] = (mpos, match_scalar("Q37", mpos[0]), ms)

# Q41: (f o g)(2)
f = lambda t: 2 * t + 3
g = lambda t: t ** 2 - 1
v41 = f(g(2))
v41b = sp.expand((2 * (x ** 2 - 1) + 3)).subs(x, 2)
assert v41 == v41b == 9
res["Q41"] = (v41, match_scalar("Q41", v41))

# Q45: hypotenuse
h = sp.sqrt(6 ** 2 + 8 ** 2)
# coordinate check: B(0,0), A(0,6), C(8,0)
h2 = sp.sqrt((0 - 8) ** 2 + (6 - 0) ** 2)
assert h == h2 == 10
res["Q45"] = (h, match_scalar("Q45", h))

# Q49: right triangle legs 6, 8 area
ar = sp.Rational(6 * 8, 2)
# Heron check with hypotenuse 10
s_ = sp.Rational(6 + 8 + 10, 2)
her = sp.sqrt(s_ * (s_ - 6) * (s_ - 8) * (s_ - 10))
assert ar == her == 24
res["Q49"] = (ar, match_scalar("Q49", ar))

# Q53: domain ln(x-1)
from sympy.calculus.util import continuous_domain
dom = continuous_domain(sp.log(x - 1), x, sp.S.Reals)
opts = []
for k, v in data["Q53"]["options"].items():
    s = v.strip()
    lo, hi = s[1:-1].split(",")
    iv = sp.Interval(P(lo), P(hi), left_open=s[0] == "(", right_open=s[-1] == ")")
    if iv == dom:
        opts.append(k)
res["Q53"] = (dom, opts)

# Q57: nonneg integer solutions 2x+3y=12
sols57 = [(i, j) for i in range(0, 13) for j in range(0, 13) if 2 * i + 3 * j == 12]
res["Q57"] = (len(sols57), match_scalar("Q57", len(sols57)), sols57)

# Q61: distinct-digit 3-digit numbers from {1..5}
cnt61 = len(set(itertools.permutations([1, 2, 3, 4, 5], 3)))
cnt61b = len([k for k in range(100, 1000) if set(str(k)) <= set("12345") and len(set(str(k))) == 3])
assert cnt61 == cnt61b == sp.factorial(5) / sp.factorial(2)
res["Q61"] = (cnt61, match_scalar("Q61", cnt61))

# Q65: work rate
t65 = 1 / (sp.Rational(1, 6) + sp.Rational(1, 3))
# check: in 2 hours Ali does 2/6, Veli 2/3 -> total 1
assert sp.Rational(2, 6) + sp.Rational(2, 3) == 1
res["Q65"] = (t65, match_scalar("Q65", t65))

# Q69: cost price
c69 = sp.Rational(360) / sp.Rational(6, 5)
assert c69 * sp.Rational(120, 100) == 360
res["Q69"] = (c69, match_scalar("Q69", c69))

# Q73: three consecutive even naturals sum 78
tri = [(k, k + 2, k + 4) for k in range(0, 80, 2) if 3 * k + 6 == 78]
assert len(tri) == 1
res["Q73"] = (max(tri[0]), match_scalar("Q73", max(tri[0])), tri)

# Q77: det
A = sp.Matrix([[1, 2], [3, 4]])
d77 = A.det()
assert d77 == 1 * 4 - 2 * 3 == -2
res["Q77"] = (d77, match_scalar("Q77", d77))

# Q81: inverse
Ainv = A.inv()
opts = []
for k, v in data["Q81"]["options"].items():
    M = P(v)
    if (A * M) == sp.eye(2) and (M * A) == sp.eye(2):
        opts.append(k)
assert Ainv == sp.Matrix([[-2, 1], [sp.Rational(3, 2), -sp.Rational(1, 2)]])
res["Q81"] = (Ainv, opts)

# Q85: A^3
B = sp.Matrix([[1, 1], [0, 1]])
B3 = B ** 3
B3b = B * B * B
assert B3 == B3b
opts = [k for k, v in data["Q85"]["options"].items() if P(v) == B3]
res["Q85"] = (B3, opts)

for k, v in res.items():
    print(k, v)
