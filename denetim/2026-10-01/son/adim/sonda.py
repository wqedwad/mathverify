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
             '2, 3', '6 cm', 'π/6 rad' read as the claim reads them, and that reader reads log_b, a subscript base and ln
             with a number (log_2 5, log₂5, ln 2); an option still unread blocks CORRECT; a wrong letter in a newly read
             notation is refuted (log_5 2, ln 3, [2, 3]); wordproblem's check of the options reads them the same way
  D  G1RK-8  a count over x**x decided at each integer, 0**0 read both ways: wrong under both (2, 3, 6, 7) INCORRECT,
             the two readings (4, 5) UNKNOWN
  E  G1RK-5  (recorded; a cheap exact path) f(f(1)) of a piecewise f: the inner Piecewise taken to its certified branch
  F  G2YO-5/7 (added 16 Oct evening) options with a declared tolerance: several in the window name none (UNKNOWN); the
             chosen one outside it is refuted; inside it alone, a claim certified in the window too is the same answer
  K  controls whose verdict must not change
  -- second round (21 Oct 2026): the independent audit of the branch (14 findings, SA-*) --
  L  SA-YO-2/3/4, SA-RK-1/2/7  the boundary rule narrowed: a step read on the boundary joins no premise pool (the
             wrong step after it refuted, the right one verified); only an equation or a choice of equations is a
             critical point step (the closed wrong region refuted); no boundary in a system (a > 0 next to
             x**2 - a*x - 6 = 0); none for an inequality with no point inside ((x - 3)**2 < 0, (2, 3) of an integer);
             the root of a denominator is a critical point, read where the expression is undefined; a wrong list of
             roots with a value outside the solution is no choice
  M  SA-RK-4/5  a unit the IR's units names ('derece', '°', '%', 'yüzde') is read as the plain number; a degree mark on
             a radian measure (the variable sin and cos of the IR's own relations read, an inverse trigonometric
             value) is that unit; an option word the IR's units does not name leaves it unread (SA-YO-1, SA-RK-3)
  N  SA-RK-6  with a declared tolerance, an option that names no value ('Hiçbiri', 'Belirlenemez') is outside the
             window; '7 ile 8 arasında' stays undecided; the window is read once from the certificate's value
  -- third round (22 Oct 2026): the second independent audit (son-adim-t2), decisions EK 7/EK 8 --
  P  EK 8     a claim or an option is read as the plain number only when it is one marked number AND the IR's value is
             proved to count in that unit (×100, ×180/pi, angle(), a degree variable); units proves nothing; a step
             reads its marks both ways and is refuted only under both (T2-RK-1/2, T2-OT-1, SA2-YO-4)
  Q  SA2-YO-1 a step whose two readings decide apart joins no premise pool: the wrong step after it is refuted
  R  SA2-YO-2/3, T2-RK-3/4/6  the tolerance window (a decimal comma, a range, a set undecided; 'Hiçbiri' written any
             way outside), wordproblem's unread options must carry the claim, 'x = 6' names one value, restatements
             choose together

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
        # a percentage written as ×100 counts in percent, proved: one marked number is the plain number (third round,
        # EK 8); an angle count from x + 2x + 3x = 180 or (n - 2)*180/n is not proved to be degrees: both readings
        mark = OK if lab in ("increase", "discount", "profit") else UNK
        out += [
            (f"{lab}: payload {rv}, right letter {opts[right]}", _mc(q, opts), sol(rv, option=right), mark, None),
            (f"{lab}: payload {opts[right]}, right letter", _mc(q, opts), sol(opts[right], option=right), mark, None),
            (f"{lab}: right letter only", _mc(q, opts), sol(None, option=right), mark, None),
            (f"{lab}: payload {opts[right]}, no options", q, sol(opts[right]), mark, None),
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
        # an inverse trigonometric value is a radian measure: 30° is its unit (second round, SA-RK-5)
        ("asin(1/2): payload pi/6, letter 30°", _mc(ir("evaluate", {"expr": "asin(1/2)"}), DEG), sol("pi/6", option="B"),
         OK, None),
        ("asin(1/2): payload pi/6, letter 40° (wrong)", _mc(ir("evaluate", {"expr": "asin(1/2)"}), DEG),
         sol("pi/6", option="C"), NO, None),
        # spellings of the marks
        ("triangle: payload 30 derece", tri, sol("30 derece"), UNK, None),
        ("triangle: payload 30^\\circ (LaTeX)", tri, sol("30^\\circ"), UNK, None),
        ("triangle: payload 30^{\\circ} (LaTeX)", tri, sol("30^{\\circ}"), UNK, None),
        ("triangle: payload 40^\\circ (LaTeX, wrong)", tri, sol("40^\\circ"), NO, None),
        ("increase: payload 20% (mark after)", _mc(inc, PCT), sol("20%", option="B"), OK, None),
        ("increase: payload 20\\% (LaTeX)", inc, sol("20\\%"), OK, None),
        ("increase: option '% 20', payload 20", _mc(inc, dict(PCT, B="% 20")), sol("20", option="B"), OK, None),
        ("increase: payload 2*%10 (a mark inside an expression: both readings)", inc, sol("2*%10"), UNK, None),
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
LINU = dict(LIN, units="cm")
CM = {"A": "4 cm", "B": "5 cm", "C": "6 cm", "D": "7 cm", "E": "8 cm"}


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
        # a unit word of an option is dropped only where the IR's units names it (second round, SA-YO-1, SA-RK-3)
        ("K01 option '6 cm' (units 'cm')", _mc(dict(LIN, units="cm"), _five("6 cm")), sol("6", option="C"), OK, None),
        ("K01 option '6 cm' (no units: not read)", _mc(LIN, _five("6 cm")), sol("6", option="C"), UNK, None),
        ("K03 option '6 TL' (units 'TL')", _mc(dict(LIN, units="TL"), _five("6 TL")), sol("6", option="C"), OK, None),
        ("K03 option '6 TL' (no units: not read)", _mc(LIN, _five("6 TL")), sol("6", option="C"), UNK, None),
        ("K12 option '6 tane'", _mc(LIN, _five("6 tane")), sol("6", option="C"), OK, None),
        ("K19 option '6 cm²' (units 'cm²')", _mc(dict(LIN, units="cm²"), _five("6 cm²")), sol("6", option="C"), OK, None),
        ("K19 option '6 cm²' (no units: not read)", _mc(LIN, _five("6 cm²")), sol("6", option="C"), UNK, None),
        ("K05 option '$6$' (as before)", _mc(LIN, _five("$6$")), sol("6", option="C"), OK, None),
        ("KP4 option 'π/6 rad' (units 'rad')", _mc(ir("evaluate", {"expr": "asin(1/2)"}, units="rad"),
                                                   {"A": "π/6 rad", "B": "π/4", "C": "π/3", "D": "π/2", "E": "π"}),
         sol("pi/6", option="A"), OK, None),
        ("KP4 option 'π/6 rad' (no units: not read)", _mc(ir("evaluate", {"expr": "asin(1/2)"}),
                                                          {"A": "π/6 rad", "B": "π/4", "C": "π/3", "D": "π/2", "E": "π"}),
         sol("pi/6", option="A"), UNK, None),
        ("\\log_2 5 option (as before)", _mc(ir("evaluate", {"expr": "x"}, ["2**x = 5"]),
                                             {"A": "0", "B": "\\log_2 5", "C": "100", "D": "-100", "E": "1000"}),
         sol("log(5)/log(2)", option="B"), OK, None),
        # the wrong letter in a notation now read: refuted (the veto)
        ("option 'x ∈ (1, 2)' chosen for (2, 3)", _mc(QI, OI), sol(A23, "interval", option="A"), NO, None),
        ("letter only 'x ∈ (1, 2)'", _mc(QI, OI), sol(None, "interval", option="A"), NO, None),
        ("letter only 'x ∈ [2, 3]'", _mc(QI, OI), sol(None, "interval", option="D"), NO, None),
        ("option 'x ∈ {1, 2}' chosen for {2, 3}", _mc(QE, OE), sol("{2, 3}", "set", option="A"), NO, None),
        ("option '7 cm' chosen for 6 (units 'cm')", _mc(LINU, CM), sol("6", option="D"), NO, None),
        ("letter only '7 cm' (units 'cm')", _mc(LINU, CM), sol(None, option="D"), NO, None),
        ("letter only '6 cm' (units 'cm')", _mc(LINU, CM), sol(None, option="C"), OK, None),
        ("option '7 cm' chosen for 6 (no units)", _mc(LIN, CM), sol("6", option="D"), NOTOK, None),
        ("letter only '6 cm' (no units: not read)", _mc(LIN, CM), sol(None, option="C"), UNK, None),
        # logarithms with a base and a number: read by the one reader of claims and options (the verifier's corrected
        # expectation of G1RK-1); the wrong letter in them refuted (the base reading: CORRECT)
    ]
    for opt, given, pay in (("log_2 5", "2**x = 5", "log(5)/log(2)"), ("log₂5", "2**x = 5", "log(5)/log(2)"),
                            ("log₂ 5", "2**x = 5", "log(5)/log(2)"), ("log_2(5)", "2**x = 5", "log(5)/log(2)"),
                            ("log_{2} 5", "2**x = 5", "log(5)/log(2)"), ("log2(5)", "2**x = 5", "log(5)/log(2)"),
                            ("ln 2", "exp(x) = 2", "log(2)"), ("ln2", "exp(x) = 2", "log(2)"),
                            ("ln5/ln2", "2**x = 5", "log(5)/log(2)"), ("log₂32", "x = 5", "5")):
        q = _mc(ir("evaluate", {"expr": "x"}, [given]), {"A": "0", "B": opt, "C": "100", "D": "-100", "E": "1000"})
        out += [(f"option '{opt}', payload", q, sol(pay, option="B"), OK, None),
                (f"option '{opt}', letter only", q, sol(None, option="B"), OK, None)]
    LOG = {"A": "log_5 2", "B": "log_2 5", "C": "log₂ 3", "D": "ln 5", "E": "5/2"}
    LN = {"A": "ln 3", "B": "ln 2", "C": "ln 4", "D": "2", "E": "1/2"}
    for opts, given, pay in ((LOG, "2**x = 5", "log(5)/log(2)"), (LN, "exp(x) = 2", "log(2)")):
        q = _mc(ir("evaluate", {"expr": "x"}, [given]), opts)
        for letter in ("A", "C"):
            out += [(f"wrong letter '{opts[letter]}' beside {pay}", q, sol(pay, option=letter), NO, None),
                    (f"wrong letter '{opts[letter]}' alone", q, sol(None, option=letter), NO, None)]
    q23 = _mc(QI, {"A": "[2, 3]", "B": "x ∈ (2, 3)", "C": "(1, 2)", "D": "(3, 4)", "E": "ℝ"})
    out += [("wrong letter '[2, 3]' beside (2, 3)", q23, sol(A23, "interval", option="A"), NO, None),
            ("wrong letter '[2, 3]' alone", q23, sol(None, "interval", option="A"), NO, None),
            ("option 'log 9' (no base: ln or log10?)", _mc(ir("evaluate", {"expr": "x"}, ["10**x = 9"]),
                                                           {"A": "0", "B": "log 9", "C": "1"}),
             sol("log(9)/log(10)", option="B"), UNK, None)]
    out += [
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
    (LIN, "value", "6"), (LINU, "value", "6 cm"), (LIN, "value", "$6$"), (LIN, "value", "\\frac{12}{2}"), (LIN, "value", "6.0"),
    (LIN, "value", "+6"), (LIN, "value", "\\boxed{6}"), (LIN, "value", "6 tane"),
    (ir("evaluate", {"expr": "sqrt(12)"}), "value", "2√3"), (ir("evaluate", {"expr": "sqrt(12)"}), "value", "2\\sqrt{3}"),
    (ir("evaluate", {"expr": "asin(1/2)"}), "value", "π/6"), (ir("evaluate", {"expr": "asin(1/2)"}, units="rad"), "value", "π/6 rad"),
    (ir("evaluate", {"expr": "log(2)"}), "value", "ln(2)"), (ir("evaluate", {"expr": "log(2)"}), "value", "\\ln 2"),
    (ir("evaluate", {"expr": "exp(-1)"}), "value", "1/e"), (ir("evaluate", {"expr": "exp(-1)"}), "value", "e^{-1}"),
]


