"""d4e round 3 attack (lens: unjust rejection, coverage loss, robustness). Run with PYTHONPATH of a copy:
    python sonda_rk.py out.json [group letters]
Each case: (group, label, ir, solution, expected verdict set). Expected sets are the mathematically acceptable
verdicts (NOTNO: a correct answer, never INCORRECT; OK: CORRECT expected; NOTOK: never CORRECT)."""
from __future__ import annotations

import json
import sys
import time

OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}
NOTNO = {"CORRECT", "UNKNOWN"}
UNK = {"UNKNOWN"}

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
T_ = {"name": "t", "domain": "real"}
K_ = {"name": "k", "domain": "integer"}
NP_ = {"name": "n", "domain": "positive_integer"}
AP_ = {"name": "a", "domain": "positive_real"}


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


def der(f, at=None, givens=(), vars_=None, dod=None, order=None):
    p = {"f": f, "var": "x"}
    if at is not None:
        p["at"] = at
    if order is not None:
        p["order"] = order
    return ir("derivative", p, givens, vars_, shape="scalar" if at is not None else "expression", dod=dod)


def ss(term, lo, hi, givens=(), vars_=None):
    return ir("series_sum", {"term": term, "var": "k", "lo": lo, "hi": hi}, givens, vars_ or [K_, NP_],
              shape="scalar")


def ev1(expr, vars_=None, givens=()):
    return ir("evaluate", {"expr": expr}, givens, vars_ or [T_], shape="scalar")


def lim(expr, to, givens=(), vars_=None, dod=None):
    return ir("limit", {"expr": expr, "var": "x", "to": to}, givens, vars_, shape="scalar", dod=dod)


def ext(f, which, interval, givens=(), vars_=None):
    p = {"f": f, "var": "x", "which": which}
    if interval is not None:
        p["interval"] = interval
    return ir("extremum", p, givens, vars_, shape="scalar")


