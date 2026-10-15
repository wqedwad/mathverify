"""Fourth audit, part d4h (the parser), round 2: the attack on round 1 (`denetim/2026-10-01/d4/saldiri/d4h/`).

Each case was measured wrong on the merge of round 1 with the session branch (a2f5603 + c4ca9dc):

* YO-1: round 1 held a closed form only under the NAMED deciding helpers. `∫ // 1`, `∫ > 1` in Piecewise,
  Interval(1, ∫), {∫} ∩ [1, 2], at(floor(∫_t), x, 1/3) and a count over x² - (∫ // 1) were still decided by evalf,
  which misses the peak of ∫_{-1}^{1} 1000·exp(-10⁶(x - 1/3)²) dx ≈ 1.77 (2.9e-834): every wrong value certified.
* YO-2: the Leibniz guard matched one spelling: \\frac{d}{d\\,x}(x^2) with d declared was d·x²/(d·x) = x, certified.
* YO-3: simplify(expr=2∫|cos x|) = 0 ran SymPy's simplify (the keyword escaped the form guard): verified.
* YO-4: the empty-list rule held for one argument only: f(x, y) on `x < -1, x > 1` was the empty domain.
* YO-5: with the given m = 1/2, {mπ + kπ} was read with m an index and certified for sin x = 0.
* RK-1: LaTeX `x \\in \\mathbb{R}` folded to True and was "not read": four task kinds abstained.
* RK-2: a domain list both readings decide the same way ((0, 3), (1, 5)) was refused outright.
* PRE-RK-4: the task's equation written in params was no premise of the steps: right steps refuted.
* PRE-RK-5: `$x \\in \\{-2, 2\\}$`, `$1 \\leq x \\leq 3$`, `$x \\neq 1$` were refuted as sets of relations.
* PRE-RK-6: the claim `S = {-2, 2}` read SymPy's registry S as a value (an exception, a layer crash).
* PRE-RK-7/8: the structural reading computed det of a matrix with an integral (~23 s per call) and compared a claim
  with the target's VALUE: eigmax(M)'s value 2 + √2 was "the question restated".
"""
import time

import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
T = {"name": "t", "domain": "real"}
D = {"name": "d", "domain": "real"}
DN = {"name": "dn", "domain": "real"}
DX = {"name": "dx", "domain": "real"}
N = {"name": "n", "domain": "positive_integer"}
SPK = "Integral(1000*exp(-1000000*(x - 1/3)**2), (x, -1, 1))"
SPKT = "Integral(1000*exp(-1000000*(t - x)**2), (t, -1, 1))"
COS = "Integral(Abs(cos(x)), (x, -1, 1))"
I3 = "Integral(x, (x, 0, 3))"


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


def _step(r) -> str | None:
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    steps = layer.evidence.get("steps", []) if layer is not None else []
    return steps[-1].get("status") if steps else None


def _f(domain, expr="x**2 + 1", args=("x",)):
    return [{"name": "f", "expr": expr, "args": list(args), "domain": domain}]


# ---------------------------------------------------------------- YO-1: no evalf of a closed form while parsing

@pytest.mark.parametrize("expr,wrong,vars_", [
    (f"{SPK} // 1", "0", None), (f"-((-{SPK}) // 1)", "1", None),
    (f"Piecewise((1, {SPK} > 1), (0, {SPK} <= 1))", "0", None),
    (f"at(floor({SPKT}), x, 1/3)", "0", [X, T]), (f"at(Max({SPKT}, 1), x, 1/3)", "1", [X, T]),
    (r"\lfloor \int_{-1}^{1} 1000 e^{-1000000 (x - \frac{1}{3})^{2}} \, dx \rfloor", "0", None),
])
def test_yo1_a_deciding_node_over_a_closed_form_is_not_decided_by_evalf(expr, wrong, vars_):
    assert _run(_ev(expr, vars_), wrong).verdict != "CORRECT"


