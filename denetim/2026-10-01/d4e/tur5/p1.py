"""p1: RK-6 pzeros, strict claim condition u > 0 skipped for a SWITCH |u| (f defined on both sides of u's zeros)."""
import sys
from ortak import *


def cases():
    out = []
    U = "x - cos(x)"
    tb = f"(1 + sin(x))*({U})/Abs({U})"
    # controls
    out.append(("ctrl |x-cos x|' textbook", der(f"Abs({U})"), sol(tb, "expression"), NOTNO, None))
    # claim undefined on the half-line x - cos x < 0, where f = |u| has a derivative -(1 + sin x)
    out.append(("|x-cos x|' tb + 0*log(u)", der(f"Abs({U})"), sol(f"{tb} + 0*log({U})", "expression"), NOTOK, None))
    out.append(("|x-cos x|' (1+sin)*sign(u) + 0*log(u)", der(f"Abs({U})"),
                sol(f"(1 + sin(x))*sign({U}) + 0*log({U})", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb*log(u)/log(u)", der(f"Abs({U})"), sol(f"{tb}*log({U})/log({U})", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb + 0*log(2*u)", der(f"Abs({U})"), sol(f"{tb} + 0*log(2*({U}))", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb + 0*log(u**3)", der(f"Abs({U})"), sol(f"{tb} + 0*log(({U})**3)", "expression"), NOTOK, None))
    out.append(("|x-cos x|' tb + 0*acosh(u+1)", der(f"Abs({U})"), sol(f"{tb} + 0*acosh({U} + 1)", "expression"), NOTOK, None))
    # other bases
    V = "x + exp(x)"
    out.append(("|x+e^x|' tb + 0*log(u)", der(f"Abs({V})"),
                sol(f"(1 + exp(x))*({V})/Abs({V}) + 0*log({V})", "expression"), NOTOK, None))
    out.append(("ctrl |x+e^x|' tb", der(f"Abs({V})"), sol(f"(1 + exp(x))*({V})/Abs({V})", "expression"), NOTNO, None))
    # at a point on the bad side (x = 0: u = -1 < 0, f'(0) = -1)
    out.append(("|x-cos x|' at 0 = -1 ctrl", der(f"Abs({U})", "0"), sol("-1"), NOTNO, None))
    # power: sqrt(u) has f's own u >= 0, the claim's u > 0 fails at zeros only -> CORRECT allowed (control)
    out.append(("ctrl sqrt(x-cos x)' tb", der(f"sqrt({U})"), sol(f"(1 + sin(x))/(2*sqrt({U}))", "expression"), NOTNO, None))
    out.append(("ctrl sqrt(x-cos x)' tb + 0*log(u)", der(f"sqrt({U})"),
                sol(f"(1 + sin(x))/(2*sqrt({U})) + 0*log({U})", "expression"), NOTNO, None))
    # sum f = |u| + |u|?  f = 2|u|
    out.append(("2|x-cos x|' 2tb + 0*log(u)", der(f"2*Abs({U})"), sol(f"2*{tb} + 0*log({U})", "expression"), NOTOK, None))
    out.append(("x**2+|x-cos x|' + 0*log(u)", der(f"x**2 + Abs({U})"), sol(f"2*x + {tb} + 0*log({U})", "expression"), NOTOK, None))
    return out


if __name__ == "__main__":
    run(cases(), sys.argv[1] if len(sys.argv) > 1 else None)
