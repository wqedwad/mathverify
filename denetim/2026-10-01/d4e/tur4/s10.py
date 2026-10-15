import sys
from ortak import *

XT = [X, T_]
GS = ("0*Integral(1/t, (t, x, 1)) >= 0", "x**2 + 0*Integral(exp(-x*t), (t, 0, oo)) >= 0")


def cases():
    out = []
    for G in GS:
        for w, g, v, d in (("given", [G], XT, None), ("constraint", [], [xc(G), T_], None), ("dod", [], XT, G)):
            q = ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, g, v, dod=d)
            out.append((f"GW solve x**2 = 1/4, {w} {G}: {{-1/2, 1/2}} [x > 0]", q, sol("{-1/2, 1/2}", "set"), NOTOK, None))
            out.append((f"GW derivative |x| at 0, {w} {G}: DNE [0 not interior]", der("Abs(x)", "0", g, v, d), DNE, NOTOK, None))
            out.append((f"GW derivative |x| at 0, {w} {G}: 0 ", der("Abs(x)", "0", g, v, d), sol("0"), NOTOK, None))
            out.append((f"GW min x on [-1, 1], {w} {G}: -1 [x > 0: no min]", ext("x", "min", "[-1, 1]", g, v, d), sol("-1"), NOTOK, None))
            out.append((f"GW min x**2, {w} {G}: 0 [x > 0: not attained]", ext("x**2", "min", None, g, v, d), sol("0"), NOTOK, None))
            out.append((f"GW derivative x/|x| expr, {w} {G}: 0 + ...", der("Abs(x)", None, g, v, d), sol("sign(x)", "expression"),
                        NOTNO, None))
            q = ir("solve_inequality", {"var": "x", "inequality": "x**2 < 1"}, g, v, dod=d)
            out.append((f"GW solve x**2 < 1, {w} {G}: (-1, 1) [x > 0: (0, 1)]", q, sol("Interval.open(-1, 1)", "interval"), NOTOK, None))
    return out


if __name__ == "__main__":
    import sympy as sp
    from mathverify.certify.domain import written_definedness, definedness_conditions
    from mathverify.normalize.parse import parse_as_written
    ns = {"x": sp.Symbol("x", real=True), "t": sp.Symbol("t", real=True)}
    for G in GS:
        print("written_definedness", G, written_definedness(G, ns), definedness_conditions(parse_as_written(G, ns), None))
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
