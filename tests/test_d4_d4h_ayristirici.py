"""Fourth audit (1 Oct 2026), part d4h: the parser (`denetim/2026-10-01/d4h/`).

Each case was measured wrong on ec62a68 (the session branch the part started from):

* F1: simplify(...) in a problem's text computed the Limit/Integral/Sum inside it with SymPy's doit:
  simplify(Limit(n*sin(pi/n), n, oo)) was 0 with n an integer (pi), simplify(2*Integral(|cos x|, -1..1)) 0
  (4 sin 1), and 0 was certified, a compute step claiming it verified; read as written the call ran 62-76 s.
  The same family (review of this part): floor/ceiling/Max of a closed integral were decided by evalf, which
  misses the peak of ∫_{-1}^{1} 1000·exp(-10⁶(x - 1/3)²) dx ≈ 1.77, so floor 0, ceiling 1, Max(∫, 1) = 1 were
  certified; rank and eigmax of a matrix holding a form took SymPy's value of it.
* H1: Matrix([[Limit(a*n*sin(pi/n), n, oo)]]) with a = 2 kept the plain limit (a Matrix is no Basic), the
  evaluate certificate's simplify took SymPy's 0, and Matrix([[0]]) was certified.
* D1: LaTeX `x \\notin [0, 3]` (latex2sympy: Not(Eq(x, set))) folded to True when the symbols were rebound: as a
  function's domain it restricted nothing, {-2, 2} was certified for f(x) = 5 with f = x² + 1.
* D2: a domain listing intervals, `(-oo, -1), (1, oo)`, was read as their intersection (empty): {} certified.
* I2: with d and dn declared, \\frac{d^2}{dn^2}(n \\sin(\\pi n)) was the product d²·n·sin(πn)/dn², 0 certified.
* CAP-G1: a claim computing a gcd/lcm of numbers was caught only in some spellings: \\mathit{gcd}(120, 84),
  \\textbf{gcd}, (gcd)(120, 84), gcd(120, 84)*a were certified; \\binom{6}{3} restating binomial(6, 3) too.
* G11: {nπ + kπ}: the family parameter was the first of free_symbols (hash order) and Symbol("n") captured the
  other: INCORRECT for sin x = 0 and CORRECT for cos x = 1 depending on PYTHONHASHSEED.
"""
import os
import subprocess
import sys
import time

import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
A = {"name": "a", "domain": "real"}
N = {"name": "n", "domain": "positive_integer"}
COS = "Integral(Abs(cos(x)), (x, -1, 1))"
LIM = "Limit(n*sin(pi/n), n, oo)"
LIMA = "Limit(a*n*sin(pi/n), n, oo)"
SPK = "Integral(1000*exp(-1000000*(x - 1/3)**2), (x, -1, 1))"


