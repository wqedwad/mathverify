"""Part d4f of the fourth audit's fixes (6 Oct 2026): definedness (findings CAP-F1 of the `capraz` angle, TAN-10,
TAN-12 of the `tanimlilik` angle, C1, B1 of the `ayristirici` angle and G14 of the `gorev` angle,
`denetim/2026-10-01/d4/`).

    A  CAP-F1  a closed operation with no value ((-1)!, (-2)!, Γ(0), zoo): SymPy's 1/zoo = 0 is no value on any
               path (the problem's texts, a given, a function body, a point, a bound, an interval, the claim, a
               step): never CORRECT, a step never verified, an equation around it not "defined nowhere"
    B  CAP-F1  the rules that raised on a pole (a reciprocal, an even root, log, tan, asin/acos, an odd root,
               0**0, Mod) and the factorial family (n!!, Γ, P, C)
    C  TAN-10, C1  Sum/Product limits an integer apart but not integers (1/2 .. 5/2): 9/2 stepping, 3 over the
               integers; neither CORRECT nor INCORRECT, a step neither verified nor refuted
    D  B1      a LaTeX reversed constant range whatever the index is called or how the '=' is spaced
    E  TAN-12  an inner range that names the outer index: decided at each outer value when the outer range is
               finite (n = 3); undecided otherwise, and then not called undefined
    F  G14     a limit at oo of a sequence reads the definedness of its tail only ((x - 2)!, C(x, 3))
    K  controls whose verdict must not change

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> MATHVERIFY_LEAN_REPL=/nonexistent \\
        .venv/bin/python denetim/2026-10-01/d4f/sonda.py [out.json] [groups]

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
NOTVER = {"refuted", "unknown", "skipped", None}
NEITHER = {"unknown", "skipped", None}    # neither verified nor refuted

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_integer"}
XI = {"name": "x", "domain": "integer"}
K = {"name": "k", "domain": "integer"}
N = {"name": "n", "domain": "integer"}
J = {"name": "j", "domain": "integer"}
UNDEF = "problem_undefined_as_written"


def ir(kind, params, givens=(), vars_=None, shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def sol(payload, kind="value", steps=()):
    return {"claimed_answer": {"kind": kind, "payload": payload},
            "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                      for i, (k, c) in enumerate(steps)]}


def ev(expr, givens=(), vars_=None, functions=None):
    return ir("evaluate", {"expr": expr}, givens, vars_, functions=functions)


def step(claim, kind="compute", vars_=None, givens=("x = 1",)):
    """A step next to a right answer (x = 1): only the step's status is asked."""
    return ev("x", givens, vars_), sol("1", steps=[(kind, claim)])


