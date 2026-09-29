import sympy as sp, mpmath as mp
x=sp.symbols('x', positive=True)
def main():
    F=2*sp.sqrt(x)*sp.log(x)-4*sp.sqrt(x)
    print('dF-f',sp.simplify(sp.diff(F,x)-sp.log(x)/sp.sqrt(x)))
    print('value',F.subs(x,1)-sp.limit(F,x,0,'+'))
    u=sp.symbols('u',positive=True)  # x=u^2 -> int 4 ln u du from 0..1
    print('subst',sp.integrate(4*sp.log(u),(u,0,1)))
    mp.mp.dps=30
    print('mp tanh-sinh',mp.quad(lambda t: mp.log(t)/mp.sqrt(t),[0,1],method='tanh-sinh'))
    print('mp sub',mp.quad(lambda t: 4*mp.log(t),[0,1]))
    P=lambda t: t**5-3*t**3+t+1
    print('Q44 sturm count', sp.count_roots(sp.Poly(sp.Symbol('y')**5-3*sp.Symbol('y')**3+sp.Symbol('y')+1)))
    print('Q44 vals',[(v,P(v)) for v in (-2,-1.7,-1.6,0,0.9,1.2,1.5,1.6,2)])
if __name__=='__main__':
    main()