def _ir(kind, params, givens=(), vars_=None, shape="scalar", functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _ev(expr, vars_=None, givens=()):
    return _ir("evaluate", {"expr": expr}, givens, vars_)


def _run(ir, payload, kind="value", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""} for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _ns(*vars_, givens=()):
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import build_namespace
    return build_namespace(ProblemIR.from_dict(_ir("evaluate", {"expr": "1"}, givens, list(vars_) or [X])))


# ---------------------------------------------------------------- F1: rewrites compute no form

@pytest.mark.parametrize("expr,wrong,right", [
    (f"simplify({COS} + 1) - 1", "0", "2*sin(1)"),
    (f"simplify(2*{COS})/2", "0", "2*sin(1)"),
    (f"factor(simplify(3*{COS}))", "0", "6*sin(1)"),
])
def test_a_rewrite_of_a_closed_integral_takes_the_confirmed_value(expr, wrong, right):
    q = _ev(expr)
    assert _run(q, wrong).verdict == "INCORRECT"
    assert _run(q, right).verdict == "CORRECT"


@pytest.mark.parametrize("expr,givens", [(f"simplify({LIM})", ()), (f"simplify(2*{LIM})", ()),
                                         (f"nsimplify(simplify({LIM}))", ()), (f"simplify({LIMA})", ["a = 2"]),
                                         (f"simplify({LIMA} + a) - a", ["a = 2"])])
def test_simplify_of_a_limit_sympy_gets_wrong_is_never_its_value(expr, givens):
    t = time.time()
    assert _run(_ev(expr, [N, A], givens), "0").verdict != "CORRECT"
    assert time.time() - t < 30           # read as written the call ran 62-76 s


def test_simplify_of_a_parametric_integral_pinned_by_a_given():
    """∫_0^1 dx/(x² + 1) = π/4 (a = -1); SymPy's value through simplify was 0."""
    q = _ev("simplify(2*Integral(1/(x**2 - a), (x, 0, 1)))/2", [X, A], ["a = -1"])
    assert _run(q, "0").verdict == "INCORRECT"
    assert _run(q, "pi/4").verdict != "INCORRECT"


def test_a_compute_step_through_simplify_is_not_verified():
    r = _run(_ev("1"), "1", steps=[("compute", f"simplify(2*{COS}) = 0")])
    steps = [s for la in r.layers if la.layer == "steps.refute" for s in (la.evidence or {}).get("steps", [])]
    assert steps and steps[-1]["status"] != "verified"


@pytest.mark.parametrize("wrapper", ["simplify", "expand", "factor", "cancel", "together", "apart", "nsimplify"])
@pytest.mark.parametrize("form", [COS, LIM, "Sum(1/k**2, (k, 1, oo))", "Integral(t, (t, 0, x))"])
def test_every_rewrite_keeps_the_form(wrapper, form):
    from mathverify.normalize.parse import parse_expr_str
    e = parse_expr_str(f"{wrapper}(2*{form} + 1)", _ns(X, N, {"name": "k", "domain": "integer"}, {"name": "t", "domain": "real"}))
    assert e.has(sp.Integral, sp.Limit, sp.Sum), e


def test_a_rewrite_without_a_form_still_rewrites():
    from mathverify.normalize.parse import parse_expr_str
    x = sp.Symbol("x", real=True)
    assert parse_expr_str("expand((x + 1)**2)", _ns(X)) == x**2 + 2*x + 1
    assert parse_expr_str("factor(x**2 - 1)", _ns(X)) == (x - 1)*(x + 1)


# ---------------------------------------------------------------- F1: no evalf decision on a closed form

@pytest.mark.parametrize("expr,wrong", [(f"floor({SPK})", "0"), (f"ceiling({SPK})", "1"), (f"Max({SPK}, 1)", "1"),
                                        (f"sign({SPK} - 1)", "-1")])
def test_a_closed_form_under_a_deciding_helper_is_not_decided_by_evalf(expr, wrong):
    """√π·erf(...) ≈ 1.77: floor 1, ceiling 2, Max(∫, 1) = ∫, sign(∫ - 1) = 1; evalf says ≈ 0."""
    assert _run(_ev(expr), wrong).verdict != "CORRECT"


def test_a_pinned_closed_form_under_floor_is_not_decided_by_evalf():
    assert _run(_ev(f"floor(a*{SPK})", [X, A], ["a = 1"]), "0").verdict != "CORRECT"


@pytest.mark.parametrize("text,value", [(r"\left\lfloor \int_{-1}^{1} |\cos x| \, dx \right\rfloor", "1"),
                                        (r"\lfloor \sum_{k=1}^{\infty} \frac{1}{k^2} \rfloor", "1"),
                                        (r"\max\left(\sum_{k=1}^{\infty} \frac{1}{k^2}, 1\right)", "pi**2/6"),
                                        (r"\left| \sum_{k=1}^{\infty} \frac{1}{k^2} \right|", "pi**2/6")])
def test_latex_a_deciding_helper_left_over_a_closed_form_is_read(text, value):
    """\\lfloor Σ 1/k² \\rfloor was decided by evalf when the index became an integer (`_integer_indices`); kept,
    the sum's value is taken confirmed (π²/6) and the floor is 1."""
    from mathverify.normalize.parse import parse_expr_str
    vs = [X, {"name": "k", "domain": "integer"}]
    e = parse_expr_str(text, _ns(*vs))
    assert isinstance(e, (sp.floor, sp.Max, sp.Abs)) and e.has(sp.Integral, sp.Sum)
    assert _run(_ev(text, vs), value).verdict == "CORRECT"


def test_a_confirmed_closed_form_under_a_deciding_helper_is_decided():
    assert _run(_ev(f"floor({COS})"), "1").verdict == "CORRECT"
    assert _run(_ev(f"floor({COS})"), "0").verdict == "INCORRECT"
    assert _run(_ev(f"Max({COS}, 1)"), "2*sin(1)").verdict == "CORRECT"


def test_the_deciding_helpers_are_built_unevaluated_only_over_a_closed_form():
    from mathverify.normalize.parse import ParseError, hold_parametric, parse_expr_str, substitute_free
    ns = _ns(X, A)
    e = parse_expr_str(f"floor({SPK})", ns)
    assert isinstance(e, sp.floor) and e.has(sp.Integral)
    assert parse_expr_str("floor(7/2)", ns) == 3 and parse_expr_str("Max(2, 3)", ns) == 3
    assert parse_expr_str("Max(x, 2)", ns) == sp.Max(sp.Symbol("x", real=True), 2)
    with pytest.raises(ParseError):
        parse_expr_str(f"Float({SPK})", ns)
    assert parse_expr_str("Float(2)", ns) == 2
    a = ns["a"]
    w = substitute_free(parse_expr_str(f"floor(a*{SPK})", ns), {a: 1})
    assert isinstance(w, sp.floor) and w.has(sp.Integral)
    held = hold_parametric(parse_expr_str(f"floor({SPK.replace('1000*exp', 'a*1000*exp')})", ns), {a: 1})
    assert isinstance(held, sp.floor) and held.has(sp.Integral)
    # the index of the sum becomes an integer after the call: the rebuilt floor stays unevaluated
    s = parse_expr_str("floor(Sum(1/k**2, (k, 1, oo)))", _ns(X, {"name": "k", "domain": "integer"}))
    assert isinstance(s, sp.floor) and s.has(sp.Sum)
    # merged with d4b round 10 a floor, ceiling, sign, frac or Mod over a form is held when it is built
    # (normalize.parse._jump_eval): the rebuilds are checked on the other deciding helpers too
    w = substitute_free(parse_expr_str(f"atan2(a*{SPK} - 1, 1)", ns), {a: 1})
    assert isinstance(w, sp.atan2) and w.has(sp.Integral)
    held = hold_parametric(parse_expr_str(f"atan2({SPK.replace('1000*exp', 'a*1000*exp')} - 1, 1)", ns), {a: 1})
    assert isinstance(held, sp.atan2) and held.has(sp.Integral)
    m = parse_expr_str("Max(Sum(1/k**2, (k, 1, oo)), 1)", _ns(X, {"name": "k", "domain": "integer"}))
    assert isinstance(m, sp.Max) and m.has(sp.Sum)


def test_a_helper_named_bare_is_its_sympy_class():
    """`which: "min"` is read as written with the problem's namespace; a plain function in Min's place could
    not be sympified and every extremum task abstained."""
    from mathverify.normalize.parse import parse_as_written
    ns = _ns(X)
    assert parse_as_written("min", ns) == sp.Tuple(sp.Min)
    # merged with d4b round 10 the namespace's floor is its strict subclass of SymPy's (normalize.parse.floor)
    from mathverify.normalize import parse
    assert parse_as_written("floor", ns) == sp.Tuple(parse.floor) and issubclass(parse.floor, sp.floor)
    q = _ir("extremum", {"f": "Abs(x) - x**2", "var": "x", "interval": "[0, 2]", "which": "min"},
            vars_=[{"name": "x", "domain": "positive_real"}])
    assert _run(q, "-2").verdict == "CORRECT"


# ---------------------------------------------------------------- H1: forms inside containers

def test_a_pinned_limit_inside_a_matrix_is_held_and_checked():
    q = _ev(f"Matrix([[{LIMA}]])", [N, A], ["a = 2"])
    assert _run(q, "Matrix([[0]])").verdict != "CORRECT"
    assert _run(q, "Matrix([[2*pi]])").verdict != "INCORRECT"
    ql = _ev(r"\begin{pmatrix} \lim_{n \to \infty} a n \sin(\frac{\pi}{n}) \end{pmatrix}", [N, A], ["a = 2"])
    assert _run(ql, "Matrix([[0]])").verdict != "CORRECT"


def test_a_closed_form_inside_a_matrix_is_compared_by_its_confirmed_value():
    q = _ev("Matrix([[Limit(x*sin(1/x), x, oo)]])")
    assert _run(q, "Matrix([[1]])").verdict == "CORRECT"
    assert _run(q, "Matrix([[0]])").verdict == "INCORRECT"
    q2 = _ev(f"Matrix([[a*{COS}]])", [X, A], ["a = 1"])
    assert _run(q2, "Matrix([[0]])").verdict == "INCORRECT"
    assert _run(q2, "Matrix([[2*sin(1)]])").verdict == "CORRECT"


def test_the_form_helpers_read_matrices_lists_and_tuples():
    from mathverify.equiv.forms import checked_forms, has_closed_form, has_parametric_form
    from mathverify.normalize.parse import HeldIntegral, hold_parametric
    x, a = sp.Symbol("x", real=True), sp.Symbol("a", real=True)
    i_cos = sp.Integral(sp.Abs(sp.cos(x)), (x, -1, 1))
    m = sp.Matrix([[2 * i_cos, 1]])
    assert has_closed_form(m) and has_closed_form([i_cos]) and has_closed_form((1, (i_cos,)))
    assert checked_forms(m) == sp.Matrix([[4 * sp.sin(1), 1]])
    assert checked_forms([i_cos, 2]) == [2 * sp.sin(1), 2]
    p = sp.Matrix([[sp.Integral(x, (x, 0, a))]])
    assert has_parametric_form(p) and not has_parametric_form(m)
    assert isinstance(hold_parametric(p)[0, 0], HeldIntegral)
    assert hold_parametric(p, {a: 2})[0, 0] == sp.Integral(x, (x, 0, 2))
    assert hold_parametric((sp.Integral(x, (x, 0, a)), 1), {a: 2}) == (sp.Integral(x, (x, 0, 2)), 1)


@pytest.mark.parametrize("expr", [f"rank(Matrix([[{LIM}, 1], [{LIM}, 2]]))", f"rank(Matrix([[{COS}, 1], [{COS}, 2]]))",
                                  f"eigmax(Matrix([[{COS}, 0], [0, 1]]))", f"eigmin(Matrix([[{COS}, 0], [0, 3]]))"])
def test_a_matrix_decision_on_a_form_is_not_read(expr):
    from mathverify.normalize.parse import ParseError, parse_expr_str
    with pytest.raises(ParseError):
        parse_expr_str(expr, _ns(X, N))


def test_an_eigenvalue_of_undecided_realness_is_not_dropped():
    """1 ± i·a: real only at a = 0; eigmax read the empty list of real ones."""
    from mathverify.normalize.parse import ParseError, parse_expr_str
    with pytest.raises(ParseError):
        parse_expr_str("eigmax(Matrix([[1, a], [-a, 1]]))", _ns(X, A))
    assert parse_expr_str("eigmax(Matrix([[2, 0], [0, 3]]))", _ns(X)) == 3
    assert parse_expr_str("rank(Matrix([[1, 2], [2, 4]]))", _ns(X)) == 1


# ---------------------------------------------------------------- D1: LaTeX set membership

def _f(domain, expr="x**2 + 1"):
    return [{"name": "f", "expr": expr, "args": ["x"], "domain": domain}]


@pytest.mark.parametrize("dom", [r"$x \notin [0, 3]$", r"x \notin [0, 3]", r"$x \notin \{2\}$", r"\( x \notin (0,3] \)",
                                 r"$x \notin [1, 3]$"])
def test_a_latex_notin_domain_is_no_true(dom):
    q = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
    assert _run(q, "{-2, 2}", "set").verdict != "CORRECT"
    assert _run(q, "{-2}", "set").verdict != "INCORRECT"
    e = dict(_ev("f(2)"), functions=_f(dom))
    assert _run(e, "5").verdict != "CORRECT"


def test_latex_membership_is_read_as_membership():
    from mathverify.normalize.parse import ParseError, parse_relation, read_domain_condition
    ns = _ns(X)
    x = ns["x"]
    assert parse_relation(r"x \notin [0, 3]", ns) == sp.Or(x < 0, x > 3)
    assert parse_relation(r"x \in (0, 3)", ns) == sp.And(x > 0, x < 3)
    assert parse_relation(r"x \notin \{2\}", ns) == sp.Ne(x, 2)
    with pytest.raises(ParseError):
        read_domain_condition(r"$x \notin [0, 3]$", [x], ns)
    assert read_domain_condition(r"$x \in (0, 3)$", [x], ns) == sp.And(x > 0, x < 3)
    assert read_domain_condition(r"$x \neq 2$", [x], ns) == sp.Ne(x, 2)


@pytest.mark.parametrize("given", [r"x \notin \mathbb{Z}", r"$x \notin \mathbb{Z}$", r"\( x \notin \mathbb{Z} \)"])
def test_a_latex_notin_given_outside_the_intervals_is_applied(given):
    """±2 are integers: no root of x² = 4 is left. With the delimiters the given was not applied (UNKNOWN)."""
    q = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [given], [X], "set")
    assert _run(q, "{}", "set").verdict == "CORRECT"
    assert _run(q, "{-2, 2}", "set").verdict == "INCORRECT"


