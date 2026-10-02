"""Fourth audit (1 Oct 2026), part d4d: the givens' bindings and conditions (`denetim/2026-10-01/d4d/`).

Each case was measured wrong on 158c220 (src = 1df0558) or on the session branch 195e183:

* G1: a given that is a chain, an And/Or, `x > 0 and x < 3`, `x in (0, 3)` was dropped next to the task's own
  relation: (−2, 2) was CORRECT for x² < 4 with 0 < x < 3, the count 2 for x² − 4 with Or(x < −3, x > 1), and
  the maximum 0 of −x² on [−5, 5] under that Or (the supremum −1 is not attained).
* G7, TAN-04: a binding a = c was used though another given (a < 0, a > 1, a − 1 = 0), the declaration
  (positive, integer) or a constraint (a > 5) contradicts it, or its value is undefined as written
  (4 + log(−1) − log(−1)) or a convention (0**0).
* G8: a constraint the binding makes false (x < a, a = 0, x positive) was dropped: {2} CORRECT for x² = 4.
* G9, TAN-03: a written condition on the bound parameter alone (log(a), a/a, a!, gcd(a, 2), ...) was never
  read at its value: x + log(a) − log(a) = 2 with a = −1 had {2} certified.
* G10: an undecided membership kept the candidate: x = T (π exactly, seven arctangent terms) with x > π
  certified y = 7, and {T} for x − T = 0 with x > π (the right {} was INCORRECT).
* TAN-01: a binding that reverses a Sum range (n = −3) or makes it fractional (n/2 with n = 7) certified
  Karr's value; the fractional case ran 108 s.
* TAN-09: x**a with a = 2 kept the condition x > 0: (0, 2) CORRECT and (−2, 2) INCORRECT for x**a < 4.
* P1: a pin reached a variable an enclosing operator binds, or the task's own variable: F'(2) = 0 for
  F(x) = ∫_0^x t² dt with the given x = 2, d/da ∫_0^1 a·t dt = 0 with a = 2.
"""
import pytest
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
A = {"name": "a", "domain": "real"}
T_ = {"name": "t", "domain": "real"}
KI = {"name": "k", "domain": "integer"}
N = {"name": "n", "domain": "integer"}
XA = [X, A]
# pi exactly: atan(1/2) + atan(1/5) + atan(1/8) = atan(1/3) + atan(1/5) + atan(1/7) + atan(1/8) = pi/4,
# asin(1/sqrt(26)) = atan(1/5), asin(1/sqrt(65)) = atan(1/8); no exact check decides it (2 Oct 2026)
T7 = "2*(atan(1/3) + atan(1/5) + atan(1/7) + atan(1/8) + atan(1/2) + asin(1/sqrt(26)) + asin(1/sqrt(65)))"


def _ir(kind, params, givens=(), vars_=None, shape="set", dod=None, functions=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ or [X]), "givens": list(givens),
         "answer_shape": shape}
    if dod:
        d["domain_of_discourse"] = dod
    if functions:
        d["functions"] = functions
    return d