def _claim_notations_are_option_notations():
    """Every notation the claim's reader takes is taken as an option too, and to the same value. A unit word only
    where the IR's units names it: an option's word may carry its meaning ('6 m' against cm; SA-YO-1)."""
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
    def ci(g, lo, hi):
        return ir("count_integers", {"var": "x"}, [g, f"x >= {lo}", f"x <= {hi}"], [XI], "count")
    g = "x**x*(2 + sin(x)) > 0"
    out = [(f"x**x(2 + sin x) > 0 on -3..3: {c}", ci(g, -3, 3), sol(c, "count"), want, None)
           for c, want in (("2", NO), ("3", NO), ("4", UNK), ("5", UNK), ("6", NO), ("7", NO))]
    for gg, lo, hi, right, wrongs in ((g, 1, 3, "3", ("2", "4")), (g, -3, -1, "1", ("0", "2")),
                                      ("(x - 1)**x > 0", 0, 3, "3", ("2", "4")), ("x**x > 1", -3, 3, "2", ("1", "3")),
                                      ("x**x < 0", -3, 3, "2", ("1", "3")), (g, -100, 100, None, ("100", "150", "151"))):
        if right:
            out.append((f"{gg} on {lo}..{hi}: {right}", ci(gg, lo, hi), sol(right, "count"), OK, None))
        out += [(f"{gg} on {lo}..{hi}: {w} (wrong)", ci(gg, lo, hi), sol(w, "count"),
                 UNK if (lo, hi, w) in ((-100, 100, "150"), (-100, 100, "151")) else NO, None) for w in wrongs]
    out += [(f"x**(x/2) > 0 on -3..3: {c} (a power undecided at a point)", ci("x**(x/2) > 0", -3, 3), sol(c, "count"),
             UNK, None) for c in ("2", "3", "4")]
    return out