def test_a_latex_in_given_reads_the_interval():
    q = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [r"$x \in (0, 3)$"], [X], "set")
    assert _run(q, "{}", "set").verdict != "CORRECT"
    assert _run(q, "{-2, 2}", "set").verdict != "CORRECT"
    assert _run(q, "{2}", "set").verdict != "INCORRECT"


def test_a_latex_membership_of_a_domain_on_the_line():
    from mathverify.normalize.parse import read_domain_condition
    x = sp.Symbol("x", real=True)
    ns = dict(_ns(X), x=x)
    assert read_domain_condition(r"$x \in [1, \infty)$", [x], ns) == (x >= 1)
    assert read_domain_condition(r"$x \in \mathbb{R}$", [x], ns) is None


# ---------------------------------------------------------------- D2: lists of sets in a domain

@pytest.mark.parametrize("dom", ["(-oo, -1), (1, oo)", "(0, 3), (4, 5)", "[-3, -1], [1, 3]", "(-oo, -1) & (1, oo)",
                                 "(-oo, -1) and (1, oo)", "x in (-oo, -1), x in (1, oo)", "(0, 3), (1, 5)",
                                 "(-oo, -1), x > 1", "x < -1, x > 1", "x<-1 and x>1"])
def test_a_list_of_sets_or_an_empty_list_is_no_domain(dom):
    from mathverify.normalize.parse import ParseError, read_domain_condition
    x = sp.Symbol("x", real=True)
    with pytest.raises(ParseError):
        read_domain_condition(dom, [x], dict(_ns(X), x=x))
    q = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
    assert _run(q, "{}", "set").verdict != "CORRECT"
    c = _ir("count_roots", {"expr": "f(x) - 5", "var": "x"}, (), [X], "count", _f(dom))
    assert _run(c, "0", "count").verdict != "CORRECT"


