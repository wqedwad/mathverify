import sympy as sp
x = sp.symbols('x', positive=True)
F = 2*sp.sqrt(x)*sp.log(x) - 4*sp.sqrt(x)
print(sp.simplify(sp.diff(F, x) - sp.log(x)/sp.sqrt(x)), F.subs(x, 1) - sp.limit(F, x, 0, '+'))
print(sp.integrate(sp.log(x)/sp.sqrt(x), (x, 0, 1)))
