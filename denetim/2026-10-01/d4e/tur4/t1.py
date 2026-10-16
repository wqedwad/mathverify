import sys
from ortak import *

BP = {"name": "b", "domain": "positive_real"}
BN = {"name": "b", "domain": "nonneg_real"}
AP = {"name": "a", "domain": "positive_real"}
XPOS = {"name": "x", "domain": "positive_real"}
TT = {"name": "t", "domain": "real"}


def cases():
    out = []
    # G: _point_not_interior drops conditions with a free parameter
    out.append(("PNI der x + 0*sqrt(b*x) at 0, b>0: 1 [0 is an end for every b]", der("x + 0*sqrt(b*x)", "0", vars_=[X, BP]), sol("1"), NOTOK, None))
    out.append(("PNI der x**2 + 0*sqrt(b*x) at 0, b>0: 0", der("x**2 + 0*sqrt(b*x)", "0", vars_=[X, BP]), sol("0"), NOTOK, None))
    out.append(("PNI tan x + 0*sqrt(b*x) at 0, b>0: y = x", tan("x + 0*sqrt(b*x)", "0", vars_=[X, BP]), sol("y = x", "equation"), NOTOK, None))
    out.append(("PNI der x + 0*sqrt(b - x) at 0, b>=0: 1 [b=0 end]", der("x + 0*sqrt(b - x)", "0", vars_=[X, BN]), sol("1"), NOTOK, None))
    out.append(("PNI der x + 0*log(b + x) at 0, b>0: 1 ctrl ok", der("x + 0*log(b + x)", "0", vars_=[X, BP]), sol("1"), {"CORRECT", "UNKNOWN"}, None))
    out.append(("PNI der x + 0*acos(x - b) at 0, b>=0: 1 [b=0 inside; b>2 undefined]", der("x + 0*acos(x - b)", "0", vars_=[X, BN]), sol("1"), NOTOK, None))
    out.append(("PNI der x + 0*sqrt(b*x) at 0, given b > 0: 1", der("x + 0*sqrt(b*x)", "0", givens=["b > 0"], vars_=[X, {"name": "b", "domain": "real"}]), sol("1"), NOTOK, None))
    # extremum: a symbol only in a written condition
    out.append(("EXT min x**2 + 0*sqrt(x - b) (no interval), b>0: 0 [min b**2]", ext("x**2 + 0*sqrt(x - b)", "min", None, vars_=[X, BP]), sol("0"), NOTOK, None))
    out.append(("EXT min x**2 + 0*sqrt(b*x - 1) (no interval), b>0: 0", ext("x**2 + 0*sqrt(b*x - 1)", "min", None, vars_=[X, BP]), sol("0"), NOTOK, None))
    out.append(("EXT max x + 0*sqrt(b - x) on [0,1], b>0: 1 [b<1 undefined]", ext("x + 0*sqrt(b - x)", "max", "[0, 1]", vars_=[X, BP]), sol("1"), NOTOK, None))
    # majorant with a declared-sign symbol: generic limit
    I1 = "Integral(1/((x - 1)**2*t**2 + 1), (t, 1, oo))"   # diverges at x = 1
    I2 = "Integral(exp(-(x - 1)**2*t), (t, 0, oo))"         # diverges at x = 1
    out.append(("MAJ der x**2 + 0*I1 at 1, x>0: 2 [undefined at 1]", der(f"x**2 + 0*{I1}", "1", vars_=[XPOS, TT]), sol("2"), NOTOK, None))
    out.append(("MAJ der x**2 + 0*I2 at 1, x>0: 2", der(f"x**2 + 0*{I2}", "1", vars_=[XPOS, TT]), sol("2"), NOTOK, None))
    out.append(("MAJ der x**2 + 0*I1 at 1, x real: 2", der(f"x**2 + 0*{I1}", "1", vars_=[X, TT]), sol("2"), NOTOK, None))
    out.append(("MAJ evaluate 0*Integral(1/((a-1)**2*t**2+1),(t,1,oo)) + 1, a>0: 1", ev1("0*Integral(1/((a - 1)**2*t**2 + 1), (t, 1, oo)) + 1", vars_=[AP, TT]), sol("1"), NOTOK, None))
    out.append(("MAJ evaluate 0*Integral(exp(-(a-1)**2*t),(t,0,oo)) + 1, a>0: 1", ev1("0*Integral(exp(-(a - 1)**2*t), (t, 0, oo)) + 1", vars_=[AP, TT]), sol("1"), NOTOK, None))
    out.append(("MAJ solve x**2 - 1 + 0*I1 = 0, x>0: {1}", ir("solve_equation", {"var": "x", "equation": f"x**2 - 1 + 0*{I1} = 0"}, vars_=[XPOS, TT]), sol("{1}", "set"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
