import sympy as sp
if __name__ == "__main__":
    t = sp.Symbol('t', positive=True); x = sp.Symbol('x', real=True)
    P = sp.Dummy('P', positive=True); s = sp.Dummy('s', positive=True)
    for e in [t**(-x), t**x, x/t, 1/(t + x), t**(-x)/(1+t**0)]:
        try:
            print(e, sp.limit(e, t, sp.oo))
        except Exception as ex:
            print(e, 'EXC', ex)
    for e in [s**2*sp.exp(P*s - s), s**2*sp.exp((P-1)*s)]:
        try:
            print(e, sp.limit(e, s, sp.oo))
        except Exception as ex:
            print(e, 'EXC', ex)
    e = 1/(1 + s**2*((sp.exp(sp.I*s)+sp.exp(-sp.I*s))/2)**2)
    try:
        print('expI', sp.limit(s**2*sp.Abs(e), s, sp.oo))
    except Exception as ex:
        print('expI EXC', ex)