def cases_a():
    out = []
    for e, v in (("1/factorial(-1)", "0"), (r"\frac{5!}{(-2)!}", "0"), ("factorial(4)/factorial(-1)", "0"),
                 ("1/factorial(-3) + 2", "2"), ("sqrt(1/factorial(-1))", "0"), ("exp(1/factorial(-1))", "1"),
                 ("3/factorial(-4)", "0"), ("7 - 2/factorial(-2)", "7"), (r"\frac{1}{(-3)!}", "0"),
                 ("cos(1/factorial(-1))", "1"), ("factorial(-1)**(-2)", "0"), ("1/sqrt(factorial(-2))", "0"),
                 ("asin(1/factorial(-1))", "0"), ("1/zoo", "0"), ("2 + 0*zoo", "2"), (r"\frac{1}{\Gamma(0)}", "0"),
                 (r"\frac{1}{\Gamma(-2)}", "0"), (r"\frac{1}{\gamma(0)}", "0"), (r"\frac{1}{(-1)!!}", "0"),
                 ("P(2, 3)", "0"), ("1/binomial(-1, 1/2)", "0")):
        out.append((f"evaluate {e} -> {v}", ev(e), sol(v), UNK, None))
    X3 = ["x = 3"]
    out += [
        ("x + 1/factorial(-1), x = 3 -> 3", ev("x + 1/factorial(-1)", X3), sol("3"), UNK, None),
        ("given n = 1/factorial(-1): n + 1 -> 1", ev("n + 1", ["n = 1/factorial(-1)"], [{"name": "n"}]), sol("1"),
         UNK, None),
        ("given y = 2/factorial(-5): y + 1 -> 1", ev("y + 1", ["y = 2/factorial(-5)"], [{"name": "y"}]), sol("1"),
         UNK, None),
        ("solve x + 1/factorial(-1) = 2 -> {2}", ir("solve_equation", {"var": "x", "equation": "x + 1/factorial(-1) = 2"},
                                                     shape="set"), sol("{2}", "set"), UNK, None),
        ("solve x + 1/factorial(-1) = 2 -> {} (not defined nowhere)",
         ir("solve_equation", {"var": "x", "equation": "x + 1/factorial(-1) = 2"}, shape="set"), sol("EmptySet", "set"),
         UNK, None),
        ("solve given 2x = 4 + 1/factorial(-2) -> {2}", ir("solve_equation", {"var": "x"}, ["2*x = 4 + 1/factorial(-2)"],
                                                          shape="set"), sol("{2}", "set"), UNK, None),
        ("ineq x - 1/factorial(-1) > 1 -> (1, oo)", ir("solve_inequality", {"var": "x", "inequality": "x - 1/factorial(-1) > 1"},
                                                       shape="interval"), sol("(1, oo)", "interval"), UNK, None),
        ("simplify x + 1/factorial(-1) -> x", ir("simplify_expression", {"expr": "x + 1/factorial(-1)"}, shape="expression"),
         sol("x", "expression"), UNK, None),
        ("derivative x**2 + 1/factorial(-1) at 1 -> 2", ir("derivative", {"f": "x**2 + 1/factorial(-1)", "var": "x", "at": "1"}),
         sol("2"), UNK, None),
        ("integral x + 1/factorial(-2) on [0, 1] -> 1/2",
         ir("definite_integral", {"integrand": "x + 1/factorial(-2)", "var": "x", "a": "0", "b": "1"}), sol("1/2"), UNK, None),
        ("series k + 1/factorial(-1), k = 1..3 -> 6",
         ir("series_sum", {"term": "k + 1/factorial(-1)", "var": "k", "lo": "1", "hi": "3"}, vars_=[K]), sol("6"), UNK, None),
        ("extremum max x + 1/factorial(-1) on [0, 2] -> 2",
         ir("extremum", {"f": "x + 1/factorial(-1)", "var": "x", "interval": "[0, 2]", "which": "max"}), sol("2"), UNK, None),
        ("limit x + 1/factorial(-1), x -> 2 -> 2", ir("limit", {"expr": "x + 1/factorial(-1)", "var": "x", "to": "2"}),
         sol("2"), UNK, None),
        ("limit x/factorial(-1), x -> 1 -> 0", ir("limit", {"expr": "x/factorial(-1)", "var": "x", "to": "1"}), sol("0"),
         UNK, None),
        ("count_roots x**2 - 1 + 1/factorial(-1) -> 2", ir("count_roots", {"expr": "x**2 - 1 + 1/factorial(-1)", "var": "x"},
                                                             shape="count"), sol(2, "count"), UNK, None),
        ("domain_of x + 1/factorial(-1) -> R", ir("domain_of", {"expr": "x + 1/factorial(-1)", "var": "x"}, shape="set"),
         sol("Reals", "set"), UNK, None),
        ("function f(x) = x + 1/factorial(-1): f(2) -> 2",
         ev("f(2)", functions=[{"name": "f", "args": ["x"], "expr": "x + 1/factorial(-1)"}]), sol("2"), UNK, None),
        ("function f(x) = 1/factorial(x): f(-1) -> 0",
         ev("f(-1)", functions=[{"name": "f", "args": ["x"], "expr": "1/factorial(x)"}]), sol("0"), UNK, None),
        # every other text: a point, a bound, an interval
        ("derivative x**2 at 1/factorial(-1) -> 0", ir("derivative", {"f": "x**2", "var": "x", "at": "1/factorial(-1)"}),
         sol("0"), UNK, None),
        ("limit x + 1 at x -> 1/factorial(-1) -> 1", ir("limit", {"expr": "x + 1", "var": "x", "to": "1/factorial(-1)"}),
         sol("1"), UNK, None),
        ("extremum min x on [1/factorial(-1), 1] -> 0",
         ir("extremum", {"f": "x", "var": "x", "interval": "[1/factorial(-1), 1]", "which": "min"}), sol("0"), UNK, None),
        ("extremum min x on [1/(1/0), 1] -> 0",
         ir("extremum", {"f": "x", "var": "x", "interval": "[1/(1/0), 1]", "which": "min"}), sol("0"), UNK, None),
        ("extremum min x on [1/(1/0), 1) -> 0",
         ir("extremum", {"f": "x", "var": "x", "interval": "[1/(1/0), 1)", "which": "min"}), sol("0"), UNK, None),
        ("extremum min x on Interval(1/factorial(-1), 1) -> 0",
         ir("extremum", {"f": "x", "var": "x", "interval": "Interval(1/factorial(-1), 1)", "which": "min"}), sol("0"),
         UNK, None),
        ("domain of discourse Interval.open(1/factorial(-1), oo): x**2 = 4 -> {2}",
         dict(ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, shape="set"),
              domain_of_discourse="Interval.open(1/factorial(-1), oo)"), sol("{2}", "set"), UNK, None),
        ("claim Interval(1/factorial(-1), 2) for x(x - 2) <= 0",
         ir("solve_inequality", {"inequality": "x*(x - 2) <= 0", "var": "x"}, shape="interval"),
         sol("Interval(1/factorial(-1), 2)", "interval"), UNK, None),
        ("claim [1/(1/0), 1] U [1, 2] for x(x - 2) <= 0",
         ir("solve_inequality", {"inequality": "x*(x - 2) <= 0", "var": "x"}, shape="interval"),
         sol("[1/(1/0), 1] U [1, 2]", "interval"), UNK, None),
        ("claim Interval(0, 2) for x(x - 2) <= 0 (control)",
         ir("solve_inequality", {"inequality": "x*(x - 2) <= 0", "var": "x"}, shape="interval"),
         sol("Interval(0, 2)", "interval"), OK, None),
        ("integral of 1 from 1/factorial(-1) to 1 -> 1",
         ir("definite_integral", {"integrand": "1", "var": "x", "a": "1/factorial(-1)", "b": "1"}), sol("1"), UNK, None),
        ("series k, k = 1 + 1/factorial(-1) .. 3 -> 6",
         ir("series_sum", {"term": "k", "var": "k", "lo": "1 + 1/factorial(-1)", "hi": "3"}, vars_=[K]), sol("6"), UNK, None),
        ("constraint x > 1/factorial(-1): solve x**2 = 4 -> {2}",
         ir("solve_equation", {"var": "x", "equation": "x**2 = 4"}, vars_=[{"name": "x", "constraints": ["x > 1/factorial(-1)"]}],
            shape="set"), sol("{2}", "set"), UNK, None),
        # the claim
        ("claim 1/factorial(-1) for 0", ev("0"), sol("1/factorial(-1)"), UNK, None),
        ("claim 1/zoo for 0", ev("0"), sol("1/zoo"), UNK, None),
        ("claim 2 + 1/factorial(-2) for 2", ev("2"), sol("2 + 1/factorial(-2)"), UNK, None),
        ("claim 1/(1/0) for 0", ev("0"), sol("1/(1/0)"), UNK, None),
        (r"claim \frac{1}{(-1)!} for 0", ev("0"), sol(r"\frac{1}{(-1)!}"), UNK, None),
        ("claim {1/factorial(-1)} for x**2 = 0", ir("solve_equation", {"var": "x", "equation": "x**2 = 0"}, shape="set"),
         sol("{1/factorial(-1)}", "set"), UNK, None),
        # the steps
        ("step 1/factorial(-1) = 0", *step("1/factorial(-1) = 0"), OK, NEITHER),
        ("step 4/factorial(-2) = 0", *step("4/factorial(-2) = 0"), OK, NEITHER),
        ("step eq 1/factorial(-1) = 0", *step("1/factorial(-1) = 0", "eq"), OK, NEITHER),
        ("step y = 1/factorial(-1) with y = 0", ev("y", ["y = 0"], [{"name": "y"}]),
         sol("0", steps=[("eq", "y = 1/factorial(-1)")]), OK, NEITHER),
        ("step 1/zoo = 0", *step("1/zoo = 0"), OK, NEITHER),
        (r"step \frac{1}{\Gamma(0)} = 0", *step(r"\frac{1}{\Gamma(0)} = 0"), OK, NEITHER),
        ("step Sum(1/factorial(k - 3), (k, 1, 4)) = 2", *step("Sum(1/factorial(k - 3), (k, 1, 4)) = 2", vars_=[X, K]), OK,
         NEITHER),
    ]
    return out


