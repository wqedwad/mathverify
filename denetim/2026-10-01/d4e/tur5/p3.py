"""p3: RK-1/RK-6 power rule siblings, value at a corner, parameter zero, loose open-part families."""
import sys
from ortak import *

AR = {"name": "a", "domain": "real"}


def cases():
    out = []
    # value at a corner of a root (convention: UNKNOWN; never CORRECT)
    out.append(("sqrt(x2+x4)' sign-claim (value 0 at corner 0)", der("sqrt(x**2 + x**4)"),
                sol("sign(x)*(1 + 2*x**2)/sqrt(1 + x**2)", "expression"), NOTOK, None))
    out.append(("sqrt(x2+x4)' Piecewise value 0 at 0", der("sqrt(x**2 + x**4)"),
                sol("Piecewise(((x + 2*x**3)/sqrt(x**2 + x**4), Ne(x, 0)), (0, True))", "expression"), NOTOK, None))
    out.append(("sqrt((x-a)^2+(x-a)^4)' sign-claim, a real", der("sqrt((x - a)**2 + (x - a)**4)", vars_=[X, AR]),
                sol("sign(x - a)*(1 + 2*(x - a)**2)/sqrt(1 + (x - a)**2)", "expression"), NOTOK, None))
    out.append(("sqrt(1+sin x)' value at corner via sign", der("sqrt(1 + sin(x))"),
                sol("cos(x)/(2*sqrt(1 + sin(x)))", "expression"), NOTNO, None))
    # composition smoothing the corner: cos(sqrt(x**2 + x**4)) is C1 at 0 (f'(0) = 0): claim undefined at 0
    out.append(("cos(sqrt(x2+x4))' tb undefined at 0", der("cos(sqrt(x**2 + x**4))"),
                sol("-sin(sqrt(x**2 + x**4))*(x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTOK, None))
    out.append(("sqrt(x2+x4)**3' tb undefined at 0", der("sqrt(x**2 + x**4)**3"),
                sol("3*(x + 2*x**3)*(x**2 + x**4)/sqrt(x**2 + x**4)", "expression"), NOTOK, None))
    out.append(("(x2+x4)**(3/4)' tb undefined at 0", der("(x**2 + x**4)**(3/4)"),
                sol("3*(2*x + 4*x**3)/(4*(x**2 + x**4)**(1/4))", "expression"), NOTOK, None))
    out.append(("x*sqrt(x2+x4)' tb undefined at 0", der("x*sqrt(x**2 + x**4)"),
                sol("sqrt(x**2 + x**4) + x*(x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTOK, None))
    out.append(("sin(x)*sqrt(x2+x4)' tb undefined at 0", der("sin(x)*sqrt(x**2 + x**4)"),
                sol("cos(x)*sqrt(x**2 + x**4) + sin(x)*(x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTOK, None))
    # powers with unsolved zeros: f has a derivative at the zero when g vanishes there
    out.append(("(x-cos x)*sqrt(|x-cos x|)? f=(x-cos x)*|x-cos x|' tb/|u| form", der("(x - cos(x))*Abs(x - cos(x))"),
                sol("2*(1 + sin(x))*(x - cos(x))**2/Abs(x - cos(x))", "expression"), NOTOK, None))
    out.append(("sqrt((x-cos x)**2)**3' ", der("sqrt((x - cos(x))**2)**3"),
                sol("3*(1 + sin(x))*(x - cos(x))**3/Abs(x - cos(x))", "expression"), NOTOK, None))
    out.append(("((x-cos x)**2)**(3/4)' undefined on zeros", der("((x - cos(x))**2)**(3/4)"),
                sol("3*(1 + sin(x))*(x - cos(x))/(2*((x - cos(x))**2)**(1/4))", "expression"), NOTOK, None))
    out.append(("((x-cos x)**4)**(1/2)' undefined on zeros", der("sqrt((x - cos(x))**4)"),
                sol("2*(1 + sin(x))*(x - cos(x))**3/sqrt((x - cos(x))**4)", "expression"), NOTOK, None))
    out.append(("((x-cos x)**2)**(1/2) * (x - cos x)' : x|x| type", der("sqrt((x - cos(x))**2)*(x - cos(x))"),
                sol("2*(1 + sin(x))*(x - cos(x))**2/sqrt((x - cos(x))**2)", "expression"), NOTOK, None))
    # loose non-strict condition with a double zero inside: f = x**2 as written on all R
    out.append(("x^2+0*sqrt(sin^2(x)(2+cos x))' 2x+0*cot x", der("x**2 + 0*sqrt(sin(x)**2*(2 + cos(x)))"),
                sol("2*x + 0*cot(x)", "expression"), NOTOK, None))
    out.append(("constraint sin^2 x(2+cos x)>=0: (x^2)' 2x+0*cot x",
                der("x**2", vars_=[xc("sin(x)**2*(2 + cos(x)) >= 0")]), sol("2*x + 0*cot(x)", "expression"), NOTOK, None))
    out.append(("constraint cos(x) <= 1: (x^2)' 2x+0/(1-cos x)",
                der("x**2", vars_=[xc("cos(x) <= 1")]), sol("2*x + 0/(1 - cos(x))", "expression"), NOTOK, None))
    out.append(("constraint (x-1)**2*(2+sin x)>=0: (x^2)' 2x + 0/(x-1)",
                der("x**2", vars_=[xc("(x - 1)**2*(2 + sin(x)) >= 0")]), sol("2*x + 0/(x - 1)", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
