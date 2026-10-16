"""Part d4j ("the rest") of the fourth audit's fixes (15 Oct 2026, plan A+, DECISIONS §89): the findings no branch had
fixed (`denetim/2026-10-01/d4/a_arti/kararlar_kalan.txt`; the d4f round 2 findings in
`denetim/2026-10-01/d4/saldiri/d4f2/bulgular.json`, their decisions in `kararlar_tur3.txt`).

  Realistic (exact fixes):
    A  D4F2B-RK-1      a bare name of a list or dict parameter (points P, S; outcomes S, K; sqrt, det, Sum) is a label
    B  D4F2B-RK-2      a sequence's tail: a condition whose violation set is bounded (2**n != 1000, n! != 100, ...)
    C  D4F2B-ONCEKI-1  an option is read as a claim of the answer's shape ('x > -2' a set); '1,5' is not guessed
  Artificial (narrow fail-closed rules):
    D  D4F2A-YO-1      a 0**0 entry: det/trace of the matrix is not computed as written
    E  D4F2A-YO-2      an exponent identically 0 (x - x) on a base 0 or ±oo is 0**0 / oo**0
    F  D4F2A-YO-3      over ℂ the operations with no value and the conventions still count
    G  D4F2A-YO-4      the constraints' written definedness (closed on the merged branch: kept as a guard)
    H  D4F2A-YO-5      a closed infinite argument (sin(oo), exp(-oo), atan(oo), 2**(-oo)) is no value; limits unchanged
    I  D4F2A-RK-1      a bound that is no linear one (n**2, sqrt(n)): UNKNOWN off the integers, never INCORRECT
    J  D4F2B-YO-1/RK-3 Σ with a \\log_b a bound (ln 8/ln 2, log_3 3^4): read as written, the integer proved exactly
    L  D4B9-E2-R1      atan2/arg: the branch cut is a kink of the derivative
    M  GAP-NE          Eq/Ne with a Float operand: a tolerant equality decides nothing (relation_holds_at)
    N  GAP-LFLOOR      a claim that applies the target's own integer operation (\\lfloor 17/5 \\rfloor) is no value
    P  CAP-K1          the fusion: a meaning abstention is not turned CORRECT by a later layer's pass alone
    Q  (addendum)      mc.consistency: a chosen option not shown to be the claim gives no CORRECT; a wrong one refutes
    K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/d4j/sonda.py [out.json] [groups]

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
import time
from fractions import Fraction
from itertools import combinations, permutations, product

OK = {"CORRECT"}
NO = {"INCORRECT"}
UNK = {"UNKNOWN"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false acceptance
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
VER = {"verified"}
REF = {"refuted"}
NEITHER = {"unknown", "skipped", None}

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
K = {"name": "k", "domain": "integer"}
NR = {"name": "n", "domain": "real"}
NI = {"name": "n", "domain": "integer"}
NP = {"name": "n", "domain": "positive_integer"}


def ir(kind, params, givens=(), vars_=None, shape="scalar", **extra):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    d.update(extra)
    return d


def sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": "compute", "claim": c, "from": [], "text": ""}
                                            for i, c in enumerate(steps)]}


def ev(expr, vars_=None, givens=(), **extra):
    return ir("evaluate", {"expr": expr}, givens, vars_, **extra)


def step(claim, vars_=None):
    """A step next to a right answer (x = 1): only the step's status is asked."""
    return ev("x", vars_, ("x = 1",)), sol("1", steps=[claim])


# A: labels ------------------------------------------------------------------------------------------------------
def _space(st, el, k):
    return {"sequence": lambda: list(product(el, repeat=k)), "permutation": lambda: list(permutations(el, k)),
            "combination": lambda: list(combinations(el, k))}[st]()


def _prob(st, el, k, event, wrong=False):
    sp_ = _space(st, el, k)
    p = Fraction(sum(1 for t in sp_ if eval(event, {"t": t})), len(sp_))
    q = ir("probability", {"space": {"structure": st, "elements": el, "k": k}, "event": event}, vars_=[])
    return q, sol(str(p + (1 if wrong else 0)))


def _geo(pts, claim="10"):
    a, b, c = pts
    return ir("synthetic_geometry", {"points": list(pts), "constraints": [f"dist({a},{b}) = 6", f"dist({b},{c}) = 8",
                                                                         f"angle({a},{b},{c}) = 90"],
                                     "target": f"dist({a},{c})"}, vars_=[]), sol(claim)


def cases_a():
    out = [("geo PQR", *_geo(("P", "Q", "R")), OK, None), ("geo ABS", *_geo(("A", "B", "S")), OK, None),
           ("geo PQS", *_geo(("P", "Q", "S")), OK, None), ("geo PQR wrong 11", *_geo(("P", "Q", "R"), "11"), NO, None),
           ("geo ctl KMV", *_geo(("K", "M", "V")), OK, None)]
    for lab, args, exp in [("SKMBY 2/5", ("combination", ["S", "K", "M", "B", "Y"], 2, "'S' in t"), OK),
                           ("SK^3 7/8", ("sequence", ["S", "K"], 3, "'S' in t"), OK),
                           ("PQ^2 1/2", ("sequence", ["P", "Q"], 2, "t[0] == t[1]"), OK),
                           ("PRST 1/4", ("permutation", ["P", "R", "S", "T"], 4, "t[0] == 'S'"), OK),
                           ("names 1/2", ("combination", ["sqrt", "det", "Sum", "gcd"], 2, "'det' in t"), OK),
                           ("C, Matrix 2/3", ("combination", ["C", "Matrix", "E2"], 2, "'C' in t"), OK)]:
        out.append((f"prob {lab}", *_prob(*args), exp, None))
    out.append(("prob SKMBY wrong", *_prob("combination", ["S", "K", "M", "B", "Y"], 2, "'S' in t", wrong=True), NO, None))
    q = ir("count_structures", {"space": {"structure": "permutation", "elements": ["P", "R", "S", "T", "U"], "k": 3},
                                "predicate": "True"}, vars_=[], shape="count")
    out.append(("count PRSTU 60", q, sol(60, kind="count"), OK, None))
    out.append(("count PRSTU wrong 61", q, sol(61, kind="count"), NO, None))
    # a name bound to a value is no label: zoo among the outcomes still has no value (review of d4f, YO-6)
    out.append(("ctl zoo among the outcomes", *_prob("combination", ["S", "zoo", "K"], 2, "'S' in t"), UNK, None))
    return out


