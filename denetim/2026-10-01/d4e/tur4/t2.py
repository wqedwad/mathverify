import sys
from ortak import *

XPOS = {"name": "x", "domain": "positive_real"}
XN = {"name": "x", "domain": "nonneg_real"}
TT = {"name": "t", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
NPI = {"name": "n", "domain": "positive_integer"}


def cases():
    out = []
    forms = {
        "A oo 1/((x-1)^2 t^2+1)": "Integral(1/((x - 1)**2*t**2 + 1), (t, 1, oo))",
        "B oo t/((x-1)^2 t^3+1)": "Integral(t/((x - 1)**2*t**3 + 1), (t, 1, oo))",
        "C oo 1/(t^((x-1)^2+1))": "Integral(t**(-(x - 1)**2 - 1), (t, 1, oo))",
        "D 0+ exp(-(x-1)^2/t)/t": "Integral(exp(-(x - 1)**2/t)/t, (t, 0, 1))",
        "E oo exp(-(x-1)^2 t^2)": "Integral(exp(-(x - 1)**2*t**2), (t, 0, oo))",
        "F oo 1/((x-1)^2 t + 1)^2": "Integral(1/((x - 1)**2*t + 1)**2, (t, 0, oo))",
        "G oo (x-1)^2 free: 1/(t^2 (x-1)^2 + t)": "Integral(1/((x - 1)**2*t**2 + t), (t, 1, oo))",
        "H 0+ 1/sqrt(t) * 1/((x-1)^2 + sqrt(t))": "Integral(1/(sqrt(t)*((x - 1)**2 + sqrt(t))), (t, 0, 1))",
        "I oo cos(t)^2/((x-1)^2 t^2+1)": "Integral(cos(t)**2/((x - 1)**2*t**2 + 1), (t, 1, oo))",
        "J oo 1/((x-1)^2 t^2 + 1) at -oo": "Integral(1/((x - 1)**2*t**2 + 1), (t, -oo, -1))",
    }
    for k, I in forms.items():
        out.append((f"MAJ der x**2 + 0*[{k}] at 1, x>0: 2", der(f"x**2 + 0*{I}", "1", vars_=[XPOS, TT]), sol("2"), NOTOK, None))
    # parameter declared positive, evaluate
    out.append(("MAJ-a evaluate 0*Integral(1/((a-1)**2*t**2+1),(t,1,oo)) + a, a>0: a", ev1("0*Integral(1/((a - 1)**2*t**2 + 1), (t, 1, oo)) + a", vars_=[AP, TT]), sol("a"), NOTOK, None))
    out.append(("MAJ-n evaluate 0*Integral(1/((n-1)**2*t**2+1),(t,1,oo)) + 1, n pos int: 1", ev1("0*Integral(1/((n - 1)**2*t**2 + 1), (t, 1, oo)) + 1", vars_=[NPI, TT]), sol("1"), NOTOK, None))
    # simplify / antiderivative / tangent / limit / extremum on the same mechanism
    A = forms["A oo 1/((x-1)^2 t^2+1)"]
    out.append(("MAJ tangent x**2 + 0*A at 1, x>0: y = 2x - 1", tan(f"x**2 + 0*{A}", "1", vars_=[XPOS, TT]), sol("y = 2*x - 1", "equation"), NOTOK, None))
    out.append(("MAJ derivative expr x**2 + 0*A, x>0: 2x", der(f"x**2 + 0*{A}", None, vars_=[XPOS, TT]), sol("2*x", "expression"), NOTOK, None))
    out.append(("MAJ max -(x-1)**2 + 0*A on [1/2, 2], x>0: 0 [not attained]", ext(f"-(x - 1)**2 + 0*{A}", "max", "[1/2, 2]", vars_=[XPOS, TT]), sol("0"), NOTOK, None))
    out.append(("MAJ limit (x**2 + 0*A) at 1, x>0: 1 [ctrl: punctured, ok]", lim(f"x**2 + 0*{A}", "1", vars_=[XPOS, TT]), sol("1"), {"CORRECT", "UNKNOWN"}, None))
    out.append(("MAJ antiderivative 2x + 0*A, x>0: x**2", anti(f"2*x + 0*{A}", vars_=[XPOS, TT]), sol("x**2", "expression"), NOTOK, None))
    out.append(("MAJ simplify x + 0*A, x>0: x", ir("simplify", {"expr": f"x + 0*{A}"}, vars_=[XPOS, TT], shape="expression"), sol("x", "expression"), NOTOK, None))
    out.append(("MAJ solve ineq x + 0*A >= 1, x>0: [1, oo)", ir("solve_inequality", {"var": "x", "inequality": f"x + 0*{A} >= 1"}, vars_=[XPOS, TT]), sol("Interval(1, oo)", "interval"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
