"""A symbol of the problem that a given pins to one value (third audit's N7, V15 S1; DECISIONS §75).

N7: `certify.wordproblem` checked `solve_equation` with z3 over the equation and only the
single-variable inequality givens, so every other symbol was free. The model {x: 0, a: 0} made the
right {-2, 2} of x² = a with a = 4 "miss a root" (INCORRECT), and x² + a² = 0 with a = 4 had {0}
certified (CORRECT). A claimed root was also checked only for SOME value of a free parameter, so
{-√a, √a, 2} for x² = a was certified. S1: a `compute` step in the problem's parameters
("f(2) = 2" for f = x³ + ax² + bx) was checked as an identity in them and refuted at a = b = 0,
which violates the givens. Every case below was measured wrong on 98fe2a0 unless marked a control.
"""
import pytest
import sympy as sp

from mathverify.certify.base import closed_binding
from mathverify.steps.deterministic import _pins
from mathverify.verifier import verify

XA = [{"name": "x", "domain": "real"}, {"name": "a", "domain": "real"}]
XY = [{"name": "x", "domain": "real"}, {"name": "y", "domain": "real"}]
XAN = [XA[0], {"name": "a", "domain": "nonneg_real"}]


def _eq(equation, givens, var="x", vars_=XA):
    return {"task": {"kind": "solve_equation", "params": {"equation": equation, "var": var}},
            "vars": vars_, "givens": list(givens), "answer_shape": "set"}


