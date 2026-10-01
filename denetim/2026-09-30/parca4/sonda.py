"""Part iv of the 30 Sep 2026 fixes (DECISIONS §80 "F9", §72 V15 F9, N1 and N8 of §75): SymPy's value of
an integral or a limit with a parameter is never taken as true by itself.

The parse computed `integrate(f, (x, a, b))` with a free parameter, an antiderivative `integrate(f, x)`
and `limit(f, n, p)` with a parameter through SymPy, whose parametric result is wrong in some regions
of the parameter: lim n·a·sin(π/n) is 0 with n an integer (a·π), ∫ 1/t from 1 to x is log(x) (so
L(-1) = iπ), and |cos(ax)| over [-1, 1] stays an integral that SymPy then closes to 0 at a = 1.

    A  the findings: N8, N1 (and the step "L(-1) = I*pi"), V15 F9
    B  parameters a given pins to a number: the closed form at that number, checked by numbers
    C  free parameters: the form stays unevaluated, a decision needing its value is UNKNOWN
    D  `compute` steps with such forms
    E  closed forms (no parameter): must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca4/sonda.py [out.json] [groups]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false accept
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false reject
UNK = {"UNKNOWN"}
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
NOT_VERIFIED = {"refuted", "unknown", "skipped"}

A = {"name": "a", "domain": "real"}
X = {"name": "x", "domain": "real"}
T = {"name": "t", "domain": "real"}
NP = {"name": "n", "domain": "positive_integer"}


def _ir(kind, params, vars_=(), givens=(), shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _ev(expr, vars_, givens=(), functions=None):
    return _ir("evaluate", {"expr": expr}, vars_, givens, functions=functions)


def _simp(expr, vars_, givens=()):
    return _ir("simplify_expression", {"expr": expr}, vars_, givens)


def _sol(payload, steps=(), kind="value"):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None)
def cases_a():
    L = [{"name": "L", "expr": "integrate(1/t, (t, 1, x))", "args": ["x"]}]
    seq = _ir("solve_equation", {"equation": "limit(a*n*sin(pi/n), n, oo) = 2*pi", "var": "a"}, [NP, A],
              shape="set")
    F9 = "integrate(Abs(cos(a*x)), (x, -1, 1))"
    return [
        ("N8 eq sin EmptySet", seq, _sol("{}", kind="set"), NOTOK, None),
        ("N8 eq sin {2}", seq, _sol("{2}", kind="set"), NOTNO, None),
        ("N1 L(-1) = I*pi", _ev("L(-1)", [X, T], functions=L), _sol("I*pi"), NOTOK, None),
        ("N1 L(-2) = log(2) + I*pi", _ev("L(-2)", [X, T], functions=L), _sol("log(2) + I*pi"), NOTOK, None),
        ("N1 step L(-1) = I*pi", _ev("L(-1)", [X, T], functions=L),
         _sol("I*pi", [("compute", "L(-1) = I*pi")]), NOTOK, NOT_VERIFIED),
        ("N1 L(2) = log(2) (control)", _ev("L(2)", [X, T], functions=L), _sol("log(2)"), NOTNO, None),
        ("N1 L(2) = 0 (control)", _ev("L(2)", [X, T], functions=L), _sol("0"), NOTOK, None),
        ("F9 a = 1 claim 0", _ev(F9, [A, X], ["a = 1"]), _sol("0"), NOTOK, None),
        ("F9 a = 1 claim 2*sin(1)", _ev(F9, [A, X], ["a = 1"]), _sol("2*sin(1)"), NOTNO, None),
        ("F9 capital, a = 1 claim 0", _ev(F9.replace("integrate", "Integral"), [A, X], ["a = 1"]), _sol("0"),
         NOTOK, None),
        ("F9 a = 1, step = 0", _ev(F9, [A, X], ["a = 1"]), _sol("2*sin(1)", [("compute", f"{F9} = 0")]),
         ANY, NOT_VERIFIED),
        # the two repros of the third audit (tur3_e6712f5.json, F9: par_giv_W, par_nest_W)
        ("F9 par_giv a*|cos x|, a = 1, claim 0", _ev(PG, [A, X], ["a = 1"]), _sol("0"), NOTOK, None),
        ("F9 par_giv a*|cos x|, a = 1, claim 2*sin(1)", _ev(PG, [A, X], ["a = 1"]), _sol("2*sin(1)"), NOTNO, None),
        ("F9 par_nest claim 0", _ev(PN, [X, Y]), _sol("0"), NOTOK, None),
        ("F9 par_nest claim sin(1)", _ev(PN, [X, Y]), _sol("sin(1)"), NOTNO, None),
    ]


PG = "integrate(a*Abs(cos(x)), (x, -1, 1))"
PN = "integrate(integrate(y*Abs(cos(x)), (x, -1, 1)), (y, 0, 1))"
Y = {"name": "y", "domain": "real"}


def cases_b():
    I0a = "integrate(x, (x, 0, a))"
    LS = "limit(sin(a*x)/x, x, 0)"
    LN = "limit(a*n*sin(pi/n), n, oo)"
    fa = [{"name": "f", "expr": "integrate(a*t, (t, 0, x))", "args": ["x"]}]
    eqI = _ir("solve_equation", {"equation": "x**2 = integrate(t, (t, 0, a))", "var": "x"}, [A, X, T], ["a = 2"],
              shape="set")
    return [
        ("int_0^a x, a = 2, claim 2", _ev(I0a, [A, X], ["a = 2"]), _sol("2"), OK, None),
        ("int_0^a x, a = 2, claim 3", _ev(I0a, [A, X], ["a = 2"]), _sol("3"), NO, None),
        ("Integral_0^a x, a = 2, claim 2", _ev(I0a.replace("integrate", "Integral"), [A, X], ["a = 2"]),
         _sol("2"), OK, None),
        ("Integral_0^a x, a = 2, claim 3", _ev(I0a.replace("integrate", "Integral"), [A, X], ["a = 2"]),
         _sol("3"), NO, None),
        ("2 = a pinned the other way, claim 2", _ev(I0a, [A, X], ["2 = a"]), _sol("2"), OK, None),
        ("a = 2 and a = 3 (clash), claim 2", _ev(I0a, [A, X], ["a = 2", "a = 3"]), _sol("2"), NOTOK, None),
        ("lim sin(ax)/x, a = 3, claim 3", _ev(LS, [A, X], ["a = 3"]), _sol("3"), OK, None),
        ("lim sin(ax)/x, a = 3, claim 0", _ev(LS, [A, X], ["a = 3"]), _sol("0"), NO, None),
        ("Limit sin(ax)/x, a = 3, claim 3", _ev(LS.replace("limit", "Limit"), [A, X], ["a = 3"]), _sol("3"),
         NOTNO, None),
        ("Limit sin(ax)/x, a = 3, claim 0", _ev(LS.replace("limit", "Limit"), [A, X], ["a = 3"]), _sol("0"),
         NOTOK, None),
        ("lim a n sin(pi/n), a = 2, claim 2*pi", _ev(LN, [NP, A], ["a = 2"]), _sol("2*pi"), NOTNO, None),
        ("lim a n sin(pi/n), a = 2, claim 0", _ev(LN, [NP, A], ["a = 2"]), _sol("0"), NOTOK, None),
        ("Limit a n sin(pi/n), a = 2, claim 0", _ev(LN.replace("limit", "Limit"), [NP, A], ["a = 2"]), _sol("0"),
         NOTOK, None),
        ("a**2 = 4 (not a binding): int_0^a x, claim 2", _ev(I0a, [A, X], ["a**2 = 4"]), _sol("2"), NOTNO, None),
        ("a + 1 = 3: lim a n sin(pi/n), claim 0", _ev(LN, [NP, A], ["a + 1 = 3"]), _sol("0"), NOTOK, None),
        ("a + 1 = 3: Limit a n sin(pi/n), claim 0", _ev(LN.replace("limit", "Limit"), [NP, A], ["a + 1 = 3"]),
         _sol("0"), NOTOK, None),
        ("f(x) = int_0^x a t, a = 2: f(3) = 9", _ev("f(3)", [A, X, T], ["a = 2"], functions=fa), _sol("9"), OK,
         None),
        ("f(x) = int_0^x a t, a = 2: f(3) = 18", _ev("f(3)", [A, X, T], ["a = 2"], functions=fa), _sol("18"), NO,
         None),
        ("x**2 = int_0^a t, a = 2: {-sqrt2, sqrt2}", eqI, _sol("{-sqrt(2), sqrt(2)}", kind="set"), NOTNO, None),
        ("x**2 = int_0^a t, a = 2: {2}", eqI, _sol("{2}", kind="set"), NOTOK, None),
    ]


def cases_c():
    LN = "limit(a*n*sin(pi/n), n, oo)"
    eqx = _ir("solve_equation", {"equation": "integrate(t, (t, 0, x)) = 2", "var": "x"}, [X, T], shape="set")
    return [
        ("simplify int_0^a x = a**2/2", _simp("integrate(x, (x, 0, a))", [A, X]), _sol("a**2/2", kind="expression"),
         NOTNO, None),
        ("simplify int_0^a x = a**2", _simp("integrate(x, (x, 0, a))", [A, X]), _sol("a**2", kind="expression"),
         NOTOK, None),
        ("simplify lim sin(ax)/x = a", _simp("limit(sin(a*x)/x, x, 0)", [A, X]), _sol("a", kind="expression"),
         NOTNO, None),
        ("simplify lim sin(ax)/x = 0", _simp("limit(sin(a*x)/x, x, 0)", [A, X]), _sol("0", kind="expression"),
         NOTOK, None),
        ("simplify lim a n sin(pi/n) = 0", _simp(LN, [NP, A]), _sol("0", kind="expression"), NOTOK, None),
        ("simplify lim a n sin(pi/n) = pi*a", _simp(LN, [NP, A]), _sol("pi*a", kind="expression"), NOTNO, None),
        ("simplify Limit a n sin(pi/n) = 0", _simp(LN.replace("limit", "Limit"), [NP, A]),
         _sol("0", kind="expression"), NOTOK, None),
        ("simplify Limit a n sin(pi/n) = pi*a", _simp(LN.replace("limit", "Limit"), [NP, A]),
         _sol("pi*a", kind="expression"), NOTNO, None),
        ("simplify int |cos(ax)| = 0", _simp("integrate(Abs(cos(a*x)), (x, -1, 1))", [A, X]),
         _sol("0", kind="expression"), NOTOK, None),
        ("simplify int 2x dx = x**2 (indefinite)", _simp("integrate(2*x, x)", [X]), _sol("x**2", kind="expression"),
         NOTNO, None),
        ("simplify int 2x dx = x**3 (indefinite)", _simp("integrate(2*x, x)", [X]), _sol("x**3", kind="expression"),
         NOTOK, None),
        ("evaluate lim a n sin(pi/n) = 0, no given", _ev(LN, [NP, A]), _sol("0"), NOTOK, None),
        ("solve int_0^x t = 2: {-2, 2}", eqx, _sol("{-2, 2}", kind="set"), NOTNO, None),
        ("solve int_0^x t = 2: {2}", eqx, _sol("{2}", kind="set"), NOTOK, None),
        ("solve int_0^x t = 2: {}", eqx, _sol("{}", kind="set"), NOTOK, None),
        ("a**2 = 4: int_0^a x claim 2 (both roots give 2)", _ev("integrate(x, (x, 0, a))", [A, X], ["a**2 = 4"]),
         _sol("2"), NOTNO, None),
    ]


def cases_d():
    I0a = "integrate(x, (x, 0, a))"
    LN = "limit(a*n*sin(pi/n), n, oo)"
    return [
        ("step int_0^a x = a**2/2, free a", _simp(I0a, [A, X]),
         _sol("a**2/2", [("compute", f"{I0a} = a**2/2")], kind="expression"), NOTNO, NOT_VERIFIED),
        ("step Integral_0^a x = a**2/2, free a", _simp(I0a, [A, X]),
         _sol("a**2/2", [("compute", "Integral(x, (x, 0, a)) = a**2/2")], kind="expression"), NOTNO, NOT_VERIFIED),
        ("step int_0^a x = a**2, free a (wrong)", _simp(I0a, [A, X]),
         _sol("a**2/2", [("compute", f"{I0a} = a**2")], kind="expression"), ANY, {"refuted", "unknown"}),
        ("step lim a n sin(pi/n) = pi*a, free a (right)", _simp(LN, [NP, A]),
         _sol("pi*a", [("compute", f"{LN} = pi*a")], kind="expression"), NOTNO, {"unknown", "skipped", "verified"}),
        ("step lim a n sin(pi/n) = 0, free a (wrong)", _simp(LN, [NP, A]),
         _sol("pi*a", [("compute", f"{LN} = 0")], kind="expression"), ANY, NOT_VERIFIED),
        ("step Limit a n sin(pi/n) = 0, free a (wrong)", _simp(LN, [NP, A]),
         _sol("pi*a", [("compute", f"{LN.replace('limit', 'Limit')} = 0")], kind="expression"), ANY, NOT_VERIFIED),
        ("step int_0^a x = 2, a = 2", _ev(I0a, [A, X], ["a = 2"]), _sol("2", [("compute", f"{I0a} = 2")]),
         NOTNO, {"verified"}),
        ("step int_0^a x = 3, a = 2", _ev(I0a, [A, X], ["a = 2"]), _sol("2", [("compute", f"{I0a} = 3")]),
         NO, {"refuted"}),
        ("step lim sin(ax)/x = 3, a = 3", _ev("limit(sin(a*x)/x, x, 0)", [A, X], ["a = 3"]),
         _sol("3", [("compute", "limit(sin(a*x)/x, x, 0) = 3")]), NOTNO, {"verified", "unknown"}),
        ("step int 2x dx = x**2 (indefinite, derivative certificate)", _simp("integrate(2*x, x)", [X]),
         _sol("x**2", [("compute", "integrate(2*x, x) = x**2")], kind="expression"), NOTNO, {"verified"}),
        ("eq step int_0^a x = a**2/2 then claim, a = 2", _ev(I0a, [A, X], ["a = 2"]),
         _sol("2", [("eq", f"{I0a} = a**2/2"), ("eq", "a**2/2 = 2")]), NOTNO, None),
        # eq steps: read in the problem's namespace, where the parse computed the form
        ("eq step a = 1: PG = 0 (wrong)", _ev(PG, [A, X], ["a = 1"]), _sol("2*sin(1)", [("eq", f"{PG} = 0")]),
         ANY, {"refuted", "unknown"}),
        ("eq step a = 1: PG = 2*sin(1) (right)", _ev(PG, [A, X], ["a = 1"]),
         _sol("2*sin(1)", [("eq", f"{PG} = 2*sin(1)")]), NOTNO, {"verified", "unknown", "skipped"}),
        ("eq step a = 2: LN = 0 (wrong)", _ev(LN, [NP, A], ["a = 2"]), _sol("2*pi", [("eq", f"{LN} = 0")]),
         ANY, {"refuted", "unknown"}),
        ("eq step a = 2: LN = 2*pi (right)", _ev(LN, [NP, A], ["a = 2"]), _sol("2*pi", [("eq", f"{LN} = 2*pi")]),
         NOTNO, {"verified", "unknown", "skipped"}),
        ("eq step free a: LN = 0 (wrong)", _simp(LN, [NP, A]), _sol("pi*a", [("eq", f"{LN} = 0")], kind="expression"),
         ANY, NOT_VERIFIED),
        ("eq step free a: int_0^a x = a**2/2", _simp(I0a, [A, X]),
         _sol("a**2/2", [("eq", f"{I0a} = a**2/2")], kind="expression"), NOTNO, {"unknown", "skipped"}),
    ]


def cases_e():
    return [
        ("closed int_0^3 x**2 = 9", _ev("integrate(x**2, (x, 0, 3))", [X]), _sol("9"), OK, None),
        ("closed int_0^3 x**2 = 8", _ev("integrate(x**2, (x, 0, 3))", [X]), _sol("8"), NO, None),
        ("closed int |cos x| = 0", _ev("integrate(Abs(cos(x)), (x, -1, 1))", [X]), _sol("0"), NOTOK, None),
        ("closed int |cos x| = 2*sin(1)", _ev("integrate(Abs(cos(x)), (x, -1, 1))", [X]), _sol("2*sin(1)"), NOTNO,
         None),
        ("closed lim sin(x)/x = 1", _ev("limit(sin(x)/x, x, 0)", [X]), _sol("1"), OK, None),
        ("closed lim sin(x)/x = 0", _ev("limit(sin(x)/x, x, 0)", [X]), _sol("0"), NO, None),
        ("closed lim n sin(pi/n) = pi", _ev("limit(n*sin(pi/n), n, oo)", [NP]), _sol("pi"), NOTNO, None),
        ("closed lim n sin(pi/n) = 0", _ev("limit(n*sin(pi/n), n, oo)", [NP]), _sol("0"), NOTOK, None),
        ("definite_integral task x**2 0..3 = 9",
         _ir("definite_integral", {"integrand": "x**2", "var": "x", "a": "0", "b": "3"}, [X]), _sol("9"), OK, None),
        ("definite_integral task, bound a, a = 2: 8/3",
         _ir("definite_integral", {"integrand": "x**2", "var": "x", "a": "0", "b": "a"}, [X, A], ["a = 2"]),
         _sol("8/3"), NOTNO, None),
        ("antiderivative task 2x: x**2",
         _ir("antiderivative", {"integrand": "2*x", "var": "x"}, [X], shape="expression"),
         _sol("x**2", kind="expression"), NOTNO, None),
        ("limit task sin(x)/x at 0: 1", _ir("limit", {"expr": "sin(x)/x", "var": "x", "to": "0"}, [X]), _sol("1"),
         OK, None),
        ("given a = integrate(2x,(x,0,1)): x**2 = a {-1,1}",
         _ir("solve_equation", {"equation": "x**2 = a", "var": "x"}, [X, A], ["a = integrate(2*x, (x, 0, 1))"],
             shape="set"), _sol("{-1, 1}", kind="set"), OK, None),
        ("closed step int_0^3 x**2 = 9", _ev("integrate(x**2, (x, 0, 3))", [X]),
         _sol("9", [("compute", "integrate(x**2, (x, 0, 3)) = 9")]), OK, {"verified"}),
    ]


def cases_f():
    """LaTeX, pins through constraints and earlier steps, function arguments named like a pinned
    symbol, and the task certificates that take a parametric expression themselves."""
    AC = lambda c: [dict(A, constraints=[c])]  # noqa: E731
    fx = [{"name": "f", "expr": "integrate(t, (t, 0, x))", "args": ["x"]}]
    g = [{"name": "g", "expr": "limit(sqrt(a + t**2), t, 0)", "args": ["a"]}]
    lt = lambda e, to, gv=(): _ir("limit", {"expr": e, "var": "n", "to": to}, [NP, A], gv)  # noqa: E731
    di = lambda gv: _ir("definite_integral", {"integrand": "Abs(cos(a*x))", "var": "x", "a": "-1", "b": "1"},  # noqa: E731
                        [X, A], gv)
    return [
        ("LaTeX int_0^a x, a = 2: 2", _ev(r"\int_0^a x\,dx", [A, X], ["a = 2"]), _sol("2"), OK, None),
        ("LaTeX int_0^a x, a = 2: 3", _ev(r"\int_0^a x\,dx", [A, X], ["a = 2"]), _sol("3"), NO, None),
        ("LaTeX lim a n sin(pi/n), a = 2: 0", _ev(r"\lim_{n \to \infty} a n \sin(\pi/n)", [NP, A], ["a = 2"]),
         _sol("0"), NOTOK, None),
        ("LaTeX simplify lim a n sin(pi/n) = 0", _simp(r"\lim_{n \to \infty} a n \sin(\pi/n)", [NP, A]),
         _sol("0", kind="expression"), NOTOK, None),
        ("LaTeX simplify int_0^a |cos x| a ... = 0", _simp(r"\int_{-1}^{1} a |\cos x|\,dx", [A, X]),
         _sol("0", kind="expression"), NOTOK, None),
        ("constraint a = 2: step int_0^a x = 3", _ev("a**2/2", AC("a = 2") + [X]),
         _sol("2", [("compute", "integrate(x, (x, 0, a)) = 3")]), NO, {"refuted"}),
        ("constraint a = 2: step int_0^a x = 2", _ev("a**2/2", AC("a = 2") + [X]),
         _sol("2", [("compute", "integrate(x, (x, 0, a)) = 2")]), NOTNO, {"verified"}),
        ("a + 1 = 3, eq a = 2, step int_0^a x = 3", _ev("a**2/2", [A, X], ["a + 1 = 3"]),
         _sol("2", [("eq", "a = 2"), ("compute", "integrate(x, (x, 0, a)) = 3")]), NO, {"refuted"}),
        ("x = 3 given, f(x) = int_0^x t: f(2) = 2", _ev("f(2)", [X, T], ["x = 3"], functions=fx), _sol("2"), OK,
         None),
        ("x = 3 given, f(x) = int_0^x t: f(2) = 9/2", _ev("f(2)", [X, T], ["x = 3"], functions=fx), _sol("9/2"),
         NO, None),
        ("g(a) = lim sqrt(a + t**2): g(4) = 2", _ev("g(4)", [A, T], functions=g), _sol("2"), NOTNO, None),
        ("g(a) = lim sqrt(a + t**2): g(4) = 4", _ev("g(4)", [A, T], functions=g), _sol("4"), NOTOK, None),
        ("indefinite int a x dx, a = 2: x**2", _simp("integrate(a*x, x)", [A, X], ["a = 2"]),
         _sol("x**2", kind="expression"), NOTNO, None),
        ("limit task real n, a n sin(pi/n), a = 2: 2*pi",
         _ir("limit", {"expr": "a*n*sin(pi/n)", "var": "n", "to": "oo"}, [{"name": "n", "domain": "real"}, A],
             ["a = 2"]), _sol("2*pi"), OK, None),
        ("limit task real n, a n sin(pi/n), a = 2: 0",
         _ir("limit", {"expr": "a*n*sin(pi/n)", "var": "n", "to": "oo"}, [{"name": "n", "domain": "real"}, A],
             ["a = 2"]), _sol("0"), NO, None),
        ("limit task sin(ax)/x, a = 3: 3", _ir("limit", {"expr": "sin(a*x)/x", "var": "x", "to": "0"}, [X, A],
                                                ["a = 3"]), _sol("3"), OK, None),
        ("limit task sin(ax)/x, free a: 0", _ir("limit", {"expr": "sin(a*x)/x", "var": "x", "to": "0"}, [X, A]),
         _sol("0"), NOTOK, None),
        ("limit task a n sin(pi/n), free a: 0", lt("a*n*sin(pi/n)", "oo"), _sol("0"), NOTOK, None),
        ("limit task a n sin(pi/n), a = 2: 0", lt("a*n*sin(pi/n)", "oo", ["a = 2"]), _sol("0"), NOTOK, None),
        ("limit task a n sin(pi/n), a = 2: 2*pi", lt("a*n*sin(pi/n)", "oo", ["a = 2"]), _sol("2*pi"), NOTNO, None),
        ("definite_integral task |cos(ax)|, a = 1: 0", di(["a = 1"]), _sol("0"), NOTOK, None),
        ("definite_integral task |cos(ax)|, a = 1: 2*sin(1)", di(["a = 1"]), _sol("2*sin(1)"), NOTNO, None),
        ("definite_integral task |cos(ax)|, free a: 0", di([]), _sol("0"), NOTOK, None),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f}


def _summ(r):
    lay, steps = [], []
    for l in r.layers:
        ev = l.evidence or {}
        reason = ev.get("reason") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:120] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in ev.get("steps", []):
                steps.append((s.get("id"), s.get("status"),
                              str(s.get("reason") or (s.get("evidence") or {}).get("reason") or "")[:100]))
    return lay, steps


def main():
    import mathverify
    from mathverify.verifier import verify
    print(f"mathverify: {mathverify.__file__}", flush=True)
    out_path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else None
    only = {a for a in sys.argv[1:] if not a.endswith(".json")}
    rows, bad = [], 0
    for g, fn in GROUPS.items():
        if only and g not in only:
            continue
        for label, ir, sol, exp, last in fn():
            t0 = time.perf_counter()
            try:
                r = verify(ir, sol)
                v = r.verdict
                lay, steps = _summ(r)
            except Exception as e:  # noqa: BLE001
                v, lay, steps = f"EXC {type(e).__name__}: {e}"[:200], [], []
            ok = v in exp and (last is None or (bool(steps) and steps[-1][1] in last))
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": v, "expected": sorted(exp), "ok": ok,
                         "layers": lay, "steps": [list(s) for s in steps]})
            print(f"{g} | {'ok ' if ok else 'BAD'} | {v:9s} (exp {'/'.join(sorted(exp))}) | "
                  f"{time.perf_counter() - t0:5.1f}s | {label}", flush=True)
            for s in steps:
                print(f"      step {s[0]}:{s[1]}:{s[2]}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
