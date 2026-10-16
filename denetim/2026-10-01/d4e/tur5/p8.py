"""p8: solved_pins (RK-3) with a given undefined as written at the value it fixes; region facts from such givens."""
import sys
from ortak import *

AR = {"name": "a", "domain": "real"}
NP_ = {"name": "n", "domain": "positive_integer"}


def cases():
    out = []
    g1 = "2*a + 0*sqrt(a - 5) = 4"       # folded: a = 2; as written a >= 5: no a satisfies it
    g2 = "a + 0*sqrt(a - 5) = 2"
    g3 = "2*a + 0*log(a - 5) = 4"
    for g in (g1, g2, g3):
        out.append((f"[{g}] (a x^2)' = 4x", der("a*x**2", givens=[g], vars_=[X, AR]), sol("4*x", "expression"), NOTOK, None))
        out.append((f"[{g}] (a x^2)' at 1 = 4", der("a*x**2", "1", givens=[g], vars_=[X, AR]), sol("4"), NOTOK, None))
        out.append((f"[{g}] tangent a x^2 at 1: y = 4x - 2", tan("a*x**2", "1", givens=[g], vars_=[X, AR]),
                    sol("y = 4*x - 2", "equation"), NOTOK, None))
        out.append((f"[{g}] lim a*x/x at 0 = 2", lim("a*x/x", "0", givens=[g], vars_=[X, AR]), sol("2"), NOTOK, None))
        out.append((f"[{g}] max a*x on [0,1] = 2", ext("a*x", "max", "[0, 1]", givens=[g], vars_=[X, AR]), sol("2"), NOTOK, None))
        out.append((f"[{g}] antideriv a*x = x^2", anti("a*x", givens=[g], vars_=[X, AR]), sol("x**2", "expression"), NOTOK, None))
        out.append((f"[{g}] def int a*x on [0,1] = 1",
                    ir("definite_integral", {"integrand": "a*x", "var": "x", "lo": "0", "hi": "1"}, givens=[g], vars_=[X, AR],
                       shape="scalar"), sol("1"), NOTOK, None))
        out.append((f"[{g}] series sum_k=1^3 a*k = 12", ss("a*k", "1", "3", givens=[g], vars_=[K_, AR]), sol("12"), NOTOK, None))
        out.append((f"[{g}] evaluate a + 1 = 3", ir("evaluate", {"expr": "a + 1"}, givens=[g], vars_=[AR], shape="scalar"),
                    sol("3"), NOTOK, None))
        out.append((f"[{g}] solve x - a = 0: {{2}}", ir("solve_equation", {"var": "x", "equation": "x - a = 0"}, givens=[g],
                                                         vars_=[X, AR]), sol("{2}", "set"), NOTOK, None))
    # constraint on a, written undefined at its value
    ac = {"name": "a", "domain": "real", "constraints": ["2*a + 0*sqrt(a - 5) = 4"]}
    out.append(("[constraint 2a+0*sqrt(a-5)=4] (a x^2)' = 4x", der("a*x**2", vars_=[X, ac]), sol("4*x", "expression"), NOTOK, None))
    out.append(("[constraint] series a*k = 12", ss("a*k", "1", "3", vars_=[K_, ac]), sol("12"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