def _run(ir, payload, kind="set", steps=()):
    sol = {"claimed_answer": {"kind": kind, "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _layer(r, name):
    return next(layer for layer in r.layers if layer.layer == name)


def _steps(r):
    return [s["status"] for s in _layer(r, "steps.refute").evidence.get("steps", [])]


A4 = _eq("x**2 = a", ["a = 4"])
AI = _eq("x**2 = a", ["a = integrate(2*x, (x, 0, 2))"])
SQ = _eq("sqrt(y - x) = 2", ["x = 1"], var="y", vars_=XY)
IN_GIVENS = {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": XA,
             "givens": ["x**2 = a", "a = 4"], "answer_shape": "set"}


# --- N7: the given's value reaches z3 ------------------------------------------------------------

@pytest.mark.parametrize("ir,claim", [
    (A4, "{-2, 2}"), (AI, "{-2, 2}"), (SQ, "{5}"),                      # the audit's three cases
    (_eq("x**2 = a", ["4 = a"]), "{-2, 2}"), (_eq("x**2 = a", ["a = 9/4"]), "{-3/2, 3/2}"),
    (_eq("x - a = 1", ["a = 2"]), "{3}"), (_eq("x - a = 1", ["a = 2"]), "{a + 1}"),
    (_eq("x**2 + a**2 = 0", ["a = 0"]), "{0}"),                         # control: CORRECT before too
    (IN_GIVENS, "{-2, 2}"),                                              # the equation as a given
    (_eq("x**2 = a", ["a = 4", "x > a - 4"]), "{2}"),                   # a given in x and a
])
def test_a_right_root_set_is_accepted_when_a_given_pins_the_parameter(ir, claim):
    r = _run(ir, claim)
    assert r.verdict == "CORRECT", [(la.layer, la.verdict, la.evidence.get("reason")) for la in r.layers]
    assert _layer(r, "certify.wordproblem").verdict == "pass"


@pytest.mark.parametrize("ir,claim", [
    (A4, "{2}"), (A4, "{-2, 2, 3}"), (A4, "{4}"), (A4, "{-4, 4}"), (A4, "{}"),
    (AI, "{2}"), (AI, "{4}"), (SQ, "{3}"), (SQ, "{4, 5}"),
    (_eq("x**2 = a", ["a = 9/4"]), "{3/2}"), (_eq("x - a = 1", ["a = 2"]), "{0}"),
    (_eq("x**2 + a**2 = 0", ["a = 4"]), "{0}"),                         # CORRECT before: a = 4 ignored
    (IN_GIVENS, "{2}"),
    (_eq("x**2 = a", ["a = 4", "x > a - 4"]), "{-2, 2}"),               # -2 violates x > 0
])
def test_a_wrong_root_set_stays_refuted(ir, claim):
    assert _run(ir, claim).verdict == "INCORRECT"


def test_a_wrong_set_is_refuted_by_the_given_not_by_a_model_that_violates_it():
    """{4} and {-2, 2, 3} are refuted because 4 and 3 are no roots once a = 4, not by the model
    {x: 0, a: 0} that made every claim "miss a root"."""
    for claim in ("{4}", "{-2, 2, 3}"):
        wp = _layer(_run(A4, claim), "certify.wordproblem")
        assert wp.verdict == "fail" and wp.evidence["reason"] == "refuted"
    wp = _layer(_run(A4, "{2}"), "certify.wordproblem")
    assert wp.evidence["reason"] == "missing_root" and wp.evidence["z3"]["other_model"]["a"] == "4"


@pytest.mark.parametrize("ir,claim", [
    (_eq("x**2 = a", ["a**2 = 16"]), "{-2, 2}"),                        # a = -4 leaves no real root
    (_eq("x**2 = a", ["a = 4", "a = 9"]), "{-2, 2}"),                   # no instance of the problem
    (_eq("x**2 + a**2 = 0", []), "{0}"),                                # a root only at a = 0
    (_eq("x**2 + a**2 = 0", ["a >= 0"]), "{0}"),
    (_eq("x**2 = a", []), "{-sqrt(a), sqrt(a), 2}"),                    # 2 is a root only at a = 4
    (_eq("x - a = 1", []), "{a + 1, 0}"),
    (_eq("x**2 = a", [], vars_=XAN), "{-sqrt(a), sqrt(a), 0}"),
])
def test_a_claim_true_for_one_value_of_a_free_parameter_is_not_certified(ir, claim):
    """CORRECT before: each claimed root was checked for SOME value of the parameter."""
    r = _run(ir, claim)
    assert r.verdict != "CORRECT"
    assert _layer(r, "certify.wordproblem").verdict != "pass"


def test_what_the_z3_layer_cannot_use_makes_it_abstain_not_refute():
    """a + 1 = 5 pins a without the form a = c; x = 2 next to x² = 4 is a system. Both were
    ignored: the first made {-2, 2} "miss a root" (INCORRECT)."""
    wp = _layer(_run(_eq("x**2 = a", ["a + 1 = 5"]), "{-2, 2}"), "certify.wordproblem")
    assert wp.verdict == "unknown" and wp.evidence["reason"] == "parameters_not_pinned_by_the_givens"
    wp = _layer(_run(_eq("x**2 = 4", ["x = 2"], vars_=XA[:1]), "{-2, 2}"), "certify.wordproblem")
    assert wp.verdict == "unknown" and wp.evidence["reason"].startswith("given_equation_in_the_variable")
    wp = _layer(_run(_eq("x**2 = a", ["a = 4", "a = 9"]), "{-2, 2}"), "certify.wordproblem")
    assert wp.verdict == "unknown" and wp.evidence["reason"].startswith("givens_without_an_instance")


def test_a_given_reached_through_another_given_is_read():
    """b = 3 constrains the equation only through a = b + 1: left out, a was free and {-2, 2}
    "missed" the root 3 (a = 9). a is not pinned in the form a = c, so the layer abstains."""
    ir = _eq("x**2 = a", ["a = b + 1", "b = 3"], vars_=XA + [{"name": "b", "domain": "real"}])
    r = _run(ir, "{-2, 2}")
    assert r.verdict != "INCORRECT" and _layer(r, "certify.wordproblem").verdict == "unknown"
    assert _run(ir, "{-2, 2, 3}").verdict == "INCORRECT"


B = {"name": "b", "domain": "real"}


@pytest.mark.parametrize("vars_,givens,dod", [
    ([dict(XA[0], constraints=["x > b"]), B], ["b = 0"], None),        # the variable's own constraint
    ([XA[0], B], ["x > b", "b = 0"], None),                             # a given
    ([XA[0], B], ["b = 0"], "x > b"),                                   # the domain of discourse
])
def test_a_parameter_of_a_constraint_on_the_variable_is_read(vars_, givens, dod):
    """x² = 4 with x > b and b = 0: z3 left b free (b = 0 was reached only through the constraint),
    so -2 was a root (b = -3) and {-2, 2} was certified. The z3 layer now refutes -2 and accepts {2};
    the algebra layer still drops x > b (a separate finding), so the verdict is UNKNOWN, not CORRECT."""
    ir = _eq("x**2 = 4", givens, vars_=vars_)
    if dod:
        ir["domain_of_discourse"] = dod
    r = _run(ir, "{-2, 2}")
    assert r.verdict != "CORRECT"
    assert _layer(r, "certify.wordproblem").verdict == "fail"
    assert _layer(_run(ir, "{2}"), "certify.wordproblem").verdict == "pass"


def test_a_free_parameter_of_a_constraint_on_the_variable_blocks_the_z3_certificate():
    ir = _eq("x**2 = 4", [], vars_=[dict(XA[0], constraints=["x > b"]), B])
    wp = _layer(_run(ir, "{-2, 2}"), "certify.wordproblem")
    assert wp.verdict == "unknown" and wp.evidence["z3"]["free_parameters"] == ["b"]


def test_a_value_in_another_symbol_does_not_pin():
    """a = b (a variable's own constraint) leaves a as free as b: {0} for x² + a² = 0 holds only
    at a = 0 and must not be certified."""
    ir = _eq("x**2 + a**2 = 0", [], vars_=[XA[0], {"name": "a", "domain": "real", "constraints": ["a = b"]},
                                           {"name": "b", "domain": "real"}])
    r = _run(ir, "{0}")
    assert r.verdict != "CORRECT" and _layer(r, "certify.wordproblem").verdict != "pass"


@pytest.mark.parametrize("ir,claim", [
    (_eq("x - a = 1", []), "{a + 1}"),
    (_eq("(x - 1)*(x - a) = 0", []), "{1, a}"),
    (_eq("x**2 = a", [], vars_=XAN), "{-sqrt(a), sqrt(a)}"),
])
def test_a_parametric_answer_is_still_certified_by_the_algebra_layer(ir, claim):
    """Control: the z3 layer abstains on a free parameter, the algebra layer still proves these."""
    r = _run(ir, claim)
    assert r.verdict == "CORRECT" and _layer(r, "certify.algebra").verdict == "pass"


def test_an_unrelated_given_is_not_read():
    """Control: a given about a symbol the equation never meets does not reach z3."""
    ir = _eq("x**2 = 4", ["b = pi"], vars_=XA[:1] + [{"name": "b", "domain": "real"}])
    r = _run(ir, "{-2, 2}")
    assert r.verdict == "CORRECT" and _layer(r, "certify.wordproblem").verdict == "pass"


def test_closed_binding():
    a, b = sp.symbols("a b", real=True)
    assert closed_binding(sp.Eq(a, 4)) == (a, 4)
    assert closed_binding(sp.Eq(4, a)) == (a, 4)
    assert closed_binding(sp.Eq(a, sp.sqrt(2))) == (a, sp.sqrt(2))
    c = sp.Symbol("c")               # no assumption: Eq(c, I) and Eq(c, oo) stay relations
    for rel in (sp.Eq(a ** 2, 16), sp.Eq(a + 1, 5), sp.Eq(a, b), sp.Eq(c, sp.oo), sp.Eq(c, sp.I),
                sp.Eq(c, 2 + sp.I), sp.Eq(a, sp.Integral(b, (b, 0, 1))), a > 4):
        assert isinstance(rel, (sp.Eq, sp.StrictGreaterThan)) and closed_binding(rel) is None, rel


# --- S1: a compute step in the problem's parameters ----------------------------------------------

AB = [{"name": "a"}, {"name": "b"}]
TUR = {"task": {"kind": "evaluate", "params": {"expr": "f(2)"}}, "vars": AB,
       "functions": [{"name": "f", "expr": "x**3 + a*x**2 + b*x", "args": ["x"], "params": ["a", "b"]}],
       "givens": ["at(diff(f(x), x), x, 1) = 0", "f(1) = -3"], "answer_shape": "scalar"}
PLAIN = {"task": {"kind": "evaluate", "params": {"expr": "a*b"}}, "vars": AB,
         "givens": ["a + b = 5", "a - b = 1"], "answer_shape": "scalar"}
LIN = {"task": {"kind": "evaluate", "params": {"expr": "f(4)"}}, "vars": AB,
       "functions": [{"name": "f", "expr": "a*x + b", "args": ["x"], "params": ["a", "b"]}],
       "givens": ["a + b = 5", "a - b = 1"], "answer_shape": "scalar"}
TUR_STEPS = [("eq", "3 + 2*a + b = 0"), ("eq", "1 + a + b = -3"), ("eq", "a = 1"), ("eq", "b = -5")]
AB_STEPS = [("eq", "a = 3"), ("eq", "b = 2")]


@pytest.mark.parametrize("ir,steps,claim", [
    (TUR, TUR_STEPS + [("compute", "f(2) = 2")], "2"),
    (PLAIN, AB_STEPS + [("compute", "a*b = 6")], "6"),
    (LIN, AB_STEPS + [("compute", "f(4) = 14")], "14"),
])
def test_a_right_compute_step_in_pinned_parameters_is_verified(ir, steps, claim):
    r = _run(ir, claim, kind="value", steps=steps)
    assert r.verdict == "CORRECT" and _steps(r) == ["verified"] * len(steps)
    assert _layer(r, "steps.refute").evidence["steps"][-1]["evidence"]["pinned_by_premises"]


@pytest.mark.parametrize("ir,steps,claim", [
    (TUR, TUR_STEPS + [("compute", "f(2) = 3")], "2"),
    (PLAIN, AB_STEPS + [("compute", "a*b = 5")], "6"),
    (LIN, AB_STEPS + [("compute", "f(4) = 13")], "14"),
])
def test_a_wrong_compute_step_in_pinned_parameters_stays_refuted(ir, steps, claim):
    r = _run(ir, claim, kind="value", steps=steps)
    assert r.verdict == "INCORRECT" and _steps(r)[-1] == "refuted"


def test_only_a_proved_premise_pins_a_symbol():
    """The solver's own `a = 7` about a symbol no given constrains is a definition (skipped), not
    a proved value: "a*b = 14" is still checked as an identity in a, and a = 0 with b = 2 is an
    instance of the problem that refutes it."""
    ir = {"task": {"kind": "evaluate", "params": {"expr": "a*b"}}, "vars": AB, "givens": ["b = 2"],
          "answer_shape": "scalar"}
    r = _run(ir, "14", kind="value", steps=[("eq", "a = 7"), ("compute", "a*b = 14")])
    assert _steps(r) == ["skipped", "refuted"]


def test_a_value_proved_in_another_case_branch_does_not_pin():
    """In the branch x < 0 of x² = 4 the proved x = -2 pins x; the x = 2 of the other branch does
    not. "x**3 = -8" was refuted as an identity in x (x = 0 is no root)."""
    ir = {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": XA[:1], "givens": ["x**2 = 4"],
          "answer_shape": "set"}
    sol = {"claimed_answer": {"kind": "set", "payload": "{-2, 2}"}, "steps": [
        {"id": "s1", "kind": "case", "claim": "x > 0", "from": [], "text": ""},
        {"id": "s2", "kind": "eq", "claim": "x = 2", "from": ["s1"], "text": ""},
        {"id": "s3", "kind": "case", "claim": "x < 0", "from": [], "text": ""},
        {"id": "s4", "kind": "eq", "claim": "x = -2", "from": ["s3"], "text": ""},
        {"id": "s5", "kind": "compute", "claim": "x**3 = -8", "from": ["s4"], "text": ""}]}
    r = verify(ir, sol)
    assert _steps(r) == ["skipped", "verified", "skipped", "verified", "verified"] and r.verdict == "CORRECT"
    sol["steps"][4]["claim"] = "x**3 = 8"
    assert _steps(verify(ir, sol))[4] == "refuted"


def test_a_wrong_identity_without_premises_stays_refuted():
    """Control: nothing pins x, so the identity check stands."""
    ir = {"task": {"kind": "simplify_expression", "params": {"expr": "(x + 1)**2"}}, "vars": XA[:1],
          "givens": [], "answer_shape": "expression"}
    r = _run(ir, "x**2 + 2*x + 1", kind="expression", steps=[("compute", "(x + 1)**2 = x**2 + 1")])
    assert r.verdict == "INCORRECT" and _steps(r) == ["refuted"]


def test_pins():
    a, b, x = sp.symbols("a b x", real=True)
    assert _pins(sp.Eq(a * b, 6), [sp.Eq(a, 3), sp.Eq(b, 2)]) == {a: 3, b: 2}
    assert _pins(sp.Eq(a * b, 6), [sp.Eq(a, 3)]) is None                          # b not pinned
    assert _pins(sp.Eq(a * b, 6), [sp.Eq(a, 3), sp.Eq(b, 2), sp.Eq(a, 4)]) is None  # two values
    assert _pins(sp.Eq(a * b, 6), [sp.Eq(a, 3), sp.Eq(b, 2), sp.Eq(a, sp.sqrt(9))]) == {a: 3, b: 2}
    # an operation whose bound variable a substitution could reach (a definite Integral, Sum or
    # Product is substituted since part 8: tests/test_parca8_sabitlenmis_toplam.py)
    assert _pins(sp.Eq(sp.Limit(a * x, x, 1), 2), [sp.Eq(a, 2)]) is None
    assert _pins(a * b > 6, [sp.Eq(a, 3), sp.Eq(b, 2)]) is None