def cases_b():
    out = []
    for e, v in (("tan(1/factorial(-1))", "0"), ("log(2 + 1/factorial(-1))", "log(2)"), ("acos(1/factorial(-1))", "pi/2"),
                 ("(1/factorial(-1))**(1/3)", "0"), ("(1/factorial(-1))**0", "1"), ("Mod(5, 2 + 1/factorial(-1))", "1"),
                 ("sqrt(factorial(-2))*0 + 1", "1"), ("log(factorial(-1))*0", "0"), ("sec(1/factorial(-1))", "1"),
                 ("Sum(1/factorial(k - 3), (k, 1, 4))", "2"), ("Sum(1/factorial(k), (k, -2, 2))", "5/2"),
                 ("Integral(x/factorial(-1) + 1, (x, 0, 1))", "1"), ("1/factorial(1/2)", "2/sqrt(pi)"),
                 ("1/factorial(-1/2)", "1/sqrt(pi)")):
        out.append((f"evaluate {e} -> {v}", ev(e, vars_=[X, K]), sol(v), UNK, None))
    out += [
        ("limit 1/factorial(-1) + 1/x at oo -> 0", ir("limit", {"expr": "1/factorial(-1) + 1/x", "var": "x", "to": "oo"}),
         sol("0"), UNK, None),
        ("solve x + Sum(1/factorial(k - 3), (k, 1, 4)) = 2 -> {}",
         ir("solve_equation", {"var": "x", "equation": "x + Sum(1/factorial(k - 3), (k, 1, 4)) = 2"}, vars_=[X, K], shape="set"),
         sol("EmptySet", "set"), UNK, None),
        ("solve x + 1/factorial(1/2) = 2 -> {}",
         ir("solve_equation", {"var": "x", "equation": "x + 1/factorial(1/2) = 2"}, shape="set"), sol("EmptySet", "set"),
         UNK, None),
    ]
    return out


