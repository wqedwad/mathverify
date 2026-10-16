"""The final attack after the fourth audit (A+, merged 7892190; DECISIONS §89-§91), lens 1/4 "steps, multiple choice"
(16 Oct 2026): the findings G1RK-1, G1RK-2, G1RK-3 and G1RK-8 and their sibling paths, on the branch wip/son-adim.

  A  G1RK-2  the boundary equation of an inequality premise (the sign-table method): x**2 - 5*x + 6 = 0,
             (x - 2)*(x - 3) = 0, x = 2 or x = 3 for x**2 - 5*x + 6 < 0 are no consequences of it; checked on the
             boundary equation, a wrong critical point (x = 5) is still refuted. The params and the givens form; a
             non-strict inequality; the gains of round 2 of d4h (T08/T09 chains verified) and PRE-RK-4 kept
  B  G1RK-3  '%' and '°' are unit marks: on one side only, and nothing in the question fixing the unit, the two
             readings (%20 = 1/5 and 20, 30° = pi/6 and 30) decide only where they agree: both different INCORRECT,
             one equal UNKNOWN, never CORRECT this way. TYT percentage and angle questions (increase, discount, the
             angles of a triangle, a polygon's interior and exterior angle); trig_solve keeps its radians; LaTeX
             30^\\circ is a degree (it was the number 30, and \\sin(30^\\circ) was sin(30))
  C  G1RK-1  an option is read by the claim's own reader (namespace, answer shape, notation, cleaning): 'x ∈ (2, 3)',
             '2, 3', '6 cm', 'π/6 rad' read as the claim reads them; an option still unread blocks CORRECT; a wrong
             letter in a newly read notation is refuted; wordproblem's check of the options reads them the same way
  D  G1RK-8  a count wrong under both readings of 0**0 (3, 6) is never CORRECT; the two readings (4, 5) UNKNOWN
  E  G1RK-5  (recorded; a cheap exact path) f(f(1)) of a piecewise f: the inner Piecewise taken to its certified branch
  K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/son/adim/sonda.py [out.json] [groups]

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
NEITHER = {"unknown", "skipped", None}

X = {"name": "x", "domain": "real"}
XI = {"name": "x", "domain": "integer"}
P12 = [{"name": "p1", "domain": "real"}, {"name": "p2", "domain": "real"}]


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


def ineq(e, shape="set"):
    return ir("solve_inequality", {"inequality": e, "var": "x"}, shape=shape)


def gineq(e, shape="set"):
    return ir("solve_inequality", {"var": "x"}, [e], shape=shape)


# A: G1RK-2 --------------------------------------------------------------------------------------------------------
A23 = "Interval.open(2, 3)"
CRIT = [("eq", "x**2 - 5*x + 6 = 0"), ("eq", "(x - 2)*(x - 3) = 0"), ("eq", "Or(Eq(x, 2), Eq(x, 3))")]


def cases_a():
    out = []
    for form, q in (("params", ineq("x**2 - 5*x + 6 < 0")), ("givens", gineq("x**2 - 5*x + 6 < 0"))):
        out += [
            (f"{form}: critical eq, factor, Or roots (T201)", q, sol(A23, "interval", CRIT), OK, NEITHER),
            (f"{form}: x**2 - 5x + 6 = 0 alone", q, sol(A23, "interval", CRIT[:1]), OK, NEITHER),
            (f"{form}: 'x = 2 or x = 3' alone (T05)", q, sol(A23, "interval", CRIT[2:]), OK, NEITHER),
            (f"{form}: wrong critical point x = 5", q, sol(A23, "interval", [("eq", "x = 5")]), NO, REF),
            (f"{form}: critical eq then x = 5", q, sol(A23, "interval", CRIT[:1] + [("eq", "x = 5")]), NO, REF),
            (f"{form}: Or roots with a wrong root 5", q, sol(A23, "interval", CRIT[:2] + [("eq", "Or(Eq(x, 2), Eq(x, 5))")]),
             NO, REF),
            (f"{form}: a wrong factorization", q, sol(A23, "interval", CRIT[:1] + [("eq", "(x - 1)*(x - 6) = 0")]), NO, REF),
            (f"{form}: wrong side x < 2", q, sol(A23, "interval", [("eq", "x < 2")]), NO, REF),
            (f"{form}: wrong direction > 0", q, sol(A23, "interval", [("eq", "x**2 - 5*x + 6 > 0")]), NO, REF),
            (f"{form}: factored inequality, then critical points", q,
             sol(A23, "interval", [("eq", "(x - 2)*(x - 3) < 0")] + CRIT[:1] + CRIT[2:]), OK, NEITHER),
            (f"{form}: factored inequality, then a wrong critical point", q,
             sol(A23, "interval", [("eq", "(x - 2)*(x - 3) < 0"), ("eq", "Or(Eq(x, 2), Eq(x, 5))")]), NO, REF),
            (f"{form}: right steps, wrong answer [2, 3]", q, sol("Interval(2, 3)", "interval", CRIT), NO, None),
        ]
    nonstrict = ineq("x**2 - 5*x + 6 <= 0")
    out += [
        ("non-strict <= 0: critical steps (sibling)", nonstrict, sol("Interval(2, 3)", "interval", CRIT), OK, None),
        ("non-strict <= 0: x**2 - 5x + 6 = 0 alone", nonstrict, sol("Interval(2, 3)", "interval", CRIT[:1]), OK, NEITHER),
        ("non-strict <= 0: wrong root 4", nonstrict, sol("Interval(2, 3)", "interval", CRIT[:1] + [("eq", "Or(Eq(x, 2), Eq(x, 4))")]),
         NO, REF),
        ("x**2 >= 9: x**2 = 9 (T15)", ineq("x**2 >= 9"), sol("Union(Interval(-oo, -3), Interval(3, oo))", "interval",
                                                              [("eq", "x**2 = 9")]), OK, NEITHER),
        ("x**2 - 4 >= 0: Or roots (T204)", ineq("x**2 - 4 >= 0"), sol("Union(Interval(-oo, -2), Interval(2, oo))", "interval",
                                                                      [("eq", "Or(Eq(x, -2), Eq(x, 2))")]), OK, NEITHER),
        ("(x - 1)/(x + 2) >= 0: zeros Or (T203)", ineq("(x - 1)/(x + 2) >= 0"),
         sol("Union(Interval.open(-oo, -2), Interval(1, oo))", "interval", [("eq", "Or(Eq(x, 1), Eq(x, -2))")]), OK, NEITHER),
        ("|x - 3| < 2: boundary |x - 3| = 2", ineq("Abs(x - 3) < 2"), sol("Interval.open(1, 5)", "interval",
                                                                          [("eq", "Abs(x - 3) = 2"), ("eq", "Or(Eq(x, 1), Eq(x, 5))")]),
         OK, NEITHER),
        ("|x - 3| < 2: wrong boundary point 6", ineq("Abs(x - 3) < 2"), sol("Interval.open(1, 5)", "interval",
                                                                           [("eq", "Abs(x - 3) = 2"), ("eq", "Or(Eq(x, 1), Eq(x, 6))")]),
         NO, REF),
        # the gains of round 2 of d4h: chains derived from the inequality are verified
        ("T08 log(x - 1) < 1 chain verified", ineq("log(x - 1) < 1"), sol("Interval.open(1, 1 + E)", "interval", [
            ("eq", "x - 1 > 0"), ("eq", "x - 1 < E"), ("eq", "x < 1 + E")]), OK, VER),
        ("T09 |x - 3| < 2 chain verified", ineq("Abs(x - 3) < 2"), sol("Interval.open(1, 5)", "interval", [
            ("eq", "-2 < x - 3"), ("eq", "x - 3 < 2"), ("eq", "x > 1"), ("eq", "x < 5")]), OK, VER),
        ("T202 factored inequality then chain", ineq("x**2 - 5*x + 6 < 0"), sol(A23, "interval", [
            ("eq", "(x - 2)*(x - 3) < 0"), ("eq", "2 < x < 3")]), OK, VER),
        ("PRE-RK-4 x**2 < 4: x < 2 verified", ineq("x**2 < 4"), sol("Interval.open(-2, 2)", "interval", [("eq", "x < 2")]),
         OK, VER),
        ("PRE-RK-4 x**2 < 4: x < 1 refuted", ineq("x**2 < 4"), sol("Interval.open(-2, 2)", "interval", [("eq", "x < 1")]),
         NO, REF),
        ("PRE-RK-4 x**2 - x - 2 = 0: x + 2 = x**2", ir("solve_equation", {"equation": "x**2 - x - 2 = 0", "var": "x"},
                                                       shape="set"), sol("{-1, 2}", "set", [("eq", "x + 2 = x**2")]), OK, VER),
        ("PRE-RK-4 x**2 - x - 2 = 0: x + 2 = x**3 refuted", ir("solve_equation", {"equation": "x**2 - x - 2 = 0",
                                                                                  "var": "x"}, shape="set"),
         sol("{-1, 2}", "set", [("eq", "x + 2 = x**3")]), NO, REF),
        # an inequality given next to an equation: a claim against it stays refuted (no boundary of theirs)
        ("x > 0, x**2 = 4: x = -2 refuted", ir("evaluate", {"expr": "x"}, ["x > 0", "x**2 = 4"]),
         sol("2", steps=[("eq", "x = -2")]), NO, REF),
        ("x > 0, x**2 = 4: x = 2 verified", ir("evaluate", {"expr": "x"}, ["x > 0", "x**2 = 4"]),
         sol("2", steps=[("eq", "x = 2")]), OK, VER),
        ("x > 0: x = -1 refuted (boundary x = 0)", ir("evaluate", {"expr": "x**2"}, ["x > 0"], shape="expression"),
         sol("x**2", "expression", [("eq", "x = -1")]), NO, REF),
    ]
    return out


# B: G1RK-3 --------------------------------------------------------------------------------------------------------
PCT = {"A": "%10", "B": "%20", "C": "%25", "D": "%30", "E": "%40"}
DEG = {"A": "20°", "B": "30°", "C": "40°", "D": "50°", "E": "60°"}


def _mc(q, options):
    return dict(q, options=options)


def cases_b():
    inc = ir("evaluate", {"expr": "(p2 - p1)/p1*100"}, ["p1 = 50", "p2 = 60"], P12)          # artış yüzdesi: 20
    frac = ir("evaluate", {"expr": "(p2 - p1)/p1"}, ["p1 = 50", "p2 = 60"], P12)             # the same as a fraction
    disc = ir("evaluate", {"expr": "(a - b)/a*100"}, ["a = 200", "b = 170"],
              [{"name": "a", "domain": "real"}, {"name": "b", "domain": "real"}])          # iskonto: 15
    prof = ir("evaluate", {"expr": "(s - c)/c*100"}, ["c = 80", "s = 100"],
              [{"name": "c", "domain": "real"}, {"name": "s", "domain": "real"}])          # kâr: 25
    tri = ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = 180"])                              # üçgen açıları: 30
    tri_r = ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = pi"])                             # the same in radians
    big = ir("evaluate", {"expr": "3*x"}, ["x + 2*x + 3*x = 180"])                            # the largest angle: 90
    N = [{"name": "n", "domain": "positive_integer"}]
    hexa = ir("evaluate", {"expr": "(n - 2)*180/n"}, ["n = 6"], N)                            # iç açı: 120
    octo = ir("evaluate", {"expr": "360/n"}, ["n = 8"], N)                                    # dış açı: 45
    oh = {"A": "108°", "B": "120°", "C": "135°", "D": "144°", "E": "150°"}
    oo = {"A": "30°", "B": "36°", "C": "40°", "D": "45°", "E": "60°"}
    od = {"A": "%10", "B": "%15", "C": "%20", "D": "%25", "E": "%30"}
    out = []
    for lab, q, opts, right, wrong in (("increase", inc, PCT, "B", "C"), ("discount", disc, od, "B", "C"),
                                       ("profit", prof, od, "D", "E"), ("triangle", tri, DEG, "B", "C"),
                                       ("largest angle", big, {"A": "60°", "B": "75°", "C": "90°", "D": "100°", "E": "120°"},
                                        "C", "D"),
                                       ("hexagon interior", hexa, oh, "B", "C"), ("octagon exterior", octo, oo, "D", "E")):
        rv = opts[right].replace("%", "").replace("°", "")
        wv = opts[wrong].replace("%", "").replace("°", "")
        out += [
            (f"{lab}: payload {rv}, right letter {opts[right]}", _mc(q, opts), sol(rv, option=right), UNK, None),
            (f"{lab}: payload {opts[right]}, right letter", _mc(q, opts), sol(opts[right], option=right), UNK, None),
            (f"{lab}: right letter only", _mc(q, opts), sol(None, option=right), UNK, None),
            (f"{lab}: payload {opts[right]}, no options", q, sol(opts[right]), UNK, None),
            (f"{lab}: payload {rv}, no options", q, sol(rv), OK, None),
            (f"{lab}: payload {wv}, its letter {opts[wrong]} (wrong)", _mc(q, opts), sol(wv, option=wrong), NO, None),
            (f"{lab}: payload {rv}, wrong letter {opts[wrong]}", _mc(q, opts), sol(rv, option=wrong), NO, None),
            (f"{lab}: wrong letter only {opts[wrong]}", _mc(q, opts), sol(None, option=wrong), NO, None),
            (f"{lab}: payload {opts[wrong]} no options (wrong)", q, sol(opts[wrong]), NO, None),
        ]
    out += [
        # the IR in the unit's own reading: one reading equal, never CORRECT this way (DECISIONS: G1RK-3)
        ("fraction IR: payload %20, letter %20", _mc(frac, PCT), sol("%20", option="B"), UNK, None),
        ("fraction IR: letter %20 only", _mc(frac, PCT), sol(None, option="B"), UNK, None),
        ("fraction IR: letter %25 only (wrong)", _mc(frac, PCT), sol(None, option="C"), NO, None),
        ("radian IR: payload pi/6, letter 30°", _mc(tri_r, DEG), sol("pi/6", option="B"), UNK, None),
        ("radian IR: letter 40° only (wrong)", _mc(tri_r, DEG), sol(None, option="C"), NO, None),
        ("asin(1/2): payload pi/6, letter 30°", _mc(ir("evaluate", {"expr": "asin(1/2)"}), DEG), sol("pi/6", option="B"),
         UNK, None),
        ("asin(1/2): payload pi/6, letter 40° (wrong)", _mc(ir("evaluate", {"expr": "asin(1/2)"}), DEG),
         sol("pi/6", option="C"), NO, None),
        # spellings of the marks
        ("triangle: payload 30 derece", tri, sol("30 derece"), UNK, None),
        ("triangle: payload 30^\\circ (LaTeX)", tri, sol("30^\\circ"), UNK, None),
        ("triangle: payload 30^{\\circ} (LaTeX)", tri, sol("30^{\\circ}"), UNK, None),
        ("triangle: payload 40^\\circ (LaTeX, wrong)", tri, sol("40^\\circ"), NO, None),
        ("increase: payload 20% (mark after)", _mc(inc, PCT), sol("20%", option="B"), UNK, None),
        ("increase: payload 20\\% (LaTeX)", inc, sol("20\\%"), UNK, None),
        ("increase: option '% 20', payload 20", _mc(inc, dict(PCT, B="% 20")), sol("20", option="B"), UNK, None),
        # the unit fixed by the question: decided as before
        ("synthetic_geometry angle(): 70 against 70° (25 Sep rule)", *_geo_angle("70", "D"), OK, None),
        ("synthetic_geometry angle(): 70° payload", *_geo_angle("70°", None), OK, None),
        ("synthetic_geometry angle(): 70^\\circ payload (LaTeX)", *_geo_angle("70^\\circ", None), OK, None),
        ("synthetic_geometry angle(): 60, wrong letter", *_geo_angle("60", "D"), NO, None),
        ("trig_solve [0, 2pi]: {30°, 150°}", _trig("[0, 2*pi]"), sol("{30°, 150°}", "set"), OK, None),
        ("trig_solve [0°, 360°]: {30°, 150°}", _trig("[0°, 360°]"), sol("{30°, 150°}", "set"), OK, None),
        ("trig_solve: LaTeX {30^\\circ, 150^\\circ}", _trig("[0, 2*pi]"), sol("\\{30^\\circ, 150^\\circ\\}", "set"), OK, None),
        ("trig_solve: {30°, 120°} wrong", _trig("[0, 2*pi]"), sol("{30°, 120°}", "set"), NO, None),
        ("trig_solve: pi*x/180 is a count of degrees, {30°, 150°}", ir("trig_solve", {"var": "x", "interval": "[0, 360]"},
                                                                       ["sin(pi*x/180) = 1/2"], shape="set"),
         sol("{30°, 150°}", "set"), UNK, None),
        ("evaluate sin(75°): LaTeX product formula", ir("evaluate", {"expr": "sin(75°)"}),
         sol("\\sin(45^\\circ)\\cos(30^\\circ) + \\cos(45^\\circ)\\sin(30^\\circ)"), OK, None),
        ("step \\sin(30^\\circ) = \\frac{1}{2} (LaTeX degree; the IR's own °)", ir("evaluate", {"expr": "sin(30°)"}),
         sol("1/2", steps=[("compute", "\\sin(30^\\circ) = \\frac{1}{2}")]), OK, VER),
        # the steps: a unit mark read both ways (the step layer's sibling)
        ("triangle steps: 6x = 180, x = 30°", tri, sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 30°")]), OK, NEITHER),
        ("triangle steps: x = 40° (wrong)", tri, sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 40°")]), NO, REF),
        ("triangle steps: compute 180/6 = 30°", tri, sol("30", steps=[("compute", "180/6 = 30°")]), OK, NEITHER),
        ("increase steps: compute (60 - 50)/50*100 = %20", inc, sol("20", steps=[("compute", "(60 - 50)/50*100 = %20")]),
         OK, NEITHER),
        ("increase steps: compute (60 - 50)/50*100 = %25 (wrong)", inc,
         sol("20", steps=[("compute", "(60 - 50)/50*100 = %25")]), NO, REF),
        ("trig step: sin(75°) = sin(45°)cos(30°) + cos(45°)sin(30°) (both readings)", ir("evaluate", {"expr": "sin(5*pi/12)"}),
         sol("(sqrt(6) + sqrt(2))/4", steps=[("compute", "sin(75°) = sin(45°)*cos(30°) + cos(45°)*sin(30°)")]), OK, VER),
    ]
    return out


def _geo_angle(payload, option):
    q = ir("synthetic_geometry", {"points": ["A", "B", "C"], "constraints": ["dist(A,B)**2 = dist(A,C)**2",
                                                                               "angle(B,A,C) = 40"],
                                  "target": "angle(A,B,C)"}, vars_=[])
    if option is not None:
        q["options"] = {"A": "40°", "B": "50°", "C": "60°", "D": "70°", "E": "80°"}
    return q, sol(payload, option=option)


def _trig(interval):
    return ir("trig_solve", {"var": "x", "interval": interval}, ["sin(x) = 1/2"], shape="set")


# C: G1RK-1 --------------------------------------------------------------------------------------------------------
QI = ineq("x**2 - 5*x + 6 < 0")
QE = ir("solve_equation", {"equation": "x**2 - 5*x + 6 = 0", "var": "x"}, shape="set")
OI = {"A": "x ∈ (1, 2)", "B": "x ∈ (2, 3)", "C": "x ∈ (3, 4)", "D": "x ∈ [2, 3]", "E": "x ∈ ℝ"}
OE = {"A": "x ∈ {1, 2}", "B": "x ∈ {2, 3}", "C": "x ∈ {3, 4}", "D": "x ∈ {-2, -3}", "E": "x ∈ ∅"}
LIN = ir("evaluate", {"expr": "x"}, ["x + y = 10", "x - y = 2"], [X, {"name": "y", "domain": "real"}])


def _five(c):
    return {"A": "4", "B": "5", "C": c, "D": "7", "E": "8"}


def cases_c():
    out = [
        ("F1 option 'x ∈ (2, 3)', payload the same text", _mc(QI, OI), sol("x ∈ (2, 3)", "interval", option="B"), OK, None),
        ("F1 option 'x ∈ (2, 3)', payload Interval", _mc(QI, OI), sol(A23, "interval", option="B"), OK, None),
        ("N205 option 'x ∈ {2, 3}', payload the same", _mc(QE, OE), sol("x ∈ {2, 3}", "set", option="B"), OK, None),
        ("N206 option 'x ∈ {2, 3}', payload {2, 3}", _mc(QE, OE), sol("{2, 3}", "set", option="B"), OK, None),
        ("N207 letter only 'x ∈ (2, 3)'", _mc(QI, OI), sol(None, "interval", option="B"), OK, None),
        ("KE2 option '2, 3'", _mc(QE, {"A": "{1, 2}", "B": "2, 3", "C": "{3, 4}", "D": "{-2, -3}", "E": "∅"}),
         sol("{2, 3}", "set", option="B"), OK, None),
        ("option '$x \\in (2, 3)$' (LaTeX)", _mc(QI, dict(OI, B="$x \\in (2, 3)$")), sol(A23, "interval", option="B"), OK, None),
        ("option '2 < x < 3' (as before)", _mc(QI, dict(OI, B="2 < x < 3")), sol(A23, "interval", option="B"), OK, None),
        ("K01 option '6 cm'", _mc(LIN, _five("6 cm")), sol("6", option="C"), OK, None),
        ("K03 option '6 TL'", _mc(LIN, _five("6 TL")), sol("6", option="C"), OK, None),
        ("K12 option '6 tane'", _mc(LIN, _five("6 tane")), sol("6", option="C"), OK, None),
        ("K19 option '6 cm²'", _mc(LIN, _five("6 cm²")), sol("6", option="C"), OK, None),
        ("K05 option '$6$' (as before)", _mc(LIN, _five("$6$")), sol("6", option="C"), OK, None),
        ("KP4 option 'π/6 rad'", _mc(ir("evaluate", {"expr": "asin(1/2)"}), {"A": "π/6 rad", "B": "π/4", "C": "π/3",
                                                                              "D": "π/2", "E": "π"}),
         sol("pi/6", option="A"), OK, None),
        ("\\log_2 5 option (as before)", _mc(ir("evaluate", {"expr": "x"}, ["2**x = 5"]),
                                             {"A": "0", "B": "\\log_2 5", "C": "100", "D": "-100", "E": "1000"}),
         sol("log(5)/log(2)", option="B"), OK, None),
        # the wrong letter in a notation now read: refuted (the veto)
        ("option 'x ∈ (1, 2)' chosen for (2, 3)", _mc(QI, OI), sol(A23, "interval", option="A"), NO, None),
        ("letter only 'x ∈ (1, 2)'", _mc(QI, OI), sol(None, "interval", option="A"), NO, None),
        ("letter only 'x ∈ [2, 3]'", _mc(QI, OI), sol(None, "interval", option="D"), NO, None),
        ("option 'x ∈ {1, 2}' chosen for {2, 3}", _mc(QE, OE), sol("{2, 3}", "set", option="A"), NO, None),
        ("option '7 cm' chosen for 6", _mc(LIN, {"A": "4 cm", "B": "5 cm", "C": "6 cm", "D": "7 cm", "E": "8 cm"}),
         sol("6", option="D"), NO, None),
        ("letter only '7 cm'", _mc(LIN, {"A": "4 cm", "B": "5 cm", "C": "6 cm", "D": "7 cm", "E": "8 cm"}),
         sol(None, option="D"), NO, None),
        ("letter only '6 cm'", _mc(LIN, {"A": "4 cm", "B": "5 cm", "C": "6 cm", "D": "7 cm", "E": "8 cm"}),
         sol(None, option="C"), OK, None),
        # still not read by the claim's reader either: the block stays (decision G1RK-1)
        ("option 'log_2 5' (read by nobody)", _mc(ir("evaluate", {"expr": "x"}, ["2**x = 5"]),
                                                  {"A": "0", "B": "log_2 5", "C": "100", "D": "-100", "E": "1000"}),
         sol("log(5)/log(2)", option="B"), UNK, None),
        ("option 'ln 2' (read by nobody)", _mc(ir("evaluate", {"expr": "x"}, ["exp(x) = 2"]),
                                               {"A": "0", "B": "ln 2", "C": "100", "D": "-100", "E": "1000"}),
         sol("log(2)", option="B"), UNK, None),
        ("option '2 ve 3' (read by nobody)", _mc(QE, {"A": "{1, 2}", "B": "2 ve 3", "C": "{3, 4}", "D": "{-2, -3}", "E": "∅"}),
         sol("{2, 3}", "set", option="B"), UNK, None),
        ("option '5 değil' (negated)", _mc(LIN, _five("6 değil")), sol("6", option="C"), UNK, None),
        ("readers agree on every claim notation", _claim_notations_are_option_notations, None, OK, None),
    ]
    return out


NOTATIONS = [  # (IR, claim kind, a text the claim's reader takes)
    (QI, "interval", "x ∈ (2, 3)"), (QI, "interval", "(2, 3)"), (QI, "interval", "2 < x < 3"), (QI, "interval", "$x \\in (2, 3)$"),
    (QI, "interval", "x \\in (2, 3)"), (QI, "interval", "Interval.open(2, 3)"), (QI, "interval", "\\boxed{(2, 3)}"),
    (QE, "set", "{2, 3}"), (QE, "set", "x ∈ {2, 3}"), (QE, "set", "2, 3"), (QE, "set", "x = 2 or x = 3"),
    (QE, "set", "$x \\in \\{2, 3\\}$"), (QE, "set", "{3, 2}"),
    (LIN, "value", "6"), (LIN, "value", "6 cm"), (LIN, "value", "$6$"), (LIN, "value", "\\frac{12}{2}"), (LIN, "value", "6.0"),
    (LIN, "value", "+6"), (LIN, "value", "\\boxed{6}"), (LIN, "value", "6 tane"),
    (ir("evaluate", {"expr": "sqrt(12)"}), "value", "2√3"), (ir("evaluate", {"expr": "sqrt(12)"}), "value", "2\\sqrt{3}"),
    (ir("evaluate", {"expr": "asin(1/2)"}), "value", "π/6"), (ir("evaluate", {"expr": "asin(1/2)"}), "value", "π/6 rad"),
    (ir("evaluate", {"expr": "log(2)"}), "value", "ln(2)"), (ir("evaluate", {"expr": "log(2)"}), "value", "\\ln 2"),
    (ir("evaluate", {"expr": "exp(-1)"}), "value", "1/e"), (ir("evaluate", {"expr": "exp(-1)"}), "value", "e^{-1}"),
]


def _claim_notations_are_option_notations():
    """Every notation the claim's reader takes is taken as an option too, and to the same value."""
    import copy
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.solution import Solution
    from mathverify import verifier as V
    bad = []
    for q, kind, text in NOTATIONS:
        q2 = dict(copy.deepcopy(q), options={"A": "0", "B": text})
        pir = ProblemIR.from_dict(q2)
        ctx = make_ctx(pir)
        s = Solution.from_dict(sol(text, kind))
        V._normalize_set_notation(pir, s, ctx)
        V._sanitize_payload(s, ctx)
        try:
            cv = ctx.claimed(s)
        except Exception:  # noqa: BLE001
            continue                                   # not a claim notation: nothing asked
        so = Solution.from_dict(sol("0", kind, option="B"))
        try:
            reader = getattr(V, "_option_claim_value", None)          # the old code: the option's own reader
            ov = reader(pir, so, ctx) if reader is not None else ctx.option_value("B")
        except Exception as e:  # noqa: BLE001
            bad.append(f"{text!r}: option not read ({type(e).__name__})")
            continue
        import sympy as sp
        a = cv if isinstance(cv, sp.Set) else sp.FiniteSet(cv)
        b = ov if isinstance(ov, sp.Set) else sp.FiniteSet(ov)
        if sp.simplify(a.symmetric_difference(b)) != sp.S.EmptySet and a != b:
            bad.append(f"{text!r}: claim {cv} option {ov}")
    if bad:
        print("   ", bad)
    return "CORRECT" if not bad else "INCORRECT"


