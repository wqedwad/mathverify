import itertools
from fractions import Fraction
import sympy as sp
import mpmath as mp

x, y, k = sp.symbols('x y k')

def main():
    # Q03: circle center (2,-1) r=3; check options by sampling points
    pts = [(2 + 3*sp.cos(t), -1 + 3*sp.sin(t)) for t in [sp.Rational(1, 3), 1, 2]]
    opts = {
        'A': (x-2)**2 + (y+1)**2 - 9,
        'B': (x+2)**2 + (y-1)**2 - 9,
        'C': (x-2)**2 + (y+1)**2 - 3,
        'D': x**2 + y**2 - 4*x + 2*y + 4,
        'E': (x-2)**2 + (y-1)**2 - 9,
    }
    ref = (x-2)**2 + (y+1)**2 - 9
    for L, e in opts.items():
        on = all(sp.simplify(e.subs({x: a, y: b})) == 0 for a, b in pts)
        prop = sp.simplify(sp.expand(e) / sp.expand(ref))
        print('Q03', L, on, prop)
    print('Q03 D completed:', sp.expand(opts['D']) - sp.expand((x-2)**2 + (y+1)**2 - 1))

    # Q07
    seq = [5]
    for _ in range(19):
        seq.append(seq[-1] + 3)
    print('Q07', seq[19], len(seq))

    # Q11
    print('Q11', sp.summation(sp.Rational(1, 2)**k, (k, 1, sp.oo)), sum(Fraction(1, 2**i) for i in range(1, 60)))

    # Q15
    print('Q15', sp.integrate(sp.sin(x), (x, 0, sp.pi)), mp.quad(mp.sin, [0, mp.pi]))

    # Q19
    f = (2*x**2 + 1)/(x**2 - 5)
    print('Q19', sp.limit(f, x, sp.oo), [float(f.subs(x, 10**n)) for n in (3, 6, 9)])

    # Q23: sin x = 1/2, enumerate solutions in [-4pi, 4pi] numerically, compare option sets
    sols = sp.solveset(sp.sin(x) - sp.Rational(1, 2), x, sp.Interval(-4*sp.pi, 4*sp.pi))
    sols = sorted(float(s) for s in sols)
    def optset(bases, period):
        out = []
        for b in bases:
            for kk in range(-5, 6):
                v = float(b + kk*period)
                if -4*mp.pi - 1e-9 <= v <= 4*mp.pi + 1e-9:
                    out.append(v)
        return sorted(set(round(v, 9) for v in out))
    pi = sp.pi
    o23 = {
        'A': ([pi/6], 2*pi), 'B': ([pi/6, 5*pi/6], 2*pi), 'C': ([pi/6], pi),
        'D': ([pi/6, 5*pi/6], pi), 'E': ([pi/3, 2*pi/3], 2*pi),
    }
    target = sorted(set(round(v, 9) for v in sols))
    for L, (b, p) in o23.items():
        print('Q23', L, optset(b, p) == target)

    # Q27
    g = x**2*sp.exp(x)
    h = 1e-6
    print('Q27', sp.diff(g, x).subs(x, 0), (float(g.subs(x, h)) - float(g.subs(x, -h)))/(2*h))

    # Q31
    f = x**3 - 6*x**2 + 9*x + 1
    crit = sp.solve(sp.diff(f, x), x)
    print('Q31', [(c, sp.diff(f, x, 2).subs(x, c), f.subs(x, c)) for c in crit])
    # numeric: sample neighbors
    for c in crit:
        v = f.subs(x, c)
        print('   ', c, v, f.subs(x, c - sp.Rational(1, 100)) < v, f.subs(x, c + sp.Rational(1, 100)) < v)

    # Q35: brute-force over rationals + solve
    print('Q35', sp.solveset(sp.Eq(x/(x-3), 3/(x-3) + 2), x, sp.S.Reals))
    cand = [Fraction(n, d) for n in range(-60, 61) for d in range(1, 7)]
    good = [c for c in cand if c != 3 and c/(c-3) == 3/(c-3) + 2]
    print('   brute', good)

    # Q39
    print('Q39', sp.solveset((x-1)/(x+2) >= 0, x, sp.S.Reals))
    test = [-5, -2.0001, -2, -1.9999, 0, 0.9999, 1, 1.0001, 5]
    for t in test:
        ok = (t != -2) and ((t-1)/(t+2) >= 0)
        inA = (t < -2) or (t >= 1)
        print('   ', t, ok, inA)

    # Q43
    P = x**3 - 2*x**2 + k*x + 6
    ks = sp.solve(P.subs(x, 3), k)
    print('Q43', ks, sp.rem(P.subs(k, ks[0]), x - 3, x))

    # Q47
    print('Q47', sp.sqrt(12**2 + 5**2))

    # Q51
    print('Q51', sp.calculus.util.continuous_domain(sp.sqrt(x-3), x, sp.S.Reals))

    # Q55
    print('Q55', sp.expand((x+1)**2 - (x-1)**2))

    # Q59
    print('Q59', len(list(itertools.permutations(range(5)))))

    # Q63
    outc = list(itertools.product('HT', repeat=3))
    print('Q63', Fraction(sum(1 for o in outc if o.count('H') >= 2), len(outc)))

    # Q67 brute
    print('Q67', [(4*s, s) for s in range(1, 100) if 4*s + 5 == 3*(s + 5)])

    # Q71 brute
    sols71 = [(a, b) for a in range(1, 50) for b in range(1, 50) if 3*a + 5*b == 41]
    print('Q71', sols71, [(a, b, a+b) for a, b in sols71 if a < b])

    # Q75
    print('Q75', pow(5, 100, 7), (5**100) % 7)

    # Q79
    print('Q79', sp.summation(1/(k*(k+1)), (k, 1, sp.oo)), float(sum(Fraction(1, i*(i+1)) for i in range(1, 10000))))

    # Q83
    A = sp.Matrix([[2, 1], [1, 2]])
    print('Q83', A.eigenvects())
    v = sp.Matrix([1, 1])
    print('   ', A*v == 3*v, (A - 3*sp.eye(2)).nullspace())


if __name__ == '__main__':
    main()