# B: tails -------------------------------------------------------------------------------------------------------
def lim(expr, val, var="n", dom="positive_integer", to="oo"):
    return ir("limit", {"expr": expr, "var": var, "to": to}, (), [{"name": var, "domain": dom}]), sol(val)


def cases_b():
    ok = [("1/(2**n - 1000)", "0"), ("1/(3**n - 7)", "0"), ("1/(factorial(n) - 100)", "0"), ("n**2/(n**2 - 2**n)", "0"),
          ("1/(2**n - n**2)", "0"), ("1/(n - 10*log(n))", "0"), ("2**n/(2**n - 1000)", "1"), ("1/floor(n/2)", "0"),
          ("n/floor(n/2)", "2"), ("log(n)/(n - log(n))", "0"), ("1/(2**n - 64)", "0"), ("1/(factorial(n) - 6)", "0"),
          ("n**2/(n**2 - n*log(n))", "1"), ("(3**n + 2**n)/(3**n - 5)", "1"), ("1/(2**n - 2)", "0"),
          ("n/(2**n - 5)", "0"), ("1/(n - 5)", "0")]
    out = [(f"lim {e} = {v}", *lim(e, v), OK, None) for e, v in ok]
    out.append(("lim x/(2**x - 1000) = 0 (var x)", *lim("x/(2**x - 1000)", "0", var="x"), OK, None))
    out += [("lim 1/(2**n - 1000) = 1 wrong", *lim("1/(2**n - 1000)", "1"), NO, None),
            ("lim log(n)/(n - log(n)) = 1 wrong", *lim("log(n)/(n - log(n))", "1"), NO, None),
            ("lim n/floor(n/2) = 1 wrong", *lim("n/floor(n/2)", "1"), NO, None)]
    # conditions that fail on infinitely many integers: no tail, never CORRECT
    out += [("lim cos(pi n/2)/cos(pi n/2) = 1", *lim("cos(pi*n/2)/cos(pi*n/2)", "1"), UNK, None),
            ("lim 1/(1 - (-1)**n) = 0", *lim("1/(1 - (-1)**n)", "0"), UNK, None),
            ("lim (1 - (-1)**n)/(1 - (-1)**n) = 1", *lim("(1 - (-1)**n)/(1 - (-1)**n)", "1"), UNK, None),
            ("lim n/tan(pi*n/4) = 0", *lim("1/tan(pi*n/4)", "0"), UNK, None)]
    return out


# C: options -----------------------------------------------------------------------------------------------------
def ineq(given, opts, payload, opt, shape="interval", kind="interval"):
    return (ir("solve_inequality", {"var": "x"}, [given], [{"name": "x"}], shape, options=opts),
            sol(payload, kind, option=opt))


def mc_ev(expr, opts, payload, opt):
    return ev(expr, [], options=opts), sol(payload, option=opt)