# D: G1RK-8 --------------------------------------------------------------------------------------------------------
def cases_d():
    ci = ir("count_integers", {"var": "x"}, ["x**x*(2 + sin(x)) > 0", "x >= -3", "x <= 3"], [XI], "count")
    return [(f"x**x(2 + sin x) > 0 on -3..3: {c}", ci, sol(c, "count"), want, None)
            for c, want in (("3", NOTOK), ("4", UNK), ("5", UNK), ("6", NOTOK))]


# E: G1RK-5 --------------------------------------------------------------------------------------------------------
def _fq(f, e):
    return ir("evaluate", {"expr": e}, functions=[{"name": "f", "expr": f, "args": ["x"], "params": []}])


def cases_e():
    out = []
    for f, e, right, wrong in (("Piecewise((x + 1, x < 2), (x - 1, x >= 2))", "f(f(1))", "1", "3"),
                               ("Piecewise((x**2, x < 0), (x + 3, x >= 0))", "f(f(-1))", "4", "1"),
                               ("Piecewise((3*x + 1, x <= 2), (x**2 - 1, x > 2))", "f(f(1))", "15", "13"),
                               ("Piecewise((x**2, x < 0), (x + 3, x >= 0))", "f(f(2))", "8", "9"),
                               ("Piecewise((1/x, x < 0), (x + 3, x >= 0))", "f(f(-1))", "-1", "2"),
                               ("Piecewise((sqrt(x), x >= 0), (x**2, x < 0))", "f(f(-2))", "2", "4"),
                               ("Piecewise((x + 1, x < sqrt(2)), (x - 1, x >= sqrt(2)))", "f(f(sqrt(2)))", "sqrt(2)",
                                "sqrt(2) - 1")):
        out += [(f"{e} = {right}, f = {f}", _fq(f, e), sol(right), OK, None),
                (f"{e} = {wrong} (wrong), f = {f}", _fq(f, e), sol(wrong), NO, None)]
    out += [("f(f(4)) undefined (1/(2 - 2))", _fq("Piecewise((1/(x - 2), x < 3), (x - 2, x >= 3))", "f(f(4))"), sol("0"),
             UNK, None),
            ("f(f(0)) undefined (0/0 inside)", _fq("Piecewise((x/x, x < 1), (2, x >= 1))", "f(f(0))"), sol("2"), UNK, None)]
    return out