def cases_c():
    out = []
    for e in ("Sum(k, (k, 1/2, 5/2))", r"\sum_{k=1/2}^{5/2} k", r"\sum_{k=\frac{1}{2}}^{\frac{5}{2}} k",
              r"\sum_{k=0.5}^{2.5} k", "Sum(k, (k, 0.5, 2.5))", "Sum(k, (k, Rational(1, 2), Rational(5, 2)))"):
        out.append((f"{e} -> 9/2", ev(e, vars_=[K]), sol("9/2"), UNK, None))
        out.append((f"{e} -> 3", ev(e, vars_=[K]), sol("3"), UNK, None))
    out += [
        ("Sum(1, (k, 1/2, 5/2)) -> 3", ev("Sum(1, (k, 1/2, 5/2))", vars_=[K]), sol("3"), UNK, None),
        ("Sum(1, (k, 1/2, 5/2)) -> 2", ev("Sum(1, (k, 1/2, 5/2))", vars_=[K]), sol("2"), UNK, None),
        ("Product(k, (k, 1/2, 5/2)) -> 15/8", ev("Product(k, (k, 1/2, 5/2))", vars_=[K]), sol("15/8"), UNK, None),
        ("Product(k, (k, 1/2, 5/2)) -> 2", ev("Product(k, (k, 1/2, 5/2))", vars_=[K]), sol("2"), UNK, None),
        ("Sum(k**2, (k, sqrt(2), sqrt(2) + 1)) -> 5 + 2*sqrt(2)", ev("Sum(k**2, (k, sqrt(2), sqrt(2) + 1))", vars_=[K]),
         sol("5 + 2*sqrt(2)"), UNK, None),
        ("Sum(k**2, (k, sqrt(2), sqrt(2) + 1)) -> 4", ev("Sum(k**2, (k, sqrt(2), sqrt(2) + 1))", vars_=[K]), sol("4"),
         UNK, None),
        ("Sum(k, (k, pi, pi + 1)) -> 2*pi + 1", ev("Sum(k, (k, pi, pi + 1))", vars_=[K]), sol("2*pi + 1"), UNK, None),
        ("Sum(k, (k, 1/3, 7/3)) -> 4", ev("Sum(k, (k, 1/3, 7/3))", vars_=[K]), sol("4"), UNK, None),
        ("Sum(2**k, (k, 1/2, 3/2)) -> 3*sqrt(2)", ev("Sum(2**k, (k, 1/2, 3/2))", vars_=[K]), sol("3*sqrt(2)"), UNK, None),
        ("floor(Sum(k, (k, 1/2, 5/2))) -> 4", ev("floor(Sum(k, (k, 1/2, 5/2)))", vars_=[K]), sol("4"), UNK, None),
        ("Sum(1/k**2, (k, 1/2, oo)) -> pi**2/2", ev("Sum(1/k**2, (k, 1/2, oo))", vars_=[K]), sol("pi**2/2"), UNK, None),
        ("Sum(k, (k, -1/2, 1/2)) -> 0 (both readings 0, refused all the same)", ev("Sum(k, (k, -1/2, 1/2))", vars_=[K]),
         sol("0"), UNK, None),
        ("given a = 1/2: Sum(k, (k, a, a + 2)) -> 9/2", ev("Sum(k, (k, a, a + 2))", ["a = 1/2"], [K, {"name": "a"}]),
         sol("9/2"), UNK, None),
        ("given a = 1/2: Sum(k, (k, a, a + 2)) -> 3", ev("Sum(k, (k, a, a + 2))", ["a = 1/2"], [K, {"name": "a"}]),
         sol("3"), UNK, None),
        ("given m = 1/2, n = 5/2: Sum(k, (k, m, n)) -> 9/2",
         ev("Sum(k, (k, m, n))", ["m = 1/2", "n = 5/2"], [K, {"name": "m"}, {"name": "n"}]), sol("9/2"), UNK, None),
        ("given n = 1/2 (real): Sum(k, (k, n, n + 2)) -> 9/2",
         ev("Sum(k, (k, n, n + 2))", ["n = 1/2"], [K, {"name": "n", "domain": "real"}]), sol("9/2"), UNK, None),
        ("limit x + Sum(k, (k, 1/2, 5/2)) at 0 -> 9/2",
         ir("limit", {"expr": "x + Sum(k, (k, 1/2, 5/2))", "var": "x", "to": "0"}, vars_=[X, K]), sol("9/2"), UNK, None),
        ("derivative x*Sum(k, (k, 1/2, 5/2)) at 1 -> 9/2",
         ir("derivative", {"f": "x*Sum(k, (k, 1/2, 5/2))", "var": "x", "at": "1"}, vars_=[X, K]), sol("9/2"), UNK, None),
        ("solve x + Sum(k, (k, 1/2, 5/2)) = 0 -> {-9/2}",
         ir("solve_equation", {"var": "x", "equation": "x + Sum(k, (k, 1/2, 5/2)) = 0"}, vars_=[X, K], shape="set"),
         sol("{-9/2}", "set"), UNK, None),
        ("series_sum k, 1/2 .. 5/2 -> 9/2", ir("series_sum", {"term": "k", "var": "k", "lo": "1/2", "hi": "5/2"}, vars_=[K]),
         sol("9/2"), UNK, None),
        ("series_sum k, 1/2 .. 5/2 -> 3", ir("series_sum", {"term": "k", "var": "k", "lo": "1/2", "hi": "5/2"}, vars_=[K]),
         sol("3"), UNK, None),
        ("series_sum k, a .. a + 2, a = 1/2 -> 9/2",
         ir("series_sum", {"term": "k", "var": "k", "lo": "a", "hi": "a + 2"}, ["a = 1/2"], [K, {"name": "a"}]), sol("9/2"),
         UNK, None),
        ("step Sum(k, (k, 1/2, 5/2)) = 9/2", *step("Sum(k, (k, 1/2, 5/2)) = 9/2", vars_=[X, K]), NOTOK, NEITHER),
        ("step Sum(k, (k, 1/2, 5/2)) = 3", *step("Sum(k, (k, 1/2, 5/2)) = 3", vars_=[X, K]), NOTNO, NEITHER),
        (r"step \sum_{k=1/2}^{5/2} k = 3", *step(r"\sum_{k=1/2}^{5/2} k = 3", vars_=[X, K]), NOTNO, NEITHER),
        ("step Sum(k, (k, a, a + 2)) = 3 with a = 1/2", ev("x", ["x = 1", "a = 1/2"], [X, K, {"name": "a"}]),
         sol("1", steps=[("compute", "Sum(k, (k, a, a + 2)) = 3")]), NOTNO, NEITHER),
    ]
    return out