def cases_c():
    return [
        ("x > -2 option", *ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "(-2, oo)", "A"), OK, None),
        ("x>-2 option", *ineq("x**3 > -8", {"A": "x>-2", "B": "(100, 200)"}, "(-2, oo)", "A"), OK, None),
        ("x ≥ 1 option", *ineq("2*x - 2 >= 0", {"A": "x ≥ 1", "B": "(100, 200)"}, "[1, oo)", "A"), OK, None),
        ("x >= 1 option", *ineq("2*x - 2 >= 0", {"A": "x >= 1", "B": "(100, 200)"}, "[1, oo)", "A"), OK, None),
        ("x < 3 option", *ineq("x - 3 < 0", {"A": "x < 3", "B": "(100, 200)"}, "(-oo, 3)", "A"), OK, None),
        (r"x \geq 1 option", *ineq("2*x - 2 >= 0", {"A": r"x \geq 1", "B": "(100, 200)"}, "[1, oo)", "A"), OK, None),
        ("set shape x > -2", *ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "(-2, oo)", "A", shape="set"), OK,
         None),
        ("condition claim x > -2", *ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "x > -2", "A",
                                         kind="condition"), OK, None),
        ("letter only x > -2", *ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "", "A"), OK, None),
        ("letter only x > 2 wrong", *ineq("x**3 > -8", {"A": "x > 2", "B": "x > -2"}, "", "A"), NO, None),
        ("option x > 2 wrong", *ineq("x**3 > -8", {"A": "x > 2", "B": "(100, 200)"}, "(-2, oo)", "A"), NO, None),
        ("option (100, 200) wrong", *ineq("x**3 > -8", {"A": "x > -2", "B": "(100, 200)"}, "(100, 200)", "B"), NO, None),
        ("ctl chain -1 < x < 1", *ineq("x**2 < 1", {"A": "-1 < x < 1", "B": "(100, 200)"}, "(-1, 1)", "A"), OK, None),
        ("ctl interval [1, ∞)", *ineq("2*x - 2 >= 0", {"A": "[1, ∞)", "B": "(100, 200)"}, "[1, oo)", "A"), OK, None),
        ("comma 1,5", *mc_ev("3/2 + 0", {"A": "1,5", "B": "7"}, "3/2", "A"), UNK, None, None, "decimal_comma_ambiguous"),
        ("comma 2,5", *mc_ev("5/2 + 0", {"A": "2,5", "B": "7"}, "5/2", "A"), UNK, None, None, "decimal_comma_ambiguous"),
        ("comma letter only", *mc_ev("3/2 + 0", {"A": "1,5", "B": "7"}, "", "A"), UNK, None, None,
         "decimal_comma_ambiguous"),
        ("ctl dot 1.5", *mc_ev("3/2 + 0", {"A": "1.5", "B": "7"}, "3/2", "A"), OK, None),
        ("ctl set answer, value claim pi/3, option pi/3", ir("trig_solve", {"var": "x", "interval": "[0, pi)"},
                                                             ["tan(x) = sqrt(3)"], [{"name": "x"}], "set",
                                                             options={"A": "pi/6", "B": "pi/3"}),
         sol("pi/3", option="B"), OK, None),
        ("ctl option 3", *mc_ev("1 + 2", {"A": "3", "B": "7"}, "3", "A"), OK, None),
        ("ctl option 7 wrong", *mc_ev("1 + 2", {"A": "7", "B": "3"}, "3", "A"), NO, None),
        ("tuple option (1, 5) for 3: not read as a number", *mc_ev("1 + 2", {"A": "(1, 5)", "B": "3"}, "3", "A"), UNK,
         None, None, "option_unreadable"),
        ("option x**2 < 4 restating the question", *ineq("x**2 < 4", {"A": "x**2 < 4", "B": "(100, 200)"}, "(-2, 2)", "A"),
         UNK, None, None, "option_unreadable"),
        ("option -2 < x (bound first)", *ineq("x**3 > -8", {"A": "-2 < x", "B": "(100, 200)"}, "(-2, oo)", "A"), OK, None),
        ("option x < -1 or x > 1", *ineq("x**2 > 1", {"A": "x < -1 or x > 1", "B": "(100, 200)"},
                                         "Union(Interval.open(-oo, -1), Interval.open(1, oo))", "A"), OK, None),
        ("option y > -2 (another symbol)", ir("solve_inequality", {"var": "x"}, ["x**3 > -8"], [{"name": "x"},
                                                                                              {"name": "y"}],
                                              "interval", options={"A": "y > -2", "B": "(100, 200)"}),
         sol("(-2, oo)", "interval", option="A"), NOTOK, None),
    ]


# D: 0**0 in a matrix --------------------------------------------------------------------------------------------
def cases_d():
    out = [(f"ev {e} = {v}", ev(e), sol(v), UNK, None) for e, v in [
        ("det(Matrix([[0**0, 0], [0, 1]]))", "1"), ("det(Matrix([[0**0]]))", "1"),
        ("trace(Matrix([[0**0, 0], [0, 0]]))", "1"), ("det(Matrix([[0**0, 1], [1, 1]])) + 1", "1"),
        ("trace(Matrix([[(2 - 2)**0, 1], [1, 1]]))", "2"), ("det(Matrix([[1/0**0, 0], [0, 1]]))", "1"),
        (r"\operatorname{tr}\begin{pmatrix} 0^0 & 0 \\ 0 & 1 \end{pmatrix}", "2"),
        (r"\det\begin{pmatrix} 0^0 & 0 \\ 0 & 1 \end{pmatrix}", "1"),
        (r"\begin{vmatrix} 0^0 & 0 \\ 0 & 1 \end{vmatrix}", "1")]]
    out.append(("solve x + trace([[0**0,0],[0,0]]) = 2", ir("solve_equation", {"var": "x", "equation":
                "x + trace(Matrix([[0**0, 0], [0, 0]])) = 2"}, shape="set"), sol("{1}", "set"), UNK, None))
    out.append(("step trace([[0**0,0],[0,0]]) = 1", *step("trace(Matrix([[0**0, 0], [0, 0]])) = 1"), OK, NEITHER))
    out += [("ctl det [[x**0,0],[0,1]] = 1", ev("det(Matrix([[x**0, 0], [0, 1]]))"), sol("1"), OK, None),
            ("ctl trace [[1,0],[0,1]] = 2", ev("trace(Matrix([[1, 0], [0, 1]]))"), sol("2"), OK, None),
            ("ctl det [[2**0,1],[1,2]] = 1", ev("det(Matrix([[2**0, 1], [1, 2]]))"), sol("1"), OK, None),
            ("ctl det [[1/2,1],[1,4]] = 1", ev("det(Matrix([[1/2, 1], [1, 4]]))"), sol("1"), OK, None),
            ("ctl det [[1/2,1],[1,4]] = 2 wrong", ev("det(Matrix([[1/2, 1], [1, 4]]))"), sol("2"), NO, None)]
    return out


