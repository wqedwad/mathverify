"""p9: pzeros strict-condition hole: odd roots (defined on both sides), other orientations, x*e^x - 1."""
import sys
from ortak import *


def cases():
    out = []
    U = "x - cos(x)"
    out.append(("ctrl cbrt(u)' tb", der(f"cbrt({U})"), sol(f"(1 + sin(x))/(3*cbrt(({U})**2))", "expression"), NOTNO, None))
    out.append(("cbrt(u)' tb + 0*log(u)", der(f"cbrt({U})"), sol(f"(1 + sin(x))/(3*cbrt(({U})**2)) + 0*log({U})", "expression"),
                NOTOK, None))
    out.append(("root(u,5)' tb + 0*log(u)", der(f"root({U}, 5)"),
                sol(f"(1 + sin(x))/(5*root(({U})**4, 5)) + 0*log({U})", "expression"), NOTOK, None))
    V = "cos(x) - x"
    out.append(("|cos x - x|' tb + 0*log(cos x - x)", der(f"Abs({V})"),
                sol(f"-(1 + sin(x))*({V})/Abs({V}) + 0*log({V})", "expression"), NOTOK, None))
    W_ = "x*exp(x) - 1"
    out.append(("|x e^x - 1|' tb + 0*log(u)", der(f"Abs({W_})"),
                sol(f"(x + 1)*exp(x)*({W_})/Abs({W_}) + 0*log({W_})", "expression"), NOTOK, None))
    out.append(("ctrl |x e^x - 1|' tb", der(f"Abs({W_})"), sol(f"(x + 1)*exp(x)*({W_})/Abs({W_})", "expression"), NOTNO, None))
    # constraint keeps the region on u<0 entirely and the claim names u > 0 through a power: 0*(u)**(-1/2)?
    out.append(("x<0: |x-cos x|' tb + 0*(x-cos x)**(-3/2)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                sol(f"(1 + sin(x))*({U})/Abs({U}) + 0*({U})**(-3/2)", "expression"), NOTOK, None))
    out.append(("x<0: |x-cos x|' -(1+sin x) + 0*log(u)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                sol(f"-(1 + sin(x)) + 0*log({U})", "expression"), NOTOK, None))
    out.append(("x<0: |x-cos x|' -(1+sin x) + 0*log(u) as givens", der(f"Abs({U})", givens=["x < 0"]),
                sol(f"-(1 + sin(x)) + 0*log({U})", "expression"), NOTOK, None))
    out.append(("x<0: |x-cos x|' -(1+sin x)*log(u)/log(u)", der(f"Abs({U})", vars_=[xc("x < 0")]),
                sol(f"-(1 + sin(x))*log({U})/log({U})", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
