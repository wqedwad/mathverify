"""Part (vi) of the N1-N9 re-run: a constraint on the solved variable that names another symbol (a
given inequality `x > b`, a declared constraint `vars[].constraints`, the domain of discourse, a
written condition `log(x - a)`) was dropped by the single-variable filters of certify.algebra,
certify.counting and Ctx.domain_for. Every task kind whose answer is read on the variable's domain
(solve_equation, solve_inequality, count_roots, count_integers, count_solutions, domain_of,
evaluate, extremum), each constraint source, a parameter the givens pin (`b = 0`) and one they leave
free, the right and a wrong answer, and the single-variable controls. EQG: a given EQUATION on the
variable, dropped by the same filters; PAR: parametric answers that must stay certified.

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca6/sonda.py [out.json]

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
UNK = {"UNKNOWN"}
BAD = {"INCORRECT", "UNKNOWN"}        # anything but a false accept
NOTBAD = {"CORRECT", "UNKNOWN"}       # anything but a false reject

X = {"name": "x", "domain": "real"}
B = {"name": "b", "domain": "real"}
XB = [X, B]
XBC = [dict(X, constraints=["x > b"]), B]


def _ir(kind, params, vars_, givens=(), shape="set", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def _sol(payload, kind="set"):
    return {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []}


# the constraint x > b written three ways, next to the givens `pin` (["b = 0"] or [])
def _sources(pin):
    return [("given", XB, ["x > b"] + pin, None),
            ("vars", XBC, list(pin), None),
            ("dod", XB, list(pin), "x > b")]


def cases_solve_equation():
    out = []
    eq = {"equation": "x**2 = 4", "var": "x"}
    for src, vars_, givens, dod in _sources(["b = 0"]):
        ir = _ir("solve_equation", eq, vars_, givens, dod=dod)
        out += [(f"eq x^2=4 {src} x>b b=0 {{2}}", ir, _sol("{2}"), OK),
                (f"eq x^2=4 {src} x>b b=0 {{-2,2}}", ir, _sol("{-2, 2}"), NO),
                (f"eq x^2=4 {src} x>b b=0 {{-2}}", ir, _sol("{-2}"), NO)]
    for src, vars_, givens, dod in _sources([]):
        ir = _ir("solve_equation", eq, vars_, givens, dod=dod)
        # {2} is refuted by z3 (a model b = -3 has the root -2): the answer depends on b, and a
        # refutation is no false accept (left as it is)
        out += [(f"eq x^2=4 {src} x>b free {{-2,2}}", ir, _sol("{-2, 2}"), UNK),
                (f"eq x^2=4 {src} x>b free {{2}}", ir, _sol("{2}"), BAD),
                (f"eq x^2=4 {src} x>b free {{5}}", ir, _sol("{5}"), BAD)]
    xa = [X, {"name": "a", "domain": "real"}]
    out += [
        # part (ii): x > a with the given a = 0
        ("eq x^2=4 given x>a a=0 {-2,2}", _ir("solve_equation", eq, xa, ["x > a", "a = 0"]), _sol("{-2, 2}"), NO),
        ("eq x^2=4 given x>a a=0 {2}", _ir("solve_equation", eq, xa, ["x > a", "a = 0"]), _sol("{2}"), OK),
        # b not declared as a variable: the IR is malformed, the verifier abstains
        ("eq x^2=4 given x>b b=0 (b undeclared) {-2,2}", _ir("solve_equation", eq, [X], ["x > b", "b = 0"]),
         _sol("{-2, 2}"), UNK),
        ("eq x^2=4 given x>b b=0 (b undeclared) {2}", _ir("solve_equation", eq, [X], ["x > b", "b = 0"]),
         _sol("{2}"), UNK),
        # the binding written the other way round, and two parameters both pinned
        ("eq x^2=4 given x>b 0=b {2}", _ir("solve_equation", eq, XB, ["x > b", "0 = b"]), _sol("{2}"), OK),
        ("eq x^2=4 given x>b-c b=1 c=1 {-2,2}",
         _ir("solve_equation", eq, XB + [{"name": "c", "domain": "real"}], ["x > b - c", "b = 1", "c = 1"]),
         _sol("{-2, 2}"), NO),
        ("eq x^2=4 given x>b-c b=1 only {-2,2}",
         _ir("solve_equation", eq, XB + [{"name": "c", "domain": "real"}], ["x > b - c", "b = 1"]),
         _sol("{-2, 2}"), UNK),
        # two givens bind b to different values: b is not pinned
        ("eq x^2=4 given x>b b=0 b=-5 {-2,2}", _ir("solve_equation", eq, XB, ["x > b", "b = 0", "b = -5"]),
         _sol("{-2, 2}"), BAD),
        # a binding that is not a plain value (b**2 = 0) pins nothing for the algebra layer
        ("eq x^2=4 given x>b b^2=0 {-2,2}", _ir("solve_equation", eq, XB, ["x > b", "b**2 = 0"]),
         _sol("{-2, 2}"), BAD),
        # a chained given 0 <= b < x with b pinned / free
        ("eq x^2=4 given b<x<3 b=0 {-2,2}", _ir("solve_equation", eq, XB, ["b < x < 3", "b = 0"]),
         _sol("{-2, 2}"), NO),
        ("eq x^2=4 given b<x<3 b=0 {2}", _ir("solve_equation", eq, XB, ["b < x < 3", "b = 0"]), _sol("{2}"), OK),
        ("eq x^2=4 given b<x<3 free {-2,2}", _ir("solve_equation", eq, XB, ["b < x < 3"]), _sol("{-2, 2}"), UNK),
        # the equation among the givens (the evalset writes it this way)
        ("eq in givens, x>b b=0 {2}", _ir("solve_equation", {"var": "x"}, XB, ["x**2 = 4", "x > b", "b = 0"]),
         _sol("{2}"), OK),
        ("eq in givens, x>b b=0 {-2,2}", _ir("solve_equation", {"var": "x"}, XB, ["x**2 = 4", "x > b", "b = 0"]),
         _sol("{-2, 2}"), NO),
        ("eq in givens, x>b free {-2,2}", _ir("solve_equation", {"var": "x"}, XB, ["x**2 = 4", "x > b"]),
         _sol("{-2, 2}"), UNK),
        # part (ii): a written condition with a parameter, pinned and free
        ("eq x^2+1+0*log(x-a)=5 a=0 {-2,2}",
         _ir("solve_equation", {"equation": "x**2 + 1 + 0*log(x - a) = 5", "var": "x"}, xa, ["a = 0"]),
         _sol("{-2, 2}"), NO),
        ("eq x^2+1+0*log(x-a)=5 a=0 {2}",
         _ir("solve_equation", {"equation": "x**2 + 1 + 0*log(x - a) = 5", "var": "x"}, xa, ["a = 0"]),
         _sol("{2}"), OK),
        ("eq x^2+1+0*log(x-a)=5 free {-2,2}",
         _ir("solve_equation", {"equation": "x**2 + 1 + 0*log(x - a) = 5", "var": "x"}, xa, []),
         _sol("{-2, 2}"), UNK),
        ("eq x^2+1+0*log(x-a)=5 free {2}",
         _ir("solve_equation", {"equation": "x**2 + 1 + 0*log(x - a) = 5", "var": "x"}, xa, []),
         _sol("{2}"), BAD),
        # a condition on the parameter alone restricts nothing on x
        ("eq x^2=4 given b>0 (param only) {-2,2}", _ir("solve_equation", eq, XB, ["b > 0"]), _sol("{-2, 2}"), NOTBAD),
        # single-variable controls
        ("ctrl eq x^2=4 given x>0 {2}", _ir("solve_equation", eq, [X], ["x > 0"]), _sol("{2}"), OK),
        ("ctrl eq x^2=4 given x>0 {-2,2}", _ir("solve_equation", eq, [X], ["x > 0"]), _sol("{-2, 2}"), NO),
        ("ctrl eq x^2=4 vars x>0 {2}", _ir("solve_equation", eq, [dict(X, constraints=["x > 0"])]), _sol("{2}"), OK),
        ("ctrl eq x^2=4 vars x>0 {-2,2}", _ir("solve_equation", eq, [dict(X, constraints=["x > 0"])]),
         _sol("{-2, 2}"), NO),
        ("ctrl eq x^2=4 dod x>0 {2}", _ir("solve_equation", eq, [X], dod="x > 0"), _sol("{2}"), OK),
        ("ctrl eq x^2=4 {-2,2}", _ir("solve_equation", eq, [X]), _sol("{-2, 2}"), OK),
    ]
    return out


def cases_solve_inequality():
    xa = [X, {"name": "a", "domain": "real"}]
    out = []
    ineq = {"inequality": "x**2 < 4", "var": "x"}
    for src, vars_, givens, dod in _sources(["b = 0"]):
        ir = _ir("solve_inequality", ineq, vars_, givens, shape="interval", dod=dod)
        out += [(f"ineq x^2<4 {src} x>b b=0 (0,2)", ir, _sol("(0, 2)", "interval"), OK),
                (f"ineq x^2<4 {src} x>b b=0 (-2,2)", ir, _sol("(-2, 2)", "interval"), NO)]
    for src, vars_, givens, dod in _sources([]):
        ir = _ir("solve_inequality", ineq, vars_, givens, shape="interval", dod=dod)
        out += [(f"ineq x^2<4 {src} x>b free (-2,2)", ir, _sol("(-2, 2)", "interval"), UNK),
                (f"ineq x^2<4 {src} x>b free (0,2)", ir, _sol("(0, 2)", "interval"), UNK)]
    out += [
        # b not declared: the side condition was dropped as "not a relation" and (-2, 2) certified
        ("ineq x^2<4 given x>b b=0 (b undeclared) (-2,2)",
         _ir("solve_inequality", ineq, [X], ["x > b", "b = 0"], shape="interval"), _sol("(-2, 2)", "interval"), UNK),
        ("ineq x^2<4 given x>b b=0 (b undeclared) (0,2)",
         _ir("solve_inequality", ineq, [X], ["x > b", "b = 0"], shape="interval"), _sol("(0, 2)", "interval"), UNK),
        ("ineq x^2<4 given x>b b=1/2 (1/2,2)",
         _ir("solve_inequality", ineq, XB, ["x > b", "b = 1/2"], shape="interval"), _sol("(1/2, 2)", "interval"), OK),
        ("ineq x^2<4 given x>b b=1/2 (0,2)",
         _ir("solve_inequality", ineq, XB, ["x > b", "b = 1/2"], shape="interval"), _sol("(0, 2)", "interval"), NO),
        # the inequality among the givens
        ("ineq in givens, x>b b=0 (-2,2)",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "x > b", "b = 0"], shape="interval"),
         _sol("(-2, 2)", "interval"), BAD),
        ("ineq in givens, x>b free (-2,2)",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "x > b"], shape="interval"),
         _sol("(-2, 2)", "interval"), UNK),
        # a written condition with a parameter
        ("ineq x^2+0*log(x-a)<4 a=0 (-2,2)",
         _ir("solve_inequality", {"inequality": "x**2 + 0*log(x - a) < 4", "var": "x"}, xa, ["a = 0"],
             shape="interval"), _sol("(-2, 2)", "interval"), NO),
        ("ineq x^2+0*log(x-a)<4 a=0 (0,2)",
         _ir("solve_inequality", {"inequality": "x**2 + 0*log(x - a) < 4", "var": "x"}, xa, ["a = 0"],
             shape="interval"), _sol("(0, 2)", "interval"), OK),
        ("ineq x^2+0*log(x-a)<4 free (-2,2)",
         _ir("solve_inequality", {"inequality": "x**2 + 0*log(x - a) < 4", "var": "x"}, xa, [],
             shape="interval"), _sol("(-2, 2)", "interval"), UNK),
        # controls
        ("ineq in givens, x>b b=0 (0,2)",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "x > b", "b = 0"], shape="interval"),
         _sol("(0, 2)", "interval"), OK),
        ("ineq in givens, x>b b=0 {}",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "x > b", "b = 0"], shape="interval"),
         _sol("{}", "set"), NO),
        ("ineq in givens, x^2<4 b=0 (b elsewhere) {}",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "b = 0"], shape="interval"), _sol("{}", "set"), NO),
        ("ineq in givens, x^2<4 b=0 (b elsewhere) (-2,2)",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "b = 0"], shape="interval"),
         _sol("(-2, 2)", "interval"), OK),
        ("ineq in givens, x>b free (b,2)",
         _ir("solve_inequality", {"var": "x"}, XB, ["x**2 < 4", "x > b"], shape="interval"),
         _sol("(b, 2)", "interval"), UNK),
        ("ineq x^2<4 given x>b free (b,2)", _ir("solve_inequality", ineq, XB, ["x > b"], shape="interval"),
         _sol("(b, 2)", "interval"), UNK),
        # the main inequality's own parameter, pinned and free
        ("ineq x^2<a a=4 (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < a", "var": "x"}, xa, ["a = 4"],
                                      shape="interval"), _sol("(-2, 2)", "interval"), NOTBAD),
        ("ineq x^2<a a=4 (-4,4)", _ir("solve_inequality", {"inequality": "x**2 < a", "var": "x"}, xa, ["a = 4"],
                                      shape="interval"), _sol("(-4, 4)", "interval"), BAD),
        ("ineq x^2<a free (-2,2)", _ir("solve_inequality", {"inequality": "x**2 < a", "var": "x"}, xa, [],
                                       shape="interval"), _sol("(-2, 2)", "interval"), UNK),
        ("ctrl ineq x^2<4 given x>0 (0,2)", _ir("solve_inequality", ineq, [X], ["x > 0"], shape="interval"),
         _sol("(0, 2)", "interval"), OK),
        ("ctrl ineq x^2<4 given x>0 (-2,2)", _ir("solve_inequality", ineq, [X], ["x > 0"], shape="interval"),
         _sol("(-2, 2)", "interval"), NO),
        ("ctrl ineq x^2<4 vars x>0 (0,2)",
         _ir("solve_inequality", ineq, [dict(X, constraints=["x > 0"])], shape="interval"),
         _sol("(0, 2)", "interval"), OK),
        ("ctrl ineq x^2<4 (-2,2)", _ir("solve_inequality", ineq, [X], shape="interval"),
         _sol("(-2, 2)", "interval"), OK),
    ]
    return out


def cases_count_roots():
    out = []
    cr = {"expr": "x**2 - 4", "var": "x"}
    for src, vars_, givens, dod in _sources(["b = 0"]):
        ir = _ir("count_roots", cr, vars_, givens, shape="count", dod=dod)
        out += [(f"roots x^2-4 {src} x>b b=0 1", ir, _sol(1, "count"), OK),
                (f"roots x^2-4 {src} x>b b=0 2", ir, _sol(2, "count"), NO)]
    for src, vars_, givens, dod in _sources([]):
        ir = _ir("count_roots", cr, vars_, givens, shape="count", dod=dod)
        out += [(f"roots x^2-4 {src} x>b free 2", ir, _sol(2, "count"), UNK),
                (f"roots x^2-4 {src} x>b free 1", ir, _sol(1, "count"), UNK)]
    xa = [X, {"name": "a", "domain": "real"}]
    out += [
        ("roots x^2-4+0*log(x-a) a=0 2",
         _ir("count_roots", {"expr": "x**2 - 4 + 0*log(x - a)", "var": "x"}, xa, ["a = 0"], shape="count"),
         _sol(2, "count"), NO),
        ("roots x^2-4+0*log(x-a) a=0 1",
         _ir("count_roots", {"expr": "x**2 - 4 + 0*log(x - a)", "var": "x"}, xa, ["a = 0"], shape="count"),
         _sol(1, "count"), OK),
        ("roots x^2-4+0*log(x-a) free 2",
         _ir("count_roots", {"expr": "x**2 - 4 + 0*log(x - a)", "var": "x"}, xa, [], shape="count"),
         _sol(2, "count"), UNK),
        # single-variable controls (a constraint, a given, the domain of discourse)
        ("ctrl roots x^2-4 vars x>0 1", _ir("count_roots", cr, [dict(X, constraints=["x > 0"])], shape="count"),
         _sol(1, "count"), OK),
        ("ctrl roots x^2-4 vars x>0 2", _ir("count_roots", cr, [dict(X, constraints=["x > 0"])], shape="count"),
         _sol(2, "count"), NO),
        ("ctrl roots x^2-4 given x>0 2", _ir("count_roots", cr, [X], ["x > 0"], shape="count"), _sol(2, "count"), BAD),
        ("ctrl roots x^2-4 dod x>0 2", _ir("count_roots", cr, [X], dod="x > 0", shape="count"), _sol(2, "count"), NO),
        ("ctrl roots x^2-4 dod x>0 1", _ir("count_roots", cr, [X], dod="x > 0", shape="count"), _sol(1, "count"), OK),
        ("ctrl roots x^2-4 2", _ir("count_roots", cr, [X], shape="count"), _sol(2, "count"), OK),
        ("ctrl roots x^2-4+0*log(x) 1",
         _ir("count_roots", {"expr": "x**2 - 4 + 0*log(x)", "var": "x"}, [X], shape="count"), _sol(1, "count"), OK),
        ("ctrl roots x^2-4 lo=0 1", _ir("count_roots", {"expr": "x**2 - 4", "var": "x", "lo": "0"}, [X], shape="count"),
         _sol(1, "count"), OK),
    ]
    return out


def cases_count_integers():
    XI = {"name": "x", "domain": "integer"}
    out = []
    for label, vars_, givens, dod, claim, exp in [
        ("given x>b b=0 3", [XI, B], ["x**2 < 10", "x > b", "b = 0"], None, 3, OK),
        ("given x>b b=0 7", [XI, B], ["x**2 < 10", "x > b", "b = 0"], None, 7, NO),
        ("vars x>b b=0 3", [dict(XI, constraints=["x > b"]), B], ["x**2 < 10", "b = 0"], None, 3, OK),
        ("vars x>b b=0 7", [dict(XI, constraints=["x > b"]), B], ["x**2 < 10", "b = 0"], None, 7, NO),
        ("dod x>b b=0 7", [XI, B], ["x**2 < 10", "b = 0"], "x > b", 7, NO),
        ("given x>b b=0 0", [XI, B], ["x**2 < 10", "x > b", "b = 0"], None, 0, NO),
        ("vars x>b b=0 0", [dict(XI, constraints=["x > b"]), B], ["x**2 < 10", "b = 0"], None, 0, NO),
        ("unrelated b=0 7", [XI, B], ["x**2 < 10", "b = 0"], None, 7, OK),
        ("unrelated b=0 0", [XI, B], ["x**2 < 10", "b = 0"], None, 0, NO),
        ("given x>b free 7", [XI, B], ["x**2 < 10", "x > b"], None, 7, UNK),
        ("given x>b free 3", [XI, B], ["x**2 < 10", "x > b"], None, 3, UNK),
        ("vars x>b free 7", [dict(XI, constraints=["x > b"]), B], ["x**2 < 10"], None, 7, UNK),
        ("dod x>b free 7", [XI, B], ["x**2 < 10"], "x > b", 7, UNK),
        ("ctrl given x>0 3", [XI], ["x**2 < 10", "x > 0"], None, 3, OK),
        ("ctrl vars x>0 3", [dict(XI, constraints=["x > 0"])], ["x**2 < 10"], None, 3, OK),
        ("ctrl vars x>0 7", [dict(XI, constraints=["x > 0"])], ["x**2 < 10"], None, 7, NO),
        ("ctrl 7", [XI], ["x**2 < 10"], None, 7, OK),
    ]:
        out.append((f"ints x^2<10 {label}", _ir("count_integers", {"var": "x"}, vars_, givens, shape="count", dod=dod),
                    _sol(claim, "count"), exp))
    return out


def cases_count_solutions():
    XN = {"name": "x", "domain": "nonneg_integer"}
    YN = {"name": "y", "domain": "nonneg_integer"}
    BN = {"name": "b", "domain": "nonneg_integer"}
    bnd = {"bounds": {"x": ["0", "4"], "y": ["0", "4"]}}
    bnd_b = {"bounds": {"x": ["0", "4"], "y": ["0", "4"], "b": ["0", "4"]}}
    out = []
    for label, vars_, givens, dod, claim, exp in [
        # b undeclared: the IR is malformed, the verifier abstains
        ("given x>b b=2 (b undeclared) 2", [XN, YN], ["x + y = 4", "x > b", "b = 2"], None, 2, UNK),
        ("vars x>b b=2 (b undeclared) 5", [dict(XN, constraints=["x > b"]), YN], ["x + y = 4", "b = 2"], None, 5, UNK),
        ("dod x>b b=2 (b undeclared) 5", [XN, YN], ["x + y = 4", "b = 2"], "x > b", 5, UNK),
        ("given x>b free (b undeclared) 5", [XN, YN], ["x + y = 4", "x > b"], None, 5, UNK),
        ("vars x>b free (b undeclared) 5", [dict(XN, constraints=["x > b"]), YN], ["x + y = 4"], None, 5, UNK),
        ("dod x>b free (b undeclared) 5", [XN, YN], ["x + y = 4"], "x > b", 5, UNK),
    ]:
        out.append((f"sols x+y=4 {label}", _ir("count_solutions", bnd, vars_, givens, shape="count", dod=dod),
                    _sol(claim, "count"), exp))
    # b declared and counted (0..4): the given b = 2 leaves the triples (3, 1, 2) and (4, 0, 2)
    for label, vars_, givens, dod, claim, exp in [
        ("given x>b b=2 (b counted) 2", [XN, YN, BN], ["x + y = 4", "x > b", "b = 2"], None, 2, OK),
        ("given x>b b=2 (b counted) 5", [XN, YN, BN], ["x + y = 4", "x > b", "b = 2"], None, 5, NO),
        ("vars x>b b=2 (b counted) 2", [dict(XN, constraints=["x > b"]), YN, BN], ["x + y = 4", "b = 2"], None, 2, OK),
        # the domain of discourse also names b, where it reads b < x with x free: undecided
        ("dod x>b b=2 (b counted) 2", [XN, YN, BN], ["x + y = 4", "b = 2"], "x > b", 2, NOTBAD),
        ("dod x>b b=2 (b counted) 5", [XN, YN, BN], ["x + y = 4", "b = 2"], "x > b", 5, BAD),
        # b free and counted: x > b is a condition between counted variables (1 + 2 + 3 + 4 = 10)
        ("given x>b (b counted) 10", [XN, YN, BN], ["x + y = 4", "x > b"], None, 10, OK),
        ("given x>b (b counted) 25", [XN, YN, BN], ["x + y = 4", "x > b"], None, 25, NO),
        ("dod x>b (b counted) 25", [XN, YN, BN], ["x + y = 4"], "x > b", 25, BAD),
    ]:
        out.append((f"sols x+y=4 {label}", _ir("count_solutions", bnd_b, vars_, givens, shape="count", dod=dod),
                    _sol(claim, "count"), exp))
    for label, vars_, givens, dod, claim, exp in [
        # a constraint between two counted variables is part of the count, not a parameter
        ("ctrl given x>y 2", [XN, YN], ["x + y = 4", "x > y"], None, 2, OK),
        ("ctrl vars x>y 2", [dict(XN, constraints=["x > y"]), YN], ["x + y = 4"], None, 2, OK),
        ("ctrl vars x>y 5", [dict(XN, constraints=["x > y"]), YN], ["x + y = 4"], None, 5, NO),
        ("ctrl given x>2 2", [XN, YN], ["x + y = 4", "x > 2"], None, 2, OK),
        ("ctrl dod x>2 2", [XN, YN], ["x + y = 4"], "x > 2", 2, OK),
        ("ctrl dod x>2 5", [XN, YN], ["x + y = 4"], "x > 2", 5, NO),
        ("ctrl 5", [XN, YN], ["x + y = 4"], None, 5, OK),
    ]:
        out.append((f"sols x+y=4 {label}", _ir("count_solutions", bnd, vars_, givens, shape="count", dod=dod),
                    _sol(claim, "count"), exp))
    return out


def cases_domain_of():
    out = []
    do = {"expr": "sqrt(4 - x**2)", "var": "x"}
    for src, vars_, givens, dod in _sources(["b = 0"]):
        ir = _ir("domain_of", do, vars_, givens, shape="interval", dod=dod)
        out += [(f"dom sqrt(4-x^2) {src} x>b b=0 (0,2]", ir, _sol("(0, 2]", "interval"), OK),
                (f"dom sqrt(4-x^2) {src} x>b b=0 [-2,2]", ir, _sol("[-2, 2]", "interval"), NO)]
    for src, vars_, givens, dod in _sources([]):
        ir = _ir("domain_of", do, vars_, givens, shape="interval", dod=dod)
        out += [(f"dom sqrt(4-x^2) {src} x>b free [-2,2]", ir, _sol("[-2, 2]", "interval"), UNK),
                (f"dom sqrt(4-x^2) {src} x>b free (0,2]", ir, _sol("(0, 2]", "interval"), UNK)]
    xa = [X, {"name": "a", "domain": "real"}]
    out += [
        # the expression's own parameter: pinned by a given, or free (its domain depends on a)
        ("dom sqrt(x-a) a=0 [0,oo)", _ir("domain_of", {"expr": "sqrt(x - a)", "var": "x"}, xa, ["a = 0"], shape="interval"),
         _sol("[0, oo)", "interval"), NOTBAD),
        ("dom sqrt(x-a) a=0 [1,oo)", _ir("domain_of", {"expr": "sqrt(x - a)", "var": "x"}, xa, ["a = 0"], shape="interval"),
         _sol("[1, oo)", "interval"), BAD),
        ("dom sqrt(x-a) free [0,oo)", _ir("domain_of", {"expr": "sqrt(x - a)", "var": "x"}, xa, [], shape="interval"),
         _sol("[0, oo)", "interval"), UNK),
        ("ctrl dom sqrt(4-x^2) vars x>0 (0,2]",
         _ir("domain_of", do, [dict(X, constraints=["x > 0"])], shape="interval"), _sol("(0, 2]", "interval"), OK),
        ("ctrl dom sqrt(4-x^2) vars x>0 [-2,2]",
         _ir("domain_of", do, [dict(X, constraints=["x > 0"])], shape="interval"), _sol("[-2, 2]", "interval"), NO),
        ("ctrl dom sqrt(4-x^2) given x>0 (0,2]", _ir("domain_of", do, [X], ["x > 0"], shape="interval"),
         _sol("(0, 2]", "interval"), OK),
        ("ctrl dom sqrt(4-x^2) given x>0 [-2,2]", _ir("domain_of", do, [X], ["x > 0"], shape="interval"),
         _sol("[-2, 2]", "interval"), NO),
        ("ctrl dom sqrt(4-x^2) [-2,2]", _ir("domain_of", do, [X], shape="interval"), _sol("[-2, 2]", "interval"), OK),
    ]
    return out


def cases_evaluate():
    out = []
    ev = {"expr": "x"}
    for src, vars_, givens, dod in _sources(["b = 0"]):
        ir = _ir("evaluate", ev, vars_, ["x**2 = 4"] + givens, shape="scalar", dod=dod)
        out += [(f"eval x, x^2=4 {src} x>b b=0 2", ir, _sol("2", "value"), OK),
                (f"eval x, x^2=4 {src} x>b b=0 -2", ir, _sol("-2", "value"), NO)]
    for src, vars_, givens, dod in _sources([]):
        ir = _ir("evaluate", ev, vars_, ["x**2 = 4"] + givens, shape="scalar", dod=dod)
        out += [(f"eval x, x^2=4 {src} x>b free 2", ir, _sol("2", "value"), UNK),
                (f"eval x, x^2=4 {src} x>b free -2", ir, _sol("-2", "value"), UNK)]
    out += [
        ("eval x, x^2=4 given x>b b=0 (b undeclared) -2",
         _ir("evaluate", ev, [X], ["x**2 = 4", "x > b", "b = 0"], shape="scalar"), _sol("-2", "value"), UNK),
        ("eval x, x^2=4 given x>b b=0 (b undeclared) 2",
         _ir("evaluate", ev, [X], ["x**2 = 4", "x > b", "b = 0"], shape="scalar"), _sol("2", "value"), UNK),
        # a system whose unknowns are tied by a constraint between them (not a parameter)
        ("ctrl eval x*y, x+y=5 x-y=1 vars x>y 6",
         _ir("evaluate", {"expr": "x*y"}, [dict(X, constraints=["x > y"]), {"name": "y", "domain": "real"}],
             ["x + y = 5", "x - y = 1"], shape="scalar"), _sol("6", "value"), OK),
        ("ctrl eval x, x^2=4 given x>0 2", _ir("evaluate", ev, [X], ["x**2 = 4", "x > 0"], shape="scalar"),
         _sol("2", "value"), OK),
        ("ctrl eval x, x^2=4 given x>0 -2", _ir("evaluate", ev, [X], ["x**2 = 4", "x > 0"], shape="scalar"),
         _sol("-2", "value"), NO),
    ]
    return out


def cases_simplify():
    # the identity check reads the domain of each symbol; a dropped joint constraint makes it stricter
    # (a false reject at worst), never a false accept
    XY = [dict(X, constraints=["x > b"]), B]
    return [
        ("simp Abs(x) vars x>b b=0 -> x", _ir("simplify_expression", {"expr": "Abs(x)"}, XY, ["b = 0"], shape="expression"),
         _sol("x", "expression"), NOTBAD),
        ("simp Abs(x) vars x>b free -> x", _ir("simplify_expression", {"expr": "Abs(x)"}, XY, [], shape="expression"),
         _sol("x", "expression"), BAD),
        ("simp Abs(x) vars x>b b=0 -> -x", _ir("simplify_expression", {"expr": "Abs(x)"}, XY, ["b = 0"], shape="expression"),
         _sol("-x", "expression"), BAD),
    ]


def cases_given_equation():
    # a given EQUATION on the variable next to the task's own relation was dropped by the same filters
    # (the algebra layer and count_roots skipped every Eq given): a second relation on x, not a binding
    Y = {"name": "y", "domain": "real"}
    eq = {"equation": "x**2 = 4", "var": "x"}
    return [
        ("eqg x^2=4 given x^3=8 {-2,2}", _ir("solve_equation", eq, [X], ["x**3 = 8"]), _sol("{-2, 2}"), NO),
        ("eqg x^2=4 given x^3=8 {2}", _ir("solve_equation", eq, [X], ["x**3 = 8"]), _sol("{2}"), OK),
        ("eqg x^2=4 given x+y=3 y=1 {-2,2}", _ir("solve_equation", eq, [X, Y], ["x + y = 3", "y = 1"]),
         _sol("{-2, 2}"), NO),
        ("eqg x^2=4 given x+y=3 y=1 {2}", _ir("solve_equation", eq, [X, Y], ["x + y = 3", "y = 1"]), _sol("{2}"), OK),
        ("eqg x^2=4 given x+y=3 free {-2,2}", _ir("solve_equation", eq, [X, Y], ["x + y = 3"]), _sol("{-2, 2}"), UNK),
        ("eqg in givens x^2=4, x^3=8 {-2,2}", _ir("solve_equation", {"var": "x"}, [X], ["x**2 = 4", "x**3 = 8"]),
         _sol("{-2, 2}"), NO),
        ("eqg in givens x^2=4, x^3=8 {2}", _ir("solve_equation", {"var": "x"}, [X], ["x**2 = 4", "x**3 = 8"]),
         _sol("{2}"), OK),
        ("eqg ineq x^2<4 given x^3=1 (-2,2)",
         _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, [X], ["x**3 = 1"], shape="interval"),
         _sol("(-2, 2)", "interval"), NO),
        ("eqg ineq x^2<4 given x^3=1 {1}",
         _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, [X], ["x**3 = 1"], shape="interval"),
         _sol("{1}", "set"), OK),
        ("eqg roots x^2-4 given x^3=8 2", _ir("count_roots", {"expr": "x**2 - 4", "var": "x"}, [X], ["x**3 = 8"],
                                              shape="count"), _sol(2, "count"), NO),
        ("eqg roots x^2-4 given x^3=8 1", _ir("count_roots", {"expr": "x**2 - 4", "var": "x"}, [X], ["x**3 = 8"],
                                              shape="count"), _sol(1, "count"), OK),
        # the task's own equation repeated among the givens (the evalset writes f(x) = 5 both ways)
        ("eqg repeated main eq {-2,2}", _ir("solve_equation", eq, [X], ["x**2 = 4"]), _sol("{-2, 2}"), OK),
        # a given equation that cannot be solved exactly is not applied: abstain
        ("eqg x^2=4 given sin(x)=x/2 {-2,2}", _ir("solve_equation", eq, [X], ["sin(x) = x/2"]),
         _sol("{-2, 2}"), BAD),
    ]


def cases_parametric():
    # a parametric answer: the certificate checks the equation's (the expression's) own condition with
    # the parameter symbolic, so it is not a dropped condition. A parametric SIDE condition is (x > a
    # next to x - a = 4): the algebra layer abstains there, a known loss of coverage
    xa = [X, {"name": "a", "domain": "real"}]
    return [
        ("par sqrt(x-a)=2 free {a+4}", _ir("solve_equation", {"equation": "sqrt(x - a) = 2", "var": "x"}, xa),
         _sol("{a + 4}"), OK),
        ("par sqrt(x-a)=2 free {a+5}", _ir("solve_equation", {"equation": "sqrt(x - a) = 2", "var": "x"}, xa),
         _sol("{a + 5}"), NO),
        ("par dom sqrt(x-a) free [a,oo)", _ir("domain_of", {"expr": "sqrt(x - a)", "var": "x"}, xa, shape="interval"),
         _sol("[a, oo)", "interval"), OK),
        ("par dom sqrt(x-a) free (a,oo)", _ir("domain_of", {"expr": "sqrt(x - a)", "var": "x"}, xa, shape="interval"),
         _sol("(a, oo)", "interval"), NO),
        ("par x-a=4 given x>a free {a+4}", _ir("solve_equation", {"equation": "x - a = 4", "var": "x"}, xa, ["x > a"]),
         _sol("{a + 4}"), NOTBAD),
    ]


def cases_extremum():
    ext = {"f": "(x - 1)**2", "var": "x", "which": "min"}
    XGE = [dict(X, constraints=["x >= b"]), B]
    return [
        ("ext min (x-1)^2 vars x>=b b=2 -> 1", _ir("extremum", ext, XGE, ["b = 2"], shape="scalar"),
         _sol("1", "value"), OK),
        ("ext min (x-1)^2 vars x>=b b=2 -> 0", _ir("extremum", ext, XGE, ["b = 2"], shape="scalar"),
         _sol("0", "value"), NO),
        ("ext min (x-1)^2 vars x>=b free -> 0", _ir("extremum", ext, XGE, [], shape="scalar"), _sol("0", "value"), UNK),
        ("ext min (x-1)^2 dod x>=b b=2 -> 0", _ir("extremum", ext, XB, ["b = 2"], shape="scalar", dod="x >= b"),
         _sol("0", "value"), NO),
        ("ext min (x-1)^2 dod x>=b free -> 0", _ir("extremum", ext, XB, [], shape="scalar", dod="x >= b"),
         _sol("0", "value"), UNK),
        ("ctrl ext min (x-1)^2 vars x>=2 -> 1",
         _ir("extremum", ext, [dict(X, constraints=["x >= 2"])], shape="scalar"), _sol("1", "value"), OK),
        ("ctrl ext min (x-1)^2 vars x>=2 -> 0",
         _ir("extremum", ext, [dict(X, constraints=["x >= 2"])], shape="scalar"), _sol("0", "value"), NO),
        ("ctrl ext min (x-1)^2 -> 0", _ir("extremum", ext, [X], shape="scalar"), _sol("0", "value"), OK),
    ]


GROUPS = {"EQ": cases_solve_equation, "INEQ": cases_solve_inequality, "ROOTS": cases_count_roots,
          "INTS": cases_count_integers, "SOLS": cases_count_solutions, "DOM": cases_domain_of,
          "EVAL": cases_evaluate, "SIMP": cases_simplify, "EXT": cases_extremum, "EQG": cases_given_equation,
          "PAR": cases_parametric}


def _summ(r):
    lay = []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ev.get("why") or ev.get("error") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:140] + ')' if reason else ''}")
    return lay


def main():
    from mathverify.verifier import verify
    out_path = None
    sel = list(GROUPS)
    for a in sys.argv[1:]:
        if a.endswith(".json"):
            out_path = a
        else:
            sel = a.split(",")
    rows, bad = [], 0
    for g in sel:
        for label, ir, sol, exp in GROUPS[g]():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay = _summ(r)
                flags = list(r.flags)
            except Exception as e:  # noqa: BLE001
                v, lay, flags = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "layers": lay, "flags": flags})
            print(f"{g:5s} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            for x in lay:
                print(f"      {x}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