# E: an exponent identically 0 -----------------------------------------------------------------------------------
def cases_e():
    out = [(f"ev {e} = 1", ev(e), sol("1"), UNK, None) for e in [
        "oo**(x - x)", "(-oo)**(x - x)", r"\infty^{x - x}", "oo**(floor(x) - floor(x))", "(oo*x)**(x - x)", "(oo*x)**0",
        "0**(x - x)", "0**(x**2 - x**2)", "0**(sin(x)**2 + cos(x)**2 - 1)", "oo**((x + 1)**2 - x**2 - 2*x - 1)"]]
    out.append(("solve x + oo**(x - x) = 2", ir("solve_equation", {"var": "x", "equation": "x + oo**(x - x) = 2"},
                                                shape="set"), sol("{1}", "set"), UNK, None))
    out.append(("step oo**(x - x) = 1", *step("oo**(x - x) = 1"), OK, NEITHER))
    out += [(f"ctl {e} = 1", ev(e), sol("1"), OK, None) for e in
            ["x**(x - x)", "x**0", "2**(x - x)", "2**(sin(x)**2 + cos(x)**2 - 1)"]]
    out.append(("ctl 2**(2x - x) = 2**x", ev("2**(2*x - x)"), sol("2**x"), OK, None))
    return out


# F: ℂ ----------------------------------------------------------------------------------------------------------
def evc(expr):
    return ev(expr, [], domain_of_discourse="complex")


def cases_f():
    out = [(f"C {e} = {v}", evc(e), sol(v), UNK, None) for e, v in [
        ("1/factorial(-1)", "0"), ("2 + 1/factorial(-2)", "2"), (r"\frac{1}{(-1)!}", "0"), (r"\frac{1}{\Gamma(0)}", "0"),
        ("1/binomial(-1, 1/2)", "0"), ("1/(1/0)", "0"), ("0**0", "1"), ("oo**0", "1"), ("Mod(7, -5)", "-3"),
        ("1/factorial(-1) + 1/factorial(-1)", "0"), ("sqrt(-4) + 0**0", "2*I + 1")]]
    out += [("C ctl sqrt(-4) = 2I", evc("sqrt(-4)"), sol("2*I"), OK, None),
            ("C ctl sqrt(-4) = -2I wrong", evc("sqrt(-4)"), sol("-2*I"), NO, None),
            ("C ctl log(-1) = I pi", evc("log(-1)"), sol("I*pi"), OK, None),
            ("C ctl asin(2) - asin(2) + 1 = 1", evc("asin(2) - asin(2) + 1"), sol("1"), OK, None),
            ("C ctl (1 + I)**2 = 2I", evc("(1 + I)**2"), sol("2*I"), OK, None),
            ("C ctl Mod(7, 5) = 2", evc("Mod(7, 5)"), sol("2"), OK, None),
            ("real ctl 1/factorial(-1) = 0", ev("1/factorial(-1)", []), sol("0"), UNK, None)]
    return out


# G: constraints as written (closed on the merged branch: a guard) -----------------------------------------------
def solve3(constraint, claim):
    return ir("solve_equation", {"var": "x", "equation": "x**3 = x"}, (),
              [{"name": "x", "domain": "real", "constraints": [constraint]}], "set"), sol(claim, "set")


def cases_g():
    out = [(f"constraint {c}", ir("solve_equation", {"var": "x", "equation": "x**2 = 1"}, (),
                                  [{"name": "x", "domain": "real", "constraints": [c]}], "set"), sol("{1}", "set"), UNK,
            None) for c in ["x > sqrt(-1)**2", "x > log(-1)*0", "x > asin(2)*0"]]
    out.append(("limit given x > log(-1)*0", ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"},
                                                ("x > log(-1)*0",)), sol("1"), UNK, None))
    out += [("x/x > 0: {-1, 1}", *solve3("x/x > 0", "{-1, 1}"), OK, None),
            ("x/x > 0: {-1, 0, 1} wrong", *solve3("x/x > 0", "{-1, 0, 1}"), NO, None),
            ("sqrt(x)**2 >= -1: {0, 1}", *solve3("sqrt(x)**2 >= -1", "{0, 1}"), OK, None),
            ("sqrt(x)**2 >= -1: {-1, 0, 1} wrong", *solve3("sqrt(x)**2 >= -1", "{-1, 0, 1}"), NO, None),
            ("log x - log x >= 0: {1}", *solve3("log(x) - log(x) >= 0", "{1}"), OK, None),
            ("log x - log x >= 0: {-1, 1} wrong", *solve3("log(x) - log(x) >= 0", "{-1, 1}"), NO, None)]
    return out


# H: infinite arguments ------------------------------------------------------------------------------------------
def cases_h():
    out = [(f"ev {e} = {v}", ev(e), sol(v), UNK, None) for e, v in [
        ("0*sin(oo)", "0"), ("0*cos(oo) + 1", "1"), ("x + 0*sin(oo)", "x"), ("0*frac(oo)", "0"), (r"0 \cdot \sin(\infty)", "0"),
        ("2**(-oo)", "0"), ("exp(-oo)", "0"), ("1/2**oo", "0"), ("atan(oo)", "pi/2"), ("tanh(oo)", "1"), ("0*sign(-oo)", "0"),
        ("E**(-oo)", "0"), ("(1/2)**oo", "0"), ("1/oo", "0")]]
    out.append(("solve x + 0*sin(oo) = 2", ir("solve_equation", {"var": "x", "equation": "x + 0*sin(oo) = 2"},
                                              shape="set"), sol("{2}", "set"), UNK, None))
    out.append(("claim 0*sin(oo) for 0", ev("0"), sol("0*sin(oo)"), UNK, None))
    out.append(("step 0*sin(oo) = 0", *step("0*sin(oo) = 0"), OK, NEITHER))
    out.append(("derivative x**2 + 0*sin(oo) at 1", ir("derivative", {"f": "x**2 + 0*sin(oo)", "var": "x", "at": "1"}),
                sol("2"), UNK, None))
    # limits are not touched
    out += [("lim exp(-x) at oo = 0", ir("limit", {"expr": "exp(-x)", "var": "x", "to": "oo"}), sol("0"), OK, None),
            ("lim atan(x) at oo = pi/2", ir("limit", {"expr": "atan(x)", "var": "x", "to": "oo"}), sol("pi/2"), OK, None),
            ("lim sin(x)/x at oo = 0", ir("limit", {"expr": "sin(x)/x", "var": "x", "to": "oo"}), sol("0"), OK, None),
            ("lim exp(-x) at oo = 1 wrong", ir("limit", {"expr": "exp(-x)", "var": "x", "to": "oo"}), sol("1"), NO, None),
            ("series (1/2)**k = 2", ir("series_sum", {"var": "k", "lo": "0", "hi": "oo", "term": "(1/2)**k"}, (), [K]),
             sol("2"), OK, None),
            ("ctl exp(0) + atan(1)", ev("exp(0) + atan(1)"), sol("1 + pi/4"), OK, None)]
    return out


