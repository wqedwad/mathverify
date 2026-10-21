"""The final attack after the fourth audit (A+, merged 7892190; DECISIONS §89-§91), lens 4 "parser, steps, fusion"
(16 Oct 2026, evening addendum): the findings G4YO-1, G4YO-2, G4YO-3, G4-RK-5 and G4-K-4 and their sibling paths, on
the branch wip/son-ayristirici.

  A  G4YO-1  '{∅}' (the set holding the empty set) is no "no solution": the shortcut reads only a text that IS the
             empty set or says "no solution" as a whole (∅, {}, Ø, \\emptyset, \\varnothing, 'Çözüm yok', 'Gerçel kök
             yoktur', 'Ç = ∅', 'x ∈ ∅'); a text that only names it ('{∅}', '{0, ∅}', '∅ ∪ {1}', 'Çözüm yok değil') is
             read as written: never CORRECT beside ∅, the letter alone refuted where it is read
  B  G4-RK-5 premises with no instance refute no step: '1 = 3', '0 = 2' from 2x + 1 = 2x + 3, x**2 = -1 (eq and
             compute) from x**2 + 1 = 0, the inequality form, an inconsistent linear system (sibling); a wrong step
             where the premises do have instances is still refuted
  C  G4YO-2  a factor right after a divisor ('1/2π', '1/2√x', 'x/2π', '$1/2\\pi$', '3/4\\sqrt{2}') is read neither
             way: claim, option and step; the dual \\ln 2/2 (a function's argument without brackets before a '/',
             sibling) too; explicit operators, brackets and \\frac are read as before
  D  G4YO-3  Turkish negation and doubt with their suffixes after the value ('5 değildir', '5 yanlıştır', '5
             olmayabilir', '5 sanmıyorum', '5 midir', '5 hariçtir', '5 çıkmaz'): the payload is not read; plain prose
             after a value ('5 bulunur', '5 olmalıdır', '5 cm') is cleaned as before
  E  G4-K-4  a given that holds at one real point only (a sum of squares, √ + |·| = 0, squares completed): a wrong
             step is refuted there, a right one is not
  K  controls whose verdict must not change
  Second round (21 Oct 2026; the two-lens audit of the branch, son_denetim/son-ayristirici/bulgular.json, EK 3):
  F  SA-YO-1 premises with no real instance withdraw an open step's refutation only when the step is proved to follow
             from them (a multiple of a premise, true at every complex solution); refuted at an exact complex solution,
             it stays refuted (a wrong completed square); undecided, a compute step leaves the solution UNKNOWN
  G  SA-RK-1, SA-RK-2  'gerçek', 'gerçek sayılarda', the domain and solution-set prefixes (Tanım kümesi, T.K., TK, D(f),
             ÇK, Ç.K.), '(∅)', ''dir', 'There is no solution': the empty set; a 'yok' no reading takes is never a
             refutation of ∅
  H  SA-YO-2, SA-RK-3, SA-RK-5, SA-RK-6  the trailing prose: an allow list (a rejection is negated, an unknown word
             unread, a symbol or a single letter never dropped, a final ',' punctuation)
  J  SA-YO-3, SA-RK-4, SA-YO-4  a LaTeX function's argument to the first operator (its base skipped; a '/' in it is
             ambiguous; the argument bracketed for latex2sympy, sibling), '\\%' and '^\\circ', the Unicode minus

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/son/ayristirici/sonda.py [out.json] [groups]

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
NOTREF = {"verified", "unknown", "skipped", None}
NEITHER = {"unknown", "skipped", None}

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
Y = {"name": "y", "domain": "real"}
Z = {"name": "z", "domain": "real"}


def ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update({k: v for k, v in extra.items() if v is not None})
    return d


def sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                                            for i, (k, c) in enumerate(steps)]}


def eqn(e, **kw):
    return ir("solve_equation", {"var": "x", "equation": e}, shape="set", **kw)


# A: G4YO-1 --------------------------------------------------------------------------------------------------------
SET_OF_EMPTY = ["{∅}", "{ ∅ }", "{Ø}", "$\\{\\emptyset\\}$", "\\{\\emptyset\\}", "{\\emptyset}", "$\\{\\varnothing\\}$",
                "{0, ∅}", "{∅, 1}", "Çözüm yok değil", "∅ değildir"]
NO_SOLUTION = ["∅", "{}", "{ }", "Ø", "$\\emptyset$", "\\emptyset", "$\\varnothing$", "$\\{\\}$", "Çözüm yok",
               "Çözüm yoktur", "Çözüm kümesi boştur", "Boş küme", "Kök yoktur", "Gerçel kök yoktur", "Reel kök yoktur",
               "Gerçel çözümü yoktur", "Hiçbir çözüm yok", "No real solution", "Ç = ∅", "Ç = {}", "Ç.K. = ∅", "x ∈ ∅",
               "∅ (boş küme)", "Çözüm kümesi ∅", "Denklemin reel kökü yoktur."]


def _opts(d):
    return {"A": "{0}", "B": "{-1}", "C": "{1}", "D": d, "E": "{-1, 1}"}


def cases_a():
    out = []
    for d in SET_OF_EMPTY:
        q = eqn("x**2 + 1 = 0", options=_opts(d))
        out += [(f"x²+1=0: ∅ letter D={d!r}", q, sol("∅", "set", option="D"), NOTOK, None),
                (f"x²+1=0: letter D={d!r} alone", q, sol(None, "set", option="D"), NOTOK, None)]
    for d in ("{∅}", "{ ∅ }", "\\{\\emptyset\\}", "{\\emptyset}", "$\\{\\emptyset\\}$", "{0, ∅}"):
        out.append((f"x²+1=0: letter D={d!r} alone, read as written", eqn("x**2 + 1 = 0", options=_opts(d)),
                    sol(None, "set", option="D"), NO, None))
    for d in NO_SOLUTION:
        q = eqn("x**2 + 1 = 0", options=_opts(d))
        out += [(f"x²+1=0: ∅ letter D={d!r}", q, sol("∅", "set", option="D"), OK, None),
                (f"x²+1=0: letter D={d!r} alone", q, sol(None, "set", option="D"), OK, None),
                (f"x-1=0: {{1}} letter D={d!r} (wrong)", eqn("x - 1 = 0", options=_opts(d)), sol("{1}", "set", option="D"),
                 NO, None)]
    for d in ("∅ ∪ {1}", "{1} ∪ ∅"):
        out += [(f"x-1=0: {{1}} letter D={d!r}", eqn("x - 1 = 0", options=_opts(d)), sol("{1}", "set", option="D"), OK, None),
                (f"x²+1=0: ∅ letter D={d!r} (wrong)", eqn("x**2 + 1 = 0", options=_opts(d)), sol("∅", "set", option="D"),
                 NO, None)]
    out += [
        ("|x|+1=0: {} letter D={∅}", eqn("Abs(x) + 1 = 0", options=_opts("{∅}")), sol("{}", "set", option="D"), NOTOK, None),
        ("2x+1=2x+3: kind none, letter D={∅}", eqn("2*x + 1 = 2*x + 3", options=_opts("{∅}")), sol("", "none", option="D"),
         NOTOK, None),
        ("x²<0: ∅ letter D={∅}", ir("solve_inequality", {"var": "x", "inequality": "x**2 < 0"}, shape="interval",
                                     options=_opts("{∅}")), sol("∅", "interval", option="D"), NOTOK, None),
        ("x²<0: ∅ letter D='Çözüm yok'", ir("solve_inequality", {"var": "x", "inequality": "x**2 < 0"}, shape="interval",
                                             options=_opts("Çözüm yok")), sol("∅", "interval", option="D"), OK, None),
        ("x²+1=0: ∅ letter D='{0} ∪ ∅' (wrong)", eqn("x**2 + 1 = 0", options=_opts("{0} ∪ ∅")), sol("∅", "set", option="D"),
         NO, None),
        ("x²+1=0: ∅ letter D='Reel sayılarda çözüm yok' (prose, read by nobody)",
         eqn("x**2 + 1 = 0", options=_opts("Reel sayılarda çözüm yok")), sol("∅", "set", option="D"), NOTNO, None),
        ("payload {∅} without a letter (control)", eqn("x**2 + 1 = 0"), sol("{∅}", "set"), NO, None),
        ("payload ∅ letter E={-1, 1} (wrong letter, control)", eqn("x**2 + 1 = 0", options=_opts("∅")),
         sol("∅", "set", option="E"), NO, None),
    ]
    return out


# B: G4-RK-5 -------------------------------------------------------------------------------------------------------
def cases_b():
    lin = eqn("2*x + 1 = 2*x + 3")
    sq = eqn("x**2 + 1 = 0")
    ab = eqn("Abs(x) + 1 = 0")
    sys2 = ir("solve_equation", {"var": "x"}, ["x + y = 1", "2*x + 2*y = 3"], [X, Y], "set")
    ineq = ir("solve_inequality", {"var": "x", "inequality": "x**2 + 2 < 2*x"}, shape="set")
    return [
        ("2x+1=2x+3: eq '1 = 3'", lin, sol("{}", "set", [("eq", "1 = 3")]), OK, NEITHER),
        ("2x+1=2x+3: eq '0 = 2'", lin, sol("{}", "set", [("eq", "0 = 2")]), OK, NEITHER),
        ("2x+1=2x+3: eq '2*x - 2*x = 3 - 1'", lin, sol("{}", "set", [("eq", "2*x - 2*x = 3 - 1")]), OK, NEITHER),
        ("2x+1=2x+3: eq '2*x + 1 - (2*x + 3) = 0' then '-2 = 0'", lin,
         sol("{}", "set", [("eq", "2*x + 1 - (2*x + 3) = 0"), ("eq", "-2 = 0")]), OK, NEITHER),
        ("x²+1=0: compute 'x**2 = -1'", sq, sol("{}", "set", [("compute", "x**2 = -1")]), OK, NEITHER),
        ("x²+1=0: eq 'x**2 = -1'", sq, sol("{}", "set", [("eq", "x**2 = -1")]), OK, NEITHER),
        ("|x|+1=0: eq 'Abs(x) = -1'", ab, sol("{}", "set", [("eq", "Abs(x) = -1")]), OK, NEITHER),
        ("|x|+1=0: compute 'Abs(x) = -1'", ab, sol("{}", "set", [("compute", "Abs(x) = -1")]), OK, NEITHER),
        ("x²+2<2x: eq '(x - 1)**2 + 1 < 0'", ineq, sol("{}", "set", [("eq", "(x - 1)**2 + 1 < 0")]), OK, NEITHER),
        ("x²+2<2x: eq '1 < 0'", ineq, sol("{}", "set", [("eq", "1 < 0")]), OK, NEITHER),
        ("x+y=1, 2x+2y=3: eq '2 = 3' (sibling)", sys2, sol("{}", "set", [("eq", "2 = 3")]), NOTNO, NEITHER),
        ("x+y=1, 2x+2y=3: compute '2*(x + y) = 2' (sibling)", sys2, sol("{}", "set", [("compute", "2*(x + y) = 2")]),
         NOTNO, NEITHER),
        # the premises have instances: a closed false step stays refuted
        ("2x+1=5: eq '2 = 3' (wrong)", eqn("2*x + 1 = 5"), sol("{2}", "set", [("eq", "2 = 3")]), NO, REF),
        ("2x+1=5: compute '5 - 1 = 3' (wrong)", eqn("2*x + 1 = 5"), sol("{2}", "set", [("compute", "5 - 1 = 3")]), NO, REF),
        ("x²=4: eq 'x = 3' (wrong)", eqn("x**2 = 4"), sol("{-2, 2}", "set", [("eq", "x = 3")]), NO, REF),
        ("x²=4: compute 'x**2 = -4' (wrong)", eqn("x**2 = 4"), sol("{-2, 2}", "set", [("compute", "x**2 = -4")]), NO, REF),
        ("x+y=1, x-y=3: eq '2 = 3' (wrong)", ir("solve_equation", {"var": "x"}, ["x + y = 1", "x - y = 3"], [X, Y], "set"),
         sol("{2}", "set", [("eq", "2 = 3")]), NO, REF),
        # a closed computation is true or false whatever the premises: a wrong one stays refuted
        ("x²+1=0: compute '0 - 4 = 4' (wrong arithmetic)", sq, sol("{}", "set", [("compute", "0 - 4 = 4")]), NO, REF),
        # empty premises, a wrong answer: the certificate refutes it all the same
        ("x²+1=0: {1} after '0 = 2'", sq, sol("{1}", "set", [("eq", "0 = 2")]), NO, NEITHER),
        # an IR domain that leaves the equation no instance: x positive, x + 1 = 0
        ("x>0, x+1=0: eq '1 = 0'", eqn("x + 1 = 0", vars_=[XP]), sol("{}", "set", [("eq", "1 = 0")]), OK, NEITHER),
        # the window: no instance inside it is no empty problem (the window is dropped, as before)
        ("max of x³-3x on [2, 4]: eq 'x = 3' after 3x²-3 = 0 (wrong)",
         ir("extremum", {"f": "x**3 - 3*x", "var": "x", "interval": "[2, 4]", "which": "max"}),
         sol("52", steps=[("eq", "3*x**2 - 3 = 0"), ("eq", "x = 3")]), NO, REF),
        ("cos x = -1 on [0, π): {} after a wrong 'x = 0'",
         ir("trig_solve", {"equation": "cos(x) = -1", "var": "x", "interval": "[0, pi)"}, shape="set"),
         sol("{}", "set", [("eq", "cos(x) = -1"), ("eq", "x = 0")]), NO, REF),
    ]


# C: G4YO-2 --------------------------------------------------------------------------------------------------------
def _der(f, v=XP):
    return ir("derivative", {"f": f, "var": "x"}, vars_=[v], shape="expression")


def _ev(e):
    return ir("evaluate", {"expr": e}, vars_=[])


def cases_c():
    out = []
    for name, q, claim in (
            ("(x√x/3)' = √x/2", _der("x*sqrt(x)/3"), "1/2√x"), ("(√x)' = 1/(2√x)", _der("sqrt(x)"), "1/2√x"),
            ("(πx²/4)' = πx/2", _der("pi*x**2/4", X), "x/2π"), ("(x²/(4π))' = x/(2π)", _der("x**2/(4*pi)", X), "x/2π"),
            ("π/2", _ev("asin(1)"), "1/2π"), ("1/(2π)", _ev("asin(1)/pi**2"), "1/2π"), ("√3/2", _ev("sin(pi/3)"), "1/2√3"),
            ("√3/6", _ev("sin(pi/3)/3"), "1/2√3"), ("3π/4", _ev("acos(-sqrt(2)/2)"), "3/4π"), ("3/(4π)", _ev("3*asin(1)/(2*pi**2)"), "3/4π"),
            ("π/8", _ev("asin(1)/4"), "1/2^3π"), ("π/2", _ev("asin(1)"), "1/2 π"), ("-√3/2", _ev("-sin(pi/3)"), "-1/2√3"),
            ("π/2 LaTeX", _ev("asin(1)"), "$1/2\\pi$"), ("1/(2π) LaTeX", _ev("asin(1)/pi**2"), "$1/2\\pi$"),
            ("3√2/4 LaTeX", _ev("3*sin(pi/4)/2"), "3/4\\sqrt{2}"), ("3/(4√2) LaTeX", _ev("3*sin(pi/4)/4"), "3/4\\sqrt{2}"),
            ("√x/2 LaTeX", _der("x*sqrt(x)/3"), "$1/2\\sqrt{x}$"), ("1/(2√x) LaTeX", _der("sqrt(x)"), "$1/2\\sqrt{x}$"),
            ("π/(2x) LaTeX", _der("pi*log(x)/2"), "$\\pi/2x$"), ("π/2 LaTeX thin space", _ev("asin(1)"), "1/2\\,\\pi"),
            ("(ln 2)/2 \\ln 2/2", _ev("log(sqrt(2))"), "$\\ln 2/2$"), ("(ln 2)/2 \\ln{2}/2", _ev("log(sqrt(2))"), "\\ln{2}/2"),
            ("0 \\ln 2/2", _ev("sin(pi)"), "\\ln 2/2"), ("cos(π/3) \\cos \\pi/3", _ev("sin(pi/6)"), "\\cos \\pi/3"),
            ("1/200 (half a percent)", _ev("asin(1)/(100*pi)"), "1/2%"), ("50", _ev("acos(-1)*50/pi"), "1/2%"),
            ("π/2 (90°)", _ev("asin(1)"), "180/2°")):
        out.append((f"{name}: claim {claim!r} (not read)", q, sol(claim, "expression" if q["answer_shape"] == "expression"
                                                                  else "value"), UNK, None))
    for name, q, claim, want in (
            ("(√x)' = 1/(2√x)", _der("sqrt(x)"), "1/(2√x)", OK), ("(√x)' = 1/(2√x)", _der("sqrt(x)"), "√x/2", NO),
            ("(x√x/3)' = √x/2", _der("x*sqrt(x)/3"), "√x/2", OK), ("π/2", _ev("asin(1)"), "π/2", OK),
            ("π/2", _ev("asin(1)"), "(1/2)π", OK), ("π/2", _ev("asin(1)"), "1/2·π", OK), ("π/2", _ev("asin(1)"), "1/2*π", OK),
            ("1/(2π)", _ev("asin(1)/pi**2"), "1/(2π)", OK), ("2π/3", _ev("acos(-1/2)"), "2π/3", OK), ("5π/6", _ev("acos(-sqrt(3)/2)"), "5π/6", OK),
            ("2√3/3", _ev("2*tan(pi/3)/3"), "2√3/3", OK), ("π/2", _ev("asin(1)"), "\\frac{1}{2}\\pi", OK),
            ("1/(2π)", _ev("asin(1)/pi**2"), "\\frac{1}{2\\pi}", OK), ("π/2", _ev("asin(1)"), "$1/2 \\cdot \\pi$", OK),
            ("2π/3", _ev("acos(-1/2)"), "$2\\pi/3$", OK), ("√3/2", _ev("sin(pi/3)"), "\\sqrt{3}/2", OK),
            ("(ln 2)/2", _ev("log(sqrt(2))"), "\\ln(2)/2", OK), ("(ln 2)/2", _ev("log(sqrt(2))"), "\\frac{\\ln 2}{2}", OK),
            ("1/sin(1)", _ev("csc(1)"), "1/\\sin 1", OK), ("π/2", _ev("asin(1)"), "1/(2π)", NO)):
        out.append((f"{name}: claim {claim!r}", q, sol(claim, "expression" if q["answer_shape"] == "expression" else "value"),
                    want, None))
    mc = _der("sqrt(x)")
    mc["options"] = {"A": "1/2√x", "B": "2√x", "C": "√x/2", "D": "1/x", "E": "x"}
    out += [("MC: option A '1/2√x', claim 1/(2√x) letter A", mc, sol("1/(2*sqrt(x))", "expression", option="A"), UNK, None),
            ("MC: option A '1/2√x', letter A alone", mc, sol(None, "expression", option="A"), UNK, None),
            ("MC: option C '√x/2', claim 1/(2√x) letter C (wrong)", mc, sol("1/(2*sqrt(x))", "expression", option="C"),
             NO, None),
            ("step 'Derivative(sqrt(x), x) = 1/2√x' is not refuted", _der("sqrt(x)"),
             sol("1/(2*sqrt(x))", "expression", [("compute", "Derivative(sqrt(x), x) = 1/2√x")]), NOTNO, NEITHER),
            ("step 'Derivative(sqrt(x), x) = √x/2' refuted (control)", _der("sqrt(x)"),
             sol("1/(2*sqrt(x))", "expression", [("compute", "Derivative(sqrt(x), x) = √x/2")]), NO, REF)]
    return out


# D: G4YO-3 --------------------------------------------------------------------------------------------------------
def cases_d():
    e = _ev("2 + 3")
    out = [(f"2+3: payload {p!r} (negated or doubted)", e, sol(p), UNK, None) for p in
           ("5 değil", "5 olamaz", "5 değildir", "5 değildir.", "5 yanlıştır", "5 olmayabilir", "5 sanmıyorum", "5 midir",
            "5 hariçtir", "5 çıkmaz", "5 olmuyor", "5 tutmuyor", "5 olabilir", "5 belki", "5 sanırım", "5 galiba",
            "5 herhalde", "5 muhtemelen", "5 mi?", "5 mıdır", "5 değil midir", "5 olmamalı", "5 is not", "5 is wrong",
            "5 is incorrect", "5 maybe", "5 DEĞİLDİR", "5 Yanlıştır")]
    out += [(f"2+3: payload {p!r} (plain prose)", e, sol(p), OK, None) for p in
            ("5 bulunur", "5 olur", "5 olarak bulunur", "5 olmalıdır", "5 elde edilir", "5 cm", "5 birim", "5 eşittir",
             "5 doğrudur", "5 is the answer", "5 tane", "5 sonucuna ulaşılır")]
    out += [("2+3: payload '6 değildir' (wrong value, negated)", e, sol("6 değildir"), UNK, None),
            ("2+3: payload '6 bulunur' (wrong value)", e, sol("6 bulunur"), NO, None)]
    return out


# E: G4-K-4 --------------------------------------------------------------------------------------------------------
def _xy(e, g, steps, claim, vars_=(X, Y)):
    return ir("evaluate", {"expr": e}, g, list(vars_)), sol(claim, steps=steps)


G1 = ["x**2 + y**2 + 2*x - 4*y + 5 = 0"]        # (x + 1)^2 + (y - 2)^2 = 0: x = -1, y = 2
G2 = ["sqrt(x - 2) + Abs(y + 3) = 0"]            # x = 2, y = -3
G3 = ["(x - 1)**2 + (y + 2)**2 = 0"]             # x = 1, y = -2
G4 = ["x**2 + 4*y**2 - 2*x + 8*y + 5 = 0"]       # (x - 1)^2 + 4(y + 1)^2 = 0: x = 1, y = -1
G5 = ["(x - 1)**2 + (y - 2)**2 + (z - 3)**2 = 0"]


def cases_e():
    out = []

    def add(name, pair, want, st):
        out.append((name, pair[0], pair[1], want, st))
    for st in (("eq", "x = 1"), ("eq", "x + y = 3"), ("compute", "x*y = 2"), ("eq", "(x - 1)**2 + (y + 2)**2 = 0"),
               ("eq", "y = -2")):
        add(f"G1: wrong {st[0]} {st[1]!r}, right answer 1", _xy("x + y", G1, [st], "1"), NO, REF)
    for st in (("eq", "(x + 1)**2 + (y - 2)**2 = 0"), ("eq", "x = -1"), ("eq", "y = 2"), ("compute", "x*y = -2"),
               ("eq", "x + y = 1")):
        add(f"G1: right {st[0]} {st[1]!r}", _xy("x + y", G1, [st], "1"), OK, NOTREF)
    add("G2: wrong eq 'x = -2', right answer -1", _xy("x + y", G2, [("eq", "x = -2")], "-1"), NO, REF)
    add("G2: wrong compute 'x*y = 6'", _xy("x + y", G2, [("compute", "x*y = 6")], "-1"), NO, REF)
    add("G2: right eq 'x = 2'", _xy("x + y", G2, [("eq", "x = 2")], "-1"), OK, NOTREF)
    add("G2: right compute 'x*y = -6'", _xy("x + y", G2, [("compute", "x*y = -6")], "-1"), OK, NOTREF)
    add("G3: wrong eq 'x = -1'", _xy("x*y", G3, [("eq", "x = -1")], "-2"), NO, REF)
    add("G3: right eq 'x = 1'", _xy("x*y", G3, [("eq", "x = 1")], "-2"), OK, NOTREF)
    add("G4: wrong eq 'y = 1'", _xy("x + y", G4, [("eq", "y = 1")], "0"), NO, REF)
    add("G4: right eq 'y = -1'", _xy("x + y", G4, [("eq", "y = -1")], "0"), OK, NOTREF)
    add("G5 (three unknowns): wrong eq 'x + y + z = 7'", _xy("x + y + z", G5, [("eq", "x + y + z = 7")], "6", (X, Y, Z)),
        NO, REF)
    add("G5 (three unknowns): right eq 'z = 3'", _xy("x + y + z", G5, [("eq", "z = 3")], "6", (X, Y, Z)), OK, NOTREF)
    add("x²+y²=0: wrong eq 'x = 1'", _xy("x + y", ["x**2 + y**2 = 0"], [("eq", "x = 1")], "0"), NO, REF)
    add("x²+y²=0: right eq 'x = 0'", _xy("x + y", ["x**2 + y**2 = 0"], [("eq", "x = 0")], "0"), OK, NOTREF)
    # a circle is no point: 'x = 1' is a choice, not refuted by this route
    add("x²+y²=1: eq 'x = 1' (a point of the circle)", _xy("x**2 + y**2", ["x**2 + y**2 = 1"], [("eq", "x = 1")], "1"),
        OK, NOTREF)
    # a cross term: (x + y)^2 + y^2, positive definite; (x + y)^2 = 0 is a line, no point
    add("x²+2xy+2y²=0 (cross term): wrong eq 'x = 1'", _xy("x + y", ["x**2 + 2*x*y + 2*y**2 = 0"], [("eq", "x = 1")], "0"),
        NO, REF)
    add("x²+2xy+y²=0 (a line): eq 'x = 1' (a choice)", _xy("x + y", ["x**2 + 2*x*y + y**2 = 0"], [("eq", "x = 1")], "0"),
        NOTNO, NOTREF)
    # a hyperbola and a line have real points: a wrong closed step stays refuted (no square to complete, no
    # nonnegative terms)
    add("x²-y²+1=0 (hyperbola): eq '1 = 2' (wrong)", _xy("x + y", ["x**2 - y**2 + 1 = 0"], [("eq", "1 = 2")], "1"), NO, REF)
    add("x+y+1=0 (a line): eq '1 = 2' (wrong)", _xy("x + y", ["x + y + 1 = 0"], [("eq", "1 = 2")], "-1"), NO, REF)
    # no real point (r > 0): the premises hold nowhere, no step refuted
    add("x²+y²+2x+2=0 (no real point): eq '1 = 0'", _xy("x + y", ["x**2 + y**2 + 2*x + 2 = 0"], [("eq", "1 = 0")], "0"),
        NOTOK, NEITHER)
    return out


# K: controls ------------------------------------------------------------------------------------------------------
def cases_k():
    return [
        ("x**2 = 4: {-2, 2}", eqn("x**2 = 4"), sol("{-2, 2}", "set"), OK, None),
        ("x**2 = 4: {2} wrong", eqn("x**2 = 4"), sol("{2}", "set"), NO, None),
        ("x**2 + 1 = 0: ∅", eqn("x**2 + 1 = 0"), sol("∅", "set"), OK, None),
        ("x**2 + 1 = 0: {} with a right step x**2 = -1", eqn("x**2 + 1 = 0"), sol("{}", "set", [("eq", "x**2 = -1")]),
         OK, NEITHER),
        ("x+1=4 with a wrong step x = 2", eqn("x + 1 = 4"), sol("{3}", "set", [("eq", "x = 2")]), NO, REF),
        ("evaluate 2**10 = 1024", _ev("2**10"), sol("1024"), OK, None),
        ("payload '11 bu çözüm doğrudur' for 2+3", _ev("2 + 3"), sol("11 bu çözüm doğrudur"), NO, None),
        ("payload '5 bu çözüm doğrudur'", _ev("2 + 3"), sol("5 bu çözüm doğrudur"), OK, None),
        ("x>0 given, compute 'Abs(x) = x'", ir("evaluate", {"expr": "x"}, ["x > 0", "x**2 = 4"]),
         sol("2", steps=[("compute", "Abs(x) = x")]), OK, NOTREF),
        ("sin(π/6) = 1/2", _ev("sin(pi/6)"), sol("1/2"), OK, None),
        ("π/6 + 2kπ notation", ir("evaluate", {"expr": "asin(1/2)"}), sol("π/6"), OK, None),
    ]


# F: SA-YO-1 -------------------------------------------------------------------------------------------------------
def cases_f():
    q5 = eqn("x**2 - 2*x + 5 = 0")
    q1 = eqn("x**2 + 1 = 0")
    qs = eqn("sqrt(x) + 1 = 0")
    cnt = ir("count_roots", {"expr": "x**2 + x + 1", "var": "x"})
    ineq = ir("solve_inequality", {"var": "x", "inequality": "x**2 + 2 < 2*x"}, shape="set")
    return [
        ("x²-2x+5=0: compute '... = (x - 1)**2 + 6' (wrong square)", q5,
         sol("∅", "set", [("compute", "x**2 - 2*x + 5 = (x - 1)**2 + 6")]), NO, REF),
        ("x²-2x+5=0: compute '... = (x - 1)**2 + 4' (right)", q5,
         sol("∅", "set", [("compute", "x**2 - 2*x + 5 = (x - 1)**2 + 4")]), OK, NOTREF),
        ("count x²+x+1: compute '(x + 1/2)**2 + 1/2' (wrong)", cnt,
         sol("0", "count", [("compute", "x**2 + x + 1 = (x + 1/2)**2 + 1/2")]), NO, REF),
        ("x⁴+x²+1=0: compute '= (x**2 + 1)**2' (wrong)", eqn("x**4 + x**2 + 1 = 0"),
         sol("∅", "set", [("compute", "x**4 + x**2 + 1 = (x**2 + 1)**2")]), NO, REF),
        ("x²+1=0: compute 'Derivative(x**2, x) = 3*x' (wrong)", q1,
         sol("∅", "set", [("compute", "Derivative(x**2, x) = 3*x")]), NO, REF),
        ("x²+1=0: compute 'x**2 + 1 = x**2 - 1' (wrong)", q1, sol("∅", "set", [("compute", "x**2 + 1 = x**2 - 1")]), NO, REF),
        ("x²+1=0: compute 'x**4 = -1' (false at ±i)", q1, sol("∅", "set", [("compute", "x**4 = -1")]), NO, REF),
        ("x²+4=0: compute '(x + 2)**2 = x**2 + 4' (wrong)", eqn("x**2 + 4 = 0"),
         sol("∅", "set", [("compute", "(x + 2)**2 = x**2 + 4")]), NO, REF),
        ("x²+1=0: compute '(x**3 + x)/x = x**2 - 1' (its written pole is no solution)", q1,
         sol("∅", "set", [("compute", "(x**3 + x)/x = x**2 - 1")]), NO, REF),
        # the decision's cases: still withdrawn
        ("x²+1=0: compute 'x**2 = -1' (a multiple)", q1, sol("∅", "set", [("compute", "x**2 = -1")]), OK, NEITHER),
        ("x²+1=0: eq 'x**2 = -1'", q1, sol("∅", "set", [("eq", "x**2 = -1")]), OK, NEITHER),
        ("sqrt(x)+1=0: eq 'sqrt(x) = -1' (a multiple)", qs, sol("∅", "set", [("eq", "sqrt(x) = -1")]), OK, NEITHER),
        ("sqrt(x)+1=0: compute 'sqrt(x) = -1' (a multiple)", qs, sol("∅", "set", [("compute", "sqrt(x) = -1")]), OK, NEITHER),
        ("x²+1=0: compute '(x**2 + 1)*(x - 1) = 0' (true at ±i)", q1,
         sol("∅", "set", [("compute", "(x**2 + 1)*(x - 1) = 0")]), OK, NEITHER),
        ("x²+1=0: compute 'x**4 = 1' (true at ±i)", q1, sol("∅", "set", [("compute", "x**4 = 1")]), OK, NEITHER),
        ("x/(x-1)=1: compute 'x = x - 1' (no complex solution either)", eqn("x/(x - 1) = 1"),
         sol("∅", "set", [("compute", "x = x - 1")]), OK, NEITHER),
        ("2x+1=2x+3: eq '0 = 2' (closed)", eqn("2*x + 1 = 2*x + 3"), sol("∅", "set", [("eq", "0 = 2")]), OK, NEITHER),
        ("x²+2<2x: eq '(x - 1)**2 + 1 < 0' (a multiple of the order)", ineq,
         sol("∅", "set", [("eq", "(x - 1)**2 + 1 < 0")]), OK, NEITHER),
        # undecided: an order or a transcendental premise has no complex reading; the compute step blocks CORRECT
        ("x²+2<2x: compute 'x**2 - 2*x + 2 = (x - 1)**2 + 2' (undecided)", ineq,
         sol("∅", "set", [("compute", "x**2 - 2*x + 2 = (x - 1)**2 + 2")]), UNK, NEITHER),
        ("2^x+3=0: compute '2**x + 3 = 2**(x + 3)' (undecided)", eqn("2**x + 3 = 0"),
         sol("∅", "set", [("compute", "2**x + 3 = 2**(x + 3)")]), UNK, NEITHER),
        ("|x-1|+|x+1|=1: compute '... = 2*Abs(x)' (undecided)", eqn("Abs(x - 1) + Abs(x + 1) = 1"),
         sol("∅", "set", [("compute", "Abs(x - 1) + Abs(x + 1) = 2*Abs(x)")]), UNK, NEITHER),
        # false at ±i only after the evaluation: the claim as written is 0/0 there (principle 12)
        ("x²+1=0: compute '(x**4 - 1)/(x**2 + 1) = 0' (a written pole)", q1,
         sol("∅", "set", [("compute", "(x**4 - 1)/(x**2 + 1) = 0")]), UNK, NEITHER),
        ("x²+1=0: compute '(x**2 + 1)*(x - 1)/(x**2 + 1) = 0' (a written pole)", q1,
         sol("∅", "set", [("compute", "(x**2 + 1)*(x - 1)/(x**2 + 1) = 0")]), UNK, NEITHER),
        ("x²+1=0: compute '1/(x**2 + 1) = 0' (a pole)", q1, sol("∅", "set", [("compute", "1/(x**2 + 1) = 0")]), UNK, NEITHER),
        # an eq step, undecided, is unknown as on the base
        ("x²+2<2x: eq 'x**2 - 2*x + 2 = (x - 1)**2 + 2' (undecided, eq)", ineq,
         sol("∅", "set", [("eq", "x**2 - 2*x + 2 = (x - 1)**2 + 2")]), OK, NEITHER),
    ]


# G: SA-RK-1, SA-RK-2 ----------------------------------------------------------------------------------------------
NS2 = ["Gerçek kökü yoktur", "Denklemin gerçek kökü yoktur", "Gerçek kök yoktur", "Gerçek kökleri yoktur",
       "Gerçek sayılarda çözümü yoktur", "Denklemin gerçek sayılarda çözümü yoktur", "Gerçek çözüm yoktur",
       "Gerçel kökü yoktur", "Reel kökü yoktur", "Kökü yoktur", "Çözümü yoktur", "Reel sayılarda çözüm yoktur",
       "Boş küme (∅)", "Çözüm yok (∅)", "ÇK = ∅", "Ç.K. = ∅", "Ç = ∅'dir", "Çözüm kümesi Ø'dir", "There is no solution",
       "No real roots", "Çözüm kümesi { }", "{ } (boş küme)", "Çözüm kümesi boş kümedir."]
DOM = ["Tanım kümesi boş kümedir", "T.K. = ∅", "TK = ∅", "D(f) = ∅", "Tanım kümesi ∅"]


def cases_g():
    out = []
    for d in NS2:
        q = eqn("x**2 + 4 = 0", options={"A": "{-2, 2}", "B": "{2}", "C": "{-2}", "D": "{0}", "E": d})
        out += [(f"x²+4=0: ∅ letter E={d!r}", q, sol("∅", "set", option="E"), OK, None),
                (f"x²+4=0: letter E={d!r} alone", q, sol(None, "set", option="E"), OK, None),
                (f"x-2=0: {{2}} letter E={d!r} (wrong)", eqn("x - 2 = 0", options={"A": "{-2, 2}", "B": "{2}", "E": d}),
                 sol("{2}", "set", option="E"), NO, None)]
    for d in DOM:
        q = ir("domain_of", {"expr": "sqrt(-x**2 - 1)", "var": "x"}, shape="set",
               options={"A": "ℝ", "B": "[-1, 1]", "C": "(0, ∞)", "D": d, "E": "{0}"})
        out += [(f"domain sqrt(-x²-1): ∅ letter D={d!r}", q, sol("∅", "set", option="D"), OK, None),
                (f"domain sqrt(-x²-1): letter D={d!r} alone", q, sol(None, "set", option="D"), OK, None)]
    for d in ("Gerçek sayılarda çözümü yoktur", "Gerçek çözümü yoktur", "Hiçbir gerçek sayı için sağlanmaz"):
        q = ir("solve_inequality", {"var": "x", "inequality": "x**2 + 1 < 0"}, shape="interval",
               options={"A": "(-1, 1)", "B": "ℝ", "C": "(0, ∞)", "D": d, "E": "{0}"})
        out.append((f"x²+1<0: ∅ letter D={d!r}", q, sol("∅", "interval", option="D"), OK, None))
    # a 'yok' no reading takes, beside ∅: undecided, never a refutation
    for d in ("Bu denklemin reel sayılarda bir kökü yok", "Gerçek kök yok, karmaşık kökler var",
              "Sağlayan bir x değeri yoktur", "Denklemi sağlayan sayı yok"):
        q = eqn("x**2 + 4 = 0", options={"A": "{-2, 2}", "B": "{2}", "E": d})
        out += [(f"x²+4=0: ∅ letter E={d!r} (prose)", q, sol("∅", "set", option="E"), NOTNO, None),
                (f"x²+4=0: letter E={d!r} alone (prose)", q, sol(None, "set", option="E"), NOTNO, None)]
    for d in ("{∅}", "{0} ∪ ∅", "Çözüm yok değil", "∅ değildir"):
        q = eqn("x**2 + 4 = 0", options={"A": "{-2, 2}", "B": "{2}", "E": d})
        out.append((f"x²+4=0: ∅ letter E={d!r} (no empty set)", q, sol("∅", "set", option="E"), NOTOK, None))
    return out


# H: SA-YO-2, SA-RK-3, SA-RK-5, SA-RK-6 ----------------------------------------------------------------------------
def cases_h():
    e = _ev("2 + 3")
    out = [(f"2+3: payload {p!r} (rejected)", e, sol(p), UNK, None) for p in
           ("5 sağlamadı", "5 çıkmadı", "5 tutmadı", "5 bulunamadı", "5 sağlamadığından", "5 tutmadığı için", "5 çıkmayacak",
            "5 sağlamamaktadır", "5 geçersiz", "5 geçersizdir", "5 reddedilir", "5 reddedildi", "5 elenir", "5 hatalı",
            "5 hatalıdır", "5 (reddedilir)", "5 ✗", "5 ❌", "5 is invalid", "5 is rejected", "5 is extraneous",
            "5 (başka çözüm yoktur)", "5 (diğer kök tanım kümesine girmez)", "5 muhtemelen", "5 tahminen", "5 şüpheli")]
    out += [(f"x-5=0: payload {p!r} (rejected)", eqn("x - 5 = 0"), sol(p, "set"), UNK, None)
            for p in ("{5} reddedilir", "{5} geçersizdir", "{5} sağlamadı")]
    out += [(f"2+3: payload {p!r} (affirmative)", e, sol(p), OK, None) for p in
            ("5 olabilecek en büyük değerdir", "5 olabilecek en küçük değer", "5 (negatif olmayan tek değer)",
             "5 (negatif olmayan kök)", "5 (sıfır olmayan değer)", "5 şüphesiz", "5 kuşkusuz", "5 değişmez",
             "5 (sabit kalır, değişmez)", "5 (tahmin edilen değer)", "5 (olası en büyük değer)", "5 (en büyük değer)",
             "5 is the largest possible value", "5 kesinlikle", "5 tamsayısıdır", "5 (tek çözüm)", "5 cevaptır")]
    out.append(("6*6: payload '36 muhtemel durum' (affirmative)", _ev("6*6"), sol("36 muhtemel durum"), OK, None))
    out += [(f"payload {p!r} (an unknown word: not read)", e, sol(p), UNK, None)
            for p in ("5 civarında", "5 yaklaşık", "5 kadar", "5 falan")]
    # a symbol of the problem is never prose (SA-RK-5)
    out += [("e^(iπ/3): payload '1/2 + √3/2 i'", _ev("exp(I*pi/3)"), sol("1/2 + √3/2 i"), NOTNO, None),
            ("(1+2i)(1+i): payload '-1 + 3 i'", _ev("(1 + 2*I)*(1 + I)"), sol("-1 + 3 i"), NOTNO, None),
            ("2+3i: payload '2 + 3 i'", _ev("2 + 3*I"), sol("2 + 3 i"), NOTNO, None),
            ("3i: payload '3 i'", _ev("3*I"), sol("3 i"), NOTNO, None),
            ("e+e: payload '2 e'", _ev("exp(1) + exp(1)"), sol("2 e"), NOTNO, None),
            ("(x²)': payload '2 x'", _der("x**2", X), sol("2 x", "expression"), NOTNO, None),
            ("x+1 at x=4: payload '5 m' (a single letter)", _ev("2 + 3"), sol("5 m"), NOTNO, None)]
    # a final comma is punctuation (SA-RK-6)
    out += [(f"payload {p!r} (a final comma)", q, sol(p, k), OK, None) for q, p, k in
            ((e, "5,", "value"), (e, "5, kesinlikle", "value"), (e, "5;", "value"), (e, "$5,$", "value"),
             (_ev("sin(pi/6)"), "1/2,", "value"), (_ev("sin(pi/6)"), "$1/2,$", "value"),
             (eqn("x**2 - 5*x + 6 = 0"), "{2, 3}, kesinlikle", "set"))]
    out += [("payload '(5,)' (a tuple of one element)", e, sol("(5,)"), UNK, None),
            ("payload '6,' (wrong, a final comma)", e, sol("6,"), NO, None)]
    return out


# J: SA-YO-3, SA-RK-4, SA-YO-4 -------------------------------------------------------------------------------------
def cases_j():
    out = [(f"{name}: claim {claim!r} (not read)", q, sol(claim, "expression" if q["answer_shape"] == "expression"
                                                          else "value"), UNK, None) for name, q, claim in (
        ("log₂(8/3)", _ev("log(8/3, 2)"), "$\\log_2 8/3$"), ("(log₂8)/3 = 1", _ev("log(8, 2)/3"), "$\\log_2 8/3$"),
        ("log₃(9/2)", _ev("log(9/2, 3)"), "$\\log_3 9/2$"), ("(log₃2)/2", _ev("log(2)/log(9)"), "$\\log_3 2/2$"),
        ("(log₃2)/2 braced base", _ev("log(2)/log(9)"), "$\\log_{3}2/2$"), ("(log₃2)/2 braced arg", _ev("log(2)/log(9)"), "$\\log_3{2}/2$"),
        ("log₂3", _ev("log(3, 2)"), "$\\log_2 9/2$"), ("sin(3π/2)", _ev("sin(3*pi/2)"), "$\\sin 3\\pi/2$"),
        ("sin x", _der("-cos(x)", X), "$\\sin 2x/2$"), ("ln x", _der("x*log(x) - x"), "$\\ln 2x/2$"),
        ("(1/2)% = 1/200", _ev("asin(1)/(100*pi)"), "$1/2\\%$"), ("50", _ev("acos(-1)*50/pi"), "1/2\\%"),
        ("3/400", _ev("3*asin(1)/(200*pi)"), "$3/4\\%$"), ("90° = π/2", _ev("asin(1)"), "$180/2^\\circ$"),
        ("-π/2", _ev("-asin(1)"), "1/−2π"), ("-π/2 en dash", _ev("-asin(1)"), "1/–2π"), ("-√3/2", _ev("-sin(pi/3)"), "1/−2√3"))]
    sin2 = _der("sin(x)**2", X)
    out += [(f"{name}: claim {claim!r}", q, sol(claim, "expression" if q["answer_shape"] == "expression" else "value"),
             want, None) for name, q, claim, want in (
        ("(sin²x)' = 2 sin x cos x", sin2, "$2\\sin x \\cdot \\cos x$", OK), ("(sin²x)' = sin 2x", sin2, "$\\sin 2x$", OK),
        ("(sin²x)' wrong 3 sin x cos x", sin2, "$3\\sin x \\cdot \\cos x$", NO),
        ("3 sin(1)", _ev("sin(1) + sin(1) + sin(1)"), "$\\sin 1 \\cdot 3$", OK), ("(ln 2)/2 \\frac", _ev("log(sqrt(2))"), "$\\frac{\\ln 2}{2}$", OK),
        ("log₃2 / 2 \\frac", _ev("log(2)/log(9)"), "$\\frac{\\log_3 2}{2}$", OK), ("log₂8 = 3", _ev("asin(1)*6/pi"), "$\\log_2 8$", OK),
        ("sin(x)/2 with brackets", _der("-cos(x)/2", X), "$\\sin(x)/2$", OK), ("1/(-2π)", _ev("-1/(2*asin(1)*2)"), "1/(−2π)", OK),
        ("-π/2 Unicode minus", _ev("-asin(1)"), "−π/2", OK), ("50%", _ev("asin(1)/pi"), "50\\%", OK))]
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "J": cases_j, "K": cases_k}


def main(out_path=None, groups="ABCDEFGHJK"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for case in GROUPS[g]():
            label, q, s, verdicts, statuses = case[:5]
            t = time.time()
            status, flags = None, []
            try:
                r = verify(q, s)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                status = steps[-1].get("status") if steps else None
                flags = sorted({f for la in r.layers for f in (la.flags or [])} | set(r.flags))[:6]
            except Exception as e:  # noqa: BLE001
                verdict = f"EXC {type(e).__name__}: {e}"
            ok = verdict in verdicts and (statuses is None or status in statuses)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok, "flags": flags,
                         "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {time.time() - t:5.1f}s {label}  {flags}",
                  flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCDEFGHJK"
    sys.exit(1 if main(out, grp) else 0)