# F: G2YO-5, G2YO-7 ------------------------------------------------------------------------------------------------
def cases_f():
    def tol(options, integral=False):
        if not integral:
            return ir("evaluate", {"expr": "sqrt(50)", "rel_tol": "0.01"}, options=options)
        return ir("definite_integral", {"integrand": "exp(x**2)", "var": "x", "a": "0", "b": "1", "rel_tol": "0.01"},
                  options=options)
    o50 = {"A": "7.01", "B": "7.07", "C": "7.1", "D": "7.2", "E": "7.5"}
    o50u = {"A": "6.5", "B": "7.07", "C": "7.5", "D": "8", "E": "9"}
    oex = {"A": "1.25", "B": "1.46", "C": "1.47", "D": "1.72", "E": "2"}
    oexu = {"A": "1.25", "B": "1.46", "C": "1.6", "D": "1.72", "E": "2"}
    x2 = ir("definite_integral", {"integrand": "x**2", "var": "x", "a": "0", "b": "1", "rel_tol": "0.05"},
            options={"A": "1/3", "B": "0.34", "C": "1/2", "D": "1", "E": "2/3"})
    return [
        ("YO5-a √50: A 7.01 (in the window, wrong)", tol(o50), sol("7.01", option="A"), NOTOK, None),
        ("YO5-b √50: B 7.07 (three in the window)", tol(o50), sol("7.07", option="B"), NOTOK, None),
        ("YO5-c √50: C 7.1 (in the window, wrong)", tol(o50), sol("7.1", option="C"), NOTOK, None),
        ("YO5-d √50: letter A only", tol(o50), sol(None, option="A"), NOTOK, None),
        ("YO5-e ∫e^{x²}: C 1.47", tol(oex, True), sol("1.47", option="C"), NOTOK, None),
        ("YO5-f ∫e^{x²}: letter C only", tol(oex, True), sol(None, option="C"), NOTOK, None),
        ("YO5-g ∫x²: B 0.34 (A = 1/3 exact)", x2, sol("0.34", option="B"), NOTOK, None),
        ("YO7-a √50: 7.0711 letter B (three in the window)", tol(o50), sol("7.0711", option="B"), NOTNO, None),
        ("YO7-b ∫e^{x²}: 1.4627 letter B (two in the window)", tol(oex, True), sol("1.4627", option="B"), NOTNO, None),
        ("√50 one in the window: 7.0711 letter B", tol(o50u), sol("7.0711", option="B"), OK, None),
        ("√50 one in the window: 7.07 letter B", tol(o50u), sol("7.07", option="B"), OK, None),
        ("√50 one in the window: letter B only", tol(o50u), sol(None, option="B"), OK, None),
        ("√50 one in the window: 7.0711 letter C (wrong)", tol(o50u), sol("7.0711", option="C"), NO, None),
        ("√50 one in the window: letter C only (wrong)", tol(o50u), sol(None, option="C"), NO, None),
        ("∫e^{x²} one in the window: 1.4627 letter B", tol(oexu, True), sol("1.4627", option="B"), OK, None),
        ("∫e^{x²} one in the window: letter B only", tol(oexu, True), sol(None, option="B"), OK, None),
        ("∫e^{x²} one in the window: 1.4627 letter C (wrong)", tol(oexu, True), sol("1.4627", option="C"), NO, None),
        ("√50 no options: 7.07", ir("evaluate", {"expr": "sqrt(50)", "rel_tol": "0.01"}), sol("7.07"), OK, None),
    ]


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


# L: second round, the boundary rule narrowed (SA-YO-2/3/4, SA-RK-1/2/7) ---------------------------------------------
GE = "Union(Interval(-oo, 2), Interval(3, oo))"
RGE = "Union(Interval.open(-oo, -2), Interval(1, oo))"


