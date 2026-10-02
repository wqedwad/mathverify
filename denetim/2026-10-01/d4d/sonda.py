"""Part d4d of the fourth audit's fixes (2 Oct 2026): the givens' bindings and conditions (findings G1, G7, G8, G9,
G10 of the `gorev` angle, TAN-01, TAN-03, TAN-04, TAN-09 of the `tanimlilik` angle and P1 of the `ayristirici` angle,
`denetim/2026-10-01/d4/`).

    A  G1      a Boolean or unreadable given (chain, And, Or, 'and', ',', '&', '∧', 'x in (0, 3)') is applied or
               abstained on, never dropped
    B  G7, TAN-04  a binding a = c contradicted by another given, the declaration or a constraint, or undefined /
               a convention as written: no CORRECT
    C  G8      a constraint that the binding makes False (empty region): no CORRECT
    D  G9, TAN-03  a written condition on the bound parameter alone (log(a), a/a, a!, ...) at the bound value
    E  G10     an undecided membership (T = atan(1) + atan(2) + atan(3) = pi against x > pi)
    F  TAN-01  a Sum range that the binding makes backwards or fractional
    G  TAN-09  x**a with a bound: the conditions are read after the binding
    H  P1      a pinned value never reaches a variable bound by an enclosing operator or the task's variable
    K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \
        .venv/bin/python denetim/2026-10-01/d4d/sonda.py [out.json] [groups]

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false acceptance
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
UNK = {"UNKNOWN"}
VER = {"verified"}
NOTVER = {"refuted", "unknown", "skipped", None}

X = {"name": "x", "domain": "real"}
A = {"name": "a", "domain": "real"}
T_ = {"name": "t", "domain": "real"}
KI = {"name": "k", "domain": "integer"}
XA = [X, A]
T = "atan(1) + atan(2) + atan(3)"          # exactly pi (decided since d4c)
# exactly pi too: atan(1/2) + atan(1/5) + atan(1/8) = atan(1/3) + atan(1/5) + atan(1/7) + atan(1/8) = pi/4 and
# asin(1/sqrt(26)) = atan(1/5), asin(1/sqrt(65)) = atan(1/8); seven terms, which no exact check decides (2 Oct 2026)
T7 = "2*(atan(1/3) + atan(1/5) + atan(1/7) + atan(1/8) + atan(1/2) + asin(1/sqrt(26)) + asin(1/sqrt(65)))"


def ir(kind, params, givens=(), vars_=None, shape="set", dod=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    if functions:
        d["functions"] = functions
    return d


def sol(payload, kind="set", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def ineq(rel, givens, vars_=None, dod=None):
    return ir("solve_inequality", {"inequality": rel, "var": "x"}, givens, vars_, dod=dod)


def eqn(rel, givens, vars_=None, dod=None):
    return ir("solve_equation", {"equation": rel, "var": "x"}, givens, vars_, dod=dod)


def roots(expr, givens, vars_=None):
    return ir("count_roots", {"expr": expr, "var": "x"}, givens, vars_, shape="count")


def dom(expr, givens, vars_=None):
    return ir("domain_of", {"expr": expr, "var": "x"}, givens, vars_)


def lim(expr, to, givens, vars_=None):
    return ir("limit", {"expr": expr, "var": "x", "to": to}, givens, vars_, shape="scalar")


def cases_a():
    out = []
    for g in ["0 < x < 3", "And(x > 0, x < 3)", "0 < x <= 3", r"0 < x \le 3", r"0 \lt x \lt 3", "x > 0 and x < 3",
              "x > 0, x < 3", "x in (0, 3)", "(x > 0) & (x < 3)", "x ∈ (0, 3)", "x > 0 ∧ x < 3", "x>0 ve x<3",
              "x > 0; x < 3", "x in Interval.open(0, 3)", r"x \in (0, 3)"]:
        q = ineq("x**2 < 4", [g])
        out.append((f"ineq x**2<4, given {g!r}: (-2, 2) [wrong]", q, sol("Interval.open(-2, 2)", "interval"), NOTOK, None))
        out.append((f"ineq x**2<4, given {g!r}: (0, 2) [right]", q, sol("Interval.open(0, 2)", "interval"), NOTNO, None))
        e = eqn("x**2 = 4", [g])
        out.append((f"eq x**2=4, given {g!r}: {{-2, 2}} [wrong]", e, sol("{-2, 2}"), NOTOK, None))
        out.append((f"eq x**2=4, given {g!r}: {{2}} [right]", e, sol("{2}"), NOTNO, None))
    q = ineq("x**2 < 4", ["x in (0, 3) and x != 1"])
    out.append(("ineq x**2<4, given 'x in (0, 3) and x != 1': (0, 2) [wrong]", q, sol("Interval.open(0, 2)", "interval"),
                NOTOK, None))
    out.append(("ineq x**2<4, given 'x in (0, 3) and x != 1': (0, 1) U (1, 2) [right]", q,
                sol("Union(Interval.open(0, 1), Interval.open(1, 2))", "set"), NOTNO, None))
    for g in ["Or(x < -3, x > 1)", "x < -3 or x > 1", "(x < -3) | (x > 1)", "x < -3 ∨ x > 1"]:
        c = roots("x**2 - 4", [g])
        out.append((f"roots x**2-4, given {g!r}: 2 [wrong]", c, sol("2", "count"), NOTOK, None))
        out.append((f"roots x**2-4, given {g!r}: 1 [right]", c, sol("1", "count"), NOTNO, None))
        e = ir("extremum", {"f": "-x**2", "var": "x", "which": "max", "interval": "[-5, 5]"}, [g], shape="scalar")
        out.append((f"max -x**2 on [-5,5], given {g!r}: 0 [no max]", e, sol("0", "value"), NOTOK, None))
        e2 = ir("extremum", {"f": "-x**2", "var": "x", "which": "max"}, [g], shape="scalar")
        out.append((f"max -x**2, given {g!r}: 0 [no max]", e2, sol("0", "value"), NOTOK, None))
        e = eqn("x**2 = 4", [g])
        out.append((f"eq x**2=4, given {g!r}: {{-2, 2}} [wrong]", e, sol("{-2, 2}"), NOTOK, None))
        out.append((f"eq x**2=4, given {g!r}: {{2}} [right]", e, sol("{2}"), NOTNO, None))
        d = dom("sqrt(16 - x**2)", [g])
        out.append((f"domain sqrt(16-x**2), given {g!r}: [-4, 4] [wrong]", d, sol("Interval(-4, 4)", "interval"), NOTOK, None))
        q = ineq("x**2 < 16", [g])
        out.append((f"ineq x**2<16, given {g!r}: (-4, 4) [wrong]", q, sol("Interval.open(-4, 4)", "interval"), NOTOK, None))
        out.append((f"ineq x**2<16, given {g!r}: (-4,-3) U (1,4) [right]", q,
                    sol("Union(Interval.open(-4, -3), Interval.open(1, 4))", "set"), NOTNO, None))
    out.append(("roots x**2-4, given 0 < x < 3: 1 [right]", roots("x**2 - 4", ["0 < x < 3"]), sol("1", "count"), NOTNO, None))
    out.append(("roots x**2-4, given 0 < x < 3: 2 [wrong]", roots("x**2 - 4", ["0 < x < 3"]), sol("2", "count"), NOTOK, None))
    XI = [{"name": "x", "domain": "integer"}]
    ci = ir("count_integers", {"var": "x"}, ["x**2 < 20", "Or(x < -3, x > 1)"], XI, shape="count")
    out.append(("count_integers x**2<20, Or(x<-3, x>1): 9 [wrong]", ci, sol("9", "count"), NOTOK, None))
    out.append(("count_integers x**2<20, Or(x<-3, x>1): 4 [right]", ci, sol("4", "count"), NOTNO, None))
    ci2 = ir("count_integers", {"var": "x"}, ["x**2 < 20", "x < -3 or x > 1"], XI, shape="count")
    out.append(("count_integers x**2<20, 'x<-3 or x>1': 9 [wrong]", ci2, sol("9", "count"), NOTOK, None))
    ev = ir("evaluate", {"expr": "y"}, ["x**2 = 4", "y = x + 1", "Or(x < -3, x > 1)"], [X, {"name": "y"}], shape="scalar")
    out.append(("evaluate y, x**2=4, y=x+1, Or(x<-3, x>1): 3 [right]", ev, sol("3", "value"), NOTNO, None))
    out.append(("evaluate y, x**2=4, y=x+1, Or(x<-3, x>1): -1 [wrong]", ev, sol("-1", "value"), NOTOK, None))
    ev2 = ir("evaluate", {"expr": "y"}, ["x**2 = 4", "y = x + 1", "0 < x < 3"], [X, {"name": "y"}], shape="scalar")
    out.append(("evaluate y, x**2=4, y=x+1, 0<x<3: -1 [wrong]", ev2, sol("-1", "value"), NOTOK, None))
    c = roots("x**2 - 4", ["Or(Eq(x, 2), Eq(x, 5))"])
    out.append(("roots x**2-4, given Or(x=2, x=5): 2 [wrong]", c, sol("2", "count"), NOTOK, None))
    out.append(("roots x**2-4, given Or(x=2, x=5): 1 [right]", c, sol("1", "count"), NOTNO, None))
    d = dom("sqrt(4 - x**2)", ["x > 0 and x < 3"])
    out.append(("domain sqrt(4-x**2), given 'x > 0 and x < 3': [-2, 2] [wrong]", d, sol("Interval(-2, 2)", "interval"), NOTOK, None))
    out.append(("domain sqrt(4-x**2), given 'x > 0 and x < 3': (0, 2] [right]", d, sol("Interval.Lopen(0, 2)", "interval"), NOTNO, None))
    d = dom("sqrt(4 - x**2)", ["0 < x < 3"])
    out.append(("domain sqrt(4-x**2), given 0<x<3: [-2, 2] [wrong]", d, sol("Interval(-2, 2)", "interval"), NOTOK, None))
    q = ineq("x**2 < 4", ["b < x < 3"], [X, {"name": "b", "domain": "real"}])
    out.append(("ineq x**2<4, given b < x < 3 (b free): (-2, 2)", q, sol("Interval.open(-2, 2)", "interval"), NOTOK, None))
    q = ineq("x**2 < 4", ["0 < x < a", "a = 3"], XA)
    out.append(("ineq x**2<4, given 0 < x < a, a = 3: (-2, 2) [wrong]", q, sol("Interval.open(-2, 2)", "interval"), NOTOK, None))
    out.append(("ineq x**2<4, given 0 < x < a, a = 3: (0, 2) [right]", q, sol("Interval.open(0, 2)", "interval"), NOTNO, None))
    return out


def cases_b():
    out = []
    q = ineq("x**2 < 4", ["x > a", "a = 1", "a < 0"], XA)
    out.append(("ineq x**2<4, x>a, a=1, a<0: (1, 2)", q, sol("Interval.open(1, 2)", "interval"), NOTOK, None))
    c = roots("x**2 - 4", ["x > a", "a = 1"], [X, {"name": "a", "domain": "real", "constraints": ["a > 5"]}])
    out.append(("roots x**2-4, x>a, a=1, constraint a>5: 1", c, sol("1", "count"), NOTOK, None))
    l1 = lim("sin(a*x)/x", "0", ["a = -2"], [X, {"name": "a", "domain": "positive_real"}])
    out.append(("lim sin(ax)/x, a positive, a=-2: -2", l1, sol("-2", "value"), NOTOK, None))
    for g in ["a = 4 + log(-1) - log(-1)", "a = 4 + acos(2) - acos(2)", "a = sqrt(-4)**2", "a = 0*log(-1) + 4"]:
        w = eqn("x**2 = a", [g], XA)
        out.append((f"eq x**2=a, {g}: {{-2, 2}}", w, sol("{-2, 2}"), NOTOK, None))
    z = lim("sin(a*x)/x", "0", ["a = 0**0"], XA)
    out.append(("lim sin(ax)/x, a = 0**0: 1", z, sol("1", "value"), NOTOK, None))
    i = eqn("x**2 = 4", ["x > a", "a = 1/2"], [X, {"name": "a", "domain": "integer"}])
    out.append(("eq x**2=4, x>a, a integer, a=1/2: {2}", i, sol("{2}"), NOTOK, None))
    for extra in (["a > 1"], ["a - 1 = 0"], ["a**2 = 1"], ["2*a = 1"]):
        g = ["a = 0", "x > a"] + extra
        out.append((f"eq x**2=4, {g}: {{2}}", eqn("x**2 = 4", g, XA), sol("{2}"), NOTOK, None))
    out.append(("eq x**2=4, a positive, a=0, x>a: {2}",
                eqn("x**2 = 4", ["a = 0", "x > a"], [X, {"name": "a", "domain": "positive_real"}]), sol("{2}"), NOTOK, None))
    out.append(("eq x**2=4, a constraint a>1, a=0, x>a: {2}",
                eqn("x**2 = 4", ["a = 0", "x > a"], [X, {"name": "a", "domain": "real", "constraints": ["a > 1"]}]),
                sol("{2}"), NOTOK, None))
    g = ["a = 0", "x > a", "a > 1"]
    out.append(("ineq x**2<9, a=0, x>a, a>1: (0, 3)", ineq("x**2 < 9", g, XA), sol("Interval.open(0, 3)", "interval"), NOTOK, None))
    out.append(("roots x**2-4, a=0, x>a, a>1: 1", roots("x**2 - 4", g, XA), sol("1", "count"), NOTOK, None))
    out.append(("domain sqrt(4-x**2), a=0, x>a, a>1: (0, 2]", dom("sqrt(4 - x**2)", g, XA),
                sol("Interval.Lopen(0, 2)", "interval"), NOTOK, None))
    out.append(("lim a*x x->1, a=0, a-1=0: 0", lim("a*x", "1", ["a = 0", "a - 1 = 0"], XA), sol("0", "value"), NOTOK, None))
    out.append(("evaluate a + 1, a=0, a>1: 1",
                ir("evaluate", {"expr": "a + 1"}, ["a = 0", "a > 1"], XA, shape="scalar"), sol("1", "value"), NOTOK, None))
    out.append(("derivative a*x**2, a=0, a>1: 0",
                ir("derivative", {"f": "a*x**2", "var": "x"}, ["a = 0", "a > 1"], XA, shape="expression"),
                sol("0", "expression"), NOTOK, None))
    out.append(("eq x**2=4, x>a, a=1, a<b, b=0: {2}",
                eqn("x**2 = 4", ["x > a", "a = 1", "b = 0", "a < b"], XA + [{"name": "b", "domain": "real"}]),
                sol("{2}"), NOTOK, None))
    return out


def cases_c():
    out = []
    V = [{"name": "x", "domain": "positive_real", "constraints": ["x < a"]}, A]
    q = eqn("x**2 = 4", ["a = 0"], V)
    out.append(("eq x**2=4, x positive, x<a, a=0: {2}", q, sol("{2}"), NOTOK, None))
    out.append(("eq x**2=4, x positive, x<a, a=0: {}", q, sol("{}"), NOTOK, None))
    out.append(("ineq x**2<4, x positive, x<a, a=0: (0, 2)", ineq("x**2 < 4", ["a = 0"], V),
                sol("Interval.open(0, 2)", "interval"), NOTOK, None))
    out.append(("domain sqrt(x), x positive, x<a, a=0: (0, oo)", dom("sqrt(x)", ["a = 0"], V),
                sol("Interval.open(0, oo)", "interval"), NOTOK, None))
    out.append(("roots x**2-4, x positive, x<a, a=0: 1", roots("x**2 - 4", ["a = 0"], V), sol("1", "count"), NOTOK, None))
    out.append(("roots x**2-4, x positive, x<a, a=0: 0", roots("x**2 - 4", ["a = 0"], V), sol("0", "count"), NOTOK, None))
    Vg = [{"name": "x", "domain": "positive_real"}, A]
    q = eqn("x**2 = 4", ["a = 0"], Vg, dod="x < a")
    out.append(("eq x**2=4, x positive, dod x<a, a=0: {2}", q, sol("{2}"), NOTOK, None))
    out.append(("eq x**2=4, x positive, dod x<a, a=0: {}", q, sol("{}"), NOTOK, None))
    q = eqn("x**2 = 4", ["a = 0", "x < a"], Vg)
    out.append(("eq x**2=4, x positive, given x<a, a=0: {2}", q, sol("{2}"), NOTOK, None))
    out.append(("eq x**2=4, x positive, given x<a, a=0: {}", q, sol("{}"), NOTOK, None))
    return out


def cases_d():
    out = []
    V = [{"name": "x"}, {"name": "a"}]
    for term, a in [("log(a)", "-1"), ("sqrt(a)", "-1"), ("acos(a)", "2"), ("a/a", "0"), ("tan(a)", "pi/2"),
                    ("log(a - 1)", "1/2"), ("factorial(a)", "-1"), ("factorial(a)", "1/2"), ("binomial(a, 2)", "-1"),
                    ("gcd(a, 2)", "sqrt(2)"), ("gcd(a, 2)", "pi"), ("Sum(k, (k, 1, a))", "-3")]:
        e = eqn(f"x + {term} - {term} = 2", [f"a = {a}"], V)
        out.append((f"eq x + {term} - {term} = 2, a={a}: {{2}}", e, sol("{2}"), NOTOK, None))
    L = "x + log(a) - log(a)"
    g = ["a = -1"]
    out.append(("derivative x + log(a) - log(a), a=-1: 1",
                ir("derivative", {"f": L, "var": "x"}, g, V, shape="expression"), sol("1", "expression"), NOTOK, None))
    out.append(("derivative at 2, a=-1: 1",
                ir("derivative", {"f": L, "var": "x", "at": "2"}, g, V, shape="scalar"), sol("1", "value"), NOTOK, None))
    out.append(("tangent at 1, a=-1: y = x",
                ir("tangent_line", {"f": L, "var": "x", "at": "1"}, g, V, shape="equation"), sol("y = x", "equation"),
                NOTOK, None))
    out.append(("defint 0..1, a=-1: 1/2",
                ir("definite_integral", {"integrand": L, "var": "x", "a": "0", "b": "1"}, g, V, shape="scalar"),
                sol("1/2", "value"), NOTOK, None))
    out.append(("extremum max on [0,1], a=-1: 1",
                ir("extremum", {"f": L, "var": "x", "which": "max", "interval": "[0, 1]"}, g, V, shape="scalar"),
                sol("1", "value"), NOTOK, None))
    out.append(("limit x->1, a=-1: 1", lim(L, "1", g, V), sol("1", "value"), NOTOK, None))
    out.append(("limit sin(x)/x + log(a) - log(a) x->0, a=-1: 1", lim("sin(x)/x + log(a) - log(a)", "0", g, V),
                sol("1", "value"), NOTOK, None))
    out.append(("limit a*x + acos(a) - acos(a) x->1, a=2: 2", lim("a*x + acos(a) - acos(a)", "1", ["a = 2"], V),
                sol("2", "value"), NOTOK, None))
    out.append(("simplify, a=-1: x",
                ir("simplify_expression", {"expr": L}, g, V, shape="expression"), sol("x", "expression"), NOTOK, None))
    out.append(("ineq x + log(a) - log(a) > 0, a=-1: (0, oo)", ineq(L + " > 0", g, V),
                sol("Interval.open(0, oo)", "interval"), NOTOK, None))
    out.append(("ineq x + binomial(a, 2) - binomial(a, 2) > 0, a=-1: (0, oo)",
                ineq("x + binomial(a, 2) - binomial(a, 2) > 0", g, V), sol("Interval.open(0, oo)", "interval"), NOTOK, None))
    out.append(("roots x - 1 + log(a) - log(a), a=-1: 1", roots("x - 1 + log(a) - log(a)", g, V), sol("1", "count"),
                NOTOK, None))
    out.append(("domain sqrt(x)*a/a, a=0: [0, oo)", dom("sqrt(x)*a/a", ["a = 0"], V), sol("Interval(0, oo)", "interval"),
                NOTOK, None))
    out.append(("eq via function f(t) = log(t) - log(t), x + f(a) = 2, a=-1: {2}",
                ir("solve_equation", {"equation": "x + f(a) = 2", "var": "x"}, g, V,
                   functions=[{"name": "f", "args": ["t"], "expr": "log(t) - log(t)"}]), sol("{2}"), NOTOK, None))
    out.append(("limit a constraint a = -1, x + log(a) - log(a) x->1: 1",
                lim(L, "1", [], [{"name": "x"}, {"name": "a", "constraints": ["a = -1"]}]), sol("1", "value"), NOTOK, None))
    out.append(("series_sum 1/k**2 + log(a) - log(a), a=-1: pi**2/6",
                ir("series_sum", {"term": "1/k**2 + log(a) - log(a)", "index": "k", "start": "1"}, g,
                   [{"name": "k", "domain": "positive_integer"}, {"name": "a"}], shape="scalar"),
                sol("pi**2/6", "value"), NOTOK, None))
    out.append(("evaluate chain b = log(a) - log(a), a=-1, x = b: 0",
                ir("evaluate", {"expr": "x"}, ["a = -1", "b = log(a) - log(a)", "x = b"], V + [{"name": "b"}],
                   shape="scalar"), sol("0", "value"), NOTOK, None))
    return out


def cases_e():
    out = []
    for t in (T, T7):
        out += _cases_e(t, "T" if t == T else "T7")
    return out


def _cases_e(T, nm):
    out = []
    XY = [X, {"name": "y", "domain": "real"}]
    out.append((f"[{nm}] evaluate y, x = T, y = 7, x > pi: 7",
                ir("evaluate", {"expr": "y"}, [f"x = {T}", "y = 7", "x > pi"], XY, shape="scalar"), sol("7", "value"),
                NOTOK, None))
    out.append((f"[{nm}] evaluate y, x = T, y = 7, x > pi: 8",
                ir("evaluate", {"expr": "y"}, [f"x = {T}", "y = 7", "x > pi"], XY, shape="scalar"), sol("8", "value"),
                NOTNO, None))
    out.append((f"[{nm}] evaluate y, x**2 = T**2, y = x/|x|, x > pi: 1",
                ir("evaluate", {"expr": "y"}, [f"x**2 = ({T})**2", "y = x/Abs(x)", "x > pi"], XY, shape="scalar"),
                sol("1", "value"), NOTOK, None))
    for g in ["x < pi", "x != pi"]:
        out.append((f"[{nm}] evaluate y, x = T, y = 7, {g}: 7",
                    ir("evaluate", {"expr": "y"}, [f"x = {T}", "y = 7", g], XY, shape="scalar"), sol("7", "value"),
                    NOTOK, None))
    out.append((f"[{nm}] evaluate y, x = T, y = 7, constraint x > pi: 7",
                ir("evaluate", {"expr": "y"}, [f"x = {T}", "y = 7"],
                   [{"name": "x", "domain": "real", "constraints": ["x > pi"]}, {"name": "y"}], shape="scalar"),
                sol("7", "value"), NOTOK, None))
    out.append((f"[{nm}] evaluate y, x = T, y = 7, dod x > pi: 7",
                ir("evaluate", {"expr": "y"}, [f"x = {T}", "y = 7"], XY, shape="scalar", dod="x > pi"),
                sol("7", "value"), NOTOK, None))
    for where in ("given", "constraint", "dod"):
        if where == "given":
            q = eqn(f"x - ({T}) = 0", ["x > pi"])
        elif where == "constraint":
            q = eqn(f"x - ({T}) = 0", [], [{"name": "x", "domain": "real", "constraints": ["x > pi"]}])
        else:
            q = eqn(f"x - ({T}) = 0", [], dod="x > pi")
        out.append((f"[{nm}] eq x - T = 0, x > pi ({where}): {{T}}", q, sol("{" + T + "}"), NOTOK, None))
        out.append((f"[{nm}] eq x - T = 0, x > pi ({where}): {{}}", q, sol("{}"), NOTNO, None))
    q = eqn(f"x**2 = ({T})**2", ["x > pi"])
    out.append((f"[{nm}] eq x**2 = T**2, x > pi: {{T}}", q, sol("{" + T + "}"), NOTOK, None))
    out.append((f"[{nm}] eq x**2 = T**2, x > pi: {{}}", q, sol("{}"), NOTNO, None))
    q = eqn("x - atan(1/2) - atan(1/3) = 0", ["x > pi/4"])
    out.append((f"[{nm}] eq x = atan(1/2)+atan(1/3), x > pi/4: {{atan(1/2)+atan(1/3)}}", q, sol("{atan(1/2) + atan(1/3)}"),
                NOTOK, None))
    return out


def cases_f():
    out = []
    N = {"name": "n", "domain": "integer"}
    S = "Sum(k, (k, 1, n))"
    out.append(("ineq x + S > 5, n=-3: (2, oo) [Karr]", ineq(f"x + {S} > 5", ["n = -3"], [X, N, KI]),
                sol("Interval.open(2, oo)", "interval"), NOTOK, None))
    out.append(("ineq x + S > 5, n=-3: (5, oo) [empty sum]", ineq(f"x + {S} > 5", ["n = -3"], [X, N, KI]),
                sol("Interval.open(5, oo)", "interval"), NOTOK, None))
    out.append(("ineq x*S > 2, n=-2: (2, oo)", ineq(f"x*{S} > 2", ["n = -2"], [X, N, KI]),
                sol("Interval.open(2, oo)", "interval"), NOTOK, None))
    out.append(("ineq x**2 < 100, given x > S, n=-3: (3, 10)", ineq("x**2 < 100", [f"x > {S}", "n = -3"], [X, N, KI]),
                sol("Interval.open(3, 10)", "interval"), NOTOK, None))
    out.append(("ineq x + Sum(k,(k,m,n)) > 5, m=3, n=1: (7, oo)",
                ineq("x + Sum(k, (k, m, n)) > 5", ["m = 3", "n = 1"], [X, N, KI, {"name": "m", "domain": "integer"}]),
                sol("Interval.open(7, oo)", "interval"), NOTOK, None))
    out.append(("ineq x + Sum(k,(k,1,n/2)) > 5, n=7: (-23/8, oo)",
                ineq("x + Sum(k, (k, 1, n/2)) > 5", ["n = 7"], [X, N, KI]), sol("Interval.open(-23/8, oo)", "interval"),
                NOTOK, None))
    out.append(("ineq x + Sum(k,(k,1,n)) > 5, n real = 5/2: (5/8, oo)",
                ineq("x + Sum(k, (k, 1, n)) > 5", ["n = 5/2"], [X, KI, {"name": "n"}]),
                sol("Interval.open(5/8, oo)", "interval"), NOTOK, None))
    out.append(("eq x**2=4, given x > S, n=-3: {}", eqn("x**2 = 4", [f"x > {S}", "n = -3"], [X, N, KI]), sol("{}"), NOTOK, None))
    out.append(("roots x**2-4, given x > S, n=-3: 0", roots("x**2 - 4", [f"x > {S}", "n = -3"], [X, N, KI]),
                sol("0", "count"), NOTOK, None))
    out.append(("domain sqrt(x), given x > S, n=-3: (3, oo)", dom("sqrt(x)", [f"x > {S}", "n = -3"], [X, N, KI]),
                sol("Interval.open(3, oo)", "interval"), NOTOK, None))
    out.append(("count_integers x + S < 5, x > 0, n=-3: 1",
                ir("count_integers", {"var": "x"}, [f"x + {S} < 5", "x > 0", "n = -3"],
                   [{"name": "x", "domain": "integer"}, N, KI], shape="count"), sol("1", "count"), NOTOK, None))
    out.append(("trig sin(x)*S = 0 on [0, 2pi), n=-2: {0, pi}",
                ir("trig_solve", {"equation": f"sin(x)*{S} = 0", "var": "x", "interval": "[0, 2*pi)"}, ["n = -2"],
                   [X, N, KI]), sol("{0, pi}"), NOTOK, None))
    out.append(("extremum max x*S on [0,1], n=-2: 0",
                ir("extremum", {"f": f"x*{S}", "var": "x", "which": "max", "interval": "[0, 1]"}, ["n = -2"], [X, N, KI],
                   shape="scalar"), sol("0", "value"), NOTOK, None))
    out.append(("derivative x + S, n=-2: 1",
                ir("derivative", {"f": f"x + {S}", "var": "x"}, ["n = -2"], [X, N, KI], shape="expression"),
                sol("1", "expression"), NOTOK, None))
    return out


def cases_g():
    out = []
    V = [X, A]
    q = ineq("x**a < 4", ["a = 2"], V)
    out.append(("ineq x**a < 4, a=2: (0, 2) [wrong]", q, sol("Interval.open(0, 2)", "interval"), NOTOK, None))
    out.append(("ineq x**a < 4, a=2: (-2, 2) [right]", q, sol("Interval.open(-2, 2)", "interval"), NOTNO, None))
    for e, a, right, wrong in [("x**a = 4", "2", "{-2, 2}", "{2}"), ("x**a = 1/4", "-2", "{-2, 2}", "{2}"),
                               ("x**a = -8", "3", "{-2}", "{}")]:
        out.append((f"eq {e}, a={a}: {right} [right]", eqn(e, [f"a = {a}"], V), sol(right), NOTNO, None))
        out.append((f"eq {e}, a={a}: {wrong} [wrong]", eqn(e, [f"a = {a}"], V), sol(wrong), NOTOK, None))
    out.append(("eq x**a = 4, a integer, a=2: {-2, 2} [right]",
                eqn("x**a = 4", ["a = 2"], [X, {"name": "a", "domain": "integer"}]), sol("{-2, 2}"), NOTNO, None))
    out.append(("ineq x**a < 4, a=1/2: [0, 16) [right]", ineq("x**a < 4", ["a = 1/2"], V),
                sol("Interval.Ropen(0, 16)", "interval"), NOTNO, None))
    out.append(("limit x**a x->-1, a=2: 1 [right]", lim("x**a", "-1", ["a = 2"], V), sol("1", "value"), NOTNO, None))
    out.append(("ineq x**a < 4, a=1/2: (-oo, 16) [wrong]", ineq("x**a < 4", ["a = 1/2"], V),
                sol("Interval.open(-oo, 16)", "interval"), NOTOK, None))
    return out


def cases_h():
    out = []
    F = "Integral(t**2, (t, 0, x))"
    d = ir("derivative", {"f": F, "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar")
    out.append(("derivative F at 2, given x=2: 0 [wrong]", d, sol("0", "value"), NOTOK, None))
    out.append(("derivative F at 2, given x=2: 4 [right]", d, sol("4", "value"), NOTNO, None))
    d2 = ir("derivative", {"f": "integrate(t**2, (t, 0, x))", "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar")
    out.append(("derivative integrate(...) at 2, given x=2: 0", d2, sol("0", "value"), NOTOK, None))
    d3 = ir("derivative", {"f": r"\int_0^x t^2 \, dt", "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar")
    out.append(("derivative LaTeX int at 2, given x=2: 0", d3, sol("0", "value"), NOTOK, None))
    an = ir("antiderivative", {"integrand": F, "var": "x"}, ["x = 2"], [X, T_], shape="expression")
    out.append(("antiderivative F, given x=2: 8*x/3", an, sol("8*x/3", "expression"), NOTOK, None))
    tl = ir("tangent_line", {"f": F, "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="equation")
    out.append(("tangent F at 2, given x=2: y = 8/3", tl, sol("y = 8/3", "equation"), NOTOK, None))
    lm = lim(f"(x*{F})/x**3", "0", ["x = 2"], [X, T_])
    out.append(("limit (x*F)/x**3 x->0, given x=2: oo", lm, sol("oo", "value"), NOTOK, None))
    lm2 = lim(f"{F}/x**3", "0", ["x = 2"], [X, T_])
    out.append(("limit F/x**3 x->0, given x=2: 1/3 [right]", lm2, sol("1/3", "value"), NOTNO, None))
    e = ir("evaluate", {"expr": "Derivative(Integral(a*t, (t, 0, 1)), a)"}, ["a = 2"], [X, T_, A], shape="scalar")
    out.append(("evaluate d/da Integral(a*t), a=2: 0 [wrong]", e, sol("0", "value"), NOTOK, None))
    out.append(("evaluate d/da Integral(a*t), a=2: 1/2", e, sol("1/2", "value"), NOTNO, None))
    st = ir("evaluate", {"expr": "1"}, ["a = 2"], [X, T_, A], shape="scalar")
    out.append(("step compute d/da Integral(a*t) = 0, a=2", st,
                sol("1", "value", [("compute", "Derivative(Integral(a*t, (t, 0, 1)), a) = 0")]), NOTOK | OK, NOTVER))
    e2 = ir("evaluate", {"expr": "Derivative(Limit(a*sin(x)/x, x, 0), a)"}, ["a = 2"], [X, A], shape="scalar")
    out.append(("evaluate d/da Limit(a sin x/x), a=2: 0", e2, sol("0", "value"), NOTOK, None))
    K = {"name": "k", "domain": "integer"}
    s = ir("evaluate", {"expr": "Sum(Integral(t, (t, 0, k)), (k, 1, 2))"}, ["k = 5"], [T_, K], shape="scalar")
    out.append(("evaluate Sum_k Integral(t,0,k), k integer, k=5: 25", s, sol("25", "value"), NOTOK, None))
    fn = ir("derivative", {"f": "f(x)", "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar",
            functions=[{"name": "f", "args": ["x"], "expr": F}])
    out.append(("derivative f(x) = F at 2 (IR function), given x=2: 0", fn, sol("0", "value"), NOTOK, None))
    se = eqn(f"{F} = 8/3", ["x = 2"], [X, T_])
    out.append(("eq F = 8/3 (task var x pinned by a given x = 2): {2} not certified via pins", se, sol("{2}"),
                NOTOK | OK, None))
    out.append(("eq F = 8/3, given x = 2: {} [wrong]", se, sol("{}"), NOTOK, None))
    ev = ir("evaluate", {"expr": "f(x)"}, ["x = 2"], [X, T_], shape="scalar",
            functions=[{"name": "f", "args": ["x"], "expr": F}])
    out.append(("ctl: evaluate f(x) = F, x = 2: 8/3", ev, sol("8/3", "value"), OK, None))
    out.append(("ctl: evaluate f(x) = F, x = 2: 4", ev, sol("4", "value"), NO, None))
    ev2 = ir("evaluate", {"expr": F}, ["x = 2"], [X, T_], shape="scalar")
    out.append(("ctl: evaluate F, x = 2: 8/3", ev2, sol("8/3", "value"), OK, None))
    st2 = ir("evaluate", {"expr": "1"}, ["a = 2"], [X, T_, A], shape="scalar")
    out.append(("step eq Derivative(Integral(a*t), a) = 1/2, a=2: not refuted", st2,
                sol("1", "value", [("eq", "Derivative(Integral(a*t, (t, 0, 1)), a) = 1/2")]), NOTNO, None))
    pa = ir("derivative", {"f": "Integral(a*t, (t, 0, x))", "var": "a"}, ["a = 2", "x = 1"], [X, T_, A],
            shape="expression")
    out.append(("derivative wrt a of Integral(a*t,(t,0,x)), a=2, x=1: 0", pa, sol("0", "expression"), NOTOK, None))
    return out


def cases_k():
    out = []
    out.append(("ctl: ineq x**2<4, given x > 0: (0, 2)", ineq("x**2 < 4", ["x > 0"]), sol("Interval.open(0, 2)", "interval"),
                OK, None))
    out.append(("ctl: ineq x**2<4, given x > 0: (-2, 2)", ineq("x**2 < 4", ["x > 0"]),
                sol("Interval.open(-2, 2)", "interval"), NO, None))
    out.append(("ctl: eq x**2=4, x>a, a=0: {2}", eqn("x**2 = 4", ["x > a", "a = 0"], XA), sol("{2}"), OK, None))
    out.append(("ctl: eq x**2=4, x>a, a=0: {-2, 2}", eqn("x**2 = 4", ["x > a", "a = 0"], XA), sol("{-2, 2}"), NO, None))
    out.append(("ctl: eq x**2=a, a=4: {-2, 2}", eqn("x**2 = a", ["a = 4"], XA), sol("{-2, 2}"), OK, None))
    out.append(("ctl: eq x**2=4, a positive, a=1, x>a: {2}",
                eqn("x**2 = 4", ["a = 1", "x > a"], [X, {"name": "a", "domain": "positive_real"}]), sol("{2}"), OK, None))
    out.append(("ctl: eq x**2=4, a=1, a>0, x>a: {2}", eqn("x**2 = 4", ["a = 1", "a > 0", "x > a"], XA), sol("{2}"), OK, None))
    out.append(("ctl: lim sin(ax)/x, a=2: 2", lim("sin(a*x)/x", "0", ["a = 2"], XA), sol("2", "value"), OK, None))
    out.append(("ctl: eq x + log(a) - log(a) = 2, a=1: {2}", eqn("x + log(a) - log(a) = 2", ["a = 1"], XA), sol("{2}"),
                OK, None))
    out.append(("ctl: ineq x + S > 5, n=3: (-1, oo)",
                ineq("x + Sum(k, (k, 1, n)) > 5", ["n = 3"], [X, KI, {"name": "n", "domain": "integer"}]),
                sol("Interval.open(-1, oo)", "interval"), OK, None))
    out.append(("ctl: eq x**3 = 8 (x**a, a=3): {2}", eqn("x**a = 8", ["a = 3"], XA), sol("{2}"), NOTNO, None))
    out.append(("ctl: evaluate y, x = pi, y = 7, x > pi: 7 (ir_inconsistent)",
                ir("evaluate", {"expr": "y"}, ["x = pi", "y = 7", "x > pi"], [X, {"name": "y"}], shape="scalar"),
                sol("7", "value"), NOTOK, None))
    out.append(("ctl: evaluate y, x = T, y = 7, x >= pi: 7",
                ir("evaluate", {"expr": "y"}, [f"x = {T}", "y = 7", "x >= pi"], [X, {"name": "y"}], shape="scalar"),
                sol("7", "value"), NOTNO, None))
    out.append(("ctl: evaluate x**2 + 1, x = 3: 10", ir("evaluate", {"expr": "x**2 + 1"}, ["x = 3"], shape="scalar"),
                sol("10", "value"), OK, None))
    out.append(("ctl: evaluate x**2 + 1, x = 3: 11", ir("evaluate", {"expr": "x**2 + 1"}, ["x = 3"], shape="scalar"),
                sol("11", "value"), NO, None))
    F = "Integral(t**2, (t, 0, x))"
    out.append(("ctl: derivative F at 2 (no given): 4", ir("derivative", {"f": F, "var": "x", "at": "2"}, [], [X, T_],
                                                         shape="scalar"), sol("4", "value"), NOTNO, None))
    out.append(("ctl: evaluate Integral(a*t,(t,0,1)), a=2: 1",
                ir("evaluate", {"expr": "Integral(a*t, (t, 0, 1))"}, ["a = 2"], [T_, A], shape="scalar"),
                sol("1", "value"), OK, None))
    out.append(("ctl: domain sqrt(x), given x > 1: (1, oo)", dom("sqrt(x)", ["x > 1"]), sol("Interval.open(1, oo)", "interval"),
                OK, None))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "K": cases_k}


def main(out_path=None, groups="ABCDEFGHK"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for label, q, s, verdicts, statuses in GROUPS[g]():
            t = time.time()
            try:
                r = verify(q, s)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                status = steps[-1].get("status") if steps else None
                flags = sorted({f for la in r.layers for f in (la.flags or [])})[:6]
            except Exception as e:  # noqa: BLE001
                verdict, status, flags = f"EXC {type(e).__name__}: {e}", None, []
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
    grp = args[1] if len(args) > 1 else "ABCDEFGHK"
    sys.exit(1 if main(out, grp) else 0)