def cases_a():
    """smooth_at reads a power whose base is nonnegative by its form (no written condition) as analytic at the
    base's zero: sqrt(x**2 + x**4) = |x|*sqrt(1 + x**2) has a corner at 0, and the textbook derivative, undefined
    exactly there, is called 'undefined where f has a derivative' (RK-8)."""
    out = []
    for f, c in (("sqrt(x**2 + x**4)", "(x + 2*x**3)/sqrt(x**2 + x**4)"),
                 ("sqrt(x**2 + x**4)", "(2*x**3 + x)/sqrt(x**4 + x**2)"),
                 ("sqrt(x**2 + sin(x)**2)", "(x + sin(x)*cos(x))/sqrt(x**2 + sin(x)**2)"),
                 ("(x**2 + x**4)**(1/3)", "(2*x + 4*x**3)/(3*(x**2 + x**4)**(2/3))"),
                 ("sqrt(sin(x)**2 + sin(x)**4)", "(sin(x)*cos(x) + 2*sin(x)**3*cos(x))/sqrt(sin(x)**2 + sin(x)**4)"),
                 ("sqrt(x**2 + x**2*sin(x)**2)", "(x + x*sin(x)**2 + x**2*sin(x)*cos(x))/sqrt(x**2 + x**2*sin(x)**2)"),
                 ("sqrt((x - 1)**2 + (x - 1)**4)", "((x - 1) + 2*(x - 1)**3)/sqrt((x - 1)**2 + (x - 1)**4)"),
                 ("sqrt(x**2 + x**4) + x**3", "(x + 2*x**3)/sqrt(x**2 + x**4) + 3*x**2")):
        out.append(("A", f"derivative {f}: {c} [textbook, undefined at the corner]", der(f), sol(c, "expression"), NOTNO))
    # controls: the claim wrong off the corner stays refuted; the same with |x| written
    out.append(("A", "ctrl derivative sqrt(x**2 + x**4): (x + 2*x**3)/sqrt(x**2 + x**4) + 1 [wrong]", der("sqrt(x**2 + x**4)"),
                sol("(x + 2*x**3)/sqrt(x**2 + x**4) + 1", "expression"), NO))
    out.append(("A", "ctrl derivative Abs(x)*sqrt(1 + x**2): textbook", der("Abs(x)*sqrt(1 + x**2)"),
                sol("(x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTNO))
    # derivative at the corner itself: no derivative
    out.append(("A", "ctrl derivative sqrt(x**2 + x**4) at 0: DNE", der("sqrt(x**2 + x**4)", "0"),
                {"claimed_answer": {"kind": "dne", "payload": "DNE"}, "steps": []}, NOTNO))
    out.append(("A", "ctrl derivative sqrt(x**2 + x**4) at 0: 0 [wrong]", der("sqrt(x**2 + x**4)", "0"), sol("0"), NOTOK))
    # R2 path: a parameter of declared sign, witness x0 = 0
    out.append(("A", "R2 derivative sqrt(a**2 - x**2) + sqrt(x**2 + x**4), a > 0: textbook", der(
        "sqrt(a**2 - x**2) + sqrt(x**2 + x**4)", None, [], [X, AP_]),
        sol("-x/sqrt(a**2 - x**2) + (x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTNO))
    return out


def cases_b():
    """claim_where_derivative: claims whose condition's zeros are not solved (transcendental) or lie on the
    region's end; textbook answers the base certified."""
    out = []
    for f, c in (("sqrt(x - cos(x))", "(1 + sin(x))/(2*sqrt(x - cos(x)))"),
                 ("sqrt(x + exp(x))", "(1 + exp(x))/(2*sqrt(x + exp(x)))"),
                 ("sqrt(x - sin(x))", "(1 - cos(x))/(2*sqrt(x - sin(x)))"),
                 ("sqrt(1 - cos(x))", "sin(x)/(2*sqrt(1 - cos(x)))"),
                 ("sqrt(sin(x))", "cos(x)/(2*sqrt(sin(x)))"),
                 ("sqrt(x*exp(x) - 1)", "(exp(x) + x*exp(x))/(2*sqrt(x*exp(x) - 1))"),
                 ("sqrt(log(x) + x)", "(1/x + 1)/(2*sqrt(log(x) + x))"),
                 ("sqrt(x**5 - x + 1)", "(5*x**4 - 1)/(2*sqrt(x**5 - x + 1))"),
                 ("sqrt(x**3 - x + 1)", "(3*x**2 - 1)/(2*sqrt(x**3 - x + 1))"),
                 ("acosh(x)", "1/sqrt(x**2 - 1)"),
                 ("asin(x)", "1/sqrt(1 - x**2)"),
                 ("asin(x)", "1/(sqrt(1 - x)*sqrt(1 + x))"),
                 ("log(x - cos(x))", "(1 + sin(x))/(x - cos(x))"),
                 ("x**x", "x**x*(log(x) + 1)"),
                 ("log(log(x))", "1/(x*log(x))"),
                 ("cot(x)", "-1/sin(x)**2"),
                 ("cot(x)", "-(1 + cot(x)**2)"),
                 ("sec(x)", "sec(x)*tan(x)"),
                 ("log(Abs(x))", "1/x"),
                 ("log(x**2)", "2/x"),
                 ("sqrt(x)*log(x)", "log(x)/(2*sqrt(x)) + 1/sqrt(x)"),
                 ("1/(x**2 - 1)", "-2*x/((x - 1)**2*(x + 1)**2)"),
                 ("log((x - 1)/(x + 1))", "2/(x**2 - 1)"),
                 ("sqrt(x**2 - 1)", "x/sqrt(x**2 - 1)"),
                 ("atan(1/x)", "-1/(1 + x**2)"),
                 ("x*sqrt(x)", "3*sqrt(x)/2"),
                 ("exp(sqrt(x))", "exp(sqrt(x))/(2*sqrt(x))"),
                 ("sqrt(tan(x))", "1/(2*cos(x)**2*sqrt(tan(x)))"),
                 ("sqrt(x)/(1 + x)", "(1 - x)/(2*sqrt(x)*(1 + x)**2)"),
                 ("tan(x)/x", "(x/cos(x)**2 - tan(x))/x**2"),
                 ("sin(x)/x", "(x*cos(x) - sin(x))/x**2"),
                 ("log(sin(x))", "cot(x)"),
                 ("log(cos(x))", "-tan(x)")):
        out.append(("B", f"derivative {f}: {c}", der(f), sol(c, "expression"), NOTNO))
    return out


def cases_c():
    """series_sum with a symbolic upper bound: the terms are now read on Range(lo, oo)."""
    out = []
    out.append(("C", "series binomial(n, k), k = 0..n: 2**n", ss("binomial(n, k)", 0, "n"), sol("2**n"), NOTNO))
    out.append(("C", "series k*binomial(n, k), k = 0..n: n*2**(n - 1)", ss("k*binomial(n, k)", 0, "n"),
                sol("n*2**(n - 1)"), NOTNO))
    out.append(("C", "series binomial(n, k)*2**k, k = 0..n: 3**n", ss("binomial(n, k)*2**k", 0, "n"), sol("3**n"), NOTNO))
    out.append(("C", "series 1/(n + k), k = 1..n (n positive integer): harmonic(2n) - harmonic(n)",
                ss("1/(n + k)", 1, "n"), sol("harmonic(2*n) - harmonic(n)"), NOTNO))
    out.append(("C", "series 1/(k*(k + 1)), k = 1..n: n/(n + 1)", ss("1/(k*(k + 1))", 1, "n"), sol("n/(n + 1)"), NOTNO))
    out.append(("C", "series k, k = 1..n: n*(n + 1)/2", ss("k", 1, "n"), sol("n*(n + 1)/2"), NOTNO))
    out.append(("C", "series k/n, k = 1..n (n positive integer): (n + 1)/2", ss("k/n", 1, "n"), sol("(n + 1)/2"), NOTNO))
    out.append(("C", "series 1/(n - k + 1), k = 1..n: harmonic(n)", ss("1/(n - k + 1)", 1, "n"), sol("harmonic(n)"), NOTNO))
    out.append(("C", "series (n - k), k = 0..n: n*(n + 1)/2", ss("n - k", 0, "n"), sol("n*(n + 1)/2"), NOTNO))
    out.append(("C", "series sqrt(n - k), k = n..n: 0", ss("sqrt(n - k)", "n", "n"), sol("0"), NOTNO))
    out.append(("C", "series 1/(2**k), k = 0..n - 1: 2 - 2**(1 - n)", ss("1/2**k", 0, "n - 1"), sol("2 - 2**(1 - n)"), NOTNO))
    out.append(("C", "series log(k), k = 1..n: log(factorial(n))", ss("log(k)", 1, "n"), sol("log(factorial(n))"), NOTNO))
    out.append(("C", "series 1/(k - n - 1), k = 1..n: -harmonic(n)", ss("1/(k - n - 1)", 1, "n"), sol("-harmonic(n)"), NOTNO))
    out.append(("C", "series sqrt(n - k) k = 0..n-1 ... k=0..2 n=2 given", ss("sqrt(n - k)", 0, "n", ["n = 2"]),
                sol("1 + sqrt(2)"), NOTNO))
    out.append(("C", "series binomial(n, k), k = 0..n, n = 3 given: 8", ss("binomial(n, k)", 0, "n", ["n = 3"]), sol("8"), OK))
    out.append(("C", "series binomial(n, k), k = 0..n, 2n = 6 given: 8", ss("binomial(n, k)", 0, "n", ["2*n = 6"]), sol("8"),
                NOTNO))
    return out


def cases_d():
    """Second derivatives with several kinks (budget 3) and many switches: never a wrong verdict, time."""
    out = []
    P4 = "x*(x - 1)*(x - 2)*(x - 3)"
    out.append(("D", f"derivative order 2 |{P4}|: (P'')*P/|P|", der(f"Abs({P4})", order=2),
                sol(f"diff({P4}, x, 2)*({P4})/Abs({P4})".replace("diff(" + P4 + ", x, 2)", "(12*x**2 - 36*x + 22)"),
                    "expression"), NOTNO))
    out.append(("D", f"derivative order 2 |{P4}|: 0 [wrong]", der(f"Abs({P4})", order=2), sol("0", "expression"), NOTOK))
    out.append(("D", "derivative order 2 |x**2 - 1|: 2*(x**2 - 1)/|x**2 - 1|", der("Abs(x**2 - 1)", order=2),
                sol("2*(x**2 - 1)/Abs(x**2 - 1)", "expression"), NOTNO))
    out.append(("D", "derivative |x|+|x-1|+|x-2|+|x-3|+|x-4|: sum of signs as u/|u|",
                der("Abs(x) + Abs(x - 1) + Abs(x - 2) + Abs(x - 3) + Abs(x - 4)"),
                sol("x/Abs(x) + (x - 1)/Abs(x - 1) + (x - 2)/Abs(x - 2) + (x - 3)/Abs(x - 3) + (x - 4)/Abs(x - 4)",
                    "expression"), NOTNO))
    out.append(("D", "derivative sum of 9 |x - j|: u/|u| sum",
                der(" + ".join(f"Abs(x - {j})" for j in range(9))),
                sol(" + ".join(f"(x - {j})/Abs(x - {j})" for j in range(9)), "expression"), NOTNO))
    out.append(("D", "derivative |x**2 - 2| * |x**2 - 3|: textbook",
                der("Abs(x**2 - 2)*Abs(x**2 - 3)"),
                sol("2*x*(x**2 - 2)*Abs(x**2 - 3)/Abs(x**2 - 2) + 2*x*(x**2 - 3)*Abs(x**2 - 2)/Abs(x**2 - 3)", "expression"),
                NOTNO))
    out.append(("D", "derivative Max(x, x**2): Piecewise", der("Max(x, x**2)"),
                sol("Piecewise((2*x, x < 0), (1, x < 1), (2*x, x > 1))", "expression"), NOTOK))
    out.append(("D", "derivative Max(x, x**2): via abs", der("Max(x, x**2)"),
                sol("(1 + 2*x + (x**2 - x)*(2*x - 1)/Abs(x**2 - x))/2", "expression"), NOTNO))
    out.append(("D", "derivative Max(sin(x), cos(x)): via abs", der("Max(sin(x), cos(x))"),
                sol("(cos(x) - sin(x) + (sin(x) - cos(x))*(cos(x) + sin(x))/Abs(sin(x) - cos(x)))/2", "expression"),
                NOTNO))
    out.append(("D", "derivative x*Heaviside(x): Heaviside off 0 [value at 0?]", der("x*Heaviside(x)"),
                sol("(1 + x/Abs(x))/2", "expression"), NOTNO))
    out.append(("D", "derivative Piecewise((x**2, x < 0), (x, True)): (x - |x|)... textbook", der(
        "Piecewise((x**2, x < 0), (x, True))"), sol("Piecewise((2*x, x < 0), (1, x > 0))", "expression"), NOTNO))
    out.append(("D", "derivative Piecewise((x**2, x < 0), (0, True)): 2x for x<0, 0 else (smooth at 0)", der(
        "Piecewise((x**2, x < 0), (0, True))"), sol("Piecewise((2*x, x < 0), (0, True))", "expression"), NOTNO))
    out.append(("D", "derivative Piecewise((x**2, x < 0), (0, True)): x - |x| (=2x for x<0, 0 for x>=0)", der(
        "Piecewise((x**2, x < 0), (0, True))"), sol("x - Abs(x)", "expression"), NOTNO))
    return out


def cases_e():
    """Convergence majorant: convergent integrals the base proved by a limit."""
    out = []
    for I, v in (("Integral(exp(-t)*sin(t), (t, 0, oo))", "1/2"),
                 ("Integral(exp(-t)/(2 + sin(t)), (t, 0, oo))", None),
                 ("Integral(sin(t)/t**2, (t, 1, oo))", None),
                 ("Integral(sin(t)/t, (t, 0, oo))", "pi/2"),
                 ("Integral(cos(t)/(1 + t**2), (t, 0, oo))", "pi/(2*E)"),
                 ("Integral(exp(-t)*cos(t)**2, (t, 0, oo))", "3/5"),
                 ("Integral(exp(-t)*Abs(sin(t)), (t, 0, oo))", None),
                 ("Integral(exp(-t)*floor(t), (t, 0, oo))", "1/(E - 1)"),
                 ("Integral(exp(-t)*Max(sin(t), 0), (t, 0, oo))", None),
                 ("Integral(exp(-t)*log(2 + sin(t)), (t, 0, oo))", None),
                 ("Integral(exp(-t)*atan(sin(t)), (t, 0, oo))", None),
                 ("Integral(sin(t)**2/t**2, (t, 0, oo))", "pi/2"),
                 ("Integral(exp(-t**2)*cos(t), (t, -oo, oo))", "sqrt(pi)*exp(-1/4)"),
                 ("Integral(t*exp(-t)*sin(t), (t, 0, oo))", "1/2"),
                 ("Integral(sin(1/t), (t, 0, 1))", None),
                 ("Integral(log(t)*sin(t)/t**3, (t, 1, oo))", None),
                 ("Integral(1/(t**2 + cos(t)**2), (t, 0, oo))", None),
                 ("Integral(exp(-t)*sign(sin(t)), (t, 0, oo))", None),
                 ("Integral(exp(-t)*sin(t)**3/(1 + cos(t)**2), (t, 0, oo))", None)):
        if v is None:
            continue
        q = ev1(I)
        out.append(("E", f"evaluate {I}: {v}", q, sol(v), NOTNO))
        out.append(("E", f"evaluate {I}: {v} + 1 [wrong]", q, sol(f"{v} + 1"), NOTOK))
    # used in a derivative: d/dx (x**2 + I) = 2x
    for I in ("Integral(exp(-t)/(2 + sin(t)), (t, 0, oo))", "Integral(exp(-t)*Abs(sin(t)), (t, 0, oo))",
              "Integral(sin(t)/t**2, (t, 1, oo))", "Integral(exp(-t)*Max(sin(t), 0), (t, 0, oo))",
              "Integral(exp(-t)*log(2 + sin(t)), (t, 0, oo))", "Integral(exp(-t)*atan(sin(t)), (t, 0, oo))",
              "Integral(log(t)*sin(t)/t**3, (t, 1, oo))", "Integral(1/(t**2 + cos(t)**2), (t, 1, oo))",
              "Integral(exp(-t)*sign(sin(t)), (t, 0, oo))", "Integral(exp(-t)*sin(t)**3/(1 + cos(t)**2), (t, 0, oo))",
              "Integral(sin(1/t), (t, 0, 1))", "Integral(exp(-t)*sin(t)**2/(2 - cos(t)), (t, 0, oo))",
              "Integral(exp(-t)*sqrt(1 + sin(t)), (t, 0, oo))", "Integral(exp(-t)*cos(sin(t)), (t, 0, oo))",
              "Integral(exp(-t)*exp(sin(t)), (t, 0, oo))", "Integral(exp(-t)*(2 + sin(t))**(-1/2), (t, 0, oo))",
              "Integral(exp(-t)*tanh(sin(t)), (t, 0, oo))"):
        q = der(f"x**2 + {I}", None, [], [X, T_])
        out.append(("E", f"derivative x**2 + {I}: 2*x", q, sol("2*x", "expression"), NOTNO))
        out.append(("E", f"derivative x**2 + {I}: 2*x + 1 [wrong]", q, sol("2*x + 1", "expression"), NOTOK))
    return out


def cases_f():
    """Limit with givens / constraints now read for written definedness; extremum fail-closed."""
    out = []
    out.append(("F", "limit sin(a*x)/x at 0, given sqrt(a) = 3: 9", lim("sin(a*x)/x", "0", ["sqrt(a) = 3"],
                [X, {"name": "a", "domain": "real"}]), sol("9"), NOTNO))
    out.append(("F", "limit sin(a*x)/x at 0, given 1/a = 1/2: 2", lim("sin(a*x)/x", "0", ["1/a = 1/2"],
                [X, {"name": "a", "domain": "real"}]), sol("2"), NOTNO))
    out.append(("F", "limit sin(a*x)/x at 0, given log(a) = 0: 1", lim("sin(a*x)/x", "0", ["log(a) = 0"],
                [X, {"name": "a", "domain": "real"}]), sol("1"), NOTNO))
    out.append(("F", "limit (x**2 - 1)/(x - 1) at 1, given y = 1/x: 2", lim("(x**2 - 1)/(x - 1)", "1", ["y = 1/x"],
                [X, {"name": "y", "domain": "real"}]), sol("2"), NOTNO))
    out.append(("F", "limit x*sin(1/x) at 0, given x != 0: 0", lim("x*sin(1/x)", "0", ["x != 0"]), sol("0"), NOTNO))
    out.append(("F", "limit sqrt(x)*log(x) at 0, given x > 0: 0", lim("sqrt(x)*log(x)", "0", ["x > 0"]), sol("0"), NOTNO))
    out.append(("F", "limit (1 + 1/x)**x at oo, given x > 0: E", lim("(1 + 1/x)**x", "oo", ["x > 0"]), sol("E"), NOTNO))
    out.append(("F", "limit (1 + a/x)**x at oo, given a = log(2): 2", lim("(1 + a/x)**x", "oo", ["a = log(2)"],
                [X, {"name": "a", "domain": "real"}]), sol("2"), NOTNO))
    out.append(("F", "limit sin(x)/x at 0, constraint on a: sqrt(a) > 1, a real", lim("sin(x)/x", "0", [],
                [X, {"name": "a", "domain": "real", "constraints": ["sqrt(a) > 1"]}]), sol("1"), NOTNO))
    out.append(("F", "limit sin(x)/x at 0, dod x > 0: 1", lim("sin(x)/x", "0", [], None, "x > 0"), sol("1"), NOTNO))
    out.append(("F", "limit sin(x)/x at 0, given x**2 + 0*sqrt(x) >= 0 -> x>=0: 1", lim("sin(x)/x", "0",
                ["x**2 + 0*sqrt(x) >= 0"]), sol("1"), NOTNO))
    # derivative with a given on a parameter carrying a written condition
    out.append(("F", "derivative a*x**2, given sqrt(a) = 2: 8*x", der("a*x**2", None, ["sqrt(a) = 2"],
                [X, {"name": "a", "domain": "real"}]), sol("8*x", "expression"), NOTNO))
    out.append(("F", "derivative x**2 with constraint log(x) > -10**9 hmm: 2*x", der("x**2", None, [],
                [{"name": "x", "domain": "real", "constraints": ["x > 0"]}]), sol("2*x", "expression"), OK))
    # extremum fail-closed
    for f, w, iv, v in (("log(x - sin(x))", "max", "[1, 2]", "log(2 - sin(2))"),
                        ("sqrt(cos(x))", "max", "[0, 1]", "1"),
                        ("sqrt(x - cos(x))", "max", "[1, 2]", "sqrt(2 - cos(2))"),
                        ("x + sqrt(exp(x) - x)", "min", "[0, 1]", "1"),
                        ("log(x + exp(x))", "max", "[0, 1]", "log(1 + E)"),
                        ("1/(x - cos(x))", "max", "[1, 2]", "1/(1 - cos(1))")):
        out.append(("F", f"extremum {w} {f} on {iv}: {v}", ext(f, w, iv), sol(v), NOTNO))
    for f, at, v in (("log(x - sin(x))", "1", "(1 - cos(1))/(1 - sin(1))"), ("sqrt(x - cos(x))", "1",
                     "(1 + sin(1))/(2*sqrt(1 - cos(1)))"), ("1/(x - cos(x))", "pi", "-1/(pi + 1)**2"),
                     ("x**(1/3)", "8", "1/12"), ("Integral(sin(t)/t, (t, 0, x))", "pi", "0")):
        out.append(("F", f"derivative {f} at {at}: {v}", der(f, at, [], [X, T_]), sol(v), NOTNO))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f}


def main(out_path=None, groups="ABCDEFGHI"):
    from mathverify.verifier import verify
    rows = []
    t0 = time.time()
    for g in groups:
        for grp, label, q, s, verdicts in GROUPS[g]():
            t = time.time()
            reason = None
            try:
                r = verify(q, s)
                verdict = r.verdict
                flags = sorted({f for la in r.layers for f in (la.flags or [])})[:6]
                for la in r.layers:
                    ev = la.evidence or {}
                    if isinstance(ev, dict):
                        cmp_ = ev.get("compare")
                        if isinstance(cmp_, dict):
                            reason = {k: cmp_.get(k) for k in ("method", "reason", "claim_as_written", "kinks",
                                                                "smooth_witness") if k in cmp_}
                        elif ev.get("reason"):
                            reason = reason or ev.get("reason")
            except Exception as e:  # noqa: BLE001
                verdict, flags = f"EXC {type(e).__name__}: {e}", []
            dt = time.time() - t
            ok = verdict in verdicts and dt < 60
            rows.append({"group": grp, "label": label, "verdict": verdict, "ok": ok, "flags": flags,
                         "reason": str(reason)[:300], "s": round(dt, 1)})
            print(f"{'ok ' if ok else 'BAD'} {grp} {verdict:9} {dt:6.1f}s {label} | {str(reason)[:200]} {flags}",
                  flush=True)
    print(f"{len(rows)} cases, {sum(not r['ok'] for r in rows)} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)



AR_ = {"name": "a", "domain": "real"}


def cases_g():
    """A parameter fixed by a given in a form other than `a = c` (2a = 4, sqrt(a) = 2, a**2 = 4 with a > 0) in the
    calculus tasks (task_pins, not solved_pins): the right answer for the fixed value."""
    out = []
    for gv in (["2*a = 4"], ["a - 2 = 0"], ["sqrt(a) = sqrt(2)"], ["a**2 = 4", "a > 0"], ["a = b", "b = 2"]):
        vs = [X, AR_] + ([{"name": "b", "domain": "real"}] if any("b" in g for g in gv) else [])
        out.append(("G", f"derivative a*x**2, given {gv}: 4*x", der("a*x**2", None, gv, vs), sol("4*x", "expression"), NOTNO))
        out.append(("G", f"derivative a*x**2 at 1, given {gv}: 4", der("a*x**2", "1", gv, vs), sol("4"), NOTNO))
        out.append(("G", f"max a*x on [0, 1], given {gv}: 2", ext("a*x", "max", "[0, 1]", gv, vs), sol("2"), NOTNO))
        out.append(("G", f"limit sin(a*x)/x at 0, given {gv}: 2", lim("sin(a*x)/x", "0", gv, vs), sol("2"), NOTNO))
        out.append(("G", f"antiderivative a*x, given {gv}: x**2", ir("antiderivative", {"integrand": "a*x", "var": "x"}, gv,
                    vs, shape="expression"), sol("x**2", "expression"), NOTNO))
    # a real parameter whose zero makes the claim undefined at one point only when it is 0 (f = |x| then)
    out.append(("G", "derivative sqrt(x**2 + a**2), a real: x/sqrt(x**2 + a**2)", der("sqrt(x**2 + a**2)", None, [], [X, AR_]),
                sol("x/sqrt(x**2 + a**2)", "expression"), NOTNO))
    out.append(("G", "derivative sqrt(x**2 + 1): x/sqrt(x**2 + 1)", der("sqrt(x**2 + 1)"),
                sol("x/sqrt(x**2 + 1)", "expression"), OK))
    out.append(("G", "derivative x**n, n positive integer: n*x**(n - 1)", der("x**n", None, [], [X, NP_]),
                sol("n*x**(n - 1)", "expression"), NOTNO))
    out.append(("G", "derivative log(x)/log(a), a > 1 given: 1/(x*log(a))", der("log(x)/log(a)", None, ["a > 1"], [X, AR_]),
                sol("1/(x*log(a))", "expression"), NOTNO))
    out.append(("G", "derivative log(x)/log(a), a positive, a != 1: 1/(x*log(a))", der("log(x)/log(a)", None, ["a != 1"],
                [X, AP_]), sol("1/(x*log(a))", "expression"), NOTNO))
    out.append(("G", "derivative a*x**2, constraint sqrt(a) > 1 on a: 2*a*x", der("a*x**2", None, [],
                [X, {"name": "a", "domain": "real", "constraints": ["sqrt(a) > 1"]}]), sol("2*a*x", "expression"), NOTNO))
    out.append(("G", "derivative x**2 + a, constraint log(a) > 0 on a: 2*x", der("x**2 + a", None, [],
                [X, {"name": "a", "domain": "real", "constraints": ["log(a) > 0"]}]), sol("2*x", "expression"), NOTNO))
    out.append(("G", "derivative a*x**2, a positive: 2*a*x", der("a*x**2", None, [], [X, AP_]), sol("2*a*x", "expression"), OK))
    out.append(("G", "derivative x/a, a positive: 1/a", der("x/a", None, [], [X, AP_]), sol("1/a", "expression"), OK))
    out.append(("G", "derivative exp(a*x), a real: a*exp(a*x)", der("exp(a*x)", None, [], [X, AR_]),
                sol("a*exp(a*x)", "expression"), OK))
    out.append(("G", "derivative sqrt(a - x), a positive: -1/(2*sqrt(a - x))", der("sqrt(a - x)", None, [], [X, AP_]),
                sol("-1/(2*sqrt(a - x))", "expression"), NOTNO))
    out.append(("G", "derivative log(a*x), a positive: 1/x", der("log(a*x)", None, [], [X, AP_]), sol("1/x", "expression"), OK))
    out.append(("G", "derivative log(a*x), a positive: a/(a*x)", der("log(a*x)", None, [], [X, AP_]),
                sol("a/(a*x)", "expression"), NOTNO))
    out.append(("G", "derivative asin(x/a), a positive: 1/sqrt(a**2 - x**2)", der("asin(x/a)", None, [], [X, AP_]),
                sol("1/sqrt(a**2 - x**2)", "expression"), OK))
    out.append(("G", "derivative x*sqrt(a**2 - x**2), a positive: textbook", der("x*sqrt(a**2 - x**2)", None, [], [X, AP_]),
                sol("sqrt(a**2 - x**2) - x**2/sqrt(a**2 - x**2)", "expression"), NOTNO))
    out.append(("G", "derivative x*sqrt(a**2 - x**2), a positive: (a**2 - 2x**2)/sqrt(...)", der("x*sqrt(a**2 - x**2)", None,
                [], [X, AP_]), sol("(a**2 - 2*x**2)/sqrt(a**2 - x**2)", "expression"), NOTNO))
    return out


def cases_i():
    """The kink rule with a power whose base condition was dropped: f = |x| - sqrt(x**2 + x**4) = |x|(1 - sqrt(1 + x**2))
    has a derivative 0 at 0; f = |x| + sqrt(x**2 + x**4) a corner."""
    out = []
    f = "Abs(x) - sqrt(x**2 + x**4)"
    out.append(("I", f"derivative {f} at 0: 0", der(f, "0"), sol("0"), NOTNO))
    out.append(("I", f"derivative {f}: sign(x)*(1 - (1 + 2*x**2)/sqrt(1 + x**2)) [right everywhere, 0 at 0]", der(f),
                sol("sign(x)*(1 - (1 + 2*x**2)/sqrt(1 + x**2))", "expression"), NOTNO))
    out.append(("I", f"derivative {f}: x/Abs(x) - (x + 2*x**3)/sqrt(x**2 + x**4) [undefined at 0 where f' = 0]", der(f),
                sol("x/Abs(x) - (x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTOK))
    g = "Abs(x) + sqrt(x**2 + x**4)"
    out.append(("I", f"derivative {g}: x/Abs(x) + (x + 2*x**3)/sqrt(x**2 + x**4) [textbook]", der(g),
                sol("x/Abs(x) + (x + 2*x**3)/sqrt(x**2 + x**4)", "expression"), NOTNO))
    return out


def cases_h():
    """Robustness: time of kink readings with nested radicals, order 2, many switches; claims with many conditions."""
    out = []
    U2 = "x**4 - 10*x**2 + 1"
    U3 = "x**3 - 3*x + 1"
    out.append(("H", f"derivative order 2 |{U2}|: 12x**2-20 times sign [right]", der(f"Abs({U2})", order=2),
                sol(f"(12*x**2 - 20)*({U2})/Abs({U2})", "expression"), NOTNO))
    out.append(("H", f"derivative order 2 |{U2}| + |{U3}|: 0 [wrong]", der(f"Abs({U2}) + Abs({U3})", order=2),
                sol("0", "expression"), NOTOK))
    out.append(("H", f"derivative |{U2}| * |{U3}|: textbook", der(f"Abs({U2})*Abs({U3})"),
                sol(f"(4*x**3 - 20*x)*({U2})*Abs({U3})/Abs({U2}) + (3*x**2 - 3)*({U3})*Abs({U2})/Abs({U3})", "expression"),
                NOTNO))
    out.append(("H", f"derivative sqrt(Abs({U2})) + sqrt(Abs({U3})): 0 [wrong]", der(f"sqrt(Abs({U2})) + sqrt(Abs({U3}))"),
                sol("0", "expression"), NOTOK))
    out.append(("H", f"derivative Abs({U2})/({U3}): textbook", der(f"Abs({U2})/({U3})"),
                sol(f"((4*x**3 - 20*x)*({U2})/Abs({U2})*({U3}) - Abs({U2})*(3*x**2 - 3))/({U3})**2", "expression"), NOTNO))
    out.append(("H", f"derivative Max({U2}, {U3}): via abs", der(f"Max({U2}, {U3})"),
                sol(f"((4*x**3 - 20*x) + (3*x**2 - 3) + (({U2}) - ({U3}))*((4*x**3 - 20*x) - (3*x**2 - 3))/Abs(({U2}) - ({U3})))/2",
                    "expression"), NOTNO))
    out.append(("H", "derivative Abs(sin(x)) + Abs(x**4 - 10*x**2 + 1): textbook", der(f"Abs(sin(x)) + Abs({U2})"),
                sol(f"cos(x)*sin(x)/Abs(sin(x)) + (4*x**3 - 20*x)*({U2})/Abs({U2})", "expression"), NOTNO))
    out.append(("H", "derivative sin(x)*Abs(sin(x)) + Abs(x**4 - 10*x**2 + 1): textbook",
                der(f"sin(x)*Abs(sin(x)) + Abs({U2})"),
                sol(f"2*cos(x)*Abs(sin(x)) + (4*x**3 - 20*x)*({U2})/Abs({U2})", "expression"), NOTNO))
    out.append(("H", "derivative Abs(x**5 - x + 1): textbook (CRootOf kink)", der("Abs(x**5 - x + 1)"),
                sol("(5*x**4 - 1)*(x**5 - x + 1)/Abs(x**5 - x + 1)", "expression"), NOTNO))
    out.append(("H", "derivative Abs(x**5 - x + 1) order 2: textbook", der("Abs(x**5 - x + 1)", order=2),
                sol("20*x**3*(x**5 - x + 1)/Abs(x**5 - x + 1)", "expression"), NOTNO))
    out.append(("H", "derivative Abs(x - cos(x)): textbook", der("Abs(x - cos(x))"),
                sol("(1 + sin(x))*(x - cos(x))/Abs(x - cos(x))", "expression"), NOTNO))
    out.append(("H", "derivative Abs(x - cos(x)): 1 + sin(x) [wrong]", der("Abs(x - cos(x))"),
                sol("1 + sin(x)", "expression"), NOTOK))
    out.append(("H", "derivative Abs(exp(x) - 2) * Abs(x**4 - 10*x**2 + 1) order 2: 0 [wrong]",
                der(f"Abs(exp(x) - 2)*Abs({U2})", order=2), sol("0", "expression"), NOTOK))
    return out


GROUPS.update({"G": cases_g, "H": cases_h, "I": cases_i})


def cases_j():
    """Parametric textbook derivatives: the claim's condition follows from f's own (var-free) condition or holds for
    every value of the parameter (the zero it allows is a corner of f)."""
    out = []
    for vs, g, lab in (([X, AR_], [], "a real"), ([X, AP_], [], "a positive"), ([X, AR_], ["a != 0"], "given a != 0")):
        out.append(("J", f"derivative sqrt(x**2 + a**2), {lab}: x/sqrt(x**2 + a**2)", der("sqrt(x**2 + a**2)", None, g, vs),
                    sol("x/sqrt(x**2 + a**2)", "expression"), NOTNO))
        out.append(("J", f"derivative atan(x/a), {lab}: a/(a**2 + x**2)", der("atan(x/a)", None, g, vs),
                    sol("a/(a**2 + x**2)", "expression"), NOTNO))
        out.append(("J", f"derivative atan(x/a), {lab}: 1/(a*(1 + x**2/a**2))", der("atan(x/a)", None, g, vs),
                    sol("1/(a*(1 + x**2/a**2))", "expression"), NOTNO))
        out.append(("J", f"derivative sqrt(x)/a, {lab}: 1/(2*a*sqrt(x))", der("sqrt(x)/a", None, g, vs),
                    sol("1/(2*a*sqrt(x))", "expression"), NOTNO))
        out.append(("J", f"derivative log(x)/a, {lab}: 1/(a*x)", der("log(x)/a", None, g, vs),
                    sol("1/(a*x)", "expression"), NOTNO))
        out.append(("J", f"derivative exp(x/a), {lab}: exp(x/a)/a", der("exp(x/a)", None, g, vs),
                    sol("exp(x/a)/a", "expression"), NOTNO))
        out.append(("J", f"derivative log(x**2 + a**2), {lab}: 2*x/(x**2 + a**2)", der("log(x**2 + a**2)", None, g, vs),
                    sol("2*x/(x**2 + a**2)", "expression"), NOTNO))
        out.append(("J", f"derivative x**2/a, {lab}: 2*x/a", der("x**2/a", None, g, vs), sol("2*x/a", "expression"), NOTNO))
    for vs, g, lab in (([X, AP_], ["a != 1"], "a positive, given a != 1"), ([X, AR_], ["a > 1"], "given a > 1"),
                       ([X, AR_], ["a > 0", "a != 1"], "given a > 0, a != 1")):
        out.append(("J", f"derivative log(x)/log(a), {lab}: 1/(x*log(a))", der("log(x)/log(a)", None, g, vs),
                    sol("1/(x*log(a))", "expression"), NOTNO))
        out.append(("J", f"derivative a**x, {lab}: a**x*log(a)", der("a**x", None, g, vs), sol("a**x*log(a)", "expression"),
                    NOTNO))
        out.append(("J", f"derivative log(x)/log(a), {lab}: 1/(x*log(a)) + 1 [wrong]", der("log(x)/log(a)", None, g, vs),
                    sol("1/(x*log(a)) + 1", "expression"), NOTOK))
    out.append(("J", "derivative log(x, 2): 1/(x*log(2))", der("log(x, 2)"), sol("1/(x*log(2))", "expression"), OK))
    out.append(("J", "derivative log(x)/log(2): 1/(x*log(2))", der("log(x)/log(2)"), sol("1/(x*log(2))", "expression"), OK))
    out.append(("J", "derivative log(x)/log(b), b = 2 given: 1/(x*log(2))", der("log(x)/log(b)", None, ["b = 2"],
                [X, {"name": "b", "domain": "real"}]), sol("1/(x*log(b))", "expression"), NOTNO))
    return out


GROUPS["J"] = cases_j


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else None, a[1] if len(a) > 1 else "ABCDEFGHIJ")
