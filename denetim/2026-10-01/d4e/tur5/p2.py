"""p2: variants of the pzeros strict-condition hole (Max/Min, a region on the bad side, other writings)."""
import sys
from ortak import *


def cases():
    out = []
    U = "x - cos(x)"
    tb = f"(1 + sin(x))*({U})/Abs({U})"
    # region entirely where u < 0: the claim has a value NOWHERE there
    out.append(("x<0: |x-cos x|' tb + 0*log(u)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                sol(f"{tb} + 0*log({U})", "expression"), NOTOK, None))
    out.append(("x<0 ctrl: |x-cos x|' = -(1+sin x)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                sol("-(1 + sin(x))", "expression"), NOTNO, None))
    out.append(("given x<0: |x-cos x|' tb + 0*log(u)", der(f"Abs({U})", givens=["x < 0"]),
                sol(f"{tb} + 0*log({U})", "expression"), NOTOK, None))
    # Max / Min (abs_form makes |x - cos x|)
    mx = f"(1 - sin(x))/2 + (1 + sin(x))*({U})/(2*Abs({U}))"
    out.append(("ctrl Max(x,cos x)' tb", der("Max(x, cos(x))"), sol(mx, "expression"), NOTNO, None))
    out.append(("Max(x,cos x)' tb + 0*log(u)", der("Max(x, cos(x))"), sol(f"{mx} + 0*log({U})", "expression"), NOTOK, None))
    mn = f"(1 - sin(x))/2 - (1 + sin(x))*({U})/(2*Abs({U}))"
    out.append(("Min(x,cos x)' tb + 0*log(u)", der("Min(x, cos(x))"), sol(f"{mn} + 0*log({U})", "expression"), NOTOK, None))
    # other writings of u > 0
    out.append(("|x-cos x|' tb + 0/sqrt(u)", der(f"Abs({U})"), sol(f"{tb} + 0/sqrt({U})", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb*sqrt(u)/sqrt(u)", der(f"Abs({U})"), sol(f"{tb}*sqrt({U})/sqrt({U})", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb + 0*log(u/2)", der(f"Abs({U})"), sol(f"{tb} + 0*log(({U})/2)", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb + 0*log(x)*0 + 0*log(u) LaTeX-ish ln", der(f"Abs({U})"), sol(f"{tb} + 0*ln({U})", "expression"), NOTOK, None))
    # another base, the zero not solvable: x + exp(x) and x - sin(x) - 1, 1 + x + x**3/3 + exp(x)?
    W_ = "x - sin(x) - 1"
    out.append(("|x-sin x-1|' tb + 0*log(u)", der(f"Abs({W_})"),
                sol(f"(1 - cos(x))*({W_})/Abs({W_}) + 0*log({W_})", "expression"), NOTOK, None))
    out.append(("ctrl |x-sin x-1|' tb", der(f"Abs({W_})"), sol(f"(1 - cos(x))*({W_})/Abs({W_})", "expression"), NOTNO, None))
    # the whole region bad side via a parameter? (declared) - and LaTeX claim
    out.append(("|x-cos x|' LaTeX claim + 0*\\ln(u)", der(f"Abs({U})"),
                sol(r"\frac{(1+\sin x)(x-\cos x)}{|x-\cos x|} + 0\cdot\ln(x-\cos x)", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