def test_yo1_the_right_value_is_not_refuted():
    assert _run(_ev(f"{SPK} // 1"), "1").verdict != "INCORRECT"


@pytest.mark.parametrize("expr", [f"Interval(1, {SPK})", f"Intersection(Interval(1, 2), FiniteSet({SPK}))"])
def test_yo1_sets_over_a_closed_form(expr):
    assert _run(_ir("evaluate", {"expr": expr}, (), [X], "set"), "EmptySet", "set").verdict != "CORRECT"


def test_yo1_count_and_step():
    q = _ir("count_roots", {"expr": f"x**2 - ({SPK} // 1)", "var": "x"}, (), [X], "count")
    assert _run(q, "1", "count").verdict != "CORRECT"
    r = _run(_ev("1", [X, T]), "1", steps=[("compute", f"{SPK} // 1 = 0")])
    assert _step(r) != "verified"


def test_yo1_the_parse_holds_the_node_and_evalf_is_sympys_outside():
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import build_namespace, parse_expr_str
    e = parse_expr_str(f"{SPK} // 1", build_namespace(ProblemIR.from_dict(_ev("1"))))
    assert isinstance(e, sp.floor)                      # held, not 0
    assert sp.Integral(sp.exp(-sp.Symbol("x") ** 2), (sp.Symbol("x"), 0, 1)).evalf(5) > 0.7   # SymPy's evalf, unchanged


def test_yo1_every_reader_that_builds_a_tree_holds_the_form():
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import ParseError, build_namespace, parse_domain, parse_relation, parse_set_str
    ns = build_namespace(ProblemIR.from_dict(_ev("1", [X])))
    x = ns["x"]
    assert not isinstance(parse_relation(f"{SPK} < 1", ns), sp.logic.boolalg.BooleanAtom)       # the relation itself
    try:                                                                                      # the ends of a set
        assert parse_set_str(f"(1, {SPK})", ns) is not sp.S.EmptySet
    except ParseError:
        pass                                    # ends compared exactly: not read
    assert parse_domain(f"x > {SPK} and x < 1", x, ns) is not sp.S.EmptySet                    # a domain's parts
    r = _run(_ev("1", [X, T]), "1", steps=[("compute", f"{SPK} < 1")])
    assert _step(r) != "verified"


def test_yo1_controls_decide_as_before():
    assert _run(_ev(f"floor({I3})"), "4").verdict == "CORRECT"
    assert _run(_ev(f"floor({I3})"), "3").verdict == "INCORRECT"
    assert _run(_ev(f"{I3} // 1"), "4").verdict == "CORRECT"
    assert _run(_ir("evaluate", {"expr": f"Interval(1, {I3})"}, (), [X], "set"), "Interval(1, 9/2)", "set").verdict == "CORRECT"
    assert _step(_run(_ev("1"), "1", steps=[("compute", f"{I3} // 1 = 4")])) == "verified"
    assert _step(_run(_ev("1"), "1", steps=[("compute", f"floor({I3}) = 3")])) == "refuted"


# ---------------------------------------------------------------- YO-2: Leibniz fractions, any typography