def cases_d():
    out = []
    for idx in (r"\alpha", r"\theta", r"\lambda", r"\mu", "k_{1}", "j_{0}", r"\mathrm{k}", "k"):
        for lo, hi in (("3", r"\sqrt{1}"), (r"\sqrt{9}", "1"), ("3", "1")):
            for fn, (l_, r_) in (("floor", (r"\lfloor", r"\rfloor")), ("ceil", (r"\lceil", r"\rceil"))):
                e = f"{l_} \\sum_{{{idx}={lo}}}^{{{hi}}} {idx} {r_}"
                out.append((f"{e} -> -2", ev(e), sol("-2"), UNK, None))
    for e in (r"\lfloor \sum_{k\,=\,3}^{\sqrt{1}} k \rfloor", r"\lfloor \sum_{k \; = \; 3}^{\sqrt{1}} k \rfloor",
              r"\lfloor \sum_{k\!=\!3}^{\sqrt{1}} k \rfloor", r"\left| \sum_{\alpha=3}^{\sqrt{1}} \alpha \right|",
              r"\lfloor \prod_{\alpha=3}^{\sqrt{0}} \alpha \rfloor", r"\left| \prod_{\theta=3}^{\sqrt{1}} \theta \right|"):
        out.append((f"{e} -> Karr", ev(e), sol("-2" if "sum" in e else "1/2"), UNK, None))
    out += [
        (r"\lfloor \sum_{\alpha=3}^{\sqrt{1}} \alpha \rfloor -> 0 (empty-sum reading)",
         ev(r"\lfloor \sum_{\alpha=3}^{\sqrt{1}} \alpha \rfloor"), sol("0"), UNK, None),
        (r"step \lfloor \sum_{\alpha=3}^{\sqrt{1}} \alpha \rfloor = 0", *step(r"\lfloor \sum_{\alpha=3}^{\sqrt{1}} \alpha \rfloor = 0"),
         NOTNO, NEITHER),
        (r"\lfloor \sum_{\alpha=\frac{1}{2}}^{\frac{5}{2}} \alpha \rfloor -> 4",
         ev(r"\lfloor \sum_{\alpha=\frac{1}{2}}^{\frac{5}{2}} \alpha \rfloor"), sol("4"), UNK, None),
    ]
    return out


