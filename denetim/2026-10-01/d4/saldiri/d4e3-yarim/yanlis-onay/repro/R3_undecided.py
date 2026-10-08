"""D4E3-YO-3: a constraint / domain of discourse / limit given whose written definedness is undecided (a binder, a
closed condition) is read as having no condition: written_definedness drops DEFINEDNESS_UNDECIDED. Run as R1."""
from common import P, S, X, T, show

DNE = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}
G1 = "0*Integral(1/t, (t, x, 1)) >= 0"                  # exists iff x > 0
G2 = "x**2 + 0*Integral(exp(-x*t), (t, 0, oo)) >= 0"     # exists iff x > 0
G3 = "x + 0*tan(acot(2) + acot(1/2)) > 0"                # tan(pi/2): no value anywhere


def xc(c):
    return [{"name": "x", "domain": "real", "constraints": [c]}, T]


if __name__ == "__main__":
    XT = [X, T]
    show([
        (f"solve x**2 = 1/4, constraint {G1}: {{-1/2, 1/2}}", P("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                               vars_=xc(G1), shape="set"), S("{-1/2, 1/2}", "set")),
        (f"min x on [-1, 1], dod {G1}: -1", P("extremum", {"f": "x", "var": "x", "which": "min", "interval": "[-1, 1]"},
                                              vars_=XT, dod=G1), S("-1")),
        (f"derivative |x| at 0, constraint {G2}: DNE", P("derivative", {"f": "Abs(x)", "var": "x", "at": "0"}, vars_=xc(G2)), DNE),
        (f"limit |x|/x at 0, given {G1}: DNE", P("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, [G1], XT), DNE),
        (f"limit |x|/x at 0, given {G2}: DNE", P("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, [G2], XT), DNE),
        (f"solve x**2 = 1/4, constraint {G3}: {{1/2}}", P("solve_equation", {"var": "x", "equation": "x**2 = 1/4"},
                                                         vars_=xc(G3), shape="set"), S("{1/2}", "set")),
        (f"limit |x|/x at 0, dod {G3}: 1", P("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, vars_=XT, dod=G3), S("1")),
        (f"ctrl solve x**2 = 1/4, GIVEN {G1}: {{-1/2, 1/2}}", P("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, [G1],
                                                               vars_=XT, shape="set"), S("{-1/2, 1/2}", "set")),
        (f"ctrl solve x**2 = 1/4, GIVEN {G3}: {{1/2}}", P("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, [G3],
                                                         vars_=XT, shape="set"), S("{1/2}", "set")),
    ])
