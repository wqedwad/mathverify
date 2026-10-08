import sys
from ortak import *


def cases():
    out = []
    for f in ("Piecewise((x, x < 0), (x, x > 0))", "Piecewise((sin(x), x < 0), (sin(x), x > 0))", "Piecewise((x, x < 1), (x, x > 1))",
              "Piecewise((x**3, x < 0), (x**3, x > 0)) + x", "Piecewise((x, Abs(x) > 0))", "Piecewise((x, x**2 > 0))",
              "Piecewise((x, x < 0), (x, x > 0))*Abs(x) + x"):
        p = "1" if "x < 1" in f else "0"
        out.append((f"PWG derivative {f} at {p}: [undefined at {p}]", der(f, p), sol("1"), NOTOK, None))
        out.append((f"PWG tangent {f} at {p}", tan(f, p), sol(f"y = x" if p == "0" else "y = x", "equation"), NOTOK, None))
    out.append(("PWG max Piecewise((-x**2, x < 0), (-x**2, x > 0)) on [-1, 1]: 0 [not attained]",
                ext("Piecewise((-x**2, x < 0), (-x**2, x > 0))", "max", "[-1, 1]"), sol("0"), NOTOK, None))
    out.append(("PWG local_max Piecewise((-x**2, x < 0), (-x**2, x > 0)) on [-1, 1]: 0 [not attained]",
                ext("Piecewise((-x**2, x < 0), (-x**2, x > 0))", "local_max", "[-1, 1]"), sol("0"), NOTOK, None))
    out.append(("PWG min Piecewise((Abs(x), x < 0), (Abs(x), x > 0)) on [-1, 1]: 0 [not attained]",
                ext("Piecewise((Abs(x), x < 0), (Abs(x), x > 0))", "min", "[-1, 1]"), sol("0"), NOTOK, None))
    out.append(("PWG min Piecewise((x**2, x**2 > 0)) on [-1, 1]: 0", ext("Piecewise((x**2, x**2 > 0))", "min", "[-1, 1]"),
                sol("0"), NOTOK, None))
    out.append(("PWG derivative Piecewise((x**2, x < 0), (x**2, x > 0)): 2*x [ctrl]", der("Piecewise((x**2, x < 0), (x**2, x > 0))"),
                sol("2*x", "expression"), NOTNO, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
