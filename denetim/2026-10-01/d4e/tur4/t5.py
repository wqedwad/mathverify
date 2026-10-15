import sys
from ortak import *

GS = {"A": "x + 0*sqrt(x - 1) > 0",      # as written x >= 1; parsed x > 0
      "B": "x/x > 0",                      # as written x != 0; parsed True
      "C": "x**2 + 0*log(x) >= 0",         # as written x > 0; parsed True
      }


def cases():
    out = []
    for k, G in GS.items():
        for w, g, v, d in (("given", [G], [X], None), ("constraint", [], [xc(G)], None), ("dod", [], [X], G)):
            # extremum
            if k == "A":
                out.append((f"GD{k} min x**2, {w}: 0 [x>=1: 1]", ext("x**2", "min", None, g, v, d), sol("0"), NOTOK, None))
                out.append((f"GD{k} min x on [-1, 2], {w}: -1 [x>=1: 1]", ext("x", "min", "[-1, 2]", g, v, d), sol("-1"), NOTOK, None))
                out.append((f"GD{k} solve x**2 = 1/4, {w}: {{1/2}} [x>=1: empty]", ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, g, v, dod=d), sol("{1/2}", "set"), NOTOK, None))
                out.append((f"GD{k} solve x**2 < 4, {w}: (0, 2) [x>=1: [1, 2)]", ir("solve_inequality", {"var": "x", "inequality": "x**2 < 4"}, g, v, dod=d), sol("Interval.open(0, 2)", "interval"), NOTOK, None))
                out.append((f"GD{k} der |x - 1/2| at 1/2, {w}: DNE [x>=1: outside]", der("Abs(x - 1/2)", "1/2", g, v, d), DNE, NOTOK, None))
                out.append((f"GD{k} der |x - 1| at 1, {w}: DNE [x>=1: end -> UNKNOWN]", der("Abs(x - 1)", "1", g, v, d), DNE, NOTOK, None))
                out.append((f"GD{k} tangent x**2 at 1/2, {w}: y = x - 1/4 [outside]", tan("x**2", "1/2", g, v, d), sol("y = x - 1/4", "equation"), NOTOK, None))
                out.append((f"GD{k} limit |x-1|/(x-1) at 1, {w}: DNE [x>=1: 1]", lim("Abs(x - 1)/(x - 1)", "1", g, v, d), DNE, NOTOK, None))
                out.append((f"GD{k} antiderivative 1/x, {w}: log(-x)? [x>=1: not real]", anti("1/x", g, v, d), sol("log(-x)", "expression"), NOTOK, None))
                out.append((f"GD{k} der expr |x - 1/2|, {w}: 1 [x>=1: 1 ok -> ctrl]", der("Abs(x - 1/2)", None, g, v, d), sol("1", "expression"), {"CORRECT", "UNKNOWN"}, None))
            if k in ("B", "C"):
                p0 = "0"
                out.append((f"GD{k} min x**2, {w}: 0 [0 excluded]", ext("x**2", "min", None, g, v, d), sol("0"), NOTOK, None))
                out.append((f"GD{k} min x**2 on [-1, 1], {w}: 0 [0 excluded]", ext("x**2", "min", "[-1, 1]", g, v, d), sol("0"), NOTOK, None))
                out.append((f"GD{k} solve x**3 = 0, {w}: {{0}} [excluded]", ir("solve_equation", {"var": "x", "equation": "x**3 = 0"}, g, v, dod=d), sol("{0}", "set"), NOTOK, None))
                out.append((f"GD{k} solve x**2 <= 0, {w}: {{0}} [excluded]", ir("solve_inequality", {"var": "x", "inequality": "x**2 <= 0"}, g, v, dod=d), sol("{0}", "set"), NOTOK, None))
                out.append((f"GD{k} der x**2 at 0, {w}: 0 [0 excluded]", der("x**2", "0", g, v, d), sol("0"), NOTOK, None))
                out.append((f"GD{k} tangent x**2 at 0, {w}: y = 0 [0 excluded]", tan("x**2", "0", g, v, d), sol("y = 0", "equation"), NOTOK, None))
                out.append((f"GD{k} limit x/x... |x|/x at 0 {w}: DNE ctrl", lim("Abs(x)/x", "0", g, v, d), DNE, NOTNO if k == "B" else NOTOK, None))
                out.append((f"GD{k} evaluate x**2 at? series sum k**2 k=-1..1 [no x] skip", ir("evaluate", {"expr": "x**2 - x**2 + 1"}, g, v, shape="scalar", dod=d), sol("1"), NOTNO, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
