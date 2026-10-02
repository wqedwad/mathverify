"""A condition on the solved variable that names another symbol (part vi of the third audit's re-run).

`Ctx.domain_for`, `certify.algebra` and `certify.counting` read a declared constraint, a given
inequality, the domain of discourse or a written condition only when it named the variable alone:
`x > b` was dropped silently. With the given b = 0, (-2, 2) was certified for x² < 4 and the right
(0, 2) refuted, count_roots gave x² − 4 two roots, count_integers counted 0 (solveset read the
binding b = 0 on x as the empty set); with b free, {-2, 2} was certified for x² = 4. A symbol the
givens pin is now read as its value; a condition that still names a free symbol makes the certificate
abstain (`condition_not_applied`). The same filters dropped a given EQUATION on the variable
(x³ = 8 next to x² = 4) and every given of count_roots and domain_of, and count_solutions ignored the
domain of discourse. Every case below was measured wrong on 4c2a2e4 unless marked a control
(denetim/2026-09-30/parca6/sonda.py).
"""
import pytest
import sympy as sp

from mathverify.certify.base import make_ctx
from mathverify.ir import ProblemIR
from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
B = {"name": "b", "domain": "real"}
A = {"name": "a", "domain": "real"}
XB = [X, B]
XBC = [dict(X, constraints=["x > b"]), B]