@pytest.mark.parametrize("expr,vars_", [
    (r"\frac{d}{d\,x}(x^2)", [X, D]), (r"\dfrac{d}{d\;x}(x^2)", [X, D]), (r"\frac{d}{dx}(x^2)", [X, D]),
    (r"\frac{\mathrm{d}}{\mathrm{d}\,x}(x^2)", [X, D]), (r"d/d\,x (x^2)", [X, D]),
    (r"\frac{d^2}{d{n}^2}(n \sin(\pi n))", [N, X, D]), (r"\frac{d^2}{(dn)^2}(n \sin(\pi n))", [N, X, D, DN]),
    (r"\frac{d^2}{dn\,dn}(n \sin(\pi n))", [N, X, D, DN]), (r"\frac{{d}^2}{d n^2}(n \sin(\pi n))", [N, X, D]),
    (r"\frac{d^2}{dn^2}(n \sin(\pi n))", [N, X, DN]),
    # latex2sympy reads these as a derivative, so the tree holds no quotient of differentials: the text alone
    # finds the fraction (\dfrac, an upright d, \! and a trailing \, inside it, dx declared without d)
    (r"\dfrac{d}{dx}(x^2)", [X, D]), (r"\tfrac{d}{dx}(x^2)", [X, D]), (r"\frac{\mathrm{d}}{\mathrm{d}x}(x^2)", [X, D]),
    (r"\frac{\operatorname{d}}{\operatorname{d}x}(x^2)", [X, D]), (r"\frac{d}{d\!x}(x^2)", [X, D]),
    (r"\frac{d}{dx\,}(x^2)", [X, D]), (r"\frac{d}{dx}(x^2)", [X, DX]), (r"\frac{d}{dx} x^2", [X, DX]),
])
def test_yo2_a_leibniz_fraction_with_d_or_dv_declared_is_not_read(expr, vars_):
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import ParseError, build_namespace, parse_expr_str
    ns = build_namespace(ProblemIR.from_dict(_ir("simplify_expression", {"expr": "1"}, (), vars_, "expression")))
    with pytest.raises(ParseError):
        parse_expr_str(expr, ns)


def test_yo2_both_readings_abstain_and_the_step_is_not_verified():
    q = _ir("simplify_expression", {"expr": r"\frac{d}{d\,x}(x^2)"}, (), [X, D], "expression")
    assert _run(q, "x", "expression").verdict == "UNKNOWN"
    assert _run(q, "2*x", "expression").verdict == "UNKNOWN"
    # read as a derivative by latex2sympy, with d declared: still a product too
    q = _ir("simplify_expression", {"expr": r"\frac{\mathrm{d}}{\mathrm{d}x}(x^2)"}, (), [X, D], "expression")
    assert _run(q, "2*x", "expression").verdict == "UNKNOWN"
    # the claim too: \frac{d}{d\,x}(x^2) for 2x is x (a product) or 2x (a derivative)
    q = _ir("simplify_expression", {"expr": "2*x"}, (), [X, D], "expression")
    assert _run(q, r"\frac{d}{d\,x}(x^2)", "expression").verdict == "UNKNOWN"
    st = _ir("simplify_expression", {"expr": "x"}, (), [X, D], "expression")
    assert _step(_run(st, "x", "expression", steps=[("eq", r"\frac{d}{d\,x}(x^2) = x")])) != "verified"


def test_yo2_controls():
    q = _ir("simplify_expression", {"expr": r"\frac{d}{dx} x^3"}, (), [X], "expression")
    assert _run(q, "3*x**2", "expression").verdict == "CORRECT"
    for e, c in [(r"\frac{d}{2} + \frac{d}{2}", "d"), (r"\frac{a}{d}", "a/d"), (r"\frac{d}{a} + \frac{d}{a}", "2*d/a")]:
        q = _ir("simplify_expression", {"expr": e}, (), [X, D, {"name": "a", "domain": "positive_real"}], "expression")
        assert _run(q, c, "expression").verdict == "CORRECT", e


# ---------------------------------------------------------------- YO-3: rewrites by keyword

@pytest.mark.parametrize("step,bad", [
    (f"simplify(expr=2*{COS}) = 0", "verified"), (f"expand(e=simplify(expr=2*{COS})) = 0", "verified"),
    (f"factor(f=2*{COS}) = 0", "verified"), (f"simplify(expr=2*{COS}) = 4*sin(1)", "refuted"),
])
def test_yo3_a_rewrite_by_keyword_keeps_the_form(step, bad):
    assert _step(_run(_ev("1"), "1", steps=[("compute", step)])) != bad


def test_yo3_a_keyword_rewrite_reads_as_written_too():
    for step in ["expand(e=(x + 1)**2) = x**2 + 2*x + 1", "simplify(expr=x**2 - x**2) = 0"]:
        assert _step(_run(_ev("1"), "1", steps=[("compute", step)])) == "verified", step


