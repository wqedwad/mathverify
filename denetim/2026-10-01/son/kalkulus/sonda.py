"""The last attack (A+ son saldırı, 16 Oct 2026), lens 3 (calculus, definedness): the fixes of the branch
wip/son-kalkulus (decisions: the main session's `kararlar.txt`, "MERCEK 3"; findings SON-G3-YO-1..5).

    A  SON-G3-YO-1   at(diff(·)) and the pinned diff(·): a Piecewise's switch point and atan2/arg's branch cut are no
                     points of the derivative unless it is proved to exist there (u continuous, the two one-sided
                     derivatives equal: certify.calculus's criterion); a C1 junction keeps its value. Siblings: x*|x|
                     (a point with a derivative read as one without), the derivative task / tangent / step at a
                     Piecewise corner (SymPy's one-sided limit reads the wrong branch), textbook piecewise questions
    B  SON-G3-YO-2   a tangent claim read as written: undefined at a point of the true line (the point of tangency
                     first) INCORRECT, a condition not proved on the whole line UNKNOWN
    C  SON-G3-YO-3   a closed infinite argument written as a limit is no value (A-YO-5's rule on the value)
    D  SON-G3-YO-4   over ℂ a closed division by 0 or pole inside any operation has no value (A-YO-3's rule)
    E  SON-G3-YO-5   record: (x**n)' = n*x**(n - 1) for n a positive integer stays CORRECT (D4E4-U5)
    K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/son/kalkulus/sonda.py [out.json] [groups]

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
VER = {"verified"}
NEITHER = {"unknown", "skipped", None}

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
A_ = {"name": "a", "domain": "real"}
B_ = {"name": "b", "domain": "real"}
NP = {"name": "n", "domain": "positive_integer"}
NN = {"name": "n", "domain": "nonneg_integer"}
K_ = {"name": "k", "domain": "integer"}

PW_ABS = "Piecewise((-x, x < 0), (x, x >= 0))"
JUMP = "Piecewise((x**2, x < 1), (2*x, x >= 1))"
CORNER = "Piecewise((x**2, x < 1), (3*x - 2, x >= 1))"
CUBE = "Piecewise((x**3, x < 1), (3*x - 2, x >= 1))"
C1 = "Piecewise((x**2 + 1, x < 1), (2*x, x >= 1))"
C1B = "Piecewise((x**2, x < 1), (2*x - 1, x >= 1))"
C2 = "Piecewise((x**3, x < 0), (x**3 + x**4, x >= 0))"
ROOF = "Piecewise((x + 2, x < 0), (2 - x, x >= 0))"
MC = {"A": "-1", "B": "0", "C": "1", "D": "2", "E": "Yoktur"}
MC2 = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "Yoktur"}


def ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update({k: v for k, v in extra.items() if v is not None})
    return d


def sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


DNE = {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}


def fn(body):
    return [{"name": "f", "expr": body, "args": ["x"], "params": []}] if body else None


def ev(expr, f=None, givens=(), vars_=None, options=None, dod=None):
    return ir("evaluate", {"expr": expr}, givens, vars_, functions=fn(f), options=options, domain_of_discourse=dod)


def der(f, at=None, vars_=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    return ir("derivative", p, (), vars_, "scalar" if at is not None else "expression")


def tan(f, at, vars_=None):
    return ir("tangent_line", {"f": f, "var": "x", "at": at, "dep": "y"}, (), list(vars_ or [X]) + [Y], "equation")


def se(eq, f=None):
    return ir("solve_equation", {"var": "x", "equation": eq}, (), None, "set", functions=fn(f))


def si(ineq, f=None):
    return ir("solve_inequality", {"var": "x", "inequality": ineq}, (), None, "interval", functions=fn(f))


def lim(expr, to):
    return ir("limit", {"expr": expr, "var": "x", "to": to})


def at1(f, p="1", order=1):
    return ev(f"at(diff(f(x), x{', ' + str(order) if order > 1 else ''}), x, {p})", f)


# A: SON-G3-YO-1 ------------------------------------------------------------------------------------------------
def cases_a():
    return [
        # the findings: no value where the derivative does not exist
        ("pw |x|: f'(0) = 1", at1(PW_ABS, "0"), sol("1"), UNK, None),
        ("jump: f'(1) = 2", at1(JUMP), sol("2"), UNK, None),
        ("corner: f'(1) = 3", at1(CORNER), sol("3"), UNK, None),
        ("corner: f'(1) = 2", at1(CORNER), sol("2"), UNK, None),
        ("MC pw |x| f'(0): C = 1", ev("at(diff(f(x), x), x, 0)", PW_ABS, options=MC), sol("1", option="C"), NOTOK, None),
        ("MC jump f'(1): B = 2", ev("at(diff(f(x), x), x, 1)", JUMP, options=MC2), sol("2", option="B"), NOTOK, None),
        ("x^3 | 3x-2: f''(1) = 0", at1(CUBE, "1", 2), sol("0"), UNK, None),
        ("x^3 | 3x-2: f''(1) = 6", at1(CUBE, "1", 2), sol("6"), UNK, None),
        ("pinned x = 1: (jump)' = 2", ev("diff(f(x), x)", JUMP, ("x = 1",)), sol("2"), UNK, None),
        ("pinned x = 0: (pw |x|)' = 1", ev("diff(f(x), x)", PW_ABS, ("x = 0",)), sol("1"), UNK, None),
        ("atan2(x, -1)'(0) = -1", ev("at(diff(atan2(x, -1), x), x, 0)"), sol("-1"), UNK, None),
        ("arg(-1 + I x)'(0) = -1", ev("at(diff(arg(-1 + I*x), x), x, 0)"), sol("-1"), UNK, None),
        ("solve f' = -1, f = atan2(x, -1): {0}", se("diff(f(x), x) = -1", "atan2(x, -1)"), sol("{0}", "set"), NO, None),
        ("solve f' = -1, f = atan2(x, -1): empty", se("diff(f(x), x) = -1", "atan2(x, -1)"), sol("EmptySet", "set"),
         OK, None),
        # siblings: a point with a derivative is no point without one (x*|x| at 0 has f'(0) = 0)
        ("solve (x|x|)' = 0: {0}", se("diff(x*Abs(x), x) = 0"), sol("{0}", "set"), OK, None),
        ("solve (x|x|)' = 0: empty", se("diff(x*Abs(x), x) = 0"), sol("EmptySet", "set"), NO, None),
        ("solve f' = 0, f = x|x|: {0}", se("diff(f(x), x) = 0", "x*Abs(x)"), sol("{0}", "set"), OK, None),
        ("solve f' = 0, f = x|x|: empty", se("diff(f(x), x) = 0", "x*Abs(x)"), sol("EmptySet", "set"), NO, None),
        # siblings: the derivative task, the tangent and a step at a Piecewise corner (SymPy's one-sided limit)
        ("derivative task pw |x| at 0: 1", der(PW_ABS, "0"), sol("1"), NO, None),
        ("derivative task pw |x| at 0: DNE", der(PW_ABS, "0"), DNE, OK, None),
        ("derivative task roof at 0: DNE", der(ROOF, "0"), DNE, OK, None),
        ("derivative task roof at 0: -1", der(ROOF, "0"), sol("-1"), NO, None),
        ("derivative task jump at 1: DNE", der(JUMP, "1"), DNE, OK, None),
        ("derivative task jump at 1: 2", der(JUMP, "1"), sol("2"), NO, None),
        ("derivative function pw |x|", der(PW_ABS), sol("Piecewise((-1, x < 0), (1, x > 0))", "expression"), OK, None),
        ("tangent roof at 0: DNE", tan(ROOF, "0"), DNE, OK, None),
        ("tangent roof at 0: y = x + 2", tan(ROOF, "0"), sol("y = x + 2", "equation"), NO, None),
        ("step at(diff(f)) of roof at 0 = -1", ev("x", ROOF, ("x = 1",)),
         sol("1", steps=["at(diff(f(x), x), x, 0) = -1"]), {"CORRECT", "UNKNOWN", "INCORRECT"}, {"refuted", "unknown"}),
        # textbook: a C1 junction keeps its derivative, off the switch point the derivative is read as before
        ("C1 x^2+1 | 2x: f'(1) = 2", at1(C1), sol("2"), OK, None),
        ("C1 x^2 | 2x-1: f'(1) = 2", at1(C1B), sol("2"), OK, None),
        ("C1 x^2 | 2x-1: f'(1) = 3", at1(C1B), sol("3"), NO, None),
        ("C1 MC f'(1): B = 2", ev("at(diff(f(x), x), x, 1)", C1, options=MC2), sol("2", option="B"), OK, None),
        ("C1 MC f'(1): C = 3", ev("at(diff(f(x), x), x, 1)", C1, options=MC2), sol("3", option="C"), NO, None),
        ("C2 x^3 | x^3+x^4: f''(0) = 0", at1(C2, "0", 2), sol("0"), OK, None),
        ("C1 pinned x = 1: f' = 2", ev("diff(f(x), x)", C1, ("x = 1",)), sol("2"), OK, None),
        ("C1 derivative task at 1: 2", der(C1, "1"), sol("2"), OK, None),
        ("C1 tangent at 1: y = 2x", tan(C1, "1"), sol("y = 2*x", "equation"), OK, None),
        ("roof: f'(-1) = 1", at1(ROOF, "-1"), sol("1"), OK, None),
        ("roof: f'(3) = -1", at1(ROOF, "3"), sol("-1"), OK, None),
        ("roof: f'(3) = 1", at1(ROOF, "3"), sol("1"), NO, None),
        ("roof: f'(0) = -1", at1(ROOF, "0"), sol("-1"), UNK, None),
        ("roof: lim at 0 = 2", lim(ROOF, "0"), sol("2"), OK, None),
        ("jump: f'(2) = 2", at1(JUMP, "2"), sol("2"), OK, None),
        ("pw |x|: f'(-3) = -1", at1(PW_ABS, "-3"), sol("-1"), OK, None),
        ("|x|: derivative task at 0: DNE", der("Abs(x)", "0"), DNE, OK, None),
        ("|x|: derivative task at 2: 1", der("Abs(x)", "2"), sol("1"), OK, None),
        ("|x|: at(diff) at -2 = -1", ev("at(diff(Abs(x), x), x, -2)"), sol("-1"), OK, None),
        ("|x|: derivative x/|x|", der("Abs(x)"), sol("x/Abs(x)", "expression"), OK, None),
        ("|x - 2|: derivative (x - 2)/|x - 2|", der("Abs(x - 2)"), sol("(x - 2)/Abs(x - 2)", "expression"), OK, None),
        ("solve |x|' > 0: (0, oo)", si("diff(Abs(x), x) > 0"), sol("Interval.open(0, oo)", "interval"), OK, None),
        ("a, b for differentiability: a + b = 3", ev("a + b", vars_=[A_, B_, X], givens=(
            "a*1**2 + b = 4*1 - 1", "at(diff(a*x**2 + b, x), x, 1) = at(diff(4*x - 1, x), x, 1)")), sol("3"), OK, None),
        ("a, b for differentiability: a + b = 4", ev("a + b", vars_=[A_, B_, X], givens=(
            "a*1**2 + b = 4*1 - 1", "at(diff(a*x**2 + b, x), x, 1) = at(diff(4*x - 1, x), x, 1)")), sol("4"), NO, None),
        ("atan2(x, 1)'(0) = 1", ev("at(diff(atan2(x, 1), x), x, 0)"), sol("1"), OK, None),
        ("atan2(x, -1)'(1) = -1/2", ev("at(diff(atan2(x, -1), x), x, 1)"), sol("-1/2"), OK, None),
        ("atan2(x**2, -1)'(0) = 0", ev("at(diff(atan2(x**2, -1), x), x, 0)"), sol("0"), OK, None),
        ("arg(1 + I x)'(0) = 1", ev("at(diff(arg(1 + I*x), x), x, 0)"), sol("1"), OK, None),
        ("solve (x^3)' = 3: {-1, 1}", se("diff(x**3, x) = 3"), sol("{-1, 1}", "set"), OK, None),
    ]


# B: SON-G3-YO-2 ------------------------------------------------------------------------------------------------
def cases_b():
    out = []
    for f, a, line in [("x**2", "1", "y = 2*x - 1 + 0*log(x - 1)"), ("x**2", "1", "y = 2*x - 1 + 0*log(-x)"),
                       ("x**2", "1", "y = 2*x - 1 + 0*sqrt(x - 5)"), ("sin(x)", "0", "y = x + 0*cot(x)"),
                       ("exp(x)", "0", "y = x + 1 + 0*log(x)"), ("log(x)", "1", "y = (x**2 - x)/x"),
                       ("x**2", "1", "y = 2*x - 1 + 0*sqrt(x - 1)"), ("x**2", "1", "y = 2*x - 1 + 0*sqrt(1 - x)"),
                       ("x**2", "1", "y = 2*x - 1 + 0*log(x)"), ("x**2", "1", "y = (2*x**2 - x)/x"),
                       ("x**2", "1", "y = 2*x - 1 + 0/x"), ("x**2", "1", "y = 2*x - 1 + 0*asin(x)"),
                       ("x**2", "1", "y = 2*x - 1 + 0*tan(x)"), ("x**2", "1", "y = (2*x - 1)*x/x"),
                       ("x**2", "1", r"y = 2x - 1 + 0\cdot\sqrt{x-5}"), ("x**2", "1", "2*x - 1 + 0*sqrt(x - 5)"),
                       ("x**2", "1", "y - 2*x + 1 + 0*sqrt(x - 5) = 0"), ("x**2", "1", "y = 2*x - 1 + 0*sqrt(y - 5)"),
                       ("x**2", "1", "y = 2*x - 1 + 0*log(sin(x))"), ("sqrt(x)", "4", "y = x/4 + 1 + 0*log(x - 4)"),
                       ("x**3", "0", "y = 0*x + 0*sqrt(-x)"), ("sin(x)", "0", "y = x*sin(x)/sin(x)")]:
        out.append((f"tangent {f} at {a}: {line}", tan(f, a), sol(line, "equation"), NOTOK, None))
    for f, a, line in [("x**2", "1", "y = 2*x - 1 + 0*log(x - 1)"), ("x**2", "1", "y = 2*x - 1 + 0*log(-x)"),
                       ("sin(x)", "0", "y = x + 0*cot(x)"), ("exp(x)", "0", "y = x + 1 + 0*log(x)"),
                       ("log(x)", "1", "y = (x**2 - x)/x"), ("x**3", "0", "y = 0*x + 0*sqrt(-x)")]:
        out.append((f"tangent {f} at {a}: {line} (a point of the line)", tan(f, a), sol(line, "equation"), NO, None))
    for f, a, line in [("x**2", "1", "y = 2*x - 1"), ("x**2", "1", "2*x - y = 1"), ("x**2", "1", "y - 1 = 2*(x - 1)"),
                       ("x**2", "1", "2*x - 1"), ("x**2", "1", "y = 2*x - 1 + 0*sqrt(x**2 + 1)"),
                       ("x**2", "1", "y = 2*x - 1 + 0*log(x**2 + 1)"), ("sin(x)", "0", "y = x"),
                       ("log(x)", "1", "y = x - 1"), ("sqrt(x)", "4", "y = x/4 + 1"), ("exp(x)", "0", "y = x + 1")]:
        out.append((f"tangent {f} at {a}: {line} (right)", tan(f, a), sol(line, "equation"), OK, None))
    out.append(("tangent x**2 at 1: y = 2*x + 1 (wrong)", tan("x**2", "1"), sol("y = 2*x + 1", "equation"), NO, None))
    return out


# C: SON-G3-YO-3 ------------------------------------------------------------------------------------------------
def cases_c():
    q = lim("exp(-1/x**2)", "0")
    e = lambda t: ev(t, vars_=[])  # noqa: E731
    return [
        ("arctan(lim_{x->0} 1/x^2) = pi/2", e(r"\arctan\left(\lim_{x \to 0} \frac{1}{x^2}\right)"), sol("pi/2"), UNK, None),
        ("0*sin(lim_{x->oo} x) = 0", e(r"0 \cdot \sin\left(\lim_{x \to \infty} x\right)"), sol("0"), UNK, None),
        ("1/lim_{x->0} 1/x^2 = 0", e(r"\frac{1}{\lim_{x \to 0} \frac{1}{x^2}}"), sol("0"), UNK, None),
        ("e^{-lim_{x->oo} x} = 0", e(r"e^{-\lim_{x \to \infty} x}"), sol("0"), UNK, None),
        ("2^{-lim_{x->oo} x} = 0", e(r"2^{-\lim_{x \to \infty} x}"), sol("0"), UNK, None),
        ("tanh(lim_{x->oo} x) = 1", e(r"\tanh\left(\lim_{x \to \infty} x\right)"), sol("1"), UNK, None),
        ("arctan(lim_{n->oo} 2^n) = pi/2", e(r"\arctan\left(\lim_{n \to \infty} 2^n\right)"), sol("pi/2"), UNK, None),
        ("canonical atan(Limit(1/x**2, x, 0)) = pi/2", ev("atan(Limit(1/x**2, x, 0))"), sol("pi/2"), UNK, None),
        ("canonical exp(-Limit(x, x, oo)) = 0", ev("exp(-Limit(x, x, oo))"), sol("0"), UNK, None),
        ("step e^{-lim_{x->0} 1/x^2} = 0", q, sol("0", steps=[r"e^{-\lim_{x \to 0} \frac{1}{x^2}} = 0"]), OK, NEITHER),
        ("step control e^{-oo} = 0", q, sol("0", steps=[r"e^{-\infty} = 0"]), OK, NEITHER),
        ("control arctan(oo) = pi/2", e(r"\arctan(\infty)"), sol("pi/2"), UNK, None),
        ("control lim_{x->0} 1/x^2 = oo", lim("1/x**2", "0"), sol("oo"), OK, None),
        ("control arctan(lim_{x->0} (x + 1)) = pi/4", e(r"\arctan\left(\lim_{x \to 0} (x + 1)\right)"), sol("pi/4"),
         OK, None),
        ("control e^{lim_{x->0} sin x/x} = e", e(r"e^{\lim_{x \to 0} \frac{\sin x}{x}}"), sol("E"), OK, None),
        ("control 1/lim_{x->1} x = 1", e(r"\frac{1}{\lim_{x \to 1} x}"), sol("1"), OK, None),
        ("control 1/lim_{x->1} x = 2", e(r"\frac{1}{\lim_{x \to 1} x}"), sol("2"), NO, None),
        ("control exp(-Sum(1/2**k, (k, 1, oo))) = exp(-1)", ev("exp(-Sum(1/2**k, (k, 1, oo)))", vars_=[K_]),
         sol("exp(-1)"), OK, None),
    ]


# D: SON-G3-YO-4 ------------------------------------------------------------------------------------------------
def cases_d():
    c = lambda t: ev(t, vars_=[], dod="complex")  # noqa: E731
    return [
        ("C |1/0| = oo", c("Abs(1/0)"), sol("oo"), UNK, None),
        ("C acot(|1/0|) = 0", c("acot(Abs(1/0))"), sol("0"), UNK, None),
        ("C exp(-|1/(1 + i^2)|) = 0", c("exp(-Abs(1/(1 + I**2)))"), sol("0"), UNK, None),
        ("C acot(|tan(pi/2)|) = 0", c("acot(Abs(tan(pi/2)))"), sol("0"), UNK, None),
        ("C acot(|log 0|) = 0", c("acot(Abs(log(0)))"), sol("0"), UNK, None),
        ("C acot(|cot 0|) = 0", c("acot(Abs(cot(0)))"), sol("0"), UNK, None),
        (r"C \cot^{-1}|1/0| = 0", c(r"\cot^{-1}\left|\frac{1}{0}\right|"), sol("0"), UNK, None),
        ("C control 1/0 = zoo", c("1/0"), sol("zoo"), UNK, None),
        ("C control 1/(1/0) = 0", c("1/(1/0)"), sol("0"), UNK, None),
        ("R control acot(|1/0|) = 0", ev("acot(Abs(1/0))", vars_=[]), sol("0"), UNK, None),
        ("C control sqrt(-4) = 2i", c("sqrt(-4)"), sol("2*I"), OK, None),
        ("C control log(-1) = i pi", c("log(-1)"), sol("I*pi"), OK, None),
        ("C control |1/(1 + i)| = sqrt(2)/2", c("Abs(1/(1 + I))"), sol("sqrt(2)/2"), OK, None),
        ("C control 1/(2 + i**2) = 1", c("1/(2 + I**2)"), sol("1"), OK, None),
        ("C control tan(pi/4) = 1", c("tan(pi/4)"), sol("1"), OK, None),
        ("C control i**2 = -1", c("I**2"), sol("-1"), OK, None),
    ]


# E: SON-G3-YO-5 (record) ---------------------------------------------------------------------------------------
def cases_e():
    return [
        ("[n in Z+] (x**n)' = n*x**(n - 1)", der("x**n", vars_=[X, NP]), sol("n*x**(n - 1)", "expression"), OK, None),
        ("[n in N] (x**(n + 1))' = (n + 1)*x**n", der("x**(n + 1)", vars_=[X, NN]), sol("(n + 1)*x**n", "expression"),
         OK, None),
        ("[n in Z+] (x**n)' = x**(n - 1) wrong", der("x**n", vars_=[X, NP]), sol("x**(n - 1)", "expression"), NO, None),
        ("control (x)' = x**0", der("x"), sol("x**0", "expression"), UNK, None),
        ("control (x)' = 1", der("x"), sol("1", "expression"), OK, None),
    ]


# K: controls ----------------------------------------------------------------------------------------------------
def cases_k():
    return [
        ("d x**3 = 3x**2", der("x**3"), sol("3*x**2", "expression"), OK, None),
        ("d x**3 at 2 = 12", der("x**3", "2"), sol("12"), OK, None),
        ("at(diff(x**3), x, 2) = 12", ev("at(diff(x**3, x), x, 2)"), sol("12"), OK, None),
        ("at(diff(x**3), x, 2) = 11", ev("at(diff(x**3, x), x, 2)"), sol("11"), NO, None),
        ("at(diff(Abs(x - 1)), x, 1) = 0", ev("at(diff(Abs(x - 1), x), x, 1)"), sol("0"), UNK, None),
        ("at(diff(Abs(x - 1)), x, 3) = 1", ev("at(diff(Abs(x - 1), x), x, 3)"), sol("1"), OK, None),
        ("at(diff(sqrt(x)), x, 4) = 1/4", ev("at(diff(sqrt(x), x), x, 4)"), sol("1/4"), OK, None),
        ("x**2 = 4: {-2, 2}", se("x**2 = 4"), sol("{-2, 2}", "set"), OK, None),
        ("solve (x**3 - 3x)' = 0: {-1, 1}", se("diff(x**3 - 3*x, x) = 0"), sol("{-1, 1}", "set"), OK, None),
        ("solve (|x - 2|)' = 1: (2, oo) as an interval", si("diff(Abs(x - 2), x) > 0"),
         sol("Interval.open(2, oo)", "interval"), OK, None),
        ("tangent x**3 at 1: y = 3x - 2", tan("x**3", "1"), sol("y = 3*x - 2", "equation"), OK, None),
        ("lim sin(x)/x at 0 = 1", lim("sin(x)/x", "0"), sol("1"), OK, None),
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