def cases_e():
    V = [K, N, J]
    out = []
    for e, v in (("Product(Sum(1, (j, 1, k)), (k, 1, n))", "6"), ("Sum(k*Sum(1, (j, 1, k)), (k, 1, n))", "14"),
                 ("Sum(Product(j, (j, 1, k)), (k, 1, n))", "9")):
        out.append((f"{e}, n = 3 -> {v}", ev(e, ["n = 3"], V), sol(v), OK, None))
        out.append((f"{e}, n = 3 -> {v} + 1 (wrong)", ev(e, ["n = 3"], V), sol(str(int(v) + 1)), NO, None))
    out += [
        ("Sum(2**k*Sum(1, (j, 1, k)), (k, 1, n)), n = 2 -> 10", ev("Sum(2**k*Sum(1, (j, 1, k)), (k, 1, n))", ["n = 2"], V),
         sol("10"), OK, None),
        # SymPy merges these into one binder: its range conditions were decided before; the value is the value
        # path's (no numeric check confirms SymPy's value of the merged form), never a definedness abstention
        ("Sum(Sum(1, (j, 1, k)), (k, 1, n)), n = 3 -> 6", ev("Sum(Sum(1, (j, 1, k)), (k, 1, n))", ["n = 3"], V), sol("6"),
         NOTNO, None, UNDEF),
        ("Product(Sum(1, (j, 1, k)), (k, 1, 3)) -> 6", ev("Product(Sum(1, (j, 1, k)), (k, 1, 3))", vars_=V), sol("6"), NOTNO,
         None, UNDEF),
        # undecided (n free, any integer: reversed outer ranges), never "undefined"
        ("Product(Sum(1, (j, 1, k)), (k, 1, n)), n free -> factorial(n)",
         ev("Product(Sum(1, (j, 1, k)), (k, 1, n))", vars_=V), sol("factorial(n)"), UNK, None, UNDEF),
        ("Sum(k*Sum(1, (j, 1, k)), (k, 1, n)), n free -> n(n+1)(2n+1)/6",
         ev("Sum(k*Sum(1, (j, 1, k)), (k, 1, n))", vars_=V), sol("n*(n + 1)*(2*n + 1)/6"), UNK, None, UNDEF),
        ("Product(Sum(1, (j, k, 2)), (k, 1, 5)) -> 0 (reversed inner at k = 4, 5)",
         ev("Product(Sum(1, (j, k, 2)), (k, 1, 5))", vars_=V), sol("0"), UNK, None, UNDEF),
    ]
    return out