def test_yo3_keyword_rewrite_reads_its_argument():
    from mathverify.normalize.parse import ParseError, _form_kept
    f = _form_kept(sp.simplify)
    i = sp.Integral(sp.Symbol("x"), (sp.Symbol("x"), 0, 1))
    assert f(expr=i) is i
    with pytest.raises(ParseError):
        f(expr=i, rational=sp.Integer(1))


# ---------------------------------------------------------------- YO-4: empty lists, any number of arguments

@pytest.mark.parametrize("dom", ["x < -1, x > 1", "x < -1 and x > 1", "x < -1, y > 0, x > 1"])
def test_yo4_a_two_argument_domain_list_no_number_meets_is_not_read(dom):
    q = _ir("solve_equation", {"equation": "f(x, 1) = 3", "var": "x"}, (), [X, Y], "set", _f(dom, "x + y", ("x", "y")))
    assert _run(q, "{}", "set").verdict == "UNKNOWN"
    assert _run(q, "{2}", "set").verdict == "UNKNOWN"


def test_yo4_the_list_on_any_argument_and_a_union_over_several_arguments():
    q = _ir("solve_equation", {"equation": "f(1, y) = 3", "var": "y"}, (), [X, Y], "set", _f("y < -1, y > 1", "x + y", ("x", "y")))
    assert _run(q, "{2}", "set").verdict == "UNKNOWN" and _run(q, "{}", "set").verdict == "UNKNOWN"
    # a set listed next to a condition on x, and one on y: the union of conditions on two arguments is not read
    q = _ir("solve_equation", {"equation": "f(x, 1) = 3", "var": "x"}, (), [X, Y], "set",
            _f("x in (0, 3), x > 1, y > 0", "x + y", ("x", "y")))
    assert _run(q, "{2}", "set").verdict == "UNKNOWN"


def test_yo4_control():
    q = _ir("solve_equation", {"equation": "f(x, 1) = 3", "var": "x"}, (), [X, Y], "set",
            _f("x > 0, y > 0", "x + y", ("x", "y")))
    assert _run(q, "{2}", "set").verdict == "CORRECT"


# ---------------------------------------------------------------- YO-5: a family name the problem uses

@pytest.mark.parametrize("givens,claim", [
    (["sin(x) = 0", "m = 1/2"], "{m*pi + k*pi}"), (["sin(x) = 0", "m = 1/2"], "{m*pi}"),
    (["sin(x) = 0", "0 < m < 1"], "{m*pi}"), (["cos(x) = 1", "m = 1/3"], "{2*n*pi + 6*m*pi}"),
])
def test_yo5_a_family_name_a_given_uses_is_no_index(givens, claim):
    q = _ir("trig_solve", {"var": "x"}, givens, [X, {"name": "m", "domain": "real"}], "set")
    assert _run(q, claim, "set").verdict == "UNKNOWN"


def test_yo5_a_constraint_or_an_unread_given_names_it_too():
    m = {"name": "m", "domain": "real", "constraints": ["0 < m < 1"]}
    assert _run(_ir("trig_solve", {"var": "x"}, ["sin(x) = 0"], [X, m], "set"), "{m*pi}", "set").verdict == "UNKNOWN"
    q = _ir("trig_solve", {"var": "x"}, ["sin(x) = 0", "m in (0, 1)"], [X, {"name": "m", "domain": "real"}], "set")
    assert _run(q, "{m*pi}", "set").verdict == "UNKNOWN"


def test_yo5_controls():
    q = _ir("trig_solve", {"var": "x"}, ["sin(x) = 0"], [X, {"name": "m", "domain": "real"}], "set")
    assert _run(q, "{m*pi}", "set").verdict == "CORRECT"            # V17: declared, no given
    q = _ir("trig_solve", {"var": "x"}, ["sin(x) = 0", "m = 1/2"], [X, {"name": "m", "domain": "real"}], "set")
    assert _run(q, "{k*pi}", "set").verdict == "CORRECT"