def cases_l():
    lt, le, ge = ineq("x**2 - 5*x + 6 < 0"), ineq("x**2 - 5*x + 6 <= 0"), ineq("x**2 - 5*x + 6 >= 0")
    lt2, rat, rge, rle = (ineq("x**2 - 4*x - 5 < 0"), ineq("(x - 1)/(x + 2) < 0"), ineq("(x - 1)/(x + 2) >= 0"),
                          ineq("(x + 3)/(x - 1) <= 0"))
    a15 = "Interval.open(-1, 5)"
    par = ir("evaluate", {"expr": "a"}, ["a > 0", "x**2 - a*x - 6 = 0", "x = 3"], [X, {"name": "a", "domain": "real"}])
    sys_ = ir("evaluate", {"expr": "x - y"}, ["x > 0", "y > 0", "x + y = 5", "x*y = 6", "x > y"],
              [X, {"name": "y", "domain": "real"}])
    cnt = ir("count_integers", {"var": "x"}, ["x**2 - 5*x + 6 < 0"], [XI], "count")
    cnt4 = ir("count_integers", {"var": "x"}, ["x**2 - 5*x + 4 < 0"], [XI], "count")
    return [
        # SA-YO-2/SA-RK-2: a step read on the boundary joins no premise pool
        ("YO2 >= 0: roots, Or roots, then wrong 2 <= x <= 3", ge,
         sol(GE, "interval", [("eq", "x**2 - 5*x + 6 = 0"), ("eq", "Or(Eq(x, 2), Eq(x, 3))"), ("eq", "And(x >= 2, x <= 3)")]),
         NO, REF),
        ("YO2 <= 0: roots then x in {2, 5/2, 3} (a choice, never verified)", le,
         sol("Interval(2, 3)", "interval", [("eq", "x**2 - 5*x + 6 = 0"), ("eq", "Or(Eq(x, 2), Eq(x, 3), Eq(x, 5/2))")]),
         NOTNO, NEITHER),
        ("YO2 <= 0: roots then x != 11/5", le, sol("Interval(2, 3)", "interval", [("eq", "x**2 - 5*x + 6 = 0"),
                                                                                ("eq", "Ne(x, 11/5)")]), NO, REF),
        ("YO2 < 0: Or roots then x > 0", lt2, sol(a15, "interval", [("eq", "Or(Eq(x, -1), Eq(x, 5))"), ("eq", "x > 0")]),
         NO, REF),
        ("YO2 < 0: roots then -1 < x < 4", lt2, sol(a15, "interval", [("eq", "x**2 - 4*x - 5 = 0"),
                                                                   ("eq", "And(x > -1, x < 4)")]), NO, REF),
        ("YO2 rational: x - 1 = 0 then x < 0", rat, sol("Interval.open(-2, 1)", "interval", [("eq", "x - 1 = 0"),
                                                                                           ("eq", "x < 0")]), NO, REF),
        ("RK2 < 0: critical steps then x < 5/2", lt, sol(A23, "interval", CRIT + [("eq", "x < 5/2")]), NO, REF),
        ("RK2 < 0: roots then x > 5/2", lt, sol(A23, "interval", CRIT[:1] + [("eq", "x > 5/2")]), NO, REF),
        ("RK2 < 0: roots then Or(x < 3/2, x > 5/2)", lt, sol(A23, "interval", CRIT[:1] + [("eq", "Or(x < 3/2, x > 5/2)")]),
         NO, REF),
        ("RK2 rational >= 0: Or zeros then x >= 2", rge, sol(RGE, "interval", [("eq", "Or(Eq(x, 1), Eq(x, -2))"),
                                                                             ("eq", "x >= 2")]), NO, REF),
        ("RK2 rational >= 0: Or zeros then Or(x < -2, x > 5)", rge,
         sol(RGE, "interval", [("eq", "Or(Eq(x, 1), Eq(x, -2))"), ("eq", "Or(x < -2, x > 5)")]), NO, REF),
        ("RK2 count: roots then wrong Or(x = 2, x = 5)", cnt4,
         sol("2", "count", [("eq", "x**2 - 5*x + 4 = 0"), ("eq", "Or(Eq(x, 2), Eq(x, 5))")]), NO, REF),
        ("RK2 < 0: roots then the right 2 < x < 3 verified", lt, sol(A23, "interval", CRIT[:1] + [("eq", "And(x > 2, x < 3)")]),
         OK, VER),
        ("RK2 < 0: critical steps then 2 < x < 3 verified", lt, sol(A23, "interval", CRIT + [("eq", "2 < x < 3")]), OK, VER),
        # SA-YO-3: only an equation (or a choice of equations) is a critical point step
        ("YO3 < 0: wrong region Or(x <= 2, x >= 3)", lt, sol(A23, "interval", [("eq", "Or(x <= 2, x >= 3)")]), NO, REF),
        ("YO3 < 0: wrong region x**2 - 5x + 6 >= 0", lt, sol(A23, "interval", [("eq", "x**2 - 5*x + 6 >= 0")]), NO, REF),
        ("YO3 < 0 givens: wrong region (x - 2)(x - 3) >= 0", gineq("x**2 - 5*x + 6 < 0"),
         sol(A23, "interval", [("eq", "(x - 2)*(x - 3) >= 0")]), NO, REF),
        ("YO3 >= 0: wrong region 2 <= x <= 3", ge, sol(GE, "interval", [("eq", "And(x >= 2, x <= 3)")]), NO, REF),
        # SA-YO-4: no boundary in a system
        ("YO4 a > 0: 9 + 3a - 6 = 0 (sign error)", par, sol("1", steps=[("eq", "9 + 3*a - 6 = 0")]), NO, REF),
        ("YO4 a > 0: a = -1", par, sol("1", steps=[("eq", "a = -1")]), NO, REF),
        ("YO4 a > 0: a < 0", par, sol("1", steps=[("eq", "a < 0")]), NO, REF),
        ("YO4 system: y = -2", sys_, sol("1", steps=[("eq", "y = -2")]), NO, REF),
        ("YO4 system: x = -3", sys_, sol("1", steps=[("eq", "x = -3")]), NO, REF),
        ("YO4 a > 0: the right a = 1", par, sol("1", steps=[("eq", "a = 1")]), OK, None),
        # SA-RK-1: an inequality with no point inside has no boundary
        ("RK1 (x - 3)**2 < 0 = ∅: restated", ineq("x**2 - 6*x + 9 < 0"), sol("EmptySet", "set", [("eq", "(x - 3)**2 < 0")]),
         OK, NEITHER),
        ("RK1 -x**2 + 4x - 4 > 0 = ∅: -(x - 2)**2 > 0", ineq("-x**2 + 4*x - 4 > 0"),
         sol("EmptySet", "set", [("eq", "-(x - 2)**2 > 0")]), OK, NEITHER),
        ("RK1 x**2 + 1 < 0 = ∅: x**2 < -1", ineq("x**2 + 1 < 0"), sol("EmptySet", "set", [("eq", "x**2 < -1")]), OK, NEITHER),
        ("RK1 |x - 1| < 0 = ∅", ineq("Abs(x - 1) < 0"), sol("EmptySet", "set", [("eq", "Abs(x - 1) < 0")]), OK, NEITHER),
        ("RK1 count 0 integers in (2, 3): 2 < x < 3", cnt, sol("0", "count", [("eq", "And(x > 2, x < 3)")]), OK, NEITHER),
        ("RK1 count 0 integers: (x - 2)(x - 3) < 0", cnt, sol("0", "count", [("eq", "(x - 2)*(x - 3) < 0")]), OK, NEITHER),
        ("RK1 control (x - 3)**2 <= 0 = {3}", ineq("x**2 - 6*x + 9 <= 0"), sol("FiniteSet(3)", "set",
                                                                             [("eq", "(x - 3)**2 <= 0")]), OK, VER),
        # SA-RK-7 (the root of a denominator)
        ("RK7 rational >= 0: x + 2 = 0", rge, sol(RGE, "interval", [("eq", "x + 2 = 0")]), OK, NEITHER),
        ("RK7 rational >= 0: x = 1 then x = -2", rge, sol(RGE, "interval", [("eq", "x = 1"), ("eq", "x = -2")]), OK, NEITHER),
        ("RK7 rational >= 0: x - 1 = 0, x + 2 = 0", rge, sol(RGE, "interval", [("eq", "x - 1 = 0"), ("eq", "x + 2 = 0")]),
         OK, NEITHER),
        ("RK7 rational <= 0: x + 3 = 0, x - 1 = 0", rle, sol("Interval.Ropen(-3, 1)", "interval",
                                                             [("eq", "x + 3 = 0"), ("eq", "x - 1 = 0")]), OK, NEITHER),
        ("RK7 1/(x - 2) > 0: x - 2 = 0", ineq("1/(x - 2) > 0"), sol("Interval.open(2, oo)", "interval",
                                                                   [("eq", "x - 2 = 0")]), OK, NEITHER),
        ("RK7 rational >= 0: wrong point x = -1", rge, sol(RGE, "interval", [("eq", "x = -1")]), NO, REF),
        ("RK7 rational <= 0: wrong point x = 3", rle, sol("Interval.Ropen(-3, 1)", "interval", [("eq", "x = 3")]), NO, REF),
        ("RK7 x > 0 given: x = -2 is no boundary", ir("solve_inequality", {"inequality": "(x - 1)/(x + 2) >= 0", "var": "x"},
                                                      ["x > 0"], shape="set"),
         sol("Interval(1, oo)", "interval", [("eq", "x = -2")]), NO, REF),
        # a wrong list of roots with a value outside the solution is no choice (yanlis-onay c1 s4)
        ("Or list: roots then x = 1 or x = -5", lt2, sol(a15, "interval", [("eq", "x**2 - 4*x - 5 = 0"),
                                                                          ("eq", "Or(Eq(x, 1), Eq(x, -5))")]), NO, REF),
        ("Or list: x = 1 or x = -5 alone", lt2, sol(a15, "interval", [("eq", "Or(Eq(x, 1), Eq(x, -5))")]), NO, REF),
        ("Or list: <= 0 roots then x = 2 or x = 4", le, sol("Interval(2, 3)", "interval",
                                                           CRIT[:1] + [("eq", "Or(Eq(x, 2), Eq(x, 4))")]), NO, REF),
    ]


