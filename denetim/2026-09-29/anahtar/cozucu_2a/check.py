import itertools
import math
from fractions import Fraction

import mpmath as mp
import sympy as sp

x = sp.symbols('x', real=True)
out = {}


def main():
    # Q02 distance: brute Pythagoras + sympy Point
    d = math.hypot(4 - 1, 6 - 2)
    out['Q02'] = (d, sp.Point(1, 2).distance(sp.Point(4, 6)))

    # Q06 recurrence: iterative + closed form a_n = (2^(n+1) + (-1)^n)/3 ? check
    a = [None, 1, 3]
    for n in range(3, 7):
        a.append(a[n - 1] + 2 * a[n - 2])
    n = sp.symbols('n', integer=True)
    rs = sp.rsolve(sp.Function('f')(n) - sp.Function('f')(n - 1) - 2 * sp.Function('f')(n - 2),
                   sp.Function('f')(n), {sp.Function('f')(1): 1, sp.Function('f')(2): 3})
    out['Q06'] = (a[6], sp.simplify(rs.subs(n, 6)))

    # Q10
    out['Q10'] = (sum(k * k for k in range(1, 11)), 10 * 11 * 21 // 6)

    # Q14
    I = sp.integrate(x * sp.exp(x), (x, 0, 1))
    out['Q14'] = (I, mp.quad(lambda t: t * mp.e ** t, [0, 1]))

    # Q18 one-sided limits
    f = sp.Abs(x) / x
    out['Q18'] = (sp.limit(f, x, 0, '+'), sp.limit(f, x, 0, '-'),
                  [float(f.subs(x, v)) for v in (1e-9, -1e-9)])

    # Q22 cos2x=1/2 on [0,2pi): solveset + numeric scan
    sol = sp.solveset(sp.cos(2 * x) - sp.Rational(1, 2), x, sp.Interval.Ropen(0, 2 * sp.pi))
    roots = []
    N = 200000
    for i in range(N):
        t0 = 2 * math.pi * i / N
        t1 = 2 * math.pi * (i + 1) / N
        g0 = math.cos(2 * t0) - 0.5
        g1 = math.cos(2 * t1) - 0.5
        if g0 == 0 or g0 * g1 < 0:
            roots.append(round(t0 / math.pi * 6, 3))
    opts22 = {
        'A': {sp.pi / 6, 5 * sp.pi / 6},
        'B': {sp.pi / 6, 5 * sp.pi / 6, 7 * sp.pi / 6, 11 * sp.pi / 6},
        'C': {sp.pi / 3, 5 * sp.pi / 3},
        'D': {sp.pi / 6, 11 * sp.pi / 6},
        'E': {sp.pi / 3, 2 * sp.pi / 3, 4 * sp.pi / 3, 5 * sp.pi / 3},
    }
    out['Q22'] = (sol, roots, [k for k, v in opts22.items() if sp.FiniteSet(*v) == sol])

    # Q26 max of x^3-3x on [-2,3]: calculus + dense grid
    g = x ** 3 - 3 * x
    crit = [c for c in sp.solve(sp.diff(g, x), x) if -2 <= c <= 3] + [-2, 3]
    mx = max(g.subs(x, c) for c in crit)
    grid = max((-2 + 5 * i / 100000) ** 3 - 3 * (-2 + 5 * i / 100000) for i in range(100001))
    out['Q26'] = (mx, grid)

    # Q30 min of x+4/x, x>0
    h = x + 4 / x
    cp = [c for c in sp.solve(sp.diff(h, x), x) if c > 0]
    out['Q30'] = ([h.subs(x, c) for c in cp], min(t / 1000 + 4 / (t / 1000) for t in range(1, 100000)))

    # Q34 sqrt(x+4)=x-2: sympy solveset over reals + integer/rational brute check
    s34 = sp.solveset(sp.sqrt(x + 4) - (x - 2), x, sp.S.Reals)
    cands = [c for c in sp.solve((x + 4) - (x - 2) ** 2, x)]
    valid = [c for c in cands if sp.sqrt(c + 4) == c - 2]
    out['Q34'] = (s34, cands, valid)

    # Q38 / Q74
    s38 = sp.solve_univariate_inequality(x ** 2 - 5 * x - 14 < 0, x, relational=False)
    ints = [k for k in range(-100, 101) if k * k - 5 * k - 14 < 0]
    out['Q38'] = (s38, s38 == sp.Interval.open(-2, 7))
    out['Q74'] = (len(ints), ints)

    # Q42 inverse
    y = sp.symbols('y')
    finv = sp.solve(sp.Eq((2 * y + 3) / (y - 1), x), y)
    out['Q42'] = ([fi.subs(x, 5) for fi in finv], ((2 * sp.Rational(8, 3) + 3) / (sp.Rational(8, 3) - 1)))

    # Q46, Q50
    out['Q46'] = ((180 - 40) / 2,)
    out['Q50'] = (180 - 50 - 60,)

    # Q54: compare each option with 1/x+1/(x+1)
    e54 = 1 / x + 1 / (x + 1)
    opts54 = {
        'A': (2 * x + 1) / (x * (x + 1)),
        'B': (2 * x + 1) / (x + 1),
        'C': 2 / (2 * x + 1),
        'D': (x + 1) / (x * (x + 1)),
        'E': 1 / (x * (x + 1)),
    }
    m54 = [k for k, v in opts54.items() if sp.simplify(e54 - v) == 0]
    num54 = [k for k, v in opts54.items() if all(abs(float((e54 - v).subs(x, t))) < 1e-12 for t in (0.3, 2.7, -5.1))]
    out['Q54'] = (sp.together(e54), m54, num54)

    # Q58 enumerate dice
    cnt = sum(1 for a1, b1 in itertools.product(range(1, 7), repeat=2) if a1 + b1 == 7)
    out['Q58'] = (Fraction(cnt, 36),)

    # Q62 enumerate unordered pairs of 5 distinct balls
    balls = ['R1', 'R2', 'R3', 'B1', 'B2']
    pairs = list(itertools.combinations(balls, 2))
    rr = sum(1 for p in pairs if all(b[0] == 'R' for b in p))
    out['Q62'] = (Fraction(rr, len(pairs)), Fraction(3, 5) * Fraction(2, 4))

    # Q66
    out['Q66'] = (sp.solve(sp.Eq(3 * x + 5, 5 * x - 7), x), [k for k in range(-100, 101) if 3 * k + 5 == 5 * k - 7])

    # Q70
    out['Q70'] = (math.gcd(84, 120), max(d for d in range(1, 85) if 84 % d == 0 and 120 % d == 0))

    # Q78
    nn = sp.symbols('nn', positive=True, integer=True)
    out['Q78'] = (sp.limit((1 + 1 / nn) ** nn, nn, sp.oo), (1 + 1 / 10 ** 8) ** (10 ** 8), math.e)

    # Q82
    M = sp.Matrix([[2, 1], [1, 2]])
    out['Q82'] = (M.eigenvals(), sp.factor(M.charpoly().as_expr()))

    # Q86 det: sympy + Leibniz brute
    A = [[2, 0, 1], [1, 3, 2], [1, 1, 1]]
    leib = 0
    for p in itertools.permutations(range(3)):
        sgn = 1
        for i in range(3):
            for j in range(i + 1, 3):
                if p[i] > p[j]:
                    sgn = -sgn
        leib += sgn * A[0][p[0]] * A[1][p[1]] * A[2][p[2]]
    out['Q86'] = (sp.Matrix(A).det(), leib)

    for k, v in out.items():
        print(k, v)


if __name__ == '__main__':
    main()