# ---------------------------------------------------------------- RK-1: x ∈ ℝ

@pytest.mark.parametrize("given", [r"$x \in \mathbb{R}$", r"x \in \mathbb{R}", r"$x \in (-\infty, \infty)$",
                                   r"$x \in (-\infty, 0) \cup [0, \infty)$"])
def test_rk1_a_membership_in_the_line_restricts_nothing(given):
    c = _ir("count_roots", {"expr": "x**2 - 4", "var": "x"}, [given], [X], "count")
    assert _run(c, "2", "count").verdict == "CORRECT"
    assert _run(c, "1", "count").verdict == "INCORRECT"
    m = _ir("extremum", {"f": "x**2 - 2*x", "var": "x", "which": "min"}, [given], [X])
    assert _run(m, "-1").verdict == "CORRECT"
    d = _ir("domain_of", {"expr": "sqrt(x - 1)", "var": "x"}, [given], [X], "set")
    assert _run(d, "Interval(1, oo)", "interval").verdict == "CORRECT"


def test_rk1_the_membership_stays_for_a_complex_symbol_and_a_domain_reads_it():
    from mathverify.normalize.parse import parse_relation
    z = sp.Symbol("z")
    rel = parse_relation(r"z \in \mathbb{R}", {"z": z})
    assert isinstance(rel, sp.Contains) and rel.args == (z, sp.S.Reals)
    q = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(r"$x \in \mathbb{R}$"))
    assert _run(q, "{-2, 2}", "set").verdict == "CORRECT"
    q = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [r"$x \notin \mathbb{R}$"], [X], "set")
    assert _run(q, "{-2, 2}", "set").verdict != "CORRECT"


@pytest.mark.parametrize("given,right,wrong", [(r"$x \in [0, \infty)$", "{2}", "{-2, 2}"), (r"$x \neq 2$", "{-2}", "{-2, 2}"),
                                               (r"$x \geq 0$", "{2}", "{-2, 2}")])
def test_rk1_a_latex_condition_given_is_read_as_written_too(given, right, wrong):
    """The as-written reading takes a LaTeX membership (`_LATEX_MEMBER_RE`, latex2sympy has no ∞ with evaluation off)
    and a LaTeX relation (its sides): read as no text, the given made the problem undecided."""
    q = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, [given], [X], "set")
    assert _run(q, right, "set").verdict == "CORRECT"
    assert _run(q, wrong, "set").verdict == "INCORRECT"


# ---------------------------------------------------------------- RK-2: two readings of a domain list

@pytest.mark.parametrize("dom,right,wrong", [("(0, 3), (1, 5)", "{2}", "{-2, 2}"), ("x in (0, 3), x in (1, 5)", "{2}", "{}"),
                                             ("(0, 3), x > 1", "{2}", "{}"), ("[0, 5], [1, 3]", "{2}", "{-2, 2}"),
                                             ("(-3, 3), (-5, 5)", "{-2, 2}", "{2}")])
def test_rk2_both_readings_agree(dom, right, wrong):
    q = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
    assert _run(q, right, "set").verdict == "CORRECT"
    assert _run(q, wrong, "set").verdict == "INCORRECT"


@pytest.mark.parametrize("dom", ["(0, 3), (1, 5)", "x in (0, 3), x in (1, 5)", "(0, 3), x > 1", "[0, 5], [1, 3]", "x > 1, (0, 3)"])
def test_rk2_the_decided_table(dom):
    """kararlar_tur2 RK-2: union and intersection both give {2} for x² + 1 = 5 and one root."""
    q = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
    assert [_run(q, c, "set").verdict for c in ("{2}", "{-2, 2}", "{}")] == ["CORRECT", "INCORRECT", "INCORRECT"]
    c = _ir("count_roots", {"expr": "f(x) - 5", "var": "x"}, (), [X], "count", _f(dom))
    assert [_run(c, n, "count").verdict for n in ("1", "2")] == ["CORRECT", "INCORRECT"]


