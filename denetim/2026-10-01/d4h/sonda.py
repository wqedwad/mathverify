"""Part d4h of the fourth audit's fixes (7 Oct 2026): the parser (findings F1, H1, D1, D2, I2 of the `ayristirici`
angle, CAP-G1 of the `capraz` angle and G11 of the `gorev` angle, `denetim/2026-10-01/d4/`).

    A  F1      simplify(...) and the other rewrites of a problem's text compute no Limit/Integral/Sum: the form
               stays and its value is the one numbers confirm (checked_forms), held when it has a parameter
    B  H1      a form inside a Matrix (or a list): held and checked like a scalar one; rank/eigmax/eigmin of
               a matrix holding a form are not read
    C  F1'     floor/ceiling/Max/Min/sign/Float of a closed form are not decided by evalf at parse
    D  D1      LaTeX `x \\notin S` is a condition (or not read), never the constant True: function domain, givens
    E  D2      a domain listing sets (`(-oo, -1), (1, oo)`) is a union or an intersection: not read; relations
               alone all hold; a list no number meets is not read
    F  I2      \\frac{d^k}{dn^k} with d and dn declared: a derivative or a product, not read
    G  CAP-G1  a claim that makes the parse compute a gcd/lcm of numbers is no value, whatever its spelling; a LaTeX
               restatement of the target (\\binom{6}{3} for binomial(6, 3)) too
    H  G11     a general solution with two family parameters: one family by the gcd of its coefficients, or not
               read (the verdict does not depend on PYTHONHASHSEED: `tests/test_d4_d4h_ayristirici.py`)
    K  controls whose verdict must not change

Round 2 (8 Oct 2026, the attack on round 1: `denetim/2026-10-01/d4/saldiri/d4h/`; C and E revised: RK-3, RK-2)
    L  YO-1    no closed form's value is decided by evalf while a text is read: //, comparisons, Piecewise, sets,
               at()/subs, LaTeX, steps, givens, function bodies (controls: confirmed integrals decide as before)
    M  YO-2    a Leibniz fraction in any typography with d or dv declared (or a quotient with a differential above
               and below): a derivative or a product, not read
    N  YO-3    a rewrite called by keyword keeps the form too
    P  YO-4    a domain list no number meets on one argument is not read, whatever the number of arguments
    Q  YO-5    a family name the problem uses (a given, a constraint) is no index of the claim
    R  RK-1    `x \in S` with S holding the line restricts no real x
    S  RK-2    a domain list read as union and as intersection: a verdict where both agree
    T  PRE-RK-4  the task's relation written in params is a premise of the steps
    U  PRE-RK-5  a condition on the variable is read as the set it names (notation only); otherwise not read
    V  PRE-RK-6  SymPy's registry S is no value: UNKNOWN, no exception
    W  PRE-RK-7/8  matrix operations stay operations in the structure; a restatement is the same tree, not the value

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/d4h/sonda.py [out.json] [groups]

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
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
NOTVER = {"refuted", "unknown", "skipped", None}

X = {"name": "x", "domain": "real"}
A = {"name": "a", "domain": "real"}
N = {"name": "n", "domain": "positive_integer"}
KI = {"name": "k", "domain": "integer"}
COS = "Integral(Abs(cos(x)), (x, -1, 1))"            # 2 sin 1 = 1.6829...; SymPy's simplify says 0 for 2*COS
LIM = "Limit(n*sin(pi/n), n, oo)"                    # pi; SymPy says 0 with n an integer
LIMA = "Limit(a*n*sin(pi/n), n, oo)"                 # a*pi
SPK = "Integral(1000*exp(-1000000*(x - 1/3)**2), (x, -1, 1))"   # sqrt(pi)*erf(...) = 1.7724...; evalf misses the peak
SPKV = "sqrt(pi)*(erf(2000/3) + erf(4000/3))/2"                   # its exact value (mpmath: 1.77245385090551602729...)
SPKT = "Integral(1000*exp(-1000000*(t - x)**2), (t, -1, 1))"     # SPK at x = 1/3
I3 = "Integral(x, (x, 0, 3))"                                     # 9/2
INV = "Integral(1/(x**2 - a), (x, 0, 1))"            # pi/4 at a = -1


def ir(kind, params, givens=(), vars_=None, shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def ev(expr, vars_=None, givens=(), shape="scalar"):
    return ir("evaluate", {"expr": expr}, givens, vars_, shape)


def sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def cases_a():
    out = []
    for e, wrong, right in [(f"simplify({COS} + 1) - 1", "0", "2*sin(1)"), (f"simplify(2*{COS})/2", "0", "2*sin(1)"),
                            (f"nsimplify(simplify(2*{COS}))", "0", "4*sin(1)"), (f"expand(simplify({COS}))", "0", "2*sin(1)"),
                            (f"simplify(simplify({COS}) + 1)", "1", "1 + 2*sin(1)"), (f"factor(simplify(3*{COS}))", "0", "6*sin(1)"),
                            (f"simplify(Sum({COS}*k, (k, 1, 2)))", "0", "6*sin(1)"),
                            (f"simplify({LIM})", "0", "pi"), (f"simplify(2*{LIM})", "0", "2*pi"),
                            (f"simplify({LIM} + 1) - 1", "0", "pi"), (f"nsimplify(simplify({LIM}))", "0", "pi"),
                            (f"simplify(Limit(n*tan(pi/n), n, oo))", "0", "pi")]:
        out.append((f"F1 evaluate {e}: {wrong} [wrong]", ev(e, [N, X]), sol(wrong), NOTOK, None))
        out.append((f"F1 evaluate {e}: {right} [right]", ev(e, [N, X]), sol(right), NOTNO, None))
    pinned = [(f"simplify({LIMA})", "0", "2*pi", ["a = 2"]), (f"simplify(2*{INV})/2", "0", "pi/4", ["a = -1"]),
              (f"simplify(Integral(tan(x), (x, 0, a)) + 1) - 1", "-log(cos(2))", None, ["a = 2"]),
              (f"simplify({LIMA} + a) - a", "0", "2*pi", ["a = 2"])]
    for e, wrong, right, g in pinned:
        out.append((f"F1 evaluate {e}, {g}: {wrong} [wrong]", ev(e, [N, X, A], g), sol(wrong), NOTOK, None))
        if right:
            out.append((f"F1 evaluate {e}, {g}: {right} [right]", ev(e, [N, X, A], g), sol(right), NOTNO, None))
    out.append(("F1 simplify_expression simplify(2*Integral(1/(x**2 - a), (x, 0, 1)))/2, a free: 0",
                ir("simplify_expression", {"expr": f"simplify(2*{INV})/2"}, (), [X, A], "expression"), sol("0", "expression"),
                NOTOK, None))
    sv = ir("solve_equation", {"equation": f"simplify({LIMA}) = 2*pi", "var": "a"}, (), [N, A], "set")
    out.append(("F1 solve simplify(lim a n sin(pi/n)) = 2 pi for a: {} [wrong]", sv, sol("{}", "set"), NOTOK, None))
    out.append(("F1 solve simplify(lim a n sin(pi/n)) = 2 pi for a: {2} [right]", sv, sol("{2}", "set"), NOTNO, None))
    for st in [f"simplify(2*{COS}) = 0", f"simplify({LIM}) = 0", f"expand(simplify({COS})) = 0"]:
        out.append((f"F1 step compute '{st}' [false]", ev("1", [N, X]), sol("1", "value", [("compute", st)]), ANY, NOTVER))
    return out


def cases_b():
    out = []
    for e, wrong, right, g, vs in [
            (f"Matrix([[{LIMA}]])", "Matrix([[0]])", "Matrix([[2*pi]])", ["a = 2"], [N, A]),
            (f"Matrix([[{LIM}]])", "Matrix([[0]])", "Matrix([[pi]])", [], [N]),
            ("Matrix([[limit(2*n*sin(pi/n), n, oo)]])", "Matrix([[0]])", "Matrix([[2*pi]])", [], [N]),
            (f"Matrix([[simplify(2*{COS})]])", "Matrix([[0]])", "Matrix([[4*sin(1)]])", [], [X]),
            (f"Matrix([[2*{COS}, 1]])", "Matrix([[0, 1]])", "Matrix([[4*sin(1), 1]])", [], [X]),
            (f"Matrix([[a*{COS}]])", "Matrix([[0]])", "Matrix([[2*sin(1)]])", ["a = 1"], [X, A]),
            (r"\begin{pmatrix} \lim_{n \to \infty} a n \sin(\frac{\pi}{n}) \end{pmatrix}", "Matrix([[0]])",
             "Matrix([[2*pi]])", ["a = 2"], [N, A])]:
        out.append((f"H1 evaluate {e}, {g}: {wrong} [wrong]", ev(e, vs, g), sol(wrong), NOTOK, None))
        out.append((f"H1 evaluate {e}, {g}: {right} [right]", ev(e, vs, g), sol(right), NOTNO, None))
    for e, wrong, right in [(f"rank(Matrix([[{LIM}, 1], [{LIM}, 2]]))", "1", "2"),
                            (f"rank(Matrix([[{COS}, 1], [{COS}, 2]]))", "1", "2"),
                            (f"eigmax(Matrix([[{COS}, 0], [0, 1]]))", "1", "2*sin(1)"),
                            ("eigmax(Matrix([[Sum(1/k**2, (k, 1, oo)), 0], [0, 1]]))", "1", "pi**2/6")]:
        out.append((f"H1 evaluate {e}: {wrong} [wrong]", ev(e, [N, X, KI]), sol(wrong), NOTOK, None))
        out.append((f"H1 evaluate {e}: {right} [right]", ev(e, [N, X, KI]), sol(right), NOTNO, None))
    return out


def cases_c():
    out = []
    for e, wrong, right in [(f"floor({SPK})", "0", "1"), (f"ceiling({SPK})", "1", "2"), (f"Max({SPK}, 1)", "1", SPKV),
                            (f"Min({SPK}, 2)", "2", None), (f"frac({SPK})", "0", None),
                            (f"sign({SPK} - 1)", "-1", "1"), (f"floor(a*{SPK.replace('1000*', '1000*')})", "0", "1")]:
        g = ["a = 1"] if "a*" in e else []
        vs = [X, A] if g else [X]
        out.append((f"F1' evaluate {e}: {wrong} [wrong]", ev(e, vs, g), sol(wrong), NOTOK, None))
        if right:
            out.append((f"F1' evaluate {e}: {right} [right]", ev(e, vs, g), sol(right), NOTNO, None))
    # round 2 (RK-3): SPK is not sqrt(pi) (they differ by ~1.27e-193023): sqrt(pi) is a wrong claim
    out.append((f"F1' evaluate Max({SPK}, 1): sqrt(pi) [wrong, RK-3]", ev(f"Max({SPK}, 1)"), sol("sqrt(pi)"), NOTOK, None))
    out.append((f"F1' evaluate Float({SPK}): 0", ev(f"Float({SPK})"), sol("0"), NOTOK, None))
    out.append((f"F1' ctl evaluate floor({COS}): 1", ev(f"floor({COS})"), sol("1"), OK, None))
    out.append((f"F1' ctl evaluate floor({COS}): 0", ev(f"floor({COS})"), sol("0"), NO, None))
    out.append((f"F1' ctl evaluate Max({COS}, 1): 2*sin(1)", ev(f"Max({COS}, 1)"), sol("2*sin(1)"), OK, None))
    return out


def _f(domain, expr="x**2 + 1"):
    return [{"name": "f", "expr": expr, "args": ["x"], "domain": domain}]


def cases_d():
    out = []
    for dom in [r"$x \notin [0, 3]$", r"x \notin [0, 3]", r"$x \notin (0, 3]$", r"$x \notin \left[0, 3\right]$",
                r"$x \notin \{2\}$", r"$x \notin [1, 3]$", r"\( x \notin [0,3] \)", r"$x \notin \mathbb{Z}$"]:
        fn = _f(dom)
        q = ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", fn)
        right = "{}" if "mathbb" in dom else "{-2}"
        out.append((f"D1 domain {dom}: f(x)=5, {{-2, 2}} [wrong]", q, sol("{-2, 2}", "set"), NOTOK, None))
        out.append((f"D1 domain {dom}: f(x)=5, {right} [right]", q, sol(right, "set"), NOTNO, None))
        e = ev("f(2)", [X])
        e["functions"] = fn
        out.append((f"D1 domain {dom}: evaluate f(2) = 5 [undefined]", e, sol("5"), NOTOK, None))
        c = ir("count_roots", {"expr": "f(x) - 5", "var": "x"}, (), [X], "count", fn)
        out.append((f"D1 domain {dom}: count roots f(x) - 5: 2 [wrong]", c, sol("2", "count"), NOTOK, None))
    for g in [r"$x \notin [0, 3]$", r"x \notin [0, 3]", r"$x \notin \{2\}$"]:
        q = ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [g], [X], "set")
        out.append((f"D1 given {g}: x**2=4, {{-2, 2}} [wrong]", q, sol("{-2, 2}", "set"), NOTOK, None))
        out.append((f"D1 given {g}: x**2=4, {{-2}} [right]", q, sol("{-2}", "set"), NOTNO, None))
        c = ir("count_roots", {"expr": "x**2 - 4", "var": "x"}, [g], [X], "count")
        out.append((f"D1 given {g}: count x**2-4: 2 [wrong]", c, sol("2", "count"), NOTOK, None))
        s = ir("solve_inequality", {"inequality": "x**2 < 16", "var": "x"}, [g], [X], "set")
        out.append((f"D1 given {g}: x**2<16: (-4, 4) [wrong]", s, sol("Interval.open(-4, 4)", "interval"), NOTOK, None))
    for g in [r"$x \in (0, 3)$", r"x \in (0, 3)"]:
        q = ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [g], [X], "set")
        out.append((f"D1 given {g}: x**2=4, {{}} [wrong]", q, sol("{}", "set"), NOTOK, None))
        out.append((f"D1 given {g}: x**2=4, {{-2, 2}} [wrong]", q, sol("{-2, 2}", "set"), NOTOK, None))
        out.append((f"D1 given {g}: x**2=4, {{2}} [right]", q, sol("{2}", "set"), NOTNO, None))
        fq = ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(g))
        out.append((f"D1 domain {g}: f(x)=5, {{-2, 2}} [wrong]", fq, sol("{-2, 2}", "set"), NOTOK, None))
        out.append((f"D1 domain {g}: f(x)=5, {{2}} [right]", fq, sol("{2}", "set"), NOTNO, None))
    return out


def cases_e():
    """D2, revised in round 2 (RK-2): a list of a set and another condition on the same argument is read as the union
    and as the intersection; a verdict only where both readings give it (a reading that is not one interval with
    points left out, or the empty set, is not read: UNKNOWN). Lists of relations alone are a conjunction; one no
    number meets is not read."""
    out = []
    # (domain, union answer of f(x) = 5, its count, expected per claim: {}, union answer, domain_of {}, count 0, union count)
    lists = [("(-oo, -1), (1, oo)", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("(0, 3), (4, 5)", "{2}", "1", UNK, UNK, UNK, UNK, UNK),
             ("[-3, -1], [1, 3]", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("(-oo, -1) & (1, oo)", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("(-oo, -1) and (1, oo)", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("(-oo, -1) ∧ (1, oo)", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("x in (-oo, -1), x in (1, oo)", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("x < -1, x > 1", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("x <= -1 ∧ x >= 1", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             ("x<-1 and x>1", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             # union (0, 5), intersection (1, 3): {2} and one root in both readings
             ("(0, 3), (1, 5)", "{2}", "1", NO, OK, NO, NO, OK),
             ("x in (0, 3), x in (1, 5)", "{2}", "1", NO, OK, NO, NO, OK),
             ("(-oo, -1), x > 1", "{-2, 2}", "2", UNK, UNK, UNK, UNK, UNK),
             # union (0, oo), intersection (1, 3)
             ("(0, 3), x > 1", "{2}", "1", NO, OK, NO, NO, OK)]
    for dom, union_answer, union_count, e_empty, e_union, e_dom, e_c0, e_cu in lists:
        fn = _f(dom)
        q = ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", fn)
        out.append((f"D2 domain {dom!r}: f(x)=5, {{}}", q, sol("{}", "set"), e_empty, None))
        out.append((f"D2 domain {dom!r}: f(x)=5, {union_answer} [union reading]", q, sol(union_answer, "set"), e_union, None))
        d = ir("domain_of", {"expr": "f(x)", "var": "x"}, (), [X], "set", fn)
        out.append((f"D2 domain {dom!r}: domain_of f, {{}}", d, sol("{}", "set"), e_dom, None))
        c = ir("count_roots", {"expr": "f(x) - 5", "var": "x"}, (), [X], "count", fn)
        out.append((f"D2 domain {dom!r}: count f(x) - 5: 0", c, sol("0", "count"), e_c0, None))
        out.append((f"D2 domain {dom!r}: count f(x) - 5: {union_count} [union reading]", c, sol(union_count, "count"), e_cu,
                    None))
    for dom, wrong, right in [("x > 0, x < 3", "{-2, 2}", "{2}"), ("x > 0 and x < 3", "{-2, 2}", "{2}"),
                              ("x in [0, 3), x != 1", "{-2, 2}", "{2}"), ("(0, 3), (0, 3)", "{-2, 2}", "{2}"),
                              ("x in (0, 3), x in (0, 3)", "{-2, 2}", "{2}"), ("(0, 3)", "{-2, 2}", "{2}"),
                              ("(-oo,-1) U (1,oo)", "{}", None)]:
        q = ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
        out.append((f"D2 domain {dom!r}: f(x)=5, {wrong} [wrong]", q, sol(wrong, "set"), NOTOK, None))
        if right:
            out.append((f"D2 domain {dom!r}: f(x)=5, {right} [right]", q, sol(right, "set"), OK, None))
    return out


def cases_f():
    out = []
    dvars = [N, X, {"name": "d", "domain": "real"}, {"name": "dn", "domain": "real"}, {"name": "dx", "domain": "real"}]
    for e, wrong in [(r"\frac{d^2}{dn^2}(n \sin(\pi n))", "0"), (r"\frac{d^{2}}{d n^{2}}(n \sin(\pi n))", "0"),
                     (r"\frac{\mathrm{d}^2}{\mathrm{d}n^2}(n \sin(\pi n))", "0"), (r"\dfrac{d^2}{dn^2}(n \sin(\pi n))", "0"),
                     (r"\frac{d^2}{dx^2} x^3", "d**2*x**3/dx**2"), (r"\frac{d}{dx} x^3", "d*x**3/dx"),
                     (r"\frac{d^3}{dx^3}(x^4)", "d**3*x**4/dx**3")]:
        q = ir("simplify_expression", {"expr": e}, (), dvars, "expression")
        out.append((f"I2 d, dn, dx declared: {e}: {wrong} [product reading]", q, sol(wrong, "expression"), UNK, None))
    q = ir("simplify_expression", {"expr": r"\frac{d^2}{dn^2}(n \sin(\pi n))"}, (), dvars, "expression")
    out.append(("I2 d, dn declared: (n sin(pi n))'': 2*pi*(-1)**n [right]", q, sol("2*pi*(-1)**n", "expression"), NOTNO, None))
    out.append(("I2 ctl d not declared: \\frac{d^2}{dn^2}(n \\sin(\\pi n)): 0",
                ir("simplify_expression", {"expr": r"\frac{d^2}{dn^2}(n \sin(\pi n))"}, (), [N, X], "expression"),
                sol("0", "expression"), UNK, None))
    out.append(("I2 ctl \\frac{d}{dx} x^3, d undeclared: 3*x**2",
                ir("simplify_expression", {"expr": r"\frac{d}{dx} x^3"}, (), [X], "expression"), sol("3*x**2", "expression"),
                OK, None))
    out.append(("I2 ctl \\frac{d}{2} with d declared: d/2",
                ir("simplify_expression", {"expr": r"\frac{d}{2} + \frac{d}{2}"}, (), [X, {"name": "d", "domain": "real"}],
                   "expression"), sol("d", "expression"), OK, None))
    return out


def cases_g():
    out = []
    g = ev("gcd(84, 120)", [])
    for c in [r"\mathit{gcd}(120,84)", r"\mathbf{gcd}(120,84)", r"\textit{gcd}(120,84)", r"\textbf{gcd}(120,84)",
              r"\textnormal{gcd}(120,84)", r"\gcd(120, 84)", r"\operatorname{gcd}(120, 84)", "gcd(120, 84)", "igcd(84, 120)",
              "(gcd)(120, 84)", "((gcd))(120, 84)", "(igcd)(120, 84)", "gcd(120, 84) + 0", r"\mathit{gcd}(120,84) + 1 - 1"]:
        out.append((f"G1 evaluate gcd(84, 120): {c}", g, sol(c), UNK, None))
    for c in [r"\mathit{lcm}(6,4)", r"\textbf{lcm}(6,4)", "lcm(6, 4)", "(lcm)(6, 4)", "ilcm(6, 4)"]:
        out.append((f"G1 evaluate lcm(4, 6): {c}", ev("lcm(4, 6)", []), sol(c), UNK, None))
    AP = [{"name": "a", "domain": "positive_integer"}]
    for c in ["gcd(120, 84)*a", "a*gcd(120, 84)", "gcd(120, 84)*a + 0", r"\mathit{gcd}(120, 84) a"]:
        out.append((f"G1 evaluate gcd(84, 120)*a: {c}", ev("gcd(84, 120)*a", AP), sol(c), UNK, None))
    sv = ir("solve_equation", {"var": "x", "equation": "x - gcd(84, 120)*a = 0"}, (), [X] + AP, "set")
    out.append(("G1 solve x - 12a = 0: {gcd(120, 84)*a}", sv, sol("{gcd(120, 84)*a}", "set"), UNK, None))
    s12 = ir("solve_equation", {"var": "x", "equation": "x - 12 = 0"}, (), [X], "set")
    out.append(("G1 solve x - 12 = 0: [\\mathit{gcd}(84,120)]", s12, sol([r"\mathit{gcd}(84,120)"], "set"), UNK, None))
    out.append(("G1 solve x - 12 = 0: {\\textbf{gcd}(84,120)}", s12, sol(r"\{\textbf{gcd}(84,120)\}", "set"), UNK, None))
    for c in [r"\binom{6}{3}", r"{6 \choose 3}", r"\dbinom{6}{3}", "C(6, 3)", "binomial(6, 3)"]:
        out.append((f"G1 evaluate binomial(6, 3): {c} [restatement]", ev("binomial(6, 3)", []), sol(c), UNK, None))
    for c in [r"\lfloor\frac{17}{5}\rfloor", r"\left\lfloor\frac{17}{5}\right\rfloor"]:
        # latex2sympy writes 17/5 as Rational, the text as 17*5**-1: no restatement caught (open, value right)
        out.append((f"G1 evaluate floor(17/5): {c} [restatement, open]", ev("floor(17/5)", []), sol(c), NOTNO, None))
    # controls
    out.append(("G1 ctl evaluate gcd(84, 120): 12", g, sol("12"), OK, None))
    out.append(("G1 ctl evaluate gcd(84, 120): 8", g, sol("8"), NO, None))
    out.append(("G1 ctl evaluate gcd(84, 120): \\mathit{gcd}(24, 16) [wrong value]", g, sol(r"\mathit{gcd}(24,16)"), NOTOK, None))
    out.append(("G1 ctl evaluate gcd(84, 120)*a: 12*a", ev("gcd(84, 120)*a", AP), sol("12*a"), OK, None))
    NI = [{"name": "n", "domain": "positive_integer"}]
    out.append(("G1 ctl evaluate gcd(n, 4), n = 12: 4", ev("gcd(n, 4)", NI, ["n = 12"]), sol("4"), OK, None))
    out.append(("G1 ctl simplify_expression gcd(n, 4): gcd(4, n)",
                ir("simplify_expression", {"expr": "gcd(n, 4)"}, (), NI, "expression"), sol("gcd(4, n)", "expression"),
                NOTNO, None))
    out.append(("G1 ctl evaluate binomial(6, 3): 20", ev("binomial(6, 3)", []), sol("20"), OK, None))
    out.append(("G1 ctl evaluate binomial(6, 3): binomial(6, 6 - 3) (DECISIONS 28)", ev("binomial(6, 3)", []),
                sol("binomial(6, 6 - 3)"), OK, None))
    out.append(("G1 ctl evaluate 2*10: \\binom{6}{3}", ev("2*10", []), sol(r"\binom{6}{3}"), OK, None))
    out.append(("G1 ctl evaluate floor(17/5): 3", ev("floor(17/5)", []), sol("3"), OK, None))
    return out


def cases_h():
    out = []
    t = lambda eq, vs=None: ir("trig_solve", {"var": "x"}, [eq], vs or [X], "set")  # noqa: E731
    for eq, c in [("sin(x) = 0", "{n*pi + k*pi}"), ("sin(x) = 0", "{k*pi + 2*n*pi}"), ("sin(x) = 0", "{n*pi + 2*k*pi}"),
                  ("tan(x) = 0", "{n*pi + k*pi}"), ("cos(x) = 1", "{2*n*pi + 4*k*pi}"), ("cos(x) = 0", "{pi/2 + n*pi + k*pi}"),
                  ("sin(x) = 0", "{(n + k)*pi}")]:
        out.append((f"G11 {eq}: {c} [right]", t(eq), sol(c, "set"), OK, None))
    for eq, c in [("cos(x) = 1", "{n*pi + k*pi}"), ("cos(x) = 1", "{3*n*pi - k*pi}"), ("sin(x) = 0", "{n*pi/2 + k*pi/2}"),
                  ("cos(x) = 0", "{pi/2 + n*pi/2 + k*pi/2}"), ("tan(x) = 1", "{pi/4 + n*pi/2 + k*pi/2}"),
                  ("sin(x) = 0", "{n*pi/3 + 2*k*pi/3}"), ("cos(x) = 1", "{2*n*pi + 3*k*pi}"), ("sin(x) = 0", "{2*n*pi + 2*k*pi}")]:
        out.append((f"G11 {eq}: {c} [wrong]", t(eq), sol(c, "set"), NOTOK, None))
    for eq, c in [("sin(x) = 0", "{n*pi + k}"), ("sin(x) = 0", "{n*k*pi}"), ("sin(x) = 0", "{n**2*pi + k*pi}")]:
        out.append((f"G11 {eq}: {c} [not one family]", t(eq), sol(c, "set"), UNK, None))
    M = {"name": "m", "domain": "integer"}
    out.append(("G11 sin(x) = 0, m declared: {n*pi + 2*m*pi} [right]", t("sin(x) = 0", [X, M]), sol("{n*pi + 2*m*pi}", "set"),
                OK, None))
    out.append(("G11 cos(x) = 1, m declared: {n*pi + m*pi} [wrong]", t("cos(x) = 1", [X, M]), sol("{n*pi + m*pi}", "set"),
                NOTOK, None))
    return out


def cases_k():
    out = []
    out.append(("ctl evaluate Integral(Abs(cos(x)), (x, -1, 1)): 2*sin(1)", ev(COS), sol("2*sin(1)"), OK, None))
    out.append(("ctl evaluate Integral(Abs(cos(x)), (x, -1, 1)): 0", ev(COS), sol("0"), NO, None))
    out.append(("ctl evaluate simplify(x**2/x) at x: x [expression]",
                ir("simplify_expression", {"expr": "simplify((x**2 - 1)/(x - 1))"}, (), [X], "expression"),
                sol("x + 1", "expression"), NOTNO, None))
    out.append(("ctl evaluate Limit(x*sin(1/x), x, oo): 1", ev("Limit(x*sin(1/x), x, oo)"), sol("1"), OK, None))
    out.append(("ctl evaluate simplify(Limit(x*sin(1/x), x, oo)): 1", ev("simplify(Limit(x*sin(1/x), x, oo))"), sol("1"), OK, None))
    out.append(("ctl evaluate Matrix([[Limit(x*sin(1/x), x, oo)]]): [[1]]", ev("Matrix([[Limit(x*sin(1/x), x, oo)]])"),
                sol("Matrix([[1]])"), OK, None))
    out.append(("ctl evaluate Matrix([[Limit(x*sin(1/x), x, oo)]]): [[0]]", ev("Matrix([[Limit(x*sin(1/x), x, oo)]])"),
                sol("Matrix([[0]])"), NO, None))
    # rank returns a Python int: the algebra layer raises on it (before this part too; out of scope)
    out.append(("ctl evaluate rank(Matrix([[1, 2], [2, 4]])): 1", ev("rank(Matrix([[1, 2], [2, 4]]))"), sol("1"), UNK, None))
    out.append(("ctl evaluate eigmax(Matrix([[2, 0], [0, 3]])): 3", ev("eigmax(Matrix([[2, 0], [0, 3]]))"), sol("3"), OK, None))
    out.append(("ctl evaluate floor(7/2): 3", ev("floor(7/2)"), sol("3"), OK, None))
    out.append(("ctl evaluate Max(2, 3): 3", ev("Max(2, 3)"), sol("3"), OK, None))
    out.append(("ctl extremum min Abs(x) - x**2 on [0, 2] (x positive): -2",
                ir("extremum", {"f": "Abs(x) - x**2", "var": "x", "interval": "[0, 2]", "which": "min"}, (),
                   [{"name": "x", "domain": "positive_real"}]), sol("-2"), OK, None))
    out.append(("ctl domain 'x > 0': f(x)=5: {2}",
                ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f("x > 0")), sol("{2}", "set"),
                OK, None))
    out.append(("ctl trig sin(x) = 0: {k*pi}", ir("trig_solve", {"var": "x"}, ["sin(x) = 0"], [X], "set"),
                sol("{k*pi}", "set"), OK, None))
    out.append(("ctl given x != 2: x**2 = 4: {-2}",
                ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [r"$x \neq 2$"], [X], "set"), sol("{-2}", "set"),
                OK, None))
    return out


# ---------------------------------------------------------------------------- round 2 (attack on round 1, 8 Oct 2026)
T_ = {"name": "t", "domain": "real"}
Y_ = {"name": "y", "domain": "real"}
D_ = {"name": "d", "domain": "real"}
DN_ = {"name": "dn", "domain": "real"}
NOTREF = {"verified", "unknown", "skipped", None}     # a true step: never refuted
VER = {"verified"}
REF = {"refuted"}


def _steps(*steps, vs=None):
    return ev("1", vs or [X, T_]), sol("1", steps=list(steps))


def cases_l():
    """YO-1: no closed form's value is decided by evalf while a text is parsed: operators (//, comparisons), sets,
    Piecewise, at()/subs, LaTeX, steps, givens, function bodies."""
    out = []
    for e, wrong, right, vs in [(f"{SPK} // 1", "0", "1", None), (f"-((-{SPK}) // 1)", "1", "2", None),
                                (f"Piecewise((1, {SPK} > 1), (0, {SPK} <= 1))", "0", "1", None),
                                (f"at(floor({SPKT}), x, 1/3)", "0", "1", [X, T_]), (f"at(Max({SPKT}, 1), x, 1/3)", "1", None, [X, T_]),
                                (f"ceiling({SPK})", "1", "2", None), (f"Abs({SPK} - 1) + 1", "2", None, None),
                                (f"sign({SPK} - 1)", "-1", "1", None), (f"floor(2*{SPK}/3)", "0", "1", None),
                                (r"\lfloor \int_{-1}^{1} 1000 e^{-1000000 (x - \frac{1}{3})^{2}} \, dx \rfloor", "0", "1", None),
                                (r"\lceil \int_{-1}^{1} 1000 e^{-1000000 (x - \frac{1}{3})^{2}} \, dx \rceil", "1", "2", None)]:
        out.append((f"YO1 evaluate {e[:60]}: {wrong} [wrong]", ev(e, vs), sol(wrong), NOTOK, None))
        if right:
            out.append((f"YO1 evaluate {e[:60]}: {right} [right]", ev(e, vs), sol(right), NOTNO, None))
    for e, c in [(f"Interval(1, {SPK})", "EmptySet"), (f"Intersection(Interval(1, 2), FiniteSet({SPK}))", "EmptySet"),
                 (f"Union(Interval(0, 1), Interval({SPK}, 3))", "Interval(0, 3)")]:
        out.append((f"YO1 evaluate {e[:60]} [set]: {c} [wrong]", ir("evaluate", {"expr": e}, (), [X], "set"), sol(c, "set"),
                    NOTOK, None))
    cr = ir("count_roots", {"expr": f"x**2 - ({SPK} // 1)", "var": "x"}, (), [X], "count")
    out.append(("YO1 count_roots x**2 - (SPK // 1): 1 [wrong]", cr, sol("1", "count"), NOTOK, None))
    out.append(("YO1 count_roots x**2 - (SPK // 1): 2 [right]", cr, sol("2", "count"), NOTNO, None))
    for k, st in [("compute", f"{SPK} // 1 = 0"), ("eq", f"{SPK} // 1 = 0"), ("compute", f"floor({SPK}) = 0"),
                  ("compute", f"{SPK} < 1"), ("compute", f"Interval(1, {SPK}) = EmptySet"),
                  ("compute", f"at(floor({SPKT}), x, 1/3) = 0")]:
        q, s_ = _steps((k, st))
        out.append((f"YO1 step {k} {st[:60]} [wrong]", q, s_, ANY, NOTVER))
    q, s_ = _steps(("compute", f"{SPK} // 1 = 1"))
    out.append(("YO1 step compute SPK // 1 = 1 [right]", q, s_, ANY, NOTREF))
    out.append(("YO1 given y = SPK // 1: evaluate y: 0 [wrong]", ev("y", [X, Y_], [f"y = {SPK} // 1"]), sol("0"), NOTOK, None))
    out.append(("YO1 solve x = SPK // 1: {0} [wrong]", ir("solve_equation", {"equation": f"x = {SPK} // 1", "var": "x"}, (), [X],
                                                          "set"), sol("{0}", "set"), NOTOK, None))
    out.append(("YO1 solve x < SPK // 1: (-oo, 0) [wrong]",
                ir("solve_inequality", {"inequality": f"x < {SPK} // 1", "var": "x"}, (), [X], "set"),
                sol("Interval.open(-oo, 0)", "interval"), NOTOK, None))
    fq = ir("evaluate", {"expr": "f(1/3)"}, (), [X, T_], "scalar",
            [{"name": "f", "expr": f"floor({SPKT})", "args": ["x"]}])
    out.append(("YO1 function f(x) = floor(SPKt), f(1/3): 0 [wrong]", fq, sol("0"), NOTOK, None))
    # controls: an integral numbers confirm decides as before
    for e, c, exp in [(f"floor({I3})", "4", OK), (f"floor({I3})", "3", NO), (f"{I3} // 1", "4", OK), (f"Max({I3}, 1)", "9/2", OK),
                      (r"\lfloor \int_0^3 x \, dx \rfloor", "4", OK), ("Sum(1/k**2, (k, 1, 3)) // 1", "1", OK)]:
        out.append((f"YO1 ctl evaluate {e}: {c}", ev(e, [X, {"name": "k", "domain": "positive_integer"}]), sol(c), exp, None))
    out.append((f"YO1 ctl evaluate Interval(1, {I3}) [set]: Interval(1, 9/2)", ir("evaluate", {"expr": f"Interval(1, {I3})"}, (),
                [X], "set"), sol("Interval(1, 9/2)", "set"), OK, None))
    for st, exp in [(f"{I3} // 1 = 4", VER), (f"{I3} > 4", VER), (f"floor({I3}) = 3", REF)]:
        q, s_ = _steps(("compute", st))
        out.append((f"YO1 ctl step {st}", q, s_, ANY, exp))
    out.append(("YO1 ctl given x = I3: evaluate x: 9/2", ev("x", [X], [f"x = {I3}"]), sol("9/2"), OK, None))
    out.append(("YO1 ctl given x > I3, x = 5: evaluate x: 5", ev("x", [X], [f"x > {I3}", "x = 5"]), sol("5"), OK, None))
    return out


def cases_m():
    """YO-2: a Leibniz fraction whatever its typography, with d or dv declared: a derivative or a product (UNKNOWN);
    a slash or a product with a differential above and below too."""
    out = []
    for e, wrong, right, vs in [(r"\frac{d}{d\,x}(x^2)", "x", "2*x", [X, D_]), (r"\frac{d}{d\,x}\left(x^{2}\right)", "x", "2*x", [X, D_]),
                                (r"\frac{d}{d\, x} x^3", "x**2", "3*x**2", [X, D_]), (r"\dfrac{d}{d\,x}(x^2)", "x", "2*x", [X, D_]),
                                (r"\frac{d}{dx}(x^2)", "x", "2*x", [X, D_]), (r"\frac{d}{d x}(x^2)", "x", "2*x", [X, D_]),
                                (r"\frac{\mathrm{d}}{\mathrm{d}x}(x^2)", "x", "2*x", [X, D_]), (r"d/d\,x (x^2)", "x**3", "2*x", [X, D_]),
                                (r"\frac{d}{d\,x}(x^2) + 1", "x + 1", "2*x + 1", [X, D_])]:
        q = ir("simplify_expression", {"expr": e}, (), vs, "expression")
        out.append((f"YO2 {e}: {wrong} [product reading]", q, sol(wrong, "expression"), UNK, None))
        out.append((f"YO2 {e}: {right} [derivative reading]", q, sol(right, "expression"), UNK, None))
    for e, vs, tag in [(r"\frac{d^{2}}{d\,n^{2}}(n \sin(\pi n))", [N, X, D_], "d"), (r"\frac{d^2}{d{n}^2}(n \sin(\pi n))", [N, X, D_], "d"),
                       (r"\frac{d^2}{d\;n^2}(n \sin(\pi n))", [N, D_], "d"), (r"\frac{d^2}{d\!n^2}(n \sin(\pi n))", [N, D_], "d"),
                       (r"\frac{d^2}{d\ n^2}(n \sin(\pi n))", [N, D_], "d"), (r"\frac{d^{2}}{d{n}^{2}}(n \sin(\pi n))", [N, D_], "d"),
                       (r"\frac{\mathrm{d}^2}{\mathrm{d}\,n^2}(n \sin(\pi n))", [N, X, D_], "d"),
                       (r"\frac{d^2}{\mathrm{d}\,n^2}(n \sin(\pi n))", [N, X, D_], "d"),
                       (r"\frac{d^2}{(dn)^2}(n \sin(\pi n))", [N, X, D_, DN_], "d,dn"), (r"\frac{d^2}{dn\,dn}(n \sin(\pi n))", [N, X, D_, DN_], "d,dn"),
                       (r"\frac{{d}^2}{d n^2}(n \sin(\pi n))", [N, X, D_], "d"), (r"\frac{{d}^2}{dn^2}(n \sin(\pi n))", [N, X, D_, DN_], "d,dn"),
                       (r"\frac{d^2}{dn^2}(n \sin(\pi n))", [N, X, DN_], "dn"), (r"\frac{d^2}{d n^2}(n \sin(\pi n))", [N, X, DN_], "dn"),
                       (r"\frac{d \cdot d}{d n^2}(n \sin(\pi n))", [N, X, D_], "d"), (r"\frac{d^2}{d \cdot n^2}(n \sin(\pi n))", [N, X, D_], "d")]:
        q = ir("simplify_expression", {"expr": e}, (), vs, "expression")
        out.append((f"YO2 [{tag}] {e}: 0 [product reading]", q, sol("0", "expression"), UNK, None))
        out.append((f"YO2 [{tag}] {e}: 2*pi*(-1)**n [derivative reading]", q, sol("2*pi*(-1)**n", "expression"), NOTNO, None))
    e3 = ev(r"\frac{d}{d\,x}(x^2)", [X, D_], ["x = 3"])
    out.append(("YO2 evaluate d/d\\,x x^2 at x = 3: 3 [product]", e3, sol("3"), UNK, None))
    out.append(("YO2 evaluate d/d\\,x x^2 at x = 3: 6 [derivative]", e3, sol("6"), UNK, None))
    st = ir("simplify_expression", {"expr": "x"}, (), [X, D_], "expression")
    out.append(("YO2 step eq \\frac{d}{d\\,x}(x^2) = x", st, sol("x", "expression", steps=[("eq", r"\frac{d}{d\,x}(x^2) = x")]),
                ANY, NOTVER))
    out.append(("YO2 step eq \\frac{d}{d\\,x}(x^2) = 2x", st, sol("x", "expression", steps=[("eq", r"\frac{d}{d\,x}(x^2) = 2 x")]),
                ANY, NOTREF))
    # controls
    out.append(("YO2 ctl \\frac{d}{dx} x^3, d undeclared: 3*x**2", ir("simplify_expression", {"expr": r"\frac{d}{dx} x^3"}, (), [X],
                "expression"), sol("3*x**2", "expression"), OK, None))
    # the algebra layer leaves a wrong multiple of the derivative undecided (before this part too)
    out.append(("YO2 ctl \\frac{d}{dx} x^3, d undeclared: x**2", ir("simplify_expression", {"expr": r"\frac{d}{dx} x^3"}, (), [X],
                "expression"), sol("x**2", "expression"), NOTOK, None))
    A_ = {"name": "a", "domain": "positive_real"}
    for e, c in [(r"\frac{d}{a} + \frac{d}{a}", "2*d/a"), (r"\frac{a}{d}", "a/d"), (r"\frac{d}{2} + \frac{d}{2}", "d")]:
        out.append((f"YO2 ctl {e}, d declared: {c}", ir("simplify_expression", {"expr": e}, (), [X, D_, A_], "expression"),
                    sol(c, "expression"), OK, None))
    out.append(("YO2 coverage \\frac{2 d}{3 d}, d declared: 2/3 (a quotient with d above and below: not read)",
                ir("simplify_expression", {"expr": r"\frac{2 d}{3 d}"}, (), [X, D_], "expression"), sol("2/3", "expression"),
                NOTNO, None))
    return out


def cases_n():
    """YO-3: a value-keeping rewrite called with the expression by keyword keeps the form too."""
    out = []
    for st, exp in [(f"simplify(expr=2*{COS}) = 0", NOTVER), (f"expand(e=simplify(expr=2*{COS})) = 0", NOTVER),
                    (f"nsimplify(expr={COS}) = 0", NOTVER), (f"factor(f=2*{COS}) = 0", NOTVER),
                    (f"simplify(expr={LIM}) = 0", NOTVER), (f"simplify(expr=2*{COS}) = 4*sin(1)", NOTREF),
                    (f"simplify(2*{COS}) = 4*sin(1)", NOTREF), (f"simplify(expr={LIM}) = pi", NOTREF),
                    ("simplify(expr=x**2 - x**2) = 0", VER), ("expand(e=(x + 1)**2) = x**2 + 2*x + 1", VER),
                    (f"simplify(2*{COS}) = 0", REF)]:
        q, s_ = _steps(("compute", st), vs=[X, N])
        out.append((f"YO3 step {st}", q, s_, ANY, exp))
    out.append(("YO3 evaluate simplify(expr=2*COS): 0", ev(f"simplify(expr=2*{COS})"), sol("0"), NOTOK, None))
    out.append(("YO3 given b = simplify(expr=2*COS): evaluate b: 0",
                ev("b", [X, {"name": "b", "domain": "real"}], [f"b = simplify(expr=2*{COS})"]), sol("0"), NOTOK, None))
    return out


def _f2(dom):
    return [{"name": "f", "expr": "x + y", "args": ["x", "y"], "domain": dom}]


def cases_p():
    """YO-4: a domain list no number meets on one argument is not read, whatever the number of arguments."""
    out = []
    for dom in ["x < -1, x > 1", "x < -1 and x > 1", "(x < -1) & (x > 1)", "x < -1, y > 0, x > 1",
                "x in (-oo, -1), x in (1, oo)", "(x < -1), (x > 1), (y > 0)"]:
        q = ir("solve_equation", {"equation": "f(x, 1) = 3", "var": "x"}, (), [X, Y_], "set", _f2(dom))
        out.append((f"YO4 f(x, y) on {dom!r}: f(x, 1) = 3: {{}}", q, sol("{}", "set"), UNK, None))
        out.append((f"YO4 f(x, y) on {dom!r}: f(x, 1) = 3: {{2}} [union reading]", q, sol("{2}", "set"), UNK, None))
        c = ir("count_roots", {"expr": "f(x, 1) - 3", "var": "x"}, (), [X, Y_], "count", _f2(dom))
        out.append((f"YO4 f(x, y) on {dom!r}: count f(x, 1) - 3: 0", c, sol("0", "count"), UNK, None))
    q = ir("solve_equation", {"equation": "f(x, 1) = 3", "var": "x"}, (), [X, Y_], "set", _f2("x > 0, y > 0"))
    out.append(("YO4 ctl f(x, y) on 'x > 0, y > 0': f(x, 1) = 3: {2}", q, sol("{2}", "set"), OK, None))
    out.append(("YO4 ctl f(x, y) on 'x > 0, y > 0': f(x, 1) = 3: {}", q, sol("{}", "set"), NO, None))
    for x0, c in [("4", "{}"), ("1/2", "{}"), ("2", "{2}")]:
        q = ir("solve_equation", {"equation": f"x = {x0}", "var": "x"}, ["x in (0, 3), x in (1, 5)"], [X], "set")
        out.append((f"YO4 ctl given list (a conjunction) x = {x0}: {c}", q, sol(c, "set"), NOTNO, None))
    return out


def cases_q():
    """YO-5: a family name the problem uses (a given pins it, a constraint restricts it, the equation names it) is no
    index of the claim: UNKNOWN; a declared one no given names stays an integer index (V17)."""
    out = []
    MR, MI = {"name": "m", "domain": "real"}, {"name": "m", "domain": "integer"}
    t = lambda g, vs: ir("trig_solve", {"var": "x"}, g, vs, "set")  # noqa: E731
    for g, c in [(["sin(x) = 0", "m = 1/2"], "{m*pi + k*pi}"), (["sin(x) = 0", "m = 1/2"], "{pi*n + m*pi}"),
                 (["sin(x) = 0", "m = 1/2"], "{m*pi}"), (["sin(x) = 0", "m = 1/2"], "{m*pi + 2*k*pi}"),
                 (["sin(x) = 0", "m = 1/2"], "{2*m*pi + k*pi + n*pi}"), (["cos(x) = 1", "m = 1/3"], "{2*n*pi + 6*m*pi}"),
                 (["sin(x) = 0", "0 < m < 1"], "{m*pi}"), (["sin(x - m*pi) = 0", "m = 1/2"], "{k*pi}")]:
        out.append((f"YO5 {g}: {c} [wrong or a reading]", t(g, [X, MR]), sol(c, "set"), NOTOK, None))
    out.append(("YO5 sin(x - m pi) = 0, m = 1/2: {pi/2 + k*pi} [right]", t(["sin(x - m*pi) = 0", "m = 1/2"], [X, MR]),
                sol("{pi/2 + k*pi}", "set"), NOTNO, None))
    out.append(("YO5 sin x = 0, k = 2 (k real): {k*pi} [a reading]", t(["sin(x) = 0", "k = 2"], [X, {"name": "k", "domain": "real"}]),
                sol("{k*pi}", "set"), NOTOK, None))
    # controls
    out.append(("YO5 ctl sin x = 0, m = 1/2: {k*pi}", t(["sin(x) = 0", "m = 1/2"], [X, MR]), sol("{k*pi}", "set"), OK, None))
    out.append(("YO5 ctl sin x = 0, m real declared, no given: {m*pi} (V17)", t(["sin(x) = 0"], [X, MR]), sol("{m*pi}", "set"),
                OK, None))
    out.append(("YO5 ctl sin x = 0, m integer: {m*pi}", t(["sin(x) = 0"], [X, MI]), sol("{m*pi}", "set"), OK, None))
    out.append(("YO5 ctl sin x = 0, k = 2 (k real): {n*pi}", t(["sin(x) = 0", "k = 2"], [X, {"name": "k", "domain": "real"}]),
                sol("{n*pi}", "set"), OK, None))
    out.append(("YO5 ctl cos x = 1: {2*n*pi}", t(["cos(x) = 1"], [X, MR]), sol("{2*n*pi}", "set"), OK, None))
    return out


def cases_r():
    """RK-1: `x \\in S` with S holding the line is a membership: no restriction for a real x."""
    out = []
    for g in [r"$x \in \mathbb{R}$", r"$x \in (-\infty, \infty)$", r"x \in \mathbb{R}", r"$x\in\mathbb{R}$",
              r"$x \in (-\infty, 0) \cup [0, \infty)$"]:
        c = ir("count_roots", {"expr": "x**2 - 4", "var": "x"}, [g], [X], "count")
        out.append((f"RK1 given {g}: count x**2 - 4: 2", c, sol("2", "count"), OK, None))
        out.append((f"RK1 given {g}: count x**2 - 4: 1", c, sol("1", "count"), NO, None))
        out.append((f"RK1 given {g}: x**2 < 4: (-2, 2)", ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, [g], [X], "set"),
                    sol("Interval.open(-2, 2)", "interval"), OK, None))
        m = ir("extremum", {"f": "x**2 - 2*x", "var": "x", "which": "min"}, [g], [X])
        out.append((f"RK1 given {g}: min x**2 - 2x: -1", m, sol("-1"), OK, None))
        out.append((f"RK1 given {g}: min x**2 - 2x: 0", m, sol("0"), NO, None))
        out.append((f"RK1 given {g}: domain of sqrt(x - 1): [1, oo)",
                    ir("domain_of", {"expr": "sqrt(x - 1)", "var": "x"}, [g], [X], "set"), sol("Interval(1, oo)", "interval"),
                    OK, None))
        out.append((f"RK1 given {g}: x**2 = 4: {{-2, 2}}", ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [g], [X], "set"),
                    sol("{-2, 2}", "set"), OK, None))
    out.append((r"RK1 domain $x \in \mathbb{R}$: f(x) = 5: {-2, 2}",
                ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(r"$x \in \mathbb{R}$")),
                sol("{-2, 2}", "set"), OK, None))
    out.append((r"RK1 given $x \notin \mathbb{R}$ (no real x): x**2 = 4: {-2, 2}",
                ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [r"$x \notin \mathbb{R}$"], [X], "set"),
                sol("{-2, 2}", "set"), NOTOK, None))
    out.append((r"RK1 ctl given $x \in [0, \infty)$: x**2 = 4: {2}",
                ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [r"$x \in [0, \infty)$"], [X], "set"),
                sol("{2}", "set"), OK, None))
    out.append((r"RK1 ctl given $x \in [0, \infty)$: x**2 = 4: {-2, 2}",
                ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [r"$x \in [0, \infty)$"], [X], "set"),
                sol("{-2, 2}", "set"), NO, None))
    return out


def cases_s():
    """RK-2: a domain list of a set and another condition: a verdict where the union and the intersection readings
    agree, UNKNOWN where they part."""
    out = []
    for dom, rows in [("(-3, 3), (-5, 5)", [("{-2, 2}", OK), ("{2}", NO)]), ("[0, 5], [1, 3]", [("{2}", OK), ("{-2, 2}", NO)]),
                      ("x > 1, (0, 3)", [("{2}", OK), ("{}", NO)]), ("(0, oo), x <= 5", [("{2}", UNK), ("{-2, 2}", UNK)]),
                      ("(-oo, -1), (1, oo)", [("{}", UNK), ("{-2, 2}", UNK), ("{2}", NOTOK)]),
                      ("(-oo, 1), (1, oo)", [("{-2, 2}", UNK)]), ("(0, 3) and (4, 5)", [("{}", UNK)])]:
        q = ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
        for c, exp in rows:
            out.append((f"RK2 domain {dom!r}: f(x) = 5: {c}", q, sol(c, "set"), exp, None))
    for dom, rows in [("(-3, 3), (-5, 5)", [("2", OK), ("1", NO)]), ("(0, oo), x <= 5", [("1", UNK), ("2", UNK)])]:
        c = ir("count_roots", {"expr": "f(x) - 5", "var": "x"}, (), [X], "count", _f(dom))
        for v, exp in rows:
            out.append((f"RK2 domain {dom!r}: count f(x) - 5: {v}", c, sol(v, "count"), exp, None))
    return out


def cases_t():
    """PRE-RK-4: the task's relation written in params is a premise of the steps, as givens[0] is."""
    out = []
    for form in ("params", "givens"):
        for eq, c, steps, exp, st in [("sqrt(x + 2) = x", "{2}", [("eq", "x + 2 = x**2")], OK, VER),
                                      ("x**2 - x - 2 = 0", "{-1, 2}", [("eq", "x + 2 = x**2")], OK, VER),
                                      ("sqrt(x + 2) = x", "{2}", [("eq", "x**2 - x - 2 = 0"), ("eq", "x = 2")], OK, VER),
                                      ("x**2 - x - 2 = 0", "{-1, 2}", [("eq", "(x - 2)*(x + 1) = 0")], OK, VER),
                                      ("sqrt(x + 2) = x", "{2}", [("eq", "x + 2 = x**3")], NO, REF),
                                      ("x**2 - x - 2 = 0", "{-1, 2}", [("eq", "x + 2 = x**3")], NO, REF)]:
            q = ir("solve_equation", {"equation": eq, "var": "x"} if form == "params" else {"var": "x"},
                   () if form == "params" else [eq], [X], "set")
            out.append((f"RK4 {form} {eq}: {c} with {[s for _, s in steps]}", q, sol(c, "set", steps), exp, st))
        q = ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"} if form == "params" else {"var": "x"},
               () if form == "params" else ["x**2 < 4"], [X], "set")
        out.append((f"RK4 {form} x**2 < 4: (-2, 2) with x < 2", q, sol("Interval.open(-2, 2)", "interval", [("eq", "x < 2")]), OK, VER))
        out.append((f"RK4 {form} x**2 < 4: (-2, 2) with x < 1", q, sol("Interval.open(-2, 2)", "interval", [("eq", "x < 1")]), NO, REF))
    return out