# K: controls ------------------------------------------------------------------------------------------------------
def cases_k():
    return [
        ("x**2 = 4: {-2, 2}", ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, shape="set"), sol("{-2, 2}", "set"),
         OK, None),
        ("x**2 = 4: {2} wrong", ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, shape="set"), sol("{2}", "set"),
         NO, None),
        ("x**2 < 4: (-2, 2)", ineq("x**2 < 4", "interval"), sol("(-2, 2)", "interval"), OK, None),
        ("evaluate 2**10 = 1024, letter", _mc(ir("evaluate", {"expr": "2**10"}), {"A": "512", "B": "1024", "C": "2048",
                                                                                 "D": "4096", "E": "256"}),
         sol("1024", option="B"), OK, None),
        ("evaluate 2**10, wrong letter", _mc(ir("evaluate", {"expr": "2**10"}), {"A": "512", "B": "1024", "C": "2048",
                                                                                "D": "4096", "E": "256"}),
         sol("1024", option="A"), NO, None),
        ("x > -2 option names (-2, oo)", _mc(ineq("x + 2 > 0"), {"A": "x > -2", "B": "x < -2", "C": "x > 2", "D": "x < 2",
                                                                 "E": "x > 0"}),
         sol("Interval.open(-2, oo)", "interval", option="A"), OK, None),
        ("x > -2 option, wrong letter", _mc(ineq("x + 2 > 0"), {"A": "x > -2", "B": "x < -2", "C": "x > 2", "D": "x < 2",
                                                                "E": "x > 0"}),
         sol("Interval.open(-2, oo)", "interval", option="B"), NO, None),
        ("decimal comma option '1,5' not guessed", _mc(ir("evaluate", {"expr": "x"}, ["2*x = 3"]),
                                                       {"A": "1", "B": "1,5", "C": "2", "D": "3", "E": "4"}),
         sol("3/2", option="B"), UNK, None),
        ("no solution option", _mc(ir("solve_equation", {"var": "x", "equation": "x**2 = -1"}, shape="set"),
                                   {"A": "{1}", "B": "Çözüm yok", "C": "{-1}", "D": "{0}", "E": "{1, -1}"}),
         sol("EmptySet", "set", option="B"), OK, None),
        ("percent in the IR itself: %20 of 50 = 10", ir("evaluate", {"expr": "%20*50"}), sol("10"), OK, None),
        ("degree in the IR itself: sin(30°) = 1/2", ir("evaluate", {"expr": "sin(30°)"}), sol("1/2"), OK, None),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "K": cases_k}


def main(out_path=None, groups="ABCDEK"):
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
                if callable(q):
                    verdict = q()
                else:
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
    grp = args[1] if len(args) > 1 else "ABCDEK"
    sys.exit(1 if main(out, grp) else 0)
