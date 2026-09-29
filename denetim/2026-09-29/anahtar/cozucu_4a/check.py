import sympy as sp, mpmath as mp, itertools, math
x,y,n,a,b,C=sp.symbols('x y n a b C')
def main():
    # Q04
    d=sp.Abs(3*3+4*4-5)/sp.sqrt(9+16); print('Q04',d)
    # brute: minimize distance numerically along line
    t=sp.symbols('t'); px=t; py=(5-3*t)/4
    dd=sp.sqrt((px-3)**2+(py-4)**2); tt=sp.solve(sp.diff(dd**2,t),t)[0]; print(' Q04 check', sp.simplify(dd.subs(t,tt)))
    # Q08
    seq=[3*2**k for k in range(5)]
    for L,e in {'A':3*2**n,'B':3*2**(n-1),'C':2*3**(n-1),'D':6**(n-1),'E':3**n}.items():
        print(' Q08',L,[e.subs(n,k) for k in range(1,6)]==seq)
    # Q12
    F=sp.integrate(sp.log(x),x); print('Q12',F)
    for L,e in {'A':x*sp.log(x)-x,'B':x*sp.log(x),'C':sp.log(x)/x,'D':x*sp.log(x)+x,'E':1/x}.items():
        print(' Q12',L,sp.simplify(sp.diff(e,x)-sp.log(x))==0)
    print(' Q12 numeric', mp.quad(mp.log,[1,3]), 3*mp.log(3)-3-(0-1))
    # Q16
    print('Q16',sp.limit((x**2-4)/(x-2),x,2), [(v**2-4)/(v-2) for v in (1.999,2.001)])
    # Q20
    print('Q20',sp.limit((sp.sqrt(x)-1)/(x-1),x,1), [(math.sqrt(v)-1)/(v-1) for v in (0.9999,1.0001)])
    # Q24
    v=sp.sin(sp.pi*75/180)
    for L,e in {'A':(sp.sqrt(6)+sp.sqrt(2))/4,'B':(sp.sqrt(6)-sp.sqrt(2))/4,'C':sp.sqrt(3)/2,'D':(sp.sqrt(2)+1)/2,'E':sp.sqrt(2)/2}.items():
        print(' Q24',L,sp.N(e-v,30), sp.simplify(sp.expand_trig(e-v))==0 or abs(sp.N(e-v,50))<1e-45)
    # Q28
    f=x**2; m=sp.diff(f,x).subs(x,1); print('Q28 tangent y =',sp.expand(m*(x-1)+1))
    h=1e-7; print(' Q28 numeric slope',((1+h)**2-(1-h)**2)/(2*h))
    # Q32
    fx=x**3+a*x**2+b*x
    sol=sp.solve([sp.diff(fx,x).subs(x,1), fx.subs(x,1)+3],[a,b],dict=True); print('Q32',sol,[s[a]*s[b] for s in sol])
    s=sol[0]; fp=sp.diff(fx,x).subs(s); print(' Q32 fprime',sp.factor(fp),[fp.subs(x,v) for v in (0.9,1.1)])
    # Q36
    print('Q36',sp.solveset(sp.Abs(2*x-3)-5,x,sp.S.Reals), [k for k in range(-100,101) if abs(2*k-3)==5])
    # Q40
    print('Q40',[k for k in range(-100,101) if abs(k-3)<2])
    # Q44
    P=x**5-3*x**3+x+1
    print('Q44',sp.factor(P), sp.real_roots(P), len(set(sp.real_roots(P))), sp.count_roots(P))
    print(' Q44 nroots',sp.Poly(P).nroots())
    # sign changes on grid
    xs=[ -3+i*1e-4 for i in range(60001)]; vals=[float(P.subs(x,0)) ]
    Pf=sp.lambdify(x,P); sc=0; prev=Pf(xs[0]); zeros=0
    for xv in xs[1:]:
        cur=Pf(xv)
        if cur==0: zeros+=1
        if prev*cur<0: sc+=1
        prev=cur
    print(' Q44 grid sign changes',sc,'exact zeros on grid',zeros, 'disc', sp.discriminant(P))
    # Q48
    print('Q48',sp.sqrt(10**2-6**2)); Ax,Ay=0,sp.sqrt(64); print(' Q48 coords AB',sp.sqrt((0+6)**2+Ay**2))
    # Q52
    dom=sp.calculus.util.continuous_domain(1/(x**2-4),x,sp.S.Reals); print('Q52',dom)
    optA=sp.Union(sp.Interval.open(-sp.oo,-2),sp.Interval.open(-2,2),sp.Interval.open(2,sp.oo)); print(' Q52 A eq',optA==dom)
    # Q56
    print('Q56',len([(i,j) for i in range(1,11) for j in range(1,11) if i+j==10]))
    # Q60
    print('Q60',len(list(itertools.combinations(range(6),3))), math.comb(6,3))
    # Q64
    print('Q64',[(t_,30-t_) for t_ in range(31) if 2*t_+4*(30-t_)==88])
    # Q68
    print('Q68',sp.Rational(240,80)+sp.Rational(240,60))
    # Q72
    print('Q72',[N for N in range(10,100) if N//10+N%10==11 and (N%10)*10+N//10-N==27])
    # Q76
    I=sp.integrate(sp.log(x)/sp.sqrt(x),(x,0,1)); print('Q76',I, mp.quad(lambda t: mp.log(t)/mp.sqrt(t),[0,1]))
    # Q80
    M=sp.Matrix([[2,1],[1,2]]); print('Q80',M.eigenvals(), sp.solve(sp.det(M-x*sp.eye(2)),x))
    # Q84
    A=sp.Matrix([[1,1],[2,4]]); B=sp.Matrix([30,88]); print('Q84',A.inv()*B, sp.solve([x+y-30,2*x+4*y-88],[x,y]))
if __name__=='__main__':
    main()
