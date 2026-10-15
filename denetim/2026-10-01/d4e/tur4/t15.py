import sys
from ortak import *

XPOS = {"name": "x", "domain": "positive_real"}
TT = {"name": "t", "domain": "real"}


def cases():
    out = []
    forms = {
        "F1 0+ 1/(t + (x-1)^2 sqrt t)": "Integral(1/(t + (x - 1)**2*sqrt(t)), (t, 0, 1))",
        "F2 0+ 1/(t^2 + (x-1)^2 sqrt t)": "Integral(1/(t**2 + (x - 1)**2*sqrt(t)), (t, 0, 1))",
        "F3 0+ 1/(t*((x-1)^2/sqrt(t) + 1))": "Integral(1/(t*((x - 1)**2/sqrt(t) + 1)), (t, 0, 1))",
        "F4 0+ 1/(sqrt(t)*(sqrt(t) + (x - 1)**2))": "Integral(1/(sqrt(t)*(sqrt(t) + (x - 1)**2)), (t, 0, 1))",
        "F5 oo 1/(t*((x-1)^2*t + 1))": "Integral(1/(t*((x - 1)**2*t + 1)), (t, 1, oo))",
        "F6 oo 1/((x-1)^2*t^2 + sqrt(t))": "Integral(1/((x - 1)**2*t**2 + sqrt(t)), (t, 1, oo))",
        "F7 oo exp(-t*(x-1)**2)/sqrt(t)... ": "Integral(1/((x - 1)**4*t**2 + 1), (t, 0, oo))",
        "F8 oo atan(t)/((x-1)^2 t^2 + 1)": "Integral(atan(t)/((x - 1)**2*t**2 + 1), (t, 1, oo))",
        "F9 oo sin(t)^2/((x-1)^2 t^2 + 1)": "Integral(sin(t)**2/((x - 1)**2*t**2 + 1), (t, 1, oo))",
    }
    for k, I in forms.items():
        out.append((f"MAJ2 der x**2 + 0*[{k}] at 1, x>0: 2", der(f"x**2 + 0*{I}", "1", vars_=[XPOS, TT]), sol("2"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