def _run(ir, payload, kind="set", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _flags(r):
    return {f for la in r.layers for f in (la.flags or [])}


def _ineq(rel, givens, vars_=None, dod=None):
    return _ir("solve_inequality", {"inequality": rel, "var": "x"}, givens, vars_, dod=dod)


def _eq(rel, givens, vars_=None, dod=None):
    return _ir("solve_equation", {"equation": rel, "var": "x"}, givens, vars_, dod=dod)


def _roots(expr, givens, vars_=None):
    return _ir("count_roots", {"expr": expr, "var": "x"}, givens, vars_, shape="count")


def _lim(expr, to, givens, vars_=None):
    return _ir("limit", {"expr": expr, "var": "x", "to": to}, givens, vars_, shape="scalar")


# --- G1: conditions read, never dropped --------------------------------------------------------------------
def test_read_condition_forms():
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import ParseError, build_namespace, read_condition
    ir = ProblemIR.from_dict(_ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}))
    ns = build_namespace(ir)
    x = ns["x"]
    want = sp.Interval.open(0, 3)
    from mathverify.certify.base import Ctx
    for g in ["0 < x < 3", "And(x > 0, x < 3)", "x > 0 and x < 3", "x > 0, x < 3", "(x > 0) & (x < 3)",
              "x > 0 ∧ x < 3", "x in (0, 3)", "x ∈ (0, 3)", r"x \in (0, 3)", r"0 \lt x \lt 3"]:
        assert Ctx.condition_set(read_condition(g, ns), x) == want, g
    for g in ["Or(x < -3, x > 1)", "x < -3 or x > 1", "(x < -3) | (x > 1)", "x < -3 ∨ x > 1"]:
        got = Ctx.condition_set(read_condition(g, ns), x)
        assert got == sp.Union(sp.Interval.open(-sp.oo, -3), sp.Interval.open(1, sp.oo)), g
    for g in ["x>0 ve x<3", "x > 0; x < 3", "x"]:
        with pytest.raises(ParseError):
            read_condition(g, ns)


@pytest.mark.parametrize("given", ["0 < x < 3", "x > 0 and x < 3", "x > 0, x < 3", "x in (0, 3)", "x ∈ (0, 3)",
                                   "(x > 0) & (x < 3)", r"0 < x \le 3"])
def test_g1_chain_and_membership_applied(given):
    q = _ineq("x**2 < 4", [given])
    assert _run(q, "Interval.open(-2, 2)", "interval").verdict != "CORRECT"
    assert _run(q, "Interval.open(0, 2)", "interval").verdict == "CORRECT"


@pytest.mark.parametrize("given", ["Or(x < -3, x > 1)", "x < -3 or x > 1", "(x < -3) | (x > 1)"])
def test_g1_or_applied(given):
    c = _roots("x**2 - 4", [given])
    assert _run(c, "2", "count").verdict != "CORRECT"
    assert _run(c, "1", "count").verdict == "CORRECT"
    e = _ir("extremum", {"f": "-x**2", "var": "x", "which": "max", "interval": "[-5, 5]"}, [given], shape="scalar")
    assert _run(e, "0", "value").verdict != "CORRECT"
    assert _run(_eq("x**2 = 4", [given]), "{-2, 2}").verdict != "CORRECT"


def test_g1_domain_of_and_unreadable():
    d = _ir("domain_of", {"expr": "sqrt(4 - x**2)", "var": "x"}, ["x > 0 and x < 3"])
    assert _run(d, "Interval(-2, 2)", "interval").verdict != "CORRECT"
    assert _run(d, "Interval.Lopen(0, 2)", "interval").verdict == "CORRECT"
    for g in ["x>0 ve x<3", "x > 0; x < 3"]:
        r = _run(_ineq("x**2 < 4", [g]), "Interval.open(-2, 2)", "interval")
        assert r.verdict == "UNKNOWN" and "given_not_applied" in _flags(r), g
    r = _run(_ineq("x**2 < 4", ["b < x < 3"], [X, {"name": "b"}]), "Interval.open(-2, 2)", "interval")
    assert r.verdict == "UNKNOWN"


def test_g1_extremum_unreadable_given_abstains():
    e = _ir("extremum", {"f": "-x**2", "var": "x", "which": "max", "interval": "[-5, 5]"}, ["x>0 ve x<3"],
            shape="scalar")
    r = _run(e, "0", "value")
    assert r.verdict == "UNKNOWN" and "condition_not_applied" in _flags(r)
    e2 = _ir("extremum", {"f": "-(x - 1)**2", "var": "x", "which": "max", "interval": "[-5, 5]"}, ["x in (2, 3)"],
             shape="scalar")
    assert _run(e2, "0", "value").verdict != "CORRECT"


def test_g1_extremum_reads_textual_conjunction():
    e = _ir("extremum", {"f": "x", "var": "x", "which": "max", "interval": "[-5, 5]"}, ["x >= 1 and x <= 3"],
            shape="scalar")
    assert _run(e, "3", "value").verdict == "CORRECT"
    assert _run(e, "5", "value").verdict == "INCORRECT"


