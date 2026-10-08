import sys
from ortak import *

XT = [X, T_]


def cases():
    out = []
    # FAM: more writings of the 4-member family check
    out.append(("FAM derivative x**2, given x > 10: 2*x + 0*cot(4*x)", der("x**2", None, ["x > 10"]),
                sol("2*x + 0*cot(4*x)", "expression"), NOTOK, None))
    out.append(("FAM derivative x**2, given x > 10: 2*x*cos(4*x)/cos(4*x)", der("x**2", None, ["x > 10"]),
                sol("2*x*cos(4*x)/cos(4*x)", "expression"), NOTOK, None))
    out.append(("FAM derivative x**3, x > 30 constraint: 3*x**2 + 0*csc(x)", der("x**3", None, [], [xc("x > 30")]),
                sol("3*x**2 + 0*csc(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative log(x - 20): 1/(x - 20) + 0*tan(x)", der("log(x - 20)"),
                sol("1/(x - 20) + 0*tan(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative exp(x), given x > 20: exp(x)*tan(x)/tan(x)", der("exp(x)", None, ["x > 20"]),
                sol("exp(x)*tan(x)/tan(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative x**2, x positive_real: 2*x*sin(x/7)/sin(x/7)", der("x**2", None, [], [XP]),
                sol("2*x*sin(x/7)/sin(x/7)", "expression"), NOTOK, None))
    out.append(("FAM derivative sin(x), given x > 10: cos(x) + 0*cot(x)", der("sin(x)", None, ["x > 10"]),
                sol("cos(x) + 0*cot(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative x**2 + log(x - 13): 2*x + 1/(x - 13) + 0*cot(x)", der("x**2 + log(x - 13)"),
                sol("2*x + 1/(x - 13) + 0*cot(x)", "expression"), NOTOK, None))
    # C: corners with no switch written (acos(cos x), sqrt of a square): a claim with a value at the corner
    out.append(("HID derivative acos(cos(x)): sign(sin(x)) [value at n*pi]", der("acos(cos(x))"),
                sol("sign(sin(x))", "expression"), NOTOK, None))
    out.append(("HID derivative asin(sin(x)): sign(cos(x)) [value at pi/2 + n*pi]", der("asin(sin(x))"),
                sol("sign(cos(x))", "expression"), NOTOK, None))
    out.append(("HID derivative sqrt(x**2 + x**4): sign(x)*(1 + 2*x**2)/sqrt(1 + x**2) [value at 0]",
                der("sqrt(x**2 + x**4)"), sol("sign(x)*(1 + 2*x**2)/sqrt(1 + x**2)", "expression"), NOTOK, None))
    out.append(("HID derivative sqrt(x**2 - 2*x + 1): sign(x - 1) [value at 1]", der("sqrt(x**2 - 2*x + 1)"),
                sol("sign(x - 1)", "expression"), NOTOK, None))
    out.append(("HID derivative sqrt(1 - cos(x)): sqrt(2)*cos(x/2)*sign(sin(x/2))/2 [value at 2n*pi]",
                der("sqrt(1 - cos(x))"), sol("sqrt(2)*cos(x/2)*sign(sin(x/2))/2", "expression"), NOTOK, None))
    out.append(("HID derivative sqrt(x**2 - 2*x + 1): 1 [wrong]", der("sqrt(x**2 - 2*x + 1)"),
                sol("1", "expression"), NOTOK, None))
    out.append(("HID derivative (x**2 + x**4)**(1/2) at 0: 0 [corner]", der("(x**2 + x**4)**(1/2)", "0"),
                sol("0"), NOTOK, None))
    out.append(("HID derivative acos(cos(x)) at 0: 0 [corner]", der("acos(cos(x))", "0"), sol("0"), NOTOK, None))
    out.append(("HID tangent acos(cos(x)) at 0: y = 0 [corner]", tan("acos(cos(x))", "0"), sol("y = 0", "equation"),
                NOTOK, None))
    out.append(("HID ctrl derivative acos(cos(x)): sin(x)/Abs(sin(x))", der("acos(cos(x))"),
                sol("sin(x)/Abs(sin(x))", "expression"), NOTNO, None))
    # D: Piecewise with a gap, Piecewise kinks, Heaviside
    PG = "Piecewise((x**2, x < 0), (x**2, x > 0))"
    out.append((f"PW derivative {PG} at 0: 0 [undefined at 0]", der(PG, "0"), sol("0"), NOTOK, None))
    out.append((f"PW tangent {PG} at 0: y = 0 [undefined at 0]", tan(PG, "0"), sol("y = 0", "equation"), NOTOK, None))
    out.append((f"PW min {PG} on [-1, 1]: 0 [not attained]", ext(PG, "min", "[-1, 1]"), sol("0"), NOTOK, None))
    q = ir("solve_equation", {"var": "x", "equation": f"{PG} = 0"}, [], [X])
    out.append((f"PW solve {PG} = 0: {{0}}", q, sol("{0}", "set"), NOTOK, None))
    PG2 = "Piecewise((x + 1, x < 0), (x + 1, x > 0))"
    out.append((f"PW derivative {PG2} at 0: 1 [undefined at 0]", der(PG2, "0"), sol("1"), NOTOK, None))
    for f, c in (("Piecewise((x, x > 0), (-x, True))", "Piecewise((1, x > 0), (-1, True))"),
                 ("Piecewise((x**2, x >= 0), (x, True))", "Piecewise((2*x, x >= 0), (1, True))"),
                 ("Piecewise((x, x < 1), (2 - x, True))", "Piecewise((1, x < 1), (-1, True))"),
                 ("Heaviside(x)*x", "Heaviside(x)"), ("Max(x, x**2)", "Piecewise((2*x, x < 0), (1, x < 1), (2*x, True))"),
                 ("Max(x, 0, -x)", "sign(x)"), ("Abs(Abs(x) - 1)", "sign(Abs(x) - 1)*sign(x)"),
                 ("Min(x**2, 1)", "Piecewise((2*x, x**2 < 1), (0, True))"),
                 ("Abs(x)*Heaviside(x)", "Heaviside(x)"), ("Max(x, 0)**1", "Heaviside(x)"),
                 ("Piecewise((x, x > 0), (0, True))", "Heaviside(x)"),
                 ("Piecewise((x, Abs(x) < 1), (sign(x), True))", "Piecewise((1, Abs(x) < 1), (0, True))")):
        out.append((f"KINK derivative {f}: {c} [value at a corner]", der(f), sol(c, "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