def cases_u():
    """PRE-RK-5: a claim written as a condition on the task's variable is read as the set it names (LaTeX and plain
    text the same tree), notation only; one that is no notation is not read and never refuted."""
    out = []
    sq = ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, (), [X], "set")
    for c, k, exp in [(r"$x \in \{-2, 2\}$", "set", OK), (r"$x = \pm 2$", "set", NOTNO), (r"x \in \{-2, 2\}", "set", OK),
                      ("x in {-2, 2}", "set", OK), (r"$x \in \{-3, 3\}$", "set", NO), ("x = 2", "set", NO),
                      (r"$x = -2 \lor x = 2$", "set", NOTNO), ("x = -2, x = 2", "set", NOTNO), ("x**2 = 4", "set", NOTOK),
                      ("{x}", "set", NOTOK)]:
        out.append((f"RK5 x**2 = 4: {c} [{k}]", sq, sol(c, k), exp, None))
    iq = ir("solve_inequality", {"inequality": "x**2 - 4*x + 3 <= 0", "var": "x"}, (), [X], "set")
    for c, k, exp in [(r"$1 \leq x \leq 3$", "interval", OK), (r"$x \in [1, 3]$", "interval", OK), (r"$x \in [1, 3]$", "set", OK),
                      (r"$1 \le x \le 3$", "condition", OK), ("1 <= x <= 3", "interval", OK), (r"$x \in [1, 4]$", "interval", NO),
                      (r"$1 \le x \le 4$", "set", NO), ("x**2 - 4*x + 3 <= 0", "interval", UNK), ("x**2 - 4*x + 3 <= 0", "set", UNK),
                      ("x**2 - 4*x + 3 <= 0", "condition", UNK)]:
        out.append((f"RK5 x**2 - 4x + 3 <= 0: {c} [{k}]", iq, sol(c, k), exp, None))
    gq = ir("solve_inequality", {"inequality": "x**2 - 4*x + 3 > 0", "var": "x"}, (), [X], "set")
    for c, k, exp in [(r"$x \in (-\infty, 1) \cup (3, \infty)$", "interval", OK), (r"$x < 1 \text{ or } x > 3$", "condition", NOTNO),
                      ("x < 1 or x > 3", "condition", NOTNO)]:
        out.append((f"RK5 x**2 - 4x + 3 > 0: {c} [{k}]", gq, sol(c, k), exp, None))
    r2 = ir("solve_inequality", {"inequality": "x**2 + 1 > 0", "var": "x"}, (), [X], "set")
    out.append((r"RK5 x**2 + 1 > 0: $x \in \mathbb{R}$", r2, sol(r"$x \in \mathbb{R}$", "set"), OK, None))
    out.append((r"RK5 x**2 + 1 > 0: $x \in \mathbb{Z}$", r2, sol(r"$x \in \mathbb{Z}$", "set"), NO, None))
    d1 = ir("domain_of", {"expr": "1/(x - 1)", "var": "x"}, (), [X], "set")
    for c, exp in [(r"$x \neq 1$", OK), ("x != 1", OK), (r"$x \in \mathbb{R} \setminus \{1\}$", NOTNO), (r"$x \neq 2$", NO)]:
        out.append((f"RK5 domain of 1/(x - 1): {c}", d1, sol(c, "set"), exp, None))
    d2 = ir("domain_of", {"expr": "sqrt(x - 1)", "var": "x"}, (), [X], "set")
    for c, exp in [(r"$x \geq 1$", OK), (r"$x \in [1, \infty)$", OK), ("x >= 1", OK), (r"$x > 1$", NO)]:
        out.append((f"RK5 domain of sqrt(x - 1): {c}", d2, sol(c, "set"), exp, None))
    return out


