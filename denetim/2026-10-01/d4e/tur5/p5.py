"""p5: improper integrals with the task variable / a parameter: the finite part beside the (new) majorant."""
import sys
from ortak import *

XP_ = {"name": "x", "domain": "positive_real"}
AN = {"name": "a", "domain": "nonneg_real"}
AP = {"name": "a", "domain": "positive_real"}


def solve(eq, vars_):
    return ir("solve_equation", {"var": "x", "equation": eq}, vars_=vars_)


def cases():
    out = []
    I1 = "Integral(1/(t**2 - x**2), (t, 1, oo))"          # pole at t = |x| when |x| >= 1
    out.append(("der x^2+0*I1 at 2 (pole t=2): 4", der(f"x**2 + 0*{I1}", "2", vars_=[X, T_]), sol("4"), NOTOK, None))
    out.append(("solve x^2-4+0*I1=0: {-2,2}", solve(f"x**2 - 4 + 0*{I1} = 0", [X, T_]), sol("{-2, 2}", "set"), NOTOK, None))
    out.append(("ctrl der x^2+0*I1 at 1/2: 1", der(f"x**2 + 0*{I1}", "1/2", vars_=[X, T_]), sol("1"), NOTNO, None))
    I2 = "Integral(1/(t**2 + x*t), (t, 1, oo))"           # pole at t = -x when x <= -1
    out.append(("solve x + 0*I2 = -2: {-2}", solve(f"x + 0*{I2} = -2", [X, T_]), sol("{-2}", "set"), NOTOK, None))
    out.append(("der x^2+0*I2 at -2: -4", der(f"x**2 + 0*{I2}", "-2", vars_=[X, T_]), sol("-4"), NOTOK, None))
    I3 = "Integral(exp(-t)/(t - x), (t, 0, oo))"          # pole inside for x > 0
    out.append(("der x^2+0*I3 at 1 (x>0): 2", der(f"x**2 + 0*{I3}", "1", vars_=[XP_, T_]), sol("2"), NOTOK, None))
    I4 = "Integral(sin(t)/(t + x), (t, 1, oo))"           # pole for x <= -1
    out.append(("der x^2+0*I4 at -2 (x real): -4", der(f"x**2 + 0*{I4}", "-2", vars_=[X, T_]), sol("-4"), NOTOK, None))
    I5 = "Integral(exp(-x*t), (t, 1, oo))"                # diverges for x <= 0
    out.append(("der x^2+0*I5 at 0 (x real): 0", der(f"x**2 + 0*{I5}", "0", vars_=[X, T_]), sol("0"), NOTOK, None))
    out.append(("solve x + 0*I5 = 0: {0}", solve(f"x + 0*{I5} = 0", [X, T_]), sol("{0}", "set"), NOTOK, None))
    I6 = "Integral(1/(t + a), (t, 0, 1))"                 # a >= 0: diverges at a = 0
    out.append(("a>=0: der x^2 + 0*I6 at 1 (a=0 diverges)", der(f"x**2 + 0*{I6}", "1", vars_=[X, T_, AN]), sol("2"), NOTOK, None))
    I7 = "Integral(1/(t**2 + a*t), (t, 1, oo))"           # a >= 0: fine everywhere; ctrl
    out.append(("ctrl a>=0: der x^2 + 0*I7 at 1", der(f"x**2 + 0*{I7}", "1", vars_=[X, T_, AN]), sol("2"), NOTNO, None))
    I8 = "Integral(1/(t - a), (t, 1, oo))"                # diverges for all a
    out.append(("a>0: der x^2 + 0*I8 at 1", der(f"x**2 + 0*{I8}", "1", vars_=[X, T_, AP]), sol("2"), NOTOK, None))
    I9 = "Integral(1/((t - a)**2 + 1), (t, 0, oo))"       # converges for all a
    out.append(("ctrl a real: der x^2 + 0*I9 at 1", der(f"x**2 + 0*{I9}", "1", vars_=[X, T_, A_]), sol("2"), NOTNO, None))
    I10 = "Integral(1/(t**2 - a), (t, 2, oo))"             # a > 0: pole at sqrt(a) >= 2 when a >= 4
    out.append(("a>0: der x^2 + 0*I10 at 1", der(f"x**2 + 0*{I10}", "1", vars_=[X, T_, AP]), sol("2"), NOTOK, None))
    I11 = "Integral(sqrt(t)/(t**2 - x), (t, 0, 1))"        # x in (0,1]: pole
    out.append(("der x^2+0*I11 at 1/4 (pole t=1/2): 1/2", der(f"x**2 + 0*{I11}", "1/4", vars_=[X, T_]), sol("1/2"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