@pytest.mark.parametrize("dom,claims", [("(0, oo), x <= 5", ["{2}", "{-2, 2}"]), ("(-oo, -1), (1, oo)", ["{}", "{-2, 2}"]),
                                        ("(-oo, 1), (1, oo)", ["{-2, 2}"])])
def test_rk2_readings_that_part_or_are_not_read_abstain(dom, claims):
    q = _ir("solve_equation", {"equation": "f(x) = 5", "var": "x"}, (), [X], "set", _f(dom))
    for c in claims:
        assert _run(q, c, "set").verdict == "UNKNOWN", c


def test_rk2_the_union_reading_writes_back_an_interval_with_points_out():
    from mathverify.normalize.parse import ParseError, _set_as_relations
    x = sp.Symbol("x", real=True)
    assert _set_as_relations(sp.Union(sp.Interval.open(-sp.oo, 1), sp.Interval.open(1, sp.oo)), x, "") == [sp.Ne(x, 1)]
    assert _set_as_relations(sp.S.Reals, x, "") == []
    with pytest.raises(ParseError):
        _set_as_relations(sp.Union(sp.Interval(0, 1), sp.Interval(2, 3)), x, "")
    with pytest.raises(ParseError):
        _set_as_relations(sp.S.EmptySet, x, "")


# ---------------------------------------------------------------- PRE-RK-4: the task's equation is a premise

@pytest.mark.parametrize("eq,claim,steps", [("x**2 - x - 2 = 0", "{-1, 2}", [("eq", "x + 2 = x**2")]),
                                            ("sqrt(x + 2) = x", "{2}", [("eq", "x + 2 = x**2")]),
                                            ("sqrt(x + 2) = x", "{2}", [("eq", "x**2 - x - 2 = 0"), ("eq", "x = 2")])])
def test_rk4_params_equation_is_a_premise_as_givens0_is(eq, claim, steps):
    for q in (_ir("solve_equation", {"equation": eq, "var": "x"}, (), [X], "set"),
              _ir("solve_equation", {"var": "x"}, [eq], [X], "set")):
        r = _run(q, claim, "set", steps)
        assert r.verdict == "CORRECT" and _step(r) == "verified"


def test_rk4_a_wrong_step_is_refuted_in_both_forms():
    for q in (_ir("solve_equation", {"equation": "x**2 - x - 2 = 0", "var": "x"}, (), [X], "set"),
              _ir("solve_equation", {"var": "x"}, ["x**2 - x - 2 = 0"], [X], "set")):
        assert _step(_run(q, "{-1, 2}", "set", [("eq", "x + 2 = x**3")])) == "refuted"
    q = _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, (), [X], "set")
    assert _step(_run(q, "Interval.open(-2, 2)", "interval", [("eq", "x < 2")])) == "verified"
    assert _step(_run(q, "Interval.open(-2, 2)", "interval", [("eq", "x < 1")])) == "refuted"


def test_rk4_trig_solve_reads_its_params_equation_as_a_premise_too():
    """trig_solve's certificate reads params.equation or givens[0]; the steps did not: every step was skipped in the
    params form, the wrong sin x = 1/3 too, which the givens form refutes."""
    for q in (_ir("trig_solve", {"var": "x", "equation": "2*sin(x) = 1", "interval": "[0, 2*pi)"}, (), [X], "set"),
              _ir("trig_solve", {"var": "x", "interval": "[0, 2*pi)"}, ["2*sin(x) = 1"], [X], "set")):
        assert _step(_run(q, "{pi/6, 5*pi/6}", "set", [("eq", "sin(x) = 1/2")])) == "verified"
        r = _run(q, "{pi/6, 5*pi/6}", "set", [("eq", "sin(x) = 1/3")])
        assert _step(r) == "refuted" and r.verdict == "INCORRECT"


# ---------------------------------------------------------------- PRE-RK-5: conditions as notation