def test_g1_equation_layer_reads_textual_conjunction():
    r = _run(_eq("x**2 = 4", ["x > 0 and x < 3"]), "{2}")
    assert next(la for la in r.layers if la.layer == "certify.algebra").verdict == "pass"
    r = _run(_eq("x**2 = 4", ["x in (0, 3)"]), "{-2, 2}")
    assert r.verdict == "INCORRECT"


def test_g1_evaluate_chain_or_undecided_inequality():
    ev = _ir("evaluate", {"expr": "y"}, ["x**2 = 4", "y = x + 1", "Or(x < -3, x > 1)"], [X, {"name": "y"}],
             shape="scalar")
    assert _run(ev, "3", "value").verdict == "CORRECT"
    assert _run(ev, "-1", "value").verdict == "INCORRECT"


# --- G7, TAN-04: a binding the rest of the problem contradicts --------------------------------------------
@pytest.mark.parametrize("givens,vars_", [
    (["x > a", "a = 1", "a < 0"], XA),
    (["a = 0", "x > a", "a > 1"], XA),
    (["a = 0", "x > a", "a - 1 = 0"], XA),
    (["a = 0", "x > a", "a**2 = 1"], XA),
    (["a = 0", "x > a"], [X, {"name": "a", "domain": "positive_real"}]),
    (["a = 0", "x > a"], [X, {"name": "a", "domain": "real", "constraints": ["a > 1"]}]),
    (["x > a", "a = 1/2"], [X, {"name": "a", "domain": "integer"}]),
    (["x > a", "a = 1", "a = 2"], XA),
])
def test_g7_inconsistent_binding(givens, vars_):
    r = _run(_eq("x**2 = 4", givens, vars_), "{2}")
    assert r.verdict == "UNKNOWN" and "ir_inconsistent" in _flags(r)


@pytest.mark.parametrize("given,flag", [("a = 4 + log(-1) - log(-1)", "problem_undefined_as_written"),
                                        ("a = 4 + acos(2) - acos(2)", "problem_undefined_as_written"),
                                        ("a = sqrt(-4)**2", "problem_undefined_as_written"),
                                        ("a = 0**0 + 3", "given_binding_undecided")])
def test_g7_binding_value_undefined_or_convention(given, flag):
    r = _run(_eq("x**2 = a", [given], XA), "{-2, 2}")
    assert r.verdict == "UNKNOWN" and flag in _flags(r)


def test_g7_limit_binding_checked():
    lp = _lim("sin(a*x)/x", "0", ["a = -2"], [X, {"name": "a", "domain": "positive_real"}])
    assert _run(lp, "-2", "value").verdict == "UNKNOWN"
    assert _run(_lim("a*x", "1", ["a = 0", "a - 1 = 0"], XA), "0", "value").verdict == "UNKNOWN"
    assert _run(_lim("sin(a*x)/x", "0", ["a = 0**0"], XA), "1", "value").verdict == "UNKNOWN"


# --- G8: a constraint false at the values ------------------------------------------------------------------
def test_g8_false_constraint_not_dropped():
    V = [{"name": "x", "domain": "positive_real", "constraints": ["x < a"]}, A]
    for payload in ("{2}", "{}"):
        r = _run(_eq("x**2 = 4", ["a = 0"], V), payload)
        assert r.verdict == "UNKNOWN" and "ir_inconsistent" in _flags(r)
    assert _run(_roots("x**2 - 4", ["a = 0"], V), "1", "count").verdict == "UNKNOWN"
    Vg = [{"name": "x", "domain": "positive_real"}, A]
    assert _run(_eq("x**2 = 4", ["a = 0", "x < a"], Vg), "{}").verdict == "UNKNOWN"
    assert _run(_eq("x**2 = 4", ["a = 0"], Vg, dod="x < a"), "{2}").verdict == "UNKNOWN"


