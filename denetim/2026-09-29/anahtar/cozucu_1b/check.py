import json
import itertools
import math
import mpmath as mp
import sympy as sp

x, n = sp.symbols("x n")
D = json.load(open("/tmp/claude-0/-home-user-asd/aa4a1d71-7b24-5272-b084-980d72fce676/scratchpad/anahtar/grup1.json"))
Q = {d["qid"]: d for d in D}


def P(s):
    return sp.sympify(s, locals={"Matrix": sp.Matrix, "x": x, "n": n})


def eq_opts(qid, target, cmp=None):
    out = []
    for k, v in Q[qid]["options"].items():
        try:
            if "=" in v and "==" not in v:
                l, r = v.split("=")
                val = sp.expand(P(l) - P(r))
            else:
                val = P(v)
            ok = cmp(val) if cmp else sp.simplify(val - target) == 0
        except Exception as e:
            ok = False
        if ok:
            out.append(k)
    return out


# Q01: line through (1,2),(4,8); independent: check each option passes both points
res = {}
res["Q01"] = [k for k, v in Q["Q01"]["options"].items()
              if all(sp.simplify(P(v.split("=")[1]).subs(x, px) - py) == 0 for px, py in [(1, 2), (4, 8)])]
# Q05: shoelace
pts = [(0, 0), (4, 0), (0, 3)]
area = abs(sum(pts[i][0] * pts[(i + 1) % 3][1] - pts[(i + 1) % 3][0] * pts[i][1] for i in range(3))) / 2
res["Q05"] = (area, eq_opts("Q05", sp.Rational(area)))
# Q09: compute fib by recurrence and compare options for n=1..15
fib = [None, 1, 1]
for i in range(3, 20):
    fib.append(fib[-1] + fib[-2])
m = []
for k, v in Q["Q09"]["options"].items():
    e = P(v)
    if all(sp.nsimplify(sp.N(e.subs(n, i), 50)) == fib[i] and abs(sp.N(e.subs(n, i), 50) - fib[i]) < 1e-30 for i in range(1, 16)):
        m.append(k)
res["Q09"] = m
# Q13: sympy integrate + mpmath quad
I1 = sp.integrate(sp.Abs(x - 1) + sp.Abs(x + 2), (x, -3, 3))
I2 = mp.quad(lambda t: abs(t - 1) + abs(t + 2), [-3, -2, 1, 3])
res["Q13"] = (I1, I2, eq_opts("Q13", I1))
# Q17
L = sp.limit(sp.sin(3 * x) / x, x, 0)
res["Q17"] = (L, [float(mp.sin(3 * t) / t) for t in (1e-3, -1e-3, 1e-6)], eq_opts("Q17", L))
# Q21
L = sp.limit(x * sp.log(x), x, 0, "+")
res["Q21"] = (L, [float(t * mp.log(t)) for t in (1e-3, 1e-6, 1e-12)], eq_opts("Q21", L))
# Q25
sol = sp.solveset(sp.tan(x) - sp.sqrt(3), x, sp.Interval.Ropen(0, sp.pi))
res["Q25"] = (sol, [k for k, v in Q["Q25"]["options"].items() if abs(mp.tan(float(P(v))) - mp.sqrt(3)) < 1e-9])
# Q29: derivative + numeric finite difference
d = sp.diff(sp.log(x ** 2 + 1), x)
fd = [(mp.log((t + 1e-7) ** 2 + 1) - mp.log((t - 1e-7) ** 2 + 1)) / 2e-7 for t in (0.7, -1.3, 2.5)]
res["Q29"] = (d, fd, eq_opts("Q29", d))
# Q33: brute over solveset and domain
sol = sp.solveset(sp.log(x - 1) + sp.log(x - 3) - sp.log(3), x, sp.Reals)
cand = [k for k, v in Q["Q33"]["options"].items()]
res["Q33"] = (sol, [t for t in range(-10, 20) if t > 3 and (t - 1) * (t - 3) == 3])
# Q37
m_ = sp.symbols("m")
sol = sp.solve(sp.discriminant(x ** 2 - (m_ + 1) * x + 4, x), m_)
res["Q37"] = (sol, [mv for mv in range(-20, 20) if (mv + 1) ** 2 - 16 == 0])
# Q41
f = lambda t: 2 * t + 3
g = lambda t: t ** 2 - 1
res["Q41"] = f(g(2))
# Q45
res["Q45"] = math.hypot(6, 8)
# Q49
res["Q49"] = 6 * 8 / 2
# Q53
res["Q53"] = sp.calculus.util.continuous_domain(sp.log(x - 1), x, sp.Reals)
# Q57
res["Q57"] = [(a, b) for a in range(0, 13) for b in range(0, 13) if 2 * a + 3 * b == 12]
# Q61
res["Q61"] = len([p for p in itertools.product(range(1, 6), repeat=3) if len(set(p)) == 3])
# Q65
t = sp.symbols("t")
res["Q65"] = sp.solve(t / 6 + t / 3 - 1, t)
# Q69
c = sp.symbols("c")
res["Q69"] = sp.solve(c * sp.Rational(6, 5) - 360, c)
# Q73
res["Q73"] = [(a, a + 2, a + 4) for a in range(0, 80, 2) if 3 * a + 6 == 78]
# Q77
A = sp.Matrix([[1, 2], [3, 4]])
res["Q77"] = (A.det(), 1 * 4 - 2 * 3)
# Q81
inv = A.inv()
res["Q81"] = (inv, [k for k, v in Q["Q81"]["options"].items() if A * P(v) == sp.eye(2) and P(v) * A == sp.eye(2)])
# Q85
B = sp.Matrix([[1, 1], [0, 1]])
res["Q85"] = (B ** 3, B * B * B, [k for k, v in Q["Q85"]["options"].items() if P(v) == B * B * B])

for k, v in res.items():
    print(k, v)
