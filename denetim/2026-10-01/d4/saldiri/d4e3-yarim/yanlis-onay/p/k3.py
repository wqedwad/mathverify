import sympy as sp
if __name__ == "__main__":
    import mathverify.certify.domain as D
    t = sp.Symbol('t', real=True); x = sp.Symbol('x', real=True)
    g = t*sp.sin(t)/(x**2*t**2 + 1)
    m, s = D.majorant(g, t, sp.oo) if hasattr(D, "majorant") else (None, None)
    print("majorant", m)
    print("dirichlet", D._dirichlet_test(g, t, sp.oo))
    print("decays_at", D.decays_at(g, t, sp.oo))
    print("decays_at x=0", D.decays_at(g.subs(x, 0), t, sp.oo))
    body = sp.Symbol('t', real=True)
    gi, tt = D._integrand_on(g, t, t)
    print("integrand_on", gi)
    import mpmath as mp
    mp.mp.dps = 30
    F = lambda T: mp.sin(T) - T*mp.cos(T) - (mp.sin(1) - mp.cos(1))
    print("x=0 partial integrals at T=2*pi*n:", [mp.nstr(F(2*mp.pi*n), 8) for n in (10, 100, 1000)])
    for xv in (mp.mpf('0.5'), mp.mpf('0.1')):
        f = lambda tt: tt*mp.sin(tt)/(xv**2*tt**2 + 1)
        vals = [mp.quadosc(f, [1, mp.inf], omega=1)]
        print("x=", xv, "quadosc", mp.nstr(vals[0], 15))