@pytest.mark.parametrize("dom,expected", [("x > 0, x < 3", "And(x > 0, x < 3)"), ("(0, 3), (0, 3)", "And(x > 0, x < 3)"),
                                          ("x in (0, 3), x in (0, 3)", "And(x > 0, x < 3)"),
                                          ("x in [0, 3), x != 1", "And(x >= 0, x < 3, Ne(x, 1))"),
                                          ("x > 0, x != 1, x != 2", "And(x > 0, Ne(x, 1), Ne(x, 2))")])
def test_relations_a_repeated_set_and_exclusions_all_hold(dom, expected):
    from mathverify.normalize.parse import read_domain_condition
    x = sp.Symbol("x", real=True)
    assert read_domain_condition(dom, [x], dict(_ns(X), x=x)) == sp.sympify(expected, locals={"x": x})


def test_two_arguments_listed_with_their_sets():
    from mathverify.normalize.parse import read_domain_condition
    x, y = sp.Symbol("x", real=True), sp.Symbol("y", real=True)
    ns = dict(_ns(X), x=x, y=y)
    assert read_domain_condition("x in (0, oo), y in (0, oo)", [x, y], ns) == sp.And(x > 0, y > 0)


# ---------------------------------------------------------------- I2: Leibniz notation or a product

DV = [N, X, {"name": "d", "domain": "real"}, {"name": "dn", "domain": "real"}, {"name": "dx", "domain": "real"}]


