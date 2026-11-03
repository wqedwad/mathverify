import sys
from ortak import *

TT = {"name": "t", "domain": "real"}
XT = [X, TT]
DIV = ["0*Integral(1/(1 + t**2*sin(t)**2), (t, 0, oo))",   # diverges (undecided)
       "0*Integral(1/t, (t, 1, oo))",                       # diverges
       "0*Integral(1/(t - 1/2), (t, 0, 1))",                # diverges
       "0*Integral(1/(t - x), (t, 0, oo))",                 # undefined for every x
       "0*Integral(exp(-t)/(t - x), (t, 0, oo))",           # undefined for x >= 0
       "0*Limit(sin(1/t), t, 0)",                           # does not exist
       "0*Sum(1/k, (k, 1, oo))",                            # diverges
       ]


def cases():
    out = []
    for D in DIV:
        out.append((f"CU der expr x**2: 2x + {D}", der("x**2", None, vars_=XT), sol(f"2*x + {D}", "expression"), NOTOK, None))
        out.append((f"CU der at 1 x**2: 2 + {D}", der("x**2", "1", vars_=XT), sol(f"2 + {D}"), NOTOK, None))
        out.append((f"CU anti 2x: x**2 + {D}", anti("2*x", vars_=XT), sol(f"x**2 + {D}", "expression"), NOTOK, None))
        out.append((f"CU simplify 2x/2: x + {D}", ir("simplify", {"expr": "2*x/2"}, vars_=XT, shape="expression"), sol(f"x + {D}", "expression"), NOTOK, None))
        out.append((f"CU der expr log(a x), a>0: 1/x + {D}", der("log(a*x)", None, vars_=XT + [{"name": "a", "domain": "positive_real"}]), sol(f"1/x + {D}", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
