import mpmath as mp
mp.mp.dps = 60
cases = [
 ("sqrt(x^2+x^4)", lambda x: mp.sqrt(x**2+x**4), lambda x: (x+2*x**3)/mp.sqrt(x**2+x**4), 0),
 ("(x^2+x^4)^(1/3)", lambda x: mp.cbrt(x**2+x**4), lambda x: (2*x+4*x**3)/(3*mp.cbrt(x**2+x**4)**2), 0),
 ("sqrt(sin^2+sin^4)", lambda x: mp.sqrt(mp.sin(x)**2+mp.sin(x)**4), lambda x: (mp.sin(x)*mp.cos(x)+2*mp.sin(x)**3*mp.cos(x))/mp.sqrt(mp.sin(x)**2+mp.sin(x)**4), 0),
 ("sqrt(x^2+x^2 sin^2)", lambda x: mp.sqrt(x**2+x**2*mp.sin(x)**2), lambda x: (x+x*mp.sin(x)**2+x**2*mp.sin(x)*mp.cos(x))/mp.sqrt(x**2+x**2*mp.sin(x)**2), 0),
 ("sqrt((x-1)^2+(x-1)^4)", lambda x: mp.sqrt((x-1)**2+(x-1)**4), lambda x: ((x-1)+2*(x-1)**3)/mp.sqrt((x-1)**2+(x-1)**4), 1),
]
for name, f, c, p in cases:
    h = mp.mpf('1e-30')
    r = (f(p+h)-f(p))/h; l = (f(p-h)-f(p))/(-h)
    md = 0
    for x0 in [mp.mpf('0.3'), mp.mpf('-1.7'), mp.mpf('2.2'), mp.mpf('-0.05')]:
        d = mp.diff(f, p + x0)
        md = max(md, abs(d - c(p + x0)))
    print(f"{name}: right quotient {mp.nstr(r, 15)}, left quotient {mp.nstr(l, 15)}; max |f' - claim| at 4 points: {mp.nstr(md, 5)}")