@pytest.mark.parametrize("expr", [r"\frac{d^2}{dn^2}(n \sin(\pi n))", r"\frac{\mathrm{d}^2}{\mathrm{d}n^2}(n \sin(\pi n))",
                                  r"\dfrac{d^{2}}{d n^{2}}(n \sin(\pi n))", r"\frac{d}{dx} x^3", r"\frac{d^3}{dx^3}(x^4)"])
def test_leibniz_notation_whose_product_reading_is_declared_is_not_read(expr):
    from mathverify.normalize.parse import ParseError, parse_expr_str
    with pytest.raises(ParseError):
        parse_expr_str(expr, _ns(*DV))
    q = _ir("simplify_expression", {"expr": r"\frac{d^2}{dn^2}(n \sin(\pi n))"}, (), DV, "expression")
    assert _run(q, "0", "expression").verdict != "CORRECT"


def test_leibniz_notation_without_declared_names_reads_as_before():
    from mathverify.normalize.parse import _leibniz_names, parse_expr_str
    assert _run(_ir("simplify_expression", {"expr": r"\frac{d}{dx} x^3"}, (), [X], "expression"), "3*x**2",
                "expression").verdict == "CORRECT"
    ns = _ns(X, {"name": "d", "domain": "real"})
    assert parse_expr_str(r"\frac{d}{2}", ns) == ns["d"] / 2
    assert _leibniz_names("d^2", "dn^2") == {"d", "dn"}
    # round 2 (YO-2): d itself is among the names too (`d y` is the product d·y): one of them declared is enough
    assert _leibniz_names("dy", "dx") == {"d", "dy", "dx"}
    assert _leibniz_names(r"\mathrm{d}^{2} y", r"\mathrm{d} x^{2}") == {"d", "dx"}
    assert _leibniz_names("d", "2") is None and _leibniz_names("a", "dx") is None


