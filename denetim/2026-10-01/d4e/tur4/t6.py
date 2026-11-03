import sys
from ortak import *

DNE_ = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}


def cases():
    out = []
    for G, lab in (("x != 0", "ctrl x!=0"), ("x/x > 0", "x/x>0"), ("x**2 + 0*log(x) >= 0", "0*log(x)"),
                   ("1/x != 0", "1/x!=0"), ("x + 0*sqrt(x - 1) > 0", "x+0sqrt(x-1)>0"), ("x > 0", "ctrl x>0"),
                   ("x**2 + 0*sqrt(x - 1/2) >= 0", "0*sqrt(x-1/2)")):
        for w, g, v, d in (("given", [G], [X], None), ("constraint", [], [xc(G)], None), ("dod", [], [X], G)):
            out.append((f"EI min x**2 on [-1, 1], {w} {lab}: 0", ext("x**2", "min", "[-1, 1]", g, v, d), sol("0"), NOTOK, None))
            out.append((f"EI max -x**2 on [-1, 1], {w} {lab}: 0", ext("-x**2", "max", "[-1, 1]", g, v, d), sol("0"), NOTOK, None))
            out.append((f"EI min x**2 on [0, 2], {w} {lab}: DNE (as written attained?)", ext("x**2", "min", "[0, 2]", g, v, d), DNE_,
                        NOTOK if "sqrt" in G else {"CORRECT", "UNKNOWN", "INCORRECT"}, None))
            out.append((f"EI local_min x**2 on [-1, 1], {w} {lab}: 0", ext("x**2", "local_min", "[-1, 1]", g, v, d), sol("0"), NOTOK, None))
            out.append((f"EI argmin x**2 on [-1, 1], {w} {lab}: x=0", ir("extremum", {"f": "x**2", "var": "x", "which": "argmin", "interval": "[-1, 1]"}, g, v, shape="scalar", dod=d), sol("0"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
