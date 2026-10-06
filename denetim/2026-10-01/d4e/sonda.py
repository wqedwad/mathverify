"""Part d4e of the fourth audit's fixes (2 Oct 2026): how the task certificates read the conditions on their
variable and the written domain of their function (findings G4, G6, G12 of the `gorev` angle and TAN-02, TAN-05,
TAN-06, TAN-07 of the `tanimlilik` angle, `denetim/2026-10-01/d4/`).

    A  G6      a limit reads every condition on its variable (declaration, constraint, given, domain of discourse):
               the same condition written any way gives one verdict; a point outside the region is not approached
    B  G6      a derivative / tangent at a point that is not interior to the region (a given included)
    C  G4      an end of the extremum interval that is a symbol (pinned by a given or a constraint, or free)
    D  TAN-02  a parameter of the extremum's f (pinned or free); a candidate value that is not a number
    E  G12     the antiderivative is compared on the variable's region (constraint, given, dod, declaration) and
               must be real there
    F  TAN-05  the variable of a point binder (at, Subs, Limit) carries no declared assumption in the
               definedness reading
    G  TAN-06  derivative / tangent / antiderivative / simplification of a function whose written domain is an end
               point, an isolated point or empty
    H  TAN-07  an integral with an infinite bound: undefined points between the bounds and divergence at the
               infinite end
    K  controls whose verdict must not change
    L  TAN-06 with periodic conditions; trigonometric derivatives, tangents and primitives that must stay decided
    M  a parameter a given or a constraint fixes, read in every task certificate and in the written conditions

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \
        .venv/bin/python denetim/2026-10-01/d4e/sonda.py [out.json] [groups]

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
XP = {"name": "x", "domain": "positive_real"}
XN = {"name": "x", "domain": "nonneg_real"}
Y = {"name": "y", "domain": "real"}
T_ = {"name": "t", "domain": "real"}


def xc(*cs):
    return {"name": "x", "domain": "real", "constraints": list(cs)}


def ir(kind, params, givens=(), vars_=None, shape="set", dod=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    if functions:
        d["functions"] = functions
    return d


def sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


DNE = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}


def lim(expr, to, givens=(), vars_=None, dod=None, side=None):
    p = {"expr": expr, "var": "x", "to": to}
    if side:
        p["side"] = side
    return ir("limit", p, givens, vars_, shape="scalar", dod=dod)


def der(f, at=None, givens=(), vars_=None, dod=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    return ir("derivative", p, givens, vars_, shape="scalar" if at is not None else "expression", dod=dod)


def tan(f, at, givens=(), vars_=None, dod=None):
    return ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, givens, list(vars_ or [X]) + [Y],
              shape="equation", dod=dod)


def anti(f, givens=(), vars_=None, dod=None):
    return ir("antiderivative", {"integrand": f, "var": "x"}, givens, vars_, shape="expression", dod=dod)


def ext(f, which, interval, givens=(), vars_=None, dod=None):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return ir("extremum", p, givens, vars_, shape="scalar", dod=dod)


def simp(e, givens=(), vars_=None):
    return ir("simplify_expression", {"expr": e}, givens, vars_, shape="expression")


# the ways of writing one condition on x: (label, givens, vars, dod)
def writings(cond, decl=None):
    out = [("constraint", [], [xc(cond)], None), ("given", [cond], [X], None), ("dod", [], [X], cond)]
    if decl:
        out.insert(0, ("declared", [], [{"name": "x", "domain": decl}], None))
    return out


def cases_a():
    out = []
    for w, g, v, d in writings("x > 0", "positive_real"):
        q = lim("Abs(x)/x", "0", g, v, d)
        out.append((f"lim |x|/x at 0, {w} x > 0: 1 [right, from inside]", q, sol("1"), OK, None))
        out.append((f"lim |x|/x at 0, {w} x > 0: DNE [wrong]", q, DNE, NOTOK, None))
        out.append((f"lim |x|/x at 0, {w} x > 0: -1 [wrong]", q, sol("-1"), NOTOK, None))
        q = lim("x", "-oo", g, v, d)
        out.append((f"lim x at -oo, {w} x > 0: -oo [not approached]", q, sol("-oo"), UNK, None))
        q = lim("Abs(x)/x", "0", g, v, d, side="-")
        out.append((f"lim |x|/x at 0-, {w} x > 0: -1 [not approached]", q, sol("-1"), UNK, None))
        q = lim("x*log(x)", "0", g, v, d)
        out.append((f"lim x log x at 0, {w} x > 0: 0 [right]", q, sol("0"), NOTNO, None))
    for w, g, v, d in writings("x > 1"):
        q = lim("x", "0", g, v, d)
        out.append((f"lim x at 0, {w} x > 1: 0 [not approached]", q, sol("0"), UNK, None))
        q = lim("floor(x)", "1", g, v, d)
        out.append((f"lim floor(x) at 1, {w} x > 1: 1 [right]", q, sol("1"), NOTNO, None))
        out.append((f"lim floor(x) at 1, {w} x > 1: DNE [wrong]", q, DNE, NOTOK, None))
    for w, g, v, d in writings("x < 0"):
        q = lim("1/x", "0", g, v, d)
        out.append((f"lim 1/x at 0, {w} x < 0: -oo [right]", q, sol("-oo"), NOTNO, None))
        out.append((f"lim 1/x at 0, {w} x < 0: DNE [wrong]", q, DNE, NOTOK, None))
        q = lim("x", "oo", g, v, d)
        out.append((f"lim x at oo, {w} x < 0: oo [not approached]", q, sol("oo"), UNK, None))
    for w, g, v, d in writings("x >= 0", "nonneg_real"):
        q = lim("Abs(x)/x", "0", g, v, d)
        out.append((f"lim |x|/x at 0, {w} x >= 0: 1 [right]", q, sol("1"), OK, None))
        out.append((f"lim |x|/x at 0, {w} x >= 0: DNE [wrong]", q, DNE, NOTOK, None))
    for w, g, v, d in writings("0 < x < 2")[:2]:
        q = lim("Abs(x - 2)/(x - 2)", "2", g, v, d)
        out.append((f"lim |x-2|/(x-2) at 2, {w} 0<x<2: -1 [right]", q, sol("-1"), NOTNO, None))
        out.append((f"lim |x-2|/(x-2) at 2, {w} 0<x<2: DNE [wrong]", q, DNE, NOTOK, None))
        q = lim("x", "3", g, v, d)
        out.append((f"lim x at 3, {w} 0<x<2: 3 [not approached]", q, sol("3"), UNK, None))
    # a region of two pieces: 2 is approached from the right only
    q = lim("Abs(x - 2)/(x - 2)", "2", ["x < 1 or x > 2"])
    out.append(("lim |x-2|/(x-2) at 2, given x<1 or x>2: 1 [right]", q, sol("1"), NOTNO, None))
    out.append(("lim |x-2|/(x-2) at 2, given x<1 or x>2: DNE [wrong]", q, DNE, NOTOK, None))
    q = lim("Abs(x - 1)/(x - 1)", "1", ["x < 1 or x > 2"])
    out.append(("lim |x-1|/(x-1) at 1, given x<1 or x>2: -1 [right]", q, sol("-1"), NOTNO, None))
    out.append(("lim |x-1|/(x-1) at 1, given x<1 or x>2: DNE [wrong]", q, DNE, NOTOK, None))
    q = lim("x", "3/2", ["x < 1 or x > 2"])
    out.append(("lim x at 3/2, given x<1 or x>2: 3/2 [not approached]", q, sol("3/2"), UNK, None))
    # a condition naming a free parameter: the region is unknown
    q = lim("Abs(x)/x", "0", ["x > b"], [X, {"name": "b"}])
    out.append(("lim |x|/x at 0, given x > b (b free): 1", q, sol("1"), UNK, None))
    out.append(("lim |x|/x at 0, given x > b (b free): DNE", q, DNE, UNK, None))
    q = lim("Abs(x)/x", "0", ["x > b", "b = 0"], [X, {"name": "b"}])
    out.append(("lim |x|/x at 0, given x > b, b = 0: 1 [right]", q, sol("1"), NOTNO, None))
    out.append(("lim |x|/x at 0, given x > b, b = 0: DNE [wrong]", q, DNE, NOTOK, None))
    # an isolated point of the region is not approached
    q = lim("x", "0", ["x**2*(x - 1) >= 0"])
    out.append(("lim x at 0, given x**2 (x-1) >= 0 (0 isolated): 0", q, sol("0"), UNK, None))
    return out


def cases_b():
    out = []
    for w, g, v, d in writings("x >= 0", "nonneg_real"):
        out.append((f"derivative |x| at 0, {w} x >= 0: DNE", der("Abs(x)", "0", g, v, d), DNE, UNK, None))
        out.append((f"derivative |x| at 0, {w} x >= 0: 1", der("Abs(x)", "0", g, v, d), sol("1"), UNK, None))
        out.append((f"tangent |x| at 0, {w} x >= 0: y = x", tan("Abs(x)", "0", g, v, d), sol("y = x", "equation"), UNK,
                    None))
        out.append((f"tangent |x| at 0, {w} x >= 0: DNE", tan("Abs(x)", "0", g, v, d), DNE, UNK, None))
    for w, g, v, d in writings("x < 2"):
        out.append((f"derivative x**2 at 3, {w} x < 2: 6", der("x**2", "3", g, v, d), sol("6"), UNK, None))
        out.append((f"derivative x**2 at 1, {w} x < 2: 2 [right]", der("x**2", "1", g, v, d), sol("2"), OK, None))
        out.append((f"derivative x**2 at 1, {w} x < 2: 3 [wrong]", der("x**2", "1", g, v, d), sol("3"), NO, None))
        out.append((f"tangent x**2 at 1, {w} x < 2: y = 2x - 1", tan("x**2", "1", g, v, d), sol("y = 2*x - 1", "equation"),
                    OK, None))
    out.append(("derivative |x| at 0, given x >= b, b = 0: 1", der("Abs(x)", "0", ["x >= b", "b = 0"],
                                                                      [X, {"name": "b"}]), sol("1"), UNK, None))
    out.append(("derivative |x| at 0, given x >= b (b free): 1", der("Abs(x)", "0", ["x >= b"], [X, {"name": "b"}]),
                sol("1"), UNK, None))
    out.append(("derivative |x| at 0, given x >= 0 or x <= -1: DNE", der("Abs(x)", "0", ["x >= 0 or x <= -1"]), DNE,
                UNK, None))
    # the expression form: compared on the region the given leaves
    out.append(("derivative |x| (expr), given x > 0: 1 [right]", der("Abs(x)", None, ["x > 0"]), sol("1", "expression"),
                NOTNO, None))
    out.append(("derivative |x| (expr), given x > 0: -1 [wrong]", der("Abs(x)", None, ["x > 0"]),
                sol("-1", "expression"), NOTOK, None))
    # a region without interior: the derivative function has nowhere to live (4 is 2x there: never refuted)
    out.append(("derivative x**2 (expr), given x = 2: 4", der("x**2", None, ["x = 2"]), sol("4", "expression"), UNK,
                None))
    out.append(("derivative x**2 (expr), given x = 2: 2*x", der("x**2", None, ["x = 2"]), sol("2*x", "expression"), UNK,
                None))
    return out


B_ = {"name": "b", "domain": "real"}


def cases_c():
    out = []
    XB = [X, B_]
    q = ext("x", "max", "[0, b]", ["b = 3"], XB)
    out.append(("max x on [0, b], b = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max x on [0, b], b = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("x", "min", "[b, 5]", ["b = 1"], XB)
    out.append(("min x on [b, 5], b = 1: 5 [wrong]", q, sol("5"), NOTOK, None))
    out.append(("min x on [b, 5], b = 1: 1 [right]", q, sol("1"), NOTNO, None))
    q = ext("x", "max", "[b, 1]", ["b = 5"], XB)
    out.append(("max x on [b, 1], b = 5 (empty): 1", q, sol("1"), NOTOK, None))
    out.append(("max x on [b, 1], b = 5 (empty): 5", q, sol("5"), NOTOK, None))
    q = ext("x", "max", "[0, b]", [], [X, {"name": "b", "domain": "real", "constraints": ["b = 3"]}])
    out.append(("max x on [0, b], constraint b = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max x on [0, b], constraint b = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("x", "max", "Interval(0, b)", ["b = 3"], XB)
    out.append(("max x on Interval(0, b), b = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max x on Interval(0, b), b = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("x", "max", "[0, b]", [], [X, {"name": "b", "domain": "positive_real"}])
    out.append(("max x on [0, b], b positive free: 0 [wrong]", q, sol("0"), NOTOK, None))
    q = ext("x", "max", "[0, b]", [], XB)
    out.append(("max x on [0, b], b free: 0", q, sol("0"), NOTOK, None))
    q = ext("x", "max", "[0, b]", ["b > 5"], XB)
    out.append(("max x on [0, b], b > 5: 0 [wrong]", q, sol("0"), NOTOK, None))
    q = ext("x", "argmax", "[0, b]", ["b = 3"], XB)
    out.append(("argmax x on [0, b], b = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("argmax x on [0, b], b = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("x", "min", "[0, 2*b]", ["b = 3"], XB)
    out.append(("min -x on [0, 2b], b = 3... min x: 6 [wrong]", q, sol("6"), NOTOK, None))
    out.append(("min x on [0, 2b], b = 3: 0 [right]", q, sol("0"), NOTNO, None))
    q = ext("exp(x)", "min", "[b, 0]", ["b = -1"], XB)
    out.append(("min e^x on [b, 0], b = -1: 1 [wrong]", q, sol("1"), NOTOK, None))
    out.append(("min e^x on [b, 0], b = -1: exp(-1) [right]", q, sol("exp(-1)"), NOTNO, None))
    q = ext("x - b", "max", "[0, 1]", ["b = 3"], XB)
    out.append(("max x - b on [0, 1], b = 3: -2 [right]", q, sol("-2"), NOTNO, None))
    out.append(("max x - b on [0, 1], b = 3: 1 [wrong]", q, sol("1"), NOTOK, None))
    q = ext("x", "min", "[-b, b]", ["b = 2"], XB)
    out.append(("min x on [-b, b], b = 2: -2 [right]", q, sol("-2"), NOTNO, None))
    out.append(("min x on [-b, b], b = 2: 2 [wrong]", q, sol("2"), NOTOK, None))
    q = ext("x", "max", "(0, b)", ["b = 3"], XB)
    out.append(("max x on (0, b), b = 3: 0 [no max]", q, sol("0"), NOTOK, None))
    q = ext("x", "max", "[0, b]", ["b = 3", "b = 4"], XB)
    out.append(("max x on [0, b], b = 3 and b = 4: 3", q, sol("3"), NOTOK, None))
    q = ext("x", "max", "[0, b]", ["b = log(-1)"], XB)
    out.append(("max x on [0, b], b = log(-1): 0", q, sol("0"), NOTOK, None))
    q = ext("x", "max", "[a, b]", ["a = 1", "b = 3"], [X, {"name": "a"}, B_])
    out.append(("max x on [a, b], a = 1, b = 3: 3 [right]", q, sol("3"), NOTNO, None))
    out.append(("max x on [a, b], a = 1, b = 3: 1 [wrong]", q, sol("1"), NOTOK, None))
    q = ext("x", "local_max", "[0, b]", ["b = 3"], XB)
    out.append(("local_max x on [0, b], b = 3: 3", q, sol("3"), NOTOK, None))
    # the verifiers' variants
    q = ext("x**2", "max", "[-1, b]", ["b = 2"], XB)
    out.append(("max x**2 on [-1, b], b = 2: 1 [wrong]", q, sol("1"), NOTOK, None))
    out.append(("max x**2 on [-1, b], b = 2: 4 [right]", q, sol("4"), NOTNO, None))
    q = ext("x**2", "min", "[a, b]", ["a = 1", "b = 4"], [X, {"name": "a"}, B_])
    out.append(("min x**2 on [a, b], a = 1, b = 4: 16 [wrong]", q, sol("16"), NOTOK, None))
    out.append(("min x**2 on [a, b], a = 1, b = 4: 1 [right]", q, sol("1"), NOTNO, None))
    q = ext("cos(x)", "min", "[0, b]", ["b = 3"], XB)
    out.append(("min cos x on [0, b], b = 3: 1 [wrong]", q, sol("1"), NOTOK, None))
    out.append(("min cos x on [0, b], b = 3: cos(3) [right]", q, sol("cos(3)"), NOTNO, None))
    q = ext("x", "min", "(0, b]", ["b = 3"], XB)
    out.append(("min x on (0, b], b = 3: 3 [wrong]", q, sol("3"), NOTOK, None))
    q = ext("(x - b)**2", "min", "[0, 5]", ["b = 2"], XB)
    out.append(("min (x - b)**2 on [0, 5], b = 2: 4 [wrong]", q, sol("4"), NOTOK, None))
    out.append(("min (x - b)**2 on [0, 5], b = 2: 0 [right]", q, sol("0"), NOTNO, None))
    q = ext("sin(x)", "min", "[0, b]", ["b = pi"], XB)
    out.append(("min sin x on [0, b], b = pi: 1 [wrong]", q, sol("1"), NOTOK, None))
    out.append(("min sin x on [0, b], b = pi: 0 [right]", q, sol("0"), NOTNO, None))
    q = ext("x**2", "min", "[b, 2]", ["b = -1"], XB)
    out.append(("min x**2 on [b, 2], b = -1: 1 [wrong]", q, sol("1"), NOTOK, None))
    out.append(("min x**2 on [b, 2], b = -1: 0 [right]", q, sol("0"), NOTNO, None))
    # a written condition naming the parameter: x + 0*sqrt(b - x) is x after parsing (review of d4e)
    q = ext("x + 0*sqrt(b - x)", "max", "[0, 1]", ["b = 1/2"], XB)
    out.append(("max x + 0*sqrt(b - x) on [0, 1], b = 1/2: 1 [undefined on (1/2, 1]]", q, sol("1"), NOTOK, None))
    q = ext("x + 0*sqrt(b - x)", "max", "[0, 1]", [], XB)
    out.append(("max x + 0*sqrt(b - x) on [0, 1], b free: 1", q, sol("1"), UNK, None))
    q = ext("x + 0*sqrt(b - x)", "max", "[0, 1]", ["b = 2"], XB)
    out.append(("max x + 0*sqrt(b - x) on [0, 1], b = 2: 1 [right]", q, sol("1"), NOTNO, None))
    return out


A_ = {"name": "a", "domain": "real"}


def cases_d():
    out = []
    XA = [X, A_]
    q = ext("a*x", "max", "[0, 1]", ["a = 3"], XA)
    out.append(("max a*x on [0, 1], a = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max a*x on [0, 1], a = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("a*x", "argmax", "[0, 1]", ["a = 3"], XA)
    out.append(("argmax a*x on [0, 1], a = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("argmax a*x on [0, 1], a = 3: 1 [right]", q, sol("1"), NOTNO, None))
    q = ext("a*x", "min", "[0, 1]", ["a = -3"], XA)
    out.append(("min a*x on [0, 1], a = -3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("min a*x on [0, 1], a = -3: -3 [right]", q, sol("-3"), NOTNO, None))
    q = ext("x**2 + a", "max", "[0, 1]", ["a = 3"], XA)
    out.append(("max x**2 + a on [0, 1], a = 3: 4 [right]", q, sol("4"), NOTNO, None))
    out.append(("max x**2 + a on [0, 1], a = 3: 3 [wrong]", q, sol("3"), NOTOK, None))
    q = ext("a*x", "max", "[0, 1]", [], [X, {"name": "a", "domain": "real", "constraints": ["a = 3"]}])
    out.append(("max a*x on [0, 1], constraint a = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max a*x on [0, 1], constraint a = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("n*x", "max", "[0, 1]", ["n = 3"], [X, {"name": "n", "domain": "positive_integer"}])
    out.append(("max n*x on [0, 1], n posint = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max n*x on [0, 1], n posint = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("a*x", "max", "[0, 1]", [], XA)
    out.append(("max a*x on [0, 1], a free: 0", q, sol("0"), NOTOK, None))
    out.append(("max a*x on [0, 1], a free: a", q, sol("a"), NOTOK, None))
    q = ext("a*x", "max", "[0, 1]", ["a > 0"], XA)
    out.append(("max a*x on [0, 1], a > 0 free: 0", q, sol("0"), NOTOK, None))
    q = ext("x*Sum(k, (k, 1, n))", "max", "[0, 1]", ["n = 3"], [X, {"name": "k", "domain": "integer"},
                                                                  {"name": "n", "domain": "integer"}])
    out.append(("max x*Sum(k,1..n) on [0, 1], n = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max x*Sum(k,1..n) on [0, 1], n = 3: 6 [right]", q, sol("6"), NOTNO, None))
    q = ext("a*x**2", "max", "[-1, 2]", ["a = 1"], XA)
    out.append(("max a*x**2 on [-1, 2], a = 1: 4 [right]", q, sol("4"), NOTNO, None))
    out.append(("max a*x**2 on [-1, 2], a = 1: 1 [wrong]", q, sol("1"), NOTOK, None))
    q = ext("exp(a*x)", "min", "[0, 1]", ["a = -1"], XA)
    out.append(("min exp(a x) on [0, 1], a = -1: 1 [wrong]", q, sol("1"), NOTOK, None))
    out.append(("min exp(a x) on [0, 1], a = -1: exp(-1) [right]", q, sol("exp(-1)"), NOTNO, None))
    q = ext("a*x", "max", "[0, 1]", ["3 = a"], XA)
    out.append(("max a*x on [0, 1], 3 = a: 0 [wrong]", q, sol("0"), NOTOK, None))
    q = ext("a*x - x**2", "max", None, ["a = 2"], XA)
    out.append(("max a*x - x**2 (no interval), a = 2: 1 [right]", q, sol("1"), NOTNO, None))
    out.append(("max a*x - x**2 (no interval), a = 2: 0 [wrong]", q, sol("0"), NOTOK, None))
    q = ext("x**3 - a", "max", "[0, 2]", ["a = 1"], XA)
    out.append(("max x**3 - a on [0, 2], a = 1: 7 [right]", q, sol("7"), NOTNO, None))
    # candidates whose value is no number: never dropped silently
    q = ext("x + x*pi**I", "max", "[0, 1]", [], [X])
    out.append(("max x + x*pi**I on [0, 1] (complex values): 0", q, sol("0"), NOTOK, None))
    # the verifiers' variants
    q = ext("x**3 - 3*a*x", "local_max", "Reals", ["a = 1"], XA)
    out.append(("local_max x**3 - 3ax on R, a = 1: 2 [right]", q, sol("2"), NOTNO, None))
    out.append(("local_max x**3 - 3ax on R, a = 1: 0 [wrong]", q, sol("0"), NOTOK, None))
    q = ext("x**3 - 3*a*x", "local_argmax", "Reals", ["a = 1"], XA)
    out.append(("local_argmax x**3 - 3ax on R, a = 1: -1 [right]", q, sol("-1"), NOTNO, None))
    out.append(("local_argmax x**3 - 3ax on R, a = 1: 0 [wrong]", q, sol("0"), NOTOK, None))
    q = ext("x**3 - 3*a*x", "local_max", "Reals", [], XA)
    out.append(("local_max x**3 - 3ax on R, a free: 2", q, sol("2"), UNK, None))
    q = ext("a*x + c", "max", "[0, 1]", ["a = 2", "c = 1"], XA + [{"name": "c"}])
    out.append(("max a*x + c on [0, 1], a = 2, c = 1: 3 [right]", q, sol("3"), NOTNO, None))
    out.append(("max a*x + c on [0, 1], a = 2, c = 1: 1 [wrong]", q, sol("1"), NOTOK, None))
    q = ext("a*x", "max", None, ["a = 3"], [{"name": "x", "domain": "real", "constraints": ["x >= 0", "x <= 1"]}, A_])
    out.append(("max a*x (x in [0, 1] by constraints), a = 3: 0 [wrong]", q, sol("0"), NOTOK, None))
    out.append(("max a*x (x in [0, 1] by constraints), a = 3: 3 [right]", q, sol("3"), NOTNO, None))
    q = ext("(x - a)**2", "max", "[0, 5]", ["a = 3"], XA)
    out.append(("max (x - a)**2 on [0, 5], a = 3: 9 [right]", q, sol("9"), NOTNO, None))
    out.append(("max (x - a)**2 on [0, 5], a = 3: 4 [wrong]", q, sol("4"), NOTOK, None))
    return out


def cases_e():
    out = []
    for w, g, v, d in writings("x > 0", "positive_real"):
        out.append((f"anti 1/x, {w} x > 0: log(-x) [not real]", anti("1/x", g, v, d), sol("log(-x)", "expression"),
                    NOTOK, None))
        out.append((f"anti 1/x, {w} x > 0: log(x) [right]", anti("1/x", g, v, d), sol("log(x)", "expression"),
                    NOTNO, None))
        out.append((f"anti 1/x, {w} x > 0: log(-x) + C [not real]", anti("1/x", g, v, d),
                    sol("log(-x) + C", "expression"), NOTOK, None))
        out.append((f"anti |x|, {w} x > 0: x**2/2 [right]", anti("Abs(x)", g, v, d), sol("x**2/2", "expression"),
                    NOTNO, None))
        out.append((f"anti |x|, {w} x > 0: -x**2/2 [wrong]", anti("Abs(x)", g, v, d), sol("-x**2/2", "expression"),
                    NOTOK, None))
        out.append((f"anti 1/x, {w} x > 0: log(x) + I*pi [not real]", anti("1/x", g, v, d),
                    sol("log(x) + I*pi", "expression"), NOTOK, None))
        out.append((f"anti 2x, {w} x > 0: x**2 + 0*log(-x) [undefined]", anti("2*x", g, v, d),
                    sol("x**2 + 0*log(-x)", "expression"), NOTOK, None))
        out.append((f"anti 2x, {w} x > 0: x**2 + sqrt(-x) - sqrt(-x) [undefined]", anti("2*x", g, v, d),
                    sol("x**2 + sqrt(-x) - sqrt(-x)", "expression"), NOTOK, None))
        out.append((f"anti 1/(2 sqrt x), {w} x > 0: -I*sqrt(-x)", anti("1/(2*sqrt(x))", g, v, d),
                    sol("-I*sqrt(-x)", "expression"), NOTOK, None))
    for w, g, v, d in writings("x < 0", "negative_real"):
        if w == "declared":
            continue
        out.append((f"anti 1/x, {w} x < 0: log(-x) [right]", anti("1/x", g, v, d), sol("log(-x)", "expression"),
                    NOTNO, None))
        out.append((f"anti 1/x, {w} x < 0: log(x) [undefined]", anti("1/x", g, v, d), sol("log(x)", "expression"),
                    NOTOK, None))
        out.append((f"anti |x|, {w} x < 0: -x**2/2 [right]", anti("Abs(x)", g, v, d), sol("-x**2/2", "expression"),
                    NOTNO, None))
        out.append((f"anti |x|, {w} x < 0: x**2/2 [wrong]", anti("Abs(x)", g, v, d), sol("x**2/2", "expression"),
                    NOTOK, None))
    for w, g, v, d in writings("x > 2"):
        out.append((f"anti 1/(x-2), {w} x > 2: log(x-2) [right]", anti("1/(x - 2)", g, v, d),
                    sol("log(x - 2)", "expression"), NOTNO, None))
    out.append(("anti 1/(x-2), given x < 2: log(2-x) [right]", anti("1/(x - 2)", ["x < 2"]),
                sol("log(2 - x)", "expression"), NOTNO, None))
    out.append(("anti 1/(x-2) (R): log(2-x) [wrong]", anti("1/(x - 2)"), sol("log(2 - x)", "expression"), NOTOK, None))
    out.append(("anti 1/x (R): log(Abs(x)) [right]", anti("1/x"), sol("log(Abs(x))", "expression"), NOTNO, None))
    out.append(("anti 1/x (R): log(x) [wrong on x<0]", anti("1/x"), sol("log(x)", "expression"), NOTOK, None))
    # a constant that differs between the pieces of the region: a convention
    out.append(("anti 1/x (R): log|x| + Heaviside(x) [piecewise constant]", anti("1/x"),
                sol("log(Abs(x)) + Heaviside(x)", "expression"), UNK, None))
    out.append(("anti 1/x, given x<-1 or x>1: log|x| + sign(x)", anti("1/x", ["x < -1 or x > 1"]),
                sol("log(Abs(x)) + sign(x)", "expression"), UNK, None))
    out.append(("anti 1/x, given x<-1 or x>1: log|x| [right]", anti("1/x", ["x < -1 or x > 1"]),
                sol("log(Abs(x))", "expression"), NOTNO, None))
    # the complex constant on ℝ
    out.append(("anti 1 (R): x + I [not real]", anti("1"), sol("x + I", "expression"), NOTOK, None))
    out.append(("anti cos x (R): sin(x) + I [not real]", anti("cos(x)"), sol("sin(x) + I", "expression"), NOTOK, None))
    # a region SymPy leaves unsolved is sampled at its own points; none where the integrand is defined: undecided
    out.append(("anti tan(x)**2 + 1, given x > 100: tan(x) + I [not real]", anti("tan(x)**2 + 1", ["x > 100"]),
                sol("tan(x) + I", "expression"), NOTOK, None))
    out.append(("anti tan(x)**2 + 1, given x > 100: tan(x) [right]", anti("tan(x)**2 + 1", ["x > 100"]),
                sol("tan(x)", "expression"), OK, None))
    W = "tan(x)**2 + 1 + 0/((x - 101)*(7*x - 701))"
    out.append((f"anti {W}, given x > 100: tan(x) + I [not real]", anti(W, ["x > 100"]), sol("tan(x) + I", "expression"),
                NOTOK, None))
    # a free parameter in the region
    out.append(("anti 1/x, given x > b (b free): log(x)", anti("1/x", ["x > b"], [X, B_]), sol("log(x)", "expression"),
                NOTOK, None))
    # the verifiers' variants
    for f, c in (("1/x", "log(-3*x)"), ("2/x", "2*log(-x)"), ("1/(2*x)", "log(-x)/2"), ("1/(x + 1)", "log(-x - 1)"),
                 ("1/x", "log(-x) + log(-x) - log(-x)"), ("1/x", "log(-x) - log(-1)")):
        out.append((f"anti {f}, x positive: {c} [not real]", anti(f, [], [XP]), sol(c, "expression"), NOTOK, None))
    out.append(("anti 1/x, dod x in (0, oo): log(-x) [not real]", anti("1/x", [], [X], "x in (0, oo)"),
                sol("log(-x)", "expression"), NOTOK, None))
    out.append(("anti 1/x, dod x in (-oo, 0): log(-x) [right]", anti("1/x", [], [X], "x in (-oo, 0)"),
                sol("log(-x)", "expression"), NOTNO, None))
    out.append(("anti |x|, constraint x > 1: x**2/2 [right]", anti("Abs(x)", [], [xc("x > 1")]),
                sol("x**2/2", "expression"), NOTNO, None))
    out.append(("anti |x| (R): x**2/2 [wrong for x < 0]", anti("Abs(x)"), sol("x**2/2", "expression"), NOTOK, None))
    out.append(("anti |x| (R): x*|x|/2 [right]", anti("Abs(x)"), sol("x*Abs(x)/2", "expression"), NOTNO, None))
    out.append(("anti 1/x, given x < 0: log|x| [right]", anti("1/x", ["x < 0"]), sol("log(Abs(x))", "expression"), NOTNO,
                None))
    out.append(("anti 1/x, given x != 0: log|x| [right]", anti("1/x", ["x != 0"]), sol("log(Abs(x))", "expression"),
                NOTNO, None))
    # two constants on the pieces without a jump function: atan(1/x) + atan(x) is -pi/2 on x < 0, pi/2 on x > 0
    for F in ("log(Abs(x)) + atan(1/x) + atan(x)", "log(x**2)/2 + 2*atan(1/x) + 2*atan(x)"):
        out.append((f"anti 1/x (R): {F} [two constants]", anti("1/x"), sol(F, "expression"), UNK, None))
    out.append(("anti 1/x (R): log|x| + 5 [right]", anti("1/x"), sol("log(Abs(x)) + 5", "expression"), OK, None))
    # a restricted region keeps the proofs read on whole cells
    out.append(("anti 1/x, given x > 1: log|x| [right]", anti("1/x", ["x > 1"]), sol("log(Abs(x))", "expression"),
                OK, None))
    out.append(("anti 1/x, given x > 1: -log|x| [wrong]", anti("1/x", ["x > 1"]), sol("-log(Abs(x))", "expression"),
                NO, None))
    out.append(("derivative log|x| (expr), given x > 1: 1/x [right]", der("log(Abs(x))", None, ["x > 1"]),
                sol("1/x", "expression"), OK, None))
    out.append(("derivative |x| (expr), given x > 1: -1 [wrong]", der("Abs(x)", None, ["x > 1"]),
                sol("-1", "expression"), NOTOK, None))
    return out


def cases_f():
    out = []
    E = "y + at(diff(sqrt(-x), x), x, -1)"
    for decl in ("positive_real", "nonneg_real", "real"):
        V = [{"name": "x", "domain": decl}, Y]
        q = ir("solve_equation", {"var": "y", "equation": E + " = -1/2"}, [], V)
        out.append((f"solve {E} = -1/2, x {decl}: EmptySet [wrong]", q, sol("EmptySet", "set"), NOTOK, None))
        out.append((f"solve {E} = -1/2, x {decl}: {{0}} [right]", q, sol("{0}", "set"), NOTNO, None))
        q = ir("count_roots", {"var": "y", "expr": "y**2 - 1 + at(diff(sqrt(-x), x), x, -1) + 1/2"}, [], V,
               shape="count")
        out.append((f"count_roots y**2-1+at(..)+1/2, x {decl}: 0 [wrong]", q, sol("0", "count"), NOTOK, None))
        out.append((f"count_roots y**2-1+at(..)+1/2, x {decl}: 2 [right]", q, sol("2", "count"), NOTNO, None))
        q = ir("solve_inequality", {"var": "y", "inequality": E + " > -1/2"}, [], V)
        out.append((f"ineq {E} > -1/2, x {decl}: EmptySet [wrong]", q, sol("EmptySet", "set"), NOTOK, None))
        out.append((f"ineq {E} > -1/2, x {decl}: (0, oo) [right]", q, sol("Interval.open(0, oo)", "interval"), NOTNO,
                    None))
        q = ir("domain_of", {"var": "y", "expr": "sqrt(y) + at(diff(sqrt(-x), x), x, -1)"}, [], V)
        out.append((f"domain sqrt(y) + at(..), x {decl}: EmptySet [wrong]", q, sol("EmptySet", "set"), NOTOK, None))
        out.append((f"domain sqrt(y) + at(..), x {decl}: [0, oo) [right]", q, sol("Interval(0, oo)", "interval"), NOTNO,
                    None))
        q = ir("solve_equation", {"var": "y", "equation": "y + at(diff(log(-x), x), x, -1) = -1"}, [], V)
        out.append((f"solve y + at(diff(log(-x)),x,-1) = -1, x {decl}: EmptySet [wrong]", q, sol("EmptySet", "set"),
                    NOTOK, None))
        q = ir("solve_equation", {"var": "y", "equation": "y + Subs(diff(sqrt(-x), x), x, -1) = -1/2"}, [], V)
        out.append((f"solve y + Subs(diff(sqrt(-x)),x,-1) = -1/2, x {decl}: EmptySet [wrong]", q,
                    sol("EmptySet", "set"), NOTOK, None))
        q = ir("solve_equation", {"var": "y", "equation": "y + Sum(at(diff(sqrt(-x), x), x, -k), (k, 1, 1)) = -1/2"},
               [], V + [{"name": "k", "domain": "integer"}])
        out.append((f"solve y + Sum(at(diff..),(k,1,1)) = -1/2, x {decl}: EmptySet [wrong]", q, sol("EmptySet", "set"),
                    NOTOK, None))
    for decl in ("positive_real", "nonneg_real"):
        V = [{"name": "x", "domain": decl}]
        for e in ("Limit(sqrt(x)**2/x, x, -oo)", "Limit(log(x) - log(x) + 1, x, -oo)", "Limit(1 + 0*acos(x), x, -oo)",
                  "limit(sqrt(x)**2/x, x, -oo)", "Limit(sqrt(x)*sqrt(x)/x, x, -oo)"):
            q = ir("evaluate", {"expr": e}, [], V, shape="scalar")
            out.append((f"evaluate {e}, x {decl}: 1 [undefined]", q, sol("1"), UNK, None))
        q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], V, shape="scalar")
        out.append((f"step compute Limit(sqrt(x)**2/x, x, -oo) = 1, x {decl}", q,
                    sol("2", steps=[("compute", "Limit(sqrt(x)**2/x, x, -oo) = 1")]), OK, NOTVER))
        q = ir("solve_equation", {"var": "y", "equation": "y + Limit(log(x) - log(x), x, -oo) = 0"}, [], V + [Y])
        out.append((f"solve y + Limit(log x - log x, x, -oo) = 0, x {decl}: {{0}}", q, sol("{0}", "set"), NOTOK, None))
    q = ir("evaluate", {"expr": "Limit(sqrt(n)**2/n, n, -oo)"}, [], [{"name": "n", "domain": "positive_integer"}],
           shape="scalar")
    out.append(("evaluate Limit(sqrt(n)**2/n, n, -oo), n posint: 1 [undefined]", q, sol("1"), UNK, None))
    q = ir("evaluate", {"expr": "Limit(sqrt(x**2)/x, x, -oo)"}, [], [XP], shape="scalar")
    out.append(("evaluate Limit(sqrt(x**2)/x, x, -oo), x positive: -1 [right]", q, sol("-1"), NOTNO, None))
    out.append(("evaluate Limit(sqrt(x**2)/x, x, -oo), x positive: 1 [wrong]", q, sol("1"), NOTOK, None))
    q = ir("solve_equation", {"var": "y", "equation": "y + at(sqrt(x**2), x, -1) = 1"}, [], [XP, Y])
    out.append(("solve y + at(sqrt(x**2), x, -1) = 1, x positive: {0} [right]", q, sol("{0}", "set"), NOTNO, None))
    out.append(("solve y + at(sqrt(x**2), x, -1) = 1, x positive: {2} [wrong]", q, sol("{2}", "set"), NOTOK, None))
    # the verifiers' variants
    for decl in ("positive_real", "real"):
        V = [{"name": "x", "domain": decl}, Y]
        for e, right in (("y + at(Derivative(sqrt(-x), x), x, -1) = -1/2", "{0}"),
                         ("y + at(diff(sqrt(-x), x, 2), x, -1) = -1/4", "{0}")):
            q = ir("solve_equation", {"var": "y", "equation": e}, [], V)
            out.append((f"solve {e}, x {decl}: EmptySet [wrong]", q, sol("EmptySet", "set"), NOTOK, None))
            out.append((f"solve {e}, x {decl}: {right} [right]", q, sol(right, "set"), NOTNO, None))
        q = ir("solve_equation", {"var": "y", "equation": "y + at(diff(f(x), x), x, -1) = -1/2"}, [], V + [T_],
               functions=[{"name": "f", "args": ["t"], "expr": "sqrt(-t)"}])
        out.append((f"solve y + at(diff(f(x)),x,-1) = -1/2 (f = sqrt(-t)), x {decl}: EmptySet [wrong]", q,
                    sol("EmptySet", "set"), NOTOK, None))
        q = ir("evaluate", {"expr": "at(diff(sqrt(-x), x), x, -1)"}, [], V[:1], shape="scalar")
        out.append((f"evaluate at(diff(sqrt(-x)),x,-1), x {decl}: -1/2 [right]", q, sol("-1/2"), NOTNO, None))
        out.append((f"evaluate at(diff(sqrt(-x)),x,-1), x {decl}: 1/2 [wrong]", q, sol("1/2"), NOTOK, None))
        q = ir("solve_equation", {"var": "y", "equation": "y + at(diff(sqrt(-x), x), x, -1) = -1/2"}, [], V)
        out.append((f"step compute at(diff(sqrt(-x)),x,-1) = -1/2, x {decl}", q,
                    sol("{0}", "set", steps=[("compute", "at(diff(sqrt(-x), x), x, -1) = -1/2")]), NOTNO,
                    {"verified", "unknown", "skipped", None}))
        q = ir("evaluate", {"expr": "Limit(sqrt(x)**2/x, x, -oo, '+')"}, [], V[:1], shape="scalar")
        out.append((f"evaluate Limit(sqrt(x)**2/x, x, -oo, '+'), x {decl}: 1 [undefined]", q, sol("1"), NOTOK, None))
        q = ir("solve_inequality", {"var": "y", "inequality": "y + Limit(log(x) - log(x), x, -oo) > 0"}, [], V)
        out.append((f"ineq y + Limit(log x - log x, x, -oo) > 0, x {decl}: (0, oo)", q,
                    sol("Interval.open(0, oo)", "interval"), NOTOK, None))
        q = ir("solve_equation", {"var": "y", "equation": "y + Limit(log(x) - log(x), x, -oo) = 0"}, [], V)
        out.append((f"step compute Limit(log x - log x, x, -oo) = 0, x {decl}", q,
                    sol("{0}", "set", steps=[("compute", "Limit(log(x) - log(x), x, -oo) = 0")]), NOTOK, NOTVER))
    for decl in ("nonneg_integer", "integer"):
        q = ir("evaluate", {"expr": "Limit(sqrt(n)**2/n, n, -oo)"}, [], [{"name": "n", "domain": decl}], shape="scalar")
        out.append((f"evaluate Limit(sqrt(n)**2/n, n, -oo), n {decl}: 1 [undefined]", q, sol("1"), NOTOK, None))
    return out


def cases_g():
    out = []
    for f, at in (("sqrt(x)**2", "0"), ("x + sqrt(x) - sqrt(x)", "0"), ("x + acos(x) - acos(x)", "1"),
                  ("x + sqrt(1 - x**2) - sqrt(1 - x**2)", "1"), ("x + sqrt(x) - sqrt(x) + sqrt(-x) - sqrt(-x)", "0"),
                  ("Abs(x) + sqrt(x) - sqrt(x)", "0"), ("x + acos(x) - acos(x)", "-1"),
                  ("x + log(x**2*(x - 1)) - log(x**2*(x - 1)) + sqrt(x**2*(x-1)) - sqrt(x**2*(x - 1))", "0")):
        out.append((f"derivative {f} at {at}: 1", der(f, at), sol("1"), UNK, None))
        out.append((f"derivative {f} at {at}: DNE", der(f, at), DNE, UNK, None))
        out.append((f"tangent {f} at {at}: y = x + c", tan(f, at), sol(f"y = x - {at} + {at}", "equation"), UNK, None))
    for N in ("x + log(x) - log(x) + log(-x) - log(-x)", "x + acos(x) - acos(x) + acos(x - 3) - acos(x - 3)",
              "x + sqrt(x - 1) - sqrt(x - 1) + sqrt(-x) - sqrt(-x)"):
        out.append((f"derivative {N} (expr): 1", der(N), sol("1", "expression"), UNK, None))
        out.append((f"derivative {N} at 1: 1", der(N, "1"), sol("1"), UNK, None))
        out.append((f"simplify {N}: x", simp(N), sol("x", "expression"), UNK, None))
        a = "1" + N[1:]
        out.append((f"antiderivative {a}: x", anti(a), sol("x", "expression"), UNK, None))
        out.append((f"max {N} on [0, 1]: 1", ext(N, "max", "[0, 1]"), sol("1"), UNK, None))
    P0 = "log(x) - log(x) + log(-x) - log(-x)"
    out.append((f"simplify {P0}: 0", simp(P0), sol("0", "expression"), UNK, None))
    out.append((f"simplify {P0}: x", simp(P0), sol("x", "expression"), UNK, None))
    # the isolated-point domain {0}: the derivative function has no interior to live on
    I0 = "x + sqrt(x) - sqrt(x) + sqrt(-x) - sqrt(-x)"
    out.append((f"derivative {I0} (expr): 1", der(I0), sol("1", "expression"), UNK, None))
    out.append((f"derivative {I0} (expr): 0", der(I0), sol("0", "expression"), UNK, None))
    out.append(("antiderivative 1 + ... (domain {0}): x", anti("1" + I0[1:]), sol("x", "expression"), UNK, None))
    # right on the domain's interior
    out.append(("derivative Abs(x) + sqrt(x) - sqrt(x) (expr): 1 [right on (0, oo)]", der("Abs(x) + sqrt(x) - sqrt(x)"),
                sol("1", "expression"), NOTNO, None))
    out.append(("derivative Abs(x) + sqrt(x) - sqrt(x) (expr): -1 [wrong]", der("Abs(x) + sqrt(x) - sqrt(x)"),
                sol("-1", "expression"), NOTOK, None))
    out.append(("derivative x + acos(x) - acos(x) at 1/2: 1 [right]", der("x + acos(x) - acos(x)", "1/2"), sol("1"), OK,
                None))
    out.append(("derivative sqrt(x)**2 at 1: 1 [right]", der("sqrt(x)**2", "1"), sol("1"), OK, None))
    out.append(("tangent sqrt(x)**2 at 1: y = x [right]", tan("sqrt(x)**2", "1"), sol("y = x", "equation"), OK, None))
    # an IR function's body
    fn = [{"name": "f", "args": ["x"], "expr": "sqrt(x)**2"}]
    out.append(("derivative f(x) (f = sqrt(x)**2) at 0: 1", ir("derivative", {"f": "f(x)", "var": "x", "at": "0"}, [], [X],
                                                               shape="scalar", functions=fn), sol("1"), UNK, None))
    # the verifiers' variants
    for f, at, c in (("x + asin(x) - asin(x)", "-1", "1"), ("x**2 + sqrt(x - 2) - sqrt(x - 2)", "2", "4"),
                     ("x*sqrt(x)", "0", "0"), ("x + sqrt(1 - x**2) - sqrt(1 - x**2)", "-1", "1")):
        out.append((f"derivative {f} at {at}: {c} [end]", der(f, at), sol(c), UNK, None))
    out.append(("tangent x**2 + sqrt(1 - x**2) - sqrt(1 - x**2) at 1: y = 2x - 1 [end]",
                tan("x**2 + sqrt(1 - x**2) - sqrt(1 - x**2)", "1"), sol("y = 2*x - 1", "equation"), UNK, None))
    N2 = "log(x) - log(x) + log(-x) - log(-x)"
    out.append((f"derivative x**2 + {N2} at 1: 2", der("x**2 + " + N2, "1"), sol("2"), UNK, None))
    out.append(("derivative Abs(x) + log(x) - log(x) (expr): 1 [right on (0, oo)]", der("Abs(x) + log(x) - log(x)"),
                sol("1", "expression"), NOTNO, None))
    out.append(("simplify x + log(-1) - log(-1): x", simp("x + log(-1) - log(-1)"), sol("x", "expression"), NOTOK, None))
    out.append(("derivative sqrt(x)**2 (expr): 1 [right on (0, oo)]", der("sqrt(x)**2"), sol("1", "expression"), NOTNO,
                None))
    out.append((f"limit x + {N2} at 1: 1", lim("x + " + N2, "1"), sol("1"), UNK, None))
    out.append((f"limit x + {N2} at 1: DNE", lim("x + " + N2, "1"), DNE, UNK, None))
    return out


def cases_h():
    out = []
    V = [XP, T_]
    for f, c in (("Integral(1/t, (t, -oo, x))", "1/x"), ("Integral(1/t**2, (t, -oo, x))", "x**(-2)"),
                 ("Integral(1/sqrt(Abs(t)), (t, -oo, x))", "1/sqrt(x)"), ("Integral(exp(t)/t, (t, -oo, x))", "exp(x)/x"),
                 ("Integral(1/(t + 1), (t, x, oo))", "-1/(x + 1)"), ("Integral(1, (t, x, oo))", "-1"),
                 ("Integral(1/t, (t, x, oo))", "-1/x"), ("Integral(t, (t, -oo, x))", "x"),
                 ("Integral(1/(t - 3), (t, x, oo))", "-1/(x - 3)")):
        out.append((f"derivative {f}, x > 0: {c}", ir("derivative", {"f": f, "var": "x"}, [], V, shape="expression"),
                    sol(c, "expression"), UNK, None))
        out.append((f"derivative {f} at 2, x > 0: value", ir("derivative", {"f": f, "var": "x", "at": "2"}, [], V,
                                                              shape="scalar"),
                    sol(str(__import__("sympy").sympify(c).subs("x", 2))), UNK, None))
    q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], V, shape="scalar")
    out.append(("step eq diff(Integral(1/t, (t, -oo, x)), x) = 1/x", q,
                sol("2", steps=[("eq", "diff(Integral(1/t, (t, -oo, x)), x) = 1/x")]), OK, NOTVER))
    q = ir("solve_equation", {"var": "y", "equation": "y + Integral(1/t, (t, -oo, x)) = 0"}, [], V + [Y])
    out.append(("solve y + Integral(1/t,(t,-oo,x)) = 0: EmptySet", q, sol("EmptySet", "set"), NOTNO, None))
    # controls: convergent at the infinite end, no undefined point
    out.append(("derivative Integral(exp(-t), (t, x, oo)), x > 0: -exp(-x) [right]",
                ir("derivative", {"f": "Integral(exp(-t), (t, x, oo))", "var": "x"}, [], V, shape="expression"),
                sol("-exp(-x)", "expression"), NOTNO, None))
    out.append(("derivative Integral(exp(t), (t, -oo, x)), x > 0: exp(x) [right]",
                ir("derivative", {"f": "Integral(exp(t), (t, -oo, x))", "var": "x"}, [], V, shape="expression"),
                sol("exp(x)", "expression"), NOTNO, None))
    out.append(("derivative Integral(1/t**2, (t, x, oo)), x > 0: -1/x**2 [right]",
                ir("derivative", {"f": "Integral(1/t**2, (t, x, oo))", "var": "x"}, [], V, shape="expression"),
                sol("-1/x**2", "expression"), NOTNO, None))
    out.append(("derivative Integral(1/t, (t, 0, x)), x > 0: 1/x (closed by #14)",
                ir("derivative", {"f": "Integral(1/t, (t, 0, x))", "var": "x"}, [], V, shape="expression"),
                sol("1/x", "expression"), UNK, None))
    out.append(("derivative Integral(1/t, (t, 1, x)), x > 0: 1/x [right]",
                ir("derivative", {"f": "Integral(1/t, (t, 1, x))", "var": "x"}, [], V, shape="expression"),
                sol("1/x", "expression"), NOTNO, None))
    # siblings: a sum of a convergent and a divergent integral, poles towards the infinite end, an integral
    # inside an integral; a conditionally convergent one is not proved (never refuted)
    for f, c, want in (("Integral(exp(-t), (t, x, oo)) + Integral(1/t, (t, x, oo))", "-exp(-x) - 1/x", UNK),
                       ("Integral(tan(t)*exp(-t**2), (t, x, oo))", "-tan(x)*exp(-x**2)", UNK),
                       ("Integral(sin(t)/t, (t, x, oo))", "-sin(x)/x", NOTNO),
                       ("Integral(1/(t**2 + 1), (t, -oo, x))", "1/(x**2 + 1)", NOTNO),
                       ("Integral(exp(-t**2), (t, x, oo))", "-exp(-x**2)", NOTNO)):
        out.append((f"derivative {f}, x > 0: {c}", ir("derivative", {"f": f, "var": "x"}, [], V, shape="expression"),
                    sol(c, "expression"), want, None))
    return out


def cases_k():
    out = []
    out.append(("ctl: lim sin(x)/x at 0: 1", lim("sin(x)/x", "0"), sol("1"), OK, None))
    out.append(("ctl: lim |x|/x at 0 (R): DNE", lim("Abs(x)/x", "0"), DNE, OK, None))
    out.append(("ctl: lim |x|/x at 0 (R): 1", lim("Abs(x)/x", "0"), sol("1"), NO, None))
    out.append(("ctl: lim sqrt(x) at 0 (R): 0 (one side, convention)", lim("sqrt(x)", "0"), sol("0"), UNK, None))
    out.append(("ctl: lim 1/x at oo, x > 0: 0", lim("1/x", "oo", ["x > 0"]), sol("0"), OK, None))
    out.append(("ctl: lim (x**2-1)/(x-1) at 1, x > 0: 2", lim("(x**2 - 1)/(x - 1)", "1", ["x > 0"]), sol("2"), OK, None))
    out.append(("ctl: lim (x**2-1)/(x-1) at 1, constraint x != 1: 2", lim("(x**2 - 1)/(x - 1)", "1", [], [xc("x != 1")]),
                sol("2"), OK, None))
    out.append(("ctl: lim sin(ax)/x, a=2: 2", lim("sin(a*x)/x", "0", ["a = 2"], [X, A_]), sol("2"), OK, None))
    out.append(("ctl: derivative x**3 at 2: 12", der("x**3", "2"), sol("12"), OK, None))
    out.append(("ctl: derivative |x| at 0 (R): DNE", der("Abs(x)", "0"), DNE, OK, None))
    out.append(("ctl: derivative x**2 (expr): 2x", der("x**2"), sol("2*x", "expression"), OK, None))
    out.append(("ctl: derivative log(x) (expr): 1/x", der("log(x)"), sol("1/x", "expression"), OK, None))
    out.append(("ctl: derivative sqrt(x) (expr): 1/(2 sqrt x)", der("sqrt(x)"), sol("1/(2*sqrt(x))", "expression"), OK,
                None))
    out.append(("ctl: tangent x**2 at 1: y = 2x - 1", tan("x**2", "1"), sol("y = 2*x - 1", "equation"), OK, None))
    out.append(("ctl: anti 2x: x**2", anti("2*x"), sol("x**2", "expression"), OK, None))
    out.append(("ctl: anti 2x: x**2 + C", anti("2*x"), sol("x**2 + C", "expression"), OK, None))
    out.append(("ctl: anti 1/x: log(x) (R)", anti("1/x"), sol("log(x)", "expression"), NO, None))
    out.append(("ctl: anti 1/x, x positive: log(x)", anti("1/x", [], [XP]), sol("log(x)", "expression"), OK, None))
    out.append(("ctl: anti cos x: sin x", anti("cos(x)"), sol("sin(x)", "expression"), OK, None))
    out.append(("ctl: anti cos x: sin x + 1", anti("cos(x)"), sol("sin(x) + 1", "expression"), OK, None))
    out.append(("ctl: anti 1/sqrt(x): 2 sqrt(x)", anti("1/sqrt(x)"), sol("2*sqrt(x)", "expression"), OK, None))
    out.append(("ctl: max x on [0, 3]: 3", ext("x", "max", "[0, 3]"), sol("3"), OK, None))
    out.append(("ctl: max x on [0, 3]: 0", ext("x", "max", "[0, 3]"), sol("0"), NO, None))
    out.append(("ctl: max 3x on [0, 1]: 3", ext("3*x", "max", "[0, 1]"), sol("3"), OK, None))
    out.append(("ctl: min x**2 - 2x on [0, 3]: -1", ext("x**2 - 2*x", "min", "[0, 3]"), sol("-1"), OK, None))
    out.append(("ctl: argmax -(x-1)**2 on [0, 3]: 1", ext("-(x - 1)**2", "argmax", "[0, 3]"), sol("1"), OK, None))
    out.append(("ctl: max x*Integral(t,(t,0,2)) on [0,1]: 2", ext("x*Integral(t, (t, 0, 2))", "max", "[0, 1]", [], [X, T_]),
                sol("2"), NOTNO, None))
    out.append(("ctl: simplify x/x: 1", simp("x/x"), sol("1", "expression"), NOTNO, None))
    out.append(("ctl: simplify (x**2-1)/(x-1): x + 1", simp("(x**2 - 1)/(x - 1)"), sol("x + 1", "expression"), NOTNO,
                None))
    out.append(("ctl: simplify sin(x)**2 + cos(x)**2: 1", simp("sin(x)**2 + cos(x)**2"), sol("1", "expression"), OK,
                None))
    out.append(("ctl: derivative Integral(t**2, (t, 0, x)) (expr): x**2",
                ir("derivative", {"f": "Integral(t**2, (t, 0, x))", "var": "x"}, [], [X, T_], shape="expression"),
                sol("x**2", "expression"), NOTNO, None))
    out.append(("ctl: solve y + at(diff(x**2, x), x, 3) = 7: {1}",
                ir("solve_equation", {"var": "y", "equation": "y + at(diff(x**2, x), x, 3) = 7"}, [], [XP, Y]),
                sol("{1}", "set"), NOTNO, None))
    out.append(("ctl: evaluate Limit(1/x, x, oo), x positive: 0",
                ir("evaluate", {"expr": "Limit(1/x, x, oo)"}, [], [XP], shape="scalar"), sol("0"), NOTNO, None))
    out.append(("ctl: evaluate Integral(exp(-t), (t, 0, oo)): 1",
                ir("evaluate", {"expr": "Integral(exp(-t), (t, 0, oo))"}, [], [T_], shape="scalar"), sol("1"), NOTNO, None))
    return out



def cases_l():
    """TAN-06 with periodic conditions (on ℝ SymPy leaves them unsolved) and the trigonometric functions whose
    derivative, tangent and primitive must stay decided."""
    out = []
    NT = "log(sin(x)) - log(sin(x)) + log(-sin(x)) - log(-sin(x))"
    out.append(("derivative x + NT (expr; defined nowhere): 1", der("x + " + NT), sol("1", "expression"), UNK, None))
    out.append(("derivative x + NT at 1: 1", der("x + " + NT, "1"), sol("1"), UNK, None))
    out.append(("antiderivative 1 + NT: x", anti("1 + " + NT), sol("x", "expression"), UNK, None))
    out.append(("simplify x + NT: x", simp("x + " + NT), sol("x", "expression"), UNK, None))
    out.append(("limit x + NT at 1: 1", lim("x + " + NT, "1"), sol("1"), UNK, None))
    out.append(("max x + NT on [0, 1]: 1", ext("x + " + NT, "max", "[0, 1]"), sol("1"), UNK, None))
    PT = "sqrt(sin(x)) - sqrt(sin(x)) + sqrt(-sin(x)) - sqrt(-sin(x))"
    out.append(("derivative x + PT (expr; defined at k*pi alone): 1", der("x + " + PT), sol("1", "expression"), UNK, None))
    out.append(("derivative x + PT at 0: 1", der("x + " + PT, "0"), sol("1"), UNK, None))
    out.append(("antiderivative 1 + PT: x", anti("1 + " + PT), sol("x", "expression"), UNK, None))
    MX = "x + log(x) - log(x) + log(sin(x)) - log(sin(x))"
    out.append(("derivative MX (expr): 1 [right]", der(MX), sol("1", "expression"), NOTNO, None))
    out.append(("derivative MX at 1: 1 [right]", der(MX, "1"), sol("1"), OK, None))
    out.append(("derivative MX at 4 (sin 4 < 0): 1", der(MX, "4"), sol("1"), UNK, None))
    AS = "Abs(sin(x)) + sqrt(sin(x)) - sqrt(sin(x))"
    out.append(("derivative AS (expr): cos(x) [right on the domain]", der(AS), sol("cos(x)", "expression"), NOTNO, None))
    out.append(("derivative AS (expr): -cos(x) [wrong]", der(AS), sol("-cos(x)", "expression"), NOTOK, None))
    out.append(("derivative AS at 0 (end): 1", der(AS, "0"), sol("1"), UNK, None))
    out.append(("derivative AS at pi/2: 0 [right]", der(AS, "pi/2"), sol("0"), OK, None))
    for f, at, c in (("tan(x)", "pi/4", "2"), ("sec(x)", "pi/4", "sqrt(2)"), ("cot(x)", "pi/4", "-2"),
                     ("1/(1 + cos(x))", "pi/2", "1"), ("tan(x)**2", "pi/4", "4")):
        out.append((f"derivative {f} at {at}: {c} [right]", der(f, at), sol(c), OK, None))
        out.append((f"derivative {f} at {at}: 0 [wrong]", der(f, at), sol("0"), NO, None))
    out.append(("tangent tan(x) at pi/4: y = 2x - pi/2 + 1 [right]", tan("tan(x)", "pi/4"),
                sol("y = 2*x - pi/2 + 1", "equation"), OK, None))
    out.append(("tangent tan(x) at pi/4: y = 2x [wrong]", tan("tan(x)", "pi/4"), sol("y = 2*x", "equation"), NO, None))
    out.append(("derivative tan(x) (expr): 1/cos(x)**2 [right]", der("tan(x)"), sol("1/cos(x)**2", "expression"), OK,
                None))
    out.append(("derivative tan(x) (expr): 1/sin(x)**2 [wrong]", der("tan(x)"), sol("1/sin(x)**2", "expression"), NO,
                None))
    out.append(("derivative log(sin(x)) (expr): cot(x) [right]", der("log(sin(x))"), sol("cot(x)", "expression"), OK,
                None))
    out.append(("antiderivative 1/cos(x)**2: tan(x) [right]", anti("1/cos(x)**2"), sol("tan(x)", "expression"), OK, None))
    out.append(("antiderivative sec(x)**2: tan(x) + 1 [right]", anti("sec(x)**2"), sol("tan(x) + 1", "expression"), OK,
                None))
    return out


def cases_m():
    """A parameter a given or a declared constraint fixes, read in every task certificate (siblings of TAN-02
    and G4): in the function, the point, the interval, the claim, and in the written conditions, which SymPy
    drops with the parameter (x + 0*sqrt(b - x) is x)."""
    out = []
    AC = {"name": "a", "domain": "real", "constraints": ["a = 3"]}
    for w, g, v in (("given", ["a = 3"], [X, A_]), ("constraint", [], [X, AC])):
        out.append((f"derivative a*x**2 (expr), {w} a = 3: 6*x [right]", der("a*x**2", None, g, v),
                    sol("6*x", "expression"), OK, None))
        out.append((f"derivative a*x**2 (expr), {w} a = 3: 2*a*x [right]", der("a*x**2", None, g, v),
                    sol("2*a*x", "expression"), OK, None))
        out.append((f"derivative a*x**2 (expr), {w} a = 3: 2*x [wrong]", der("a*x**2", None, g, v),
                    sol("2*x", "expression"), NO, None))
        out.append((f"derivative a*x**2 at 1, {w} a = 3: 6 [right]", der("a*x**2", "1", g, v), sol("6"), NOTNO, None))
        out.append((f"derivative a*x**2 at 1, {w} a = 3: 2 [wrong]", der("a*x**2", "1", g, v), sol("2"), NOTOK, None))
        out.append((f"derivative x**3 at a, {w} a = 3: 27 [right]", der("x**3", "a", g, v), sol("27"), NOTNO, None))
        out.append((f"tangent a*x**2 at 1, {w} a = 3: y = 6x - 3 [right]", tan("a*x**2", "1", g, v),
                    sol("y = 6*x - 3", "equation"), NOTNO, None))
        out.append((f"tangent a*x**2 at 1, {w} a = 3: y = 2x - 1 [wrong]", tan("a*x**2", "1", g, v),
                    sol("y = 2*x - 1", "equation"), NOTOK, None))
        out.append((f"anti a*x, {w} a = 3: 3*x**2/2 [right]", anti("a*x", g, v), sol("3*x**2/2", "expression"), NOTNO,
                    None))
        out.append((f"anti a*x, {w} a = 3: x**2/2 [wrong]", anti("a*x", g, v), sol("x**2/2", "expression"), NOTOK, None))
        out.append((f"limit a*x at 1, {w} a = 3: 3 [right]", lim("a*x", "1", g, v), sol("3"), OK, None))
        out.append((f"limit a*x at 1, {w} a = 3: a [right]", lim("a*x", "1", g, v), sol("a"), OK, None))
        out.append((f"limit a*x at 1, {w} a = 3: 1 [wrong]", lim("a*x", "1", g, v), sol("1"), NOTOK, None))
        q = ir("definite_integral", {"integrand": "a*x", "var": "x", "a": "0", "b": "1"}, g, v, shape="scalar")
        out.append((f"defint a*x on [0, 1], {w} a = 3: 3/2 [right]", q, sol("3/2"), NOTNO, None))
        out.append((f"defint a*x on [0, 1], {w} a = 3: 1/2 [wrong]", q, sol("1/2"), NOTOK, None))
    BB = [X, B_]
    S0 = "x + 0*sqrt(b - x)"
    q = ir("definite_integral", {"integrand": S0, "var": "x", "a": "0", "b": "1"}, ["b = 1/2"], BB, shape="scalar")
    out.append((f"defint {S0} on [0, 1], b = 1/2: 1/2 [undefined on (1/2, 1]]", q, sol("1/2"), NOTOK, None))
    q = ir("definite_integral", {"integrand": S0, "var": "x", "a": "0", "b": "1"}, [], BB, shape="scalar")
    out.append((f"defint {S0} on [0, 1], b free: 1/2", q, sol("1/2"), UNK, None))
    q = ir("definite_integral", {"integrand": S0, "var": "x", "a": "0", "b": "1"}, ["b = 2"], BB, shape="scalar")
    out.append((f"defint {S0} on [0, 1], b = 2: 1/2 [right]", q, sol("1/2"), NOTNO, None))
    out.append((f"limit {S0} at 0, b free: 0", lim(S0, "0", [], BB), sol("0"), UNK, None))
    out.append((f"limit {S0} at 0, b = -1 (0 outside its domain): 0", lim(S0, "0", ["b = -1"], BB), sol("0"), NOTOK,
                None))
    out.append((f"limit {S0} at 0, b = 1: 0 [right]", lim(S0, "0", ["b = 1"], BB), sol("0"), NOTNO, None))
    S1 = "x + 0*sqrt(b - x) + 0*sqrt(x - b)"
    out.append((f"derivative {S1} (expr; defined at b alone), b free: 1", der(S1, None, [], BB), sol("1", "expression"),
                UNK, None))
    out.append((f"derivative {S1} (expr), b = 2: 1", der(S1, None, ["b = 2"], BB), sol("1", "expression"), UNK, None))
    out.append((f"derivative {S1} at 2, b = 2: 1", der(S1, "2", ["b = 2"], BB), sol("1"), UNK, None))
    out.append(("antiderivative 1 + 0*sqrt(b - x) + 0*sqrt(x - b), b free: x",
                anti("1 + 0*sqrt(b - x) + 0*sqrt(x - b)", [], BB), sol("x", "expression"), UNK, None))
    out.append((f"derivative {S0} at 0, b free: 1", der(S0, "0", [], BB), sol("1"), UNK, None))
    out.append((f"derivative {S0} at 0, b = 1: 1 [right]", der(S0, "0", ["b = 1"], BB), sol("1"), NOTNO, None))
    out.append((f"derivative {S0} at 0, b = 0 (end): 1", der(S0, "0", ["b = 0"], BB), sol("1"), UNK, None))
    out.append((f"tangent {S0} at 0, b free: y = x", tan(S0, "0", [], BB), sol("y = x", "equation"), UNK, None))
    # bounded from one side only, the side the region leaves open: a half-line for every value of a
    XA = [X, A_]
    out.append(("derivative sqrt(x - a) (expr), a free: 1/(2 sqrt(x - a)) [right]", der("sqrt(x - a)", None, [], XA),
                sol("1/(2*sqrt(x - a))", "expression"), OK, None))
    out.append(("derivative sqrt(a - x) (expr), a free: -1/(2 sqrt(a - x)) [right]", der("sqrt(a - x)", None, [], XA),
                sol("-1/(2*sqrt(a - x))", "expression"), OK, None))
    out.append(("derivative sqrt(x - a) (expr), a free: 1/sqrt(x - a) [wrong]", der("sqrt(x - a)", None, [], XA),
                sol("1/sqrt(x - a)", "expression"), NO, None))
    out.append(("derivative x + 0*sqrt(x - a) + 0*sqrt(5 - x) (expr), a free: 1 [empty for a > 5]",
                der("x + 0*sqrt(x - a) + 0*sqrt(5 - x)", None, [], XA), sol("1", "expression"), UNK, None))
    # a parameter left in the claim is a real constant
    out.append(("anti a (a free): a*x [right]", anti("a", [], XA), sol("a*x", "expression"), OK, None))
    out.append(("anti 1 (a free): x + I*(a**2 + 1) [not real]", anti("1", [], XA), sol("x + I*(a**2 + 1)", "expression"),
                NOTOK, None))
    # the tangent's own dependent variable is never pinned
    out.append(("tangent x**2 at 1, given y = 1: y = 2x - 1 [right]", tan("x**2", "1", ["y = 1"]),
                sol("y = 2*x - 1", "equation"), NOTNO, None))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "K": cases_k, "L": cases_l, "M": cases_m}


def main(out_path=None, groups="ABCDEFGHKLM"):
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
    grp = args[1] if len(args) > 1 else "ABCDEFGHKLM"
    sys.exit(1 if main(out, grp) else 0)
