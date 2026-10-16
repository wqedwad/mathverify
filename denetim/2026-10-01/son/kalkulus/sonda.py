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
    F  the evening's additions: G2RK-13 (a real root's kink), G2RK-14 (a claim's odd root on the declared region),
                     G2RK-15 (extremum of a fractional or irrational power), SON-G3-RK-1 (x**pi on an unconstrained x),
                     RK-2 (n >= 2 on the claim's exponent), RK-9 (a trigonometric condition strict at the point),
                     RK-4 (R - {2}, \\setminus, \\cup)
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
        ("|sin x|' at pi/2 = 0", ev("at(diff(Abs(sin(x)), x), x, pi/2)"), sol("0"), OK, None),
        ("|sin x|' at pi = -1", ev("at(diff(Abs(sin(x)), x), x, pi)"), sol("-1"), UNK, None),
        ("|x**2 - 4|' at 3 = 6 (1)", ev("at(diff(Abs(x**2 - 4), x), x, 3)"), sol("6"), OK, None),
        ("|x**2 - 4|' at 3 = 6 (2)", ev("at(diff(Abs(x**2 - 4), x), x, 3)"), sol("6"), OK, None),
        ("|x**2 - 4|' at 3 = 5", ev("at(diff(Abs(x**2 - 4), x), x, 3)"), sol("5"), NO, None),
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


# F: the additions of the evening (G2RK-13/14/15, SON-G3-RK-1/2/4/9) ---------------------------------------------
XP = {"name": "x", "domain": "real", "constraints": ["x > 0"]}
NP2 = {"name": "n", "domain": "positive_integer", "constraints": ["n >= 2"]}
NP3 = {"name": "n", "domain": "positive_integer", "constraints": ["n >= 3"]}


def anti(f):
    return ir("antiderivative", {"integrand": f, "var": "x"}, (), None, "expression")


def ext(f, which, interval):
    return ir("extremum", {"f": f, "var": "x", "which": which, "interval": interval})


def derk(f, order, vars_):
    return ir("derivative", {"f": f, "var": "x", "order": order}, (), vars_, "expression")


def cases_f():
    E_ = lambda v: sol(v, "expression")  # noqa: E731
    out = []
    for f, c in [("cbrt(x)", "1/(3*cbrt(x)**2)"), ("cbrt(x)", "1/(3*cbrt(x**2))"), ("cbrt(x)", "cbrt(x)/(3*x)"),
                 ("cbrt(2*x + 1)", "2/(3*cbrt((2*x + 1)**2))"), ("cbrt(x)**4", "4*cbrt(x)/3"),
                 ("root(x, 3)", "1/(3*root(x, 3)**2)"), ("cbrt(x)**2", "2/(3*cbrt(x))")]:
        out.append((f"G2RK-13 ({f})' = {c}", der(f), E_(c), OK, None))
    out += [("G2RK-13 (cbrt x)' = 1/(3 cbrt x) wrong", der("cbrt(x)"), E_("1/(3*cbrt(x))"), NO, None),
            ("G2RK-13 (x cbrt x)' = cbrt x wrong", der("x*cbrt(x)"), E_("cbrt(x)"), NO, None)]
    for f, c in [("cbrt(x)", "1/(3*x**(2/3))"), ("cbrt(x)", "x**(-2/3)/3"), ("cbrt(x**2)", "2/(3*x**(1/3))"),
                 ("x*cbrt(x)", "4*x**(1/3)/3")]:
        out.append((f"G2RK-14 [x>0] ({f})' = {c}", der(f, vars_=[XP]), E_(c), OK, None))
    out += [("G2RK-14 [x>0] (cbrt x)' = 1/(3 x^(1/3)) wrong", der("cbrt(x)", vars_=[XP]), E_("1/(3*x**(1/3))"), NO, None),
            ("G2RK-14 control [R] (cbrt x)' = 1/(3 x^(2/3))", der("cbrt(x)"), E_("1/(3*x**(2/3))"), UNK, None)]
    for f, w, iv, c, v in [("x**(1/3)*(1 - x)", "max", "[0, 1]", "3/(4*4**(1/3))", OK), ("x**(2/3)", "max", "[1, 8]", "4", OK),
                           ("x**(1/3) - x/3", "max", "[0, 8]", "2/3", OK), ("x**(1/3) - x/3", "min", "[0, 8]", "-2/3", OK),
                           ("x**(1/3) - x/3", "argmax", "[0, 8]", "1", OK), ("x**(2/3)*(5 - x)", "max", "[0, 5]", "3*cbrt(4)", OK),
                           ("x**(1/3)*(1 - x)", "max", "[0, 1]", "1/2", NO), ("x**pi", "max", "[1, 2]", "2**pi", OK),
                           ("x**pi", "min", "[1, 2]", "1", OK), ("x**sqrt(2)", "max", "[1, 2]", "2**sqrt(2)", OK),
                           ("x**pi", "max", "[1, 2]", "4", NO), ("x**x", "max", "[1, 2]", "4", OK),
                           ("x*exp(-x)", "max", "[0, 3]", "exp(-1)", OK), ("sin(x) + cos(x)", "max", "[0, pi/2]", "sqrt(2)", OK)]:
        out.append((f"G2RK-15 {w} {f} on {iv} = {c}", ext(f, w, iv), sol(c), v, None))
    out += [("RK-1 (x^pi)' = pi x^(pi-1)", der("x**pi"), E_("pi*x**(pi - 1)"), OK, None),
            ("RK-1 (x^pi)' = x^(pi-1) wrong", der("x**pi"), E_("x**(pi - 1)"), NO, None),
            ("RK-1 (x^sqrt2)'", der("x**sqrt(2)"), E_("sqrt(2)*x**(sqrt(2) - 1)"), OK, None),
            ("RK-1 ((2x+1)^pi)'", der("(2*x + 1)**pi"), E_("2*pi*(2*x + 1)**(pi - 1)"), OK, None),
            ("RK-1 int x^pi", anti("x**pi"), E_("x**(pi + 1)/(pi + 1)"), OK, None),
            ("RK-1 int x^sqrt2", anti("x**sqrt(2)"), E_("x**(sqrt(2) + 1)/(sqrt(2) + 1)"), OK, None),
            ("RK-1 control (x^x)' stays undecided (decision: finitely many ends)", der("x**x"), E_("x**x*(log(x) + 1)"), UNK, None),
            ("RK-1 control ((x^2)^pi)' (0 interior)", der("(x**2)**pi"), E_("2*pi*x*(x**2)**(pi - 1)"), UNK, None),
            ("RK-2 (x^n)'' n>=2", derk("x**n", 2, [X, NP2]), E_("n*(n - 1)*x**(n - 2)"), OK, None),
            ("RK-2 (x^n)''' n>=3", derk("x**n", 3, [X, NP3]), E_("n*(n - 1)*(n - 2)*x**(n - 3)"), OK, None),
            ("RK-2 ((x+1)^n)'' n>=2", derk("(x + 1)**n", 2, [X, NP2]), E_("n*(n - 1)*(x + 1)**(n - 2)"), OK, None),
            ("RK-2 (x^n)'' wrong", derk("x**n", 2, [X, NP2]), E_("n**2*x**(n - 2)"), NO, None),
            ("RK-2 control n in Z+ only", derk("x**n", 2, [X, NP]), E_("n*(n - 1)*x**(n - 2)"), UNK, None)]
    for q, c, v in [(der("log(sin(x))", "pi/4"), "1", OK), (der("sqrt(sin(x))", "pi/6"), "sqrt(6)/4", OK),
                    (der("sqrt(cos(x))", "0"), "0", OK), (der("log(cos(x))", "pi/3"), "-sqrt(3)", OK),
                    (der("log(tan(x))", "pi/4"), "2", OK), (der("sqrt(1 + sin(x))", "0"), "1/2", OK),
                    (der("log(sin(x))", "pi/4"), "0", NO), (lim("log(cos(x))/x**2", "0"), "-1/2", OK),
                    (lim("log(cos(x))/x**2", "0"), "1/2", NO), (lim("log(1 + sin(x))/x", "0"), "1", OK)]:
        out.append((f"RK-9 {q['task']['kind']} {q['task']['params']} = {c}", q, sol(c), v, None))
    out.append(("RK-9 tangent sqrt(sin x) at pi/2: y = 1", tan("sqrt(sin(x))", "pi/2"), sol("y = 1", "equation"), OK, None))
    for kind, text, c, v in [("domain_of", "1/(x - 2)", "R - {2}", OK), ("domain_of", "1/(x - 2)", r"\mathbb{R} - \{2\}", OK),
                             ("domain_of", "1/(x - 2)", r"\mathbb{R} \setminus \{2\}", OK), ("domain_of", "1/(x - 2)", "ℝ∖{2}", OK),
                             ("domain_of", "1/(x - 2)", r"(-\infty, 2) \cup (2, \infty)", OK),
                             ("domain_of", "log(x**2 - 1)", r"(-\infty, -1) \cup (1, \infty)", OK),
                             ("domain_of", "1/(x - 2)", "R - {3}", NO), ("domain_of", "1/(x - 2)", "ℝ - {2}", OK),
                             ("solve_inequality", "x**2 - 5*x + 6 > 0", r"(-\infty, 2) \cup (3, \infty)", OK),
                             ("solve_inequality", "x**2 - 5*x + 6 > 0", "R - [2, 3]", OK),
                             ("solve_inequality", "x**2 - 5*x + 6 > 0", r"(-\infty, 2) \cup (4, \infty)", NO),
                             ("solve_inequality", "x**2 - 5*x + 6 > 0", "(-oo, 2) U (3, oo)", OK)]:
        params = {"expr": text, "var": "x"} if kind == "domain_of" else {"inequality": text, "var": "x"}
        shape = "set" if kind == "domain_of" else "interval"
        out.append((f"RK-4 {kind} {text}: {c}", ir(kind, params, (), None, shape), sol(c, shape), v, None))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "K": cases_k}


def main(out_path=None, groups="ABCDEFK"):
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
    grp = args[1] if len(args) > 1 else "ABCDEFK"
    sys.exit(1 if main(out, grp) else 0)
