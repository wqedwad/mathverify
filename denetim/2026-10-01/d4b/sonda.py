"""Part d4b of the fourth audit's fixes (1 Oct 2026): periodic conditions and solver completeness.

SymPy 1.14 solves an inequality or a `!=` with a trigonometric function on ONE period ([0, P)) and returns
that as the answer, also on a bounded domain; the callers took it for the domain or the solution set
(G2, D4-ADIM-G). `evaluate` with given equations trusted `solve`'s principal roots (G5). `trig_solve` read
no condition on the variable but its interval (G3), nor a written condition that fails everywhere (TAN-08).
The fix: `sandbox.exactsets.exact_solveset` (rebuilt and checked on a bounded domain, progressions for an
equation on ℝ, otherwise a ConditionSet), `Ctx.domain_for` solving trigonometric conditions last on what the
others leave, `Ctx.cut_by`, the completeness rule of `algebra._complete_solutions`, `trig._region`.

    A  G2 / D4-ADIM-G: one period read as the domain or the solution set (domain_of, solve_equation,
       solve_inequality, count_roots, count_integers, extremum, the step layer)
    B  G5: evaluate under given equations whose solution list is not proved complete
    C  G3 / TAN-08: trig_solve with other conditions on the variable, an equation defined nowhere,
       count_solutions with a condition defined nowhere
    D  controls whose verdict must not change (no periodic condition, or one solved exactly)
    E  the review of d4b (2 Oct 2026): no exact class, multiple roots, slowness; controls of the classes
    F  round 4 (2 Oct 2026): the classes (iv) one strictly monotone function, (v) a same-frequency sin/cos
       combination, (vi) their products, right and wrong claims and the edges (a root out of the range,
       base 1, log's domain); a rational system in several unknowns (completeness proved or not)
    G  round 5 (2 Oct 2026): no complete set out of the classes (two solvers agreeing is no proof): a full
       claim of a non-class equation UNKNOWN, a missing or extra root INCORRECT only when proved; the new
       classes (vii) exponent ratio, (viii) Abs/sign piecewise, (ix) one radical, (x) a sum of logs
    H  the review of round 5 (2 Oct 2026): B1 a positive generator for log/sinh/atan (Max(log x, 0) = 0,
       sqrt(log(x)**2) = 1), B2 sign(0) lost on closed cells, B3 a folded cell keeping undefined points,
       the odd-root convention of part d4a in the guarded solveset; controls

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/d4b/sonda.py [out.json] [groups]

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false acceptance
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
UNK = {"UNKNOWN"}
REF = {"refuted"}
NOTVER = {"refuted", "unknown", "skipped"}

X = {"name": "x", "domain": "real"}


def V(name="x", dom="real", cons=None):
    v = {"name": name, "domain": dom}
    if cons:
        v["constraints"] = list(cons)
    return v


def _ir(kind, params, vars_=(X,), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def eq(e, givens=(), vars_=(X,), dod=None):
    return _ir("solve_equation", {"equation": e, "var": "x"}, vars_, givens, "set", dod)


def ineq(e, givens=(), vars_=(X,)):
    return _ir("solve_inequality", {"inequality": e, "var": "x"}, vars_, givens, "set")


def croots(e, givens=(), vars_=(X,)):
    return _ir("count_roots", {"expr": e, "var": "x"}, vars_, givens, "count")


def cint(givens, vars_=(X,)):
    return _ir("count_integers", {"var": "x"}, vars_, givens, "count")


def ext(f, which="max", interval=None, vars_=(X,), givens=()):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return _ir("extremum", p, vars_, givens)


def domof(e, givens=(), vars_=(X,)):
    return _ir("domain_of", {"expr": e, "var": "x"}, vars_, givens, "set")


def ev(expr, givens, vars_=(X,), dod=None):
    return _ir("evaluate", {"expr": expr}, vars_, givens, "scalar", dod)


def trig(givens, interval=None, vars_=(X,), dod=None, equation=None):
    p = {"var": "x"}
    if interval:
        p["interval"] = interval
    if equation:
        p["equation"] = equation
    return _ir("trig_solve", p, vars_, givens, "set", dod)


S_ = "set"
TWO_PERIODS = "Union(Interval.Ropen(0, pi/2), Interval.open(pi/2, 3*pi/2), Interval.open(3*pi/2, 2*pi))"


# (label, ir, solution, expected verdicts, expected status of the LAST step or None)
def cases_a():
    return [
        # G2 finder (p21): constraint / given / dod sin(x) > 0, written tan / log(sin)
        ("eq x^2=49 cons sin>0: {7}", eq("x**2 = 49", vars_=[V("x", "real", ["sin(x) > 0"])]), _sol("{7}", S_), NOTNO, None),
        ("eq x^2=49 cons sin>0: {}", eq("x**2 = 49", vars_=[V("x", "real", ["sin(x) > 0"])]), _sol("{}", S_), NOTOK, None),
        ("eq x^2=49 given sin>0: {7}", eq("x**2 = 49", ["sin(x) > 0"]), _sol("{7}", S_), NOTNO, None),
        ("eq x^2=49 given sin>0: {}", eq("x**2 = 49", ["sin(x) > 0"]), _sol("{}", S_), NOTOK, None),
        ("eq x^2=49 dod sin>0: {}", eq("x**2 = 49", dod="sin(x) > 0"), _sol("{}", S_), NOTOK, None),
        ("eq x^2=49 dod sin>0: {7}", eq("x**2 = 49", dod="sin(x) > 0"), _sol("{7}", S_), NOTNO, None),
        ("eq x^2+tan-tan=4: {-2,2}", eq("x**2 + tan(x) - tan(x) = 4"), _sol("{-2, 2}", S_), NOTNO, None),
        ("eq x^2+tan-tan=4: {2}", eq("x**2 + tan(x) - tan(x) = 4"), _sol("{2}", S_), NOTOK, None),
        ("eq x^2*cos/cos=4: {2}", eq("x**2*cos(x)/cos(x) = 4"), _sol("{2}", S_), NOTOK, None),
        ("eq x^2*cos/cos=4: {-2,2}", eq("x**2*cos(x)/cos(x) = 4"), _sol("{-2, 2}", S_), NOTNO, None),
        ("eq log(sin x)=0: {pi/2}", eq("log(sin(x)) = 0"), _sol("{pi/2}", S_), NOTOK, None),
        ("eq sqrt(sin x)=1: {pi/2}", eq("sqrt(sin(x)) = 1"), _sol("{pi/2}", S_), NOTOK, None),
        ("eq x+log(sin)-log(sin)=7: {7}", eq("x + log(sin(x)) - log(sin(x)) = 7"), _sol("{7}", S_), NOTNO, None),
        ("eq x+log(sin)-log(sin)=7: {}", eq("x + log(sin(x)) - log(sin(x)) = 7"), _sol("{}", S_), NOTOK, None),
        ("ineq x^2+tan-tan<4: (-2,2) minus pi/2s", ineq("x**2 + tan(x) - tan(x) < 4"),
         _sol("Union(Interval.open(-2, -pi/2), Interval.open(-pi/2, pi/2), Interval.open(pi/2, 2))", "interval"), NOTNO, None),
        ("ineq x^2+tan-tan<4: [0,pi/2)U(pi/2,2)", ineq("x**2 + tan(x) - tan(x) < 4"),
         _sol("Union(Interval.Ropen(0, pi/2), Interval.open(pi/2, 2))", "interval"), NOTOK, None),
        ("croots x^2-4+tan-tan: 2", croots("x**2 - 4 + tan(x) - tan(x)"), _sol("2", "count"), NOTNO, None),
        ("croots x^2-4+tan-tan: 1", croots("x**2 - 4 + tan(x) - tan(x)"), _sol("1", "count"), NOTOK, None),
        ("croots x^2-49 cons sin>0: 1", croots("x**2 - 49", vars_=[V("x", "real", ["sin(x) > 0"])]), _sol("1", "count"), NOTNO, None),
        ("croots x^2-49 cons sin>0: 0", croots("x**2 - 49", vars_=[V("x", "real", ["sin(x) > 0"])]), _sol("0", "count"), NOTOK, None),
        ("croots x^2-49 given sin>0: 0", croots("x**2 - 49", ["sin(x) > 0"]), _sol("0", "count"), NOTOK, None),
        ("cint 0..10 sin>0: 6", cint(["x >= 0", "x <= 10", "sin(x) > 0"]), _sol("6", "count"), NOTNO, None),
        ("cint 0..10 sin>0: 3", cint(["x >= 0", "x <= 10", "sin(x) > 0"]), _sol("3", "count"), NOTOK, None),
        ("cint 0..10 int cons sin>0: 3", cint(["x >= 0", "x <= 10"], [V("x", "integer", ["sin(x) > 0"])]), _sol("3", "count"), NOTOK, None),
        ("cint 0..10 int cons sin>0: 6", cint(["x >= 0", "x <= 10"], [V("x", "integer", ["sin(x) > 0"])]), _sol("6", "count"), NOTNO, None),
        ("cint -3..3 sin<1/2: 2", cint(["x >= -3", "x <= 3", "sin(x) < 1/2"], [V("x", "integer")]), _sol("2", "count"), NOTOK, None),
        ("cint -3..3 sin<1/2: 5", cint(["x >= -3", "x <= 3", "sin(x) < 1/2"], [V("x", "integer")]), _sol("5", "count"), NOTNO, None),
        ("ext max -(x-7)^2 given sin>0: 0", ext("-(x - 7)**2", givens=["sin(x) > 0"]), _sol("0"), NOTNO, None),
        ("ext max -(x-7)^2 given sin>0: -(pi-7)^2", ext("-(x - 7)**2", givens=["sin(x) > 0"]), _sol("-(pi - 7)**2"), NOTOK, None),
        ("ext max -(x-7)^2 [0,10] cons sin>=0: 0", ext("-(x - 7)**2", "max", "[0, 10]", [V("x", "real", ["sin(x) >= 0"])]), _sol("0"), NOTNO, None),
        ("ext max -(x+6)^2 given cos>0: 0", ext("-(x + 6)**2", givens=["cos(x) > 0"]), _sol("0"), NOTNO, None),
        ("ext max sin x on [7,8]: sin(7)", ext("sin(x)", "max", "[7, 8]"), _sol("sin(7)"), NOTOK, None),
        ("ext max sqrt(sin x)+x on [10,12]: sqrt(sin 12)+12", ext("sqrt(sin(x)) + x", "max", "[10, 12]"), _sol("sqrt(sin(12)) + 12"), NOTOK, None),
        ("domof log(sin x): (0,pi)", domof("log(sin(x))"), _sol("Interval.open(0, pi)", "interval"), NOTOK, None),
        ("domof sqrt(sin x): [0,pi]", domof("sqrt(sin(x))"), _sol("Interval(0, pi)", "interval"), NOTOK, None),
        ("domof 1/cos x: one period", domof("1/cos(x)"), _sol(TWO_PERIODS, "interval"), NOTOK, None),
        ("domof tan x: one period", domof("tan(x)"), _sol(TWO_PERIODS, "interval"), NOTOK, None),
        ("domof x given sin>0: (0,pi)", domof("x", ["sin(x) > 0"]), _sol("Interval.open(0, pi)", "interval"), NOTOK, None),
        ("domof sqrt(x) given tan>1: (pi/4,pi/2)", domof("sqrt(x)", ["tan(x) > 1"]), _sol("Interval.open(pi/4, pi/2)", "interval"), NOTOK, None),
        ("domof sqrt(cos x): [0,pi/2]U[3pi/2,2pi]", domof("sqrt(cos(x))"), _sol("Union(Interval(0, pi/2), Interval(3*pi/2, 2*pi))", "interval"), NOTOK, None),
        ("domof sqrt(sin t) var t: [0,pi]", _ir("domain_of", {"expr": "sqrt(sin(t))", "var": "t"}, [V("t")], (), "interval"), _sol("[0, pi]", "interval"), NOTOK, None),
        ("eq tan x=1: {pi/4, 5pi/4}", eq("tan(x) = 1"), _sol("{pi/4, 5*pi/4}", S_), NOTOK, None),
        ("eq tan x=1 given 0<=x<10: {pi/4,5pi/4}", eq("tan(x) = 1", ["x >= 0", "x < 10"]), _sol("{pi/4, 5*pi/4}", S_), NOTOK, None),
        ("eq tan x=1 given 0<=x<10: {pi/4,5pi/4,9pi/4}", eq("tan(x) = 1", ["x >= 0", "x < 10"]), _sol("{pi/4, 5*pi/4, 9*pi/4}", S_), NOTNO, None),
        ("eq x*tan/tan=7: {7}", eq("x*tan(x)/tan(x) = 7"), _sol("{7}", S_), NOTNO, None),
        ("eq x*tan/tan=7: {}", eq("x*tan(x)/tan(x) = 7"), _sol("{}", S_), NOTOK, None),
        ("ineq tan x>1: (pi/4,pi/2)", ineq("tan(x) > 1"), _sol("Interval.open(pi/4, pi/2)", "interval"), NOTOK, None),
        ("ineq x^2<100 & sin>0: (0,pi)", _ir("solve_inequality", {"var": "x"}, [X], ["x**2 < 100", "sin(x) > 0"], "interval"),
         _sol("Interval.open(0, pi)", "interval"), NOTOK, None),
        ("ineq x^2<64 & sin>0: right set", _ir("solve_inequality", {"var": "x"}, [X], ["x**2 < 64", "sin(x) > 0"], "interval"),
         _sol("Union(Interval.open(-2*pi, -pi), Interval.open(0, pi), Interval.open(2*pi, 8))", "interval"), NOTNO, None),
        ("croots x-7+tan-tan: 1", croots("x - 7 + tan(x) - tan(x)"), _sol("1", "count"), NOTNO, None),
        ("croots x-7+tan-tan: 0", croots("x - 7 + tan(x) - tan(x)"), _sol("0", "count"), NOTOK, None),
        ("eq x^2=36 given cos>0: {6}", eq("x**2 = 36", ["cos(x) > 0"]), _sol("{6}", S_), NOTOK, None),
        ("eq x^2=36 given cos>0: {-6,6}", eq("x**2 = 36", ["cos(x) > 0"]), _sol("{-6, 6}", S_), NOTNO, None),
        ("eq x+1=x+1 int 0..10 sin>0: {1,2,3}", eq("x + 1 = x + 1", ["sin(x) > 0", "x >= 0", "x <= 10"], [V("x", "integer")]),
         _sol("{1, 2, 3}", S_), NOTOK, None),
        ("eq x+1=x+1 int 0..10 sin>0: {1,2,3,7,8,9}", eq("x + 1 = x + 1", ["sin(x) > 0", "x >= 0", "x <= 10"], [V("x", "integer")]),
         _sol("{1, 2, 3, 7, 8, 9}", S_), NOTNO, None),
        ("eq x^2+log(sin)-log(sin)=49: {}", eq("x**2 + log(sin(x)) - log(sin(x)) = 49"), _sol("{}", S_), NOTOK, None),
        ("eq x^2+log(sin)-log(sin)=49: {7}", eq("x**2 + log(sin(x)) - log(sin(x)) = 49"), _sol("{7}", S_), NOTNO, None),
        # not periodic: SymPy reads cos(atan(x) + atan(2)) = 0 as x = -2 (the zero is 1/2, a pole of the tan)
        ("eq x+tan(acot..)-tan(acot..)=1/2: {1/2}", eq("x + tan(acot(x) + acot(2)) - tan(acot(x) + acot(2)) = 1/2"), _sol("{1/2}", S_), NOTOK, None),
        ("eq x+tan(acot..)-tan(acot..)=1/2: {}", eq("x + tan(acot(x) + acot(2)) - tan(acot(x) + acot(2)) = 1/2"), _sol("{}", S_), NOTNO, None),
        # D4-ADIM-G: the step layer read x on one period of tan's domain
        ("ADIM-G simplify tan*cos, step Abs(x)=x", _ir("simplify_expression", {"expr": "tan(x)*cos(x)"}, [X], (), "expression"),
         _sol("sin(x)", "expression", [("compute", "Abs(x) = x")]), NOTOK, NOTVER),
        ("ADIM-G evaluate x+tan-tan, step eq x >= 0", _ir("simplify_expression", {"expr": "x + tan(x) - tan(x)"}, [X], (), "expression"),
         _sol("x", "expression", [("eq", "Abs(x) = x")]), NOTOK, NOTVER),
        ("ADIM-G eq x^2+log(sin)-log(sin)=49, step x > 0", eq("x**2 + log(sin(x)) - log(sin(x)) = 49"),
         _sol("{7}", S_, [("eq", "x**2 = 49"), ("eq", "x = 7")]), NOTNO, None),
    ]


def cases_b():
    return [
        ("eval x | sin=0, 3<x<7: pi", ev("x", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("pi"), NOTOK, None),
        ("eval x | sin=0, 3<x<7: 2pi", ev("x", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("2*pi"), NOTOK, None),
        ("eval x | sin=0, 4<x<7: 2pi", ev("x", ["sin(x) = 0", "x > 4", "x < 7"]), _sol("2*pi"), NOTNO, None),
        ("eval x | tan=1, 0<x<4: pi/4", ev("x", ["tan(x) = 1", "x > 0", "x < 4"]), _sol("pi/4"), NOTOK, None),
        ("eval x | tan=1, 0<x<4: 5pi/4", ev("x", ["tan(x) = 1", "x > 0", "x < 4"]), _sol("5*pi/4"), NOTOK, None),
        ("eval x | cos=1, 1<x<13: 2pi", ev("x", ["cos(x) = 1", "x > 1", "x < 13"]), _sol("2*pi"), NOTOK, None),
        ("eval x | cos=0, 0<x<5: pi/2", ev("x", ["cos(x) = 0", "x > 0", "x < 5"]), _sol("pi/2"), NOTOK, None),
        ("eval x | sin=1/2, 0<x<3: pi/6", ev("x", ["sin(x) = 1/2", "x > 0", "x < 3"]), _sol("pi/6"), NOTOK, None),
        ("eval x | sin=1/2, 2<x<3: 5pi/6", ev("x", ["sin(x) = 1/2", "x > 2", "x < 3"]), _sol("5*pi/6"), NOTNO, None),
        ("eval x | sin=1/2, 6<x<7: 13pi/6", ev("x", ["sin(x) = 1/2", "x > 6", "x < 7"]), _sol("13*pi/6"), NOTNO, None),
        ("eval x**2 | sin=0, 3<x<7: pi^2", ev("x**2", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("pi**2"), NOTOK, None),
        ("eval cos x | sin=0, 3<x<7: -1", ev("cos(x)", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("-1"), NOTOK, None),
        ("eval cos x | sin=0, 3<x<7: 1", ev("cos(x)", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("1"), NOTOK, None),
        ("eval cos x | sin=0 cons 3<x<7: -1", ev("cos(x)", ["sin(x) = 0"], [V("x", "real", ["x > 3", "x < 7"])]), _sol("-1"), NOTOK, None),
        ("eval x | sin=0 dod (3,7): pi", ev("x", ["sin(x) = 0"], dod="(3, 7)"), _sol("pi"), NOTOK, None),
        ("eval x | sin(pi x)=0, 0<x<3: 1", ev("x", ["sin(pi*x) = 0", "x > 0", "x < 3"]), _sol("1"), NOTOK, None),
        ("eval x^2 | sin(pi x)=0, 0<x<3: 1", ev("x**2", ["sin(pi*x) = 0", "x > 0", "x < 3"]), _sol("1"), NOTOK, None),
        ("eval sin x | tan=1: sqrt2/2", ev("sin(x)", ["tan(x) = 1"]), _sol("sqrt(2)/2"), NOTOK, None),
        ("eval sin x | tan=1: -sqrt2/2", ev("sin(x)", ["tan(x) = 1"]), _sol("-sqrt(2)/2"), NOTOK, None),
        ("eval sin x | cos=1/2, 4<x<8: -sqrt3/2", ev("sin(x)", ["cos(x) = 1/2", "x > 4", "x < 8"]), _sol("-sqrt(3)/2"), NOTOK, None),
        ("eval x | cos 2x=1, 1<x<7: pi", ev("x", ["cos(2*x) = 1", "x > 1", "x < 7"]), _sol("pi"), NOTOK, None),
        ("eval sin x | sin^2=1/4, 3<x<7: -1/2", ev("sin(x)", ["sin(x)**2 = 1/4", "x > 3", "x < 7"]), _sol("-1/2"), NOTOK, None),
        ("eval x | x*exp(x)=-1/5: W0", ev("x", ["x*exp(x) = -1/5"]), _sol("LambertW(-1/5)"), NOTOK, None),
        ("eval x | 2^x=x^2, x>0: 2", ev("x", ["2**x = x**2", "x > 0"]), _sol("2"), NOTOK, None),
        ("eval x | sin x = x/2, x>0", ev("x", ["sin(x) = x/2", "x > 0"]), _sol("1.895494267"), NOTOK, None),
        ("eval x | Abs(x-1)=2: 3", ev("x", ["Abs(x - 1) = 2"]), _sol("3"), NOTOK, None),
    ]


ALL4 = "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}"
G = "sin(x) + log(-1 - x**2) - log(-1 - x**2) = 0"


def cases_c():
    return [
        ("trig cos2x=1/2 [0,2pi) given x>pi: all4", trig(["cos(2*x) = 1/2", "x > pi"], "[0, 2*pi)"), _sol(ALL4, S_), NOTOK, None),
        ("trig cos2x=1/2 [0,2pi) given x>pi: two", trig(["cos(2*x) = 1/2", "x > pi"], "[0, 2*pi)"), _sol("{7*pi/6, 11*pi/6}", S_), NOTNO, None),
        ("trig cos2x=1/2 [0,2pi) cons x>pi: all4", trig(["cos(2*x) = 1/2"], "[0, 2*pi)", [V("x", "real", ["x > pi"])]), _sol(ALL4, S_), NOTOK, None),
        ("trig cos2x=1/2 [0,2pi) cons x>pi: two", trig(["cos(2*x) = 1/2"], "[0, 2*pi)", [V("x", "real", ["x > pi"])]), _sol("{7*pi/6, 11*pi/6}", S_), NOTNO, None),
        ("trig cos2x=1/2 [0,2pi) dod x>pi: all4", trig(["cos(2*x) = 1/2"], "[0, 2*pi)", dod="x > pi"), _sol(ALL4, S_), NOTOK, None),
        ("trig cos2x=1/2 [0,2pi) x>b, b=pi: all4", trig(["cos(2*x) = 1/2", "x > b", "b = pi"], "[0, 2*pi)", [X, V("b")]), _sol(ALL4, S_), NOTOK, None),
        ("trig cos2x=1/2 [0,2pi) x>b, b free: all4", trig(["cos(2*x) = 1/2", "x > b"], "[0, 2*pi)", [X, V("b")]), _sol(ALL4, S_), UNK, None),
        ("trig cos2x=1/2 [0,2pi) given cos<0: all4", trig(["cos(2*x) = 1/2", "cos(x) < 0"], "[0, 2*pi)"), _sol(ALL4, S_), NOTOK, None),
        ("trig cos2x=1/2 [0,2pi) given cos<0: {5pi/6,7pi/6}", trig(["cos(2*x) = 1/2", "cos(x) < 0"], "[0, 2*pi)"), _sol("{5*pi/6, 7*pi/6}", S_), NOTNO, None),
        ("trig cos2x=1/2 [0,2pi) given sin>0: {pi/6,5pi/6}", trig(["cos(2*x) = 1/2", "sin(x) > 0"], "[0, 2*pi)"), _sol("{pi/6, 5*pi/6}", S_), NOTNO, None),
        ("trig sinx=1/2 [0,2pi) given x>pi/2: both", trig(["sin(x) = 1/2", "x > pi/2"], "[0, 2*pi)"), _sol("{pi/6, 5*pi/6}", S_), NOTOK, None),
        ("trig sinx=1/2 [0,2pi) given x>pi/2: {5pi/6}", trig(["sin(x) = 1/2", "x > pi/2"], "[0, 2*pi)"), _sol("{5*pi/6}", S_), NOTNO, None),
        ("trig sinx=0 general, x positive: {n*pi}", trig(["sin(x) = 0"], None, [V("x", "positive_real")]), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 general, cons x>0: {n*pi}", trig(["sin(x) = 0"], None, [V("x", "real", ["x > 0"])]), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 general, given x>0: {n*pi}", trig(["sin(x) = 0", "x > 0"]), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 general, dod x>0: {n*pi}", trig(["sin(x) = 0"], None, dod="x > 0"), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 general, cons 0<x<4: {n*pi}", trig(["sin(x) = 0"], None, [V("x", "real", ["0 < x < 4"])]), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 general, cons 0<x<4: {pi}", trig(["sin(x) = 0"], None, [V("x", "real", ["0 < x < 4"])]), _sol("{pi}", S_), NOTNO, None),
        ("trig sinx=0 general, x integer: {n*pi}", trig(["sin(x) = 0"], None, [V("x", "integer")]), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 general, x integer: {0}", trig(["sin(x) = 0"], None, [V("x", "integer")]), _sol("{0}", S_), NOTNO, None),
        ("trig sinx=0 [-10,10] x integer: {-3pi..3pi}", trig(["sin(x) = 0"], "[-10, 10]", [V("x", "integer")]),
         _sol("{-3*pi, -2*pi, -pi, 0, pi, 2*pi, 3*pi}", S_), NOTOK, None),
        ("trig cos x=0 nonneg: {pi/2+n*pi}", trig(["cos(x) = 0"], None, [V("x", "nonneg_real")]), _sol("{pi/2 + n*pi}", S_), NOTOK, None),
        ("trig tan x=1 cons -pi<x<0: {pi/4+n*pi}", trig(["tan(x) = 1"], None, [V("x", "real", ["-pi < x < 0"])]), _sol("{pi/4 + n*pi}", S_), NOTOK, None),
        ("trig tan x=1 cons -pi<x<0: {-3pi/4}", trig(["tan(x) = 1"], None, [V("x", "real", ["-pi < x < 0"])]), _sol("{-3*pi/4}", S_), NOTNO, None),
        ("trig sin2x=0 [-pi,pi] dod x>0: all", trig(["sin(2*x) = 0"], "[-pi, pi]", dod="x > 0"), _sol("{-pi, -pi/2, 0, pi/2, pi}", S_), NOTOK, None),
        ("trig sin2x=0 [-pi,pi] dod x>0: {pi/2,pi}", trig(["sin(2*x) = 0"], "[-pi, pi]", dod="x > 0"), _sol("{pi/2, pi}", S_), NOTNO, None),
        ("trig param sinx=0 [0,2pi] given x!=0: {0,pi,2pi}", trig(["x != 0"], "[0, 2*pi]", equation="sin(x) = 0"), _sol("{0, pi, 2*pi}", S_), NOTOK, None),
        ("trig param sinx=0 [0,2pi] given x!=0: {pi,2pi}", trig(["x != 0"], "[0, 2*pi]", equation="sin(x) = 0"), _sol("{pi, 2*pi}", S_), NOTNO, None),
        ("trig sinx=0 [0,2pi] given cos=1: {0,pi,2pi}", trig(["sin(x) = 0", "cos(x) = 1"], "[0, 2*pi]"), _sol("{0, pi, 2*pi}", S_), NOTOK, None),
        ("trig sinx=0 [0,2pi] given cos=1: {0,2pi}", trig(["sin(x) = 0", "cos(x) = 1"], "[0, 2*pi]"), _sol("{0, 2*pi}", S_), NOTNO, None),
        ("trig sinx=0 & cos=1 general: {n*pi}", trig(["sin(x) = 0", "cos(x) = 1"]), _sol("{n*pi}", S_), NOTOK, None),
        ("trig sinx=0 & cos=1 general: {2n*pi}", trig(["sin(x) = 0", "cos(x) = 1"]), _sol("{2*n*pi}", S_), NOTNO, None),
        # TAN-08: defined nowhere as written
        ("TAN-08 trig [0,2pi) nowhere: {0,pi}", trig([G], "[0, 2*pi)"), _sol("{0, pi}", S_), NOTOK, None),
        ("TAN-08 trig general nowhere: {n*pi}", trig([G]), _sol("{n*pi}", S_), NOTOK, None),
        ("TAN-08 trig param nowhere: {0,pi}", trig([], "[0, 2*pi)", equation=G), _sol("{0, pi}", S_), NOTOK, None),
        ("TAN-08 trig [0,2pi) nowhere: {}", trig([G], "[0, 2*pi)"), _sol("{}", S_), NOTNO, None),
        ("TAN-08 count_solutions sqrt(-x) x>=1: 3",
         _ir("count_solutions", {"bounds": {"x": ["1", "3"], "y": ["1", "3"]}}, [V("x", "positive_integer"), V("y", "positive_integer")],
             ["x + y + sqrt(-x) - sqrt(-x) = 4"], "count"), _sol("3", "count"), NOTOK, None),
        ("TAN-08 count_solutions sqrt(-x) x>=1: 0",
         _ir("count_solutions", {"bounds": {"x": ["1", "3"], "y": ["1", "3"]}}, [V("x", "positive_integer"), V("y", "positive_integer")],
             ["x + y + sqrt(-x) - sqrt(-x) = 4"], "count"), _sol("0", "count"), NOTNO, None),
    ]


def cases_d():
    return [
        ("ctl trig cos2x=1/2 [0,2pi): all4", trig(["cos(2*x) = 1/2"], "[0, 2*pi)"), _sol(ALL4, S_), OK, None),
        ("ctl trig cos2x=1/2 [0,2pi): three", trig(["cos(2*x) = 1/2"], "[0, 2*pi)"), _sol("{pi/6, 5*pi/6, 7*pi/6}", S_), NO, None),
        ("ctl trig sin x=1/2 general", trig(["sin(x) = 1/2"]), _sol("{pi/6 + 2*n*pi, 5*pi/6 + 2*n*pi}", S_), OK, None),
        ("ctl trig tan x=1 general", trig(["tan(x) = 1"]), _sol("{pi/4 + n*pi}", S_), OK, None),
        ("ctl trig tan x=1 general wrong", trig(["tan(x) = 1"]), _sol("{pi/4 + 2*n*pi}", S_), NO, None),
        ("ctl trig tan x=sqrt3 [0,2pi)", trig(["tan(x) = sqrt(3)"], "[0, 2*pi)"), _sol("{pi/3, 4*pi/3}", S_), OK, None),
        ("ctl trig sqrt3 sin - cos = 1 [0,2pi)", trig(["sqrt(3)*sin(x) - cos(x) = 1"], "[0, 2*pi)"), _sol("{pi/3}", S_), NOTOK, None),
        ("ctl eq x^2=4 given x>0: {2}", eq("x**2 = 4", ["x > 0"]), _sol("{2}", S_), OK, None),
        ("ctl eq x^2=4: {2}", eq("x**2 = 4"), _sol("{2}", S_), NO, None),
        ("ctl eq tan x=1 given 0<=x<10 (sin form)", eq("sin(x) = cos(x)", ["x >= 0", "x < 10"]), _sol("{pi/4, 5*pi/4, 9*pi/4}", S_), NOTNO, None),
        ("ctl ineq x^2<4", ineq("x**2 < 4"), _sol("Interval.open(-2, 2)", "interval"), OK, None),
        ("ctl ineq sin x > 2: {}", ineq("sin(x) > 2"), _sol("{}", S_), NOTNO, None),
        ("ctl cint 0..10 x^2<20: 5", cint(["x >= 0", "x <= 10", "x**2 < 20"]), _sol("5", "count"), OK, None),
        ("ctl domof sqrt(4-x^2)", domof("sqrt(4 - x**2)"), _sol("Interval(-2, 2)", "interval"), OK, None),
        ("ctl domof log(x) given x<5", domof("log(x)", ["x < 5"]), _sol("Interval.open(0, 5)", "interval"), OK, None),
        ("ctl ext max sin x on [0,pi]: 1", ext("sin(x)", "max", "[0, pi]"), _sol("1"), NOTNO, None),
        ("ctl ext max sin x on [0,pi]: 1/2", ext("sin(x)", "max", "[0, pi]"), _sol("1/2"), NO, None),
        ("ctl ext max -(x-1)^2 on [0,3]: 0", ext("-(x - 1)**2", "max", "[0, 3]"), _sol("0"), OK, None),
        ("ctl simplify tan*cos = sin", _ir("simplify_expression", {"expr": "tan(x)*cos(x)"}, [X], (), "expression"),
         _sol("sin(x)", "expression"), NOTNO, None),
        ("ctl simplify tan*cos = cos", _ir("simplify_expression", {"expr": "tan(x)*cos(x)"}, [X], (), "expression"),
         _sol("cos(x)", "expression"), NO, None),
        ("ctl eval x+y=5, x-y=1: 3", ev("x", ["x + y = 5", "x - y = 1"], [X, V("y")]), _sol("3"), OK, None),
        ("ctl eval x^2=49, sin>0: 7", ev("x", ["x**2 = 49", "sin(x) > 0"]), _sol("7"), NOTNO, None),
        # no exact class: SymPy's finite set is no proof of completeness (coverage given up, review of d4b)
        ("ctl eval exp(x)=2: log 2", ev("x", ["exp(x) = 2"]), _sol("log(2)"), NOTNO, None),
        ("ctl eval Abs(x-1)=2, x>0: 3", ev("x", ["Abs(x - 1) = 2", "x > 0"]), _sol("3"), NOTNO, None),
        ("ctl eval x^5-x=0, x>1/2: 1", ev("x", ["x**5 - x = 0", "x > 1/2"]), _sol("1"), OK, None),
        ("ctl eval floor(x)=2, 2x=5: 5/2", ev("x", ["floor(x) = 2", "2*x = 5"]), _sol("5/2"), NOTNO, None),
        ("ctl eval sqrt(x)=2: 4", ev("x", ["sqrt(x) = 2"]), _sol("4"), NOTNO, None),
        ("ctl croots x^2-4: 2", croots("x**2 - 4"), _sol("2", "count"), OK, None),
        ("ctl count_solutions x+y=4 1..3: 3",
         _ir("count_solutions", {"bounds": {"x": ["1", "3"], "y": ["1", "3"]}}, [V("x", "positive_integer"), V("y", "positive_integer")],
             ["x + y = 4"], "count"), _sol("3", "count"), OK, None),
    ]


Q = "(sqrt(3)*sin(x) - cos(x) - 1)"          # its zeros on [0, 7]: pi/3 and pi
W2 = ["x >= 0", "x <= 2*pi"]
W7 = ["x >= 0", "x <= 7"]


def cases_e():
    """The review of d4b (2 Oct 2026): sets of equations with no exact class (B1), a multiple root a numeric
    search misses (B2), the same as a side condition (B3), evaluate (B4), definedness (B5), slowness (B6)."""
    return [
        ("B1 eq x*Q=0 [0,2pi]: {0,pi/3}", eq(f"x*{Q} = 0", W2), _sol("{0, pi/3}", S_), NOTOK, None),
        ("B1 eq x*Q=0 [0,2pi]: {0,pi/3,pi}", eq(f"x*{Q} = 0", W2), _sol("{0, pi/3, pi}", S_), NOTNO, None),
        ("B1 eq (x+1)*Q=0 [0,2pi]: {pi/3}", eq(f"(x + 1)*{Q} = 0", W2), _sol("{pi/3}", S_), NOTOK, None),
        ("B1 eq exp(x)*Q=0 [0,2pi]: {pi/3}", eq(f"exp(x)*{Q} = 0", W2), _sol("{pi/3}", S_), NOTOK, None),
        ("B1 eq expanded x Q: {0,pi/3}", eq("sqrt(3)*x*sin(x) - x*cos(x) = x", W2), _sol("{0, pi/3}", S_), NOTOK, None),
        ("B1 eq Q/x=0 [1,2pi]: {pi/3}", eq(f"{Q}/x = 0", ["x >= 1", "x <= 2*pi"]), _sol("{pi/3}", S_), NOTOK, None),
        ("B1 eq (x-10)Q(2x)=0 [0,4]: {pi/6}", eq("(x - 10)*(sqrt(3)*sin(2*x) - cos(2*x) - 1) = 0", ["x >= 0", "x <= 4"]),
         _sol("{pi/6}", S_), NOTOK, None),
        # on [0, 2] the zeros are 0 and pi/3 (pi > 2, pi/sqrt(2) = 2.22 > 2): {0, pi/3} is right. Round 3 expected
        # "not CORRECT" here, a wrong expectation (0ed77e2's CORRECT was right; corrected in round 4)
        ("B1 eq Q*sin(sqrt2 x)=0 [0,2]: {0,pi/3}", eq(f"{Q}*sin(sqrt(2)*x) = 0", ["x >= 0", "x <= 2"]), _sol("{0, pi/3}", S_),
         NOTNO, None),
        ("B1 eq Q*sin(sqrt2 x)=0 [0,2]: {pi/3}", eq(f"{Q}*sin(sqrt(2)*x) = 0", ["x >= 0", "x <= 2"]), _sol("{pi/3}", S_),
         NOTOK, None),
        ("B1 eq Q*sin(sqrt2 x)=0 [0,4]: {0,pi/3,pi}", eq(f"{Q}*sin(sqrt(2)*x) = 0", ["x >= 0", "x <= 4"]),
         _sol("{0, pi/3, pi}", S_), NOTOK, None),
        ("B1 croots x*Q on [0,2pi]: 2", croots(f"x*{Q}", W2), _sol("2", "count"), NOTOK, None),
        ("B2 eq Q^3=0 [0,7]: {pi/3}", eq(f"{Q}**3 = 0", W7), _sol("{pi/3}", S_), NOTOK, None),
        ("B2 ineq Q^3>0 [0,7]: {}", ineq(f"{Q}**3 > 0", W7), _sol("{}", S_), NOTOK, None),
        ("B3 eq x^2=4 given Q^3>0 [0,7]: {}", eq("x**2 = 4", [f"{Q}**3 > 0"] + W7), _sol("{}", S_), NOTOK, None),
        ("B3 eq x^2=4 given Q^3>0 [0,7]: {2}", eq("x**2 = 4", [f"{Q}**3 > 0"] + W7), _sol("{2}", S_), NOTNO, None),
        ("B3 eq x^2=4 dod Q^3>0 [0,7]: {}", eq("x**2 = 4", W7, dod=f"{Q}**3 > 0"), _sol("{}", S_), NOTOK, None),
        ("B3 eq x^2=4 cons Q^3>0 [0,7]: {}", eq("x**2 = 4", W7, vars_=[V("x", "real", [f"{Q}**3 > 0"])]), _sol("{}", S_),
         NOTOK, None),
        ("B3 croots x^2-4 given Q^3>0: 0", croots("x**2 - 4", [f"{Q}**3 > 0"] + W7), _sol("0", "count"), NOTOK, None),
        ("B3 trig Q^3=0 [0,7]: {pi/3}", trig([f"{Q}**3 = 0"], "[0, 7]"), _sol("{pi/3}", S_), NOTOK, None),
        ("B4 eval x | (x+1)Q=0, 0<x<4: pi/3", ev("x", [f"(x + 1)*{Q} = 0", "x > 0", "x < 4"]), _sol("pi/3"), NOTOK, None),
        ("B4 eval x | Q^3=0, 0<x<4: pi/3", ev("x", [f"{Q}**3 = 0", "x > 0", "x < 4"]), _sol("pi/3"), NOTOK, None),
        ("B4 eval x | exp(x)=3x: W0", ev("x", ["exp(x) = 3*x"]), _sol("-LambertW(-1/3)"), NOTOK, None),
        ("B5 ext max on [2,4] undefined at pi", ext(f"-(x - pi)**2 + (x + 1)*{Q}/((x + 1)*{Q}) - 1", "max", "[2, 4]"),
         _sol("0"), NOTOK, None),
        ("B6 eq x^2=4 given sin(1000x)>0 [0,30]: {2}", eq("x**2 = 4", ["sin(1000*x) > 0", "x >= 0", "x <= 30"]),
         _sol("{2}", S_), NOTNO, None),
        ("B6 eq x^2=4 given Q^2+sin^2>0 [0,7]: {2}", eq("x**2 = 4", [f"{Q}**2 + sin(x)**2 > 0"] + W7), _sol("{2}", S_),
         NOTNO, None),
        # controls: the exact classes keep their verdicts
        ("E ctl eq x*sin(x)=0 [0,7]: {0,pi,2pi}", eq("x*sin(x) = 0", W7), _sol("{0, pi, 2*pi}", S_), OK, None),
        ("E ctl eq x*sin(x)=0 [0,7]: {0,pi}", eq("x*sin(x) = 0", W7), _sol("{0, pi}", S_), NO, None),
        ("E ctl eq (x-1)^3 cos^3=0 [0,7]", eq("(x - 1)**3*cos(x)**3 = 0", W7), _sol("{1, pi/2, 3*pi/2}", S_), OK, None),
        ("E ctl ineq sin^3>0 [0,7]", ineq("sin(x)**3 > 0", W7), _sol("Union(Interval.open(0, pi), Interval.Lopen(2*pi, 7))", "interval"),
         OK, None),
        ("E ctl eq 4sin^2=1 [0,2pi)", eq("4*sin(x)**2 = 1", ["x >= 0", "x < 2*pi"]),
         _sol("{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", S_), OK, None),
        ("E ctl cint -10..10 tan>0: 10", cint(["x >= -10", "x <= 10", "tan(x) > 0"], [V("x", "integer")]), _sol("10", "count"),
         NOTNO, None),
    ]


Y = V("y")


def cases_f():
    return [
        # (iv) one strictly monotone function of a linear argument
        ("F4 eq exp(x)=2: {log 2}", eq("exp(x) = 2"), _sol("{log(2)}", S_), OK, None),
        ("F4 eq exp(x)=2: {log 2, -log 2}", eq("exp(x) = 2"), _sol("{log(2), -log(2)}", S_), NO, None),
        ("F4 eval exp(x)=2: log 2", ev("x", ["exp(x) = 2"]), _sol("log(2)"), OK, None),
        ("F4 eval exp(x)=2: log 3", ev("x", ["exp(x) = 2"]), _sol("log(3)"), NO, None),
        ("F4 eq 4^x-3*2^x+2=0: {0,1}", eq("4**x - 3*2**x + 2 = 0"), _sol("{0, 1}", S_), OK, None),
        ("F4 eq 4^x-3*2^x+2=0: {1}", eq("4**x - 3*2**x + 2 = 0"), _sol("{1}", S_), NO, None),
        ("F4 eq 2^(2x)-3*2^x+2=0: {0,1}", eq("2**(2*x) - 3*2**x + 2 = 0"), _sol("{0, 1}", S_), OK, None),
        ("F4 eval 4^x-3*2^x+2=0, x>0: 1", ev("x", ["4**x - 3*2**x + 2 = 0", "x > 0"]), _sol("1"), OK, None),
        ("F4 eq (1/2)^x=4: {-2}", eq("(1/2)**x = 4"), _sol("{-2}", S_), OK, None),
        ("F4 edge exp root out of range: {log 2}", eq("exp(2*x) - exp(x) - 2 = 0"), _sol("{log(2)}", S_), OK, None),
        ("F4 edge exp root out of range: {}", eq("exp(2*x) - exp(x) - 2 = 0"), _sol("{}", S_), NO, None),
        ("F4 edge atan(x)=2: {}", eq("atan(x) = 2"), _sol("{}", S_), OK, None),
        ("F4 edge atan(x)=2: {tan 2}", eq("atan(x) = 2"), _sol("{tan(2)}", S_), NO, None),
        ("F4 eq atan(x)=1: {tan 1}", eq("atan(x) = 1"), _sol("{tan(1)}", S_), OK, None),
        ("F4 eq sinh(x)=1: {log(1+sqrt2)}", eq("sinh(x) = 1"), _sol("{log(1 + sqrt(2))}", S_), OK, None),
        ("F4 edge log domain log^2=log: {1,E}", eq("log(x)**2 - log(x) = 0"), _sol("{1, E}", S_), OK, None),
        ("F4 edge log domain log^2=log: {0,1,E}", eq("log(x)**2 - log(x) = 0"), _sol("{0, 1, E}", S_), NO, None),
        ("F4 edge log domain ineq log x<1", ineq("log(x) < 1"), _sol("Interval.open(0, E)", "interval"), OK, None),
        ("F4 edge log domain ineq log x<1 wrong", ineq("log(x) < 1"), _sol("Interval.open(-oo, E)", "interval"), NO, None),
        ("F4 ineq exp(x)>2", ineq("exp(x) > 2"), _sol("Interval.open(log(2), oo)", "interval"), OK, None),
        ("F4 croots exp(2x)-3exp(x)+2: 2", croots("exp(2*x) - 3*exp(x) + 2"), _sol("2", "count"), OK, None),
        ("F4 croots exp(2x)-3exp(x)+2: 1", croots("exp(2*x) - 3*exp(x) + 2"), _sol("1", "count"), NO, None),
        ("F4 edge base 1: eval x | 1**x=1: 0", ev("x", ["1**x = 1"]), _sol("0"), NOTOK, None),
        ("F4 3^x=2^x: {0} (class vii since round 5)", eq("3**x = 2**x"), _sol("{0}", S_), OK, None),
        ("F4 out of class eval exp(x)=3x, x<1: W0", ev("x", ["exp(x) = 3*x", "x < 1"]), _sol("-LambertW(-1/3)"), NOTOK, None),
        # (v) a same-frequency sin/cos combination
        ("F5 eq sin=cos [0,2pi]: {pi/4,5pi/4}", eq("sin(x) = cos(x)", W2), _sol("{pi/4, 5*pi/4}", S_), OK, None),
        ("F5 eq sin=cos [0,2pi]: {pi/4}", eq("sin(x) = cos(x)", W2), _sol("{pi/4}", S_), NO, None),
        ("F5 eq sqrt3 sin-cos=1 [0,2pi]: {pi/3,pi}", eq("sqrt(3)*sin(x) - cos(x) = 1", W2), _sol("{pi/3, pi}", S_), OK, None),
        ("F5 eq sqrt3 sin-cos=1 [0,2pi]: {pi/3}", eq("sqrt(3)*sin(x) - cos(x) = 1", W2), _sol("{pi/3}", S_), NO, None),
        ("F5 trig sqrt3 sin-cos=1 [0,2pi): {pi/3,pi}", trig(["sqrt(3)*sin(x) - cos(x) = 1"], "[0, 2*pi)"),
         _sol("{pi/3, pi}", S_), OK, None),
        ("F5 eq sin2x+cos2x=1 [0,2pi]", eq("sin(2*x) + cos(2*x) = 1", W2), _sol("{0, pi/4, pi, 5*pi/4, 2*pi}", S_), OK, None),
        ("F5 eq sin-cos=2: {}", eq("sin(x) - cos(x) = 2"), _sol("{}", S_), OK, None),
        ("F5 ineq sin+cos>1 [0,2pi]", ineq("sin(x) + cos(x) > 1", W2), _sol("Interval.open(0, pi/2)", "interval"), OK, None),
        ("F5 eval sin=cos, 0<x<2: pi/4", ev("x", ["sin(x) = cos(x)", "x > 0", "x < 2"]), _sol("pi/4"), OK, None),
        ("F5 eval sin=cos, 0<x<4: pi/4", ev("x", ["sin(x) = cos(x)", "x > 0", "x < 4"]), _sol("pi/4"), NOTOK, None),
        # (vi) products of the classes
        ("F6 eq x(sin-cos)=0 [0,2pi]", eq("x*(sin(x) - cos(x)) = 0", W2), _sol("{0, pi/4, 5*pi/4}", S_), OK, None),
        ("F6 eq (exp(x)-2) sin x=0 [0,4]", eq("(exp(x) - 2)*sin(x) = 0", ["x >= 0", "x <= 4"]), _sol("{0, log(2), pi}", S_), OK, None),
        ("F6 eq (exp(x)-2) sin x=0 [0,4]: {0,pi}", eq("(exp(x) - 2)*sin(x) = 0", ["x >= 0", "x <= 4"]), _sol("{0, pi}", S_), NO, None),
        ("F6 eq log(x)*Q=0 [0,2pi]", eq(f"log(x)*{Q} = 0", W2), _sol("{1, pi/3, pi}", S_), OK, None),
        ("F6 eval x | (x+1)Q=0, 0<x<2: pi/3", ev("x", [f"(x + 1)*{Q} = 0", "x > 0", "x < 2"]), _sol("pi/3"), OK, None),
        ("F6 eq x*Q=0 [0,2pi]: {0,pi/3,pi}", eq(f"x*{Q} = 0", W2), _sol("{0, pi/3, pi}", S_), OK, None),
        ("F6 eq Q^3=0 [0,7]: {pi/3,pi}", eq(f"{Q}**3 = 0", W7), _sol("{pi/3, pi}", S_), OK, None),
        # a rational system in several unknowns
        ("FS eval xy | x+y=5, x^2+y^2=13: 6", ev("x*y", ["x + y = 5", "x**2 + y**2 = 13"], [X, Y]), _sol("6"), OK, None),
        ("FS eval xy | x+y=5, x^2+y^2=13: 5", ev("x*y", ["x + y = 5", "x**2 + y**2 = 13"], [X, Y]), _sol("5"), NO, None),
        ("FS eval x | x+y=5, xy=6, x>y: 3", ev("x", ["x + y = 5", "x*y = 6", "x > y"], [X, Y]), _sol("3"), OK, None),
        ("FS eval x | x+y=5, xy=6: 3", ev("x", ["x + y = 5", "x*y = 6"], [X, Y]), _sol("3"), NOTOK, None),
        ("FS eval x | x^2=y, y^2=x, x>0: 1", ev("x", ["x**2 = y", "y**2 = x", "x > 0"], [X, Y]), _sol("1"), OK, None),
        ("FS eval x+y | 1/x+1/y=1, xy=4: 4", ev("x + y", ["1/x + 1/y = 1", "x*y = 4"], [X, Y]), _sol("4"), OK, None),
        ("FS eval x+y | x^2+y^2=2, xy=1: 2", ev("x + y", ["x**2 + y**2 = 2", "x*y = 1"], [X, Y]), _sol("2"), NOTOK, None),
        ("FS eval x+y | xy=1 (a curve): 2", ev("x + y", ["x*y = 1"], [X, Y]), _sol("2"), NOTOK, None),
    ]


def cases_g():
    return [
        # out of the classes: a full claim is not certified, a wrong one is refuted only with a proof
        ("G0 eq exp(x)+x=1: {0} (only root, no class)", eq("exp(x) + x = 1"), _sol("{0}", S_), UNK, None),
        ("G0 eq exp(x)+x=1: {1} (no root)", eq("exp(x) + x = 1"), _sol("{1}", S_), NO, None),
        ("G0 eq log(x)=x-1: {1}", eq("log(x) = x - 1"), _sol("{1}", S_), UNK, None),
        ("G0 eq log(x)=x-1: {2}", eq("log(x) = x - 1"), _sol("{2}", S_), NO, None),
        ("G0 eq x^x=4: {2}", eq("x**x = 4", ["x > 0"]), _sol("{2}", S_), UNK, None),
        ("G0 eq exp(x)=3x: {}", eq("exp(x) = 3*x"), _sol("{}", S_), NOTOK, None),
        ("G0 eq 2^x=x^2: {2,4} (third root missing)", eq("2**x = x**2"), _sol("{2, 4}", S_), NOTOK, None),
        ("G0 eq 2^x=x^2: {2,4,5}", eq("2**x = x**2"), _sol("{2, 4, 5}", S_), NO, None),
        ("G0 ineq exp(x)>x+1: x!=0", ineq("exp(x) > x + 1"), _sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", "interval"),
         UNK, None),
        ("G0 eval x | exp(x)+x=1: 0", ev("x", ["exp(x) + x = 1"]), _sol("0"), NOTOK, None),
        ("G0 eq floor(x)=2: [2,3)", eq("floor(x) = 2"), _sol("Interval.Ropen(2, 3)", "interval"), NOTNO, None),
        # (vii) the ratio of two exponentials: log of both sides is linear
        ("G7 eq 3^x=2^x: {0}", eq("3**x = 2**x"), _sol("{0}", S_), OK, None),
        ("G7 eq 3^x=2^x: {0,1}", eq("3**x = 2**x"), _sol("{0, 1}", S_), NO, None),
        ("G7 eq 3^x=2^x: {}", eq("3**x = 2**x"), _sol("{}", S_), NO, None),
        ("G7 eq 3^(2x+1)=2^(x-1)", eq("3**(2*x + 1) = 2**(x - 1)"), _sol("{-log(6)/log(9/2)}", S_), NOTNO, None),
        ("G7 ineq 3^x>2^x", ineq("3**x > 2**x"), _sol("Interval.open(0, oo)", "interval"), OK, None),
        ("G7 eq 3^x=-2^x: {}", eq("3**x + 2**x = 0"), _sol("{}", S_), OK, None),
        ("G7 eq 4^x=2^(2x) (identity): {0}", eq("4**x = 2**(2*x)"), _sol("{0}", S_), NOTOK, None),
        # (viii) Abs and sign: piecewise on the cells of their arguments
        ("G8 eq |2x-3|=5: {-1,4}", eq("Abs(2*x - 3) = 5"), _sol("{-1, 4}", S_), OK, None),
        ("G8 eq |2x-3|=5: {4}", eq("Abs(2*x - 3) = 5"), _sol("{4}", S_), NO, None),
        ("G8 ineq |x-3|<2", ineq("Abs(x - 3) < 2"), _sol("Interval.open(1, 5)", "interval"), OK, None),
        ("G8 cint |x-3|<2: 3", cint(["Abs(x - 3) < 2"], [V("x", "integer")]), _sol("3", "count"), OK, None),
        ("G8 cint |x-3|<2: 5", cint(["Abs(x - 3) < 2"], [V("x", "integer")]), _sol("5", "count"), NO, None),
        ("G8 eq |x^2-4|=3x: {1,4}", eq("Abs(x**2 - 4) = 3*x"), _sol("{1, 4}", S_), OK, None),
        ("G8 eq |x|+|x-1|=1: [0,1]", eq("Abs(x) + Abs(x - 1) = 1"), _sol("Interval(0, 1)", "interval"), NOTNO, None),
        # (ix) one radical: eliminate it, check every candidate
        ("G9 eq sqrt(x+4)=x-2: {5}", eq("sqrt(x + 4) = x - 2"), _sol("{5}", S_), OK, None),
        ("G9 eq sqrt(x+4)=x-2: {0,5}", eq("sqrt(x + 4) = x - 2"), _sol("{0, 5}", S_), NO, None),
        ("G9 ineq sqrt(x+4)>x-2", ineq("sqrt(x + 4) > x - 2"), _sol("Interval.Ropen(-4, 5)", "interval"), OK, None),
        ("G9 eq sqrt(x)=-1: {}", eq("sqrt(x) = -1"), _sol("{}", S_), OK, None),
        ("G9 eq sqrt(x)=-1: {1}", eq("sqrt(x) = -1"), _sol("{1}", S_), NO, None),
        # (x) a sum of logs of polynomials
        ("G10 eq log(x-1)+log(x-3)=log3: {4}", eq("log(x - 1) + log(x - 3) = log(3)"), _sol("{4}", S_), OK, None),
        ("G10 eq log(x-1)+log(x-3)=log3: {0,4}", eq("log(x - 1) + log(x - 3) = log(3)"), _sol("{0, 4}", S_), NO, None),
        ("G10 ineq log(x-1)+log(x-3)<log3", ineq("log(x - 1) + log(x - 3) < log(3)"), _sol("Interval.open(3, 4)", "interval"),
         OK, None),
        ("G10 eq log(x^2)=log4: {-2,2}", eq("log(x**2) = log(4)"), _sol("{-2, 2}", S_), OK, None),
        ("G10 eq 2log(x)=log4: {2}", eq("2*log(x) = log(4)"), _sol("{2}", S_), OK, None),
        ("G10 eq 2log(x)=log4: {-2,2}", eq("2*log(x) = log(4)"), _sol("{-2, 2}", S_), NO, None),
        # count_roots of a class
        ("G croots exp(2x)-3exp(x)+2: 2", croots("exp(2*x) - 3*exp(x) + 2"), _sol("2", "count"), OK, None),
        ("G croots exp(2x)-3exp(x)+2: 1", croots("exp(2*x) - 3*exp(x) + 2"), _sol("1", "count"), NO, None),
        ("G croots exp(x)-3x: 2 (no class)", croots("exp(x) - 3*x"), _sol("2", "count"), UNK, None),
    ]


def cases_h():
    return [
        # B1
        ("H1 eq Max(log x,0)=0: {1}", eq("Max(log(x), 0) = 0"), _sol("{1}", S_), NO, None),
        ("H1 eq Max(log x,0)=0: (0,1]", eq("Max(log(x), 0) = 0"), _sol("Interval.Lopen(0, 1)", "interval"), NOTNO, None),
        ("H1 eq Max(sinh x,0)=0: {0}", eq("Max(sinh(x), 0) = 0"), _sol("{0}", S_), NO, None),
        ("H1 croots Max(log x,0): 1", croots("Max(log(x), 0)"), _sol("1", "count"), NOTOK, None),
        ("H1 eq sqrt(log^2)=1: {E}", eq("sqrt(log(x)**2) = 1"), _sol("{E}", S_), NO, None),
        ("H1 eq sqrt(log^2)=1: {E,1/E}", eq("sqrt(log(x)**2) = 1"), _sol("{E, exp(-1)}", S_), OK, None),
        ("H1 eq |log x|=1: {E}", eq("Abs(log(x)) = 1"), _sol("{E}", S_), NO, None),
        ("H1 eq |log x|=1: {E,1/E}", eq("Abs(log(x)) = 1"), _sol("{E, exp(-1)}", S_), OK, None),
        ("H1 croots sqrt(log^2)-1: 2", croots("sqrt(log(x)**2) - 1"), _sol("2", "count"), OK, None),
        ("H1 croots sqrt(log^2)-1: 1", croots("sqrt(log(x)**2) - 1"), _sol("1", "count"), NO, None),
        ("H1 eval x | sqrt(log^2)=1, x>0: E", ev("x", ["sqrt(log(x)**2) = 1", "x > 0"]), _sol("E"), NOTOK, None),
        ("H1 eval x | sqrt(log^2)=1, x>1: E", ev("x", ["sqrt(log(x)**2) = 1", "x > 1"]), _sol("E"), OK, None),
        ("H1 domof log(Max(x,0)): (0,oo)", domof("log(Max(x, 0))"), _sol("Interval.open(0, oo)", "interval"), OK, None),
        # B2
        ("H2 eq sign(x)=0: {}", eq("sign(x) = 0"), _sol("{}", S_), NO, None),
        ("H2 eq sign(x)=0: {0}", eq("sign(x) = 0"), _sol("{0}", S_), OK, None),
        ("H2 eq sign(x^2-4)=0: {}", eq("sign(x**2 - 4) = 0"), _sol("{}", S_), NO, None),
        ("H2 croots sign(x): 0", croots("sign(x)"), _sol("0", "count"), NO, None),
        ("H2 croots sign(x): 1", croots("sign(x)"), _sol("1", "count"), OK, None),
        ("H2 eq sign(x)+|x|=0: {-1}", eq("sign(x) + Abs(x) = 0"), _sol("{-1}", S_), NO, None),
        ("H2 eq sign(x)+|x|=0: {-1,0}", eq("sign(x) + Abs(x) = 0"), _sol("{-1, 0}", S_), OK, None),
        ("H2 cint sign(x)=0 [-3,3]: 0", cint(["sign(x) = 0", "x >= -3", "x <= 3"], [V("x", "integer")]), _sol("0", "count"), NO, None),
        ("H2 cint sign(x)=0 [-3,3]: 1", cint(["sign(x) = 0", "x >= -3", "x <= 3"], [V("x", "integer")]), _sol("1", "count"), OK, None),
        ("H2 ineq sign(x)>=1: (0,oo)", ineq("sign(x) >= 1"), _sol("Interval.open(0, oo)", "interval"), OK, None),
        ("H2 ineq sign(x)>=1: [0,oo)", ineq("sign(x) >= 1"), _sol("Interval(0, oo)", "interval"), NO, None),
        ("H2 domof 1/sign(x): R", domof("1/sign(x)"), _sol("Reals", "interval"), NO, None),
        ("H2 step sign(x)=0 => x=0 verified", ev("x", ["sign(x) = 0"]), _sol("0", steps=[("eq", "x = 0")]), OK, {"verified"}),
        # B3
        ("H3 eq |x|/x=1: (0,oo)", eq("Abs(x)/x = 1"), _sol("Interval.open(0, oo)", "interval"), NOTNO, None),
        ("H3 eq |x|/x=1: [0,oo)", eq("Abs(x)/x = 1"), _sol("Interval(0, oo)", "interval"), NOTOK, None),
        ("H3 ineq |x|/x>=-1: R", ineq("Abs(x)/x >= -1"), _sol("Reals", "interval"), NO, None),
        ("H3 ineq |x|/x>=-1: R-{0}", ineq("Abs(x)/x >= -1"), _sol("Union(Interval.open(-oo, 0), Interval.open(0, oo))", "interval"),
         OK, None),
        ("H3 croots |x|/x+x-1: 0", croots("Abs(x)/x + x - 1"), _sol("0", "count"), OK, None),
        ("H3 croots |x|/x+x-1: 1", croots("Abs(x)/x + x - 1"), _sol("1", "count"), NO, None),
        # the odd-root convention (part d4a): no reading is picked in the guarded solveset
        ("H4 eq x^(2/3)=1: {1}", eq("x**(2/3) = 1"), _sol("{1}", S_), UNK, None),
        ("H4 eq x^(2/3)=1: {-1,1}", eq("x**(2/3) = 1"), _sol("{-1, 1}", S_), UNK, None),
        ("H4 eq x^(2/3)=1, x>0: {1}", eq("x**(2/3) = 1", ["x > 0"]), _sol("{1}", S_), OK, None),
        ("H4 eq cbrt(x)=x: {-1,0,1}", eq("cbrt(x) = x"), _sol("{-1, 0, 1}", S_), OK, None),
        ("H4 croots x^(1/3)-x: 3", croots("x**(1/3) - x"), _sol("3", "count"), NOTOK, None),
        # controls
        ("H5 ctl eq |2x-3|=5: {-1,4}", eq("Abs(2*x - 3) = 5"), _sol("{-1, 4}", S_), OK, None),
        ("H5 ctl eq Max(x,2)=3: {3}", eq("Max(x, 2) = 3"), _sol("{3}", S_), OK, None),
        ("H5 ctl eq Min(x,2)=2: [2,oo)", eq("Min(x, 2) = 2"), _sol("{2}", S_), NO, None),
        ("H5 ctl eq |sinh x|=1", eq("Abs(sinh(x)) = 1"), _sol("{log(1 + sqrt(2)), -log(1 + sqrt(2))}", S_), OK, None),
    ]


class _Slow(Exception):
    pass


def _on_alarm(signum, frame):
    raise _Slow()


# one verify past this (seconds) is a hang, counted as not expected (0ed77e2: over 20 minutes for B6)
CASE_TIMEOUT = int(os.environ.get("CASE_TIMEOUT", "120"))
signal.signal(signal.SIGALRM, _on_alarm)

GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g, "H": cases_h}


def main(out_path=None, groups="ABCDEFGH"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for label, ir, sol, verdicts, statuses in GROUPS[g]():
            t = time.time()
            signal.alarm(CASE_TIMEOUT)
            try:
                r = verify(ir, sol)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                status = steps[-1].get("status") if steps else None
                cert = [f"{la.layer}:{la.verdict}:{(la.evidence or {}).get('reason', '')}"[:120]
                        for la in r.layers if la.layer.startswith("certify") and la.verdict != "unknown"
                        or (la.layer.startswith("certify") and (la.evidence or {}).get("reason", "") not in ("not_applicable",))]
            except _Slow:
                verdict, status, cert = f"TIMEOUT {CASE_TIMEOUT} s", None, []
            except Exception as e:  # noqa: BLE001
                verdict, status, cert = f"EXC {type(e).__name__}: {e}", None, []
            signal.alarm(0)
            ok = verdict in verdicts and (statuses is None or status in statuses)
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "status": status, "ok": ok,
                         "certificates": cert[:3], "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {str(status):9} {label}  {cert[:1]}", flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ABCDEFGH"
    sys.exit(1 if main(out, grp) else 0)