# ---------------------------------------------------------------- CAP-G1: a computed gcd/lcm is no value

@pytest.mark.parametrize("target,claim,vars_", [
    ("gcd(84, 120)", r"\mathit{gcd}(120,84)", ()), ("gcd(84, 120)", r"\mathbf{gcd}(120,84)", ()),
    ("gcd(84, 120)", r"\textit{gcd}(120,84)", ()), ("gcd(84, 120)", r"\textbf{gcd}(120,84)", ()),
    ("gcd(84, 120)", "(gcd)(120, 84)", ()), ("gcd(84, 120)", "(igcd)(120, 84)", ()),
    ("gcd(84, 120)", "gcd(120, 84) + 0", ()), ("lcm(4, 6)", r"\mathit{lcm}(6,4)", ()),
    ("lcm(4, 6)", "(lcm)(6, 4)", ()), ("gcd(84, 120)", r"\gcd(120, 84)", ()),
    ("gcd(84, 120)*a", "gcd(120, 84)*a", ({"name": "a", "domain": "positive_integer"},)),
    ("gcd(84, 120)*a", r"\mathit{gcd}(120, 84) a", ({"name": "a", "domain": "positive_integer"},)),
    ("binomial(6, 3)", r"\binom{6}{3}", ()), ("binomial(6, 3)", r"{6 \choose 3}", ()),
])
def test_a_claim_that_computes_or_restates_is_no_value(target, claim, vars_):
    r = _run(_ev(target, list(vars_)), claim)
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in r.flags


def test_a_set_claim_with_a_closed_gcd_next_to_a_symbol_is_no_value():
    a = {"name": "a", "domain": "positive_integer"}
    q = _ir("solve_equation", {"var": "x", "equation": "x - gcd(84, 120)*a = 0"}, (), [X, a], "set")
    r = _run(q, "{gcd(120, 84)*a}", "set")
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in r.flags
    r2 = _run(_ir("solve_equation", {"var": "x", "equation": "x - 12 = 0"}, (), [X], "set"), [r"\mathit{gcd}(84,120)"], "set")
    assert r2.verdict == "UNKNOWN" and "claim_is_not_a_value" in r2.flags


def test_values_and_symbolic_gcds_stay_claims():
    a = {"name": "a", "domain": "positive_integer"}
    n = {"name": "n", "domain": "positive_integer"}
    assert _run(_ev("gcd(84, 120)", []), "12").verdict == "CORRECT"
    assert _run(_ev("gcd(84, 120)*a", [a]), "12*a").verdict == "CORRECT"
    assert _run(_ev("gcd(n, 4)", [n], ["n = 12"]), "4").verdict == "CORRECT"
    assert _run(_ev("binomial(6, 3)", []), "binomial(6, 6 - 3)").verdict == "CORRECT"
    assert _run(_ev("2*10", []), r"\binom{6}{3}").verdict == "CORRECT"
    from mathverify.normalize.parse import parse_expr_str, recording_integer_ops
    with recording_integer_ops() as seen:
        parse_expr_str("gcd(n, 4) + 1", _ns(n))
    assert seen == []
    with recording_integer_ops() as seen:
        parse_expr_str(r"\mathbf{lcm}(4, 6)", _ns(X))
    assert seen and parse_expr_str("gcd(4, 6)", _ns(X)) == 2


