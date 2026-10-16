import sys
from ortak import *


def cases():
    out = []
    for f, c in (("Piecewise((x, x > 0), (-x, x <= 0))", "Piecewise((1, x > 0), (-1, x <= 0))"),
                 ("Piecewise((x**2, x >= 0), (x, x < 0))", "Piecewise((2*x, x >= 0), (1, x < 0))"),
                 ("Piecewise((x, x < 1), (2 - x, x >= 1))", "Piecewise((1, x < 1), (-1, x >= 1))"),
                 ("Max(x, x**2)", "Piecewise((2*x, x < 0), (1, x < 1), (2*x, x >= 1))"),
                 ("Min(x**2, 1)", "Piecewise((2*x, x**2 < 1), (0, x**2 >= 1))"),
                 ("Piecewise((x, x > 0), (0, x <= 0))", "Piecewise((1, x > 0), (0, x <= 0))"),
                 ("Piecewise((x, x > 0), (0, x <= 0))", "(1 + sign(x))/2"),
                 ("Piecewise((x, Abs(x) < 1), (sign(x), Abs(x) >= 1))", "Piecewise((1, Abs(x) < 1), (0, Abs(x) >= 1))"),
                 ("Piecewise((x, x**3 > 0), (-x, x**3 <= 0))", "sign(x)"),
                 ("Piecewise((x, x**2 > x), (x**2, x**2 <= x))", "Piecewise((1, x**2 > x), (2*x, x**2 <= x))"),
                 ("Piecewise((sin(x), sin(x) > 0), (-sin(x), sin(x) <= 0))", "sign(sin(x))*cos(x)"),
                 ("Piecewise((exp(x), x > 0), (1 + x, x <= 0))", "Piecewise((exp(x), x > 0), (1, x <= 0))"),
                 ("Max(x, -x) + Max(x - 1, 1 - x)", "sign(x) + sign(x - 1)"),
                 ("Max(x, -x)*Max(x, -x)", "2*x"),
                 ("Max(x**3, -x**3)", "3*x**2*sign(x)"),
                 ("Max(sqrt(x**2), 0)", "sign(x)"),
                 ("x*Max(x, -x)", "2*Max(x, -x)"),
                 ("Max(x, -x)**(1/2)", "sign(x)/(2*sqrt(Abs(x)))"),
                 ("Max(x, 2*x)", "Piecewise((1, x < 0), (2, x >= 0))"),
                 ("Min(x, 2*x)", "Piecewise((2, x < 0), (1, x >= 0))"),
                 ("Max(x, 2*x)", "(3 + sign(x))/2"),
                 ("Max(x, -x, 2*x)", "Piecewise((-1, x < 0), (2, x >= 0))"),
                 ("Abs(x) + Max(x, -x)", "2*sign(x)"),
                 ("Abs(x - 1)*sign(x - 1)", "2*Abs(x - 1)"),
                 ("sign(x)*x**2 + Abs(x)", "2*Abs(x) + sign(x)")):
        out.append((f"KINK derivative {f}: {c} [value at a corner]", der(f), sol(c, "expression"), NOTOK, None))
    out.append(("KINK ctrl derivative Max(x, 2*x): Piecewise((1, x < 0), (2, x > 0))", der("Max(x, 2*x)"),
                sol("Piecewise((1, x < 0), (2, x > 0))", "expression"), NOTNO, None))
    # derivative at the corner itself
    for f, at, c in (("Max(x, 2*x)", "0", "1"), ("Piecewise((x, x < 1), (2 - x, x >= 1))", "1", "1"),
                     ("Piecewise((x**2, x >= 0), (x, x < 0))", "0", "0"), ("Max(x, -x, 2*x)", "0", "0")):
        out.append((f"KINK derivative {f} at {at}: {c} [corner]", der(f, at), sol(c), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