def cases_v():
    """PRE-RK-6: SymPy's registry S is no value: a claim naming it bare is UNKNOWN, never an exception."""
    out = []
    sq = ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, (), [X], "set")
    for c, k in [("S = {-2, 2}", "set"), ("S = {-3, 3}", "set"), (r"$S = (-2, 2)$", "interval"), ("S = [1, 2]", "interval"),
                 ("S", "set"), ("{S}", "set")]:
        out.append((f"RK6 x**2 = 4: {c!r} [{k}]", sq, sol(c, k), UNK, None))
    e2 = ev("2", [X])
    for c in ["S = 2", "S", "S + 1", "Eq(S, 2)", "{S: 2}"]:
        out.append((f"RK6 evaluate 2: {c!r}", e2, sol(c), UNK, None))
    for st in ["S = 2", "S + 1 = 3", "x = S"]:
        out.append((f"RK6 step {st!r}", e2, sol("2", steps=[("eq", st)]), UNK, None))
    out.append(("RK6 given S = 2", ev("x", [X], ["S = 2", "x = 2"]), sol("2"), UNK, None))
    for c, exp in [("S(2)", OK), ("S.Half*4", OK), ("2*S.One", OK), ("S(3)", NO)]:
        out.append((f"RK6 ctl evaluate 2: {c!r}", e2, sol(c), exp, None))
    return out


