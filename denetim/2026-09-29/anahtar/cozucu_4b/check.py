import itertools
import math
import sympy as sp
import mpmath as mp

x, y, n, C, a, b, s = sp.symbols('x y n C a b s')

# Q04: point-line distance, plus brute minimization of distance to points on the line
d_formula = abs(3*3 + 4*4 - 5) / sp.sqrt(3**2 + 4**2)
t = sp.symbols('t')
# parametrize line: point (t, (5-3t)/4)
dist2 = (t - 3)**2 + ((5 - 3*t)/4 - 4)**2
tmin = sp.solve(sp.diff(dist2, t), t)[0]
print('Q04', d_formula, sp.sqrt(dist2.subs(t, tmin)))

# Q08: first terms
seq = [3 * 2**k for k in range(5)]
optsQ08 = {'A': 3*2**n, 'B': 3*2**(n-1), 'C': 2*3**(n-1), 'D': 6**(n-1), 'E': 3**n}
for k, e in optsQ08.items():
    print('Q08', k, [e.subs(n, i) for i in range(1, 6)] == seq)

# Q12: derivative of options equals ln x
optsQ12 = {'A': x*sp.log(x) - x + C, 'B': x*sp.log(x) + C, 'C': sp.log(x)/x + C,
           'D': x*sp.log(x) + x + C, 'E': 1/x + C}
for k, e in optsQ12.items():
    print('Q12', k, sp.simplify(sp.diff(e, x) - sp.log(x)) == 0)

# Q16, Q20: limits symbolic and numeric
print('Q16', sp.limit((x**2 - 4)/(x - 2), x, 2), [float(((2+h)**2 - 4)/h) for h in (1e-4, -1e-4)])
print('Q20', sp.limit((sp.sqrt(x) - 1)/(x - 1), x, 1), [(math.sqrt(1+h) - 1)/h for h in (1e-6, -1e-6)])

# Q24
v = math.sin(math.radians(75))
optsQ24 = {'A': (sp.sqrt(6) + sp.sqrt(2))/4, 'B': (sp.sqrt(6) - sp.sqrt(2))/4, 'C': sp.sqrt(3)/2,
           'D': (sp.sqrt(2) + 1)/2, 'E': sp.sqrt(2)/2}
for k, e in optsQ24.items():
    print('Q24', k, abs(float(e) - v) < 1e-12, sp.simplify(e - sp.sin(sp.pi*5/12)) == 0)

# Q28: tangent line check: touches at x=1 and double root of x^2 - line
optsQ28 = {'A': 2*x - 1, 'B': 2*x + 1, 'C': x, 'D': 2*x, 'E': x + 1}
for k, e in optsQ28.items():
    print('Q28', k, sp.factor(x**2 - e))

# Q32
sol = sp.solve([sp.diff(x**3 + a*x**2 + b*x, x).subs(x, 1), (x**3 + a*x**2 + b*x).subs(x, 1) + 3], [a, b], dict=True)
print('Q32', sol, [d[a]*d[b] for d in sol])
f = x**3 + sol[0][a]*x**2 + sol[0][b]*x
print('Q32 fprime factor', sp.factor(sp.diff(f, x)), 'f2(1)=', sp.diff(f, x, 2).subs(x, 1))
# brute force over integer a,b
print('Q32 brute', [(A, B) for A in range(-20, 21) for B in range(-20, 21) if 3 + 2*A + B == 0 and 1 + A + B == -3])

# Q36
print('Q36', sp.solveset(sp.Abs(2*x - 3) - 5, x, sp.S.Reals), [k for k in range(-100, 101) if abs(2*k - 3) == 5])

# Q40
print('Q40', [k for k in range(-100, 101) if abs(k - 3) < 2])

# Q44
P = x**5 - 3*x**3 + x + 1
print('Q44', sp.factor(P), sp.real_roots(P), len(set(sp.real_roots(P))), sp.count_roots(P))
print('Q44 numeric', sorted(r for r in mp.polyroots([1, 0, -3, 0, 1, 1]) if abs(mp.im(r)) < 1e-12))
print('Q44 sturm', sp.sqf_part(P) == P or sp.sqf_part(P))

# Q48: coordinates
B_ = sp.Point(-6, 0); C_ = sp.Point(6, 0)
A_ = sp.Point(0, sp.sqrt(100 - 36))
print('Q48', A_.distance(B_), A_.distance(C_), A_.distance(sp.Point(0, 0)))

# Q52
print('Q52', sp.calculus.util.continuous_domain(1/(x**2 - 4), x, sp.S.Reals))
optA = sp.Union(sp.Interval.open(-sp.oo, -2), sp.Interval.open(-2, 2), sp.Interval.open(2, sp.oo))
print('Q52 A equal', optA == sp.calculus.util.continuous_domain(1/(x**2 - 4), x, sp.S.Reals))

# Q56
print('Q56', len([(i, j) for i in range(1, 11) for j in range(1, 11) if i + j == 10]))

# Q60
print('Q60', math.comb(6, 3), len(list(itertools.combinations(range(6), 3))))

# Q64
print('Q64', [(t_, 30 - t_) for t_ in range(31) if 2*t_ + 4*(30 - t_) == 88])

# Q68
print('Q68', sp.Rational(240, 80) + sp.Rational(240, 60))

# Q72
print('Q72', [N for N in range(10, 100) if N//10 + N % 10 == 11 and (N % 10)*10 + N//10 == N + 27])

# Q76
print('Q76', sp.integrate(sp.log(x)/sp.sqrt(x), (x, 0, 1)), mp.quad(lambda u: mp.log(u)/mp.sqrt(u), [0, 1]))
# independent: substitution x=u^2 -> int_0^1 4 ln u du = -4
print('Q76 sub', mp.quad(lambda u: 4*mp.log(u), [0, 1]))

# Q80
M = sp.Matrix([[2, 1], [1, 2]])
print('Q80', M.eigenvals(), max(mp.eig(mp.matrix([[2, 1], [1, 2]]))[0], key=lambda z: mp.re(z)))

# Q84
Ms = sp.Matrix([[1, 1], [2, 4]]); rhs = sp.Matrix([30, 88])
print('Q84', Ms.inv()*rhs, Ms.LUsolve(rhs))