def test_g8_domain_for_reads_false_constraint_as_empty():
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    V = [{"name": "x", "domain": "positive_real", "constraints": ["x < a"]}, A]
    ctx = make_ctx(ProblemIR.from_dict(_eq("x**2 = 4", ["a = 0"], V)))
    assert ctx.domain_for(ctx.sym("x")) is sp.S.EmptySet
    for c, empty, unapplied in [("pi < 3", True, False), ("pi > 3", False, False), (f"{T7} > pi", False, True)]:
        ctx = make_ctx(ProblemIR.from_dict(_eq("x**2 = 4", [], [{"name": "x", "constraints": ["x > 0", c]}])))
        x = ctx.sym("x")
        assert (ctx.domain_for(x) is sp.S.EmptySet) is empty, c
        assert bool(ctx.unapplied_conditions(x)) is unapplied, c


def test_g8_closed_false_given_or_constraint_is_inconsistent():
    for q in (_eq("x**2 = 4", [], [{"name": "x", "constraints": ["x > 0", "pi < 3"]}]), _eq("x**2 = 4", ["1 > 2"])):
        for payload in ("{}", "{2}", "{-2, 2}"):
            r = _run(q, payload)
            assert r.verdict == "UNKNOWN" and "ir_inconsistent" in _flags(r)
    r = _run(_eq("x**2 = 4", ["a = -1"], XA, dod="Interval.open(0, oo)"), "{2}")
    assert r.verdict == "UNKNOWN" and "ir_inconsistent" in _flags(r)


# --- G9, TAN-03: a written condition on the bound parameter ------------------------------------------------
@pytest.mark.parametrize("term,a", [("log(a)", "-1"), ("sqrt(a)", "-1"), ("acos(a)", "2"), ("a/a", "0"),
                                    ("tan(a)", "pi/2"), ("log(a - 1)", "1/2"), ("factorial(a)", "-1"),
                                    ("factorial(a)", "1/2"), ("binomial(a, 2)", "-1"), ("gcd(a, 2)", "sqrt(2)")])
def test_g9_condition_at_the_bound_value(term, a):
    r = _run(_eq(f"x + {term} - {term} = 2", [f"a = {a}"], XA), "{2}")
    assert r.verdict == "UNKNOWN"
    assert {"problem_undefined_as_written", "given_binding_undecided"} & _flags(r)


def test_g9_other_tasks_and_sources():
    V = XA
    L = "x + log(a) - log(a)"
    assert _run(_ir("derivative", {"f": L, "var": "x"}, ["a = -1"], V, shape="expression"), "1",
                "expression").verdict == "UNKNOWN"
    assert _run(_lim(L, "1", ["a = -1"], V), "1", "value").verdict == "UNKNOWN"
    assert _run(_lim("a*x + acos(a) - acos(a)", "1", ["a = 2"], V), "2", "value").verdict == "UNKNOWN"
    fn = _ir("solve_equation", {"equation": "x + f(a) = 2", "var": "x"}, ["a = -1"], V,
             functions=[{"name": "f", "args": ["t"], "expr": "log(t) - log(t)"}])
    assert _run(fn, "{2}").verdict == "UNKNOWN"
    lc = _lim(L, "1", [], [X, {"name": "a", "constraints": ["a = -1"]}])
    assert _run(lc, "1", "value").verdict == "UNKNOWN"
    d = _ir("domain_of", {"expr": "sqrt(x)*a/a", "var": "x"}, ["a = 0"], V)
    assert _run(d, "Interval(0, oo)", "interval").verdict == "UNKNOWN"


def test_g9_values_implied_through_other_values():
    VB = [X, A, {"name": "b"}]
    r = _run(_eq("x + log(a) - log(a) = 2", ["a = b - 3", "b = 2"], VB), "{2}")
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in _flags(r)
    r = _run(_eq("x**2 = 4", ["x > a", "a = b - 3", "b = 2", "a > 0"], VB), "{2}")
    assert r.verdict == "UNKNOWN" and "ir_inconsistent" in _flags(r)


