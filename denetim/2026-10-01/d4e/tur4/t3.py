import sys
from ortak import *


def d(f, claim, label, exp=NOTOK, givens=(), vars_=None):
    return (label, der(f, None, givens=givens, vars_=vars_), sol(claim, "expression"), exp, None)


def cases():
    out = []
    # hidden kinks (no switch atom): value at a corner -> convention (UNKNOWN), never CORRECT
    out.append(d("sqrt(x**2 - 2*x + 1)", "sign(x - 1)", "HK |x-1| as sqrt(x^2-2x+1): sign(x-1) [value 0 at corner 1]"))
    out.append(d("Abs(x - 1)", "sign(x - 1)", "HK ctrl |x-1|: sign(x-1)"))
    out.append(d("sqrt(1 - cos(x)**2)", "sign(sin(x))*cos(x)", "HK |sin x| as sqrt(1-cos^2): sign(sin x) cos x [value at k pi]"))
    out.append(d("acos(cos(x))", "sign(sin(x))", "HK acos(cos x): sign(sin x) [value 0 at k pi corners]"))
    out.append(d("asin(sin(x))", "sign(cos(x))", "HK asin(sin x): sign(cos x) [value 0 at corners]"))
    out.append(d("acos(1 - 2*x**2)", "2*sign(x)/sqrt(1 - x**2)", "HK acos(1-2x^2): 2 sign(x)/sqrt(1-x^2) [value 0 at corner 0]"))
    out.append(d("asin(2*x/(1 + x**2))", "2*sign(1 - x**2)/(1 + x**2)", "HK asin(2x/(1+x^2)): 2 sign(1-x^2)/(1+x^2) [value 0 at corners +-1]"))
    out.append(d("sqrt(x**4 - 2*x**2 + 1)", "2*x*sign(x**2 - 1)", "HK |x^2-1| as sqrt: 2x sign(x^2-1) [value at corners]"))
    out.append(d("sqrt(x**2*(x**2 + 1))", "sign(x)*(2*x**2 + 1)/sqrt(x**2 + 1)", "HK |x| sqrt(x^2+1) as sqrt: sign(x)(2x^2+1)/sqrt(x^2+1) [value 0 at 0]"))
    out.append(d("sqrt(4*x**2 + 4*x + 1)", "2*sign(2*x + 1)", "HK |2x+1| as sqrt: 2 sign(2x+1)"))
    out.append(d("x*sqrt(x**2 - 2*x + 1)", "sqrt(x**2 - 2*x + 1) + x*sign(x - 1)", "HK x|x-1| as sqrt: value at corner 1"))
    # hidden smooth points: claim undefined where f has a derivative -> RK-8 INCORRECT (never CORRECT)
    out.append(d("sqrt(x**4 - 4*x**3 + 6*x**2 - 4*x + 1)", "2*(x - 1)**2/(x - 1)", "HS (x-1)^2 as sqrt(expanded): 2(x-1)^2/(x-1) [undefined at 1, f'(1)=0]"))
    out.append(d("(x - 1)**2", "2*(x - 1)**2/(x - 1)", "HS ctrl (x-1)^2: 2(x-1)^2/(x-1)"))
    out.append(d("sqrt(x**4)", "2*x**3/x**2", "HS sqrt(x^4): 2x^3/x^2"))
    out.append(d("sqrt(x**6 + 2*x**4 + x**2)", "(3*x**2 + 1)*x/x", "HS sqrt(x^2 (x^2+1)^2)=|x|(x^2+1): kink at 0 actually [claim value 1 at 0 -> conv]"))
    out.append(d("sqrt(sin(x)**4)", "2*sin(x)**2*cos(x)/sin(x)", "HS sin^2 as sqrt(sin^4): 2 sin^2 cos/sin [undefined at k pi]"))
    out.append(d("sqrt(1 - sin(x)**2)**2", "-2*sin(x)*cos(x)**2/cos(x)", "HS cos^2 as sqrt(..)^2: hole at pi/2"))
    # single-point wrong value
    out.append(d("x**2", "2*x + 1 - sign(x)**2", "PT x^2: 2x + 1 - sign(x)^2 [wrong at 0]"))
    out.append(d("Abs(x)**3", "3*x*Abs(x) + 1 - sign(x)**2", "PT |x|^3: 3x|x| + 1 - sign^2 [wrong at 0]"))
    out.append(d("x**2", "2*x + 0**Abs(x)", "PT x^2: 2x + 0**|x| [wrong at 0]"))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