def _ir(kind, params, vars_, givens=(), shape="set", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


def _run(ir, payload, kind="set"):
    return verify(ir, {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []})


def _sources(pin):
    """x > b as a given, a declared constraint and the domain of discourse, next to `pin`."""
    return [(XB, ["x > b"] + pin, None), (XBC, list(pin), None), (XB, list(pin), "x > b")]


EQ = {"equation": "x**2 = 4", "var": "x"}
INEQ = {"inequality": "x**2 < 4", "var": "x"}
ROOTS = {"expr": "x**2 - 4", "var": "x"}
DOM = {"expr": "sqrt(4 - x**2)", "var": "x"}

# (kind, params, shape, right claim, wrong claim, claim kind) with x > b and b = 0
PINNED = [
    ("solve_equation", EQ, "set", "{2}", "{-2, 2}", "set"),
    ("solve_inequality", INEQ, "interval", "(0, 2)", "(-2, 2)", "interval"),
    ("count_roots", ROOTS, "count", 1, 2, "count"),
    ("domain_of", DOM, "interval", "(0, 2]", "[-2, 2]", "interval"),
]


# --- a parameter the givens pin is read as its value ---------------------------------------------

@pytest.mark.parametrize("src", range(3), ids=["given", "vars", "dod"])
@pytest.mark.parametrize("kind,params,shape,right,wrong,ck", PINNED, ids=[p[0] for p in PINNED])
def test_a_pinned_parameter_of_a_constraint_is_read_as_its_value(kind, params, shape, right, wrong, ck, src):
    vars_, givens, dod = _sources(["b = 0"])[src]
    ir = _ir(kind, params, vars_, givens, shape, dod)
    assert _run(ir, right, ck).verdict == "CORRECT"
    assert _run(ir, wrong, ck).verdict == "INCORRECT"


@pytest.mark.parametrize("ir,right,wrong,ck", [
    # the part (ii) shape, the binding written the other way round, two pinned symbols, a chain
    (_ir("solve_equation", EQ, [X, A], ["x > a", "a = 0"]), "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, XB, ["x > b", "0 = b"]), "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, XB + [{"name": "c", "domain": "real"}], ["x > b - c", "b = 1", "c = 1"]),
     "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, XB, ["b < x < 3", "b = 0"]), "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", {"var": "x"}, XB, ["x**2 = 4", "x > b", "b = 0"]), "{2}", "{-2, 2}", "set"),
    (_ir("solve_inequality", INEQ, XB, ["x > b", "b = 1/2"], "interval"), "(1/2, 2)", "(0, 2)", "interval"),
    # a written condition whose parameter a given pins
    (_ir("solve_inequality", {"inequality": "x**2 + 0*log(x - a) < 4", "var": "x"}, [X, A], ["a = 0"], "interval"),
     "(0, 2)", "(-2, 2)", "interval"),
    (_ir("count_roots", {"expr": "x**2 - 4 + 0*log(x - a)", "var": "x"}, [X, A], ["a = 0"], "count"), 1, 2, "count"),
    # the main inequality's own parameter
    (_ir("solve_inequality", {"inequality": "x**2 < a", "var": "x"}, [X, A], ["a = 4"], "interval"),
     "(-2, 2)", "(-4, 4)", "interval"),
    # evaluate on a domain of discourse with a pinned parameter
    (_ir("evaluate", {"expr": "x"}, XB, ["x**2 = 4", "b = 0"], "scalar", "x > b"), "2", "-2", "value"),
    # extremum on a domain of discourse with a pinned parameter: min of (x - 1)² on x >= 2 is 1
    (_ir("extremum", {"f": "(x - 1)**2", "var": "x", "which": "min"}, XB, ["b = 2"], "scalar", "x >= b"),
     "1", "0", "value"),
])
def test_more_pinned_parameter_shapes(ir, right, wrong, ck):
    assert _run(ir, right, ck).verdict == "CORRECT"
    assert _run(ir, wrong, ck).verdict == "INCORRECT"


# --- a binding given is no relation on the variable ----------------------------------------------

@pytest.mark.parametrize("givens", [["x**2 < 4", "x > b", "b = 0"], ["x**2 < 4", "b = 0"]])
def test_a_binding_among_the_inequality_givens_is_not_the_empty_set(givens):
    """solveset read b = 0 on x as ∅: the system's solution set was empty and {} was certified."""
    ir = _ir("solve_inequality", {"var": "x"}, XB, givens, "interval")
    right = "(0, 2)" if "x > b" in givens else "(-2, 2)"
    assert _run(ir, right, "interval").verdict == "CORRECT"
    assert _run(ir, "{}").verdict == "INCORRECT"


@pytest.mark.parametrize("vars_,givens,truth", [
    ([{"name": "x", "domain": "integer"}, B], ["x**2 < 10", "x > b", "b = 0"], 3),
    ([{"name": "x", "domain": "integer", "constraints": ["x > b"]}, B], ["x**2 < 10", "b = 0"], 3),
    ([{"name": "x", "domain": "integer"}, B], ["x**2 < 10", "b = 0"], 7),
])
def test_count_integers_reads_a_binding_as_a_value(vars_, givens, truth):
    ir = _ir("count_integers", {"var": "x"}, vars_, givens, "count")
    assert _run(ir, truth, "count").verdict == "CORRECT"
    assert _run(ir, 0, "count").verdict == "INCORRECT"


# --- a parameter no given pins: the certificate abstains -----------------------------------------

FREE = [
    ("solve_equation", EQ, "set", ["{-2, 2}"], "set"),
    ("solve_inequality", INEQ, "interval", ["(-2, 2)", "(0, 2)", "(b, 2)"], "interval"),
    ("count_roots", ROOTS, "count", [2, 1], "count"),
    ("domain_of", DOM, "interval", ["[-2, 2]", "(0, 2]"], "interval"),
]


@pytest.mark.parametrize("src", range(3), ids=["given", "vars", "dod"])
@pytest.mark.parametrize("kind,params,shape,claims,ck", FREE, ids=[p[0] for p in FREE])
def test_a_free_parameter_of_a_constraint_abstains(kind, params, shape, claims, ck, src):
    vars_, givens, dod = _sources([])[src]
    ir = _ir(kind, params, vars_, givens, shape, dod)
    for claim in claims:
        r = _run(ir, claim, ck)
        assert r.verdict == "UNKNOWN", claim
        assert "condition_not_applied" in r.flags, claim


@pytest.mark.parametrize("ir,claim,ck", [
    (_ir("solve_equation", {"equation": "x**2 + 1 + 0*log(x - a) = 5", "var": "x"}, [X, A]), "{-2, 2}", "set"),
    (_ir("solve_inequality", {"inequality": "x**2 + 0*log(x - a) < 4", "var": "x"}, [X, A], [], "interval"),
     "(-2, 2)", "interval"),
    (_ir("count_roots", {"expr": "x**2 - 4 + 0*log(x - a)", "var": "x"}, [X, A], [], "count"), 2, "count"),
    (_ir("solve_equation", EQ, XB + [{"name": "c", "domain": "real"}], ["x > b - c", "b = 1"]), "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, XB, ["b < x < 3"]), "{-2, 2}", "set"),
    (_ir("solve_equation", {"var": "x"}, XB, ["x**2 = 4", "x > b"]), "{-2, 2}", "set"),
    (_ir("solve_inequality", {"inequality": "x**2 < a", "var": "x"}, [X, A], [], "interval"), "(-2, 2)", "interval"),
    (_ir("count_integers", {"var": "x"}, [{"name": "x", "domain": "integer", "constraints": ["x > b"]}, B],
         ["x**2 < 10"], "count"), 7, "count"),
    (_ir("extremum", {"f": "(x - 1)**2", "var": "x", "which": "min"}, [dict(X, constraints=["x >= b"]), B], [],
         "scalar"), "0", "value"),
])
def test_more_free_parameter_shapes_abstain(ir, claim, ck):
    r = _run(ir, claim, ck)
    assert r.verdict == "UNKNOWN"
    assert "condition_not_applied" in r.flags


def test_a_side_condition_naming_an_undeclared_symbol_abstains():
    """It did not parse and was skipped as "not a relation": (-2, 2) was CORRECT."""
    ir = _ir("solve_inequality", INEQ, [X], ["x > b", "b = 0"], "interval")
    for claim in ("(-2, 2)", "(0, 2)"):
        r = _run(ir, claim, "interval")
        assert r.verdict == "UNKNOWN" and "given_not_applied" in r.flags


# --- a given equation on the variable restricts it -----------------------------------------------

@pytest.mark.parametrize("ir,right,wrong", [
    (_ir("solve_equation", EQ, [X], ["x**3 = 8"]), ("{2}", "set"), ("{-2, 2}", "set")),
    (_ir("solve_equation", EQ, [X, {"name": "y", "domain": "real"}], ["x + y = 3", "y = 1"]),
     ("{2}", "set"), ("{-2, 2}", "set")),
    (_ir("solve_equation", {"var": "x"}, [X], ["x**2 = 4", "x**3 = 8"]), ("{2}", "set"), ("{-2, 2}", "set")),
    (_ir("solve_inequality", INEQ, [X], ["x**3 = 1"], "interval"), ("{1}", "set"), ("(-2, 2)", "interval")),
    (_ir("count_roots", ROOTS, [X], ["x**3 = 8"], "count"), (1, "count"), (2, "count")),
])
def test_a_given_equation_on_the_variable_restricts_it(ir, right, wrong):
    assert _run(ir, *right).verdict == "CORRECT"
    assert _run(ir, *wrong).verdict == "INCORRECT"


def test_a_side_condition_the_pinned_values_make_false_leaves_no_solution():
    """b·x > 1 with b = 0 holds for no x (it was dropped as one on two symbols). Since part d4d (fourth audit
    G8) a given or constraint false at the values is a problem with no instance: the verifier abstains
    (ir_inconsistent) instead of certifying the empty set. Two values for b (b = 0, b = -5) the same."""
    for ir, claims in [(_ir("solve_equation", EQ, XB, ["b*x > 1", "b = 0"]), ("{}", "{-2, 2}")),
                       (_ir("solve_inequality", INEQ, XB, ["b*x > 1", "b = 0"], "interval"), ("{}",)),
                       (_ir("solve_equation", EQ, XB, ["x > b", "b = 0", "b = -5"]), ("{-2, 2}", "{2}"))]:
        for claim in claims:
            r = _run(ir, claim, "set")
            assert r.verdict == "UNKNOWN" and "ir_inconsistent" in r.flags


def test_the_task_equation_repeated_among_the_givens_is_no_side_condition():
    """exp(x) = 3 - x cannot be solved exactly: read as a side condition of itself it would make the
    verifier abstain (given_not_applied) where the claimed root 5 is simply wrong."""
    ir = _ir("solve_equation", {"equation": "exp(x) = 3 - x", "var": "x"}, [X], ["exp(x) = 3 - x"])
    assert _run(ir, "{5}").verdict == "INCORRECT"


def test_a_given_equation_with_a_free_symbol_or_unsolvable_abstains():
    ir = _ir("solve_equation", EQ, [X, {"name": "y", "domain": "real"}], ["x + y = 3"])
    assert _run(ir, "{-2, 2}").verdict == "UNKNOWN"
    r = _run(_ir("solve_equation", EQ, [X], ["sin(x) = x/2"]), "{-2, 2}")
    assert r.verdict == "UNKNOWN" and "given_not_applied" in r.flags


# --- count_roots, domain_of, count_solutions read the domain -------------------------------------

@pytest.mark.parametrize("vars_,givens,dod", [
    ([dict(X, constraints=["x > 0"])], [], None), ([X], ["x > 0"], None), ([X], [], "x > 0")])
def test_count_roots_counts_on_the_domain(vars_, givens, dod):
    ir = _ir("count_roots", ROOTS, vars_, givens, "count", dod)
    assert _run(ir, 1, "count").verdict == "CORRECT"
    assert _run(ir, 2, "count").verdict == "INCORRECT"


def test_domain_of_reads_a_given_inequality():
    ir = _ir("domain_of", DOM, [X], ["x > 0"], "interval")
    assert _run(ir, "(0, 2]", "interval").verdict == "CORRECT"
    assert _run(ir, "[-2, 2]", "interval").verdict == "INCORRECT"


XN = {"name": "x", "domain": "nonneg_integer"}
YN = {"name": "y", "domain": "nonneg_integer"}
BN = {"name": "b", "domain": "nonneg_integer"}
B2 = {"bounds": {"x": ["0", "4"], "y": ["0", "4"]}}
B3 = {"bounds": {"x": ["0", "4"], "y": ["0", "4"], "b": ["0", "4"]}}


@pytest.mark.parametrize("params,vars_,givens,dod,truth,wrong", [
    (B2, [XN, YN], ["x + y = 4"], "x > 2", 2, 5),
    (B3, [XN, YN, BN], ["x + y = 4", "x > b", "b = 2"], None, 2, 5),
    (B3, [dict(XN, constraints=["x > b"]), YN, BN], ["x + y = 4", "b = 2"], None, 2, 5),
    # controls: a condition between counted variables is part of the count (unchanged)
    (B3, [XN, YN, BN], ["x + y = 4", "x > b"], None, 10, 25),
    (B2, [dict(XN, constraints=["x > y"]), YN], ["x + y = 4"], None, 2, 5),
    (B2, [XN, YN], ["x + y = 4"], None, 5, 2),
])
def test_count_solutions_reads_the_domain_of_discourse(params, vars_, givens, dod, truth, wrong):
    ir = _ir("count_solutions", params, vars_, givens, "count", dod)
    assert _run(ir, truth, "count").verdict == "CORRECT"
    assert _run(ir, wrong, "count").verdict == "INCORRECT"


# --- controls: unchanged ---------------------------------------------------------------------------

@pytest.mark.parametrize("ir,right,wrong,ck", [
    (_ir("solve_equation", EQ, [X], ["x > 0"]), "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, [dict(X, constraints=["x > 0"])]), "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, [X], [], "set", "x > 0"), "{2}", "{-2, 2}", "set"),
    (_ir("solve_equation", EQ, [X]), "{-2, 2}", "{2}", "set"),
    (_ir("solve_inequality", INEQ, [X], ["x > 0"], "interval"), "(0, 2)", "(-2, 2)", "interval"),
    (_ir("solve_inequality", INEQ, [X], [], "interval"), "(-2, 2)", "(0, 2)", "interval"),
    (_ir("count_roots", ROOTS, [X], [], "count"), 2, 1, "count"),
    (_ir("count_roots", {"expr": "x**2 - 4", "var": "x", "lo": "0"}, [X], [], "count"), 1, 2, "count"),
    (_ir("domain_of", DOM, [dict(X, constraints=["x > 0"])], [], "interval"), "(0, 2]", "[-2, 2]", "interval"),
    (_ir("count_integers", {"var": "x"}, [{"name": "x", "domain": "integer"}], ["x**2 < 10", "x > 0"], "count"),
     3, 7, "count"),
    (_ir("evaluate", {"expr": "x*y"}, [dict(X, constraints=["x > y"]), {"name": "y", "domain": "real"}],
         ["x + y = 5", "x - y = 1"], "scalar"), "6", "5", "value"),
    (_ir("evaluate", {"expr": "x"}, XB, ["x**2 = 4", "x > b", "b = 0"], "scalar"), "2", "-2", "value"),
    # the task's own equation repeated among the givens is no side condition
    (_ir("solve_equation", EQ, [X], ["x**2 = 4"]), "{-2, 2}", "{2}", "set"),
])
def test_controls_single_variable_and_joint_constraints_unchanged(ir, right, wrong, ck):
    assert _run(ir, right, ck).verdict == "CORRECT"
    assert _run(ir, wrong, ck).verdict == "INCORRECT"


@pytest.mark.parametrize("ir,claim,ck", [
    # a parametric answer: the equation's own condition x - a >= 0 is checked at each root
    (_ir("solve_equation", {"equation": "sqrt(x - a) = 2", "var": "x"}, [X, A]), "{a + 4}", "set"),
    # the expression's own condition is what domain_of solves
    (_ir("domain_of", {"expr": "sqrt(x - a)", "var": "x"}, [X, A], [], "interval"), "[a, oo)", "interval"),
])
def test_controls_parametric_answers_stay_certified(ir, claim, ck):
    assert _run(ir, claim, ck).verdict == "CORRECT"


def test_a_root_the_guard_cannot_decide_leaves_the_solution_set_open():
    """√(x − a) = √(2 − x) has the root a/2 + 1 only for a <= 2. The guard could not decide it and
    the solvers' agreement was read as completeness: ∅ was certified. The equation's own condition
    is exempt from condition_not_applied (checked at each root), so this completeness rule is what
    keeps the exemption sound."""
    ir = _ir("solve_equation", {"equation": "sqrt(x - a) = sqrt(2 - x)", "var": "x"}, [X, A])
    assert _run(ir, "{}").verdict == "UNKNOWN"


# --- the context helpers ---------------------------------------------------------------------------

def _ctx(ir):
    return make_ctx(ProblemIR.from_dict(ir))


def test_on_var_reads_bindings_and_lists_free_symbols():
    ctx = _ctx(_ir("solve_inequality", {"var": "x"}, XB + [{"name": "c", "domain": "real"}],
                   ["x**2 < 4", "x > b", "b = 0", "x < c"], "interval"))
    x, b, c = ctx.sym("x"), ctx.sym("b"), ctx.sym("c")
    kept, unbound = ctx.on_var(ctx.givens(), x)
    assert kept == [x**2 < 4, x > 0]
    assert unbound == [x < c]
    assert ctx.bindings() == {b: 0}


def test_unapplied_conditions_and_discourse():
    ctx = _ctx(_ir("solve_equation", EQ, XBC, ["b = 0"], dod="x < b + 3"))
    x = ctx.sym("x")
    assert ctx.discourse(x) == sp.Interval.open(-sp.oo, 3)
    assert ctx.domain_for(x) == sp.Interval.open(0, 3)
    assert ctx.unapplied_conditions(x) == []
    ctx = _ctx(_ir("solve_equation", EQ, XBC, [], dod="x < b + 3"))
    x = ctx.sym("x")
    assert ctx.unapplied_conditions(x) == ["x < b + 3", "x > b"]
    ctx = _ctx(_ir("solve_equation", {"equation": "x**2 + 0*log(x - a) = 4", "var": "x"}, [X, A]))
    x, a = ctx.sym("x"), ctx.sym("a")
    assert ctx.unapplied_conditions(x) == [x - a > 0]
    assert ctx.unapplied_conditions(x, enforced=[x - a > 0]) == []
