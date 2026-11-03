import sys
from ortak import *

DNE_ = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}
ALL = {"CORRECT", "UNKNOWN", "INCORRECT"}


def cases():
    out = []
    G = "x**2 + 0*sqrt(x - 1/2) >= 0"   # as written: x >= 1/2
    for w, g, v, d in (("given", [G], [X], None), ("constraint", [], [xc(G)], None), ("dod", [], [X], G)):
        out.append((f"EX2 min x**2 on [-1, 1], {w} [x>=1/2]: 0 (wrong; true 1/4)", ext("x**2", "min", "[-1, 1]", g, v, d), sol("0"), NOTOK, None))
        out.append((f"EX2 min x**2 on [-1, 1], {w} [x>=1/2]: 1/4 (true)", ext("x**2", "min", "[-1, 1]", g, v, d), sol("1/4"), ALL, None))
        out.append((f"EX2 max x on [-1, 1/4], {w} [x>=1/2: empty]: 1/4", ext("x", "max", "[-1, 1/4]", g, v, d), sol("1/4"), NOTOK, None))
        out.append((f"EX2 argmin x**2 on [-1, 1], {w}: 0 (wrong; true 1/2)", ir("extremum", {"f": "x**2", "var": "x", "which": "argmin", "interval": "[-1, 1]"}, g, v, shape="scalar", dod=d), sol("0"), NOTOK, None))
        out.append((f"EX2 min x**2 (no interval), {w}: 1/4 (true) ctrl", ext("x**2", "min", None, g, v, d), sol("1/4"), ALL, None))
        out.append((f"EX2 min x**2 (no interval), {w}: 0 (wrong) ctrl", ext("x**2", "min", None, g, v, d), sol("0"), NOTOK, None))
    G2 = "1/x > -100"                     # as written: x != 0 (parsed: x != 0 too) ctrl
    out.append(("EX2 ctrl given 1/x > -100: min x**2 on [-1,1] = 0", ext("x**2", "min", "[-1, 1]", [G2]), sol("0"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
