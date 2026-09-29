import itertools
from fractions import Fraction
import sympy as sp

x, y, k, n, s = sp.symbols('x y k n s')

def main():
    # Q03: circle center (2,-1), r=3
    lhs = (x - 2)**2 + (y + 1)**2 - 9
    opts = {
        'A': (x - 2)**2 + (y + 1)**2 - 9,
        'B': (x + 2)**2 + (y - 1)**2 - 9,
        'C': (x - 2)**2 + (y + 1)**2 - 3,
        'D': x**2 + y**2 - 4*x + 2*y + 4,
        'E': (x - 2)**2 + (y - 1)**2 - 9,
    }
    # equivalent iff proportional polynomials (same zero set for circles)
    m = {L: sp.simplify(sp.expand(e) - sp.expand(lhs)) == 0 for L, e in opts.items()}
    print('Q03', m)
    # independent check: points on the circle
    pts = [(2 + 3, -1), (2, -1 + 3), (2 - 3, -1), (2, -4)]
    print('Q03 pts', {L: all(e.subs({x: a, y: b}) == 0 for a, b in pts) for L, e in opts.items()})
    # D radius
    print('Q03 D completed:', sp.expand((x-2)**2 + (y+1)**2 - 1))

    # Q07
    a = [5 + 3*i for i in range(20)]
    print('Q07', a[19], 5 + 19*3)

    # Q11
    print('Q11', sp.summation(sp.Rational(1, 2)**k, (k, 1, sp.oo)), float(sum(Fraction(1, 2**i) for i in range(1, 60))))

    # Q15
    print('Q15', sp.integrate(sp.sin(x), (x, 0, sp.pi)), sp.Integral(sp.sin(x), (x, 0, sp.pi)).evalf(30))

    # Q19
    f = (2*x**2 + 1)/(x**2 - 5)
    print('Q19', sp.limit(f, x, sp.oo), [sp.N(f.subs(x, 10**j)) for j in (3, 6, 9)])

    # Q23
    sols = [sp.pi/6 + 2*k*sp.pi, 5*sp.pi/6 + 2*k*sp.pi]
    # brute: zeros of sin(x)-1/2 in [-4pi, 4pi]
    grid = [sp.pi*sp.Rational(j, 6) for j in range(-24, 25)]
    zeros = set(g for g in grid if sp.sin(g) == sp.Rational(1, 2))
    fams = {
        'A': [(sp.pi/6, 2*sp.pi)],
        'B': [(sp.pi/6, 2*sp.pi), (5*sp.pi/6, 2*sp.pi)],
        'C': [(sp.pi/6, sp.pi)],
        'D': [(sp.pi/6, sp.pi), (5*sp.pi/6, sp.pi)],
        'E': [(sp.pi/3, 2*sp.pi), (2*sp.pi/3, 2*sp.pi)],
    }
    res = {}
    for L, fam in fams.items():
        S = set()
        for b, p in fam:
            for kk in range(-10, 11):
                v = sp.nsimplify(b + kk*p)
                if -4*sp.pi <= v <= 4*sp.pi:
                    S.add(v)
        res[L] = S == zeros
    print('Q23', res, len(zeros))

    # Q27
    f = x**2*sp.exp(x)
    d = sp.diff(f, x).subs(x, 0)
    h = sp.Rational(1, 10**8)
    print('Q27', d, sp.N((f.subs(x, h) - f.subs(x, -h))/(2*h), 20))

    # Q31
    f = x**3 - 6*x**2 + 9*x + 1
    cps = sp.solve(sp.diff(f, x), x)
    print('Q31', [(c, sp.diff(f, x, 2).subs(x, c), f.subs(x, c)) for c in cps])
    print('Q31 numeric', [float(f.subs(x, 1 + e)) for e in (-0.01, 0, 0.01)])

    # Q35
    eq = sp.Eq(x/(x - 3), 3/(x - 3) + 2)
    print('Q35', sp.solveset(eq, x, sp.S.Reals))
    for c in [3, 0, -3]:
        try:
            l = sp.Rational(c)/(c - 3); r = sp.Rational(3)/(c - 3) + 2
            print('  Q35 x=', c, l == r)
        except ZeroDivisionError:
            print('  Q35 x=', c, 'undefined')

    # Q39
    print('Q39', sp.solveset((x - 1)/(x + 2) >= 0, x, sp.S.Reals))
    samp = [sp.Rational(i, 4) for i in range(-40, 41)]
    good = [v for v in samp if v != -2 and (v - 1)/(v + 2) >= 0]
    A = sp.Union(sp.Interval.open(-sp.oo, -2), sp.Interval(1, sp.oo))
    print('  Q39 A-check', all((v in A) == (v in good) for v in samp))

    # Q43
    P = x**3 - 2*x**2 + k*x + 6
    ks = sp.solve(P.subs(x, 3), k)
    print('Q43', ks, sp.rem(P.subs(k, ks[0]), x - 3, x))

    # Q47
    print('Q47', sp.sqrt(12**2 + 5**2))

    # Q51
    print('Q51', sp.solveset(x - 3 >= 0, x, sp.S.Reals))

    # Q55
    print('Q55', sp.expand((x + 1)**2 - (x - 1)**2))

    # Q59
    print('Q59', len(list(itertools.permutations(range(5)))))

    # Q63
    outs = list(itertools.product('HT', repeat=3))
    print('Q63', Fraction(sum(1 for o in outs if o.count('H') >= 2), len(outs)))

    # Q67
    for son in range(1, 100):
        if (4*son + 5) == 3*(son + 5):
            print('Q67 son', son, 'father', 4*son)

    # Q71
    print('Q71', [(a, b, a + b) for a in range(1, 50) for b in range(1, 50) if 3*a + 5*b == 41 and a < b])

    # Q75
    print('Q75', pow(5, 100, 7), (5**100) % 7)

    # Q79
    print('Q79', sp.summation(1/(k*(k + 1)), (k, 1, sp.oo)), float(sum(Fraction(1, i*(i + 1)) for i in range(1, 10000))))

    # Q83
    M = sp.Matrix([[2, 1], [1, 2]])
    print('Q83', M.eigenvects())
    v = sp.Matrix([1, 1])
    print('  Q83 Av', (M*v).T, (3*v).T)

if __name__ == '__main__':
    main()
