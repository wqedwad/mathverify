import sys
from ortak import *


def simp_(e, givens=(), vars_=None, dod=None):
    return ir("simplify_expression", {"expr": e}, givens, vars_, shape="expression", dod=dod)


def cases():
    out = []
    out.append(("FAMS anti 2*x, given x > 10: x**2 + 0*cot(4*x)", anti("2*x", ["x > 10"]), sol("x**2 + 0*cot(4*x)", "expression"),
                NOTOK, None))
    out.append(("FAMS anti 1/(x - 20): log(x - 20) + 0*cot(x)", anti("1/(x - 20)", ["x > 20"]),
                sol("log(x - 20) + 0*cot(x)", "expression"), NOTOK, None))
    out.append(("FAMS simplify x**2/x, given x > 10: x + 0*cot(4*x)", simp_("x**2/x", ["x > 10"]),
                sol("x + 0*cot(4*x)", "expression"), NOTOK, None))
    out.append(("FAMS simplify log(x - 20) + 1: log(x - 20) + 1 + 0*tan(x)", simp_("log(x - 20) + 1"),
                sol("log(x - 20) + 1 + 0*tan(x)", "expression"), NOTOK, None))
    out.append(("FAMS ctrl simplify x**2/x: x + 0*cot(x)", simp_("x**2/x"), sol("x + 0*cot(x)", "expression"), NOTOK, None))
    # derivative tasks: more natural-looking writings of the claim
    out.append(("FAM derivative log(x - 20): cot(x)*tan(x)/(x - 20)", der("log(x - 20)"),
                sol("cot(x)*tan(x)/(x - 20)", "expression"), NOTOK, None))
    out.append(("FAM derivative x*sin(x), given x > 10: sin(x) + x*cos(x)*tan(4*x)*cot(4*x)", der("x*sin(x)", None, ["x > 10"]),
                sol("sin(x) + x*cos(x)*tan(4*x)*cot(4*x)", "expression"), NOTOK, None))
    out.append(("FAM derivative tan(x), given x > 10: 1 + tan(x)**2 [ctrl right]", der("tan(x)", None, ["x > 10"]),
                sol("1 + tan(x)**2", "expression"), NOTNO, None))
    out.append(("FAM derivative sin(x)**2, given x > 10: 2*sin(x)**2*cot(x)", der("sin(x)**2", None, ["x > 10"]),
                sol("2*sin(x)**2*cot(x)", "expression"), NOTOK, None))
    out.append(("FAM derivative sin(x)**2, x > 10 constraint: 2*sin(x)**2/tan(x)", der("sin(x)**2", None, [], [xc("x > 10")]),
                sol("2*sin(x)**2/tan(x)", "expression"), NOTOK, None))
    out.append(("FAM ctrl derivative sin(x)**2: 2*sin(x)**2*cot(x)", der("sin(x)**2"),
                sol("2*sin(x)**2*cot(x)", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    sys.exit(1 if run(cases(), sys.argv[1] if len(sys.argv) > 1 else None) else 0)
