import itertools, math, json
from fractions import Fraction as F
import sympy as sp
import mpmath as mp

x, n, k = sp.symbols('x n k')
opts = {q['qid']: q['options'] for q in json.load(open('../grup2.json', encoding='utf-8'))}
out = {}

def match_num(qid, val):
    res = []
    for L, t in opts[qid].items():
        try:
            e = sp.sympify(t, locals={'E': sp.E})
            if sp.simplify(e - val) == 0:
                res.append(L)
        except Exception:
            pass
    return res

# Q02 distance
d = math.hypot(4 - 1, 6 - 2)
out['Q02'] = (d, match_num('Q02', 5))

# Q06 recurrence brute
a = [None, 1, 3]
for i in range(3, 7):
    a.append(a[i - 1] + 2 * a[i - 2])
# closed form: a_n = alpha*2^n + beta*(-1)^n
al, be = sp.symbols('al be')
s = sp.solve([al * 2 + be * (-1) - 1, al * 4 + be - 3], [al, be])
cf = s[al] * 2**6 + s[be]
out['Q06'] = (a[6], cf, match_num('Q06', a[6]))

# Q10
out['Q10'] = (sum(i * i for i in range(1, 11)), 10 * 11 * 21 // 6, match_num('Q10', 385))

# Q14
I = sp.integrate(x * sp.exp(x), (x, 0, 1))
In = mp.quad(lambda t: t * mp.e**t, [0, 1])
out['Q14'] = (I, In, match_num('Q14', I))

# Q18
out['Q18'] = ([abs(h) / h for h in (1e-3, 1e-9, -1e-3, -1e-9)],
              sp.limit(sp.Abs(x) / x, x, 0, '+'), sp.limit(sp.Abs(x) / x, x, 0, '-'))

# Q22 numeric root scan
roots = set()
for i in range(200000):
    t0 = 2 * math.pi * i / 200000
    t1 = 2 * math.pi * (i + 1) / 200000
    g = lambda t: math.cos(2 * t) - 0.5
    if g(t0) == 0 or g(t0) * g(t1) < 0:
        r = mp.findroot(lambda t: mp.cos(2 * t) - 0.5, (t0 + t1) / 2)
        roots.add(round(float(r / mp.pi), 9))
sol = sp.solveset(sp.cos(2 * x) - sp.Rational(1, 2), x, sp.Interval.Ropen(0, 2 * sp.pi))
m22 = [L for L, t in opts['Q22'].items() if sp.FiniteSet(*sp.sympify(t)) == sol]
out['Q22'] = (sorted(roots), sol, m22)

# Q26 dense scan
f = lambda t: t**3 - 3 * t
grid = max(f(-2 + 5 * i / 10**6) for i in range(10**6 + 1))
crit = [c for c in sp.solve(sp.diff(x**3 - 3 * x, x), x)]
cand = [(x**3 - 3 * x).subs(x, c) for c in crit + [-2, 3]]
out['Q26'] = (grid, max(cand), match_num('Q26', max(cand)))

# Q30
g30 = min(t + 4 / t for t in [i / 10000 for i in range(1, 200000)])
out['Q30'] = (g30, match_num('Q30', 4))

# Q34 integer + real check
cands = sp.solve(sp.Eq(x + 4, (x - 2)**2), x)
valid = [c for c in cands if sp.sqrt(c + 4) == c - 2]
ss = sp.solveset(sp.sqrt(x + 4) - (x - 2), x, sp.S.Reals)
out['Q34'] = (cands, valid, ss)

# Q38 / Q74
ss38 = sp.solveset(x**2 - 5 * x - 14 < 0, x, sp.S.Reals)
ints = [i for i in range(-100, 100) if i * i - 5 * i - 14 < 0]
out['Q38'] = (ss38, ints, len(ints))

# Q42 check f(8/3)=5 exactly with Fractions
fx = lambda t: (2 * t + 3) / (t - 1)
y = sp.symbols('y')
inv = sp.solve(sp.Eq(y, (2 * x + 3) / (x - 1)), x)[0]
out['Q42'] = (fx(F(8, 3)), inv.subs(y, 5), match_num('Q42', sp.Rational(8, 3)))

# Q46 / Q50
out['Q46'] = ((180 - 40) / 2,)
# construct triangle: A at origin, AB=AC=1, angle 40 -> compute angle B
A = sp.Matrix([0, 0]); B = sp.Matrix([1, 0]); C = sp.Matrix([sp.cos(sp.pi * 40 / 180), sp.sin(sp.pi * 40 / 180)])
v1 = A - B; v2 = C - B
angB = sp.acos((v1.dot(v2)) / (v1.norm() * v2.norm()))
out['Q46b'] = float(angB * 180 / sp.pi)
out['Q50'] = (180 - 50 - 60,)

# Q54
e54 = 1 / x + 1 / (x + 1)
m54 = []
for L, t in opts['Q54'].items():
    e = sp.sympify(t)
    if sp.simplify(e - e54) == 0:
        m54.append(L)
out['Q54'] = (sp.together(e54), m54)

# Q58
cnt = sum(1 for a1, a2 in itertools.product(range(1, 7), repeat=2) if a1 + a2 == 7)
out['Q58'] = (F(cnt, 36),)

# Q62
balls = ['R1', 'R2', 'R3', 'B1', 'B2']
pairs = list(itertools.combinations(balls, 2))
rr = sum(1 for p in pairs if all(b[0] == 'R' for b in p))
ordered = list(itertools.permutations(balls, 2))
rr2 = sum(1 for p in ordered if all(b[0] == 'R' for b in p))
out['Q62'] = (F(rr, len(pairs)), F(rr2, len(ordered)))

# Q66
out['Q66'] = ([t for t in range(-100, 100) if 3 * t + 5 == 5 * t - 7], sp.solve(3 * x + 5 - (5 * x - 7), x))

# Q70
out['Q70'] = (math.gcd(84, 120), max(dd for dd in range(1, 85) if 84 % dd == 0 and 120 % dd == 0))

# Q78
out['Q78'] = (sp.limit((1 + 1 / n)**n, n, sp.oo), float((1 + 1 / 10**7)**(10**7)))

# Q82
M = sp.Matrix([[2, 1], [1, 2]])
ev = M.eigenvals()
# check: det(M - l I) = 0 for l=1,3
out['Q82'] = (ev, [(M - l * sp.eye(2)).det() for l in (1, 3)], sp.expand((M - x * sp.eye(2)).det()))

# Q86 Leibniz brute force
N = [[2, 0, 1], [1, 3, 2], [1, 1, 1]]
def sgn(p):
    s = 1
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            if p[i] > p[j]:
                s = -s
    return s
det = sum(sgn(p) * N[0][p[0]] * N[1][p[1]] * N[2][p[2]] for p in itertools.permutations(range(3)))
out['Q86'] = (det, sp.Matrix(N).det(), sp.Matrix(N).rank())

for kk, v in out.items():
    print(kk, v)
