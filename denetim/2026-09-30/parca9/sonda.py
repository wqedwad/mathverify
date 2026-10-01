"""Part 9 of the 30 Sep 2026 fixes: a reversed symbolic range decides nothing (DECISIONS §80, "Ters toplam
aralığı"; §79 Karr).

§79 made a Sum/Product with a symbolic bound need hi - lo + 1 >= 0 (`certify.domain._range_span_conditions`),
and a point where that fails was dropped like a point where the expression is undefined. But below the
empty range (hi < lo - 1) the value is a convention, not undefined: SymPy's Karr sum gives one number, the
empty-sum (Iverson) reading 0, and the curriculum none. Dropping the point picked a convention: with
n**2 = 4 (n an integer) Σ_{k=1}^{n} k = 3 was CORRECT because n = -2 was dropped (under the empty-sum
reading the values are {3, 0}). Decision (§80): a candidate, root or solution whose acceptance or rejection
rests on a reversed range is neither kept nor dropped; the verdict is UNKNOWN. hi = lo - 1 (the empty sum,
n = 0 -> 0) stays defined.

    A  a given equation with a root in the reversed region: no value is certified (UNKNOWN)
    B  an equation in the bound itself (solve_equation, count): no solution set is certified
    C  steps: a step whose truth rests on the reversed region is not verified
    D  controls whose verdict must not change (§79's controls among them)

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-30/parca9/sonda.py [out.json] [groups]

Lean is not needed (MATHVERIFY_LEAN_REPL=/nonexistent). Kept out of pyflakes and pytest like the rest
of denetim/.
"""
from __future__ import annotations

import json
import sys
import time