def cases_f():
    lim = lambda e, to="oo", v=XP: ir("limit", {"expr": e, "var": "x", "to": to}, vars_=[v])  # noqa: E731
    return [
        ("lim (x - 2)!/x^x, x positive integer -> 0", lim("factorial(x - 2)/x**x"), sol("0"), OK, None),
        ("lim (x - 2)!/x^x -> 1 (wrong)", lim("factorial(x - 2)/x**x"), sol("1"), NO, None),
        ("lim (x - 2)!/x!, x positive integer -> 0", lim("factorial(x - 2)/factorial(x)"), sol("0"), OK, None),
        ("lim C(x, 3)/x^3, x positive integer -> 1/6", lim("binomial(x, 3)/x**3"), sol("1/6"), OK, None),
        ("lim C(x, 3)/x^3 -> 1/3 (wrong)", lim("binomial(x, 3)/x**3"), sol("1/3"), NO, None),
        ("lim (x - 2)!/x^x, x integer -> 0", lim("factorial(x - 2)/x**x", v=XI), sol("0"), OK, None),
        ("lim (2x - 3)!/x^(2x), x positive integer -> 0", lim("factorial(2*x - 3)/x**(2*x)"), sol("0"), OK, None),
        ("lim (x/2)!/x^x, x positive integer: (x/2)! at odd x", lim("factorial(x/2)/x**x"), sol("0"), UNK, None),
        # a real variable: n! has no value between the integers, on no tail
        ("lim (x - 2)!/x^x, x real -> 0", lim("factorial(x - 2)/x**x", v=X), sol("0"), UNK, None),
        # toward -oo the violations of an integer x are unbounded
        ("lim 0*(-x)! + 1/x^2 at -oo, x integer -> 0", lim("factorial(-x)*0 + 1/x**2", "-oo", XI), sol("0"), NOTNO, None),
        ("lim (x + 2)!/x^x at -oo, x integer", lim("factorial(x + 2)/x**x", "-oo", XI), sol("0"), UNK, None),
    ]