# I: a bound that is no linear one -------------------------------------------------------------------------------
def cases_i():
    return [
        ("n real: 3n^2+3+sin(pi n^2)", ev("Sum(k, (k, n**2, n**2 + 2))", [NR, K]), sol("3*n**2 + 3 + sin(pi*n**2)"), UNK,
         None),
        ("n real: 3n^2+3", ev("Sum(k, (k, n**2, n**2 + 2))", [NR, K]), sol("3*n**2 + 3"), UNK, None),
        ("n real: 3n^2+4", ev("Sum(k, (k, n**2, n**2 + 2))", [NR, K]), sol("3*n**2 + 4"), NOTOK, None),
        ("n pos int: 3sqrt(n)+3+sin", ev("Sum(k, (k, sqrt(n), sqrt(n) + 2))", [NP, K]),
         sol("3*sqrt(n) + 3 + sin(pi*sqrt(n))"), UNK, None),
        ("n int: n^2 bound 3n^2+3", ev("Sum(k, (k, n**2, n**2 + 2))", [NI, K]), sol("3*n**2 + 3"), OK, None),
        ("n int: n^2 bound 3n^2+4 wrong", ev("Sum(k, (k, n**2, n**2 + 2))", [NI, K]), sol("3*n**2 + 4"), NO, None),
        ("n pos int: n(n+1)/2 bound", ev("Sum(k, (k, 1, n*(n + 1)/2))", [NP, K]), sol("n*(n + 1)*(n**2 + n + 2)/8"), OK,
         None),
        ("n pos int: n(n+1)/2 bound wrong", ev("Sum(k, (k, 1, n*(n + 1)/2))", [NP, K]),
         sol("n*(n + 1)*(n**2 + n + 2)/8 + 1"), NO, None),
        ("n pos int: n/2 bound", ev("Sum(k, (k, 1, n/2))", [NP, K]), sol("n*(n + 2)/8"), UNK, None),
        ("ctl n real linear: 3n+3+sin", ev("Sum(k, (k, n, n + 2))", [NR, K]), sol("3*n + 3 + sin(pi*n)"), UNK, None),
        ("ctl n real linear: 3n+4", ev("Sum(k, (k, n, n + 2))", [NR, K]), sol("3*n + 4"), NO, None),
    ]


# J: log bounds --------------------------------------------------------------------------------------------------
def cases_j():
    out = []
    for b, m in [(r"\log_{3} 27", 3), (r"\log_{3} 9", 2), (r"\log_{5} 125", 3), (r"\ln e^{3}", 3),
                 (r"\frac{\ln 8}{\ln 2}", 3), (r"\log_{3} 3^{4}", 4), (r"\log_{9} 81", 2), (r"\log_{3} 81 - 1", 3),
                 (r"\log_{2} 6 - \log_{2} 3 + 2", 3), (r"\log_{2} 8", 3)]:
        v = m * (m + 1) // 2
        e = r"\sum_{k=1}^{%s} k" % b
        out.append((f"{e} = {v}", ev(e), sol(str(v)), OK, None))
        out.append((f"{e} = {v + 1} wrong", ev(e), sol(str(v + 1)), NO, None))
        out.append((f"step {e} = {v}", *step(f"{e} = {v}"), OK, VER))
    kv = [("Sum(k**2, (k, 1, 3))", "14", r"\sum_{k=1}^{\log_3 27} k^{2} = 15"),
          ("Sum(k, (k, 1, 3))", "6", r"\sum_{k=1}^{\log_3 27} k = 7"),
          ("Sum(k, (k, 1, 2))", "3", r"\sum_{k=1}^{\log_3 9} k = 4"),
          ("Sum(k, (k, 1, 3))", "6", r"\sum_{k=1}^{\frac{\ln 8}{\ln 2}} k = 7")]
    for e, v, c in kv:
        out.append((f"wrong step {c}", ev(e, [K]), sol(v, steps=[c]), NO, REF))
    out.append(("ctl \\prod_{k=1}^{\\log_3 9} 2 = 4 (parse, before too)", ev(r"\prod_{k=1}^{\log_{3} 9} 2"), sol("4"),
                NOTNO, None))
    return out


# L: atan2 / arg ------------------------------------------------------------------------------------------------
def der(f, at=None, var="x", vars_=None, givens=(), shape="scalar"):
    p = {"f": f, "var": var}
    if at is not None:
        p["at"] = at
    return ir("derivative", p, givens, vars_, shape)


