import sys
from ortak import *


def d(f, claim, label, exp=NOTOK, vars_=None, at=None):
    return (label, der(f, at, vars_=vars_), sol(claim, "expression" if at is None else "value"), exp, None)


def cases():
    out = []
    # claim with a gap where f has a derivative (RK-8: INCORRECT, never CORRECT)
    out.append(d("x**2", "Piecewise((2*x, x > 0), (2*x, x < 0))", "PG (x^2)': PW gap at 0"))
    out.append(d("x**2", "Piecewise((2*x, Ne(x, 0)))", "PG (x^2)': PW only Ne(x,0)"))
    out.append(d("x**2", "Piecewise((2*x, x**2 > 0))", "PG (x^2)': PW x^2>0"))
    out.append(d("x**3", "Piecewise((3*x**2, x < 1), (3*x**2, x > 1))", "PG (x^3)': PW gap at 1"))
    out.append(d("sin(x)", "Piecewise((cos(x), sin(x) > 0), (cos(x), sin(x) < 0))", "PG (sin x)': PW gap at k pi"))
    out.append(d("x**2", "2*x*Piecewise((1, x > 0), (1, x < 0))", "PG (x^2)': 2x*PW gap"))
    out.append(d("x**2", "Piecewise((2*x**2/x, Ne(x, 0)), (0, Eq(x, 0)))", "PG ctrl (x^2)': PW filled at 0 [right]", exp=NOTNO))
    out.append(d("x**2", "Piecewise((2*x**2/x, Ne(x, 0)), (1, Eq(x, 0)))", "PW wrong value at 0: 1 [f'(0)=0]"))
    out.append(d("Abs(x)**3", "Piecewise((3*x*Abs(x), Ne(x, 0)), (1, Eq(x, 0)))", "PW |x|^3 wrong value at 0"))
    out.append(d("x*Abs(x)", "Piecewise((2*x**2/Abs(x), Ne(x, 0)), (5, Eq(x, 0)))", "PW x|x| wrong value at 0: 5 [f'(0)=0]"))
    out.append(d("x**2", "Piecewise((1, Eq(x, 0)), (2*x, Ne(x, 0)))", "PW (x^2)': value 1 at 0 [wrong]"))
    out.append(d("x**2", "Piecewise((2*x, x > 0), (2*x + 1, x <= 0))", "PW (x^2)': wrong on x<=0 [ctrl, should be INCORRECT]"))
    # kink claims with Piecewise branch hiding: value at a corner/cusp
    out.append(d("Abs(x)", "Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", "PK |x|: PW(0 at 0, x/|x|) value at corner"))
    out.append(d("Abs(x)", "Piecewise((7, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", "PK |x|: PW(7 at 0, x/|x|) value at corner"))
    out.append(d("Abs(x)**(S(2)/3)", "Piecewise((0, Eq(x, 0)), (2*x/(3*Abs(x)**(S(4)/3)), Ne(x, 0)))", "PK |x|^(2/3): PW value 0 at cusp"))
    out.append(d("Max(x, 0)", "Piecewise((1/2, Eq(x, 0)), (Heaviside(x)*x/x, Ne(x, 0)))", "PK max(x,0): PW 1/2 at corner"))
    out.append(d("Abs(sin(x))", "Piecewise((0, Eq(sin(x), 0)), (cos(x)*sin(x)/Abs(sin(x)), Ne(sin(x), 0)))", "PK |sin x|: PW 0 at k pi"))
    out.append(d("Abs(x - 1)", "Piecewise((0, Eq(x, 1)), ((x - 1)/Abs(x - 1), Ne(x, 1)))", "PK |x-1|: PW 0 at corner 1"))
    # at a point
    out.append(d("Abs(x)", "Piecewise((0, Eq(x, 0)), (x/Abs(x), Ne(x, 0)))", "PKp |x|'(0) = PW... [value claim]", at="0"))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
