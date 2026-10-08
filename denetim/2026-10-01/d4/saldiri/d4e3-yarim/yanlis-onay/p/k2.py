import sympy as sp
if __name__ == "__main__":
    t = sp.Symbol('t', real=True); x = sp.Symbol('x', real=True); s = sp.Dummy('s', positive=True)
    for h in [t/(x**2*t**2 + 1), t**2/(x**2*t**3+1), x*t/(x**2*t**2+1), t/(x*t**2+1), (1 + x*t)/t, t/(x**2*t+1)]:
        try:
            print(h, sp.limit(h, t, sp.oo))
        except Exception as ex:
            print(h, 'EXC', ex)
    for e in [s**2/(1 + s**2*sp.Abs(sp.exp(sp.I*s)+1)**2), s**2*sp.Abs(1/(1 + s**2*sp.Abs(sp.exp(sp.I*s)+1)**2))]:
        try:
            print(e, sp.limit(e, s, sp.oo))
        except Exception as ex:
            print(e, 'EXC', ex)
    print(sp.re(sp.exp(sp.I*t)), sp.Abs(sp.exp(sp.I*t)+1))