def cases_l():
    return [
        ("d atan2(x, -1) = -1/(x^2+1)", der("atan2(x, -1)", shape="expression"), sol("-1/(x**2 + 1)"), UNK, None),
        ("d atan2(x - 1, -2)", der("atan2(x - 1, -2)", shape="expression"), sol("-2/((x - 1)**2 + 4)"), UNK, None),
        ("d atan2(y, x) wrt y, x = -1", der("atan2(y, x)", var="y", vars_=[X, Y], givens=["x = -1"], shape="expression"),
         sol("-1/(y**2 + 1)"), UNK, None),
        ("d arg(-1 + I x)", der("arg(-1 + I*x)", shape="expression"), sol("-1/(x**2 + 1)"), UNK, None),
        ("d atan2(x, -1) = 1/(x^2+1) wrong", der("atan2(x, -1)", shape="expression"), sol("1/(x**2 + 1)"), NO, None),
        ("d atan2(x, -1) at 0 = -1", der("atan2(x, -1)", "0"), sol("-1"), NOTOK, None),
        ("d atan2(x, -1) at 1 = -1/2", der("atan2(x, -1)", "1"), sol("-1/2"), OK, None),
        ("lim atan2(x, -1) at 0 = pi", ir("limit", {"expr": "atan2(x, -1)", "var": "x", "to": "0"}), sol("pi"), NOTOK,
         None),
        ("max atan2(x, -1) on [-1, 1] = 3pi/4", ir("extremum", {"f": "atan2(x, -1)", "var": "x", "which": "max",
                                                               "interval": "[-1, 1]"}), sol("3*pi/4"), NOTOK, None),
        ("ctl d atan2(x, 1)", der("atan2(x, 1)", shape="expression"), sol("1/(x**2 + 1)"), OK, None),
        ("ctl d atan2(1, x)", der("atan2(1, x)", shape="expression"), sol("-1/(x**2 + 1)"), OK, None),
        ("ctl d atan2(x**2 + 1, x)", der("atan2(x**2 + 1, x)", shape="expression"),
         sol("(x**2 - 1)/(x**4 + 3*x**2 + 1)"), OK, None),
        ("ctl d atan2(x, 1) at 0 = 1", der("atan2(x, 1)", "0"), sol("1"), OK, None),
        ("ctl d atan(x)", der("atan(x)", shape="expression"), sol("1/(x**2 + 1)"), OK, None),
        ("ctl d |x| = sign(x)", der("Abs(x)", shape="expression"), sol("sign(x)"), UNK, None),
    ]


# M: Eq/Ne with a Float operand (relation_holds_at) ---------------------------------------------------------------
def _rha(rel_src, point):
    def run():
        import sympy as sp
        from mathverify.certify.domain import relation_holds_at
        x = sp.Symbol("x", real=True)
        rel = eval(rel_src, {"x": x, "sp": sp, "F": sp.Float, "R": sp.Rational})
        return str(relation_holds_at(rel, x, eval(point, {"sp": sp, "F": sp.Float, "R": sp.Rational})))
    return run


def cases_m():
    return [(f"rha {r} at {p}", _rha(r, p), None, exp, None) for r, p, exp in [
        ("sp.Eq(x, 1)", "F('1.00000000000001')", {"None"}), ("sp.Ne(x, 1)", "F('1.00000000000001')", {"None"}),
        ("sp.Eq(x, R(1, 3))", "F('0.333333333333333')", {"None"}), ("sp.Ne(x, R(1, 3))", "F('0.333333333333333')", {"None"}),
        ("sp.Ge(x, R(1, 3))", "F('0.333333333333333')", {"None"}), ("sp.Lt(x, R(1, 3))", "F('0.333333333333333')", {"None"}),
        ("sp.Eq(x**2, 2)", "F('1.41421356237310')", {"None"}), ("sp.Eq(x, sp.pi)", "F('3.14159265358979')", {"None"}),
        ("sp.Eq(2*x, 1)", "F('0.5')", {"True"}), ("sp.Ne(x, 1)", "F('1.0')", {"False"}), ("sp.Le(x, 1)", "F('1.0')", {"True"}),
        ("sp.Lt(x, 1)", "F('1.0')", {"False"}), ("sp.Ge(x, 0)", "F('0.0')", {"True"}), ("sp.Ne(x, 1)", "F('1.5')", {"True"}),
        ("sp.Eq(x, 1)", "F('1.5')", {"False"}), ("sp.Gt(x, 1)", "F('1.5')", {"True"}), ("sp.Lt(x, 1)", "F('1.5')", {"False"}),
        ("sp.Eq(x, R(1, 3))", "R(1, 3)", {"True"}), ("sp.Ne(x, R(1, 3))", "R(1, 3)", {"False"}),
        ("sp.Ne(x, R(1, 3))", "R(1, 2)", {"True"})]]


# N: the target's own operation in the claim ---------------------------------------------------------------------
def cases_n():
    return [(f"{t}: {c}", ev(t, []), sol(c), exp, None) for t, c, exp in [
        ("floor(17/5)", r"\lfloor\frac{17}{5}\rfloor", UNK), ("floor(17/5)", r"\left\lfloor \frac{17}{5} \right\rfloor", UNK),
        ("floor(17/5)", r"\lfloor\frac{18}{5}\rfloor", UNK), ("ceiling(17/5)", r"\lceil\frac{17}{5}\rceil", UNK),
        ("Mod(17, 5)", "Mod(17, 5) + 0", UNK), ("factorial(5)", "5!", UNK), ("binomial(5, 2)", r"\binom{5}{2}", UNK),
        ("floor(17/5)", "floor(17/5)", UNK), ("floor(17/5)", "3", OK), ("floor(17/5)", "4", NO), ("factorial(5)", "120", OK),
        ("sqrt(8)", "2*sqrt(2)", OK), ("17/5 - 2/5", r"\lfloor\frac{17}{5}\rfloor", NOTNO), ("binomial(6, 3)/2", "10", OK)]
    ] + [("floor(x) + floor(x): 2 floor(x)", ev("floor(x) + floor(x)"), sol("2*floor(x)"), OK, None)]


