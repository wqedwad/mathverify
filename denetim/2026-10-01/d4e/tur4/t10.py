import sys
from ortak import *

BR = {"name": "b", "domain": "real"}
BP = {"name": "b", "domain": "positive_real"}
BN = {"name": "b", "domain": "nonneg_real"}


def cases():
    out = []
    for f, vs, lab in (("x + 0*sqrt(x + b**2)", [X, BR], "b real [b=0: 0 end]"),
                       ("x + 0*sqrt(x*b**2)", [X, BR], "b real [b!=0: 0 end]"),
                       ("x + 0*sqrt(b*x)", [X, BN], "b>=0 [b>0: 0 end]"),
                       ("x + 0*sqrt(x + b)", [X, BN], "b>=0 [b=0: end]"),
                       ("x + 0*log(x + b)", [X, BP], "b>0 ctrl [interior]"),
                       ("x + 0*sqrt(b - x)", [X, BP], "b>0 [interior]"),
                       ("x + 0*sqrt(b**2 - x**2)", [X, BR], "b real [b=0: {0} only]"),
                       ("x + 0*acos(x/(b**2 + 1))", [X, BR], "acos ctrl interior"),
                       ("x + 0*sqrt(-x*b**2)", [X, BR], "b real [b!=0: 0 end]"),
                       ("x + 0*sqrt(x**2*b)", [X, BN], "b>=0 [all R]"),
                       ("x + 0*sqrt(x*(b**2 + 1))", [X, BR], "[0 end always]")):
        exp = NOTOK if "ctrl" not in lab and "interior" not in lab and "all R" not in lab else {"CORRECT", "UNKNOWN"}
        out.append((f"PNI2 der {f} at 0, {lab}: 1", der(f, "0", vars_=vs), sol("1"), exp, None))
        out.append((f"PNI2 tan {f} at 0, {lab}: y = x", tan(f, "0", vars_=vs), sol("y = x", "equation"), exp, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
