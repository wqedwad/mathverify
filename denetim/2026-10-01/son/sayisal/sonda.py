"""A+ final attack, lens 1 (numeric sign): G1YO-1 and G1YO-2 (16 Oct 2026; the main session's decisions).

G1YO-1: an integer power of a complex number that is real, (1 + i*sqrt(3))**3 = -8, is evaluated by SymPy as
-8.0 + 0.e-22*I, an imaginary part of rounding noise. `_sympy_guards.strict_sign` read it as "nonreal" (no check of
its significant bits), the patched assumption fallback then called the number neither positive nor negative while
SymPy knows it real, so (1 + i*sqrt(3))**3 - 5 was zero: 5 was CORRECT, every wrong answer of the De Moivre family
with it. SymPy's product of complex factors also reports the accuracy of the whole number for its small part
(-(1 + i*sqrt(3))**3 came out 8.0 - 2.8e-26*I with 64 bits), and a real argument evaluated with such a part was read
by an untracked path (sin) or on a branch cut by the sign of the noise (log, sqrt). Decision: a part decides only with
significant bits of its own, measured against the error of the whole number; noise is undecided, never "nonreal".

G1YO-2: `sandbox.exactsets._on` read the candidate indices of a progression in floating point; far from 0 the window's
points fell out of the candidates: the empty set was certified the solution of sin x = 0 on [10^18, 10^18 + 20].
Decision: such a window is left unsolved (fail-closed).

SON-G3-RK-3 (added the same evening): the principal argument is (-pi, pi] in SymPy and [0, 2*pi) in the curriculum;
5*pi/4 for arg(-1 - i) was refuted. Decision: a right representative of either range is UNKNOWN, a value in neither
INCORRECT; where the ranges agree the value is CORRECT; a problem that writes its range is read in it.

    B  the finding's evaluate cases (De Moivre family)      C  its siblings (Abs, re, steps, equations, inequalities)
    D  other writings of the power                           E  other tasks (limit, derivative, extremum, givens)
    K  textbook complex numbers (De Moivre, |z|, z*conj(z), powers of i, sums of (a+bi)^n, conjugate)
    R  a real argument written with complex numbers (sin, log, sqrt of it)
    P  a progression's window far from 0 (G1YO-2)
    G  the principal argument's two conventions (SON-G3-RK-3, added the same evening)
    X  the extremum's candidates (second round, SS-YO-1)    M  the arg readings, second round (RK-SAY-1/2/3, RK-ARG-STEP)

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/son/sayisal/sonda.py [out.json] [groups]

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
UNK = {"UNKNOWN"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false acceptance
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
VER = {"verified"}
REF = {"refuted"}

X = {"name": "x", "domain": "real"}
Z = {"name": "z", "domain": "complex"}
C3 = "(1 + sqrt(3)*I)**3"


def ev(expr, vars_=(), givens=(), dod=None, options=None):
    d = {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": "scalar"}
    if dod is not None:
        d["domain_of_discourse"] = dod
    if options:
        d["options"] = options
    return d


def task(kind, params, vars_=(X,), shape="scalar", givens=()):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def sol(payload, steps=(), kind="value", option=None):
    return {"claimed_answer": {"kind": kind, "payload": payload, "option": option},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def sset(p):
    return sol(p, kind="set")


def ival(p):
    return sol(p, kind="interval")


def eq(e, cons=None, givens=()):
    v = dict(X, constraints=list(cons)) if cons else X
    return task("solve_equation", {"equation": e, "var": "x"}, (v,), "set", givens)


def ineq(e, cons=None):
    v = dict(X, constraints=list(cons)) if cons else X
    return task("solve_inequality", {"inequality": e, "var": "x"}, (v,), "set")


def right_wrong(rows, label, ir, right, wrongs, right_want=OK, wrong_want=NO):
    rows.append((f"{label}: {right}", ir, sol(right), right_want, None))
    for w in wrongs:
        rows.append((f"{label}: {w} (wrong)", ir, sol(w), wrong_want, None))


# (label, ir, solution, expected verdicts, expected step statuses: None, a set for every step, or a list per step)
def cases_b():
    rows = []
    for label, expr, right, wrongs in [
        ("(1+i s3)^3", C3, "-8", ["5", "8", "-7", "0"]),
        ("(1/2 + i s3/2)^6", "(1/2 + sqrt(3)*I/2)**6", "1", ["7", "-1"]),
        ("(s3 + i)^6", "(sqrt(3) + I)**6", "-64", ["64", "0"]),
        ("(1 - i s3)^6", "(1 - sqrt(3)*I)**6", "64", ["-64", "32"]),
        ("(s2 + i s6)^3", "(sqrt(2) + sqrt(6)*I)**3", "-16*sqrt(2)", ["16*sqrt(2)", "-16"]),
        ("(-1 + i s3)^3", "(-1 + sqrt(3)*I)**3", "8", ["-8", "1"]),
        ("(1+i)^4", "(1 + I)**4", "-4", ["4", "3"]),
        ("(1 + i s3)^3 + 30", f"{C3} + 30", "22", ["0", "30"]),
        ("|(1+i s3)^3 + 30|", f"Abs({C3} + 30)", "22", ["0"]),
        ("(cos 20 + i sin 20)^9", "(cos(pi/9) + I*sin(pi/9))**9", "-1", ["1", "0"]),
        ("((1+i s3)/2)^3", "((1 + sqrt(3)*I)/2)**3", "-1", ["1", "0"]),
    ]:
        right_wrong(rows, label, ev(expr), right, wrongs)
    opts = {"A": "-8", "B": "8", "C": "-4", "D": "4", "E": "5"}
    rows += [
        ("(1+i s3)^3 LaTeX: -8 (not read)", ev("(1+i\\sqrt{3})^3"), sol("-8"), NOTNO, None),
        ("(1+i s3)^3 LaTeX: 5 (wrong)", ev("(1+i\\sqrt{3})^3"), sol("5"), NOTOK, None),
        ("z = 1 + i s3, z^3: -8", ev("z**3", [Z], ["z = 1 + sqrt(3)*I"]), sol("-8"), NOTNO, None),
        ("z = 1 + i s3, z^3: 5 (wrong)", ev("z**3", [Z], ["z = 1 + sqrt(3)*I"]), sol("5"), NOTOK, None),
        ("z = 1 + i s3, z^3 + |z|: 10 (wrong)", ev("z**3 + Abs(z)", [Z], ["z = 1 + sqrt(3)*I"]), sol("10"), NOTOK,
         None),
        ("MC (1+i s3)^3: A -8", ev(C3, options=opts), sol("-8", option="A"), OK, None),
        ("MC (1+i s3)^3: E 5 (wrong)", ev(C3, options=opts), sol("5", option="E"), NO, None),
        ("MC (1+i s3)^3: B 8 (wrong)", ev(C3, options=opts), sol("8", option="B"), NO, None),
        ("dod complex (1+i s3)^3: -8", ev(C3, dod="complex"), sol("-8"), OK, None),
        ("dod complex (1+i s3)^3: 5 (wrong)", ev(C3, dod="complex"), sol("5"), NO, None),
        ("step eq (1+i s3)^3 = 5 (wrong step), answer -8", ev(C3), sol("-8", [("eq", f"{C3} = 5")]), NO, REF),
        ("step eq (1+i s3)^3 = -8, answer -8", ev(C3), sol("-8", [("eq", f"{C3} = -8")]), OK, VER),
    ]
    return rows


def cases_c():
    rows = []
    for label, expr, right, wrongs in [
        ("Abs(C3)", f"Abs({C3})", "8", ["-8", "5"]),
        ("sqrt(-C3)", f"sqrt(-{C3})", "2*sqrt(2)", ["3"]),
        ("(2 cis 60)^3", "(2*(cos(pi/3) + I*sin(pi/3)))**3", "-8", ["8"]),
        ("(s2/2 + i s2/2)^8", "(sqrt(2)/2 + sqrt(2)*I/2)**8", "1", ["2"]),
        ("(s2/2 + i s2/2)^4", "(sqrt(2)/2 + sqrt(2)*I/2)**4", "-1", ["1"]),
        ("C3/8", f"{C3}/8", "-1", ["1"]),
        ("re(C3)", f"re({C3})", "-8", ["5"]),
        ("-C3", f"-{C3}", "8", ["-8", "5"]),
        ("2*C3", f"2*{C3}", "-16", ["16", "5"]),
        ("-C3 - 8", f"-{C3} - 8", "0", ["1"]),
    ]:
        right_wrong(rows, label, ev(expr), right, wrongs)
    rows += [
        ("step compute C3 = 5 (wrong), answer 5", ev(C3), sol("5", [("compute", f"{C3} = 5")]), NO, None),
        ("eq x = C3: {-8}", eq(f"x = {C3}"), sset("{-8}"), OK, None),
        ("eq x = C3: {5} (wrong)", eq(f"x = {C3}"), sset("{5}"), NO, None),
        ("eq x + C3 = 0: {8}", eq(f"x + {C3} = 0"), sset("{8}"), OK, None),
        ("eq x + C3 = 0: {3} (wrong)", eq(f"x + {C3} = 0"), sset("{3}"), NO, None),
        ("ineq x > C3: (-8, oo)", ineq(f"x > {C3}"), ival("Interval.open(-8, oo)"), OK, None),
        ("ineq x > C3: (5, oo) (wrong)", ineq(f"x > {C3}"), ival("Interval.open(5, oo)"), NO, None),
        ("ineq x**2 < -C3: (-2s2, 2s2)", ineq(f"x**2 < -{C3}"), ival("Interval.open(-2*sqrt(2), 2*sqrt(2))"), OK,
         None),
        ("ineq x**2 < -C3: (-3, 3) (wrong)", ineq(f"x**2 < -{C3}"), ival("Interval.open(-3, 3)"), NO, None),
        ("ineq x**2 < -C3: EmptySet (wrong)", ineq(f"x**2 < -{C3}"), sset("EmptySet"), NO, None),
    ]
    return rows


def cases_d():
    rows = []
    for label, expr, right, wrong in [
        ("text (1 + i*sqrt(3))^3", "(1 + i*sqrt(3))^3", "-8", "5"),
        ("text (1+sqrt(3)*i)**3", "(1+sqrt(3)*i)**3", "-8", "5"),
        ("(cos(pi/3)+i sin(pi/3))^3", "(cos(pi/3) + I*sin(pi/3))**3", "-1", "1"),
        ("(cos(2pi/5)+i sin(2pi/5))^5", "(cos(2*pi/5) + I*sin(2*pi/5))**5", "1", "2"),
        ("(cos(pi/4)+i sin(pi/4))^4", "(cos(pi/4) + I*sin(pi/4))**4", "-1", "3"),
        ("(2+2i)^4", "(2 + 2*I)**4", "-64", "64"),
        ("(sqrt(3)-i)^3", "(sqrt(3) - I)**3", "-8*I", "8"),
        ("((sqrt(3)+i)/2)^12", "((sqrt(3) + I)/2)**12", "1", "12"),
        ("(1+i s3)^3 + (1-i s3)^3", "(1 + sqrt(3)*I)**3 + (1 - sqrt(3)*I)**3", "-16", "16"),
        ("((1+i s3)^3)^2", "((1 + sqrt(3)*I)**3)**2", "64", "-64"),
        ("(1+i s3)^6 / (1-i)^4", "(1 + sqrt(3)*I)**6/(1 - I)**4", "-16", "16"),
    ]:
        right_wrong(rows, label, ev(expr), right, [wrong])
    return rows


def cases_e():
    def lim(f, to):
        return task("limit", {"expr": f, "var": "x", "to": to}, shape="dne_or_scalar")

    def der(f, at):
        return task("derivative", {"f": f, "var": "x", "at": at})

    def ext(f, which, interval):
        return task("extremum", {"f": f, "var": "x", "which": which, "interval": interval})

    A = {"name": "a", "domain": "real"}
    rows = []
    right_wrong(rows, "lim x->0 x + C3", lim(f"x + {C3}", "0"), "-8", ["5"])
    right_wrong(rows, "d/dx C3*x at 1", der(f"{C3}*x", "1"), "-8", ["5"])
    right_wrong(rows, "max x^2 + C3 on [0, 1]", ext(f"x**2 + {C3}", "max", "[0, 1]"), "-7", ["5"])
    right_wrong(rows, "a + 1 with a = C3", ev("a + 1", [A], [f"a = {C3}"]), "-7", ["5"])
    right_wrong(rows, "cbrt(C3 + 35)", ev(f"cbrt({C3} + 35)"), "3", ["0"])
    right_wrong(rows, "sqrt(C3 + 12)", ev(f"sqrt({C3} + 12)"), "2", ["0"])
    rows.append(("a with a = C3 and a = 5 (contradictory givens): 5", ev("a", [A], [f"a = {C3}", "a = 5"]), sol("5"),
                 NOTOK, None))
    return rows


def cases_k():
    """Textbook complex numbers (high school curriculum): the right answer stays CORRECT, no wrong one is."""
    rows = []
    for label, expr, right, wrongs in [
        # De Moivre
        ("(1+i s3)^6", "(1 + sqrt(3)*I)**6", "64", ["-64", "32"]),
        ("(s3+i)^3", "(sqrt(3) + I)**3", "8*I", ["-8*I", "8"]),
        ("(cos 15 + i sin 15)^12", "(cos(pi/12) + I*sin(pi/12))**12", "-1", ["1"]),
        ("(cos 40 + i sin 40)^9", "(cos(2*pi/9) + I*sin(2*pi/9))**9", "1", ["-1"]),
        ("((1+i)/s2)^4", "((1 + I)/sqrt(2))**4", "-1", ["1"]),
        ("omega^3", "((-1 + sqrt(3)*I)/2)**3", "1", ["-1", "3"]),
        ("omega^2 + omega + 1", "((-1 + sqrt(3)*I)/2)**2 + (-1 + sqrt(3)*I)/2 + 1", "0", ["1"]),
        ("(1-i)^10", "(1 - I)**10", "-32*I", ["32*I", "-32"]),
        ("(2 cis 30)^6", "(2*(cos(pi/6) + I*sin(pi/6)))**6", "-64", ["64"]),
        ("(cos 72 + i sin 72)^5", "(cos(2*pi/5) + I*sin(2*pi/5))**5", "1", ["-1"]),
        ("(1+i s3)^3 * (1-i s3)^3", "(1 + sqrt(3)*I)**3*(1 - sqrt(3)*I)**3", "64", ["-64"]),
        ("(1+i s3)^9", "(1 + sqrt(3)*I)**9", "-512", ["512"]),
        # |z|
        ("|3+4i|", "Abs(3 + 4*I)", "5", ["7", "25"]),
        ("|(1+i)^10|", "Abs((1 + I)**10)", "32", ["1024", "10"]),
        ("|(3+4i)/(1-i)|", "Abs((3 + 4*I)/(1 - I))", "5*sqrt(2)/2", ["5/2"]),
        ("|(1+i s3)^3|", f"Abs({C3})", "8", ["-8"]),
        ("|(1+2i)(2-i)|", "Abs((1 + 2*I)*(2 - I))", "5", ["3"]),
        ("|(s3+i)^6| + (s3+i)^6", "Abs((sqrt(3) + I)**6) + (sqrt(3) + I)**6", "0", ["128"]),
        # z * conj(z)
        ("(3+4i)(3-4i)", "(3 + 4*I)*(3 - 4*I)", "25", ["7", "-7"]),
        ("(2-5i) conj(2-5i)", "(2 - 5*I)*conjugate(2 - 5*I)", "29", ["-21"]),
        ("(1+i s3)^3 conj((1+i s3)^3)", f"{C3}*conjugate({C3})", "64", ["-64"]),
        # powers of i
        ("i^2023", "I**2023", "-I", ["I", "1"]),
        ("i + i^2 + i^3 + i^4", "I + I**2 + I**3 + I**4", "0", ["1"]),
        ("i^17 + i^34", "I**17 + I**34", "-1 + I", ["1 + I"]),
        ("1/i", "1/I", "-I", ["I"]),
        ("((1+i)/(1-i))^2023", "((1 + I)/(1 - I))**2023", "-I", ["I"]),
        # sums of (a+bi)^n
        ("(1+i)^4 + (1-i)^4", "(1 + I)**4 + (1 - I)**4", "-8", ["8", "0"]),
        ("(2+i)^2 + (2-i)^2", "(2 + I)**2 + (2 - I)**2", "6", ["8"]),
        ("(1+i)^6 + (1-i)^6", "(1 + I)**6 + (1 - I)**6", "0", ["-16"]),
        ("(s3+i)^6 + (s3-i)^6", "(sqrt(3) + I)**6 + (sqrt(3) - I)**6", "-128", ["128"]),
        ("(1+i s3)^4 + (1-i s3)^4", "(1 + sqrt(3)*I)**4 + (1 - sqrt(3)*I)**4", "-16", ["16"]),
        # conjugate, re, im
        ("conj((1+2i)^2)", "conjugate((1 + 2*I)**2)", "-3 - 4*I", ["-3 + 4*I"]),
        ("re((2+3i)/(1-i))", "re((2 + 3*I)/(1 - I))", "-1/2", ["1/2"]),
        ("im((1+i s3)^3)", f"im({C3})", "0", ["8"]),
        ("im((1+i s3)^4)", "im((1 + sqrt(3)*I)**4)", "-8*sqrt(3)", ["8*sqrt(3)"]),
        ("z + conj z, z = (1+i s3)^4", "(1 + sqrt(3)*I)**4 + conjugate((1 + sqrt(3)*I)**4)", "-16", ["16"]),
        ("arg((1+i s3)^3)", f"arg({C3})", "pi", ["0"]),
    ]:
        right_wrong(rows, label, ev(expr), right, wrongs)
    K = {"name": "k", "domain": "integer"}
    # a sum of complex terms has no confirmed value (forms: a numeric check reads real values only; before these fixes)
    right_wrong(rows, "sum i^k, k = 1..10", ev("Sum(I**k, (k, 1, 10))", [K]), "-1 + I", ["1 + I"], NOTNO, NOTOK)
    opts = {"A": "-64", "B": "64", "C": "32", "D": "-32", "E": "0"}
    rows += [
        ("MC (s3+i)^6: A -64", ev("(sqrt(3) + I)**6", options=opts), sol("-64", option="A"), OK, None),
        ("MC (s3+i)^6: B 64 (wrong)", ev("(sqrt(3) + I)**6", options=opts), sol("64", option="B"), NO, None),
        ("z = 1 + i, z^8 (z given): 16", ev("z**8", [Z], ["z = 1 + I"]), sol("16"), NOTNO, None),
        ("z = 1 + i, z^8 (z given): -16 (wrong)", ev("z**8", [Z], ["z = 1 + I"]), sol("-16"), NOTOK, None),
        ("z = 2 - 5i, z conj(z) (z given): 29", ev("z*conjugate(z)", [Z], ["z = 2 - 5*I"]), sol("29"), NOTNO, None),
        ("z = 2 - 5i, z conj(z) (z given): 21 (wrong)", ev("z*conjugate(z)", [Z], ["z = 2 - 5*I"]), sol("21"),
         NOTOK, None),
        ("step eq (s3+i)^6 = -64, answer -64", ev("(sqrt(3) + I)**6"), sol("-64", [("eq", "(sqrt(3) + I)**6 = -64")]),
         OK, VER),
        ("step eq (s3+i)^6 = 64 (wrong step), answer -64", ev("(sqrt(3) + I)**6"),
         sol("-64", [("eq", "(sqrt(3) + I)**6 = 64")]), NO, REF),
    ]
    return rows


def cases_r():
    """A real number written with complex numbers inside sin, log, sqrt (the argument's imaginary part is noise)."""
    rows = []
    for label, expr, right, wrongs, dod, rw in [
        ("sin(pi C3/8)", f"sin(pi*{C3}/8)", "0", ["1/2", "1"], None, OK),
        ("cos(pi C3/16)", f"cos(pi*{C3}/16)", "0", ["1"], None, OK),
        ("tan(pi C3/32)", f"tan(pi*{C3}/32)", "-1", ["1", "0"], None, NOTNO),
        ("sin(C3) + sin(8)", f"sin({C3}) + sin(8)", "0", ["1"], None, NOTNO),
        ("log(C3) (C)", f"log({C3})", "log(8) + I*pi", ["log(8) - I*pi", "log(8)"], "complex", OK),
        ("log(-C3)", f"log(-{C3})", "log(8)", ["log(8) + I*pi"], None, NOTNO),
        ("sqrt(C3) (C)", f"sqrt({C3})", "2*sqrt(2)*I", ["-2*sqrt(2)*I"], "complex", OK),
        ("sqrt(-C3 - 16) (C)", f"sqrt(-{C3} - 16)", "2*sqrt(2)*I", ["-2*sqrt(2)*I"], "complex", NOTNO),
        ("sqrt(-C3 - 16)", f"sqrt(-{C3} - 16)", "2*sqrt(2)*I", ["-2*sqrt(2)*I"], None, NOTNO),
        ("cbrt(-C3 - 16)", f"cbrt(-{C3} - 16)", "-2", ["2"], None, NOTNO),
        ("floor(-C3)", f"floor(-{C3})", "8", ["7"], None, NOTNO),
    ]:
        rows.append((f"{label}: {right}", ev(expr, dod=dod), sol(right), rw, None))
        for w in wrongs:
            rows.append((f"{label}: {w} (wrong)", ev(expr, dod=dod), sol(w), NOTOK, None))
    return rows


def cases_p():
    big = "10**18"
    true6 = "{%s}" % ", ".join(f"{k}*pi" for k in range(318309886183790672, 318309886183790678))
    cons = [f"x >= {big}", f"x <= {big} + 20"]

    def trig(eqn, interval):
        return task("trig_solve", {"var": "x", "interval": interval}, shape="set", givens=[eqn])

    return [
        ("sin x = 0 on [1e18, 1e18+20]: EmptySet (wrong)", eq("sin(x) = 0", cons), sset("EmptySet"), NOTOK, None),
        ("sin x = 0 on [1e18, 1e18+20]: the six points", eq("sin(x) = 0", cons), sset(true6), NOTNO, None),
        ("cos x = 1 on [1e18, 1e18+20]: EmptySet (wrong)", eq("cos(x) = 1", cons), sset("EmptySet"), NOTOK, None),
        ("|sin x| > 0 on [1e18, 1e18+20]: the window (wrong)", ineq("Abs(sin(x)) > 0", cons),
         ival(f"Interval({big}, {big} + 20)"), NOTOK, None),
        ("trig sin x = 0 on [1e18, 1e18+20]: EmptySet (wrong)", trig("sin(x) = 0", f"[{big}, {big} + 20]"),
         sset("EmptySet"), NOTOK, None),
        ("sin x = 0, window as givens: EmptySet (wrong)", eq("sin(x) = 0", None, cons), sset("EmptySet"), NOTOK, None),
        ("sin(x - 10^17) = 0 on [0, 10]: EmptySet (wrong)", eq("sin(x - 10**17) = 0", ["x >= 0", "x <= 10"]),
         sset("EmptySet"), NOTOK, None),
        # controls: a window near 0 keeps its points
        ("sin x = 0 on [1, 10]: {pi, 2pi, 3pi}", eq("sin(x) = 0", ["x >= 1", "x <= 10"]), sset("{pi, 2*pi, 3*pi}"),
         OK, None),
        ("sin x = 0 on [1, 10]: EmptySet (wrong)", eq("sin(x) = 0", ["x >= 1", "x <= 10"]), sset("EmptySet"), NO,
         None),
        ("trig sin x = 0 on [0, 2pi): {0, pi}", trig("sin(x) = 0", "[0, 2*pi)"), sset("{0, pi}"), OK, None),
        ("cos x = 1 on [10^6, 10^6 + 7]: {318310pi, 318312pi}", eq("cos(x) = 1", ["x >= 10**6", "x <= 10**6 + 7"]),
         sset("{318310*pi, 318312*pi}"), OK, None),
        ("cos x = 1 on [10^6, 10^6 + 7]: {318310pi} (wrong)", eq("cos(x) = 1", ["x >= 10**6", "x <= 10**6 + 7"]),
         sset("{318310*pi}"), NO, None),
    ]


def cases_g():
    """SON-G3-RK-3: the principal argument, (-pi, pi] (SymPy) or [0, 2*pi) (the curriculum). Where they differ (a
    negative imaginary part) a right representative of either is UNKNOWN, any other value INCORRECT; where they agree
    the value is CORRECT; a problem that writes its range is read in it."""
    C = "complex"
    rows = []
    for expr, unk, wrong in [
        ("arg(-1 - I)", ["5*pi/4", "-3*pi/4"], ["pi/4", "13*pi/4", "3*pi/4"]),
        ("arg(-I)", ["3*pi/2", "-pi/2"], ["pi/2"]),
        ("arg(1 - sqrt(3)*I)", ["5*pi/3", "-pi/3"], ["pi/3"]),
        ("arg((1 - sqrt(3)*I)**2)", ["4*pi/3", "-2*pi/3"], ["2*pi/3", "-4*pi/3"]),
        ("2*arg(-1 - I)", ["5*pi/2", "-3*pi/2"], ["pi/2"]),
        ("Abs(-1 - I)*arg(-1 - I)", ["5*sqrt(2)*pi/4", "-3*sqrt(2)*pi/4"], ["sqrt(2)*pi/4"]),
    ]:
        for c in unk:
            rows.append((f"{expr} = {c} (one convention)", ev(expr, dod=C), sol(c), UNK, None))
        for c in wrong:
            rows.append((f"{expr} = {c} (wrong in both)", ev(expr, dod=C), sol(c), NO, None))
    for expr, right, wrongs in [
        ("arg(1 + I)", "pi/4", ["9*pi/4", "-7*pi/4"]),
        ("arg(-1)", "pi", ["-pi"]),
        ("arg(3)", "0", ["2*pi"]),
        ("arg(I)", "pi/2", ["-3*pi/2"]),
        (f"arg({C3})", "pi", ["-pi"]),
        ("arg((1 + I)**2)", "pi/2", ["-3*pi/2"]),
    ]:
        right_wrong(rows, f"{expr} (conventions agree)", ev(expr, dod=C), right, wrongs)
    opts = {"A": "pi/4", "B": "5*pi/4", "C": "3*pi/4", "D": "7*pi/4"}
    dec_a = ["-pi < arg(-1 - I)", "arg(-1 - I) <= pi"]
    dec_b = ["0 <= arg(-1 - I)", "arg(-1 - I) < 2*pi"]
    rows += [
        ("arg(-1 - I) = 5pi/4, no domain of discourse", ev("arg(-1 - I)"), sol("5*pi/4"), UNK, None),
        ("arg(-1 - I) = 5pi/4 with its step", ev("arg(-1 - I)", dod=C), sol("5*pi/4", [("eq", "arg(-1 - I) = 5*pi/4")]),
         UNK, None),
        # only the [0, 2*pi) value 5*pi/4 is among the options: they write the range (second round, RK-SAY-3)
        ("MC arg(-1 - I): B 5pi/4", ev("arg(-1 - I)", dod=C, options=opts), sol("5*pi/4", option="B"), OK, None),
        ("MC arg(-1 - I): A pi/4 (wrong)", ev("arg(-1 - I)", dod=C, options=opts), sol("pi/4", option="A"), NO, None),
        ("(-pi, pi] written: -3pi/4", ev("arg(-1 - I)", givens=dec_a, dod=C), sol("-3*pi/4"), OK, None),
        ("(-pi, pi] written: 5pi/4 (wrong)", ev("arg(-1 - I)", givens=dec_a, dod=C), sol("5*pi/4"), NO, None),
        ("[0, 2pi) written: 5pi/4", ev("arg(-1 - I)", givens=dec_b, dod=C), sol("5*pi/4"), OK, None),
        ("[0, 2pi) written: -3pi/4 (wrong)", ev("arg(-1 - I)", givens=dec_b, dod=C), sol("-3*pi/4"), NO, None),
        ("[0, 2pi) written as a chain: 5pi/4", ev("arg(-1 - I)", givens=["0 <= arg(-1 - I) < 2*pi"], dod=C),
         sol("5*pi/4"), OK, None),
        # atan2, a programming function, keeps (-pi, pi]
        ("atan2(-1, -1) = -3pi/4", ev("atan2(-1, -1)"), sol("-3*pi/4"), OK, None),
        ("atan2(-1, -1) = 5pi/4", ev("atan2(-1, -1)"), sol("5*pi/4"), NOTOK, None),
    ]
    return rows


def cases_x():
    """SS-YO-1 (second round): the extremum's candidates are the set it calls complete. An endpoint value is no maximum
    where an interior critical point beats it; the true interior extremum is not refuted."""
    def ext(f, iv, which):
        return task("extremum", {"f": f, "var": "x", "which": which, "interval": iv})

    K = "(2 + I)*(2 - I)/5"
    rows = []
    for f, iv, right, wrong in [
        ("Abs(sin(x)) + x/2", "[0, 2*pi]", "sqrt(3)/2 + 5*pi/6", "pi"),
        ("Abs(sin(x)) + cos(x)", "[0, 2*pi]", "sqrt(2)", "1"),
        ("Abs(sin(x)) - x/2", "[0, 2*pi]", "sqrt(3)/2 - pi/6", "0"),
        ("sin(x) + Abs(cos(x))", "[0, 2*pi]", "sqrt(2)", "1"),
        ("Abs(sin(x)) + Abs(cos(x))", "[0, pi]", "sqrt(2)", "1"),
        ("x + Abs(sin(2*x))", "[0, pi]", "5*pi/6 + sqrt(3)/2", "pi"),
        (f"{K}*x + 2*cos(x)", "[0, pi]", "pi/6 + sqrt(3)", "2"),
        ("x + 2*cos(x)", "[0, pi]", "pi/6 + sqrt(3)", "2"),
        (f"-x**2 - {C3}*x", "[-10, 10]", "16", "20"),
        ("Abs(cos(x)) + x/2", "[0, 2*pi]", "1 + pi", "pi/2"),
        ("Max(sin(x), cos(x)) + x/4", "[0, 2*pi]", "1 + pi/2", "pi/2"),
    ]:
        # the maximum 1 + pi/2 of Max(sin x, cos x) + x/4 is UNKNOWN in 0e93ed5 and 4153cc1 too (its candidate set is
        # not called complete): not this finding's
        want = NOTNO if f.startswith("Max(") else OK
        rows.append((f"max {f} on {iv}: {right}", ext(f, iv, "max"), sol(right), want, None))
        rows.append((f"max {f} on {iv}: {wrong} (wrong)", ext(f, iv, "max"), sol(wrong), NO, None))
    rows += [
        ("argmax |sin x| + x/2 on [0, 2pi]: 5pi/3", ext("Abs(sin(x)) + x/2", "[0, 2*pi]", "argmax"), sol("5*pi/3"), OK, None),
        ("argmax |sin x| + x/2 on [0, 2pi]: 2pi (wrong)", ext("Abs(sin(x)) + x/2", "[0, 2*pi]", "argmax"), sol("2*pi"), NO,
         None),
        ("argmax Kx + 2cos x on [0, pi]: 0 (wrong)", ext(f"{K}*x + 2*cos(x)", "[0, pi]", "argmax"), sol("0"), NO, None),
        ("min Kx + 2cos x on [0, pi]: 5pi/6 - sqrt3", ext(f"{K}*x + 2*cos(x)", "[0, pi]", "min"), sol("5*pi/6 - sqrt(3)"),
         OK, None),
        ("min Kx + 2cos x on [0, pi]: pi - 2 (wrong)", ext(f"{K}*x + 2*cos(x)", "[0, pi]", "min"), sol("pi - 2"), NO, None),
        ("argmin e^x + C3 x/4 on [0, 2]: log 2", ext(f"exp(x) + {C3}*x/4", "[0, 2]", "argmin"), sol("log(2)"), OK, None),
        ("argmin e^x + C3 x/4 on [0, 2]: 0 (wrong)", ext(f"exp(x) + {C3}*x/4", "[0, 2]", "argmin"), sol("0"), NO, None),
        ("min x^2 + C3 x on [-10, 10]: -16", ext(f"x**2 + {C3}*x", "[-10, 10]", "min"), sol("-16"), OK, None),
        # where the complete set is not found (x = sin x): no certificate either way, as before
        ("max x^2/2 + cos x on [-1, 2]: 2 + cos 2", ext("x**2/2 + cos(x)", "[-1, 2]", "max"), sol("2 + cos(2)"), NOTNO,
         None),
        ("max sin x cos x on [0, pi]: 0 (wrong)", ext("sin(x)*cos(x)", "[0, pi]", "max"), sol("0"), NO, None),
    ]
    return rows


def cases_m():
    """The arg readings, second round: pointwise tasks (RK-SAY-1), steps (RK-ARG-STEP), INCORRECT in both readings
    only on a failure of both (RK-SAY-2), options of one range (RK-SAY-3)."""
    C = "complex"

    def pw(kind, f, pt):
        key, pk = ("f", "at") if kind == "derivative" else ("expr", "to")
        return task(kind, {key: f, "var": "x", pk: pt}, shape="scalar" if kind == "derivative" else "dne_or_scalar")

    o02 = {"A": "pi/4", "B": "3*pi/4", "C": "5*pi/4", "D": "7*pi/4", "E": "3*pi/2"}
    opp = {"A": "-3*pi/4", "B": "-pi/4", "C": "pi/4", "D": "3*pi/4", "E": "pi"}
    deg = {"A": "45°", "B": "135°", "C": "225°", "D": "315°", "E": "270°"}
    both = {"A": "-3*pi/4", "B": "5*pi/4", "C": "pi/4", "D": "3*pi/4", "E": "pi"}
    return [
        ("d/dx arg(1 + xi) at 1: 1/2", pw("derivative", "arg(1 + x*I)", "1"), sol("1/2"), OK, None),
        ("d/dx arg(1 + xi) at -1: 1/2", pw("derivative", "arg(1 + x*I)", "-1"), sol("1/2"), OK, None),
        ("d/dx arg(2 + xi) at 2: 1/4", pw("derivative", "arg(2 + x*I)", "2"), sol("1/4"), OK, None),
        ("d/dx arg(1 + xi) at 1: 1 (wrong)", pw("derivative", "arg(1 + x*I)", "1"), sol("1"), NO, None),
        ("lim arg(1 + xi), x -> 1: pi/4", pw("limit", "arg(1 + x*I)", "1"), sol("pi/4"), OK, None),
        ("lim arg(1 + xi), x -> 1: pi/2 (wrong)", pw("limit", "arg(1 + x*I)", "1"), sol("pi/2"), NO, None),
        ("lim arg(1 + xi), x -> -1: 7pi/4 (one convention)", pw("limit", "arg(1 + x*I)", "-1"), sol("7*pi/4"), UNK, None),
        ("(-1-i)^4 = 4 with the [0, 2pi) arg step", ev("(-1 - I)**4", dod=C),
         sol("4", [("eq", "arg(-1 - I) = 5*pi/4"), ("eq", "(-1 - I)**4 = 4")]), NO, ["unknown", "refuted"]),
        ("arg(-1-i) = 5pi/4 from the principal value", ev("arg(-1 - I)", dod=C),
         sol("5*pi/4", [("eq", "arg(-1 - I) = -3*pi/4"), ("eq", "-3*pi/4 + 2*pi = 5*pi/4")]), UNK, None),
        ("arg(-1-i) = -3pi/4 from the [0, 2pi) value", ev("arg(-1 - I)", dod=C),
         sol("-3*pi/4", [("eq", "arg(-1 - I) = 5*pi/4"), ("eq", "5*pi/4 - 2*pi = -3*pi/4")]), UNK, None),
        ("arg(1-i) = 7pi/4 from the principal value", ev("arg(1 - I)", dod=C),
         sol("7*pi/4", [("eq", "arg(1 - I) = -pi/4")]), UNK, None),
        ("arg(-1-i) = pi/4 with a principal step (wrong)", ev("arg(-1 - I)", dod=C),
         sol("pi/4", [("eq", "arg(-1 - I) = -3*pi/4")]), NO, ["unknown"]),
        ("MC [0, 2pi) options: C 5pi/4", ev("arg(-1 - I)", dod=C, options=o02), sol("5*pi/4", option="C"), OK, None),
        ("MC [0, 2pi) options: A pi/4 (wrong)", ev("arg(-1 - I)", dod=C, options=o02), sol("pi/4", option="A"), NO, None),
        ("MC (-pi, pi] options: A -3pi/4", ev("arg(-1 - I)", dod=C, options=opp), sol("-3*pi/4", option="A"), OK, None),
        ("MC (-pi, pi] options: C pi/4 (wrong)", ev("arg(-1 - I)", dod=C, options=opp), sol("pi/4", option="C"), NO, None),
        ("MC both values: B 5pi/4", ev("arg(-1 - I)", dod=C, options=both), sol("5*pi/4", option="B"), UNK, None),
        ("MC 'Hiçbiri': C 5pi/4", ev("arg(-1 - I)", dod=C, options=dict(o02, E="Hiçbiri")), sol("5*pi/4", option="C"),
         UNK, None),
        ("MC degrees: C 225°", ev("arg(-1 - I)", dod=C, options=deg), sol("225°", option="C"), NOTOK, None),
        ("MC arg(1 - sqrt3 i), [0, 2pi): D 5pi/3", ev("arg(1 - sqrt(3)*I)", dod=C,
                                                     options={"A": "pi/3", "B": "2*pi/3", "C": "4*pi/3", "D": "5*pi/3",
                                                              "E": "pi/6"}), sol("5*pi/3", option="D"), OK, None),
    ]


GROUPS = {"B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "K": cases_k, "R": cases_r, "P": cases_p,
          "G": cases_g, "X": cases_x, "M": cases_m}


def _statuses_ok(want, got):
    if want is None:
        return True
    if isinstance(want, list):
        return len(want) == len(got) and all(g in w for w, g in zip(want, got))
    return all(g in want for g in got)


def main(out_path=None, groups="BCDEKRPGXM"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for label, ir, sol_, verdicts, statuses in GROUPS[g]():
            t = time.time()
            try:
                r = verify(ir, sol_)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                got = [s.get("status") for s in steps]
                flags = sorted(r.flags)
                why = [(la.layer, la.verdict, str((la.evidence or {}).get("reason", ""))[:60])
                       for la in r.layers if la.verdict != "unknown" or la.layer.startswith(("certify", "intake"))]
            except Exception as e:  # noqa: BLE001
                verdict, got, flags, why = f"EXC {type(e).__name__}: {e}", [], [], []
            ok = (verdicts is None or verdict in verdicts) and _statuses_ok(statuses, got) \
                and "layer_exception" not in flags
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "steps": got, "ok": ok, "flags": flags,
                         "layers": json.loads(json.dumps(why, default=str)), "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {got} {label}  {flags[:4]}", flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "BCDEKRPGXM"
    sys.exit(1 if main(out, grp) else 0)
