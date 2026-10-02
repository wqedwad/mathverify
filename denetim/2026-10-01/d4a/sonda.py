"""Part d4a of the fourth audit's fixes (1 Oct 2026): conventions and the z3 bridge.

Findings (denetim/2026-10-01/d4/dogrulama.json): capraz/CAP-C1 and adim/D4-ADIM-K (an odd root read under
two conventions: (-8)**(1/3) certified both -2 and 1 + sqrt(3)*I; the step layer solved a premise with
SymPy's principal root), capraz/CAP-N1 (ℕ / N / Naturals read as {1, 2, ...}), capraz/CAP-B1 (the
generalized binomial dropped or kept silently), gorev/G13 (0**0 = 1 applied silently), capraz/CAP-M1
(Mod with a negative divisor: SymPy floored, z3 Euclidean), capraz/CAP-D1 (the z3 bridge dropped the
integrality of domain_of_discourse), capraz/CAP-Z1 (z3 refuted every claim when the givens have no
instance).

The main session's decisions: written roots (`cbrt`, `root(., n)`, `real_root`, `\\sqrt[3]{}`, ∛) are real
roots; the power notation `b**(p/q)` (q odd) at a negative base is a convention (real root or principal
value), so a verdict that depends on it is UNKNOWN; the principal complex value is never CORRECT and two
values are never both certified. ℕ/N/Naturals: a verdict that depends on 0 ∈ ℕ is UNKNOWN (Z+, N+, ℕ⁺,
N0, ℕ0, Naturals0 and the IR keywords keep their reading). C(n, r) outside 0 <= r <= n integers, 0**0,
and Mod with a divisor that is negative or of undecided sign are conventions: UNKNOWN where the verdict
depends on them. The z3 bridge carries the integrality of the domain of discourse, and givens with no
instance get no verdict (ir_inconsistent).

    C  odd roots            N  natural numbers      B  binomial          O  0**0
    M  Mod, negative divisor  D  z3 and an integer domain of discourse    Z  z3 with unsatisfiable givens
    K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/d4a/sonda.py [out.json] [groups]

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
NOTNO = {"CORRECT", "UNKNOWN"}        # anything but a false rejection
VER = {"verified"}
REF = {"refuted"}
NOTVER = {"refuted", "unknown", "skipped"}
NOTREF = {"verified", "unknown", "skipped"}

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
N = {"name": "n", "domain": "integer"}
NR = {"name": "n", "domain": "real"}
M = {"name": "m", "domain": "integer"}
K = {"name": "k", "domain": "integer"}
A = {"name": "a", "domain": "real"}


def ev(expr, vars_=(), givens=(), dod=None, options=None):
    d = {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": "scalar"}
    if dod is not None:
        d["domain_of_discourse"] = dod
    if options:
        d["options"] = options
    return d


def solve(eq, var="x", vars_=(X,), givens=(), dod=None, kind="solve_equation"):
    key = "equation" if kind == "solve_equation" else "inequality"
    d = {"task": {"kind": kind, "params": {"var": var, key: eq}}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": "set"}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def count(var="x", vars_=(X,), givens=(), dod=None):
    d = {"task": {"kind": "count_integers", "params": {"var": var}}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": "count"}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def simp(expr, vars_=(X,)):
    return {"task": {"kind": "simplify_expression", "params": {"expr": expr}}, "vars": list(vars_), "givens": [],
            "answer_shape": "expression"}


def dom_of(expr, vars_=(X,)):
    return {"task": {"kind": "domain_of", "params": {"expr": expr, "var": "x"}}, "vars": list(vars_), "givens": [],
            "answer_shape": "set"}


def sol(payload, steps=(), kind="value", option=None):
    return {"claimed_answer": {"kind": kind, "payload": payload, "option": option},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def sset(p):
    return sol(p, kind="set")


def ival(p):
    return sol(p, kind="interval")


def cnt(n):
    return sol(n, kind="count")


def cp(*claims):
    return [("compute", c) for c in claims]


R_NOT0 = "Union(Interval.open(-oo, 0), Interval.open(0, oo))"
CPLX = "1 + sqrt(3)*I"


# (label, ir, solution, expected verdicts, expected step statuses: None, a set for every step, or a list per step)
def cases_c():
    rows = []
    for e in ("(-8)**(1/3)", "(-8)^(1/3)"):
        rows += [(f"evaluate {e} -> -2 (convention)", ev(e), sol("-2"), UNK, None),
                 (f"evaluate {e} -> 1+sqrt3 I", ev(e), sol(CPLX), NOTOK, None)]
    for e in ("cbrt(-8)", "root(-8, 3)", r"\sqrt[3]{-8}", "∛(-8)", "real_root(-8, 3)"):
        rows += [(f"evaluate {e} -> -2 (written root: real)", ev(e), sol("-2"), OK, None),
                 (f"evaluate {e} -> 1+sqrt3 I", ev(e), sol(CPLX), NOTOK, None),
                 (f"evaluate {e} -> 2*exp(I*pi/3)", ev(e), sol("2*exp(I*pi/3)"), NOTOK, None)]
    rows += [
        ("evaluate (-1)**(1/3) -> -1", ev("(-1)**(1/3)"), sol("-1"), UNK, None),
        ("evaluate (-1)**(1/3) -> 1/2+sqrt3/2 I", ev("(-1)**(1/3)"), sol("1/2 + sqrt(3)*I/2"), NOTOK, None),
        ("evaluate (-8)**(2/3) -> 4", ev("(-8)**(2/3)"), sol("4"), UNK, None),
        ("evaluate (-8)**(2/3) -> -2+2sqrt3 I", ev("(-8)**(2/3)"), sol("-2 + 2*sqrt(3)*I"), NOTOK, None),
        ("evaluate (-8)**(-1/3) -> -1/2", ev("(-8)**(-1/3)"), sol("-1/2"), UNK, None),
        ("evaluate (-8)**(-1/3) -> 1/4-sqrt3/4 I", ev("(-8)**(-1/3)"), sol("1/4 - sqrt(3)*I/4"), NOTOK, None),
        ("evaluate (-32)**(1/5) -> -2", ev("(-32)**(1/5)"), sol("-2"), UNK, None),
        ("evaluate (-8)**(1/3)+2 -> 3+sqrt3 I", ev("(-8)**(1/3) + 2"), sol("3 + sqrt(3)*I"), NOTOK, None),
        ("evaluate (-27)**(1/3)*(-8)**(1/3) -> 6", ev("(-27)**(1/3)*(-8)**(1/3)"), sol("6"), UNK, None),
        ("evaluate cbrt(-27)+sqrt(16) -> 1", ev("cbrt(-27) + sqrt(16)"), sol("1"), OK, None),
        ("evaluate cbrt(-27)+sqrt(16) -> 11/2+3sqrt3/2 I", ev("cbrt(-27) + sqrt(16)"),
         sol("11/2 + 3*sqrt(3)*I/2"), NOTOK, None),
        ("x**(1/3), x=-8 -> -2", ev("x**(1/3)", [X], ["x = -8"]), sol("-2"), UNK, None),
        ("x**(1/3), x=-8 -> 1+sqrt3 I", ev("x**(1/3)", [X], ["x = -8"]), sol(CPLX), NOTOK, None),
        ("x**(1/3), x+8=0 -> 1+sqrt3 I", ev("x**(1/3)", [X], ["x + 8 = 0"]), sol(CPLX), NOTOK, None),
        ("x**(1/3), x**3=-512 -> 1+sqrt3 I", ev("x**(1/3)", [X], ["x**3 = -512"]), sol(CPLX), NOTOK, None),
        ("x**(2/3), x=-8 -> 4", ev("x**(2/3)", [X], ["x = -8"]), sol("4"), UNK, None),
        ("x**(2/3), x=-8 -> -2+2sqrt3 I", ev("x**(2/3)", [X], ["x = -8"]), sol("-2 + 2*sqrt(3)*I"), NOTOK, None),
        ("cbrt(x), x=-8 -> -2", ev("cbrt(x)", [X], ["x = -8"]), sol("-2"), OK, None),
        ("cbrt(x), x=-8 -> 1+sqrt3 I", ev("cbrt(x)", [X], ["x = -8"]), sol(CPLX), NOTOK, None),
        ("simplify (-8)**(1/3)*x -> -2x", simp("(-8)**(1/3)*x"), sol("-2*x", kind="expression"), UNK, None),
        ("simplify (-8)**(1/3)*x -> (1+sqrt3 I)x", simp("(-8)**(1/3)*x"), sol("(1 + sqrt(3)*I)*x", kind="expression"),
         NOTOK, None),
        ("simplify cbrt(-8)*x -> -2x", simp("cbrt(-8)*x"), sol("-2*x", kind="expression"), OK, None),
        ("options: (-8)**(1/3), A=-2 C=1+sqrt3 I -> A", ev("(-8)**(1/3)", options={"A": "-2", "B": "2", "C": CPLX}),
         sol(None, option="A"), UNK, None),
        ("options: (-8)**(1/3) -> C", ev("(-8)**(1/3)", options={"A": "-2", "B": "2", "C": CPLX}),
         sol(None, option="C"), NOTOK, None),
        # the two contradictory steps are never both verified
        ("steps: (-8)**(1/3) = -2 and = 1+sqrt3 I", ev("cbrt(-8)"),
         sol("-2", cp("(-8)**(1/3) = -2", f"(-8)**(1/3) = {CPLX}")), NOTNO, [NOTREF - VER, NOTREF - VER]),
        ("steps: cbrt(-8) = -2 verified, = 1+sqrt3 I refuted", ev("cbrt(-8)"),
         sol("-2", cp("cbrt(-8) = -2", f"cbrt(-8) = {CPLX}")), NOTOK, [VER, REF]),
        ("step: cbrt(-27) = 3/2+3sqrt3/2 I refuted", ev("cbrt(-27)"),
         sol("-3", cp("cbrt(-27) = 3/2 + 3*sqrt(3)*I/2")), NOTOK, [REF]),
        ("step eq: x**(1/3) = 1+sqrt3 I at x=-8", ev("x", [X], ["x = -8"]),
         sol("-8", [("eq", f"x**(1/3) = {CPLX}")]), NOTNO, [NOTREF - VER]),
        # the given written with the power notation: the curriculum value is no longer refuted
        ("given x = (-8)**(1/3) -> -2", ev("x", [X], ["x = (-8)**(1/3)"]), sol("-2"), UNK, None),
        ("given x = (-8)**(1/3) -> 1+sqrt3 I", ev("x", [X], ["x = (-8)**(1/3)"]), sol(CPLX), NOTOK, None),
        ("given x - (-8)**(1/3) = 0 -> -2", ev("x", [X], ["x - (-8)**(1/3) = 0"]), sol("-2"), UNK, None),
        ("given x = (-1)**(1/3) -> -1", ev("x", [X], ["x = (-1)**(1/3)"]), sol("-1"), UNK, None),
        ("given x = cbrt(-8) -> -2", ev("x", [X], ["x = cbrt(-8)"]), sol("-2"), OK, None),
        ("given x = root(-8, 3) -> -2", ev("x", [X], ["x = root(-8, 3)"]), sol("-2"), OK, None),
        ("solve x = (-8)**(1/3) -> {-2}", solve("x = (-8)**(1/3)"), sset("{-2}"), UNK, None),
        ("solve x = (-8)**(1/3) -> {1+sqrt3 I}", solve("x = (-8)**(1/3)"), sset("{1 + sqrt(3)*I}"), NOTOK, None),
        # D4-ADIM-K: the premise x**(1/3) = x is {-1, 0, 1} with the real root, {0, 1} with the principal one
        ("ADIM-K: x**(1/3) = x, step Abs(x) = x", ev("x", [X], ["x**(1/3) = x"]),
         sol("x", cp("Abs(x) = x")), None, [NOTVER]),
        ("ADIM-K: solve x**(1/3) = x -> {-1, 0, 1}", solve("x**(1/3) = x"), sset("{-1, 0, 1}"), UNK, None),
        ("ADIM-K: solve x**(1/3) = x -> {0, 1}", solve("x**(1/3) = x"), sset("{0, 1}"), UNK, None),
        ("ADIM-K: x**(1/3) = -2 -> {-8}", solve("x**(1/3) = -2"), sset("{-8}"), UNK, None),
        ("ADIM-K: x**(1/3) = -2 -> {}", solve("x**(1/3) = -2"), sset("EmptySet"), UNK, None),
        ("x**(1/3) < 1 -> (-oo, 1) (convention below 0)", solve("x**(1/3) < 1", kind="solve_inequality"),
         ival("Interval.open(-oo, 1)"), UNK, None),
        ("cbrt(x) = x -> {0, 1}", solve("cbrt(x) = x"), sset("{0, 1}"), NOTOK, None),
        ("cbrt(x) = -2 -> {}", solve("cbrt(x) = -2"), sset("EmptySet"), NOTOK, None),
        ("cbrt(x) = -2 -> {-8}", solve("cbrt(x) = -2"), sset("{-8}"), NOTNO, None),
        ("cbrt(x) = x premise, step Abs(x) = x refuted at -1", ev("x", [X], ["cbrt(x) = x"]),
         sol("x", cp("Abs(x) = x")), None, [REF]),
    ]
    return rows


def cases_n():
    rows = []
    for dod in ("ℕ", "N", "Naturals", "x ∈ ℕ", "x in N"):
        rows += [(f"x^2-3x=0 over {dod!r} -> {{3}}", solve("x**2 - 3*x = 0", dod=dod), sset("{3}"), UNK, None),
                 (f"x^2-3x=0 over {dod!r} -> {{0, 3}}", solve("x**2 - 3*x = 0", dod=dod), sset("{0, 3}"), UNK, None)]
    rows += [
        ("x^2=0 over ℕ -> {0}", solve("x**2 = 0", dod="ℕ"), sset("{0}"), UNK, None),
        ("x^2=0 over ℕ -> {}", solve("x**2 = 0", dod="ℕ"), sset("{}"), UNK, None),
        ("evaluate x, x(x-1)=0 over N -> 1", ev("x", [X], ["x*(x - 1) = 0"], dod="N"), sol("1"), UNK, None),
        ("evaluate x, x(x-4)=0 over ℕ -> 4", ev("x", [X], ["x*(x - 4) = 0"], dod="ℕ"), sol("4"), UNK, None),
        ("count 0<=x<=3 over Naturals -> 3", count(givens=["x >= 0", "x <= 3"], dod="Naturals"), cnt(3), UNK, None),
        ("count 0<=x<=3 over Naturals -> 4", count(givens=["x >= 0", "x <= 3"], dod="Naturals"), cnt(4), UNK, None),
        ("count x<=5 over ℕ -> 5", count(givens=["x <= 5"], dod="ℕ"), cnt(5), UNK, None),
        ("count x<=5 over ℕ -> 6", count(givens=["x <= 5"], dod="ℕ"), cnt(6), UNK, None),
        ("x^2<4 over ℕ -> {1}", solve("x**2 < 4", dod="ℕ", kind="solve_inequality"), sset("{1}"), UNK, None),
        ("x^2<4 over N -> {0, 1}", solve("x**2 < 4", dod="N", kind="solve_inequality"), sset("{0, 1}"), UNK, None),
        ("count_roots x^3=x over ℕ -> 1", {"task": {"kind": "count_roots", "params": {"expr": "x**3 - x", "var": "x"}},
                                            "vars": [X], "givens": [], "answer_shape": "count",
                                            "domain_of_discourse": "ℕ"}, cnt(1), UNK, None),
        ("claim set ℕ: x >= 0 over Integers", solve("x >= 0", dod="Integers", kind="solve_inequality"),
         sset("ℕ"), UNK, None),
        ("claim set N: x > 0 over Integers", solve("x > 0", dod="Integers", kind="solve_inequality"),
         sset("N"), UNK, None),
        ("claim set Naturals: x >= 0 over Integers", solve("x >= 0", dod="Integers", kind="solve_inequality"),
         sset("Naturals"), UNK, None),
        # the answer does not depend on 0: decided
        ("x^2=4 over ℕ -> {2}", solve("x**2 = 4", dod="ℕ"), sset("{2}"), OK, None),
        ("x^2=4 over ℕ -> {-2, 2}", solve("x**2 = 4", dod="ℕ"), sset("{-2, 2}"), NO, None),
        ("x^2=4 over ℕ -> {}", solve("x**2 = 4", dod="ℕ"), sset("{}"), NO, None),
        # unambiguous spellings keep their reading
        ("x^2=0 over N0 -> {0}", solve("x**2 = 0", dod="N0"), sset("{0}"), OK, None),
        ("x^2=0 over Naturals0 -> {0}", solve("x**2 = 0", dod="Naturals0"), sset("{0}"), OK, None),
        ("x^2=0 over ℕ0 -> {0}", solve("x**2 = 0", dod="ℕ0"), sset("{0}"), OK, None),
        ("x^2=0 over Z+ -> {}", solve("x**2 = 0", dod="Z+"), sset("{}"), OK, None),
        ("x^2=0 over N+ -> {} (no layer_exception)", solve("x**2 = 0", dod="N+"), sset("{}"), NOTNO, None),
        ("x^2=0 over ℕ⁺ -> {} (no layer_exception)", solve("x**2 = 0", dod="ℕ⁺"), sset("{}"), NOTNO, None),
        ("x^2=0 over ℕ⁺ -> {0}", solve("x**2 = 0", dod="ℕ⁺"), sset("{0}"), NOTOK, None),
        ("x^2-3x=0 over Z+ -> {3}", solve("x**2 - 3*x = 0", dod="Z+"), sset("{3}"), OK, None),
        ("natural n, n(n-4)=0 -> 4", ev("n", [{"name": "n", "domain": "natural"}], ["n*(n - 4) = 0"]), sol("4"),
         OK, None),
        ("nonneg_integer n, n(n-4)=0 -> 4", ev("n", [{"name": "n", "domain": "nonneg_integer"}], ["n*(n - 4) = 0"]),
         sol("4"), NOTOK, None),
    ]
    return rows


def cases_b():
    rows = []
    for vars_, tag in (([N], "integer n"), ([NR], "real n")):
        q = solve("binomial(n, 2) = 3", "n", vars_)
        rows += [(f"{tag}: C(n,2)=3 -> {{-2, 3}}", q, sset("{-2, 3}"), UNK, None),
                 (f"{tag}: C(n,2)=3 -> {{3}}", q, sset("{3}"), UNK, None),
                 (f"{tag}: C(n,2)=3 -> {{-2}}", q, sset("{-2}"), NO, None),
                 (f"{tag}: C(n,2)=3 -> {{}}", q, sset("{}"), NO, None)]
    rows += [
        ("C(n,2)=1 -> {-1, 2}", solve("binomial(n, 2) = 1", "n", [N]), sset("{-1, 2}"), UNK, None),
        ("C(n,2)=6 -> {-3, 4} (C alias)", solve("C(n, 2) = 6", "n", [N]), sset("{-3, 4}"), UNK, None),
        ("C(n,2)=10 -> {-4, 5}", solve("binomial(n, 2) = 10", "n", [N]), sset("{-4, 5}"), UNK, None),
        ("C(n,2)=0 -> {}", solve("binomial(n, 2) = 0", "n", [N]), sset("{}"), UNK, None),
        ("C(n,2)=0 -> {0, 1}", solve("binomial(n, 2) = 0", "n", [N]), sset("{0, 1}"), UNK, None),
        ("n^2=4: evaluate C(n,2) -> 1", ev("binomial(n, 2)", [N], ["n**2 = 4"]), sol("1"), UNK, None),
        ("n^2=4: evaluate C(n,2) -> 3", ev("binomial(n, 2)", [N], ["n**2 = 4"]), sol("3"), UNK, None),
        ("given C(n,2)=3: evaluate n -> 3", ev("n", [N], ["binomial(n, 2) = 3"]), sol("3"), UNK, None),
        ("given C(n,2)=3: evaluate n -> -2", ev("n", [N], ["binomial(n, 2) = 3"]), sol("-2"), UNK, None),
        ("real n, given C(n,2)=10: evaluate n -> 5", ev("n", [NR], ["binomial(n, 2) = 10"]), sol("5"), UNK, None),
        ("evaluate C(-2, 2) -> 3", ev("binomial(-2, 2)"), sol("3"), UNK, None),
        ("evaluate C(2, 5) -> 0", ev("binomial(2, 5)"), sol("0"), UNK, None),
        # inside the curriculum's range: decided
        ("evaluate C(5, 2) -> 10", ev("binomial(5, 2)"), sol("10"), OK, None),
        ("evaluate C(5, 2) -> 11", ev("binomial(5, 2)"), sol("11"), NO, None),
        # completeness of {3} is not certified (z3 does not translate a symbolic binomial): before and after
        ("n>=2 integer: C(n,2)=3 -> {3}", solve("binomial(n, 2) = 3", "n", [N], ["n >= 2"]), sset("{3}"), NOTNO,
         None),
        ("n>=2 integer: C(n,2)=3 -> {}", solve("binomial(n, 2) = 3", "n", [N], ["n >= 2"]), sset("{}"), NO, None),
        ("n!: x! = 6 real -> {3}", solve("factorial(x) = 6"), sset("{3}"), NOTNO, None),
        ("n! at -3: evaluate n + n! - n!, n=-3", ev("n + factorial(n) - factorial(n)", [N], ["n = -3"]), sol("-3"),
         NOTOK, None),
    ]
    return rows


def cases_o():
    return [
        ("evaluate 0**0 -> 1", ev("0**0"), sol("1"), UNK, None),
        ("evaluate 0^0 -> 1", ev("0^0"), sol("1"), UNK, None),
        ("evaluate 0**0 -> 0", ev("0**0"), sol("0"), NOTOK, None),
        ("evaluate 0**0 + 2 -> 3", ev("0**0 + 2"), sol("3"), UNK, None),
        ("evaluate (2-2)**0 -> 1", ev("(2 - 2)**0"), sol("1"), UNK, None),
        ("evaluate 0**(3-3)*5 -> 5", ev("0**(3 - 3)*5"), sol("5"), UNK, None),
        ("evaluate sin(0)**0 -> 1", ev("sin(0)**0"), sol("1"), UNK, None),
        ("evaluate LaTeX 0^{0} -> 1", ev("0^{0}"), sol("1"), UNK, None),
        ("x**0, x=0 -> 1", ev("x**0", [X], ["x = 0"]), sol("1"), UNK, None),
        ("x**0, x**2=0 -> 1", ev("x**0", [X], ["x**2 = 0"]), sol("1"), UNK, None),
        ("given a = 0**0: a + 1 -> 2", ev("a + 1", [A], ["a = 0**0"]), sol("2"), UNK, None),
        ("x**0 = 1 -> Reals", solve("x**0 = 1"), ival("Reals"), UNK, None),
        ("x**0 = 1 -> R\\{0}", solve("x**0 = 1"), ival(R_NOT0), UNK, None),
        ("(x-2)**0 = 1 -> Reals", solve("(x - 2)**0 = 1"), ival("Reals"), UNK, None),
        ("x**0 + x = 1 -> {0}", solve("x**0 + x = 1"), sset("{0}"), UNK, None),
        ("x**0 + x = 1 -> {}", solve("x**0 + x = 1"), sset("{}"), UNK, None),
        ("(x-1)**0 = x -> {1}", solve("(x - 1)**0 = x"), sset("{1}"), UNK, None),
        ("x**0 > 0 -> Reals", solve("x**0 > 0", kind="solve_inequality"), ival("Reals"), UNK, None),
        ("domain_of (x-1)**0 -> Reals", dom_of("(x - 1)**0"), ival("Reals"), UNK, None),
        ("domain_of (x-1)**0 -> R\\{1}", dom_of("(x - 1)**0"),
         ival("Union(Interval.open(-oo, 1), Interval.open(1, oo))"), UNK, None),
        ("step: compute 0**0 = 1", ev("x", [X], ["x = 2"]), sol("2", cp("0**0 = 1")), NOTNO, [NOTREF - VER]),
        ("Sum(0**k, (k, 0, 3)) -> 1 (k declared)", ev("Sum(0**k, (k, 0, 3))", [K]), sol("1"), UNK, None),
        # no 0**0 anywhere: decided
        ("evaluate 5**0 -> 1", ev("5**0"), sol("1"), OK, None),
        ("evaluate 5**0 -> 0", ev("5**0"), sol("0"), NO, None),
        ("positive x**0, x=3 -> 1", ev("x**0", [XP], ["x = 3"]), sol("1"), OK, None),
        ("x**0, x=3 -> 1", ev("x**0", [X], ["x = 3"]), sol("1"), OK, None),
        ("positive x: x**0 = 1 -> (0, oo)", solve("x**0 = 1", vars_=[XP]), ival("Interval.open(0, oo)"), OK, None),
        ("x**0 = 2 -> {}", solve("x**0 = 2"), sset("{}"), NOTNO, None),
    ]


def cases_m():
    NM = [N, M]
    return [
        ("Mod(7,-5) -> -3", ev("Mod(7, -5)"), sol("-3"), UNK, None),
        ("Mod(7,-5) -> 2", ev("Mod(7, -5)"), sol("2"), UNK, None),
        ("Mod(-7,-5) -> -2", ev("Mod(-7, -5)"), sol("-2"), UNK, None),
        ("Mod(-7,-5) -> 3", ev("Mod(-7, -5)"), sol("3"), UNK, None),
        ("LaTeX 13 \\mod (-4) -> -3", ev(r"13 \mod (-4)"), sol("-3"), NOTOK, None),
        ("n = Mod(7,m), m=-5 indirect -> 2", ev("n", NM, ["n = Mod(7, m)", "floor(m/2) = -3", "Mod(m, 2) = 1"]),
         sol("2"), UNK, None),
        ("n = Mod(7,m), m=-5 indirect -> -3", ev("n", NM, ["n = Mod(7, m)", "floor(m/2) = -3", "Mod(m, 2) = 1"]),
         sol("-3"), UNK, None),
        ("n = Mod(7,m), -6<m<-4 -> 2", ev("n", NM, ["n = Mod(7, m)", "m > -6", "m < -4"]), sol("2"), UNK, None),
        ("n = Mod(7,m), m=-5 -> 2", ev("n", NM, ["n = Mod(7, m)", "m = -5"]), sol("2"), UNK, None),
        ("Mod(n,-5) = -3, 0<=n<5 -> 2", ev("n", [N], ["Mod(n, -5) = -3", "n >= 0", "n < 5"]), sol("2"), UNK, None),
        ("Mod(n,-5), 6<n<8 -> 2", ev("Mod(n, -5)", [N], ["n > 6", "n < 8"]), sol("2"), UNK, None),
        ("Mod(n,-5), 6<n<8 -> -3", ev("Mod(n, -5)", [N], ["n > 6", "n < 8"]), sol("-3"), UNK, None),
        ("Mod(n,-4), 12<n<14 -> 1", ev("Mod(n, -4)", [N], ["n > 12", "n < 14"]), sol("1"), UNK, None),
        ("step Mod(7,-5) = 2", ev("n", [N], ["n = 1"]), sol("1", cp("Mod(7, -5) = 2")), NOTNO, [NOTREF - VER]),
        ("step Mod(7,-5) = -3", ev("n", [N], ["n = 1"]), sol("1", cp("Mod(7, -5) = -3")), NOTNO, [NOTREF - VER]),
        ("count Mod(n,-3)=2 on [0,8] -> 3", count("n", [N], ["Mod(n, -3) = 2", "n >= 0", "n <= 8"]), cnt(3), UNK, None),
        ("count Mod(n,-3)=2 on [0,8] -> 0", count("n", [N], ["Mod(n, -3) = 2", "n >= 0", "n <= 8"]), cnt(0), UNK, None),
        ("solve Mod(x,-4) = -3 on [0,3] -> {1}", solve("Mod(n, -4) = -3", "n", [N], ["n >= 0", "n <= 3"]),
         sset("{1}"), UNK, None),
        # a positive divisor: one reading
        ("Mod(7,5) -> 2", ev("Mod(7, 5)"), sol("2"), OK, None),
        ("Mod(-7,5) -> 3", ev("Mod(-7, 5)"), sol("3"), OK, None),
        ("Mod(-7,5) -> -2", ev("Mod(-7, 5)"), sol("-2"), NO, None),
        # z3 alone decided these (algebra: cas_error); its % is Euclidean, so a divisor not proved positive is
        # not translated (coverage loss: the divisor's sign follows from the givens only)
        ("n = Mod(7,m), m=5 indirect -> 2", ev("n", NM, ["n = Mod(7, m)", "floor(m/2) = 2", "Mod(m, 2) = 1"]),
         sol("2"), NOTNO, None),
        ("n = Mod(7,m), m=5 indirect -> -3", ev("n", NM, ["n = Mod(7, m)", "floor(m/2) = 2", "Mod(m, 2) = 1"]),
         sol("-3"), NOTOK, None),
        ("positive m: n = Mod(7,m), m=5 -> 2", ev("n", [N, {"name": "m", "domain": "positive_integer"}],
                                                   ["n = Mod(7, m)", "floor(m/2) = 2", "Mod(m, 2) = 1"]),
         sol("2"), OK, None),
        ("Mod(n,5) = 2, 0<=n<5 -> 2", ev("n", [N], ["Mod(n, 5) = 2", "n >= 0", "n < 5"]), sol("2"), OK, None),
        ("Mod(5**100, 7) -> 2", ev("Mod(5**100, 7)"), sol("2"), OK, None),
        ("step Mod(7,5) = 3 refuted", ev("n", [N], ["n = 1"]), sol("1", cp("Mod(7, 5) = 3")), NO, [REF]),
    ]


def cases_d():
    G = ["floor(x) + x = 5/2"]
    rows = []
    for dod in ("Integers", "Z", "ℤ", "x in Integers", "x in Z", "Complement(Integers, {0})",
                "x in Complement(Integers, {0})"):
        rows.append((f"floor(x)+x=5/2 over {dod!r} -> 3/2", ev("x", [X], G, dod=dod), sol("3/2"), NOTOK, None))
    rows += [
        ("2x, over Integers -> 3", ev("2*x", [X], G, dod="Integers"), sol("3"), NOTOK, None),
        ("x**2, over Integers -> 9/4", ev("x**2", [X], G, dod="Integers"), sol("9/4"), NOTOK, None),
        ("ceiling(x)+x=7/2 over Integers -> 3/2", ev("x", [X], ["ceiling(x) + x = 7/2"], dod="Integers"),
         sol("3/2"), NOTOK, None),
        ("options A=3/2 over Integers -> A", ev("x", [X], G, dod="Integers", options={"A": "3/2", "B": "1", "C": "2"}),
         sol(None, option="A"), NOTOK, None),
        ("x+y, x in Integers, y=1 -> 5/2", ev("x + y", [X, {"name": "y", "domain": "real"}], G + ["y = 1"],
                                               dod="x in Integers"), sol("5/2"), NOTOK, None),
        ("solve floor(x)+x=5/2 over Integers -> {3/2}", solve("floor(x) + x = 5/2", dod="Integers"), sset("{3/2}"),
         NOTOK, None),
        # an integer solution exists: not refuted
        ("floor(x)+x=4 over Integers -> 2", ev("x", [X], ["floor(x) + x = 4"], dod="Integers"), sol("2"), NOTNO, None),
        ("floor(x)+x=4 over Integers -> 3", ev("x", [X], ["floor(x) + x = 4"], dod="Integers"), sol("3"), NOTOK, None),
        # the real problem keeps its certificate
        ("floor(x)+x=5/2 over reals -> 3/2", ev("x", [X], G), sol("3/2"), OK, None),
        ("floor(x)+x=5/2 over reals -> 1", ev("x", [X], G), sol("1"), NO, None),
        ("integer x: floor(x)+x=5/2 -> 3/2", ev("x", [{"name": "x", "domain": "integer"}], G), sol("3/2"), NOTOK, None),
    ]
    return rows


def cases_z():
    return [
        ("x=1, x=2: payload 1", ev("x", [X], ["x = 1", "x = 2"]), sol("1"), UNK, None),
        ("x=1, x=2: payload 7", ev("x", [X], ["x = 1", "x = 2"]), sol("7"), UNK, None),
        ("x=1, x=2: option A (=1)", ev("x", [X], ["x = 1", "x = 2"], options={"A": "1", "B": "2"}),
         sol(None, option="A"), UNK, None),
        ("x=1, x=2: payload 1 + option A", ev("x", [X], ["x = 1", "x = 2"], options={"A": "1", "B": "2"}),
         sol("1", option="A"), UNK, None),
        ("y=3, y=5: y+1 -> 4", ev("y + 1", [{"name": "y", "domain": "real"}], ["y = 3", "y = 5"]), sol("4"), UNK, None),
        ("a+b=3, a+b=4: a -> 1", ev("a", [A, {"name": "b", "domain": "real"}], ["a + b = 3", "a + b = 4"]), sol("1"),
         UNK, None),
        ("x^2=4, x>2 -> 2", ev("x", [X], ["x**2 = 4", "x > 2"]), sol("2"), UNK, None),
        ("sqrt(x) = -1 -> 1", ev("x", [X], ["sqrt(x) = -1"]), sol("1"), UNK, None),
        ("1/x = 0 -> 1", ev("x", [X], ["1/x = 0"]), sol("1"), UNK, None),
        ("x^2+1=0: x**2 -> -1", ev("x**2", [X], ["x**2 + 1 = 0"]), sol("-1"), UNK, None),
        ("integer n, 2n=3 -> 3/2", ev("n", [N], ["2*n = 3"]), sol("3/2"), UNK, None),
        ("integer n, 2n=3 -> 2", ev("n", [N], ["2*n = 3"]), sol("2"), UNK, None),
        ("positive x, x=-1 -> -1", ev("x", [XP], ["x = -1"]), sol("-1"), UNK, None),
        ("constraint x>5, x=2 -> 2", ev("x", [{"name": "x", "domain": "real", "constraints": ["x > 5"]}], ["x = 2"]),
         sol("2"), UNK, None),
        ("dod x>0, x=-3 -> -3", ev("x", [X], ["x = -3"], dod="x > 0"), sol("-3"), UNK, None),
        ("given Mod(n,-5) = -3 with n=7 -> ...", ev("n", [N], ["Mod(n, -5) = -3", "n = 7"]), sol("7"), UNK, None),
        # consistent givens: decided
        ("x=3 -> 4", ev("x", [X], ["x = 3"]), sol("4"), NO, None),
        ("x=3 -> 3", ev("x", [X], ["x = 3"]), sol("3"), OK, None),
        ("x^2=4, x>0 -> 2", ev("x", [X], ["x**2 = 4", "x > 0"]), sol("2"), OK, None),
        ("x^2=4, x>0 -> -2", ev("x", [X], ["x**2 = 4", "x > 0"]), sol("-2"), NO, None),
        ("floor(x)+x=5/2 -> 1 (z3 only)", ev("x", [X], ["floor(x) + x = 5/2"]), sol("1"), NO, None),
        ("integer n, 2n+1=7, n>0 -> 3", ev("n", [N], ["2*n + 1 = 7", "n > 0"]), sol("3"), OK, None),
    ]


def cases_k():
    return [
        ("8**(1/3) -> 2", ev("8**(1/3)"), sol("2"), OK, None),
        ("positive x**(1/3), x=8 -> 2", ev("x**(1/3)", [XP], ["x = 8"]), sol("2"), OK, None),
        ("x**(1/3), x=8 -> 2", ev("x**(1/3)", [X], ["x = 8"]), sol("2"), OK, None),
        ("x**(1/3), x=8 -> 3", ev("x**(1/3)", [X], ["x = 8"]), sol("3"), NO, None),
        ("sqrt(-4) -> 2I", ev("sqrt(-4)"), sol("2*I"), NOTOK, None),
        ("(-16)**(1/4) -> 2", ev("(-16)**(1/4)"), sol("2"), NOTOK, None),
        ("x**(1/3) = 2 -> {8}", solve("x**(1/3) = 2"), sset("{8}"), NOTNO, None),
        ("x**(1/3) = 2 -> {}", solve("x**(1/3) = 2"), sset("{}"), NO, None),
        ("positive: x**(1/3) < 1 -> (0, 1)", solve("x**(1/3) < 1", vars_=[XP], kind="solve_inequality"),
         ival("Interval.open(0, 1)"), NOTNO, None),
        ("cbrt(x) < 1 -> (-oo, 1)", solve("cbrt(x) < 1", kind="solve_inequality"), ival("Interval.open(-oo, 1)"),
         NOTNO, None),
        ("cbrt(x) < 1 -> (0, 1)", solve("cbrt(x) < 1", kind="solve_inequality"), ival("Interval.open(0, 1)"),
         NOTOK, None),
        ("simplify cbrt(x)**3 -> x", simp("cbrt(x)**3"), sol("x", kind="expression"), NOTNO, None),
        ("simplify x**(1/3)*x**(2/3) -> x (x>0)", simp("x**(1/3)*x**(2/3)", [XP]), sol("x", kind="expression"), OK, None),
        ("binomial(6, 3) -> 20", ev("binomial(6, 3)"), sol("20"), OK, None),
        ("Mod(100, 6) -> 4", ev("Mod(100, 6)"), sol("4"), OK, None),
        ("integer n: Mod(n, 2) = 1, 0<n<3 -> 1", ev("n", [N], ["Mod(n, 2) = 1", "n > 0", "n < 3"]), sol("1"), OK, None),
        ("x**2 = 4, x>0, dod Reals -> 2", ev("x", [X], ["x**2 = 4", "x > 0"], dod="Reals"), sol("2"), OK, None),
    ]


def cases_s():
    """Sibling paths of the same mechanisms: other task kinds, the claim side, the step layer, z3, options."""
    def kind(k, params, vars_=(X,), givens=(), shape="scalar", dod=None):
        d = {"task": {"kind": k, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}
        if dod is not None:
            d["domain_of_discourse"] = dod
        return d
    NN = [{"name": "n", "domain": "integer"}]
    return [
        ("count_roots x**(1/3) - x -> 3", kind("count_roots", {"expr": "x**(1/3) - x", "var": "x"}, shape="count"),
         cnt(3), UNK, None),
        ("count_roots x**(1/3) - x -> 2", kind("count_roots", {"expr": "x**(1/3) - x", "var": "x"}, shape="count"),
         cnt(2), UNK, None),
        ("count_roots cbrt(x) - x -> 2", kind("count_roots", {"expr": "cbrt(x) - x", "var": "x"}, shape="count"),
         cnt(2), NOTOK, None),
        ("x**(1/3) > -1 -> (-1, oo)", solve("x**(1/3) > -1", kind="solve_inequality"), ival("Interval.open(-1, oo)"),
         UNK, None),
        ("x**(1/3) > -1 -> [0, oo)", solve("x**(1/3) > -1", kind="solve_inequality"), ival("Interval(0, oo)"),
         UNK, None),
        ("domain_of x**(1/3) -> Reals", dom_of("x**(1/3)"), ival("Reals"), UNK, None),
        ("domain_of x**(1/3) -> [0, oo)", dom_of("x**(1/3)"), ival("Interval(0, oo)"), UNK, None),
        ("domain_of cbrt(x) -> Reals", dom_of("cbrt(x)"), ival("Reals"), NOTNO, None),
        ("domain_of cbrt(x) -> [0, oo)", dom_of("cbrt(x)"), ival("Interval(0, oo)"), NOTOK, None),
        ("derivative of x**(1/3) at -8 -> 1/12", kind("derivative", {"f": "x**(1/3)", "var": "x", "at": "-8"}),
         sol("1/12"), UNK, None),
        ("limit x**(1/3) at -8 -> -2", kind("limit", {"expr": "x**(1/3)", "var": "x", "to": "-8"}), sol("-2"),
         UNK, None),
        ("limit cbrt(x) at -8 -> 1+sqrt3 I", kind("limit", {"expr": "cbrt(x)", "var": "x", "to": "-8"}),
         sol(CPLX), NOTOK, None),
        ("min of x**(1/3) on [-8, 8] -> -2", kind("extremum", {"f": "x**(1/3)", "var": "x", "interval": "[-8, 8]",
                                                              "which": "min"}), sol("-2"), UNK, None),
        # the claim's own value is a convention
        ("evaluate 5**0, claim 0**0", ev("5**0"), sol("0**0"), UNK, None),
        ("evaluate cos(0), claim 0**0", ev("cos(0)"), sol("0**0"), UNK, None),
        ("evaluate 10, claim C(5,2) + C(2,5)", ev("10"), sol("binomial(5, 2) + binomial(2, 5)"), UNK, None),
        ("evaluate 2, claim Mod(12, -5) + 5", ev("2"), sol("Mod(12, -5) + 5"), UNK, None),
        ("evaluate -2, claim (-8)**(1/3)", ev("-2"), sol("(-8)**(1/3)"), UNK, None),
        ("evaluate -2, claim cbrt(-8)", ev("-2"), sol("cbrt(-8)"), OK, None),
        ("evaluate 3, claim (-8)**(1/3)", ev("3"), sol("(-8)**(1/3)"), NO, None),
        ("solve x**3 = -8 -> {(-8)**(1/3)}", solve("x**3 = -8"), sset("{(-8)**(1/3)}"), UNK, None),
        ("solve x**3 = -8 -> {cbrt(-8)}", solve("x**3 = -8"), sset("{cbrt(-8)}"), OK, None),
        ("derivative of cbrt(x) -> x**(-2/3)/3", kind("derivative", {"f": "cbrt(x)", "var": "x"}, shape="expression"),
         sol("x**(-2/3)/3", kind="expression"), UNK, None),
        ("x**0*(x-1)*x = 0 -> {1}", solve("x**0*(x - 1)*x = 0"), sset("{1}"), UNK, None),
        ("x**0*(x-1)*x = 0 -> {0}", solve("x**0*(x - 1)*x = 0"), sset("{0}"), NO, None),
        ("x = -2 given: x, claim (-8)**(1/3)", ev("x", [X], ["x = -2"]), sol("(-8)**(1/3)"), UNK, None),
        # x**0 is 1 wherever it is defined under either reading (like x/x): the simplification stands
        ("simplify x**0 -> 1", simp("x**0"), sol("1", kind="expression"), NOTNO, None),
        ("simplify positive x**0 -> 1", simp("x**0", [XP]), sol("1", kind="expression"), OK, None),
        ("simplify x*x**(1/3) -> x**(4/3)", simp("x*x**(1/3)"), sol("x**(4/3)", kind="expression"), UNK, None),
        ("simplify cbrt(x)**3 -> x", simp("cbrt(x)**3"), sol("x", kind="expression"), NOTNO, None),
        # steps
        ("C(n,2), n^2=4: step eq n = 2", ev("binomial(n, 2)", NN, ["n**2 = 4"]),
         sol("1", [("eq", "n = 2")]), UNK, [NOTVER]),
        ("x**0 expr: step eq x = 0 not refuted", ev("x**0 + x", [X], ["x**2 = 0"]),
         sol("1", [("eq", "x = 0")]), UNK, [NOTREF]),
        # x**(1/3) = x, x != 0: {-1, 1} (real root) or {1} (principal); x**2 = 1 under both readings
        ("given x**(1/3) = x: step eq x >= 0", ev("x**2", [X], ["x**(1/3) = x", "x != 0"]),
         sol("1", [("eq", "x >= 0")]), NOTNO, [NOTVER]),
        ("given x**(1/3) = x, x != 0: step compute x**2 = 1", ev("x**2", [X], ["x**(1/3) = x", "x != 0"]),
         sol("1", cp("x**2 = 1")), NOTNO, [NOTREF]),
        ("given x**(1/3) = x, x != 0: x -> 1", ev("x", [X], ["x**(1/3) = x", "x != 0"]), sol("1"), UNK, None),
        ("given x**(1/3) = x, x != 0: x -> -1", ev("x", [X], ["x**(1/3) = x", "x != 0"]), sol("-1"), UNK, None),
        # natural numbers: options, LaTeX, marks
        ("options A=ℕ: x >= 0 over Integers", {**solve("x >= 0", dod="Integers", kind="solve_inequality"),
                                               "options": {"A": "ℕ", "B": "Integers"}},
         sol(None, kind="set", option="A"), UNK, None),
        ("x^2-3x=0 over \\mathbb{N} -> {3}", solve("x**2 - 3*x = 0", dod=r"\mathbb{N}"), sset("{3}"), UNK, None),
        ("x^2-3x=0 over ℕ⁺ -> {3}", solve("x**2 - 3*x = 0", dod="ℕ⁺"), sset("{3}"), OK, None),
        ("x^2-3x=0 over ℕ0 -> {0, 3}", solve("x**2 - 3*x = 0", dod="ℕ0"), sset("{0, 3}"), OK, None),
        ("x^2-3x=0 over ℕ0 -> {3}", solve("x**2 - 3*x = 0", dod="ℕ0"), sset("{3}"), NO, None),
        ("given x in ℕ, x^2 = 3x: x -> 3", ev("x", [X], ["x**2 = 3*x"], dod="x ∈ ℕ"), sol("3"), UNK, None),
        ("variable N: N = 3 -> 3", ev("N", [{"name": "N", "domain": "real"}], ["N = 3"]), sol("3"), OK, None),
        # binders: a convention at one point of an integral is not its value; on an interval it is
        ("integral of x**0 on [-1, 1] -> 2", kind("definite_integral", {"integrand": "x**0", "var": "x",
                                                                         "a": "-1", "b": "1"}),
         sol("2"), NOTNO, None),
        ("integral of x**(1/3) on [-1, 1] -> 0", kind("definite_integral", {"integrand": "x**(1/3)", "var": "x",
                                                                             "a": "-1", "b": "1"}),
         sol("0"), UNK, None),
        ("integral of cbrt(x) on [-1, 1] -> 0", kind("definite_integral", {"integrand": "cbrt(x)", "var": "x",
                                                                            "a": "-1", "b": "1"}),
         sol("0"), NOTNO, None),
        ("Sum(binomial(5, k), (k, 0, 5)) -> 32", ev("Sum(binomial(5, k), (k, 0, 5))", [{"name": "k", "domain": "integer"}]),
         sol("32"), OK, None),
        ("Sum(binomial(5, k), (k, 0, 7)) -> 32", ev("Sum(binomial(5, k), (k, 0, 7))", [{"name": "k", "domain": "integer"}]),
         sol("32"), UNK, None),
        # z3 and the domain of discourse
        ("floor(x)+x=5/2 over N0 -> 3/2", ev("x", [X], ["floor(x) + x = 5/2"], dod="N0"), sol("3/2"), NOTOK, None),
        ("floor(x)+x=4 over N0 -> 2", ev("x", [X], ["floor(x) + x = 4"], dod="N0"), sol("2"), NOTNO, None),
        ("x in Integers constraint: floor(x)+x=5/2 -> 3/2",
         ev("x", [{"name": "x", "domain": "real", "constraints": ["x > -10"]}], ["floor(x) + x = 5/2"],
            dod="Intersection(Integers, Interval(-10, 10))"), sol("3/2"), NOTOK, None),
    ]


def cases_a():
    """The review of part d4a (attack A): a comparison read on `domain_for`, which leaves out the points
    where an odd root written as a power has a negative base, certified a claim true on x >= 0 only.
    Both readings refute Abs(x) for (x**3)**(1/3) at x = -2 (-2, or 2·e^{iπ/3}, against 2); a claim that
    holds under one reading only (cbrt(x) for x**(1/3)) decides nothing. Also a variable N next to the set N."""
    A_ = {"name": "a", "domain": "real"}

    def k(kind_, params, shape="scalar", vars_=(X,)):
        return {"task": {"kind": kind_, "params": params}, "vars": list(vars_), "givens": [], "answer_shape": shape}
    ex = lambda p: sol(p, kind="expression")  # noqa: E731
    return [
        ("simplify (x**3)**(1/3) -> Abs(x)", simp("(x**3)**(1/3)"), ex("Abs(x)"), NO, None),
        ("simplify x**(1/3) -> Abs(x)**(1/3)", simp("x**(1/3)"), ex("Abs(x)**(1/3)"), NO, None),
        ("simplify (x**5)**(1/5) -> Abs(x)", simp("(x**5)**(1/5)"), ex("Abs(x)"), NO, None),
        ("simplify ((x-1)**3)**(1/3) -> Abs(x-1)", simp("((x - 1)**3)**(1/3)"), ex("Abs(x - 1)"), NO, None),
        ("simplify x**(1/3)*x**(2/3) -> Abs(x)", simp("x**(1/3)*x**(2/3)"), ex("Abs(x)"), NO, None),
        ("simplify x**(1/3) + cbrt(x) -> 2*Abs(x)**(1/3)", simp("x**(1/3) + cbrt(x)"), ex("2*Abs(x)**(1/3)"),
         NO, None),
        ("simplify LaTeX x^{1/3} -> Abs(x)**(1/3)", simp(r"x^{\frac{1}{3}}"), ex("Abs(x)**(1/3)"), NO, None),
        ("evaluate (a**3)**(1/3) -> Abs(a)", ev("(a**3)**(1/3)", [A_]), ex("Abs(a)"), NO, None),
        ("options: simplify (x**3)**(1/3), A = Abs(x)", {**simp("(x**3)**(1/3)"), "options": {"A": "Abs(x)", "B": "-x"}},
         sol(None, kind="expression", option="A"), NOTOK, None),
        # one reading only
        ("simplify x**(1/3) -> cbrt(x)", simp("x**(1/3)"), ex("cbrt(x)"), UNK, None),
        ("simplify x**(2/3) -> cbrt(x)**2", simp("x**(2/3)"), ex("cbrt(x)**2"), UNK, None),
        ("simplify (x**3)**(2/3) -> x**2", simp("(x**3)**(2/3)"), ex("x**2"), UNK, None),
        ("simplify x**(1/3)*x**(2/3) -> x", simp("x**(1/3)*x**(2/3)"), ex("x"), UNK, None),
        ("simplify (x**3)**(1/3) + x -> 2*x", simp("(x**3)**(1/3) + x"), ex("2*x"), UNK, None),
        ("simplify x**(2/3) -> Abs(x)**(2/3)", simp("x**(2/3)"), ex("Abs(x)**(2/3)"), UNK, None),
        ("derivative (x**3)**(1/3) -> sign(x)", k("derivative", {"f": "(x**3)**(1/3)", "var": "x"}, "expression"),
         ex("sign(x)"), NOTOK, None),
        ("antiderivative (x**3)**(1/3) -> x*Abs(x)/2", k("antiderivative", {"integrand": "(x**3)**(1/3)", "var": "x"},
                                                         "expression"), ex("x*Abs(x)/2 + C"), NOTOK, None),
        ("limit (x**3)**(1/3) at -2 -> 2", k("limit", {"expr": "(x**3)**(1/3)", "var": "x", "to": "-2"}), sol("2"),
         NOTOK, None),
        ("min of (x**3)**(1/3) on [-2, 1] -> 0", k("extremum", {"f": "(x**3)**(1/3)", "var": "x", "interval": "[-2, 1]",
                                                               "which": "min"}), sol("0"), NOTOK, None),
        # controls: no value convention
        ("simplify positive x**(1/3)*x**(2/3) -> x", simp("x**(1/3)*x**(2/3)", [XP]), ex("x"), OK, None),
        ("simplify cbrt(x)**3 -> x", simp("cbrt(x)**3"), ex("x"), OK, None),
        ("simplify x**0 -> 1 (0**0: 1 or undefined)", simp("x**0"), ex("1"), OK, None),
        ("limit cbrt(x) at -8 -> -2", k("limit", {"expr": "cbrt(x)", "var": "x", "to": "-8"}), sol("-2"), OK, None),
        ("min of cbrt(x) on [-8, 1] -> -2", k("extremum", {"f": "cbrt(x)", "var": "x", "interval": "[-8, 1]",
                                                           "which": "min"}), sol("-2"), NOTNO, None),
        # a variable N and the set N
        ("vars x, N; dod N: x^2-3x=0 -> {3}", {**solve("x**2 - 3*x = 0", dod="N"),
                                              "vars": [X, {"name": "N", "domain": "real"}]}, sset("{3}"), UNK, None),
    ]


GROUPS = {"A": cases_a, "C": cases_c, "N": cases_n, "B": cases_b, "O": cases_o, "M": cases_m, "D": cases_d, "Z": cases_z,
          "K": cases_k, "S": cases_s}


def _statuses_ok(want, got):
    if want is None:
        return True
    if isinstance(want, list):
        return len(want) == len(got) and all(g in w for w, g in zip(want, got))
    return all(g in want for g in got)


def main(out_path=None, groups="ACNBOMDZSK"):
    import os
    import mathverify
    from mathverify.verifier import verify
    assert os.path.abspath(mathverify.__file__).startswith(os.getcwd()), mathverify.__file__
    rows = []
    bad = 0
    t0 = time.time()
    for g in groups:
        for label, ir, sol_, verdicts, statuses in GROUPS[g]():
            t = time.time()
            try:
                r = verify(ir, sol_)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                got = [s.get("status") for s in steps]
                flags = sorted(r.flags)
                why = [(la.layer, la.verdict, str((la.evidence or {}).get("reason", ""))[:60])
                       for la in r.layers if la.verdict != "unknown" or la.layer.startswith(("certify", "intake"))]
            except Exception as e:  # noqa: BLE001
                verdict, got, flags, why = f"EXC {type(e).__name__}: {e}", [], [], []
            ok = (verdicts is None or verdict in verdicts) and _statuses_ok(statuses, got) \
                and "layer_exception" not in flags
            bad += not ok
            rows.append({"group": g, "label": label, "verdict": verdict, "steps": got, "ok": ok, "flags": flags,
                         "layers": json.loads(json.dumps(why, default=str)), "s": round(time.time() - t, 2)})
            print(f"{'ok ' if ok else 'BAD'} {g} {verdict:9} {got} {label}  {flags[:4]}", flush=True)
    print(f"{len(rows)} cases, {bad} not as expected, {time.time() - t0:.0f} s")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else None
    grp = args[1] if len(args) > 1 else "ACNBOMDZSK"
    sys.exit(1 if main(out, grp) else 0)