@pytest.mark.parametrize("task,claim,kind,verdict", [
    (("solve_equation", {"equation": "x**2 = 4", "var": "x"}), r"$x \in \{-2, 2\}$", "set", "CORRECT"),
    (("solve_equation", {"equation": "x**2 = 4", "var": "x"}), r"$x \in \{-3, 3\}$", "set", "INCORRECT"),
    (("solve_inequality", {"inequality": "x**2 - 4*x + 3 <= 0", "var": "x"}), r"$1 \leq x \leq 3$", "interval", "CORRECT"),
    (("solve_inequality", {"inequality": "x**2 - 4*x + 3 <= 0", "var": "x"}), r"$x \in [1, 3]$", "set", "CORRECT"),
    (("solve_inequality", {"inequality": "x**2 - 4*x + 3 <= 0", "var": "x"}), r"$x \in [1, 4]$", "interval", "INCORRECT"),
    (("solve_inequality", {"inequality": "x**2 + 1 > 0", "var": "x"}), r"$x \in \mathbb{R}$", "set", "CORRECT"),
    (("domain_of", {"expr": "1/(x - 1)", "var": "x"}), r"$x \neq 1$", "set", "CORRECT"),
    (("domain_of", {"expr": "sqrt(x - 1)", "var": "x"}), r"$x \in [1, \infty)$", "set", "CORRECT"),
    (("domain_of", {"expr": "sqrt(x - 1)", "var": "x"}), r"$x > 1$", "set", "INCORRECT"),
])
def test_rk5_a_condition_on_the_variable_names_its_set(task, claim, kind, verdict):
    assert _run(_ir(task[0], task[1], (), [X], "set"), claim, kind).verdict == verdict


def test_rk5_an_equation_with_a_set_is_a_membership_and_a_tuple_no_notation():
    q = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, (), [X], "set")
    assert _run(q, "x = FiniteSet(-2, 2)", "set").verdict == "CORRECT"
    assert _run(q, "x = (-2, 2)", "set").verdict == "UNKNOWN"


@pytest.mark.parametrize("claim,kind", [("x**2 - 4*x + 3 <= 0", "interval"), ("x**2 - 4*x + 3 <= 0", "set"),
                                        ("x**2 - 4*x + 3 <= 0", "condition"), (r"$x < 1 \text{ or } x > 3$", "condition")])
def test_rk5_a_condition_that_is_no_notation_is_neither_solved_nor_refuted(claim, kind):
    q = _ir("solve_inequality", {"inequality": "x**2 - 4*x + 3 <= 0" if "<=" in claim else "x**2 - 4*x + 3 > 0", "var": "x"},
            (), [X], "set")
    assert _run(q, claim, kind).verdict == "UNKNOWN"


def test_rk5_a_claim_naming_the_unknown_keeps_its_steps_checked():
    q = _ev("Abs(x) + 1", [X], ["x > 0"])
    r = _run(q, "x + 1", steps=[("compute", "Abs(x) = x")])
    assert r.verdict != "INCORRECT" and _step(r) in ("verified", "unknown")


def test_rk5_a_set_task_claim_not_read_keeps_its_steps_checked():
    q = _ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, (), [X], "set")
    r = _run(q, r"$x < 1 \text{ or } x > 3$", "condition", steps=[("eq", "x**2 = 5")])
    assert r.verdict == "INCORRECT" and _step(r) == "refuted"


# ---------------------------------------------------------------- PRE-RK-6: S is no value

@pytest.mark.parametrize("claim,kind", [("S = {-2, 2}", "set"), (r"$S = (-2, 2)$", "interval"), ("S = [1, 2]", "interval"),
                                        ("S", "set"), ("{S}", "set")])
def test_rk6_the_registry_named_bare_is_no_value(claim, kind):
    r = _run(_ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, (), [X], "set"), claim, kind)
    assert r.verdict == "UNKNOWN"
    assert not any("layer_exception" in la.flags for la in r.layers)