# ---------------------------------------------------------------- G11: two family parameters

G11_CASES = [("sin(x) = 0", "{n*pi + k*pi}", {"CORRECT"}), ("tan(x) = 0", "{n*pi + k*pi}", {"CORRECT"}),
             ("sin(x) = 0", "{k*pi + 2*n*pi}", {"CORRECT"}), ("cos(x) = 1", "{2*n*pi + 4*k*pi}", {"CORRECT"}),
             ("cos(x) = 1", "{n*pi + k*pi}", {"INCORRECT"}), ("sin(x) = 0", "{n*pi/2 + k*pi/2}", {"INCORRECT"}),
             ("cos(x) = 1", "{2*n*pi + 3*k*pi}", {"INCORRECT"}), ("sin(x) = 0", "{n*pi + k}", {"UNKNOWN"}),
             ("sin(x) = 0", "{n*k*pi}", {"UNKNOWN"})]

_G11_SCRIPT = """
import json
from mathverify.verifier import verify
cases = json.loads(%r)
out = []
for eq, c in cases:
    ir = {"task": {"kind": "trig_solve", "params": {"var": "x"}}, "vars": [{"name": "x", "domain": "real"}],
          "givens": [eq], "answer_shape": "set"}
    out.append(verify(ir, {"claimed_answer": {"kind": "set", "payload": c}, "steps": []}).verdict)
print(json.dumps(out))
"""


@pytest.mark.parametrize("seed", ["0", "3"])
def test_two_family_parameters_whatever_the_hash_seed(seed):
    """{an + bk : n, k ∈ ℤ} = gcd(a, b)ℤ; a sum of incommensurable or non-linear parameters is not read."""
    import json
    src = _G11_SCRIPT % json.dumps([(eq, c) for eq, c, _ in G11_CASES])
    env = dict(os.environ, PYTHONHASHSEED=seed)
    r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, env=env, timeout=600)
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert [v in exp for v, (_, _, exp) in zip(got, G11_CASES)] == [True] * len(G11_CASES), got


def test_one_family_is_the_gcd_of_the_coefficients():
    from mathverify.certify.trig import _one_family, general_solution_from_claim
    n, k, m = (sp.Symbol(s, integer=True) for s in "nkm")
    pi = sp.pi
    assert _one_family(n * pi + k * pi, [k, n]) == (0, pi)
    assert _one_family(pi / 2 + n * pi / 2 + k * pi / 3, [k, n]) == (pi / 2, pi / 6)
    assert _one_family(2 * n * pi + 4 * k * pi + m * 0, [k, n]) == (0, 2 * pi)
    assert _one_family(n * pi + k, [k, n]) is None
    assert _one_family(n * k * pi, [k, n]) is None
    assert _one_family(n ** 2 * pi + k * pi, [k, n]) is None
    assert _one_family((n + k) ** 2 * pi, [k, n]) is None     # equal coefficients 2(n + k)π: still no family
    zero = n * pi + k * pi - (n + k) * pi                  # SymPy keeps it unsimplified: the constant 0
    assert _one_family(zero, [k, n]) == (0, None)
    assert general_solution_from_claim(sp.FiniteSet(zero), {}) == sp.FiniteSet(0)
    g = general_solution_from_claim(sp.FiniteSet(n * pi + k * pi), {})
    j = list(g.lamda.variables)[0]
    assert g.lamda.expr == pi * j and g.base_set == sp.S.Integers
    assert general_solution_from_claim(sp.FiniteSet(n * pi + k), {}) is None
    q = _ir("trig_solve", {"var": "x"}, ["sin(x) = 0"], [X], "set")
    r = _run(q, "{n*pi + k}", "set")
    trig = [la for la in r.layers if la.layer.startswith("certify.trig")]
    assert trig and "family_parameters_not_one_family" in str(trig[0].evidence)