def test_g9_controls_keep_their_verdicts():
    assert _run(_eq("x + log(a) - log(a) = 2", ["a = 1"], XA), "{2}").verdict == "CORRECT"
    assert _run(_eq("x**2 = a", ["a = 4"], XA), "{-2, 2}").verdict == "CORRECT"
    assert _run(_eq("x**2 = 4", ["x > a", "a = 0"], XA), "{2}").verdict == "CORRECT"
    assert _run(_eq("x**2 = 4", ["a = 1", "a > 0", "x > a"], XA), "{2}").verdict == "CORRECT"
    assert _run(_lim("sin(a*x)/x", "0", ["a = 2"], XA), "2", "value").verdict == "CORRECT"


# --- G10: undecided membership ------------------------------------------------------------------------------
def test_g10_t7_is_pi_and_undecided():
    import mpmath as mp
    from mathverify.certify.domain import _certified_compare, guard_roots, in_domain
    from mathverify.normalize.parse import build_namespace, parse_expr_str
    t7 = parse_expr_str(T7, build_namespace())
    with mp.workdps(80):
        assert abs(mp.mpf(str(sp.N(t7 - sp.pi, 90)))) < mp.mpf(10) ** -70
    assert _certified_compare(t7, sp.pi) is None
    x = sp.Symbol("x", real=True)
    dom = sp.Interval.open(sp.pi, sp.oo)
    assert in_domain(dom, t7) is None
    kept, rejected = guard_roots(sp.Eq(x - t7, 0), x, [t7], dom)
    assert kept == [] and rejected and rejected[0][1].startswith("definedness_undecided")


@pytest.mark.parametrize("where", ["given", "constraint", "dod"])
def test_g10_solve_equation_undecided_membership(where):
    if where == "given":
        q = _eq(f"x - ({T7}) = 0", ["x > pi"])
    elif where == "constraint":
        q = _eq(f"x - ({T7}) = 0", [], [{"name": "x", "domain": "real", "constraints": ["x > pi"]}])
    else:
        q = _eq(f"x - ({T7}) = 0", [], dod="x > pi")
    assert _run(q, "{" + T7 + "}").verdict == "UNKNOWN"
    assert _run(q, "{}").verdict == "UNKNOWN"


def test_g10_evaluate_undecided_membership():
    XY = [X, {"name": "y"}]
    for g in ["x > pi", "x < pi"]:
        r = _run(_ir("evaluate", {"expr": "y"}, [f"x = {T7}", "y = 7", g], XY, shape="scalar"), "7", "value")
        assert r.verdict == "UNKNOWN", g


@pytest.mark.parametrize("givens,vars_,payload", [
    # the solution x = T7 against the declared constraint x > pi (the domain): neither kept nor dropped
    ([f"x**2 = ({T7})**2", "y = x + 1"], [{"name": "x", "constraints": ["x > pi"]}, {"name": "y"}], f"{T7} + 1"),
    # against a constraint on two variables
    ([f"x**2 = ({T7})**2", "y**2 = 1", "z = x*y"], [X, {"name": "y", "constraints": ["x*y > pi"]}, {"name": "z"}],
     T7),
    # x <= pi holds at T7 = pi, but no check decides it: dropping T7 leaves 1 - T7 alone
    ([f"x**2 = ({T7})**2", "y = x + 1", "x <= pi"], [X, {"name": "y"}], f"1 - ({T7})"),
    ([f"x**2 = ({T7})**2", "y = x + 1", "x > pi"], [X, {"name": "y"}], f"1 + ({T7})"),
    # a chain: the And at T7 is undecided too (it holds, but no check proves it)
    ([f"x**2 = ({T7})**2", "y = x + 1", "0 < x <= pi"], [X, {"name": "y"}], f"1 + ({T7})"),
])
def test_g10_evaluate_solutions_neither_kept_nor_dropped(givens, vars_, payload):
    target = "z" if any(v["name"] == "z" for v in vars_) else "y"
    r = _run(_ir("evaluate", {"expr": target}, givens, vars_, shape="scalar"), payload, "value")
    assert r.verdict == "UNKNOWN"