# P: fusion with a later layer's pass ----------------------------------------------------------------------------
def _with_lean(q, s):
    def run():
        from mathverify.certify.base import result
        from mathverify.verifier import fuse_layers, verify
        fake = result("formal.lean", "pass", 0.995, True, {"stand_in": True}, 0.0, primary=True, flags=["lean_proved"])
        r = verify(q, s)
        return fuse_layers(list(r.layers) + [fake]).verdict
    return run


def cases_p():
    N_ = [{"name": "n", "domain": "integer"}]
    rows = [
        ("count Mod(n, 3) = 0 on 1..9: 3", ir("count_integers", {"var": "n"}, ["Mod(n, 3) = 0", "n >= 1", "n <= 9"], N_,
                                               "count"), sol(3, kind="count"), OK),
        ("a(n) = (n - 5)**2, a(3) = 4", ir("recurrence_term", {"recurrence": "a(n) = (n - 5)**2", "initial": {"1": "1"},
                                                                "index": 3, "name": "a", "var": "n"}, (), []), sol("4"), OK),
        ("a(n) = n - 5, a(3) = -2", ir("recurrence_term", {"recurrence": "a(n) = n - 5", "initial": {"1": "1"}, "index": 3,
                                                           "name": "a", "var": "n"}, (), []), sol("-2"), OK),
        ("reversed range n = -2: 1", ev("Sum(k, (k, 1, n))", [K, NI], ["n = -2"]), sol("1"), UNK),
        ("free parameter: ∫_0^a x dx", ev("integrate(x, (x, 0, a))", [{"name": "a"}, {"name": "x"}]),
         sol("a**2/2", "expression"), UNK),
        ("derivative at the end 0 of x > 0", der("x**2", "0", vars_=[{"name": "x", "domain": "positive_real"}]), sol("0"),
         UNK),
        ("reversed series_sum 3..1", ir("series_sum", {"var": "k", "lo": "3", "hi": "1", "term": "k"}, (), [K]), sol("-2"),
         UNK),
        ("lim factorial(x) at 0", ir("limit", {"expr": "factorial(x)", "var": "x", "to": "0"}, (), [{"name": "x"}]),
         sol("1"), UNK),
        ("lim cos(pi n/2)/cos(pi n/2)", *lim("cos(pi*n/2)/cos(pi*n/2)", "1"), UNK),
        ("parametric limit a x/x", ir("limit", {"expr": "a*x/x", "var": "x", "to": "0"}, (), [{"name": "x"},
                                                                                         {"name": "a"}]), sol("a"), UNK),
        ("0**0 = 1", ev("0**0", []), sol("1"), UNK),
    ]
    return [(f"+lean {lab}", _with_lean(q, s), None, exp, None) for lab, q, s, exp in rows]


# Q: the chosen option against the claim (d4j addendum, 16 Oct 2026) ------------------------------------------------
def _mcq(kind, params, vars_, shape, opts, givens=()):
    d = ir(kind, params, givens, vars_, shape)
    if opts is not None:
        d["options"] = opts
    return d


def _mcs(kind, payload, opt, source=None):
    d = sol(payload, kind, option=opt)
    if source:
        d["claimed_answer"]["payload_source"] = source
    return d


