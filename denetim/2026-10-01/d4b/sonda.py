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
NOTREF = {"verified", "unknown", "skipped"}

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
        ("eval x | sin=0, 3<x<7: pi", ev("x", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("pi"), UNK, None),
        ("eval x | sin=0, 3<x<7: 2pi", ev("x", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("2*pi"), UNK, None),
        ("eval x | sin=0, 4<x<7: 2pi", ev("x", ["sin(x) = 0", "x > 4", "x < 7"]), _sol("2*pi"), NOTNO, None),
        ("eval x | tan=1, 0<x<4: pi/4", ev("x", ["tan(x) = 1", "x > 0", "x < 4"]), _sol("pi/4"), UNK, None),
        ("eval x | tan=1, 0<x<4: 5pi/4", ev("x", ["tan(x) = 1", "x > 0", "x < 4"]), _sol("5*pi/4"), UNK, None),
        ("eval x | cos=1, 1<x<13: 2pi", ev("x", ["cos(x) = 1", "x > 1", "x < 13"]), _sol("2*pi"), UNK, None),
        ("eval x | cos=0, 0<x<5: pi/2", ev("x", ["cos(x) = 0", "x > 0", "x < 5"]), _sol("pi/2"), UNK, None),
        ("eval x | sin=1/2, 0<x<3: pi/6", ev("x", ["sin(x) = 1/2", "x > 0", "x < 3"]), _sol("pi/6"), UNK, None),
        ("eval x | sin=1/2, 2<x<3: 5pi/6", ev("x", ["sin(x) = 1/2", "x > 2", "x < 3"]), _sol("5*pi/6"), NOTNO, None),
        ("eval x | sin=1/2, 6<x<7: 13pi/6", ev("x", ["sin(x) = 1/2", "x > 6", "x < 7"]), _sol("13*pi/6"), NOTNO, None),
        ("eval x**2 | sin=0, 3<x<7: pi^2", ev("x**2", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("pi**2"), UNK, None),
        ("eval cos x | sin=0, 3<x<7: -1", ev("cos(x)", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("-1"), UNK, None),
        ("eval cos x | sin=0, 3<x<7: 1", ev("cos(x)", ["sin(x) = 0", "x > 3", "x < 7"]), _sol("1"), UNK, None),
        ("eval cos x | sin=0 cons 3<x<7: -1", ev("cos(x)", ["sin(x) = 0"], [V("x", "real", ["x > 3", "x < 7"])]), _sol("-1"), UNK, None),
        ("eval x | sin=0 dod (3,7): pi", ev("x", ["sin(x) = 0"], dod="(3, 7)"), _sol("pi"), UNK, None),
        ("eval x | sin(pi x)=0, 0<x<3: 1", ev("x", ["sin(pi*x) = 0", "x > 0", "x < 3"]), _sol("1"), UNK, None),
        ("eval x^2 | sin(pi x)=0, 0<x<3: 1", ev("x**2", ["sin(pi*x) = 0", "x > 0", "x < 3"]), _sol("1"), UNK, None),
        ("eval sin x | tan=1: sqrt2/2", ev("sin(x)", ["tan(x) = 1"]), _sol("sqrt(2)/2"), UNK, None),
        ("eval sin x | tan=1: -sqrt2/2", ev("sin(x)", ["tan(x) = 1"]), _sol("-sqrt(2)/2"), UNK, None),
        ("eval sin x | cos=1/2, 4<x<8: -sqrt3/2", ev("sin(x)", ["cos(x) = 1/2", "x > 4", "x < 8"]), _sol("-sqrt(3)/2"), UNK, None),
        ("eval x | cos 2x=1, 1<x<7: pi", ev("x", ["cos(2*x) = 1", "x > 1", "x < 7"]), _sol("pi"), UNK, None),
        ("eval sin x | sin^2=1/4, 3<x<7: -1/2", ev("sin(x)", ["sin(x)**2 = 1/4", "x > 3", "x < 7"]), _sol("-1/2"), UNK, None),
        ("eval x | x*exp(x)=-1/5: W0", ev("x", ["x*exp(x) = -1/5"]), _sol("LambertW(-1/5)"), UNK, None),
        ("eval x | 2^x=x^2, x>0: 2", ev("x", ["2**x = x**2", "x > 0"]), _sol("2"), UNK, None),
        ("eval x | sin x = x/2, x>0", ev("x", ["sin(x) = x/2", "x > 0"]), _sol("1.895494267"), NOTOK, None),
        ("eval x | Abs(x-1)=2: 3", ev("x", ["Abs(x - 1) = 2"]), _sol("3"), UNK, None),
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
        ("B4 eval x | (x+1)Q=0, 0<x<4: pi/3", ev("x", [f"(x + 1)*{Q} = 0", "x > 0", "x < 4"]), _sol("pi/3"), UNK, None),
        ("B4 eval x | Q^3=0, 0<x<4: pi/3", ev("x", [f"{Q}**3 = 0", "x > 0", "x < 4"]), _sol("pi/3"), UNK, None),
        ("B4 eval x | exp(x)=3x: W0", ev("x", ["exp(x) = 3*x"]), _sol("-LambertW(-1/3)"), UNK, None),
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
        ("F4 edge base 1: eval x | 1**x=1: 0", ev("x", ["1**x = 1"]), _sol("0"), UNK, None),
        ("F4 3^x=2^x: {0} (class vii since round 5)", eq("3**x = 2**x"), _sol("{0}", S_), OK, None),
        ("F4 out of class eval exp(x)=3x, x<1: W0", ev("x", ["exp(x) = 3*x", "x < 1"]), _sol("-LambertW(-1/3)"), NOTNO, None),
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
        ("F5 eval sin=cos, 0<x<4: pi/4", ev("x", ["sin(x) = cos(x)", "x > 0", "x < 4"]), _sol("pi/4"), UNK, None),
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
        ("FS eval x | x+y=5, xy=6: 3", ev("x", ["x + y = 5", "x*y = 6"], [X, Y]), _sol("3"), UNK, None),
        ("FS eval x | x^2=y, y^2=x, x>0: 1", ev("x", ["x**2 = y", "y**2 = x", "x > 0"], [X, Y]), _sol("1"), OK, None),
        ("FS eval x+y | 1/x+1/y=1, xy=4: 4", ev("x + y", ["1/x + 1/y = 1", "x*y = 4"], [X, Y]), _sol("4"), OK, None),
        ("FS eval x+y | x^2+y^2=2, xy=1: 2", ev("x + y", ["x**2 + y**2 = 2", "x*y = 1"], [X, Y]), _sol("2"), UNK, None),
        ("FS eval x+y | xy=1 (a curve): 2", ev("x + y", ["x*y = 1"], [X, Y]), _sol("2"), UNK, None),
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
        ("G0 eval x | exp(x)+x=1: 0", ev("x", ["exp(x) + x = 1"]), _sol("0"), NOTNO, None),
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
        ("H1 eval x | sqrt(log^2)=1, x>0: E", ev("x", ["sqrt(log(x)**2) = 1", "x > 0"]), _sol("E"), UNK, None),
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
        ("H4 croots x^(1/3)-x: 3", croots("x**(1/3) - x"), _sol("3", "count"), UNK, None),
        # controls
        ("H5 ctl eq |2x-3|=5: {-1,4}", eq("Abs(2*x - 3) = 5"), _sol("{-1, 4}", S_), OK, None),
        ("H5 ctl eq Max(x,2)=3: {3}", eq("Max(x, 2) = 3"), _sol("{3}", S_), OK, None),
        ("H5 ctl eq Min(x,2)=2: [2,oo)", eq("Min(x, 2) = 2"), _sol("{2}", S_), NO, None),
        ("H5 ctl eq |sinh x|=1", eq("Abs(sinh(x)) = 1"), _sol("{log(1 + sqrt(2)), -log(1 + sqrt(2))}", S_), OK, None),
    ]


L8 = "log(8)/log(2)"           # = 3 exactly (log 8 = 3 log 2)


def cases_i():
    """Round 6 (6 Oct 2026): one interval end written two ways (the solved set's 3, the given's log(8)/log(2));
    SymPy's Intersection raised TypeError and the certificate died. CORRECT/INCORRECT come back only where the
    two are PROVED equal."""
    XA = (X, V("a"))
    return [
        ("I1 eq x^2=4, x>L8: {}", eq("x**2 = 4", [f"x > {L8}"]), _sol("{}", S_), OK, None),
        ("I1 eq x^2=4, x>L8: {2}", eq("x**2 = 4", [f"x > {L8}"]), _sol("{2}", S_), NO, None),
        ("I1 eq x^2=9, x>=L8: {3}", eq("x**2 = 9", [f"x >= {L8}"]), _sol("{3}", S_), OK, None),
        ("I1 eq x^2=9, x>=L8: {-3,3}", eq("x**2 = 9", [f"x >= {L8}"]), _sol("{-3, 3}", S_), NO, None),
        ("I1 eq x^2=9, x>L8: {3}", eq("x**2 = 9", [f"x > {L8}"]), _sol("{3}", S_), NO, None),
        ("I1 eq x^2=9, x>L8: {}", eq("x**2 = 9", [f"x > {L8}"]), _sol("{}", S_), OK, None),
        ("I2 eq x^2=4, x>a, a=L8: {}", eq("x**2 = 4", ["x > a", f"a = {L8}"], XA), _sol("{}", S_), OK, None),
        ("I2 eq x^2=4, x>a, a=L8 (a=3 kısıt): {}",
         eq("x**2 = 4", ["x > a", f"a = {L8}"], (X, V("a", cons=["a = 3"]))), _sol("{}", S_), OK, None),
        ("I2 eq x^2=9, x>=a, a=L8: {3}", eq("x**2 = 9", ["x >= a", f"a = {L8}"], XA), _sol("{3}", S_), OK, None),
        ("I3 eq log(x-L8)=0: {4}", eq(f"log(x - {L8}) = 0", [f"x > {L8}"]), _sol("{4}", S_), OK, None),
        ("I3 eq sqrt(x-L8)=1: {4}", eq(f"sqrt(x - {L8}) = 1", [f"x >= {L8}"]), _sol("{4}", S_), OK, None),
        # 3 is no root (sqrt(0) = 0), but the radicand 3 - log(8)/log(2) is an exact 0 the root check does not
        # decide (claimed_root_undecided; the same at 76d0c87): anything but a false acceptance
        ("I3 eq sqrt(x-L8)=1: {3,4}", eq(f"sqrt(x - {L8}) = 1", [f"x >= {L8}"]), _sol("{3, 4}", S_), NOTOK, None),
        # a tiny difference is no equality: 3 + e^(-e^10) is not 3, nothing is written one way
        ("I4 eq x^2=9, x>L8+e^-e^10: {3}", eq("x**2 = 9", [f"x > {L8} + exp(-exp(10))"]), _sol("{3}", S_), NOTOK, None),
        ("I4 eq x^2=9, x>L8-e^-e^10: {}", eq("x**2 = 9", [f"x > {L8} - exp(-exp(10))"]), _sol("{}", S_), NOTOK, None),
        ("I4 eq x^2=9, x>L8-e^-e^10: {3}", eq("x**2 = 9", [f"x > {L8} - exp(-exp(10))"]), _sol("{3}", S_), NOTNO, None),
        ("I5 ctl eq x^2=9, x>=3: {3}", eq("x**2 = 9", ["x >= 3"]), _sol("{3}", S_), OK, None),
    ]


def cases_j():
    """Round 7 (6 Oct 2026), the review of round 6: a cell dropped whole for its midpoint (YO-1, RK1), a folded
    cell with a written odd root (YO-2), a Python 0 for a measure (RK2), a one-sided domain solved on the whole
    line (RK3), a denominator with Abs/sign in it (RK4), two writings of one endpoint in the sampler (RK6)."""
    XP = V("x", "positive_real")
    XI = V("x", "integer")
    R = "Abs(x**2 - 4*x)*log(x - 2) = 0"
    C = "(Abs(x) + Abs(x - 10) - 10)*log(x - 6) = 0"
    I_ = "interval"
    return [
        # YO-1 / RK1
        ("J1 croots |x|ln(x-1): 1", croots("Abs(x)*log(x - 1)"), _sol("1", "count"), OK, None),
        ("J1 croots |x|ln(x-1): 0", croots("Abs(x)*log(x - 1)"), _sol("0", "count"), NO, None),
        ("J1 croots sqrt(x-2)+|x|-4: 1", croots("sqrt(x - 2) + Abs(x) - 4"), _sol("1", "count"), OK, None),
        ("J1 croots sqrt(x-2)+|x|-4: 0", croots("sqrt(x - 2) + Abs(x) - 4"), _sol("0", "count"), NO, None),
        ("J1 croots |x+10|ln x: 1", croots("Abs(x + 10)*log(x)"), _sol("1", "count"), OK, None),
        ("J1 croots |x|sqrt(x-3): 1", croots("Abs(x)*sqrt(x - 3)"), _sol("1", "count"), OK, None),
        ("J1 eq x^2=9 | |x|ln(x-1)>=0: {3}", eq("x**2 = 9", ["Abs(x)*log(x - 1) >= 0"]), _sol("{3}", S_), OK, None),
        ("J1 eq x^2=9 | |x|ln(x-1)>=0: {}", eq("x**2 = 9", ["Abs(x)*log(x - 1) >= 0"]), _sol("{}", S_), NO, None),
        ("J1 eq x^2=9 | Max(x,0)ln(x-1)>=0: {}", eq("x**2 = 9", ["Max(x, 0)*log(x - 1) >= 0"]), _sol("{}", S_), NO, None),
        ("J1 eq x^2=1 | |x+10|ln x=0: {1}", eq("x**2 = 1", ["Abs(x + 10)*log(x) = 0"]), _sol("{1}", S_), OK, None),
        ("J1 eval x^2 | R: 16", ev("x**2", [R]), _sol("16"), UNK, None),
        ("J1 eval x^2 | R: 9", ev("x**2", [R]), _sol("9"), UNK, None),
        ("J1 step x^2-7x+12=0 | R => x=4", eq("x**2 - 7*x + 12 = 0", [R]), _sol("{3, 4}", S_, steps=[("eq", "x = 4")]),
         NOTNO | NO, NOTVER),
        ("J1 eq R: {3,4}", eq(R), _sol("{3, 4}", S_), OK, None),
        ("J1 eq R: {4}", eq(R), _sol("{4}", S_), NO, None),
        ("J1 eq |x|+ln(x^2-1)=0: {}", eq("Abs(x) + log(x**2 - 1) = 0"), _sol("{}", S_), NOTOK, None),
        ("J1 eq (|x|-x)ln(x-1)=0: (1,oo)", eq("(Abs(x) - x)*log(x - 1) = 0"), _sol("Interval.open(1, oo)", I_), NOTNO, None),
        ("J1 eq (|x|-x)ln(x-1)=0: {}", eq("(Abs(x) - x)*log(x - 1) = 0"), _sol("{}", S_), NO, None),
        ("J1 cint |x|ln(x-1)>0 [-5,5]: 3", cint(["Abs(x)*log(x - 1) > 0", "x >= -5", "x <= 5"], [XI]), _sol("3", "count"), OK, None),
        ("J1 cint |x|ln(x-1)>0 [-5,5]: 0", cint(["Abs(x)*log(x - 1) > 0", "x >= -5", "x <= 5"], [XI]), _sol("0", "count"), NO, None),
        ("J1 trig |x||x+5|ln(sin x)=0 [-5,0]: {-5}", trig(["Abs(x)*Abs(x + 5)*log(sin(x)) = 0"], "[-5, 0]"),
         _sol("{-5}", S_), NOTOK, None),
        ("J2 croots |x|-sqrt(2x+1): 2", croots("Abs(x) - sqrt(2*x + 1)"), _sol("2", "count"), OK, None),
        ("J2 croots |x|-sqrt(2x+1): 1", croots("Abs(x) - sqrt(2*x + 1)"), _sol("1", "count"), NO, None),
        ("J2 croots (|x-3|-1/2)ln(x-2): 3", croots("(Abs(x - 3) - 1/2)*log(x - 2)"), _sol("3", "count"), OK, None),
        ("J2 croots (|x-3|-1/2)ln(x-2): 2", croots("(Abs(x - 3) - 1/2)*log(x - 2)"), _sol("2", "count"), NO, None),
        ("J2 ineq |x-2|ln(x-1)<0: (1,2)", ineq("Abs(x - 2)*log(x - 1) < 0"), _sol("Interval.open(1, 2)", I_), OK, None),
        ("J2 eval x | |x|=sqrt(2x+1), x<0: 1-sqrt2", ev("x", ["Abs(x) = sqrt(2*x + 1)", "x < 0"]), _sol("1 - sqrt(2)"), OK, None),
        ("J2 eval x | |x|=sqrt(2x+1): 1-sqrt2", ev("x", ["Abs(x) = sqrt(2*x + 1)"]), _sol("1 - sqrt(2)"), UNK, None),
        ("J2 cint C: 4", cint([C], [XI]), _sol("4", "count"), OK, None),
        ("J2 cint C: 1", cint([C], [XI]), _sol("1", "count"), NO, None),
        ("J2 eq C: {10}", eq(C), _sol("{10}", S_), NO, None),
        ("J2 croots C: 1", croots(C.replace(" = 0", "")), _sol("1", "count"), NOTOK, None),
        # YO-2: the reading of a written odd root decides
        ("J3 eq (x+|x|)x^(1/3)=0: {0}", eq("(x + Abs(x))*x**(1/3) = 0"), _sol("{0}", S_), UNK, None),
        ("J3 eq (x+|x|)x^(1/3)=0: (-oo,0]", eq("(x + Abs(x))*x**(1/3) = 0"), _sol("Interval(-oo, 0)", I_), UNK, None),
        ("J3 eq Max(x,0)x^(1/3)=0: {0}", eq("Max(x, 0)*x**(1/3) = 0"), _sol("{0}", S_), UNK, None),
        ("J3 cint Max(x,0)x^(1/3)=0 [-5,5]: 6", cint(["Max(x, 0)*x**(1/3) = 0", "x >= -5", "x <= 5"], [XI]),
         _sol("6", "count"), UNK, None),
        # RK2
        ("J4 eq |x-3|=3-x, x>=3: {3}", eq("Abs(x - 3) = 3 - x", ["x >= 3"]), _sol("{3}", S_), OK, None),
        ("J4 eq |x|=x, x<=0: {0}", eq("Abs(x) = x", ["x <= 0"]), _sol("{0}", S_), OK, None),
        ("J4 eq |x|=-x, x>=0: {0}", eq("Abs(x) = -x", ["x >= 0"]), _sol("{0}", S_), OK, None),
        ("J4 eq Max(x,2)=2, x>=2: {2}", eq("Max(x, 2) = 2", ["x >= 2"]), _sol("{2}", S_), OK, None),
        ("J4 eq |x-1|+|x+1|=2, x>=1: {1}", eq("Abs(x - 1) + Abs(x + 1) = 2", ["x >= 1"]), _sol("{1}", S_), OK, None),
        ("J4 eq |x-1|+|x+1|=2, x>1: {}", eq("Abs(x - 1) + Abs(x + 1) = 2", ["x > 1"]), _sol("{}", S_), NOTNO, None),
        ("J4 eq |x-3|=3-x, x>=3: {}", eq("Abs(x - 3) = 3 - x", ["x >= 3"]), _sol("{}", S_), NO, None),
        ("J4 eq Max(log x,0)=0 int x>=-5: {1}", eq("Max(log(x), 0) = 0", ["x >= -5"], [XI]), _sol("{1}", S_), OK, None),
        # RK3
        ("J5 ineq pos x^(1/3)<1: (0,1)", ineq("x**(1/3) < 1", vars_=(XP,)), _sol("Interval.open(0, 1)", I_), OK, None),
        ("J5 ineq pos x^(1/3)>=2: [8,oo)", ineq("x**(1/3) >= 2", vars_=(XP,)), _sol("Interval(8, oo)", I_), OK, None),
        ("J5 ineq pos x^(2/3)<=4: (0,8]", ineq("x**(2/3) <= 4", vars_=(XP,)), _sol("Interval.Lopen(0, 8)", I_), OK, None),
        ("J5 ineq pos x^(1/3)<x: (1,oo)", ineq("x**(1/3) < x", vars_=(XP,)), _sol("Interval.open(1, oo)", I_), OK, None),
        ("J5 ineq pos x^(1/3)<1: (0,2)", ineq("x**(1/3) < 1", vars_=(XP,)), _sol("Interval.open(0, 2)", I_), NO, None),
        ("J5 cint posint x^(1/3)<2: 7", cint(["x**(1/3) < 2"], [V("x", "positive_integer")]), _sol("7", "count"), OK, None),
        ("J5 cint posint x^(1/3)<2: 8", cint(["x**(1/3) < 2"], [V("x", "positive_integer")]), _sol("8", "count"), NO, None),
        ("J5 domof pos log(2-x^(1/3)): (0,8)", domof("log(2 - x**(1/3))", vars_=(XP,)), _sol("Interval.open(0, 8)", I_), OK, None),
        ("J5 ineq real x^(1/3)<1: (0,1)", ineq("x**(1/3) < 1"), _sol("Interval.open(0, 1)", I_), NOTOK, None),
        ("J5 ineq real x^(1/3)<1: (-oo,1)", ineq("x**(1/3) < 1"), _sol("Interval.open(-oo, 1)", I_), UNK, None),
        # RK4
        ("J6 croots x/sign(x)-2: 2", croots("x/sign(x) - 2"), _sol("2", "count"), OK, None),
        ("J6 croots 1/(x-|x|)+1/2: 1", croots("1/(x - Abs(x)) + 1/2"), _sol("1", "count"), OK, None),
        ("J6 eq x/sign(x)=2: {-2,2}", eq("x/sign(x) = 2"), _sol("{-2, 2}", S_), OK, None),
        ("J6 eq x/sign(x)=0: {0}", eq("x/sign(x) = 0"), _sol("{0}", S_), NO, None),
        ("J6 eq x/|x|=1: [0,oo)", eq("x/Abs(x) = 1"), _sol("Interval(0, oo)", I_), NOTOK, None),   # an infinite claim: H3
        ("J6 eq 1/(x+|x|)=1/4: {2}", eq("1/(x + Abs(x)) = 1/4"), _sol("{2}", S_), OK, None),
        ("J6 eq (x-1)/(|x|-1)=1: [0,1)U(1,oo)", eq("(x - 1)/(Abs(x) - 1) = 1"),
         _sol("Union(Interval.Ropen(0, 1), Interval.open(1, oo))", I_), NOTNO, None),
        ("J6 eq (x-1)/(|x|-1)=1: [0,oo)", eq("(x - 1)/(Abs(x) - 1) = 1"), _sol("Interval(0, oo)", I_), NOTOK, None),
        # RK6
        ("J7 ineq x^2<16, x>L8: (3,4)", ineq("x**2 < 16", ["x > log(8)/log(2)"]), _sol("Interval.open(3, 4)", I_), OK, None),
        ("J7 ineq x^2<16, x>L8: (3,4]", ineq("x**2 < 16", ["x > log(8)/log(2)"]), _sol("Interval.Lopen(3, 4)", I_), NO, None),
        # controls
        ("J8 ctl eq |2x-3|=5: {-1,4}", eq("Abs(2*x - 3) = 5"), _sol("{-1, 4}", S_), OK, None),
        ("J8 ctl eq log(|x|-1)=0: {-2,2}", eq("log(Abs(x) - 1) = 0"), _sol("{-2, 2}", S_), OK, None),
        ("J8 ctl eq cbrt(x)=x: {-1,0,1}", eq("cbrt(x) = x"), _sol("{-1, 0, 1}", S_), OK, None),
    ]


def cases_k():
    """Round 8 (7 Oct 2026), the review of round 7: a folded cell kept the points where acos, asin, atan2, arg
    are not real (YO-1); a one-sided domain whose end is a cut written another way (RK-1, RK-3); the
    convention of an odd root read where the expression is undefined anyway (RK-2); two writings of one
    endpoint ordered by rounding in the sampler (RK-4)."""
    X0 = V("x", "real", ["x >= 0"])
    I_ = "interval"
    R2 = "sqrt(3 + 2*sqrt(2))"

    def trig_w(eqn, interval):
        return _ir("trig_solve", {"var": "x", "interval": interval}, (X,), [eqn], "set")
    return [
        # YO-1
        ("K1 ineq x>=0 (|x|-x)acos(2^x+x-2)<=0: [0,oo)", ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), NOTOK, None),
        ("K1 ineq given x>=0 (|x|-x)acos(2^x+x-2)<=0: [0,oo)", ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", ["x >= 0"]),
         _sol("Interval(0, oo)", I_), NOTOK, None),
        ("K1 ineq dod x>=0 (|x|-x)acos(..)<=0: [0,oo)",
         _ir("solve_inequality", {"inequality": "(Abs(x) - x)*acos(2**x + x - 2) <= 0", "var": "x"}, (X,), (), "set",
             "x >= 0"), _sol("Interval(0, oo)", I_), NOTOK, None),
        ("K1 ineq x>=0 (|x|-x)acos(2^x+x-2)<=0: [0,1]", ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", vars_=(X0,)),
         _sol("Interval(0, 1)", I_), NOTNO, None),
        ("K1 ineq x>=0 (|x|-x)asin(x+atan x)<=0: [0,oo)", ineq("(Abs(x) - x)*asin(x + atan(x)) <= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), NOTOK, None),
        ("K1 ineq x>=0 (Max(x,0)-x)asin(..)<=0: [0,oo)", ineq("(Max(x, 0) - x)*asin(x + atan(x)) <= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), NOTOK, None),
        ("K1 ineq x>=0 (|x|-x)acos(x e^x)<=0: [0,oo)", ineq("(Abs(x) - x)*acos(x*exp(x)) <= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), NOTOK, None),
        ("K1 ineq x<=0 (|x|+x)asin(..)>=0: (-oo,0]", ineq("(Abs(x) + x)*asin(x + atan(x)) >= 0", vars_=(V("x", "real", ["x <= 0"]),)),
         _sol("Interval(-oo, 0)", I_), NOTOK, None),
        ("K1 ineq x>=0 (|x|-x)atan2(x-1,0)>=0: [0,oo)", ineq("(Abs(x) - x)*atan2(x - 1, 0) >= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), UNK, None),
        ("K1 ineq x>=0 (|x|-x)arg(x-1)>=0: [0,oo)", ineq("(Abs(x) - x)*arg(x - 1) >= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), UNK, None),
        ("K1 ineq x>=0 (|x|-x)arg(x-1)>=0: [0,1)U(1,oo)", ineq("(Abs(x) - x)*arg(x - 1) >= 0", vars_=(X0,)),
         _sol("Union(Interval.Ropen(0, 1), Interval.open(1, oo))", I_), UNK, None),
        ("K1 ctl ineq x>=0 (|x|-x)acos(x/2)<=0: [0,oo)", ineq("(Abs(x) - x)*acos(x/2) <= 0", vars_=(X0,)),
         _sol("Interval(0, oo)", I_), NO, None),
        ("K1 ctl ineq x>=0 (|x|-x)acos(x/2)<=0: [0,2]", ineq("(Abs(x) - x)*acos(x/2) <= 0", vars_=(X0,)),
         _sol("Interval(0, 2)", I_), OK, None),
        ("K1 cint (|x|-x)acos(x/2)>=0 [0,5]: 3", cint(["(Abs(x) - x)*acos(x/2) >= 0", "x >= 0", "x <= 5"], [V("x", "integer")]),
         _sol("3", "count"), NOTNO, None),
        ("K1 cint (|x|-x)acos(x/2)>=0 [0,5]: 6", cint(["(Abs(x) - x)*acos(x/2) >= 0", "x >= 0", "x <= 5"], [V("x", "integer")]),
         _sol("6", "count"), NOTOK, None),
        # RK-1
        ("K2 ineq sign(x-3)>0, x<=L8: {}", ineq("sign(x - 3) > 0", ["x <= log(8)/log(2)"]), _sol("EmptySet", S_), NOTNO, None),
        ("K2 ineq sign(x-3)>0, x<=L8: {L8}", ineq("sign(x - 3) > 0", ["x <= log(8)/log(2)"]), _sol("{log(8)/log(2)}", S_),
         NOTOK, None),
        ("K2 ineq sign(x-2)>0, x<=L9: {}", ineq("sign(x - 2) > 0", ["x <= log(9)/log(3)"]), _sol("EmptySet", S_), NOTNO, None),
        ("K2 ineq sign(3-x)>0, x>=L8: {}", ineq("sign(3 - x) > 0", ["x >= log(8)/log(2)"]), _sol("EmptySet", S_), NOTNO, None),
        ("K2 ineq sign(x-log4)>0: (log4,oo)", ineq("sign(x - log(4)) > 0"), _sol("Interval.open(log(4), oo)", I_), NOTNO, None),
        ("K2 ineq sign(x-3)>0, -5<=x<=L8: {L8}", ineq("sign(x - 3) > 0", ["x >= -5", "x <= log(8)/log(2)"]),
         _sol("{log(8)/log(2)}", S_), NOTOK, None),
        # RK-2
        ("K3 trig sin|x|sqrt(x)(x^(1/3)-2)=0 [-1,10]", trig_w("sin(x)*Abs(x)*sqrt(x)*(x**(1/3) - 2) = 0", "[-1, 10]"),
         _sol("{0, pi, 2*pi, 3*pi, 8}", S_), OK, None),
        ("K3 trig same, 8 missing", trig_w("sin(x)*Abs(x)*sqrt(x)*(x**(1/3) - 2) = 0", "[-1, 10]"),
         _sol("{0, pi, 2*pi, 3*pi}", S_), NO, None),
        ("K3 trig sin|x-1|log x(x^(1/3)-1)=0 [-2,7]", trig_w("sin(x)*Abs(x - 1)*log(x)*(x**(1/3) - 1) = 0", "[-2, 7]"),
         _sol("{1, pi, 2*pi}", S_), OK, None),
        ("K3 trig same, -1 added", trig_w("sin(x)*Abs(x - 1)*log(x)*(x**(1/3) - 1) = 0", "[-2, 7]"),
         _sol("{-1, 1, pi, 2*pi}", S_), NO, None),
        ("K3 trig cos Max(x,1)sqrt(x-1)(x^(1/3)-2)=0 [-3,9]",
         trig_w("cos(x)*Max(x, 1)*sqrt(x - 1)*(x**(1/3) - 2) = 0", "[-3, 9]"), _sol("{1, pi/2, 3*pi/2, 5*pi/2, 8}", S_), OK, None),
        ("K3 trig same, -pi/2 added", trig_w("cos(x)*Max(x, 1)*sqrt(x - 1)*(x**(1/3) - 2) = 0", "[-3, 9]"),
         _sol("{-pi/2, 1, pi/2, 3*pi/2, 5*pi/2, 8}", S_), NO, None),
        ("K3 eq |x|sqrt(x+8)(x^(1/3)+1)=0: {-8,-1,0}", eq("Abs(x)*sqrt(x + 8)*(x**(1/3) + 1) = 0"), _sol("{-8, -1, 0}", S_), UNK, None),
        # RK-3
        ("K4 ineq |x-3|<1, x>L8: (L8,4)", ineq("Abs(x - 3) < 1", ["x > log(8)/log(2)"]),
         _sol("Interval.open(log(8)/log(2), 4)", I_), OK, None),
        ("K4 ineq |x-3|<=1, x>=L8: [L8,4]", ineq("Abs(x - 3) <= 1", ["x >= log(8)/log(2)"]),
         _sol("Interval(log(8)/log(2), 4)", I_), OK, None),
        ("K4 ineq |x-3|>1, x>L8: (4,oo)", ineq("Abs(x - 3) > 1", ["x > log(8)/log(2)"]), _sol("Interval.open(4, oo)", I_), OK, None),
        ("K4 ineq |x-3|<1, x>L8: [3,4)", ineq("Abs(x - 3) < 1", ["x > log(8)/log(2)"]), _sol("Interval.Ropen(3, 4)", I_), NO, None),
        ("K4 ineq sqrt(x-3)<1, x>L8: (3,4)", ineq("sqrt(x - 3) < 1", ["x > log(8)/log(2)"]), _sol("Interval.open(3, 4)", I_), OK, None),
        # RK-4
        ("K5 ineq |x-1-sqrt2|<1, x>R2: (1+sqrt2,2+sqrt2)", ineq("Abs(x - 1 - sqrt(2)) < 1", [f"x > {R2}"]),
         _sol("Interval.open(1 + sqrt(2), 2 + sqrt(2))", I_), NOTNO, None),
        ("K5 ineq x^2<16, x>R2: (1+sqrt2,4)", ineq("x**2 < 16", [f"x > {R2}"]), _sol("Interval.open(1 + sqrt(2), 4)", I_), NOTNO, None),
        ("K5 ineq x<5, x>=sqrt(5+2sqrt6): [s2+s3,5)", ineq("x < 5", ["x >= sqrt(5 + 2*sqrt(6))"]),
         _sol("Interval.Ropen(sqrt(2) + sqrt(3), 5)", I_), NOTNO, None),
        ("K5 ineq x^2<16, x>R2: (1+sqrt2,5)", ineq("x**2 < 16", [f"x > {R2}"]), _sol("Interval.open(1 + sqrt(2), 5)", I_), NO, None),
    ]


def cases_l():
    """Round 9 (8 Oct 2026), the review of round 8: a declared constraint dropped by an intersection that raised
    (YO-1), a jump function of an unprovable zero read off rounding noise (YO-4), a cell's zero written another way
    (RK-1), the sampler blind where an unsolved written condition fails (RK-2), 300 points and more (RK-3), factorial
    and Mod on a finite domain (RK-4), the origin convention of atan2/arg under givens (RK-5), a sampling time set
    by PYTHONHASHSEED (RK-6); SymPy's unbounded evaluation precision (one verify ran past 90 s)."""
    I_ = "interval"
    NEAR = "log(8)/log(2) + exp(-exp(10))"          # 3 + e^(-e^10), certified > 3 one way only
    NEAR2 = "log(9)/log(3) + exp(-exp(9))"
    FAR = "3 + 2*atan(tanh(1/2)) - atan(sinh(1))"     # exactly 3, no exact test proves it
    HUGE = "log(8)/log(2) + exp(-exp(exp(5)))"       # 3 + e^(-e^148): ~4e64 bits to separate from 3
    Z = "2*atan(tanh(1/2)) - atan(sinh(1))"          # exactly 0 (gd(1) twice)
    cs = (V("x", "real", [f"x <= {NEAR}", "x >= 3"]),)
    cr = (V("x", "real", ["x >= 3", f"x <= {NEAR}"]),)
    cs2 = (V("x", "real", [f"x <= {NEAR2}", "x >= 2"]),)
    cf = (V("x", "real", [f"x <= {FAR}", "x >= 3"]),)
    cfr = (V("x", "real", ["x >= 3", f"x <= {FAR}"]),)
    ch = (V("x", "real", [f"x <= {HUGE}", "x >= 3"]),)
    X0 = V("x", "real", ["x >= 0"])
    XY = (X, V("y", "real"))
    D6 = "{1, 2, 3, 4, 5, 6}"

    def cr_(e, lo, hi):
        return _ir("count_roots", {"expr": e, "var": "x", "lo": lo, "hi": hi}, (X,), (), "count")

    def trig4(vars_):
        return _ir("trig_solve", {"var": "x", "interval": "[-4, 4]"}, vars_, ["sin(x) = 0"], "set")
    out = []
    for tag, vs in (("", cs), (" rev", cr)):
        out += [
            (f"L1 ineq x<5 | x<=NEAR,x>=3{tag}: (-oo,NEAR]", ineq("x < 5", vars_=vs), _sol(f"Interval(-oo, {NEAR})", I_), NOTOK,
             None),
            (f"L1 ineq x<5 | x<=NEAR,x>=3{tag}: [3,NEAR]", ineq("x < 5", vars_=vs), _sol(f"Interval(3, {NEAR})", I_), NOTNO, None),
            (f"L1 eq x^2=4 | x<=NEAR,x>=3{tag}: {{-2,2}}", eq("x**2 = 4", vars_=vs), _sol("{-2, 2}", S_), NOTOK, None),
            (f"L1 eq x^2=4 | x<=NEAR,x>=3{tag}: {{}}", eq("x**2 = 4", vars_=vs), _sol("EmptySet", S_), NOTNO, None),
            (f"L1 ext max -x^2 | x<=NEAR,x>=3{tag}: 0", ext("-x**2", "max", vars_=vs), _sol("0"), NOTOK, None),
            (f"L1 ext max -x^2 | x<=NEAR,x>=3{tag}: -9", ext("-x**2", "max", vars_=vs), _sol("-9"), NOTNO, None),
            (f"L1 domof sqrt x | x<=NEAR,x>=3{tag}: [0,NEAR]", domof("sqrt(x)", vars_=vs), _sol(f"Interval(0, {NEAR})", I_),
             NOTOK, None),
            (f"L1 croots x^2-4 | x<=NEAR,x>=3{tag}: 2", croots("x**2 - 4", vars_=vs), _sol("2", "count"), NOTOK, None),
            (f"L1 croots x^2-4 | x<=NEAR,x>=3{tag}: 0", croots("x**2 - 4", vars_=vs), _sol("0", "count"), NOTNO, None),
            (f"L1 trig sin x=0 [-4,4] | x<=NEAR,x>=3{tag}: {{-pi,0}}", trig4(vs), _sol("{-pi, 0}", S_), NOTOK, None),
            (f"L1 trig sin x=0 [-4,4] | x<=NEAR,x>=3{tag}: {{}}", trig4(vs), _sol("EmptySet", S_), NOTNO, None),
        ]
    out += [
        ("L1 eq x^2=4 | x<=NEAR2,x>=2: {-2,2}", eq("x**2 = 4", vars_=cs2), _sol("{-2, 2}", S_), NOTOK, None),
        ("L1 eq x^2=4 | x<=NEAR2,x>=2: {2}", eq("x**2 = 4", vars_=cs2), _sol("{2}", S_), NOTNO, None),
        ("L1 eq x^2=9 | x<=FAR,x>=3: {-3,3}", eq("x**2 = 9", vars_=cf), _sol("{-3, 3}", S_), NOTOK, None),
        ("L1 eq x^2=9 | x<=FAR,x>=3: {3}", eq("x**2 = 9", vars_=cf), _sol("{3}", S_), NOTNO, None),
        ("L1 eq x^2=9 | x>=3,x<=FAR: {-3,3}", eq("x**2 = 9", vars_=cfr), _sol("{-3, 3}", S_), NOTOK, None),
        ("L1 ext max -x^2 | x>=3,x<=FAR: 0", ext("-x**2", "max", vars_=cfr), _sol("0"), NOTOK, None),
        # the evaluation precision budget: these ran past 90 s in the main process
        ("L1 eq x^2=4 | x<=HUGE,x>=3: {-2,2}", eq("x**2 = 4", vars_=ch), _sol("{-2, 2}", S_), NOTOK, None),
        ("L1 eq x^2=4 | x<=HUGE,x>=3: {}", eq("x**2 = 4", vars_=ch), _sol("EmptySet", S_), NOTNO, None),
        ("L1 ev HUGE: 3", ev(HUGE, []), _sol("3"), NOTOK, None),
        ("L1 ev log8/log2: HUGE", ev("log(8)/log(2)", []), _sol(HUGE), NOTOK, None),
        ("L1 ctl ev log8/log2+exp(-exp(10)): 3", ev(NEAR, []), _sol("3"), NO, None),
        # YO-4
        ("L2 ev ceiling(Z^2): 1", ev(f"ceiling(({Z})**2)", []), _sol("1"), NOTOK, None),
        ("L2 ev ceiling(Z^2): 0", ev(f"ceiling(({Z})**2)", []), _sol("0"), NOTNO, None),
        ("L2 ev sign(Z^2): 1", ev(f"sign(({Z})**2)", []), _sol("1"), NOTOK, None),
        ("L2 ev sign(Z^2): 0", ev(f"sign(({Z})**2)", []), _sol("0"), NOTNO, None),
        ("L2 ev ceiling(sqrt|Z|): 1", ev(f"ceiling(sqrt(Abs({Z})))", []), _sol("1"), NOTOK, None),
        ("L2 ev ceiling(sqrt|Z|): 0", ev(f"ceiling(sqrt(Abs({Z})))", []), _sol("0"), NOTNO, None),
        ("L2 ev floor(-Z^2): -1", ev(f"floor(-({Z})**2)", []), _sol("-1"), NOTOK, None),
        ("L2 ev floor(-Z^2): 0", ev(f"floor(-({Z})**2)", []), _sol("0"), NOTNO, None),
        ("L2 ev sign(|Z|): 0", ev(f"sign(Abs({Z}))", []), _sol("0"), NOTNO, None),
        ("L2 ev sign(|Z|): 1", ev(f"sign(Abs({Z}))", []), _sol("1"), NOTOK, None),
        ("L2 ev frac(Z^2+3): 0", ev(f"frac(({Z})**2 + 3)", []), _sol("0"), NOTNO, None),
        ("L2 ev Mod(Z^2+3,1): 0", ev(f"Mod(({Z})**2 + 3, 1)", []), _sol("0"), NOTNO, None),
        ("L2 ev floor(3-Z^2): 2", ev(f"floor(3 - ({Z})**2)", []), _sol("2"), NOTOK, None),
        ("L2 ev 5 sign(Z^2): 5", ev(f"5*sign(({Z})**2)", []), _sol("5"), NOTOK, None),
        ("L2 ev Piecewise((1,Z^2>0),(0,Z^2<=0)): 1", ev(f"Piecewise((1, ({Z})**2 > 0), (0, ({Z})**2 <= 0))", []), _sol("1"),
         NOTOK, None),
        ("L2 ev Piecewise((1,Z^2>0),(0,Z^2<=0)): 0", ev(f"Piecewise((1, ({Z})**2 > 0), (0, ({Z})**2 <= 0))", []), _sol("0"),
         NOTNO, None),
        ("L2 ev 0: ceiling(Z^2)", ev("0", []), _sol(f"ceiling(({Z})**2)"), NOTNO, None),
        # the step layer: doit/simplify and the solvers read the jump off the noise
        ("L2 step eq x=ceiling(Z^2) | x=0", ev("x + 1", ["x = 0"]), _sol("1", steps=[("eq", f"x = ceiling(({Z})**2)")]),
         NOTNO, NOTREF),
        ("L2 step eq x=ceiling(Z^2) | x=1", ev("x + 1", ["x = 1"]), _sol("2", steps=[("eq", f"x = ceiling(({Z})**2)")]),
         NOTNO, NOTVER),
        ("L2 step compute Piecewise(..)=1", ev("x + 1", ["x = 2"]),
         _sol("3", steps=[("compute", f"Piecewise((1, ({Z})**2 > 0), (0, ({Z})**2 <= 0)) = 1")]), NOTNO, NOTVER),
        ("L2 step compute Piecewise(..)=0", ev("x + 1", ["x = 2"]),
         _sol("3", steps=[("compute", f"Piecewise((1, ({Z})**2 > 0), (0, ({Z})**2 <= 0)) = 0")]), NOTNO, NOTREF),
        ("L2 ctl step compute floor(pi)=4", ev("x + 1", ["x = 2"]), _sol("3", steps=[("compute", "floor(pi) = 4")]), NO, REF),
        ("L2 ctl ev floor(pi): 3", ev("floor(pi)", []), _sol("3"), OK, None),
        ("L2 ctl ev ceiling(log8/log2): 3", ev("ceiling(log(8)/log(2))", []), _sol("3"), OK, None),
        ("L2 ctl ev ceiling(log8/log2): 4", ev("ceiling(log(8)/log(2))", []), _sol("4"), NO, None),
        ("L2 ctl ev sign(log8/log2-3): 0", ev("sign(log(8)/log(2) - 3)", []), _sol("0"), OK, None),
        ("L2 ctl ev Mod(7,3): 1", ev("Mod(7, 3)", []), _sol("1"), OK, None),
        ("L2 ctl ev frac(pi): pi-3", ev("frac(pi)", []), _sol("pi - 3"), OK, None),
        ("L2 ctl ev Piecewise((7,pi>3),(0,pi<=3)): 7", ev("Piecewise((7, pi > 3), (0, pi <= 3))", []), _sol("7"), OK, None),
        # RK-1
        ("L3 ineq |x-3|(2^x-8)<=0: (-oo,3]", ineq("Abs(x - 3)*(2**x - 8) <= 0"), _sol("Interval(-oo, 3)", I_), OK, None),
        ("L3 ineq |x-3|(2^x-8)<=0: (-oo,3)", ineq("Abs(x - 3)*(2**x - 8) <= 0"), _sol("Interval.open(-oo, 3)", I_), NO, None),
        ("L3 ineq |x-3|(2^x-8)>0: (3,oo)", ineq("Abs(x - 3)*(2**x - 8) > 0"), _sol("Interval.open(3, oo)", I_), OK, None),
        ("L3 ineq |x-3|(2^x-8)>0: [3,oo)", ineq("Abs(x - 3)*(2**x - 8) > 0"), _sol("Interval(3, oo)", I_), NO, None),
        ("L3 ineq (x-3)|2^x-8|<=0: (-oo,3]", ineq("(x - 3)*Abs(2**x - 8) <= 0"), _sol("Interval(-oo, 3)", I_), OK, None),
        ("L3 ineq sign(x-3)(2^x-8)>=0: R", ineq("sign(x - 3)*(2**x - 8) >= 0"), _sol("Reals", S_), OK, None),
        ("L3 ineq Max(x,3)(2^x-8)<=0: (-oo,3]", ineq("Max(x, 3)*(2**x - 8) <= 0"), _sol("Interval(-oo, 3)", I_), OK, None),
        ("L3 ineq |x-2|(3^x-9)<0: (-oo,2)", ineq("Abs(x - 2)*(3**x - 9) < 0"), _sol("Interval.open(-oo, 2)", I_), OK, None),
        ("L3 ineq |x|(x-3)<=0, x<=L8: (-oo,3]", ineq("Abs(x)*(x - 3) <= 0", ["x <= log(8)/log(2)"]),
         _sol("Interval(-oo, 3)", I_), OK, None),
        ("L3 cint |x-3|(2^x-8)<=0 [-5,10]: 9", cint(["Abs(x - 3)*(2**x - 8) <= 0", "x >= -5", "x <= 10"], [V("x", "integer")]),
         _sol("9", "count"), OK, None),
        ("L3 cint |x-3|(2^x-8)<=0 [-5,10]: 8", cint(["Abs(x - 3)*(2**x - 8) <= 0", "x >= -5", "x <= 10"], [V("x", "integer")]),
         _sol("8", "count"), NO, None),
        # RK-2
        ("L4 ineq sqrt(2^x-x-1)>=0: R", ineq("sqrt(2**x - x - 1) >= 0"), _sol("Reals", S_), NO, None),
        ("L4 ineq acos(x+atan x)>=0: R", ineq("acos(x + atan(x)) >= 0"), _sol("Reals", S_), NO, None),
        ("L4 ineq acos(2^x+x-2)>=0: [0,2]", ineq("acos(2**x + x - 2) >= 0"), _sol("Interval(0, 2)", I_), NO, None),
        ("L4 ineq acos(2^x+x-2)>=0: [0,1]", ineq("acos(2**x + x - 2) >= 0"), _sol("Interval(0, 1)", I_), NOTNO, None),
        ("L4 ineq sqrt(x e^x-1)>=0: [0,oo)", ineq("sqrt(x*exp(x) - 1) >= 0"), _sol("Interval(0, oo)", I_), NOTOK, None),
        ("L4 ineq sqrt(1-x e^x)>=0: R", ineq("sqrt(1 - x*exp(x)) >= 0"), _sol("Reals", S_), NOTOK, None),
        ("L4 ineq x>=0 (|x|-x)acos(2^x+x-2)<=0: [0,2]", ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", vars_=(X0,)),
         _sol("Interval(0, 2)", I_), NOTOK, None),
        ("L4 ineq x>=0 (|x|-x)acos(2^x+x-2)<=0: [0,1]", ineq("(Abs(x) - x)*acos(2**x + x - 2) <= 0", vars_=(X0,)),
         _sol("Interval(0, 1)", I_), NOTNO, None),
        # RK-6 (the time is bounded by CASE_TIMEOUT; the seed independence is a test)
        ("L4 ineq x>=0 (|x|-x)(4 arc terms)<=0: [0,oo)",
         ineq("(Abs(x) - x)*(acos(2**x + x - 2) + asin(x + atan(x)) + acos(x*exp(x)) + asin(3**x + x - 2)) <= 0",
              vars_=(X0,)), _sol("Interval(0, oo)", I_), NOTOK, None),
        # RK-3
        ("L5 croots sin x [0,940]: 300", cr_("sin(x)", "0", "940"), _sol("300", "count"), OK, None),
        ("L5 croots sin x [0,940]: 299", cr_("sin(x)", "0", "940"), _sol("299", "count"), NO, None),
        ("L5 croots sin 100x [0,10]: 319", cr_("sin(100*x)", "0", "10"), _sol("319", "count"), OK, None),
        ("L5 croots cos x [0,1000]: 318", cr_("cos(x)", "0", "1000"), _sol("318", "count"), OK, None),
        ("L5 croots sin(pi x) [0,300]: 301", cr_("sin(pi*x)", "0", "300"), _sol("301", "count"), OK, None),
        ("L5 ctl croots sin x [0,930]: 297", cr_("sin(x)", "0", "930"), _sol("297", "count"), OK, None),
        # RK-4
        ("L6 eq dod 1..6 x^2-5x+6=0, sin(pi x/2)x!!=0: {3}",
         _ir("solve_equation", {"equation": "x**2 - 5*x + 6 = 0", "var": "x"}, (X,), ["sin(pi*x/2)*factorial(x) != 0"], "set", D6),
         _sol("{3}", S_), OK, None),
        ("L6 eq dod 1..6 x^2-5x+6=0, sin(pi x/2)x!!=0: {2,3}",
         _ir("solve_equation", {"equation": "x**2 - 5*x + 6 = 0", "var": "x"}, (X,), ["sin(pi*x/2)*factorial(x) != 0"], "set", D6),
         _sol("{2, 3}", S_), NO, None),
        ("L6 eq dod 1..6 x^2-5x+6=0, cos(pi x)Mod(x,4)>0: {2}",
         _ir("solve_equation", {"equation": "x**2 - 5*x + 6 = 0", "var": "x"}, (X,), ["cos(pi*x)*Mod(x, 4) > 0"], "set", D6),
         _sol("{2}", S_), OK, None),
        ("L6 ineq dod 1..6 x^2<20, sin(x)x!>0: {1,2,3}",
         _ir("solve_inequality", {"inequality": "x**2 < 20", "var": "x"}, (X,), ["sin(x)*factorial(x) > 0"], "set", D6),
         _sol("{1, 2, 3}", S_), OK, None),
        ("L6 ineq dod 1..6 x^2<20, sin(x)x!>0: {1,2,3,4}",
         _ir("solve_inequality", {"inequality": "x**2 < 20", "var": "x"}, (X,), ["sin(x)*factorial(x) > 0"], "set", D6),
         _sol("{1, 2, 3, 4}", S_), NO, None),
        # RK-5
        ("L7 deriv atan2(y,x) at 0, y=2: -1/2", _ir("derivative", {"f": "atan2(y, x)", "var": "x", "at": "0"}, XY, ["y = 2"]),
         _sol("-1/2"), OK, None),
        ("L7 deriv atan2(y,x) at 0, y=2: 1/2", _ir("derivative", {"f": "atan2(y, x)", "var": "x", "at": "0"}, XY, ["y = 2"]),
         _sol("1/2"), NO, None),
        ("L7 deriv atan2(y,x), y=2: -2/(x^2+4)", _ir("derivative", {"f": "atan2(y, x)", "var": "x"}, XY, ["y = 2"], "expression"),
         _sol("-2/(x**2 + 4)"), OK, None),
        ("L7 deriv atan2(y,x), y=2: 2/(x^2+4)", _ir("derivative", {"f": "atan2(y, x)", "var": "x"}, XY, ["y = 2"], "expression"),
         _sol("2/(x**2 + 4)"), NO, None),
        ("L7 ext max atan2(x,y) [0,1], y=1: pi/4",
         _ir("extremum", {"f": "atan2(x, y)", "var": "x", "which": "max", "interval": "[0, 1]"}, XY, ["y = 1"]), _sol("pi/4"),
         OK, None),
        ("L7 ext max atan2(x,y) [0,1], y=1: pi/3",
         _ir("extremum", {"f": "atan2(x, y)", "var": "x", "which": "max", "interval": "[0, 1]"}, XY, ["y = 1"]), _sol("pi/3"),
         NO, None),
        ("L7 lim atan2(y,x) x->0, y=1: pi/2", _ir("limit", {"expr": "atan2(y, x)", "var": "x", "to": "0"}, XY, ["y = 1"]),
         _sol("pi/2"), OK, None),
        ("L7 lim atan2(y,x) x->0, y=1: 0", _ir("limit", {"expr": "atan2(y, x)", "var": "x", "to": "0"}, XY, ["y = 1"]),
         _sol("0"), NO, None),
        ("L7 deriv atan2(x-1,0) at 2: 0", _ir("derivative", {"f": "atan2(x - 1, 0)", "var": "x", "at": "2"}), _sol("0"), OK, None),
        ("L7 deriv atan2(x-1,0) at 2: 1", _ir("derivative", {"f": "atan2(x - 1, 0)", "var": "x", "at": "2"}), _sol("1"), NO, None),
        ("L7 deriv arg(x) at 1: 0", _ir("derivative", {"f": "arg(x)", "var": "x", "at": "1"}), _sol("0"), OK, None),
        ("L7 deriv atan2(x,0) at 0: 0 (convention point)", _ir("derivative", {"f": "atan2(x, 0)", "var": "x", "at": "0"}),
         _sol("0"), NOTOK, None),
    ]
    return out


class _Slow(Exception):
    pass


def _on_alarm(signum, frame):
    raise _Slow()


# one verify past this (seconds) is a hang, counted as not expected (0ed77e2: over 20 minutes for B6)
CASE_TIMEOUT = int(os.environ.get("CASE_TIMEOUT", "120"))
signal.signal(signal.SIGALRM, _on_alarm)

GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g, "H": cases_h,
          "I": cases_i, "J": cases_j, "K": cases_k, "L": cases_l}


def main(out_path=None, groups="ABCDEFGHIJKL"):
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
    grp = args[1] if len(args) > 1 else "ABCDEFGHIJKL"
    sys.exit(1 if main(out, grp) else 0)