# M: second round, units (SA-RK-4, SA-RK-5) --------------------------------------------------------------------------
def cases_m():
    tri = ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = 180"])
    tri_u, tri_d = dict(tri, units="derece"), dict(tri, units="°")
    inc = ir("evaluate", {"expr": "(p2 - p1)/p1*100"}, ["p1 = 50", "p2 = 60"], P12)
    inc_u, inc_y = dict(inc, units="%"), dict(inc, units="yüzde")
    acute = ir("evaluate", {"expr": "x"}, ["sin(x) = 1/2", "0 < x", "x < pi/2"])
    return [
        # third round (EK 8): units is free text and proves nothing; x + 2x + 3x = 180 is no proved count of degrees
        ("RK4 units derece: 30° (EK 8: both readings)", tri_u, sol("30°"), UNK, None),
        ("RK4 units derece: 30^\\circ (EK 8)", tri_u, sol("30^\\circ"), UNK, None),
        ("RK4 units derece: \\boxed{30^\\circ} (EK 8)", tri_u, sol("\\boxed{30^\\circ}"), UNK, None),
        ("RK4 units °: 30° (EK 8)", tri_d, sol("30°"), UNK, None),
        ("RK4 units derece: letter B 30° (EK 8)", _mc(tri_u, DEG), sol(None, option="B"), UNK, None),
        ("RK4 units derece: 30 letter B 30° (EK 8)", _mc(tri_u, DEG), sol("30", option="B"), UNK, None),
        ("RK4 units %: %20", inc_u, sol("%20"), OK, None),
        ("RK4 units %: letter B %20", _mc(inc_u, PCT), sol(None, option="B"), OK, None),
        ("RK4 units yüzde: 20 letter B %20", _mc(inc_y, PCT), sol("20", option="B"), OK, None),
        ("RK4 units derece: step x = 30° (EK 8: both readings)", tri_u,
         sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 30°")]), OK, NEITHER),
        ("RK4 units derece: 40° (wrong)", tri_u, sol("40°"), NO, None),
        ("RK4 units derece: letter C 40° (wrong)", _mc(tri_u, DEG), sol(None, option="C"), NO, None),
        ("RK4 units %: %25 (wrong)", inc_u, sol("%25"), NO, None),
        ("RK4 units derece: step x = 40° (wrong)", tri_u, sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 40°")]), NO, REF),
        ("RK4 no units: 30^\\circ (both readings)", tri, sol("30^\\circ"), UNK, None),
        ("RK4 the IR's own mark with units: x = 30° given, 30°", dict(ir("evaluate", {"expr": "x"}, ["x = 30°"]),
                                                                    units="derece"), sol("30°"), OK, None),
        ("RK5 acute sin x = 1/2: 30°", acute, sol("30°"), OK, None),
        ("RK5 acute sin x = 1/2: pi/6", acute, sol("pi/6"), OK, None),
        ("RK5 acute sin x = 1/2: 30 (wrong)", acute, sol("30"), NO, None),
        ("RK5 acute sin x = 1/2: 60° (wrong)", acute, sol("60°"), NO, None),
        ("RK5 acute with units derece: 30° (radians win)", dict(acute, units="derece"), sol("30°"), OK, None),
        ("RK5 cos x = 0 on (0, pi): {90°}", ir("solve_equation", {"equation": "cos(x) = 0", "var": "x"},
                                               vars_=[dict(X, constraints=["0 < x", "x < pi"])], shape="set"),
         sol("{90°}", "set"), OK, None),
        # a count of degrees, proved (pi*x/180 inside sin): one marked number is the plain number (third round, EK 8)
        ("RK5 degrees as pi*x/180: 30° is 30 (EK 8)", ir("evaluate", {"expr": "x"}, ["sin(pi*x/180) = 1/2", "0 < x",
                                                                                     "x < 90"]),
         sol("30°"), OK, None),
        ("RK3 option '1/2 saat' for 30 (minutes)", _mc(ir("evaluate", {"expr": "t"}, ["t = 60/2"],
                                                          [{"name": "t", "domain": "real"}]),
                                                       {"A": "20 dk", "B": "1/2 saat", "C": "45 dk"}),
         sol("30", option="B"), NOTNO, None),
        ("RK3 option '6 m' for 600 (cm)", _mc(ir("evaluate", {"expr": "L"}, ["L = 600"], [{"name": "L", "domain": "real"}]),
                                              {"A": "6 m", "B": "60 m", "C": "600 m"}), sol("600", option="A"), NOTOK, None),
    ]


# N: second round, the tolerance window (SA-RK-6) --------------------------------------------------------------------
def cases_n():
    def tol(options):
        return ir("evaluate", {"expr": "sqrt(50)", "rel_tol": "0.01"}, options=options)
    o50u = {"A": "6.5", "B": "7.07", "C": "7.5", "D": "8"}
    ex = ir("definite_integral", {"integrand": "exp(x**2)", "var": "x", "a": "0", "b": "1", "rel_tol": "0.01"},
            options={"A": "1.25", "B": "1.46", "C": "1.6", "D": "1.72", "E": "Hiçbiri"})
    return [
        ("RK6 E 'Hiçbiri': 7.07 letter B", tol(dict(o50u, E="Hiçbiri")), sol("7.07", option="B"), OK, None),
        ("RK6 E 'Belirlenemez': letter B only", tol(dict(o50u, E="Belirlenemez")), sol(None, option="B"), OK, None),
        ("RK6 E 'Yukarıdakilerin hiçbiri.': 7.07 letter B", tol(dict(o50u, E="Yukarıdakilerin hiçbiri.")),
         sol("7.07", option="B"), OK, None),
        ("RK6 E 'Hiçbiri': 6.5 letter A (wrong)", tol(dict(o50u, E="Hiçbiri")), sol("6.5", option="A"), NO, None),
        ("RK6 E 'Hiçbiri' chosen: not read", tol(dict(o50u, E="Hiçbiri")), sol(None, option="E"), UNK, None),
        ("RK6 E '7 ile 8 arasında': undecided", tol(dict(o50u, E="7 ile 8 arasında")), sol("7.07", option="B"), UNK, None),
        ("RK6 E '5√2' (√50 itself): two in the window", tol(dict(o50u, E="5√2")), sol("7.07", option="B"), UNK, None),
        ("RK6 ∫e^{x²} E 'Hiçbiri': 1.4627 letter B", ex, sol("1.4627", option="B"), OK, None),
        ("RK6 ∫e^{x²} E 'Hiçbiri': letter C (wrong)", ex, sol(None, option="C"), NO, None),
    ]


# P/Q/R: third round (EK 8; the second independent audit, son-adim-t2) ---------------------------------------------
def cases_p():
    inc = ir("evaluate", {"expr": "(p2 - p1)/p1*100"}, ["p1 = 50", "p2 = 60"], P12)
    inc_u = dict(inc, units="%")
    ratio_u = dict(ir("evaluate", {"expr": "(p2 - p1)/p1"}, ["p1 = 50", "p2 = 60"], P12), units="%")
    rate = ir("evaluate", {"expr": "r"}, ["1000*(1 + r) = 1200"], [{"name": "r", "domain": "positive_real"}])
    rate_u = dict(rate, units="%")
    tri_u = dict(ir("evaluate", {"expr": "x"}, ["x + 2*x + 3*x = 180"]), units="derece")
    degv = ir("evaluate", {"expr": "C"}, ["cos(pi*C/180) = 1/2", "0 < C", "C < 180"], [{"name": "C", "domain": "real"}])
    machin = dict(ir("evaluate", {"expr": "atan(1) + atan(2) + atan(3)"}), units="derece")
    tri_geo = ir("synthetic_geometry", {"points": ["A", "B", "C"], "constraints": ["angle(A,B,C) = 90", "dist(A,C) = 10",
                                                                                   "dist(B,C) = 5"],
                                        "target": "angle(B,A,C)"}, vars_=[], units="derece")
    return [
        # claims and options: one marked number, the unit proved
        ("P1 ×100: %20", inc_u, sol("%20"), OK, None),
        ("P1 ×100: 20%", inc, sol("20%"), OK, None),
        ("P1 ×100: letter %20 only", _mc(inc_u, PCT), sol(None, option="B"), OK, None),
        ("P1 ×100: %25 (wrong)", inc_u, sol("%25"), NO, None),
        ("P1 ×100: %0.2 (wrong)", inc, sol("%0.2"), NO, None),
        ("P1 ×180/pi: asin(1/2)*180/pi, 30°", ir("evaluate", {"expr": "asin(1/2)*180/pi"}), sol("30°"), OK, None),
        ("P1 degree variable cos(pi*C/180) = 1/2: 60°", degv, sol("60°"), OK, None),
        ("P1 degree variable deg(x): 60^\\circ", ir("evaluate", {"expr": "x"}, ["cos(deg(x)) = 1/2", "0 < x", "x < 90"]),
         sol("60^\\circ"), OK, None),
        ("P1 degree variable: 30° (wrong)", degv, sol("30°"), NO, None),
        # not proved: both readings, UNKNOWN where they decide apart (T2-RK-2, T2-OT-1, SA2-YO-4)
        ("P2 fraction IR units %: %20", ratio_u, sol("%20"), UNK, None),
        ("P2 fraction IR units %: letter %20", _mc(ratio_u, PCT), sol(None, option="B"), UNK, None),
        ("P2 rate units %: %20", rate_u, sol("%20"), UNK, None),
        ("P2 rate units %: %0.2 (wrong, never CORRECT)", rate_u, sol("%0.2"), UNK, None),
        ("P2 rate units yüzde: %0.2", dict(rate, units="yüzde"), sol("%0.2"), UNK, None),
        ("P2 rate: 0.2 (no mark)", rate_u, sol("0.2"), OK, None),
        ("P2 atan1 + atan2 + atan3 units derece: 180°", machin, sol("180°"), UNK, None),
        ("P2 2*asin(1/2) units derece: 60°", dict(ir("evaluate", {"expr": "2*asin(1/2)"}), units="derece"), sol("60°"),
         UNK, None),
        ("P2 acos(-1/2): 120° (an inverse trigonometric value: radians)", dict(ir("evaluate", {"expr": "acos(-1/2)"}),
                                                                               units="derece"), sol("120°"), OK, None),
        ("P2 triangle units derece: 40° (wrong under both)", tri_u, sol("40°"), NO, None),
        # steps: both readings, refuted only under both (T2-RK-1)
        ("P3 step 10/50 = %20", inc_u, sol("20", steps=[("compute", "60 - 50 = 10"), ("compute", "10/50 = %20")]), OK,
         NEITHER),
        ("P3 step %20 = 20/100", inc_u, sol("20", steps=[("compute", "%20 = 20/100")]), OK, NEITHER),
        ("P3 step p2 = p1 + %20*p1", inc_u, sol("20", steps=[("eq", "p2 = p1 + %20*p1")]), OK, NEITHER),
        ("P3 step (1 + %20)*(1 - %20) = 0.96", dict(ir("evaluate", {"expr": "((1 + 20/100)*(1 - 20/100) - 1)*100"}),
                                                    units="%"),
         sol("-4", steps=[("compute", "(1 + %20)*(1 - %20) = 0.96")]), OK, NEITHER),
        ("P3 step sin(30°) = 1/2 (triangle, units derece)", tri_u,
         sol("30", steps=[("eq", "6*x = 180"), ("eq", "x = 30"), ("compute", "sin(30°) = 1/2")]), OK, NEITHER),
        ("P3 step cos(60°) = 1/2 (degree variable)", dict(degv, units="derece"),
         sol("60", steps=[("compute", "cos(60°) = 1/2"), ("eq", "C = 60")]), OK, None),
        ("P3 geometry angle(), units derece: step sin(30°) = 1/2", tri_geo,
         sol("30", steps=[("compute", "5/10 = 1/2"), ("compute", "sin(30°) = 1/2")]), OK, None),
        ("P3 step 50/250 = %0.2 (wrong as a unit, right as a number: unknown)",
         dict(ir("evaluate", {"expr": "(300 - 250)/250*100"}), units="%"),
         sol("20", steps=[("compute", "300 - 250 = 50"), ("compute", "50/250 = %0.2")]), OK, NEITHER),
        ("P3 step 10/50 = %25 (wrong under both)", inc_u, sol("20", steps=[("compute", "10/50 = %25")]), NO, REF),
        ("P3 step sin(30°) = 1/3 (wrong under both)", tri_u,
         sol("30", steps=[("eq", "6*x = 180"), ("compute", "sin(30°) = 1/3")]), NO, REF),
    ]


def cases_q():
    abc = [{"name": n, "domain": "positive_real"} for n in "ABC"]
    q2 = ir("evaluate", {"expr": "B"}, ["A = 40", "B = C", "A + B + C = 180"], abc)
    q1 = ir("evaluate", {"expr": "C"}, ["A = 50", "B = 60", "A + B + C = 180"], abc)
    tri = ir("evaluate", {"expr": "B"}, ["A = 2*B", "C = 3*B", "A + B + C = 180"], abc)
    pv = [{"name": n, "domain": "positive_real"} for n in ("a", "b", "r")]
    pct = ir("evaluate", {"expr": "r"}, ["a = 50", "b = 60", "r = (b - a)/a*100"], pv)
    return [
        ("Q1 A = 40°, B = C, then wrong C = 2*B", q2, sol("70", steps=[("eq", "A = 40°"), ("eq", "B = C"),
                                                                       ("eq", "C = 2*B")]), NO, REF),
        ("Q1 A = 40°, B = C (right steps)", q2, sol("70", steps=[("eq", "A = 40°"), ("eq", "B = C")]), OK, VER),
        ("Q1 A = 50°, then wrong A + B = 100", q1, sol("70", steps=[("eq", "A = 50°"), ("eq", "A + B = 100")]), NO, REF),
        ("Q1 A + B + C = 180°, 6B = 180°, then wrong 5B = 180", tri,
         sol("30", steps=[("eq", "A + B + C = 180°"), ("eq", "2*B + B + 3*B = 180°"), ("eq", "5*B = 180")]), NO, REF),
        ("Q1 r = %20, then wrong b - a = 15", pct, sol("20", steps=[("eq", "r = %20"), ("eq", "b - a = 15")]), NO, REF),
        ("Q1 control: no marks, wrong C = 2*B", q2, sol("70", steps=[("eq", "A = 40"), ("eq", "B = C"), ("eq", "C = 2*B")]),
         NO, REF),
    ]


def cases_r():
    def tol(expr, options, t="0.01"):
        return ir("evaluate", {"expr": expr, "rel_tol": t}, options=options)
    o99 = {"A": "9", "B": "9,5", "C": "9,95", "D": "10", "E": "10,5"}
    xeq = {"A": "x = 4", "B": "x = 6", "C": "x = 8", "D": "x = 9"}
    lin = ir("solve_equation", {"equation": "2*x + 3 = 15", "var": "x"})
    days = ir("evaluate", {"expr": "t"}, ["t = 1/6 + 1/12"], [{"name": "t", "domain": "positive_real"}])
    out = [
        # SA2-YO-2: undecided in the window, never outside it
        ("R1 √99: decimal comma 9,95 beside 10, letter 10", tol("sqrt(99)", o99), sol("10", option="D"), UNK, None),
        ("R1 √99: letter 10 only", tol("sqrt(99)", o99), sol(None, option="D"), UNK, None),
        ("R1 pi: 3,14 beside 22/7", tol("pi", {"A": "3", "B": "3,14", "C": "22/7", "D": "3,2", "E": "4"}),
         sol("22/7", option="C"), UNK, None),
        ("R1 √99: range 9–11 beside 10", tol("sqrt(99)", {"A": "9", "B": "9–11", "C": "11", "D": "10", "E": "12"}),
         sol("10", option="D"), UNK, None),
        ("R1 √99: set [9, 11] beside 10", tol("sqrt(99)", {"A": "9", "B": "[9, 11]", "C": "11", "D": "10", "E": "12"}),
         sol("10", option="D"), UNK, None),
        ("R1 √99 control: one in the window", tol("sqrt(99)", {"A": "9", "B": "8", "C": "11", "D": "10", "E": "12"}),
         sol("10", option="D"), OK, None),
        # SA2-YO-3
        ("R2 days IR mis-formulated: 1/4 beside '3 gün' ... (no option carries it)",
         _mc(days, {"A": "3 gün", "B": "4 gün", "C": "5 gün", "D": "6 gün", "E": "8 gün"}), sol("1/4"), UNK, None),
        ("R2 a = 3*2: 6 beside '4 cm', '8 cm', '10 cm'", _mc(ir("evaluate", {"expr": "a"}, ["a = 3*2"],
                                                                 [{"name": "a", "domain": "real"}]),
                                                              {"A": "4 cm", "B": "8 cm", "C": "10 cm"}), sol("6"), UNK, None),
        ("R2 a = 3*2: 6 beside '4 cm', '6 cm' (carried)", _mc(ir("evaluate", {"expr": "a"}, ["a = 3*2"],
                                                                  [{"name": "a", "domain": "real"}]),
                                                               {"A": "4 cm", "B": "6 cm", "C": "8 cm"}), sol("6"), OK, None),
        # T2-RK-3
        ("R3 'x = 6' option: payload 6, letter B", _mc(lin, xeq), sol("6", option="B"), OK, None),
        ("R3 'x = 6' option: letter B only ({{6}} before)", _mc(lin, xeq), sol(None, option="B"), OK, None),
        ("R3 'x=6' option", _mc(lin, {"A": "x=4", "B": "x=6", "C": "x=8", "D": "x=9"}), sol("6", option="B"), OK, None),
        ("R3 sqrt(x + 2) = 3: 'x = 7'", _mc(ir("solve_equation", {"equation": "sqrt(x + 2) = 3", "var": "x"}),
                                            {"A": "x = 1", "B": "x = 7", "C": "x = 9"}), sol("7", option="B"), OK, None),
        ("R3 log2: 'x = 4'", _mc(ir("solve_equation", {"equation": "log(x, 2) + log(x - 2, 2) = 3", "var": "x"}),
                                 {"A": "x = -2", "B": "x = 4", "C": "x = 2", "D": "x = 8"}), sol("4", option="B"), OK, None),
        ("R3 payload 'x = 6', letter B", _mc(lin, xeq), sol("x = 6", option="B"), UNK, None),
        ("R3 wrong letter 'x = 4'", _mc(lin, xeq), sol("6", option="A"), NO, None),
        ("R3 letter 'x = 8' only (wrong)", _mc(lin, xeq), sol(None, option="C"), NO, None),
        # T2-RK-4
        ("R4 seven restatements, three critical steps", ineq("(x + 1)/(x - 2) >= 2", "interval"),
         sol("Interval.Lopen(2, 5)", "interval",
             [("eq", f) for f in ("(x + 1)/(x - 2) - 2 >= 0", "(5 - x)/(x - 2) >= 0", "(x - 5)/(x - 2) <= 0",
                                  "-(x - 5)/(x - 2) >= 0", "(10 - 2*x)/(2*x - 4) >= 0", "(2*x - 10)/(x - 2) <= 0",
                                  "(15 - 3*x)/(3*x - 6) >= 0")] + [("eq", "x - 5 = 0"), ("eq", "x - 2 = 0"),
                                                                  ("eq", "Or(Eq(x, 5), Eq(x, 2))")]), OK, NEITHER),
        ("R4 restatements then wrong x = 6", ineq("(x + 1)/(x - 2) >= 2", "interval"),
         sol("Interval.Lopen(2, 5)", "interval",
             [("eq", "(5 - x)/(x - 2) >= 0"), ("eq", "(x - 5)/(x - 2) <= 0"), ("eq", "x = 6")]), NO, REF),
    ]
    # T2-RK-6
    for meta in ("Yukarıdakilerden hiçbiri", "HİÇBİRİ", "Hiçbiri değil", "Hiçbiri değildir", "Bilinemez", "Belirsiz"):
        out.append((f"R5 meta option '{meta}'", tol("sqrt(50)", {"A": "7.07", "B": "7.5", "C": "8", "D": "6.5", "E": meta}),
                    sol("7.07", option="A"), OK, None))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "K": cases_k,
          "L": cases_l, "M": cases_m, "N": cases_n, "P": cases_p, "Q": cases_q, "R": cases_r}


def main(out_path=None, groups="ABCDEFKLMNPQR"):
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
    grp = args[1] if len(args) > 1 else "ABCDEFKLMNPQR"
    sys.exit(1 if main(out, grp) else 0)