def test_g10_evaluate_domain_of_discourse_undecided():
    """x > pi only as the domain of discourse: no constraint repeats it, the domain alone decides."""
    q = _ir("evaluate", {"expr": "y"}, [f"x**2 = ({T7})**2", "y = x + 1"], [X, {"name": "y"}], shape="scalar",
            dod="x > pi")
    assert _run(q, f"1 + ({T7})", "value").verdict == "UNKNOWN"


def test_g10_filter_and_inequalities_tri_state():
    from mathverify.certify.algebra import _meets_inequalities
    from mathverify.normalize.parse import build_namespace, parse_expr_str
    t7 = parse_expr_str(T7, build_namespace())
    x = sp.Symbol("x", real=True)
    assert _meets_inequalities({x: t7}, [sp.Gt(x, sp.pi)]) is None
    assert _meets_inequalities({x: t7}, [sp.Gt(x, 3)]) is True
    assert _meets_inequalities({x: t7}, [sp.Gt(x, 4)]) is False
    assert _meets_inequalities({x: 2}, [sp.And(sp.Gt(x, 0), sp.Lt(x, 1))]) is False


# --- TAN-01: ranges after the binding -----------------------------------------------------------------------
@pytest.mark.parametrize("rel,givens,payload", [
    ("x + Sum(k, (k, 1, n)) > 5", ["n = -3"], "Interval.open(2, oo)"),
    ("x + Sum(k, (k, 1, n)) > 5", ["n = -3"], "Interval.open(5, oo)"),
    ("x + Sum(k, (k, m, n)) > 5", ["m = 3", "n = 1"], "Interval.open(7, oo)"),
    ("x + Sum(k, (k, 1, n/2)) > 5", ["n = 7"], "Interval.open(-23/8, oo)"),
])
def test_tan01_reversed_or_fractional_range(rel, givens, payload):
    import time
    t0 = time.time()
    r = _run(_ineq(rel, givens, [X, N, KI, {"name": "m", "domain": "integer"}]), payload, "interval")
    assert r.verdict == "UNKNOWN"
    assert time.time() - t0 < 30


def test_tan01_side_condition_paths():
    S_ = "Sum(k, (k, 1, n))"
    V = [X, N, KI]
    assert _run(_eq("x**2 = 4", [f"x > {S_}", "n = -3"], V), "{}").verdict == "UNKNOWN"
    assert _run(_roots("x**2 - 4", [f"x > {S_}", "n = -3"], V), "0", "count").verdict == "UNKNOWN"
    assert _run(_ineq("x + Sum(k, (k, 1, n)) > 5", ["n = 3"], V), "Interval.open(-1, oo)",
                "interval").verdict == "CORRECT"


# --- TAN-09: conditions read after the binding --------------------------------------------------------------
def test_tan09_power_with_bound_exponent():
    q = _ineq("x**a < 4", ["a = 2"], XA)
    assert _run(q, "Interval.open(0, 2)", "interval").verdict == "INCORRECT"
    assert _run(q, "Interval.open(-2, 2)", "interval").verdict == "CORRECT"
    for e, a, right in [("x**a = 4", "2", "{-2, 2}"), ("x**a = 1/4", "-2", "{-2, 2}"), ("x**a = -8", "3", "{-2}")]:
        assert _run(_eq(e, [f"a = {a}"], XA), right).verdict != "INCORRECT", e
    h = _ineq("x**a < 4", ["a = 1/2"], XA)
    assert _run(h, "Interval.Ropen(0, 16)", "interval").verdict == "CORRECT"
    assert _run(_lim("x**a", "-1", ["a = 2"], XA), "1", "value").verdict == "CORRECT"


def test_tan09_free_exponent_keeps_the_cautious_rule():
    from mathverify.certify.domain import written_definedness
    from mathverify.normalize.parse import build_namespace
    ns = build_namespace()
    ns["a"] = sp.Symbol("a", real=True)
    x = ns["x"] = sp.Symbol("x", real=True)
    conds, _ = written_definedness("x**a", ns)
    assert sp.Gt(x, 0) in conds
    assert written_definedness("x**a", ns, {ns["a"]: sp.Integer(2)})[0] == []


