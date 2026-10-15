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
    N  round 2 (the attack on d4e): false accepts YO-1..YO-6 and the rejections R8, R9
    P  round 2: the coverage R1..R7, decided again by proof only
    Q  round 3 (the attack on round 2): false accepts YO-1..YO-5 (a SymPy limit as a proof of convergence, series_sum
       on an undecided term, the claim's written domain in a derivative, kinks of Max/Min/sign, written givens)
    R  round 3: RK-8, a claim undefined as written where the derivative exists is INCORRECT
    S  round 3: coverage and robustness RK-1..RK-7, decided by proof only
    T  round 4 (the attack on round 3): the false-accept probes of its second pass (tur4/t1..t18)
    Y  round 4: the false-accept probes of its first pass (tur4/s1..s12)
    U  round 4: the unjust-rejection and coverage probes (tur4/sonda_r2.py's own groups)
    V  round 4: the same, tur4/sonda_rk.py's groups
    W  round 4: the repros, the validators' variants and controls, the cases the decisions name (tur4/tekrar.py)
    X  round 5 (the attack on round 4): its false-accept probes as they ran (tur5/p1..p10)
    Z  round 5: the repros, their variants and the controls the decisions name (tur5/tekrar5.py)

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


# --- round 2 (the attack on d4e, 6 Oct 2026): findings D4E-YO-1..6, R1..R9 ----------------------------------
K_ = {"name": "k", "domain": "integer"}
KI_ = {"name": "k", "domain": "positive_integer"}
STEPU = {"unknown", "skipped", None}             # a step whose claim is undefined as written: never verified


def ss(term, lo, hi, givens=(), vars_=None):
    return ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, givens, vars_ or [K_, A_], shape="scalar")


def cf(rec, initial, givens=(), vars_=None):
    return ir("closed_form", {"recurrence": rec, "initial": initial, "var": "n", "name": "a"}, givens,
              vars_ or [{"name": "n", "domain": "positive_integer"}, {"name": "c", "domain": "real"}], shape="expression")


def cases_n():
    """False accepts of the attack (YO-1..YO-6) and the unjust rejection R8, R9."""
    out = []
    AC2 = {"name": "a", "domain": "real", "constraints": ["a = 2"]}
    # YO-1 + R9: series_sum and closed_form read the pinned value; undefined at it: UNKNOWN; 0**0: UNKNOWN
    for w, g, v in (("given", ["a = 2"], [K_, A_]), ("constraint", [], [K_, AC2])):
        out.append((f"series (k-a)/(k-a), k=1..3, {w} a = 2: 3 [0/0 at k = 2]", ss("(k - a)/(k - a)", 1, 3, g, v), sol("3"),
                    UNK, None))
        out.append((f"series 1/(k-a), k=1..3, {w} a = 2: 1/(1-a)+1/(2-a)+1/(3-a)", ss("1/(k - a)", 1, 3, g, v),
                    sol("1/(1 - a) + 1/(2 - a) + 1/(3 - a)"), UNK, None))
        out.append((f"series a*k, k=1..3, {w} a = 2: 12 [right]", ss("a*k", 1, 3, g, v), sol("12"), OK, None))
        out.append((f"series a*k, k=1..3, {w} a = 2: 6*a [right]", ss("a*k", 1, 3, g, v), sol("6*a"), OK, None))
        out.append((f"series a*k, k=1..3, {w} a = 2: 6 [wrong]", ss("a*k", 1, 3, g, v), sol("6"), NO, None))
        out.append((f"series a**k, k=0..3, {w} a = 2: 15 [right]", ss("a**k", 0, 3, g, v), sol("15"), OK, None))
        out.append((f"series k**a, k=1..3, {w} a = 2: 14 [right]", ss("k**a", 1, 3, g, v), sol("14"), OK, None))
    out.append(("series sqrt(a-k), k=1..2, constraint a = 0: sqrt(a-1)+sqrt(a-2) [not real]",
                ss("sqrt(a - k)", 1, 2, [], [K_, {"name": "a", "domain": "real", "constraints": ["a = 0"]}]),
                sol("sqrt(a - 1) + sqrt(a - 2)"), UNK, None))
    out.append(("series a**k, k=0..3, a = 1: (a**4-1)/(a-1) [0/0 claim]", ss("a**k", 0, 3, ["a = 1"]),
                sol("(a**4 - 1)/(a - 1)"), UNK, None))
    out.append(("series a**k, k=0..3, a = 1: 4 [right]", ss("a**k", 0, 3, ["a = 1"]), sol("4"), OK, None))
    out.append(("series a**k, k=0..3, a = 0: 1+a+a**2+a**3 [0**0]", ss("a**k", 0, 3, ["a = 0"]),
                sol("1 + a + a**2 + a**3"), UNK, None))
    out.append(("series a**k, k=0..3, a = 0: 1 [0**0]", ss("a**k", 0, 3, ["a = 0"]), sol("1"), UNK, None))
    out.append(("series 1/(k-a), k=1..3, a = 5: -13/12 [right]", ss("1/(k - a)", 1, 3, ["a = 5"]), sol("-13/12"), OK,
                None))
    out.append(("series literal (k-2)/(k-2), k=1..3: 3", ss("(k - 2)/(k - 2)", 1, 3, [], [K_]), sol("3"), UNK, None))
    out.append(("series literal 0**k, k=0..3: 1 [0**0]", ss("0**k", 0, 3, [], [K_]), sol("1"), UNK, None))
    out.append(("series literal 0**k, k=1..3: 0 [right]", ss("0**k", 1, 3, [], [K_]), sol("0"), NOTNO, None))
    out.append(("closed_form a(n) = c*a(n-1), a(1) = 1, c = 0: c**(n-1) [0**0 at n = 1]",
                cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 0"]), sol("c**(n - 1)", "expression"), UNK, None))
    out.append(("closed_form a(n) = c*a(n-1), a(1) = 1, c = 2: 2**(n-1) [right]",
                cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 2"]), sol("2**(n - 1)", "expression"), OK, None))
    out.append(("closed_form a(n) = c*a(n-1), a(1) = 1, c = 2: c**(n-1) [right]",
                cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 2"]), sol("c**(n - 1)", "expression"), OK, None))
    out.append(("closed_form a(n) = c*a(n-1), a(1) = 1, c = 2: 3**(n-1) [wrong]",
                cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c = 2"]), sol("3**(n - 1)", "expression"), NO, None))
    # YO-2: an integral with numbers for bounds is defined only when proved to converge
    I = "Integral(1/t, (t, 1, oo))"
    V = [T_]
    for e, c in ((f"{I} - {I}", "0"), (f"0*{I} + 1", "1"), (f"{I}/{I}", "1"), (f"{I}**0", "1"),
                 ("0*Integral(1/(t - 1/2), (t, 0, 1)) + 1", "1"), ("0*Integral(1/t**2, (t, -1, 1)) + 1", "1")):
        out.append((f"evaluate {e}: {c} [a divergent integral]", ir("evaluate", {"expr": e}, [], V), sol(c), UNK, None))
    out.append((f"solve y + 0*{I} = 2: {{2}}", ir("solve_equation", {"var": "y", "equation": f"y + 0*{I} = 2"}, [], [Y, T_]),
                sol("{2}", "set"), UNK, None))
    out.append(("derivative x + 0*Integral(1/(t - 1/2), (t, 0, 1)) (expr): 1",
                der("x + 0*Integral(1/(t - 1/2), (t, 0, 1))", None, [], [X, T_]), sol("1", "expression"), UNK, None))
    out.append(("max x + 0*Integral(1/t**2, (t, -1, 1)) on [0, 1]: 1",
                ext("x + 0*Integral(1/t**2, (t, -1, 1))", "max", "[0, 1]", [], [X, T_]), sol("1"), UNK, None))
    q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X, T_])
    out.append((f"step compute 0*{I} = 0", q, sol("2", steps=[("compute", f"0*{I} = 0")]), OK, NOTVER))
    for e, c in (("0*Integral(1/t**2, (t, 1, oo)) + 1", "1"), ("Integral(1/sqrt(t), (t, 0, 1)) - Integral(1/sqrt(t), (t, 0, 1))",
                                                              "0"),
                 ("Integral(exp(-t), (t, 0, oo))", "1"), ("Integral(1/sqrt(t), (t, 0, 1))", "2"),
                 ("Integral(log(t), (t, 0, 1))", "-1"), ("Integral(exp(-t**2), (t, -oo, oo))", "sqrt(pi)"),
                 ("Integral(1/(1 + t**2), (t, -oo, oo))", "pi")):
        out.append((f"evaluate {e}: {c} [right, converges]", ir("evaluate", {"expr": e}, [], V), sol(c), OK, None))
    out.append(("evaluate Integral(cos(t)/(1 + t**2), (t, 0, oo)): pi/(2E) [right]",
                ir("evaluate", {"expr": "Integral(cos(t)/(1 + t**2), (t, 0, oo))"}, [], V), sol("pi/(2*E)"), NOTNO, None))
    # YO-3: the body of Subs / at is read at its own point
    for g, c in ((["x = 1"], "Subs(sqrt(x - 2), x, 1)**2 = -1"),
                 (["x = 1"], "at(diff(log(x - 2) - log(x - 2) + x, x), x, 1) = 1"),
                 (["x = 1"], "Subs(1/(x - 1), x, 1)*0 = 0"),
                 (["x = -5"], "Subs(sqrt(x)**2, x, -1) = -1"),
                 (["x = -5"], "at(diff(sqrt(x)**2, x), x, -1) = 1"),
                 (["x = 3"], "at(diff(sqrt(x)**2, x), x, 0) = 1")):
        q = ir("evaluate", {"expr": "x + 1"}, g, [X])
        val = str(int(g[0].split("= ")[1]) + 1)
        out.append((f"step [{g[0]}] compute {c}", q, sol(val, steps=[("compute", c)]), OK, STEPU))
    q = ir("evaluate", {"expr": "y + 1"}, ["y = 1"], [X, Y])
    out.append(("step [no premise on x] compute Subs(sqrt(x - 2), x, 1)**2 = -1", q,
                sol("2", steps=[("compute", "Subs(sqrt(x - 2), x, 1)**2 = -1")]), OK, STEPU))
    q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X])
    out.append(("step compute Subs(sqrt(x), x, 4) = 2 [right]", q, sol("2", steps=[("compute", "Subs(sqrt(x), x, 4) = 2")]),
                OK, VER))
    out.append(("step compute at(diff(x**2, x), x, 3) = 6 [right]", q,
                sol("2", steps=[("compute", "at(diff(x**2, x), x, 3) = 6")]), OK, VER))
    # YO-4: a pin that makes a Sum / Product term undefined
    V4 = [X, A_, K_]
    for w, g, v in (("given", ["a = 2"], V4), ("constraint", [], [X, AC2, K_])):
        out.append((f"anti 1 + Sum((k-a)/(k-a),(k,1,3)) - 3, {w} a = 2: x",
                    anti("1 + Sum((k - a)/(k - a), (k, 1, 3)) - 3", g, v), sol("x", "expression"), UNK, None))
        out.append((f"anti 1 + Product((k-a)/(k-a),(k,1,3)) - 1, {w} a = 2: x",
                    anti("1 + Product((k - a)/(k - a), (k, 1, 3)) - 1", g, v), sol("x", "expression"), UNK, None))
        out.append((f"derivative x + Sum((k-a)/(k-a),(k,1,3)) - 3 (expr), {w} a = 2: 1",
                    der("x + Sum((k - a)/(k - a), (k, 1, 3)) - 3", None, g, v), sol("1", "expression"), UNK, None))
    out.append(("anti 1 + Sum((k-a)/(k-a),(k,1,3)) - 3, a = 5: x [right]",
                anti("1 + Sum((k - a)/(k - a), (k, 1, 3)) - 3", ["a = 5"], V4), sol("x", "expression"), NOTNO, None))
    # YO-5: a negative constant base with a variable exponent: a convention
    out.append(("derivative x + (-1)**x - (-1)**x (expr): 1", der("x + (-1)**x - (-1)**x"), sol("1", "expression"), UNK,
                None))
    out.append(("derivative x + 0*(-2)**x at 1/2: 1", der("x + 0*(-2)**x", "1/2"), sol("1"), UNK, None))
    out.append(("tangent x + 0*(-2)**x at 1/2: y = x", tan("x + 0*(-2)**x", "1/2"), sol("y = x", "equation"), UNK, None))
    out.append(("anti 1 + (-1)**x - (-1)**x: x", anti("1 + (-1)**x - (-1)**x"), sol("x", "expression"), UNK, None))
    out.append(("limit x + 0*(-1)**x at 1/2: 1/2", lim("x + 0*(-1)**x", "1/2"), sol("1/2"), UNK, None))
    out.append(("limit (-1)**x at 0: 1", lim("(-1)**x", "0"), sol("1"), UNK, None))
    out.append(("limit (-1)**x at 0: DNE", lim("(-1)**x", "0"), DNE, UNK, None))
    out.append(("derivative (-2)**x (expr): (-2)**x*log(-2)", der("(-2)**x"), sol("(-2)**x*log(-2)", "expression"), UNK,
                None))
    out.append(("series (-1)**(k+1)/k**2, k=1..3: 31/36 [right]", ss("(-1)**(k + 1)/k**2", 1, 3, [], [K_]), sol("31/36"),
                OK, None))
    out.append(("evaluate (-1)**n, n integer = 3: -1 [right]", ir("evaluate", {"expr": "(-1)**n"}, ["n = 3"],
                                                                    [{"name": "n", "domain": "integer"}]), sol("-1"), OK, None))
    # YO-6: defined nowhere on the variable's region: the limit has no meaning
    for w, g, v, d in writings("x > 0", "positive_real"):
        q = lim("x + 0*sqrt(-x)", "0", g, v, d)
        out.append((f"limit x + 0*sqrt(-x) at 0, {w} x > 0: DNE", q, DNE, UNK, None))
        out.append((f"limit x + 0*sqrt(-x) at 0, {w} x > 0: 0", q, sol("0"), UNK, None))
        out.append((f"limit x + 0*log(-x) at 2, {w} x > 0: DNE", lim("x + 0*log(-x)", "2", g, v, d), DNE, UNK, None))
        out.append((f"limit x + 0*sqrt(-x) at oo, {w} x > 0: DNE", lim("x + 0*sqrt(-x)", "oo", g, v, d), DNE, UNK, None))
    out.append(("limit x + 0*log(a*x) + 0*log(-x) at 1, a = 1: DNE", lim("x + 0*log(a*x) + 0*log(-x)", "1", ["a = 1"],
                                                                          [X, A_]), DNE, UNK, None))
    out.append(("limit x + 0*log(x) + 0*log(-x) at 1: DNE", lim("x + 0*log(x) + 0*log(-x)", "1"), DNE, UNK, None))
    out.append(("limit sqrt(x) at -1 (R): DNE [the expression's own domain: the convention]", lim("sqrt(x)", "-1"), DNE, OK,
                None))
    # R8: |u(x)|' is compared where f is differentiable
    for f, c, want in (("Abs(x)", "x/Abs(x)", OK), ("Abs(x)", "Abs(x)/x", OK), ("Abs(x)", "x/sqrt(x**2)", OK),
                       ("Abs(x)", "Piecewise((1, x > 0), (-1, x < 0))", OK), ("Abs(x)", "sign(x)", UNK),
                       ("Abs(x)", "-x/Abs(x)", NO), ("Abs(x - 1)", "(x - 1)/Abs(x - 1)", OK),
                       ("Abs(x**2 - 1)", "2*x*(x**2 - 1)/Abs(x**2 - 1)", OK),
                       ("Abs(sin(x))", "cos(x)*sin(x)/Abs(sin(x))", OK), ("Abs(sin(x))", "-cos(x)*sin(x)/Abs(sin(x))", NO),
                       ("Abs(x)**3", "3*x*Abs(x)", OK), ("Abs(x)**3", "3*x**5/Abs(x)**3", NO)):
        out.append((f"derivative {f} (expr): {c}", der(f), sol(c, "expression"), want, None))
    return out


def cases_p():
    """Coverage the attack measured lost (R1..R7): decided again, by proof only."""
    out = []
    AP = {"name": "a", "domain": "positive_real"}
    BP = {"name": "b", "domain": "positive_real"}
    KP = {"name": "k", "domain": "positive_real"}
    NP = {"name": "n", "domain": "positive_integer"}
    # R1: an open condition strictly true at the point, of a continuous function, is a neighbourhood
    out.append(("R1 derivative tan(x**2) at 1: 2 + 2*tan(1)**2", der("tan(x**2)", "1"), sol("2 + 2*tan(1)**2"), OK, None))
    out.append(("R1 derivative tan(x**2) at 1: 2 [wrong]", der("tan(x**2)", "1"), sol("2"), NO, None))
    out.append(("R1 derivative tan(x**2) (expr): 2*x/cos(x**2)**2", der("tan(x**2)"), sol("2*x/cos(x**2)**2", "expression"),
                OK, None))
    out.append(("R1 derivative tan(x**2) (expr): 2/cos(x**2)**2 [wrong]", der("tan(x**2)"),
                sol("2/cos(x**2)**2", "expression"), NO, None))
    out.append(("R1 tangent tan(x**2) at 1", tan("tan(x**2)", "1"), sol("y = (2 + 2*tan(1)**2)*(x - 1) + tan(1)", "equation"),
                OK, None))
    out.append(("R1 anti 2*x/cos(x**2)**2: tan(x**2)", anti("2*x/cos(x**2)**2"), sol("tan(x**2)", "expression"), OK, None))
    out.append(("R1 anti 2*x/cos(x**2)**2: 2*tan(x**2) [wrong]", anti("2*x/cos(x**2)**2"), sol("2*tan(x**2)", "expression"),
                NO, None))
    out.append(("R1 derivative 1/(x - cos(x)) at pi: -1/(pi + 1)**2", der("1/(x - cos(x))", "pi"), sol("-1/(pi + 1)**2"), OK,
                None))
    out.append(("R1 derivative 1/(x - cos(x)) at pi: 1 [wrong]", der("1/(x - cos(x))", "pi"), sol("1"), NO, None))
    out.append(("R1 derivative 1/(x + exp(x)) at 0: -2", der("1/(x + exp(x))", "0"), sol("-2"), OK, None))
    out.append(("R1 derivative 1/(2 + sin(x**2)) at 0: 0", der("1/(2 + sin(x**2))", "0"), sol("0"), OK, None))
    out.append(("R1 derivative x + 0/floor(x) at 1: 1 [an end: floor jumps]", der("x + 0/floor(x)", "1"), sol("1"), UNK, None))
    # R2: a parameter with a declared sign: the domain has interior for every allowed value
    out.append(("R2 derivative asin(x/a) (expr), a > 0: 1/sqrt(a**2 - x**2)", der("asin(x/a)", None, [], [X, AP]),
                sol("1/sqrt(a**2 - x**2)", "expression"), OK, None))
    out.append(("R2 derivative asin(x/a) (expr), a > 0: 2/sqrt(a**2 - x**2) [wrong]", der("asin(x/a)", None, [], [X, AP]),
                sol("2/sqrt(a**2 - x**2)", "expression"), NO, None))
    out.append(("R2 derivative acos(x/a) (expr), a > 0: -1/sqrt(a**2 - x**2)", der("acos(x/a)", None, [], [X, AP]),
                sol("-1/sqrt(a**2 - x**2)", "expression"), OK, None))
    out.append(("R2 derivative sqrt(a**2 - x**2) (expr), a > 0", der("sqrt(a**2 - x**2)", None, [], [X, AP]),
                sol("-x/sqrt(a**2 - x**2)", "expression"), OK, None))
    out.append(("R2 derivative log(a*x + b) (expr), a, b > 0: a/(a*x + b)", der("log(a*x + b)", None, [], [X, AP, BP]),
                sol("a/(a*x + b)", "expression"), OK, None))
    out.append(("R2 derivative log(a*x + b) (expr), a, b > 0: 2*a/(a*x + b) [wrong]", der("log(a*x + b)", None, [], [X, AP, BP]),
                sol("2*a/(a*x + b)", "expression"), NO, None))
    out.append(("R2 derivative log(k*x) (expr), k > 0: 1/x", der("log(k*x)", None, [], [X, KP]), sol("1/x", "expression"),
                OK, None))
    out.append(("R2 derivative log(x**n) (expr), n posint: n/x", der("log(x**n)", None, [], [X, NP]), sol("n/x", "expression"),
                OK, None))
    out.append(("R2 derivative log(a*x + 1) (expr), given a > 0: a/(a*x + 1)", der("log(a*x + 1)", None, ["a > 0"], [X, A_]),
                sol("a/(a*x + 1)", "expression"), OK, None))
    out.append(("R2 derivative sqrt(a**2 - x**2) (expr), a free real (a = 0: {0})", der("sqrt(a**2 - x**2)", None, [], [X, A_]),
                sol("-x/sqrt(a**2 - x**2)", "expression"), UNK, None))
    # R3: the reality of a primitive with declared parameters
    for f, F in (("exp(k*x)", "exp(k*x)/k"), ("sin(k*x)", "-cos(k*x)/k"), ("exp(-k*x)", "-exp(-k*x)/k")):
        out.append((f"R3 anti {f}, k > 0: {F}", anti(f, [], [X, KP]), sol(F, "expression"), OK, None))
    out.append(("R3 anti x**n, n posint: x**(n + 1)/(n + 1)", anti("x**n", [], [X, NP]), sol("x**(n + 1)/(n + 1)", "expression"),
                OK, None))
    out.append(("R3 anti 1/(x**2 + a**2), a > 0: atan(x/a)/a", anti("1/(x**2 + a**2)", [], [X, AP]),
                sol("atan(x/a)/a", "expression"), OK, None))
    out.append(("R3 anti exp(k*x), k > 0: exp(k*x) [wrong]", anti("exp(k*x)", [], [X, KP]), sol("exp(k*x)", "expression"),
                NOTOK, None))
    # R4: a given that restates the curve y = g(x) puts g's written domain on x alone
    out.append(("R4 tangent x**3 at 1, given y = x**3: y = 3x - 2", tan("x**3", "1", ["y = x**3"]), sol("y = 3*x - 2", "equation"),
                OK, None))
    out.append(("R4 tangent x**3 at 1, given y = x**3: y = 3x [wrong]", tan("x**3", "1", ["y = x**3"]), sol("y = 3*x", "equation"),
                NO, None))
    out.append(("R4 tangent sqrt(x) at 4, given y = sqrt(x): y = x/4 + 1", tan("sqrt(x)", "4", ["y = sqrt(x)"]),
                sol("y = x/4 + 1", "equation"), OK, None))
    out.append(("R4 derivative x**2 at 1, given y = x**2: 2", der("x**2", "1", ["y = x**2"], [X, Y]), sol("2"), OK, None))
    out.append(("R4 anti 2x, given y = x**2: x**2", anti("2*x", ["y = x**2"], [X, Y]), sol("x**2", "expression"), OK, None))
    out.append(("R4 limit x**2 at 1, given y = x**2: 1", lim("x**2", "1", ["y = x**2"], [X, Y]), sol("1"), OK, None))
    out.append(("R4 derivative x**3 at -1, y positive, given y = x**3: 3 [x > 0]", der("x**3", "-1", ["y = x**3"],
                                                                                       [X, {"name": "y", "domain": "positive_real"}]),
                sol("3"), UNK, None))
    out.append(("R4 derivative x**3 at 0, given y = x**3, y > 1: 0 [x > 1]", der("x**3", "0", ["y = x**3", "y > 1"], [X, Y]),
                sol("0"), UNK, None))
    # R5: a periodic given on the variable, read near the point
    out.append(("R5 derivative x**2 at 1, given cos(x) > 0: 2", der("x**2", "1", ["cos(x) > 0"]), sol("2"), OK, None))
    out.append(("R5 derivative x**2 at 1, given cos(x) > 0: 3 [wrong]", der("x**2", "1", ["cos(x) > 0"]), sol("3"), NO, None))
    out.append(("R5 derivative x**2 at 2, given cos(x) > 0: 4 [outside]", der("x**2", "2", ["cos(x) > 0"]), sol("4"), UNK, None))
    out.append(("R5 anti cos(x), given cos(x) > 0: sin(x)", anti("cos(x)", ["cos(x) > 0"]), sol("sin(x)", "expression"), OK,
                None))
    out.append(("R5 anti cos(x), given cos(x) > 0: -sin(x) [wrong]", anti("cos(x)", ["cos(x) > 0"]),
                sol("-sin(x)", "expression"), NO, None))
    out.append(("R5 limit x*cos(x) at pi, given cos(x) < 0: -pi", lim("x*cos(x)", "pi", ["cos(x) < 0"]), sol("-pi"), OK, None))
    out.append(("R5 limit x*cos(x) at pi, given cos(x) < 0: pi [wrong]", lim("x*cos(x)", "pi", ["cos(x) < 0"]), sol("pi"), NO,
                None))
    out.append(("R5 limit sin(x)/x at 0, given sin(x) != 0: 1", lim("sin(x)/x", "0", ["sin(x) != 0"]), sol("1"), OK, None))
    out.append(("R5 limit sin(x)/x at 0, given sin(x) != 0: 0 [wrong]", lim("sin(x)/x", "0", ["sin(x) != 0"]), sol("0"), NO,
                None))
    # R6: a primitive continuous across the gap of the region: one constant
    out.append(("R6 anti x/Abs(x): Abs(x)", anti("x/Abs(x)"), sol("Abs(x)", "expression"), OK, None))
    out.append(("R6 anti x/Abs(x): Abs(x) + sign(x) [two constants]", anti("x/Abs(x)"), sol("Abs(x) + sign(x)", "expression"),
                UNK, None))
    out.append(("R6 anti log(Abs(x)) + 1: x*log(Abs(x))", anti("log(Abs(x)) + 1"), sol("x*log(Abs(x))", "expression"), OK, None))
    out.append(("R6 anti 1/cbrt(x)**2: 3*cbrt(x)", anti("1/cbrt(x)**2"), sol("3*cbrt(x)", "expression"), NOTNO, None))
    # R7: convergence at an infinite end, a declared positive parameter, a slow power
    out.append(("R7 derivative Integral(exp(-a*t), (t, x, oo)), a > 0: -exp(-a*x)",
                der("Integral(exp(-a*t), (t, x, oo))", None, [], [X, T_, AP]), sol("-exp(-a*x)", "expression"), OK, None))
    out.append(("R7 derivative Integral(exp(-a*t), (t, x, oo)), a > 0: exp(-a*x) [wrong]",
                der("Integral(exp(-a*t), (t, x, oo))", None, [], [X, T_, AP]), sol("exp(-a*x)", "expression"), NO, None))
    out.append(("R7 derivative Integral(t**(-21/20), (t, x, oo)), x > 0: -x**(-21/20)",
                der("Integral(t**(-21/20), (t, x, oo))", None, [], [XP, T_]), sol("-x**(-21/20)", "expression"), OK, None))
    out.append(("R7 derivative Integral(exp(-a*t), (t, x, oo)), a free: -exp(-a*x)",
                der("Integral(exp(-a*t), (t, x, oo))", None, [], [X, T_, A_]), sol("-exp(-a*x)", "expression"), UNK, None))
    out.append(("R7 derivative Integral(t**(-1), (t, x, oo)), x > 0: -1/x [diverges]",
                der("Integral(t**(-1), (t, x, oo))", None, [], [XP, T_]), sol("-1/x", "expression"), UNK, None))
    return out


# --- round 3 (the attack on d4e's round 2, `d4/saldiri/d4e2/`): 13 findings
NI_ = {"name": "n", "domain": "integer"}
NN_ = {"name": "n", "domain": "natural"}
NR_ = {"name": "n", "domain": "real"}
E3 = "Integral(1/(1 + t**2*cos(t)**2), (t, 0, oo))"
E2 = "Integral(t/(1 + t**4*sin(t)**2), (t, 1, oo))"
E4 = "Integral(t**2/(1 + t**6*sin(t)**2), (t, 1, oo))"
D1 = "Integral(1/(1 + t**2*sin(t)**2), (t, 0, oo))"
D6 = "Integral(1/(1 + t**2*sin(t)**2), (t, -oo, 0))"


def ev1(expr, vars_=None, givens=()):
    return ir("evaluate", {"expr": expr}, givens, vars_ or [T_], shape="scalar")


def cases_q():
    """Round 3, false accepts: YO-1 (a SymPy limit is no proof of convergence), YO-2 (series_sum fails closed and
    reads a pin in every form), YO-3 (the claim's written domain in the derivative), YO-4 (a kink of Max, Min, sign,
    Heaviside, Piecewise), YO-5 (the written definedness of givens, constraints and the domain of discourse)."""
    out = []
    XT = [X, T_]
    # YO-1: an oscillating denominator; SymPy's limit 0 of t**(3/2)*g is no proof (the integrals diverge)
    for name, I in (("E3", E3), ("D1", D1), ("E4", E4), ("D6", D6)):
        out.append((f"YO-1 evaluate 0*{name} + 1: 1 [diverges]", ev1(f"0*{I} + 1"), sol("1"), UNK, None))
    out.append(("YO-1 evaluate D1 - D1: 0 [oo - oo]", ev1(f"{D1} - {D1}"), sol("0"), NOTOK, None))
    out.append(("YO-1 derivative x + 0*E2: 1", der(f"x + 0*{E2}", None, [], XT), sol("1", "expression"), UNK, None))
    out.append(("YO-1 derivative Integral(1/(1 + t**2 cos(t)**2), (t, x, oo)): FTC",
                der("Integral(1/(1 + t**2*cos(t)**2), (t, x, oo))", None, [], XT),
                sol("-1/(1 + x**2*cos(x)**2)", "expression"), UNK, None))
    q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], XT, shape="scalar")
    out.append(("YO-1 step compute E3*0 = 0", q, sol("2", steps=[("compute", f"{E3}*0 = 0")]), OK, NOTVER))
    q = ir("solve_equation", {"var": "y", "equation": f"y + 0*{D1} = 2"}, [], [Y, T_])
    out.append(("YO-1 solve y + 0*D1 = 2: {2}", q, sol("{2}", "set"), UNK, None))
    out.append(("YO-1 evaluate 0*Integral(1/(t**2 + cos(1/t)**2), (t, 0, 1)) + 1: 1 [diverges]",
                ev1("0*Integral(1/(t**2 + cos(1/t)**2), (t, 0, 1)) + 1"), sol("1"), NOTOK, None))
    # convergent controls: a majorant proves them, or nothing is claimed
    out.append(("YO-1 ctrl evaluate 0*Integral(1/(1 + t**2), (t, 0, oo)) + 1: 1", ev1("0*Integral(1/(1 + t**2), (t, 0, oo)) + 1"),
                sol("1"), OK, None))
    out.append(("YO-1 ctrl evaluate 0*Integral(sin(t)/t**2, (t, 1, oo)) + 1: 1 [|sin| <= 1]",
                ev1("0*Integral(sin(t)/t**2, (t, 1, oo)) + 1"), sol("1"), OK, None))
    out.append(("YO-1 ctrl evaluate 0*Integral(exp(-t)*cos(t), (t, 0, oo)) + 1: 1",
                ev1("0*Integral(exp(-t)*cos(t), (t, 0, oo)) + 1"), sol("1"), OK, None))
    out.append(("YO-1 ctrl evaluate 0*Integral(1/(1 + t**4 sin(t)**2), (t, 0, oo)) + 1: 1 [converges, no proof needed]",
                ev1("0*Integral(1/(1 + t**4*sin(t)**2), (t, 0, oo)) + 1"), sol("1"), NOTNO, None))
    out.append(("YO-1 ctrl evaluate 0*Integral(1/t, (t, 1, oo)) + 1: 1 [diverges]", ev1("0*Integral(1/t, (t, 1, oo)) + 1"),
                sol("1"), UNK, None))
    # YO-2: series_sum, written definedness undecided -> UNKNOWN; a pin read in every form
    KAB = [K_, A_, {"name": "b", "domain": "real"}]
    T1 = "(k - a)/(k - a)"
    for label, g, v in (("a = 2", ["a = 2"], None), ("2*a = 4", ["2*a = 4"], None), ("a - 2 = 0", ["a - 2 = 0"], None),
                        ("a**2 = 4, a > 0", ["a**2 = 4", "a > 0"], None), ("a + a = 4", ["a + a = 4"], None),
                        ("sqrt(a) = sqrt(2)", ["sqrt(a) = sqrt(2)"], None), ("a = b, b = 2", ["a = b", "b = 2"], KAB),
                        ("a >= 2, a <= 2", ["a >= 2", "a <= 2"], None),
                        ("constraint 2*a = 4", [], [K_, {"name": "a", "domain": "real", "constraints": ["2*a = 4"]}])):
        out.append((f"YO-2 series {T1}, k=1..3, {label}: 3 [0/0 at k = 2]", ss(T1, 1, 3, g, v), sol("3"), UNK, None))
    for label, g, v in (("2*a = 4", ["2*a = 4"], None), ("a - 2 = 0", ["a - 2 = 0"], None),
                        ("a = b, b = 2", ["a = b", "b = 2"], KAB),
                        ("constraint 2*a = 4", [], [K_, {"name": "a", "domain": "real", "constraints": ["2*a = 4"]}])):
        out.append((f"YO-2 series a*k, k=1..3, {label}: 12 [right]", ss("a*k", 1, 3, g, v), sol("12"), OK, None))
        out.append((f"YO-2 series a*k, k=1..3, {label}: 13 [wrong]", ss("a*k", 1, 3, g, v), sol("13"), NO, None))
    out.append(("YO-2 series (k - a)/(k - a), k=1..3, a free: 3", ss(T1, 1, 3), sol("3"), NOTOK, None))
    for label, g, v in (("given a > 5", ["a > 5"], None),
                        ("constraint a > 5", [], [K_, {"name": "a", "domain": "real", "constraints": ["a > 5"]}])):
        out.append((f"YO-2 series 0*log(k - a) + 1, k=1..2, {label}: 2", ss("0*log(k - a) + 1", 1, 2, g, v), sol("2"),
                    UNK, None))
        out.append((f"YO-2 series sqrt(k - a)**2, k=1..2, {label}: 3 - 2*a", ss("sqrt(k - a)**2", 1, 2, g, v),
                    sol("3 - 2*a"), UNK, None))
    for term, lo, hi, val in (("(-1)**(k/2)", 0, 3, "0"), ("(-9)**(k/2)", 0, 2, "-8 + 3*I"),
                              ("0*(-2)**(k/2) + k", 1, 3, "6"), ("((-1)**(k/2))**2", 0, 3, "0")):
        out.append((f"YO-2 series {term}, k={lo}..{hi}: {val} [negative base]", ss(term, lo, hi, [], [K_]), sol(val), UNK,
                    None))
    out.append(("YO-2 series a**(k/2), k=0..3, a = -1: 0", ss("a**(k/2)", 0, 3, ["a = -1"]), sol("0"), UNK, None))
    # the closed form and the term of a recurrence read the same pins
    out.append(("YO-2 closed form a(n) = c*a(n-1), a(1) = 1, 2*c = 0: c**(n - 1) [0**0 at n = 1]",
                cf("a(n) = c*a(n - 1)", {"1": "1"}, ["2*c = 0"]), sol("c**(n - 1)", "expression"), UNK, None))
    out.append(("YO-2 closed form a(n) = c*a(n-1), a(1) = 1, c - 2 = 0: 2**(n - 1) [right]",
                cf("a(n) = c*a(n - 1)", {"1": "1"}, ["c - 2 = 0"]), sol("2**(n - 1)", "expression"), OK, None))
    q = ir("recurrence_term", {"recurrence": "a(n) = c*a(n - 1)", "initial": {"1": "1"}, "var": "n", "name": "a",
                               "index": "4"}, ["2*c = 4"], [{"name": "n", "domain": "positive_integer"}, {"name": "c"}],
           shape="scalar")
    out.append(("YO-2 recurrence term a(4), a(n) = c*a(n-1), a(1) = 1, 2*c = 4: 8 [right]", q, sol("8"), OK, None))
    # d4b round 8, YO-2 (same root): a written condition no exact class solves is not 'defined' (extremum, series)
    SQ, AC, LG = "sqrt(2**x + x - 3)", "acos(2**x + x - 2)", "log(x + exp(x) - 2)"
    for label, q, c in (("min x**2 + SQ - SQ", ext(f"x**2 + {SQ} - {SQ}", "min", None), "0"),
                        ("min x**2 + SQ - SQ on [-1, 2]", ext(f"x**2 + {SQ} - {SQ}", "min", "[-1, 2]"), "0"),
                        ("max -(x-3)**2 + AC - AC", ext(f"-(x - 3)**2 + {AC} - {AC}", "max", None), "0"),
                        ("max -(x-3)**2*AC/AC on [-5, 5]", ext(f"-(x - 3)**2*{AC}/{AC}", "max", "[-5, 5]"), "0"),
                        ("max -(x-3)**2 + 0*AC on [-5, 5]", ext(f"-(x - 3)**2 + 0*{AC}", "max", "[-5, 5]"), "0"),
                        ("min x**2 + 1 + LG - LG", ext(f"x**2 + 1 + {LG} - {LG}", "min", None), "1"),
                        ("local_min x**2 + SQ - SQ on [-1, 2]", ext(f"x**2 + {SQ} - {SQ}", "local_min", "[-1, 2]"), "0")):
        out.append((f"d4b8-YO-2 extremum {label}: {c} [undefined where read]", q, sol(c), NOTOK, None))
    out.append(("d4b8-YO-2 extremum min x**2 + SQ - SQ: 1 [right where defined]", ext(f"x**2 + {SQ} - {SQ}", "min", None),
                sol("1"), NOTNO, None))
    out.append(("d4b8-YO-2 extremum max -(x-3)**2 + AC - AC on [-5, 5]: -4 [right where defined]",
                ext(f"-(x - 3)**2 + {AC} - {AC}", "max", "[-5, 5]"), sol("-4"), NOTNO, None))
    for term in ("k + sqrt(2**k + k - 3) - sqrt(2**k + k - 3)", "k + acos(2**k + k - 2) - acos(2**k + k - 2)",
                 "k*acos(2**k + k - 2)/acos(2**k + k - 2)", "k + log(k + exp(k) - 2) - log(k + exp(k) - 2)"):
        out.append((f"d4b8-YO-2 series {term}, k=0..3: 6 [a term undefined]", ss(term, 0, 3, [], [K_]), sol("6"), NOTOK,
                    None))
    out.append(("d4b8-YO-2 derivative x + SQ - SQ at 0: 1 [undefined at 0]", der(f"x + {SQ} - {SQ}", "0"), sol("1"), UNK,
                None))
    out.append(("d4b8-YO-2 ctrl derivative x + SQ - SQ at 2: 1", der(f"x + {SQ} - {SQ}", "2"), sol("1"), NOTNO, None))
    out.append(("d4b8-YO-2 ctrl max -(x-3)**2 + acos(x/2) - acos(x/2) on [-5, 5]: 0",
                ext("-(x - 3)**2 + acos(x/2) - acos(x/2)", "max", "[-5, 5]"), sol("0"), NOTOK, None))
    out.append(("YO-2 ctrl series (k - 7)/(k - 7), k=1..3: 3", ss("(k - 7)/(k - 7)", 1, 3, [], [K_]), sol("3"), OK, None))
    out.append(("YO-2 ctrl series (-1)**k, k=0..3: 0", ss("(-1)**k", 0, 3, [], [K_]), sol("0"), OK, None))
    out.append(("YO-2 ctrl series 1/(k*(k + 1)), k=1..oo: 1", ss("1/(k*(k + 1))", 1, "oo", [], [K_]), sol("1"), OK, None))
    out.append(("YO-2 ctrl series 1/(k - a), k=1..3, a = 5: -13/12", ss("1/(k - a)", 1, 3, ["a = 5"]), sol("-13/12"), OK,
                None))
    # YO-3: the claim's written domain in the derivative (a parameter value, a part of the derivative's domain)
    AN = {"name": "a", "domain": "nonneg_real"}
    AP = {"name": "a", "domain": "positive_real"}
    NP = {"name": "n", "domain": "positive_integer"}
    out.append(("YO-3 derivative log(a*x + 1), a >= 0 declared: 1/(x + 1/a) [a = 0]", der("log(a*x + 1)", None, [], [X, AN]),
                sol("1/(x + 1/a)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative log(a*x + 1), a >= 0 declared: a**2/(a**2*x + a) [a = 0]",
                der("log(a*x + 1)", None, [], [X, AN]), sol("a**2/(a**2*x + a)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative log(a*x + 1), given a >= 0: 1/(x + 1/a) [a = 0]", der("log(a*x + 1)", None, ["a >= 0"], [X, A_]),
                sol("1/(x + 1/a)", "expression"), NOTOK, None))
    # pinned to 0 the claim has no value anywhere, where the derivative 0 exists: RK-8 (INCORRECT) or UNKNOWN
    out.append(("YO-3 derivative log(a*x + 1), given a = 0: 1/(x + 1/a)", der("log(a*x + 1)", None, ["a = 0"], [X, A_]),
                sol("1/(x + 1/a)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative asin(x/a), a > 0: (a - 1)/((a - 1)*sqrt(a**2 - x**2)) [a = 1]",
                der("asin(x/a)", None, [], [X, AP]), sol("(a - 1)/((a - 1)*sqrt(a**2 - x**2))", "expression"), NOTOK, None))
    out.append(("YO-3 derivative asin(x/a), a > 0: 1/sqrt(a**2 - x**2) + 0*sqrt(1 - a) [a > 1]",
                der("asin(x/a)", None, [], [X, AP]), sol("1/sqrt(a**2 - x**2) + 0*sqrt(1 - a)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative asin(x/a), a > 0: 1/sqrt(a**2 - x**2) + 0*log(x) [x < 0]",
                der("asin(x/a)", None, [], [X, AP]), sol("1/sqrt(a**2 - x**2) + 0*log(x)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative log(a*x), a > 0: 1/x + 0*sqrt(-x)", der("log(a*x)", None, [], [X, AP]),
                sol("1/x + 0*sqrt(-x)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative log(x**n), n positive integer: n/x + 0*sqrt(-x)", der("log(x**n)", None, [], [X, NP]),
                sol("n/x + 0*sqrt(-x)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative |x|: x/|x| + 0*sqrt(x)", der("Abs(x)"), sol("x/Abs(x) + 0*sqrt(x)", "expression"), NOTOK,
                None))
    out.append(("YO-3 derivative tan(x**2): 2*x*sec(x**2)**2 + 0*sqrt(x)", der("tan(x**2)"),
                sol("2*x*sec(x**2)**2 + 0*sqrt(x)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative tan(x), given cos(x) > 0: sec(x)**2 + 0*sqrt(sin(x))", der("tan(x)", None, ["cos(x) > 0"]),
                sol("sec(x)**2 + 0*sqrt(sin(x))", "expression"), NOTOK, None))
    out.append(("YO-3 derivative log(x): 1/x + 0*sqrt(-x)", der("log(x)"), sol("1/x + 0*sqrt(-x)", "expression"), NOTOK,
                None))
    out.append(("YO-3 derivative x**2: 2*x + 0*sqrt(-x)", der("x**2"), sol("2*x + 0*sqrt(-x)", "expression"), NOTOK, None))
    out.append(("YO-3 derivative x**2: 2*x*(x - 1)/(x - 1)", der("x**2"), sol("2*x*(x - 1)/(x - 1)", "expression"), NOTOK,
                None))
    out.append(("YO-3 ctrl derivative log(a*x + 1), a > 0: a/(a*x + 1)", der("log(a*x + 1)", None, [], [X, AP]),
                sol("a/(a*x + 1)", "expression"), OK, None))
    out.append(("YO-3 ctrl derivative log(a*x + 1), a > 0: 1/(x + 1/a)", der("log(a*x + 1)", None, [], [X, AP]),
                sol("1/(x + 1/a)", "expression"), NOTNO, None))
    out.append(("YO-3 ctrl derivative log(a*x + 1), a > 0: 1/(x + a) [wrong]", der("log(a*x + 1)", None, [], [X, AP]),
                sol("1/(x + a)", "expression"), NOTOK, None))
    out.append(("YO-3 ctrl derivative asin(x/a), a > 0: 1/sqrt(a**2 - x**2)", der("asin(x/a)", None, [], [X, AP]),
                sol("1/sqrt(a**2 - x**2)", "expression"), NOTNO, None))
    out.append(("YO-3 ctrl anti 2*x: x**2 + 0*sqrt(-x)", anti("2*x"), sol("x**2 + 0*sqrt(-x)", "expression"), NO, None))
    # YO-4: a kink of Max, Min, sign, Heaviside, Piecewise: a claim with a value there is a convention
    for f, c in (("Abs(x)", "sign(x)"), ("Max(x, -x)", "sign(x)"), ("x*sign(x)", "sign(x)"), ("Min(x, -x)", "-sign(x)"),
                 ("Max(x, 0)", "(1 + sign(x))/2"), ("Max(sin(x), -sin(x))", "sign(sin(x))*cos(x)"), ("sign(x)", "0"),
                 ("sign(x) + x", "1"), ("sign(x**2 - 1)", "0"), ("sign(sin(x))", "0"),
                 ("tan(x**2) + Max(x, -x)", "2*x*sec(x**2)**2 + sign(x)"), ("tan(x**2) + sign(x)", "2*x*sec(x**2)**2"),
                 ("1/(x - cos(x)) + sign(x)", "-(1 + sin(x))/(x - cos(x))**2"), ("Heaviside(x)", "0"),
                 ("floor(x) + x", "1"), ("Piecewise((x, x > 0), (-x, x <= 0))", "sign(x)"),
                 ("Piecewise((1, x > 0), (0, x <= 0))", "0"), ("Piecewise((x**2, x > 1), (2*x - 1, x <= 1)) + Abs(x)",
                                                                 "Piecewise((2*x, x > 1), (2, x <= 1)) + sign(x)")):
        out.append((f"YO-4 derivative {f}: {c} [value at the kink]", der(f), sol(c, "expression"), UNK, None))
    q = ir("derivative", {"f": "x*Max(x, -x)", "var": "x", "order": 2}, [], [X], shape="expression")
    out.append(("YO-4 2nd derivative x*Max(x, -x): 2*sign(x)", q, sol("2*sign(x)", "expression"), UNK, None))
    for f, c in (("sign(cos(x))", "0"), ("Max(cos(x), -cos(x))", "-sign(cos(x))*sin(x)")):
        out.append((f"YO-4 derivative {f}, given sin(x) > 0: {c} [value at the kink]", der(f, None, ["sin(x) > 0"]),
                    sol(c, "expression"), UNK, None))
    out.append(("YO-4 derivative Max(x, -x): x/|x| [right]", der("Max(x, -x)"), sol("x/Abs(x)", "expression"), NOTNO, None))
    out.append(("YO-4 derivative Max(x, -x): Piecewise((1, x > 0), (-1, x < 0)) [right]", der("Max(x, -x)"),
                sol("Piecewise((1, x > 0), (-1, x < 0))", "expression"), NOTNO, None))
    out.append(("YO-4 derivative Max(x, -x): 1 [wrong]", der("Max(x, -x)"), sol("1", "expression"), NOTOK, None))
    out.append(("YO-4 derivative Piecewise((x**2, x > 1), (2*x - 1, x <= 1)) + |x|: Piecewise + x/|x| [right, C1 at 1]",
                der("Piecewise((x**2, x > 1), (2*x - 1, x <= 1)) + Abs(x)"),
                sol("Piecewise((2*x, x > 1), (2, x <= 1)) + x/Abs(x)", "expression"), NOTNO, None))
    out.append(("YO-4 ctrl derivative tan(x**2)*sign(x): 2*x*sec(x**2)**2*sign(x) [differentiable]",
                der("tan(x**2)*sign(x)"), sol("2*x*sec(x**2)**2*sign(x)", "expression"), NOTNO, None))
    out.append(("YO-4 ctrl derivative x**2*sign(x): 2*Abs(x) [differentiable]", der("x**2*sign(x)"),
                sol("2*Abs(x)", "expression"), NOTNO, None))
    out.append(("YO-4 ctrl derivative x**2*sign(x): 2*x [wrong]", der("x**2*sign(x)"), sol("2*x", "expression"), NOTOK,
                None))
    # YO-5: the written definedness of a given, a constraint and the domain of discourse
    G = "x + 0*sqrt(x - 1) > 0"
    for w, g, v, d in writings(G):
        q = lim("Abs(x - 1)/(x - 1)", "1", g, v, d)
        out.append((f"YO-5 lim |x-1|/(x-1) at 1, {w} {G}: DNE [x >= 1]", q, DNE, NOTOK, None))
        out.append((f"YO-5 lim |x-1|/(x-1) at 1, {w} {G}: 1 [right]", q, sol("1"), NOTNO, None))
        out.append((f"YO-5 derivative |x - 1| at 1, {w} {G}: DNE [end]", der("Abs(x - 1)", "1", g, v, d), DNE, UNK, None))
        q = ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, g, v, dod=d)
        out.append((f"YO-5 solve x**2 = 1/4, {w} {G}: {{1/2}} [no root in x >= 1]", q, sol("{1/2}", "set"), NOTOK, None))
        out.append((f"YO-5 solve x**2 = 1/4, {w} {G}: {{}} [right]", q, sol("EmptySet", "set"), NOTNO, None))
    q = lim("x", "1/2", ["0*log(x - 1) >= 0"])
    out.append(("YO-5 lim x at 1/2, given 0*log(x - 1) >= 0: 1/2 [not approached]", q, sol("1/2"), UNK, None))
    S2 = "sqrt(x)**2 = x"
    for w, g, v, d in writings(S2):
        q = ir("solve_equation", {"var": "x", "equation": "x**2 = 1/4"}, g, v, dod=d)
        out.append((f"YO-5 solve x**2 = 1/4, {w} {S2}: {{-1/2, 1/2}} [x >= 0]", q, sol("{-1/2, 1/2}", "set"), NOTOK, None))
        out.append((f"YO-5 solve x**2 = 1/4, {w} {S2}: {{1/2}} [right]", q, sol("{1/2}", "set"), NOTNO, None))
        q = lim("Abs(x)/x", "0", g, v, d)
        out.append((f"YO-5 lim |x|/x at 0, {w} {S2}: DNE [x >= 0]", q, DNE, NOTOK, None))
        out.append((f"YO-5 lim |x|/x at 0, {w} {S2}: 1 [right]", q, sol("1"), NOTNO, None))
    return out


def cases_r():
    """Round 3, RK-8: a claim undefined, as written, where the derivative exists is INCORRECT (the convention of
    simplify `claim_as_written` and of the antiderivative): the same reason for the locked INCORRECTs."""
    out = []
    for f, c in (("x**2", "2*x**2/x"), ("x**2", "2*x**3/x**2"), ("x**2", "2*x*x/x"), ("x**2", "2*x + log(x) - log(x)"),
                 ("x**2", "2*sqrt(x)**2"), ("x**2", "2*Abs(x)**2/x"), ("x**2", "2*x + 0*log(x)"), ("x**3", "3*x**3/x"),
                 ("x**3", "x**3*(3/x)"), ("x*Abs(x)", "2*x*Abs(x)/x"), ("x*Abs(x)", "2*x**2/Abs(x)"),
                 ("x*Abs(x)", "Abs(x) + x**2/Abs(x)"), ("Abs(x)**3", "3*x**5/Abs(x)**3"),
                 ("sin(x)*Abs(sin(x))", "2*cos(x)*sin(x)**2/Abs(sin(x))"), ("x**2*exp(x)", "x**2*exp(x)*(2/x + 1)"),
                 ("x**2*sin(x)", "x**2*sin(x)*(2/x + cos(x)/sin(x))")):
        out.append((f"RK-8 derivative {f}: {c} [undefined where f' exists]", der(f), sol(c, "expression"), NO, None))
    for f, c in (("x**2", "2*x"), ("Abs(x)", "x/Abs(x)"), ("log(x)", "1/x"), ("sqrt(x)", "1/(2*sqrt(x))"),
                 ("x*Abs(x)", "2*Abs(x)"), ("x**2/x", "1"), ("x**2/x", "x/x"), ("sin(x)*Abs(sin(x))", "2*cos(x)*Abs(sin(x))"),
                 ("tan(x)", "1/cos(x)**2"), ("1/x", "-1/x**2")):
        out.append((f"RK-8 ctrl derivative {f}: {c}", der(f), sol(c, "expression"), OK, None))
    out.append(("RK-8 ctrl derivative x**2, given x > 0: 2*x**2/x [x != 0 on the region]", der("x**2", None, ["x > 0"]),
                sol("2*x**2/x", "expression"), OK, None))
    out.append(("RK-8 ctrl derivative x**2: 2*x + 1 [wrong]", der("x**2"), sol("2*x + 1", "expression"), NO, None))
    return out


def cases_s():
    """Round 3, coverage and robustness (RK-1..RK-7), decided by proof only."""
    out = []
    XT = [X, T_]
    # RK-1: a simple zero of u is a corner of |u|; the textbook derivative undefined exactly there
    for f, c in (("Abs(log(x))", "log(x)/(x*Abs(log(x)))"), ("Abs(sqrt(x) - 1)", "(sqrt(x) - 1)/(2*sqrt(x)*Abs(sqrt(x) - 1))"),
                 ("x*Abs(log(x))", "Abs(log(x)) + log(x)/Abs(log(x))"),
                 ("Abs(log(x))", "Piecewise((1/x, x > 1), (-1/x, x < 1))"), ("Abs(log(x)) + 1", "log(x)/(x*Abs(log(x)))")):
        out.append((f"RK-1 derivative {f}: {c}", der(f), sol(c, "expression"), OK, None))
    out.append(("RK-1 derivative |log x|, given x > 0: log(x)/(x*Abs(log(x)))", der("Abs(log(x))", None, ["x > 0"]),
                sol("log(x)/(x*Abs(log(x)))", "expression"), OK, None))
    out.append(("RK-1 derivative |log x|: -log(x)/(x*Abs(log(x))) [wrong]", der("Abs(log(x))"),
                sol("-log(x)/(x*Abs(log(x)))", "expression"), NO, None))
    out.append(("RK-1 derivative |log x|: sign(log(x))/x [value at the kink]", der("Abs(log(x))"),
                sol("sign(log(x))/x", "expression"), UNK, None))
    out.append(("RK-1 derivative |log x|: Piecewise((1/x, x >= 1), (-1/x, x < 1)) [value at the kink]", der("Abs(log(x))"),
                sol("Piecewise((1/x, x >= 1), (-1/x, x < 1))", "expression"), UNK, None))
    # RK-2: kinks SymPy does not list as a finite set or one progression: an exact refutation off them stands
    for f, c, v in (("Abs(tan(x))", "1/cos(x)**2", [X]), ("Abs(cot(x))", "-1/sin(x)**2", [X]),
                    ("Abs(sin(x))", "cos(x)", [XP]), ("Abs(cos(x))", "-sin(x)", [XP]), ("Abs(x**2 + x + 1)", "2*x", [X])):
        out.append((f"RK-2 derivative {f}, x {v[0]['domain']}: {c} [wrong]", der(f, None, [], v), sol(c, "expression"), NO,
                    None))
    for f, c, v in (("Abs(sin(x))", "cos(x)*Abs(sin(x))/sin(x)", [XP]), ("Abs(cot(x))", "-cot(x)/(sin(x)**2*Abs(cot(x)))", [X]),
                    ("Abs(tan(x))", "tan(x)/(cos(x)**2*Abs(tan(x)))", [X]), ("Abs(x**2 + x + 1)", "2*x + 1", [X])):
        out.append((f"RK-2 derivative {f}, x {v[0]['domain']}: {c} [right]", der(f, None, [], v), sol(c, "expression"),
                    NOTNO, None))
    # RK-3: an integer exponent has no convention
    for nv in (NI_, NN_):
        dn = nv["domain"]
        out.append((f"RK-3 derivative x**2*(-1)**n, n {dn}: 2*x*(-1)**n", der("x**2*(-1)**n", None, [], [X, nv]),
                    sol("2*x*(-1)**n", "expression"), OK, None))
        out.append((f"RK-3 derivative x**2*(-1)**n, n {dn}: 2*x [wrong]", der("x**2*(-1)**n", None, [], [X, nv]),
                    sol("2*x", "expression"), NO, None))
        out.append((f"RK-3 derivative x**2*(-2)**n, n {dn}: 2*x*(-2)**n", der("x**2*(-2)**n", None, [], [X, nv]),
                    sol("2*x*(-2)**n", "expression"), OK, None))
        q = ext("(-1)**(2*n)*x**2", "max", "[0, 2]", [], [X, nv])
        out.append((f"RK-3 max (-1)**(2n)*x**2 on [0, 2], n {dn}: 4", q, sol("4"), OK, None))
        out.append((f"RK-3 max (-1)**(2n)*x**2 on [0, 2], n {dn}: 5 [wrong]", q, sol("5"), NO, None))
        out.append((f"RK-3 series k*(-1)**n, k=1..3, n {dn}: 6*(-1)**n", ss("k*(-1)**n", 1, 3, [], [K_, nv]),
                    sol("6*(-1)**n"), OK, None))
        q = ir("solve_equation", {"var": "x", "equation": "x**2 = (-1)**(2*n)"}, [], [X, nv])
        out.append((f"RK-3 solve x**2 = (-1)**(2n), n {dn}: {{-1, 1}}", q, sol("{-1, 1}", "set"), OK, None))
        out.append((f"RK-3 solve x**2 = (-1)**(2n), n {dn}: {{1}} [wrong]", q, sol("{1}", "set"), NO, None))
        q = ir("solve_inequality", {"var": "x", "inequality": "(-1)**(2*n)*x > 0"}, [], [X, nv])
        out.append((f"RK-3 solve (-1)**(2n)*x > 0, n {dn}: (0, oo)", q, sol("Interval.open(0, oo)", "interval"), OK, None))
    out.append(("RK-3 anti (-1)**n*x, n natural: (-1)**n*x**2/2", anti("(-1)**n*x", [], [X, NN_]),
                sol("(-1)**n*x**2/2", "expression"), OK, None))
    out.append(("RK-3 ctrl derivative x**2*(-1)**n, n real: 2*x*(-1)**n [convention]", der("x**2*(-1)**n", None, [], [X, NR_]),
                sol("2*x*(-1)**n", "expression"), UNK, None))
    # RK-4: convergence by a majorant: exp(-t**alpha), the task variable carried as a fixed parameter
    for I, v, w in (("exp(-sqrt(t))", "2", "3"), ("exp(-t**(1/3))", "6", "5"), ("t*exp(-sqrt(t))", "12", "11")):
        q = ev1(f"Integral({I}, (t, 0, oo))")
        out.append((f"RK-4 evaluate Integral({I}, (t, 0, oo)): {v}", q, sol(v), OK, None))
        out.append((f"RK-4 evaluate Integral({I}, (t, 0, oo)): {w} [wrong]", q, sol(w), NO, None))
    q = der("Integral(exp(-t)*(x + t), (t, 0, oo))", None, [], XT)
    out.append(("RK-4 derivative Integral(exp(-t)*(x + t), (t, 0, oo)): 1", q, sol("1", "expression"), OK, None))
    out.append(("RK-4 derivative Integral(exp(-t)*(x + t), (t, 0, oo)): 2 [wrong]", q, sol("2", "expression"), NO, None))
    q = der("Integral(exp(-t)*cos(x*t), (t, 0, oo))", None, [], XT)
    out.append(("RK-4 derivative Integral(exp(-t)*cos(x*t), (t, 0, oo)): 2*x/(1 + x**2)**2 [wrong sign]", q,
                sol("2*x/(1 + x**2)**2", "expression"), NO, None))
    out.append(("RK-4 derivative Integral(exp(-t)*cos(x*t), (t, 0, oo)): -2*x/(1 + x**2)**2", q,
                sol("-2*x/(1 + x**2)**2", "expression"), NOTNO, None))
    q = der("x**2 + Integral(exp(-sqrt(t)), (t, 0, oo))", None, [], XT)
    out.append(("RK-4 derivative x**2 + Integral(exp(-sqrt(t)), (t, 0, oo)): 2*x", q, sol("2*x", "expression"), OK, None))
    out.append(("RK-4 derivative x**2 + Integral(exp(-sqrt(t)), (t, 0, oo)): 3*x [wrong]", q, sol("3*x", "expression"), NO,
                None))
    out.append(("RK-4 ctrl evaluate Integral(exp(-t), (t, 0, oo)): 1", ev1("Integral(exp(-t), (t, 0, oo))"), sol("1"), OK,
                None))
    # RK-5: kinks of nested radicals and roots: a budget, never a wrong verdict
    U1, U2 = "x**3 - 3*x + 1", "x**4 - 10*x**2 + 1"
    out.append((f"RK-5 derivative |{U2}|: sign formula [right]", der(f"Abs({U2})"),
                sol(f"(4*x**3 - 20*x)*({U2})/Abs({U2})", "expression"), NOTNO, None))
    for f in (f"Abs({U1}) + Abs({U2})", f"Abs({U2})**3", f"sqrt(Abs({U2}))", f"Abs({U2})"):
        out.append((f"RK-5 derivative {f}: 0 [wrong]", der(f), sol("0", "expression"), NO, None))
    # RK-6: one verdict whatever the hash seed
    for f, c in (("Abs(log(x)) + Abs(tan(x))", "0"), ("Abs(sqrt(x) - 1) + Abs(tan(x))", "1/(2*sqrt(x))"),
                 ("Abs(log(x))*Abs(tan(x))", "0")):
        out.append((f"RK-6 derivative {f}: {c} [wrong]", der(f), sol(c, "expression"), NO, None))
    # RK-7: the body of at(diff(f), x, p) is defined near p by a strict condition (strict_at)
    q = ir("evaluate", {"expr": "x + 1"}, ["x = 1"], [X], shape="scalar")
    for c in ("at(diff(1/(x - cos(x)), x), x, pi) = -1/(pi + 1)**2", "at(diff(tan(x**2), x), x, 1) = 2 + 2*tan(1)**2",
              "at(diff(1/(x + exp(x)), x), x, 0) = -2", "at(diff(sec(x**2), x), x, 1) = 2*tan(1)*sec(1)"):
        out.append((f"RK-7 step compute {c}", q, sol("2", steps=[("compute", c)]), OK, VER))
    for c in ("at(diff(1/(x - cos(x)), x), x, pi) = -1/(pi + 2)**2", "at(diff(1/(x + exp(x)), x), x, 0) = -3"):
        out.append((f"RK-7 step compute {c} [wrong]", q, sol("2", steps=[("compute", c)]), NOTOK, None))
    return out


# --- round 4 (8 Oct 2026): the attack on round 3 (`d4/saldiri/d4e3/`) and the decisions `d4e3/kararlar_tur4.txt` -------
# The probes of the attack and of its validators are kept as they ran, in tur4/ (their own helpers, ortak.py), and read
# here: T the second-pass false-accept probes (t1..t18), Y the first-pass ones (s1..s12), U and V the unjust-rejection
# and coverage probes (sonda_r2 and sonda_rk groups), W the repros, the validators' variants and controls and the cases
# the decisions name (tur4/tekrar.py). A probe's expectation the decisions changed is overridden in ROUND4_EXPECT, with
# the decision named.
def _tur4():
    import os
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tur4")
    if d not in sys.path:
        sys.path.insert(0, d)


# label -> (accepted verdicts, the decision): the five KINK cases are right as CORRECT (f has a derivative at 0 and the
# claim gives it, or neither has a value there)
ROUND4_EXPECT = {
    "KINK derivative Piecewise((exp(x), x > 0), (1 + x, x <= 0)): Piecewise((exp(x), x > 0), (1, x <= 0)) "
    "[value at a corner]": (OK | UNK, "KINK"),
    "KINK derivative Max(x, -x)*Max(x, -x): 2*x [value at a corner]": (OK | UNK, "KINK"),
    "KINK derivative Max(x**3, -x**3): 3*x**2*sign(x) [value at a corner]": (OK | UNK, "KINK"),
    "KINK derivative x*Max(x, -x): 2*Max(x, -x) [value at a corner]": (OK | UNK, "KINK"),
    "KINK derivative Max(x, -x)**(1/2): sign(x)/(2*sqrt(Abs(x))) [value at a corner]": (OK | UNK, "KINK"),
    # robustness probes whose claim is wrong (measured: 2 against f' = 1; 0.190 against 0.342 at x = 0.7): INCORRECT is
    # right, never CORRECT
    "der Abs(x)*sign(x): 2*Abs(x)/x*0 + 2*x/x*Abs(x)/Abs(x)": (NOTOK, "wrong claim"),
    "der Abs(sin(x))**(1/3): cos(x)*sin(x)/(3*Abs(sin(x))**(7/3))*Abs(sin(x))**2": (NOTOK, "wrong claim"),
}


def _probe_cases(modules):
    _tur4()
    import importlib
    out = []
    for m in modules:
        for label, q, s, verdicts, statuses in importlib.import_module(m).cases():
            verdicts = ROUND4_EXPECT.get(label, (verdicts,))[0]
            out.append((f"{m}: {label}", q, s, verdicts, statuses))
    return out


def cases_t():
    return _probe_cases([f"t{i}" for i in range(1, 19)])


def cases_y():
    return _probe_cases([f"s{i}" for i in range(1, 13)])


def _rk_cases(names, module):
    _tur4()
    import importlib
    r2 = importlib.import_module("sonda_r2")
    mod = importlib.import_module(module)
    out = []
    for g in names:
        fn = r2.GROUPS[g] if module == "sonda_r2" else getattr(mod, f"cases_{g.lower()}")
        for grp, label, q, s, verdicts in fn():
            verdicts = ROUND4_EXPECT.get(label, (verdicts,))[0]
            out.append((f"{module} {grp}: {label}", q, r2._fill(s, q), verdicts, None))
    return out


def cases_u():
    return _rk_cases(["K", "P", "D", "W", "R", "M", "S", "Q", "F2", "X", "Z", "L", "K2", "T"], "sonda_r2")


def cases_v():
    return _rk_cases(list("ABCDEFGHIJ"), "sonda_rk")


def cases_w():
    _tur4()
    import importlib
    return importlib.import_module("tekrar").cases()


def _tur5():
    import os
    _tur4()
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tur5")
    if d not in sys.path:
        sys.path.insert(0, d)


# round 5: a probe's expectation the decisions (d4e4/kararlar_tur5.txt) changed, with the decision named
ROUND5_EXPECT: dict = {}


def cases_x():
    _tur5()
    import importlib
    out = []
    for m in [f"p{i}" for i in range(1, 11)]:
        for label, q, s, verdicts, statuses in importlib.import_module(m).cases():
            verdicts = ROUND5_EXPECT.get(label, (verdicts,))[0]
            out.append((f"{m}: {label}", q, s, verdicts, statuses))
    return out


def cases_z():
    _tur5()
    import importlib
    return importlib.import_module("tekrar5").cases()


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "K": cases_k, "L": cases_l, "M": cases_m, "N": cases_n, "P": cases_p,
          "Q": cases_q, "R": cases_r, "S": cases_s, "T": cases_t, "U": cases_u, "V": cases_v, "W": cases_w,
          "X": cases_x, "Y": cases_y, "Z": cases_z}


def main(out_path=None, groups="ABCDEFGHKLMNPQRSTUVWXYZ"):
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
    grp = args[1] if len(args) > 1 else "ABCDEFGHKLMNPQRSTUVWXYZ"
    sys.exit(1 if main(out, grp) else 0)
