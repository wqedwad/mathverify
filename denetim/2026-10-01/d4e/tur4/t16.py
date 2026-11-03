import sys
from ortak import *

TT = {"name": "t", "domain": "real"}
XT = [X, TT]


def cases():
    out = []
    forms = {  # all divergent
        "O1 1/(1+t^2 sin^2 t)": "Integral(1/(1 + t**2*sin(t)**2), (t, 0, oo))",
        "O2 1/(1+t^4 sin^2 t)": "Integral(1/(1 + t**4*sin(t)**2), (t, 0, oo))",
        "O3 1/(1+t^2 (1-cos 2t)/2)": "Integral(1/(1 + t**2*(1 - cos(2*t))/2), (t, 0, oo))",
        "O4 1/(1+t^2 exp(-t^2 sin^2 t))": "Integral(1/(1 + t**2*exp(-t**2*sin(t)**2)), (t, 0, oo))",
        "O5 1/(1+t^2 sin(t)^2 cos(t)^2)": "Integral(1/(1 + t**2*sin(t)**2*cos(t)**2), (t, 0, oo))",
        "O6 1/(1+t^2 tan(t)^2)": "Integral(1/(1 + t**2*tan(t)**2), (t, 0, oo))",
        "O7 1/(1+t^2 Abs(sin t))": "Integral(1/(1 + t**2*Abs(sin(t))), (t, 0, oo))",
        "O8 1/(1+t^2 sin(t)^2) at -oo": "Integral(1/(1 + t**2*sin(t)**2), (t, -oo, 0))",
        "O9 1/(1+t^2 sin(t^2)^2)": "Integral(1/(1 + t**2*sin(t**2)**2), (t, 0, oo))",
        "O10 1/(1 + t^2 * Max(sin t, 0))": "Integral(1/(1 + t**2*Max(sin(t), 0)), (t, 0, oo))",
        "O11 1/(1+t^2 sin^2(sqrt t))": "Integral(1/(1 + t**2*sin(sqrt(t))**2), (t, 0, oo))",
        "O12 0+ 1/(t^2 + cos(1/t)^2) ": "Integral(1/(t**2 + cos(1/t)**2), (t, 0, 1))",
        "O13 0+ 1/(t + t*sin(1/t))": "Integral(1/(t + t*sin(1/t)), (t, 0, 1))",
        "O14 1/(2+t^2 sin t)": "Integral(1/(2 + t*sin(t))**2, (t, 0, oo))",
    }
    for k, I in forms.items():
        out.append((f"OSC evaluate 0*[{k}] + 1: 1", ev1(f"0*{I} + 1", vars_=[TT]), sol("1"), NOTOK, None))
        out.append((f"OSC der x + 0*[{k}] at 0: 1", der(f"x + 0*{I}", "0", vars_=XT), sol("1"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
