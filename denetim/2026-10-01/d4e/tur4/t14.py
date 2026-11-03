import sys
from ortak import *

ALL = {"CORRECT", "UNKNOWN", "INCORRECT"}


def cases():
    out = []
    for G, lab in (("sqrt(x - 1/2) >= 0", "sqrt(x-1/2)>=0 [x>=1/2]"), ("sqrt(2*x - 1) >= 0", "sqrt(2x-1)>=0"),
                   ("sqrt(x) + sqrt(1 - x) > 0", "sqrt(x)+sqrt(1-x)>0 [0<=x<=1]"), ("log(x) < 10", "log x < 10 [0<x<e^10]")):
        for w, g, v, d in (("given", [G], [X], None), ("constraint", [], [xc(G)], None), ("dod", [], [X], G)):
            out.append((f"EXN min x**2 on [-1, 1], {w} {lab}: 0 / 1/4", ext("x**2", "min", "[-1, 1]", g, v, d), sol("0"),
                        NOTOK, None))
            out.append((f"EXN min x on [-1, 1], {w} {lab}: -1", ext("x", "min", "[-1, 1]", g, v, d), sol("-1"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