# --- P1: pins and bound variables ---------------------------------------------------------------------------
F = "Integral(t**2, (t, 0, x))"


@pytest.mark.parametrize("ir,payload,kind", [
    (_ir("derivative", {"f": F, "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar"), "0", "value"),
    (_ir("derivative", {"f": F, "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar"), "4", "value"),
    (_ir("antiderivative", {"integrand": F, "var": "x"}, ["x = 2"], [X, T_], shape="expression"), "8*x/3",
     "expression"),
    (_ir("evaluate", {"expr": "Derivative(Integral(a*t, (t, 0, 1)), a)"}, ["a = 2"], [X, T_, A], shape="scalar"),
     "0", "value"),
    (_ir("evaluate", {"expr": "Sum(Integral(t, (t, 0, k)), (k, 1, 2))"}, ["k = 5"], [T_, KI], shape="scalar"),
     "25", "value"),
    (_ir("derivative", {"f": "f(x)", "var": "x", "at": "2"}, ["x = 2"], [X, T_], shape="scalar",
         functions=[{"name": "f", "args": ["x"], "expr": F}]), "0", "value"),
])
def test_p1_bound_or_task_variable_pinned(ir, payload, kind):
    r = _run(ir, payload, kind)
    assert r.verdict == "UNKNOWN" and "given_binds_a_bound_variable" in _flags(r)


def test_p1_hold_parametric_respects_binders():
    from mathverify.normalize.parse import PinnedBoundVariable, hold_parametric, substitute_free
    a, t, x, k = sp.symbols("a t x k", real=True)
    d = sp.Derivative(sp.Integral(a * t, (t, 0, 1)), a)
    with pytest.raises(PinnedBoundVariable):
        hold_parametric(d, {a: sp.Integer(2)})
    with pytest.raises(PinnedBoundVariable):
        hold_parametric(sp.Integral(t**2, (t, 0, x)), {x: sp.Integer(2)}, {"x"})
    assert hold_parametric(sp.Integral(a * t, (t, 0, 1)), {a: sp.Integer(2)}) == sp.Integral(2 * t, (t, 0, 1))
    s = sp.Sum(k**2, (k, 1, x))
    assert substitute_free(s, {k: sp.Integer(5), x: sp.Integer(3)}) == sp.Sum(k**2, (k, 1, 3))


def test_p1_namespace_protects_the_task_variable():
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import PinnedBoundVariable, build_namespace, parse_expr_str
    ir = ProblemIR.from_dict(_ir("solve_equation", {"equation": "x**2 = 4", "var": "x"}, ["x = 2", "a = 3"],
                                 [X, T_, A]))
    ns = build_namespace(ir)
    with pytest.raises(PinnedBoundVariable):
        parse_expr_str("Integral(t**2, (t, 0, x))", ns)
    assert str(parse_expr_str("Integral(t, (t, 0, a))", ns)) == "Integral(t, (t, 0, 3))"


def test_p1_step_and_controls():
    st = _ir("evaluate", {"expr": "1"}, ["a = 2"], [X, T_, A], shape="scalar")
    r = _run(st, "1", "value", [("compute", "Derivative(Integral(a*t, (t, 0, 1)), a) = 0")])
    statuses = [s["status"] for la in r.layers if la.layer == "steps.refute" for s in la.evidence.get("steps", [])]
    assert "verified" not in statuses
    ev = _ir("evaluate", {"expr": "f(x)"}, ["x = 2"], [X, T_], shape="scalar",
             functions=[{"name": "f", "args": ["x"], "expr": F}])
    assert _run(ev, "8/3", "value").verdict == "CORRECT"
    assert _run(ev, "4", "value").verdict == "INCORRECT"
    ok = _ir("evaluate", {"expr": "Integral(a*t, (t, 0, 1))"}, ["a = 2"], [T_, A], shape="scalar")
    assert _run(ok, "1", "value").verdict == "CORRECT"