def test_rk6_singletons_and_numbers_still_read():
    from mathverify.normalize.parse import ParseError, parse_as_written, parse_expr_str
    assert _run(_ev("2", [X]), "S.Half*4").verdict == "CORRECT"
    assert _run(_ev("2", [X]), "S(2)").verdict == "CORRECT"
    with pytest.raises(ParseError):
        parse_expr_str("S + 1")
    assert parse_as_written("S = {-2, 2}") is None


@pytest.mark.parametrize("text", ["Limit = 1", "at = 2", "P = 2", "simplify = 1"])
def test_rk6_a_written_reading_of_a_bare_helper_is_none(text):
    """A helper named bare is no value either (a Python function SymPy cannot take): the reading as written says
    None, it raises nothing (principle 13)."""
    from mathverify.normalize.parse import parse_as_written
    assert parse_as_written(text) is None


@pytest.mark.parametrize("text", ["S", "{S}", "[S, 1]", "(S, 1)", "{S: 2}"])
def test_rk6_the_reader_refuses_the_registry_itself(text):
    """No reader hands the registry on as a value: `S` came back as SymPy's S (or a list holding it) and each caller
    met it in its own way (a SympifyError from a set reading, a layer exception)."""
    from mathverify.normalize.parse import ParseError, parse_expr_str, parse_set_str
    with pytest.raises(ParseError):
        parse_expr_str(text)
    with pytest.raises(ParseError):
        parse_set_str(text)


# ---------------------------------------------------------------- PRE-RK-7/8: the structure of the target

def test_rk7_a_determinant_of_a_matrix_with_an_integral_is_read_in_seconds():
    t = time.time()
    r = _run(_ev("det(Matrix([[Integral(x, (x, 0, 2)), 1], [1, 1]]))"), "1")
    assert r.verdict == "CORRECT" and time.time() - t < 60


@pytest.mark.parametrize("target,claim,verdict", [
    ("eigmax(Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]]))", "2 + sqrt(2)", "CORRECT"),
    ("eigmax(Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]]))", "sqrt(2) + 2", "CORRECT"),
    ("eigmin(Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]]))", "2 - sqrt(2)", "CORRECT"),
    ("eigmax(Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]]))", "eigmax(Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]]))", "UNKNOWN"),
    ("P(5, 2)", "P(5, 2)", "UNKNOWN"), ("binomial(6, 3)", "binomial(6, 3)", "UNKNOWN"), ("P(5, 2)", "20", "CORRECT"),
])
def test_rk8_a_restatement_is_the_same_tree_not_the_same_value(target, claim, verdict):
    assert _run(_ev(target), claim).verdict == verdict


def test_rk8_matrix_operations_stay_operations_in_the_structure():
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.verifier import _structure
    from sympy.core.function import AppliedUndef
    ctx = make_ctx(ProblemIR.from_dict(_ev("1")))
    t = _structure("det(Matrix([[Integral(x, (x, 0, 2)), 1], [1, 1]]))", ctx)
    assert isinstance(t, AppliedUndef) and type(t).__name__ == "det"


def test_rk8_a_text_with_no_structural_reading_is_compared_as_its_syntax():
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.verifier import _same_structure
    ctx = make_ctx(ProblemIR.from_dict(_ev("1")))
    assert _same_structure("Interval(0, 1) + Interval(2, 3)", "Interval(0, 1) + Interval(2, 3)", ctx)
    assert not _same_structure("2 + sqrt(2)", "eigmax(Matrix([[2, 1, 0], [1, 2, 1], [0, 1, 2]]))", ctx)
    # never the target's value: the sum of two intervals evaluated is their union
    assert not _same_structure("Union(Interval(0, 1), Interval(2, 3))", "Interval(0, 1) + Interval(2, 3)", ctx)
    # a sum of matrices has no structural reading: its value was compared, and was "the question restated"
    assert not _same_structure("Matrix([[4, 6]])", "Matrix([[1, 2]]) + Matrix([[3, 4]])", ctx)
    assert _same_structure("Matrix([[1, 2]]) + Matrix([[3, 4]])", "Matrix([[1, 2]]) + Matrix([[3, 4]])", ctx)