def cases_w():
    """PRE-RK-7/8: the structural reading keeps a matrix operation as an operation (no ~23 s determinant); a claim is
    a restatement only when its tree is the target's, never by the target's value."""
    out = []
    M = "Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]])"
    dq = ev("det(Matrix([[Integral(x, (x, 0, 2)), 1], [1, 1]]))", [X])
    out.append(("RK7 det([[∫_0^2 x dx, 1], [1, 1]]): 1", dq, sol("1"), OK, None))
    out.append(("RK7 det([[∫_0^2 x dx, 1], [1, 1]]): 2", dq, sol("2"), NO, None))
    for e, c, exp in [(f"eigmax({M})", "2 + sqrt(2)", OK), (f"eigmax({M})", "sqrt(2) + 2", OK), (f"eigmin({M})", "2 - sqrt(2)", OK),
                      (f"eigmax({M})", "2", NO), (f"eigmax({M})", f"eigmax({M})", UNK), (f"det({M})", "4", OK),
                      (f"det({M})", f"det({M})", UNK), (f"trace({M})", "6", OK), ("binomial(6, 3)", "binomial(6, 3)", UNK),
                      ("binomial(6, 3)", "20", OK), ("gcd(84, 120)", "gcd(84,120)", UNK), ("P(5, 2)", "P(5, 2)", UNK),
                      ("P(5, 2)", "20", OK)]:
        out.append((f"RK8 evaluate {e[:24]}: {c[:24]}", ev(e, [X]), sol(c), exp, None))
    return out


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f, "G": cases_g,
          "H": cases_h, "K": cases_k, "L": cases_l, "M": cases_m, "N": cases_n, "P": cases_p, "Q": cases_q,
          "R": cases_r, "S": cases_s, "T": cases_t, "U": cases_u, "V": cases_v, "W": cases_w}
ALL = "".join(GROUPS)


def main(out_path=None, groups=ALL):
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
    grp = args[1] if len(args) > 1 else ALL
    sys.exit(1 if main(out, grp) else 0)
