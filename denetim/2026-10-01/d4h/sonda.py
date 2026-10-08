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
    for e, wrong, right in [(f"floor({SPK})", "0", "1"), (f"ceiling({SPK})", "1", "2"), (f"Max({SPK}, 1)", "1", "sqrt(pi)"),
                            (f"Min({SPK}, 2)", "2", None), (f"frac({SPK})", "0", None),
                            (f"sign({SPK} - 1)", "-1", "1"), (f"floor(a*{SPK.replace('1000*', '1000*')})", "0", "1")]:
        g = ["a = 1"] if "a*" in e else []
        vs = [X, A] if g else [X]
        out.append((f"F1' evaluate {e}: {wrong} [wrong]", ev(e, vs, g), sol(wrong), NOTOK, None))
        if right:
            out.append((f"F1' evaluate {e}: {right} [right]", ev(e, vs, g), sol(right), NOTNO, None))
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
    out = []
    lists = [("(-oo, -1), (1, oo)", "{-2, 2}", "2"), ("(0, 3), (4, 5)", "{2}", "1"), ("[-3, -1], [1, 3]", "{-2, 2}", "2"),
             ("(-oo, -1) & (1, oo)", "{-2, 2}", "2"), ("(-oo, -1) and (1, oo)", "{-2, 2}", "2"),
             ("(-oo, -1) ∧ (1, oo)", "{-2, 2}", "2"), ("x in (-oo, -1), x in (1, oo)", "{-2, 2}", "2"),
             ("x < -1, x > 1", "{-2, 2}", "2"), ("x <= -1 ∧ x >= 1", "{-2, 2}", "2"), ("x<-1 and x>1", "{-2, 2}", "2"),
             ("(0, 3), (1, 5)", "{2}", "1"), ("x in (0, 3), x in (1, 5)", "{2}", "1"), ("(-oo, -1), x > 1", "{-2, 2}", "2"),
             ("(0, 3), x > 1", "{2}", "1")]
    for dom, union_answer, union_count in lists:
        fn = _f(dom)
        q = ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", fn)
        out.append((f"D2 domain {dom!r}: f(x)=5, {{}}", q, sol("{}", "set"), UNK, None))
        out.append((f"D2 domain {dom!r}: f(x)=5, {union_answer} [union reading]", q, sol(union_answer, "set"), UNK, None))
        d = ir("domain_of", {"expr": "f(x)", "var": "x"}, (), [X], "set", fn)
        out.append((f"D2 domain {dom!r}: domain_of f, {{}}", d, sol("{}", "set"), UNK, None))
        c = ir("count_roots", {"expr": "f(x) - 5", "var": "x"}, (), [X], "count", fn)
        out.append((f"D2 domain {dom!r}: count f(x) - 5: 0", c, sol("0", "count"), UNK, None))
        out.append((f"D2 domain {dom!r}: count f(x) - 5: {union_count} [union reading]", c, sol(union_count, "count"), UNK, None))
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
