import sys
from ortak import *

A_R = {"name": "a", "domain": "real"}
A_P = {"name": "a", "domain": "positive_real"}


def d(f, claim, label, exp=NOTOK, givens=(), vars_=None, order=None):
    return (label, der(f, None, givens=givens, vars_=vars_, order=order), sol(claim, "expression"), exp, None)


def cases():
    out = []
    # value at a kink (convention) -> never CORRECT
    out.append(d("Max(x, -x, 2*x - 1)", "Piecewise((-1, x < 0), (1, x < 1), (2, True))", "VK Max3 kinks 0,1: PW gives values"))
    out.append(d("Min(x, 1 - x)", "sign(1 - 2*x)", "VK Min(x,1-x): sign(1-2x) [0 at 1/2]"))
    out.append(d("Abs(x - Abs(x))", "-2*Heaviside(-x)", "VK |x-|x||=2max(-x,0): -2H(-x) [value -1 at 0]"))
    out.append(d("Abs(Abs(x) - 1)", "sign(Abs(x) - 1)*sign(x)", "VK ||x|-1|: kinks -1,0,1 values"))
    out.append(d("x*Heaviside(x)", "Heaviside(x)", "VK xH(x): H(x) [H(0)=1/2 at corner]"))
    out.append(d("Heaviside(x)", "0", "VK H(x)' = 0 [value at jump]"))
    out.append(d("Piecewise((0, x < 0), (x, True))", "Heaviside(x)", "VK PW ramp: H(x)"))
    out.append(d("Piecewise((x, Eq(x, 0)), (x + 1, True))", "1", "VK PW removable jump at 0: 1 [no derivative at 0]"))
    out.append(d("Piecewise((1, Eq(x, 0)), (x, True))", "1", "VK PW f(0)=1, else x: 1 [discontinuous at 0]"))
    out.append(d("Abs(x - a)", "sign(x - a)", "VK |x-a| a real: sign(x-a)", vars_=[X, A_R]))
    out.append(d("Abs(x - a)", "sign(x - a)", "VK |x-a| a>0: sign(x-a)", vars_=[X, A_P]))
    out.append(d("Abs(x - a)", "sign(x - a)", "VK |x-a| given a = 2: sign(x-a)", givens=["a = 2"], vars_=[X, A_R]))
    out.append(d("Abs(x - a)", "sign(x - 2)", "VK |x-a| given 2a = 4: sign(x-2)", givens=["2*a = 4"], vars_=[X, A_R]))
    out.append(d("Abs(x**2 - 2)", "2*x*sign(x**2 - 2)", "VK |x^2-2|: radical kinks"))
    out.append(d("Abs(x**3 - 3*x + 1)", "(3*x**2 - 3)*sign(x**3 - 3*x + 1)", "VK |cubic 3 roots|"))
    out.append(d("Abs(x**5 - x - 1)", "(5*x**4 - 1)*sign(x**5 - x - 1)", "VK |quintic| CRootOf kink"))
    out.append(d("Abs(x - cos(x))", "(1 + sin(x))*sign(x - cos(x))", "VK |x - cos x| unsolved kink"))
    out.append(d("Abs(exp(x) - 2)", "exp(x)*sign(exp(x) - 2)", "VK |e^x - 2|: kink log 2"))
    out.append(d("Abs(sin(x))*Abs(cos(x))", "cos(2*x)*sign(sin(2*x))", "VK |sin cos|: kinks k pi/2"))
    out.append(d("Abs(sin(x)) + Abs(x)", "cos(x)*sign(sin(x)) + sign(x)", "VK |sin x| + |x|: value at 0"))
    out.append(d("sign(x)*x**2", "2*Abs(x)", "VK sign(x) x^2 = x|x|: 2|x| ctrl", exp=NOTNO))
    out.append(d("sign(x)*x", "sign(x)", "VK sign(x) x = |x|: sign(x) [value at 0]"))
    out.append(d("sign(x)**2", "0", "VK sign(x)^2: 0 [jump at 0]"))
    out.append(d("Abs(sign(x))", "0", "VK |sign x|: 0 [jump at 0]"))
    out.append(d("x*Abs(x)", "2*sign(x)", "VK order2 x|x|'' = 2 sign(x) [value at 0]", order=2))
    out.append(d("Abs(x)**3", "6*sign(x)", "VK order3 |x|^3''' = 6 sign [value at 0]", order=3))
    out.append(d("x**2*Abs(x)", "6*x*sign(x)", "VK order2 x^2|x|'' = 6|x| ctrl", exp=NOTNO, order=2))
    out.append(d("Abs(x)*exp(x)", "exp(x)*sign(x) + Abs(x)*exp(x)", "VK |x| e^x: value at 0"))
    out.append(d("Abs(x)**(S(1)/2)*x", "3*sqrt(Abs(x))/2", "VK x sqrt|x| ctrl", exp=NOTNO))
    out.append(d("Abs(x)**(S(3)/2)", "3*sqrt(Abs(x))*sign(x)/2", "VK |x|^(3/2) ctrl", exp=NOTNO))
    out.append(d("Abs(x)**(S(1)/2)", "sign(x)/(2*sqrt(Abs(x))) + 0", "VK sqrt|x| ctrl", exp=NOTNO))
    out.append(d("Abs(x) + Abs(x - 1) + Abs(x - 2) + Abs(x - 3) + Abs(x - 4)", "sign(x) + sign(x - 1) + sign(x - 2) + sign(x - 3) + sign(x - 4)", "VK 5 kinks: budget"))
    out.append(d("Abs(x**4 - 10*x**2 + 1)", "(4*x**3 - 20*x)*sign(x**4 - 10*x**2 + 1)", "VK nested radical kinks"))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