UNK = {"UNKNOWN"}
OK = {"CORRECT"}
NO = {"INCORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}      # anything but a false accept
ANY = {"CORRECT", "INCORRECT", "UNKNOWN"}
NOT_VERIFIED = {"unknown", "refuted", "unverifiable", "skipped", "not_checked"}

KN = [{"name": "k", "domain": "integer"}, {"name": "n", "domain": "integer"}]
KP = [{"name": "k", "domain": "integer"}, {"name": "n", "domain": "positive_integer"}]
K0 = [{"name": "k", "domain": "integer"}, {"name": "n", "domain": "nonneg_integer"}]
KU = [{"name": "k", "domain": "integer"}, {"name": "n"}]
KJN = KN + [{"name": "j", "domain": "integer"}]


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": shape}


def _sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def ev(e, g=(), v=KN):
    return _ir("evaluate", {"expr": e}, v, g)


def solve(eq, v=KN, g=()):
    return _ir("solve_equation", {"var": "n", "equation": eq}, v, g, shape="set")


S = "Sum(k, (k, 1, n))"


# (label, ir, solution, expected verdicts, expected status of the LAST step: set or None)
def cases_a():
    return [
        # n = -2: Karr 1, empty sum 0, the curriculum none
        ("n^2 = 4: Sum = 3", ev(S, ["n**2 = 4"]), _sol("3"), UNK, None),
        ("n^2 = 4: Sum = 1 (Karr's value at -2)", ev(S, ["n**2 = 4"]), _sol("1"), NOTOK, None),
        ("n^2 = 4: Sum = 0", ev(S, ["n**2 = 4"]), _sol("0"), NOTOK, None),
        ("n^2 = 4 (n undeclared): Sum = 3", ev(S, ["n**2 = 4"], KU), _sol("3"), UNK, None),
        ("n^2 = 4 written n**2 - 4 = 0: Sum = 3", ev(S, ["n**2 - 4 = 0"]), _sol("3"), UNK, None),
        ("n^2 = 4: 2*Sum + n = 8", ev(f"2*{S} + n", ["n**2 = 4"]), _sol("8"), UNK, None),
        ("n^2 = 4: latex sum = 3", ev(r"\sum_{k=1}^{n} k", ["n**2 = 4"]), _sol("3"), UNK, None),
        # n = -3: Karr 3, empty sum 0
        ("n^2 = 9: Sum = 6", ev(S, ["n**2 = 9"]), _sol("6"), UNK, None),
        ("n^2 = 9: Sum = 3 (Karr at -3)", ev(S, ["n**2 = 9"]), _sol("3"), NOTOK, None),
        # n = -1: Karr 0 and empty sum 0 agree, the curriculum still has none
        ("n^2 = 1: Sum = 1", ev(S, ["n**2 = 1"]), _sol("1"), UNK, None),
        ("n(n + 1) = 0: Sum = 0 (n = 0 empty, n = -1 reversed)", ev(S, ["n*(n + 1) = 0"]), _sol("0"), UNK, None),
        # the reversed root is the larger one: Σ_{k=n}^{1} k at n = 3 runs backwards
        ("n^2 = 9: Sum(k, (k, n, 1)) = -5", ev("Sum(k, (k, n, 1))", ["n**2 = 9"]), _sol("-5"), UNK, None),
        ("n^2 = 4: Sum(k, (k, n, 0)) = -3 (n = 2 reversed)", ev("Sum(k, (k, n, 0))", ["n**2 = 4"]), _sol("-3"),
         UNK, None),
        # a Product: Π_{k=1}^{-2} (k + 10) is 1/90 (Karr), 1 (empty product)
        ("n^2 = 4: Product(k + 10, (k, 1, n)) = 132", ev("Product(k + 10, (k, 1, n))", ["n**2 = 4"]), _sol("132"),
         UNK, None),
        ("n^2 = 4: Product(k + 10, (k, 1, n)) = 1/90", ev("Product(k + 10, (k, 1, n))", ["n**2 = 4"]),
         _sol("1/90"), NOTOK, None),
        # a constraint, not a given
        ("constraint n^2 = 4: Sum = 3", ev(S, [], [{"name": "k", "domain": "integer"},
                                                   {"name": "n", "domain": "integer", "constraints": ["n**2 = 4"]}]),
         _sol("3"), UNK, None),
        # two givens: an equation and an inequality that leaves the reversed root in
        ("n^2 = 4, n < 3: Sum = 3", ev(S, ["n**2 = 4", "n < 3"]), _sol("3"), UNK, None),
        # the range in a second symbol
        ("m = n - 1, n^2 = 4: Sum(k,(k,1,m)) = 1", ev("Sum(k, (k, 1, m))", ["m = n - 1", "n**2 = 4"],
                                                      KN + [{"name": "m", "domain": "integer"}]), _sol("1"), UNK, None),
        # constraints that confine n to finitely many values, some reversed: candidates
        ("constraint n^2 = 4: Sum = n + 1", ev(S, [], [{"name": "k", "domain": "integer"},
                                                       {"name": "n", "domain": "integer", "constraints": ["n**2 = 4"]}]),
         _sol("n + 1"), UNK, None),
        ("constraint -5 <= n <= 5: Sum = n(n+1)/2", ev(S, [], [{"name": "k", "domain": "integer"},
                                                               {"name": "n", "domain": "integer",
                                                                "constraints": ["n >= -5", "n <= 5"]}]),
         _sol("n*(n + 1)/2"), UNK, None),
        ("n = -2, x = 1: x + Sum = 2 (Karr)", ev(f"x + {S}", ["n = -2", "x = 1"], KN + [{"name": "x"}]), _sol("2"),
         UNK, None),
        # the lower bound fixed by a given: n = 4 is the empty sum (0), n = -4 runs backwards
        ("m = 5, n^2 = 16: Sum(k,(k,m,n)) = 0", ev("Sum(k, (k, m, n))", ["m = 5", "n**2 = 16"],
                                                   KN + [{"name": "m", "domain": "integer"}]), _sol("0"), UNK, None),
        # other bounds: floor(-2/2) = -1 and (-2)**3 = -8 run backwards
        ("n^2 = 4: Sum(k,(k,1,floor(n/2))) = 1", ev("Sum(k, (k, 1, floor(n/2)))", ["n**2 = 4"]), _sol("1"), UNK, None),
        ("n^2 = 4: Sum(k,(k,1,n**3)) = 36", ev("Sum(k, (k, 1, n**3))", ["n**2 = 4"]), _sol("36"), UNK, None),
    ]


def cases_b():
    return [
        # Karr's n(n + 1)/2 = 6 has the root -4; the empty sum is 0 there
        ("solve Sum = 6 -> {3}", solve(f"{S} = 6"), _sol("{3}", "set"), UNK, None),
        ("solve Sum = 6 -> {-4, 3}", solve(f"{S} = 6"), _sol("{-4, 3}", "set"), UNK, None),
        ("solve Sum = 0 -> {0}", solve(f"{S} = 0"), _sol("{0}", "set"), UNK, None),
        ("solve Sum = 0 -> {-1, 0}", solve(f"{S} = 0"), _sol("{-1, 0}", "set"), UNK, None),
        ("solve Sum = 10 -> {4}", solve(f"{S} = 10"), _sol("{4}", "set"), UNK, None),
        # the Sum cancels as written: n = -2 makes the equation true under any value of the sum
        ("solve n^2 - 4 + Sum - Sum = 0 -> {2}", solve(f"n**2 - 4 + {S} - {S} = 0"), _sol("{2}", "set"), UNK, None),
        ("solve n^2 - 4 + Sum - Sum = 0 -> {-2, 2}", solve(f"n**2 - 4 + {S} - {S} = 0"), _sol("{-2, 2}", "set"),
         UNK, None),
        ("solve n^2 = 4 + Sum - Sum -> {2}", solve(f"n**2 = 4 + {S} - {S}"), _sol("{2}", "set"), UNK, None),
        ("solve n^2 = 4 + Sum - Sum (n undeclared) -> {2}", solve(f"n**2 = 4 + {S} - {S}", KU), _sol("{2}", "set"),
         UNK, None),
        ("solve n^2 = 4 + Product - Product -> {2}",
         solve("n**2 = 4 + Product(k + 10, (k, 1, n)) - Product(k + 10, (k, 1, n))"), _sol("{2}", "set"), UNK, None),
        ("solve (n - 2)(n + 3) = Sum - Sum -> {2}", solve(f"(n - 2)*(n + 3) = {S} - {S}"), _sol("{2}", "set"),
         UNK, None),
        ("count roots n^2 - 4 + Sum - Sum", _ir("count_roots", {"var": "n", "expr": f"n**2 - 4 + {S} - {S}"}, KN),
         _sol("1", "count"), UNK, None),
        ("count roots n^2 - 4 + Sum - Sum (2)", _ir("count_roots", {"var": "n", "expr": f"n**2 - 4 + {S} - {S}"}, KN),
         _sol("2", "count"), NOTOK, None),
        ("domain_of Sum(k,(k,1,n)), n integer", _ir("domain_of", {"var": "n", "expr": S}, KN, shape="set"),
         _sol("Range(0, oo)", "set"), UNK, None),
        # an equation in x, the range reversed for certain by the given n = -2
        ("solve x: x + Sum = 0, n = -2 -> EmptySet", _ir("solve_equation", {"var": "x", "equation": f"x + {S} = 0"},
                                                         KN + [{"name": "x"}], ["n = -2"], "set"),
         _sol("EmptySet", "set"), UNK, None),
        ("solve x: x + Sum = 0, n = -2 -> {-1} (Karr)",
         _ir("solve_equation", {"var": "x", "equation": f"x + {S} = 0"}, KN + [{"name": "x"}], ["n = -2"], "set"),
         _sol("{-1}", "set"), UNK, None),
        ("solve x: x + Sum = 0, n = -2 -> {0} (empty)",
         _ir("solve_equation", {"var": "x", "equation": f"x + {S} = 0"}, KN + [{"name": "x"}], ["n = -2"], "set"),
         _sol("{0}", "set"), UNK, None),
        ("solve_inequality n: n^2 < 5 + Sum - Sum -> {-2..2}",
         _ir("solve_inequality", {"var": "n", "inequality": f"n**2 < 5 + {S} - {S}"}, KN, shape="set"),
         _sol("{-2, -1, 0, 1, 2}", "set"), UNK, None),
        ("solve_inequality n: n^2 < 5 + Sum - Sum -> {0, 1, 2}",
         _ir("solve_inequality", {"var": "n", "inequality": f"n**2 < 5 + {S} - {S}"}, KN, shape="set"),
         _sol("{0, 1, 2}", "set"), UNK, None),
    ]


def cases_c():
    s_ir = ev("n**2", ["n**2 = 4"])
    return [
        ("steps: n^2 = 4, eq n = 2, compute Sum = 3; task Sum", ev(S, ["n**2 = 4"]),
         _sol("3", steps=[("eq", "n = 2"), ("compute", f"{S} = 3")]), UNK, None),
        ("step Sum = 1 at n = -2 (Karr)", ev("n**2", ["n = -2"]),
         _sol("4", steps=[("compute", f"{S} = 1")]), ANY, NOT_VERIFIED),
        ("step Sum = 0 at n = -2 (empty sum)", ev("n**2", ["n = -2"]),
         _sol("4", steps=[("compute", f"{S} = 0")]), ANY, NOT_VERIFIED),
        ("step Sum = 0 at n = 0 (empty, defined)", ev("n**2", ["n = 0"]),
         _sol("0", steps=[("compute", f"{S} = 0")]), ANY, {"verified"}),
        ("step Sum = 6 at n = 3", ev("n**2", ["n = 3"]),
         _sol("9", steps=[("compute", f"{S} = 6")]), ANY, {"verified"}),
        ("step Sum = n(n+1)/2 (identity), n^2 = 4", s_ir,
         _sol("4", steps=[("compute", f"{S} = n*(n + 1)/2")]), ANY, None),
        # n = 2 from n**2 = 4 holds only with n = -2 dropped (task Sum: the range is the problem's). The step
        # stays "verified" (the steps' domain leaves the reversed point out): made "unknown", it no longer
        # pins n for a later `compute` step, which is then refuted as an identity at n = 108, no instance
        # of n**2 = 4 (an older gap, outside this part) - the first case of this group would go INCORRECT
        ("step eq n = 2 from n^2 = 4 (task Sum)", ev(S, ["n**2 = 4"]), _sol("3", steps=[("eq", "n = 2")]), UNK,
         None),
        ("step eq n = 2 from n^2 = 4, n > 0 (task Sum)", ev(S, ["n**2 = 4", "n > 0"]),
         _sol("3", steps=[("eq", "n = 2")]), OK, {"verified"}),
        ("step eq n = 2 from n^2 = 4 (pos n, task Sum)", ev(S, ["n**2 = 4"], KP),
         _sol("3", steps=[("eq", "n = 2")]), OK, {"verified"}),
        ("step eq n = 2 from n^2 = 4 (task n + 1, no Sum)", ev("n + 1", ["n**2 = 4"]),
         _sol("3", steps=[("eq", "n = 2")]), NOTOK, {"refuted"}),
    ]


def cases_d():
    return [
        ("n = 3: Sum = 6", ev(S, ["n = 3"]), _sol("6"), OK, None),
        ("n = 3: Sum = 5", ev(S, ["n = 3"]), _sol("5"), NO, None),
        ("n = 0: Sum = 0 (empty)", ev(S, ["n = 0"]), _sol("0"), OK, None),
        ("n = 0: Sum = 1", ev(S, ["n = 0"]), _sol("1"), NO, None),
        ("n = -1: Sum = 0 (reversed)", ev(S, ["n = -1"]), _sol("0"), UNK, None),
        ("n = -2: Sum = 1 (Karr)", ev(S, ["n = -2"]), _sol("1"), UNK, None),
        ("n = -2: Sum = 0 (empty)", ev(S, ["n = -2"]), _sol("0"), UNK, None),
        ("n^2 = 4, n > 0: Sum = 3", ev(S, ["n**2 = 4", "n > 0"]), _sol("3"), OK, None),
        ("n^2 = 4, n > 0: Sum = 1", ev(S, ["n**2 = 4", "n > 0"]), _sol("1"), NO, None),
        ("n^2 = 4, n >= 0: Sum = 3", ev(S, ["n**2 = 4", "n >= 0"]), _sol("3"), OK, None),
        ("pos n, n^2 = 4: Sum = 3", ev(S, ["n**2 = 4"], KP), _sol("3"), OK, None),
        ("nonneg n, n^2 = 4: Sum = 3", ev(S, ["n**2 = 4"], K0), _sol("3"), OK, None),
        ("pos n = 3: Sum = 6", ev(S, ["n = 3"], KP), _sol("6"), OK, None),
        ("undeclared n = 3: Sum = 6", ev(S, ["n = 3"], KU), _sol("6"), OK, None),
        ("n^2 = 4: Sum(k,(k,1,n**2)) = 10 (never reversed)", ev("Sum(k, (k, 1, n**2))", ["n**2 = 4"]), _sol("10"),
         OK, None),
        ("n^2 = 4: Sum(k,(k,1,Abs(n))) = 3 (never reversed)", ev("Sum(k, (k, 1, Abs(n)))", ["n**2 = 4"]), _sol("3"),
         OK, None),
        ("n = 4: Sum(k,(k,1,floor(n/2))) = 3", ev("Sum(k, (k, 1, floor(n/2)))", ["n = 4"]), _sol("3"), OK, None),
        ("n = -5: Sum(k,(k,n,n+2)) = -12", ev("Sum(k, (k, n, n + 2))", ["n = -5"]), _sol("-12"), OK, None),
        ("n(n - 3) = 0: Sum: two values 0 and 6", ev(S, ["n*(n - 3) = 0"]), _sol("6"), UNK, None),
        ("n^2 = 4: n**2 + 1 = 5 (no Sum)", ev("n**2 + 1", ["n**2 = 4"]), _sol("5"), OK, None),
        ("n = 2: Product(k,(k,3,n)) = 1 (empty)", ev("Product(k, (k, 3, n))", ["n = 2"]), _sol("1"), OK, None),
        ("m = 5, n = 4: Sum(k,(k,m,n)) = 0 (empty)", ev("Sum(k, (k, m, n))", ["m = 5", "n = 4"],
                                                        KN + [{"name": "m", "domain": "integer"}]), _sol("0"), OK, None),
        ("m = 5, n = 6: Sum(k,(k,m,n)) = 11", ev("Sum(k, (k, m, n))", ["m = 5", "n = 6"],
                                                 KN + [{"name": "m", "domain": "integer"}]), _sol("11"), OK, None),
        ("constraint 0 <= n <= 5: Sum = n(n+1)/2", ev(S, [], [{"name": "k", "domain": "integer"},
                                                              {"name": "n", "domain": "integer",
                                                               "constraints": ["n >= 0", "n <= 5"]}]),
         _sol("n*(n + 1)/2"), OK, None),
        ("n = 1: Product(k,(k,3,n)) = 1 (reversed)", ev("Product(k, (k, 3, n))", ["n = 1"]), _sol("1"), UNK, None),
        ("n = 3: Product(k,(k,1,n)) = 6", ev("Product(k, (k, 1, n))", ["n = 3"]), _sol("6"), OK, None),
        ("no given: Sum = n(n+1)/2 (int)", ev(S), _sol("n*(n + 1)/2"), OK, None),
        ("no given: Sum = n^2/2 (int)", ev(S), _sol("n**2/2"), NO, None),
        ("no given: Sum = n(n+1)/2 (pos)", ev(S, (), KP), _sol("n*(n + 1)/2"), OK, None),
        ("no given: Sum = n(n+1)/2 (undeclared)", ev(S, (), KU), _sol("n*(n + 1)/2"), OK, None),
        ("simplify Sum = n(n+1)/2 (int)", _ir("simplify_expression", {"expr": S}, KN), _sol("n*(n + 1)/2"), OK, None),
        ("solve Sum = 6 (pos n) -> {3}", solve(f"{S} = 6", KP), _sol("{3}", "set"), UNK, None),
        ("solve n^2 = 4 + Sum - Sum (pos n) -> {2}", solve(f"n**2 = 4 + {S} - {S}", KP), _sol("{2}", "set"), OK, None),
        ("solve n^2 = 4 + Sum - Sum, n > 0 -> {2}", solve(f"n**2 = 4 + {S} - {S}", KN, ["n > 0"]),
         _sol("{2}", "set"), OK, None),
        ("count roots n^2 - 4 + Sum - Sum, n > 0", _ir("count_roots", {"var": "n", "expr": f"n**2 - 4 + {S} - {S}"},
                                                       KN, ["n > 0"]), _sol("1", "count"), OK, None),
        ("solve n^2 = 4 + Sum - Sum (pos n) -> {-2, 2}", solve(f"n**2 = 4 + {S} - {S}", KP), _sol("{-2, 2}", "set"),
         NOTOK, None),
        ("solve x: x + Sum = 0, n = 3 -> {-6}",
         _ir("solve_equation", {"var": "x", "equation": f"x + {S} = 0"}, KN + [{"name": "x"}], ["n = 3"], "set"),
         _sol("{-6}", "set"), UNK, None),
        ("Sum(1/k^2, 1..oo) = pi^2/6", ev("Sum(1/k**2, (k, 1, oo))"), _sol("pi**2/6"), OK, None),
        ("Sum(2^k, -oo..n), n = 0: 2", ev("Sum(2**k, (k, -oo, n))", ["n = 0"]), _sol("2"), OK, None),
        ("nested inner reversed numeric: 0 (Karr)", ev("Sum(Sum(1, (j, k, 2)), (k, 1, 5))", [], KJN), _sol("0"),
         UNK, None),
        ("x^2 = 4 (real x): x = 2 root (no Sum)", _ir("solve_equation", {"var": "x", "equation": "x**2 = 4"},
                                                     [{"name": "x"}], shape="set"), _sol("{-2, 2}", "set"), OK, None),
        ("gcd: (x - pi - E)(x - 1/2) = gcd - gcd -> {1/2}",
         _ir("solve_equation", {"var": "x", "equation": "(x - pi - E)*(x - 1/2) = gcd(x, 2) - gcd(2, x)"},
             [{"name": "x"}], shape="set"), _sol("{1/2}", "set"), NOTOK, None),
    ]


def cases_e():
    # a solution neither kept nor dropped counts only when the given inequalities do not exclude it: B's
    # gcd/factorial membership (V16) used to make the verdict UNKNOWN before the inequalities were read
    X = [{"name": "x"}]
    g = "x + gcd(x, 2) - gcd(2, x)"
    return [
        ("gcd: (x - pi - E)(x - 1/2) = 0, x < 1: value 1/2", ev(g, ["(x - pi - E)*(x - 1/2) = 0", "x < 1"], X),
         _sol("1/2"), OK, None),
        ("gcd: (x - pi - E)(x - 1/2) = 0, x < 1: value 1", ev(g, ["(x - pi - E)*(x - 1/2) = 0", "x < 1"], X),
         _sol("1"), NO, None),
        ("gcd: (x - pi - E)(x - 1/2) = 0: value 1/2 (pi + E undecided)", ev(g, ["(x - pi - E)*(x - 1/2) = 0"], X),
         _sol("1/2"), UNK, None),
        ("factorial: (x + 3)(x - 2) = 0, x > 0: x + x! - x! = 2",
         ev("x + factorial(x) - factorial(x)", ["(x + 3)*(x - 2) = 0", "x > 0"], X), _sol("2"), OK, None),
    ]


def cases_f():
    # the range inside a problem function, called at a point (Ctx._function_call_conditions)
    def fx(expr, givens=(), kind="evaluate", params=None, shape="scalar"):
        d = _ir(kind, params or {"expr": expr}, KN + [{"name": "x"}], givens, shape)
        d["functions"] = [{"name": "f", "expr": S, "args": ["n"]}]
        return d
    return [
        ("f(n) = Sum: f(-2) = 1 (Karr)", fx("f(-2)"), _sol("1"), UNK, None),
        ("f(n) = Sum: f(-2) = 0 (empty)", fx("f(-2)"), _sol("0"), UNK, None),
        ("f(n) = Sum: f(-1) = 0", fx("f(-1)"), _sol("0"), UNK, None),
        ("f(n) = Sum: f(3) = 6", fx("f(3)"), _sol("6"), OK, None),
        ("f(n) = Sum: f(0) = 0 (empty)", fx("f(0)"), _sol("0"), OK, None),
        ("f(n) = Sum: f(n), n^2 = 4: 3", fx("f(n)", ["n**2 = 4"]), _sol("3"), UNK, None),
        ("f(n) = Sum: f(n), n = 3: 6", fx("f(n)", ["n = 3"]), _sol("6"), OK, None),
        ("f(n) = Sum: solve f(n) = 6 -> {3}", fx(None, kind="solve_equation", shape="set",
                                                  params={"var": "n", "equation": "f(n) = 6"}), _sol("{3}", "set"),
         UNK, None),
        ("f(n) = Sum: solve n^2 = 4 + f(n) - f(n) -> {2}",
         fx(None, kind="solve_equation", shape="set", params={"var": "n", "equation": "n**2 = 4 + f(n) - f(n)"}),
         _sol("{2}", "set"), UNK, None),
        # a call reversed for certain next to a free variable: the call's condition has no symbol left
        ("f(n) = Sum: solve x: x + f(-2) = 0 -> {-1} (Karr)",
         fx(None, kind="solve_equation", shape="set", params={"var": "x", "equation": "x + f(-2) = 0"}),
         _sol("{-1}", "set"), UNK, None),
        ("f(n) = Sum: solve x: x + f(-2) = 0 -> EmptySet",
         fx(None, kind="solve_equation", shape="set", params={"var": "x", "equation": "x + f(-2) = 0"}),
         _sol("EmptySet", "set"), UNK, None),
        ("f(n) = Sum: evaluate x + f(-2), x = 1: 2 (Karr)", fx("x + f(-2)", ["x = 1"]), _sol("2"), UNK, None),
        ("f(n) = Sum: solve x: x + f(3) = 0 -> {-6}",
         fx(None, kind="solve_equation", shape="set", params={"var": "x", "equation": "x + f(3) = 0"}),
         _sol("{-6}", "set"), OK, None),
    ]


GROUPS = {"A": cases_a, "B": cases_b, "C": cases_c, "D": cases_d, "E": cases_e, "F": cases_f}


def _summ(r):
    lay, steps = [], []
    for l in r.layers:
        e = l.evidence or {}
        reason = e.get("reason") or ""
        lay.append(f"{l.layer}:{l.verdict}{'(' + str(reason)[:120] + ')' if reason else ''}")
        if l.layer == "steps.refute":
            for s in e.get("steps", []):
                steps.append((s.get("id"), s.get("status"),
                              str(s.get("reason") or (s.get("evidence") or {}).get("reason") or "")[:80]))
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
            for x in lay[:5]:
                print(f"      {x}", flush=True)
            for s in steps:
                print(f"      step {s[0]}:{s[1]}:{s[2]}", flush=True)
    print(f"\n{len(rows)} cases, {bad} not as expected")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
