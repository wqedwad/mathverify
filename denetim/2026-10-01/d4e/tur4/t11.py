import sys
from ortak import *


def d(f, claim, label, exp=NOTOK, vars_=None, order=None):
    return (label, der(f, None, vars_=vars_, order=order), sol(claim, "expression"), exp, None)


def cases():
    out = []
    out.append(d("(x**2)**(S(1)/3)", "2/(3*cbrt(x))", "CUSP (x^2)^(1/3): 2/(3 cbrt x) textbook", exp=NOTNO))
    out.append(d("cbrt(x**2)", "2/(3*cbrt(x))", "CUSP cbrt(x^2): 2/(3 cbrt x) textbook", exp=NOTNO))
    out.append(d("(x**2)**(S(1)/3)", "2*x/(3*(x**2)**(S(2)/3))", "CUSP (x^2)^(1/3): SymPy form", exp=NOTNO))
    out.append(d("Abs(x + (x**2)**(S(1)/3))**(S(3)/2)", "Piecewise((0, Eq(x, 0)), (3*sqrt(Abs(x + (x**2)**(S(1)/3)))*sign(x + (x**2)**(S(1)/3))*(1 + 2*x/(3*(x**2)**(S(2)/3)))/2, Ne(x, 0)))",
                 "CUSP2 |x + |x|^(2/3)|^(3/2): PW value 0 at corner 0"))
    out.append(d("(x**2)**(S(1)/3)", "Piecewise((0, Eq(x, 0)), (2*x/(3*(x**2)**(S(2)/3)), Ne(x, 0)))", "CUSP3 (x^2)^(1/3): PW value 0 at cusp"))
    out.append(d("Abs(x)**(S(2)/3)", "Piecewise((0, Eq(x, 0)), (2*sign(x)/(3*Abs(x)**(S(1)/3)), Ne(x, 0)))", "CUSP3 |x|^(2/3): PW value 0 at cusp"))
    out.append(d("Abs(x)", "Piecewise((0, Eq(x, 0)), (sign(x), Ne(x, 0)))", "CUSP3 |x|: PW value 0 at corner ctrl"))
    out.append(d("sqrt(x**2)", "Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", "CUSP3 sqrt(x^2): PW value 0"))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