def cases_k():
    return [
        ("1/factorial(2) -> 1/2", ev("1/factorial(2)"), sol("1/2"), OK, None),
        ("1/factorial(2) -> 1 (wrong)", ev("1/factorial(2)"), sol("1"), NO, None),
        ("factorial(-1) alone -> 0", ev("factorial(-1)"), sol("0"), UNK, None),
        ("factorial(1 - 3) alone -> 1", ev("factorial(1 - 3)"), sol("1"), UNK, None),
        (r"\Gamma(5) -> 24", ev(r"\Gamma(5)"), sol("24"), OK, None),
        ("P(5, 2) -> 20", ev("P(5, 2)"), sol("20"), OK, None),
        ("C(5, 2) -> 10", ev("C(5, 2)"), sol("10"), OK, None),
        ("Sum(1/factorial(k), (k, 0, oo)) -> E", ev("Sum(1/factorial(k), (k, 0, oo))", vars_=[K]), sol("E"), OK, None),
        ("Sum(k, (k, 1, 10)) -> 55", ev("Sum(k, (k, 1, 10))", vars_=[K]), sol("55"), OK, None),
        (r"\sum_{\alpha=1}^{3} \alpha -> 6", ev(r"\sum_{\alpha=1}^{3} \alpha"), sol("6"), OK, None),
        (r"\lfloor \sum_{k=1}^{\sqrt{9}} k \rfloor -> 6", ev(r"\lfloor \sum_{k=1}^{\sqrt{9}} k \rfloor"), sol("6"), OK, None),
        (r"\sum_{k=1}^{\infty} \frac{1}{k^2} -> pi^2/6", ev(r"\sum_{k=1}^{\infty} \frac{1}{k^2}"), sol("pi**2/6"), OK, None),
        ("Sum(k, (k, 1, n)), n = 3 -> 6", ev("Sum(k, (k, 1, n))", ["n = 3"], [K, N]), sol("6"), OK, None),
        ("series_sum k, 1 .. 3 -> 6", ir("series_sum", {"term": "k", "var": "k", "lo": "1", "hi": "3"}, vars_=[K]), sol("6"),
         OK, None),
        ("lim x!/x^x, x positive integer -> 0", ir("limit", {"expr": "factorial(x)/x**x", "var": "x", "to": "oo"}, vars_=[XP]),
         sol("0"), OK, None),
        ("step 4/factorial(-2) = 1 (wrong under every reading)", *step("4/factorial(-2) = 1"), NOTOK, REF),
        ("claim 1/factorial(-1) for 5 (wrong under every reading)", ev("5"), sol("1/factorial(-1)"), NOTOK, None),
        ("2x = 4 + 1/(3 - 3) -> {} (defined nowhere)", ir("solve_equation", {"var": "x", "equation": "2*x = 4 + 1/(3 - 3)"},
                                                          shape="set"), sol("EmptySet", "set"), OK, None),
        ("domain_of x + 1/(3 - 3) -> {}", ir("domain_of", {"expr": "x + 1/(3 - 3)", "var": "x"}, shape="set"),
         sol("EmptySet", "set"), OK, None),
        ("evaluate log(-1) - log(-1) - 1 -> -1", ev("log(-1) - log(-1) - 1"), sol("-1"), UNK, None, None, UNDEF),
        ("extremum min x**2 on [0, 2] -> 0", ir("extremum", {"f": "x**2", "var": "x", "interval": "[0, 2]", "which": "min"}),
         sol("0"), OK, None),
        ("derivative x**2 at 3 -> 6", ir("derivative", {"f": "x**2", "var": "x", "at": "3"}), sol("6"), OK, None),
        ("evaluate (-8)**(1/3) -> -2 (both readings compared)", ev("(-8)**(1/3)"), sol("-2"), NOTOK, None),
        ("claim cbrt(-8) for x**3 = -8", ir("solve_equation", {"var": "x", "equation": "x**3 = -8"}, shape="set"),
         sol("{cbrt(-8)}", "set"), OK, None),
        ("Sum(k, (k, 1, n)), n real free -> n*(n + 1)/2", ev("Sum(k, (k, 1, n))", vars_=[K, {"name": "n", "domain": "real"}]),
         sol("n*(n + 1)/2"), OK, None),
    ]


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
            absent = case[5] if len(case) > 5 else None          # a flag that must not be raised
            present = case[6] if len(case) > 6 else None         # a flag that must be raised
            t = time.time()
            try:
                r = verify(q, s)
                verdict = r.verdict
                layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
                steps = layer.evidence.get("steps", []) if layer is not None else []
                status = steps[-1].get("status") if steps else None
                allflags = {f for la in r.layers for f in (la.flags or [])} | set(r.flags)
                flags = sorted(allflags)[:6]
            except Exception as e:  # noqa: BLE001
                verdict, status, flags, allflags = f"EXC {type(e).__name__}: {e}", None, [], set()
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
    grp = args[1] if len(args) > 1 else "ABCDEFK"
    sys.exit(1 if main(out, grp) else 0)