def cases_q():
    xx, yy = {"name": "x"}, {"name": "y"}
    trig = _mcq("trig_solve", {"var": "x", "interval": "[0, pi)"}, [xx], "set", {"A": "pi/6", "B": "pi/3", "C": "2*pi/3"},
                ["tan(x) = sqrt(3)"])
    trigk = _mcq("trig_solve", {"var": "x"}, [xx], "set", {"A": "{pi/6 + 2*k*pi}", "B": "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}",
                                                         "C": "{pi/6 + k*pi}"}, ["sin(x) = 1/2"])
    integ = _mcq("antiderivative", {"integrand": "log(x)", "var": "x"}, [xx], "expression",
                 {"A": "x*log(x) - x + C", "B": "x*log(x) + C"})
    tan = _mcq("tangent_line", {"f": "x**2", "var": "x", "at": "1", "dep": "y"}, [xx, yy], "equation",
               {"A": "y = 2*x - 1", "B": "y = 2*x + 1"})
    cir = _mcq("equation_of", {"object": "circle_center_radius", "center": ["2", "-1"], "radius": "3"}, [xx, yy], "equation",
               {"A": "(x - 2)**2 + (y + 1)**2 = 9", "B": "(x + 2)**2 + (y - 1)**2 = 9"})
    ev3 = _mcq("evaluate", {"expr": "1 + 2"}, [], "scalar", {"A": "üç", "B": "4"})
    ev3n = _mcq("evaluate", {"expr": "1 + 2"}, [], "scalar", None)
    cnt = _mcq("count_integers", {"var": "n"}, [NI], "count", {"A": "3", "B": "4"}, ["n >= 1", "n <= 3"])
    ode = _mcq("ode", {"var": "x"}, [xx], "set", {"A": "{3}", "B": "{2}"})
    return [
        ("trig value pi/3, letter of pi/6", trig, _mcs("value", "pi/3", "A"), NO, None),
        ("trig value pi/3, letter of pi/3", trig, _mcs("value", "pi/3", "B"), OK, None),
        ("trig value pi/3, letter of 2pi/3", trig, _mcs("value", "pi/3", "C"), NO, None),
        ("trig set {pi/3}, letter of pi/6", trig, _mcs("set", "{pi/3}", "A"), NO, None),
        ("trig families k, right letter", trigk, _mcs("set", "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "B"), OK, None),
        ("trig families n, right letter (k)", trigk, _mcs("set", "{pi/6 + 2*n*pi, 5*pi/6 + 2*n*pi}", "B"), OK, None),
        ("trig families k, wrong letter", trigk, _mcs("set", "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "A"), NO, None),
        ("antiderivative F, letter of F + C", integ, _mcs("expression", "x*log(x) - x", "A"), OK, None),
        ("antiderivative F + C, letter of F + C", integ, _mcs("expression", "x*log(x) - x + C", "A"), OK, None),
        ("antiderivative F, wrong letter", integ, _mcs("expression", "x*log(x) - x", "B"), NO, None),
        ("antiderivative letter only", integ, _mcs("expression", "", "A"), OK, None),
        ("antiderivative recovered payload, wrong letter", integ, _mcs("expression", "x*log(x) - x", "B", "recovered_text"),
         UNK, None),
        ("antiderivative recovered payload, right letter", integ, _mcs("expression", "x*log(x) - x", "A", "recovered_text"),
         OK, None),
        ("tangent, right letter", tan, _mcs("equation", "y = 2*x - 1", "A"), OK, None),
        ("tangent, other form, right letter", tan, _mcs("equation", "2*x - y = 1", "A"), OK, None),
        ("tangent, wrong letter", tan, _mcs("equation", "y = 2*x - 1", "B"), NO, None),
        ("circle expanded, right letter", cir, _mcs("equation", "x**2 + y**2 - 4*x + 2*y - 4 = 0", "A"), OK, None),
        ("circle, wrong letter", cir, _mcs("equation", "(x - 2)**2 + (y + 1)**2 = 9", "B"), NO, None),
        ("evaluate, unreadable option", ev3, _mcs("value", "3", "A"), UNK, None, None, "option_claim_undecided"),
        ("evaluate, wrong letter", ev3, _mcs("value", "3", "B"), NO, None),
        ("evaluate, a letter and no options", ev3n, _mcs("value", "3", "A"), UNK, None),
        ("evaluate, no letter", ev3n, _mcs("value", "3", None), OK, None),
        ("count, right letter", cnt, _mcs("count", 3, "A"), OK, None),
        ("count, wrong letter", cnt, _mcs("count", 3, "B"), NO, None),
        ("no certificate: value 2 against {3}", ode, _mcs("value", "2", "A"), NO, None),
        ("no certificate: value 2 against {2}", ode, _mcs("value", "2", "B"), UNK, None),
    ]


# K: controls ----------------------------------------------------------------------------------------------------
def cases_k():
    return [
        ("x**2 = 4: {-2, 2}", ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, shape="set"), sol("{-2, 2}", "set"),
         OK, None),
        ("x**2 = 4: {2} wrong", ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, shape="set"), sol("{2}", "set"),
         NO, None),
        ("x**2 < 4: (-2, 2)", ir("solve_inequality", {"var": "x", "inequality": "x**2 < 4"}, shape="interval"),
         sol("(-2, 2)", "interval"), OK, None),
        ("lim sin(x)/x at 0 = 1", ir("limit", {"expr": "sin(x)/x", "var": "x", "to": "0"}), sol("1"), OK, None),
        ("lim (1 + 1/n)**n = E", *lim("(1 + 1/n)**n", "E"), OK, None),
        ("lim n/(n + 1) = 1", *lim("n/(n + 1)", "1"), OK, None),
        ("lim (n + 1)/(2n - 3) = 1/2", *lim("(n + 1)/(2*n - 3)", "1/2"), OK, None),
        ("lim 1/(n - 5) = 0", *lim("1/(n - 5)", "0"), OK, None),
        ("d x**3 = 3x**2", der("x**3", shape="expression"), sol("3*x**2"), OK, None),
        ("Σ_{k=1}^{10} k = 55", ev("Sum(k, (k, 1, 10))", [K]), sol("55"), OK, None),
        ("Σ_{k=1}^{n} k = n(n+1)/2, n pos int", ev("Sum(k, (k, 1, n))", [NP, K]), sol("n*(n + 1)/2"), OK, None),
        ("det [[1, 2], [3, 4]] = -2", ev("det(Matrix([[1, 2], [3, 4]]))"), sol("-2"), OK, None),
        ("2**10 = 1024", ev("2**10"), sol("1024"), OK, None),
        ("geo ABC: 10", *_geo(("A", "B", "C")), OK, None),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "I": cases_i, "J": cases_j, "L": cases_l, "M": cases_m, "N": cases_n, "P": cases_p,
          "Q": cases_q, "K": cases_k}


def main(out_path=None, groups="ABCDEFGHIJLMNPQK"):
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
            absent = case[5] if len(case) > 5 else None          # a flag that must not be raised
            present = case[6] if len(case) > 6 else None         # a flag that must be raised
            t = time.time()
            status, flags, allflags = None, [], set()
            try:
                if callable(q):
                    verdict = q()
                else:
                    r = verify(q, s)
                    verdict = r.verdict
                    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                    steps = layer.evidence.get("steps", []) if layer is not None else []
                    status = steps[-1].get("status") if steps else None
                    allflags = {f for la in r.layers for f in (la.flags or [])} | set(r.flags)
                    flags = sorted(allflags)[:6]
            except Exception as e:  # noqa: BLE001
                verdict = f"EXC {type(e).__name__}: {e}"
            ok = verdict in verdicts and (statuses is None or status in statuses)
            ok = ok and (absent is None or absent not in allflags) and (present is None or present in allflags)
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
    grp = args[1] if len(args) > 1 else "ABCDEFGHIJLMNPQK"
    sys.exit(1 if main(out, grp) else 0)
