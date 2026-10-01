"""A `compute` step with a Sum, Product or definite Integral in symbols the premises pin (part 8,
30 Sep 2026; DECISIONS §76 (iii) left binders out).

Part (iii) re-checks a `compute` step refuted as an identity at the values the premises pin its
symbols to, but only for a claim without an operation. With n = 3 given, the right step
`Sum(k, (k, 1, n)) = 6` was checked as an identity in n and refuted at an n != 3, no instance of the
problem (principle 5): INCORRECT. A Sum, Product or definite Integral whose bound variables are not
pinned symbols is now substituted (xreplace reaches limits and bodies, never a bound variable); a Limit,
a Derivative, a Subs and an indefinite Integral stay out. A pinned limit must pass the parser's range
checks. Every case marked "8d86e7c" was measured refuted (INCORRECT) there
(denetim/2026-09-30/parca8/sonda.py: 54 cases, 12 not as expected before, 0 after).
"""
import pytest
import sympy as sp

from mathverify.steps.deterministic import _binders_keep_clear_of, _pins
from mathverify.verifier import verify

N = {"name": "n", "domain": "positive_integer"}
NR = {"name": "n", "domain": "real"}
K = {"name": "k", "domain": "integer"}
A = {"name": "a", "domain": "real"}
X = {"name": "x", "domain": "real"}


def _ir(expr, vars_, givens):
    return {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_),
            "givens": list(givens), "answer_shape": "scalar"}


def _run(ir, payload, steps):
    sol = {"claimed_answer": {"kind": "value", "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _steps(r):
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return layer.evidence.get("steps", [])


S3 = _ir("n*(n + 1)/2", [N], ["n = 3"])
A2 = _ir("a", [A], ["a = 2"])
RIGHT = [
    (S3, "6", [("compute", "Sum(k, (k, 1, n)) = 6")]),                                  # the audit's case
    (_ir("n*(n + 1)/2", [N, K], ["n = 3"]), "6", [("compute", "Sum(k, (k, 1, n)) = 6")]),   # k declared
    (_ir("Sum(k, (k, 1, n))", [N, K], ["n = 3"]), "6", [("compute", "Sum(k, (k, 1, n)) = 6")]),
    (_ir("factorial(n)", [N], ["n = 3"]), "6", [("compute", "Product(k, (k, 1, n)) = 6")]),
    (_ir("a**2/2", [A], ["a = 2"]), "2", [("compute", "Integral(x, (x, 0, a)) = 2")]),
    (_ir("a**2/2", [A, X], ["a = 2"]), "2", [("compute", "Integral(x, (x, 0, a)) = 2")]),
    (_ir("6*a", [A], ["a = 2"]), "12", [("compute", "Sum(a*k, (k, 1, 3)) = 12")]),        # the body
    (_ir("a**3/2", [A], ["a = 2"]), "4", [("compute", "Integral(a*x, (x, 0, a)) = 4")]),  # body and limit
    (S3, "6", [("compute", "Sum(k, (k, 1, n)) + n = 9")]),                              # outside too
    (_ir("n*(n + 1)/2", [N], ["n + 1 = 4"]), "6", [("eq", "n = 3"), ("compute", "Sum(k, (k, 1, n)) = 6")]),
    (_ir("a", [{"name": "a"}], ["a = 2"]), "2", [("compute", "a + Sum(a, (a, 1, 3)) = 8")]),  # index is another a
    (A2, "2", [("compute", "Product(k - a, (k, 1, 3)) = 0")]),
]
WRONG = [
    (S3, "7", [("compute", "Sum(k, (k, 1, n)) = 7")]),
    (S3, "5", [("compute", "Sum(k, (k, 1, n)) = 5")]),
    (S3, "6", [("compute", "Sum(k, (k, 1, n)) = 7")]),                                  # right answer
    (_ir("factorial(n)", [N], ["n = 3"]), "6", [("compute", "Product(k, (k, 1, n)) = 7")]),
    (_ir("a**2/2", [A], ["a = 2"]), "2", [("compute", "Integral(x, (x, 0, a)) = 3")]),
    (_ir("6*a", [A], ["a = 2"]), "12", [("compute", "Sum(a*k, (k, 1, 3)) = 13")]),
    (_ir("a**3/2", [A], ["a = 2"]), "4", [("compute", "Integral(a*x, (x, 0, a)) = 8")]),
    (_ir("n*(n + 1)/2", [dict(N, constraints=["n = 3"])], []), "6", [("compute", "Sum(k, (k, 1, n)) = 7")]),
    (_ir("a", [{"name": "a"}], ["a = 2"]), "2", [("compute", "a + Sum(a, (a, 1, 3)) = 9")]),
]


@pytest.mark.parametrize("ir,payload,steps", RIGHT)
def test_a_right_step_with_a_binder_in_pinned_symbols_is_verified(ir, payload, steps):
    """8d86e7c: the last step refuted, INCORRECT."""
    r = _run(ir, payload, steps)
    st = _steps(r)
    assert r.verdict == "CORRECT" and [s["status"] for s in st] == ["verified"] * len(steps), \
        [(s["status"], s.get("reason")) for s in st]
    ev = st[-1]["evidence"]
    if "Integral" in steps[-1][1]:
        # part iv (DECISIONS §80): the parse reads an Integral's parameter at the value a given pins it
        # to, so the claim is closed and checked as written, with no identity to refute first
        assert "pinned_by_premises" not in ev
    else:
        assert ev["pinned_by_premises"] and ev["identity_refuted"]


@pytest.mark.parametrize("ir,payload,steps", WRONG)
def test_a_wrong_step_with_a_binder_in_pinned_symbols_stays_refuted(ir, payload, steps):
    r = _run(ir, payload, steps)
    assert r.verdict == "INCORRECT" and _steps(r)[-1]["status"] == "refuted"


@pytest.mark.parametrize("ir,steps", [
    (_ir("n*(n + 1)/2", [N], []), [("compute", "Sum(k, (k, 1, n)) = 6")]),
    (_ir("n*(n + 1)/2", [N], ["n > 2"]), [("compute", "Sum(k, (k, 1, n)) = 6")]),
    (_ir("n*(n + 1)/2", [N], []), [("eq", "n = 3"), ("compute", "Sum(k, (k, 1, n)) = 6")]),  # solver's own n
    (_ir("a", [A], ["a = 3", "a = 2"]), [("compute", "Sum(a*k, (k, 1, 2)) = 9")]),         # two values
])
def test_a_step_in_symbols_not_pinned_is_still_checked_as_an_identity(ir, steps):
    """Control: nothing (or two values) pins the symbol, so the identity check stands (as on 8d86e7c). The
    case n**2 = 9 (no closed binding, n = 3 for a positive integer) was here: since part 10 the premises'
    finite set is checked point by point and the right step is verified (tests/test_parca10_sonlu_oncul.py)."""
    st = _steps(_run(ir, "6", steps))
    assert st[-1]["status"] == "refuted" and "pinned_by_premises" not in st[-1]["evidence"]


@pytest.mark.parametrize("steps,status", [
    ([("compute", "a*Limit(x**2, x, 1) = 2")], "verified"),
    ([("compute", "a + Limit(x, x, 1) = 3")], "verified"),
    ([("compute", "Derivative(a*x**2, x) = 4*x")], "verified"),
    ([("compute", "Limit(a*x, x, 1) = 2")], "verified"),
    ([("compute", "Integral(a*x, x) = x**2")], "verified"),
])
def test_a_limit_a_derivative_and_an_indefinite_integral_stay_out(steps, status):
    """Measured the same on 8d86e7c: SymPy's Limit.subs replaces the bound variable too, and these are
    not substituted. The first three are true at a = 2 and stayed refuted there (a known false rejection);
    since part 10 the identity's counterexample, at an a != 2, is no instance, and the claim is compared
    again with a confined to the premises' region {2}, without substitution. The last two were unknown there: since part iv (DECISIONS §80) the parse reads a parameter INSIDE an
    Integral or a Limit at the value a given pins it to (never the bound variable), so they are
    checked at a = 2 as written, not by the re-check."""
    st = _steps(_run(_ir("a", [A, X], ["a = 2"]), "2", steps))
    assert st[-1]["status"] == status and "pinned_by_premises" not in (st[-1].get("evidence") or {})


@pytest.mark.parametrize("ir,payload,claim", [
    (_ir("a", [dict(NR, constraints=["n = 0"]), A], ["a = 1"]), "1", "Sum(a*k, (k, 2, n)) = -1"),
    (_ir("a", [dict(NR, constraints=["n = 0"]), A], ["a = 1"]), "1", "Product(a*k, (k, 3, n)) = 1/2"),
    (_ir("a", [dict(NR, constraints=["n = 5/2"]), A], ["a = 1"]), "1", "Sum(a*k, (k, 1, n)) = 35/8"),
])
def test_a_pinned_range_the_parser_would_not_read_is_not_verified(ir, payload, claim):
    """n = 0 makes Sum(k, (k, 2, n)) Karr's -1 and n = 5/2 a range not an integer long: the parser does
    not read either written out. Pinned by the variable's constraint, the definedness check at the
    premises' point does not see n, so only the pinned re-check keeps the step from being verified."""
    st = _steps(_run(ir, payload, [("compute", claim)]))
    assert st[-1]["status"] == "unknown" and st[-1]["evidence"]["reason"].startswith("pinned_claim_not_read")


@pytest.mark.parametrize("ir,payload,claim", [
    (_ir("n", [NR], ["n = 5/2"]), "5/2", "Sum(k, (k, 1, n)) = 35/8"),
    (_ir("n", [NR], ["n = 0"]), "0", "Sum(k, (k, 2, n)) = -1"),
    (_ir("n", [NR], ["n = 0"]), "0", "Product(k, (k, 3, n)) = 1/2"),
    (_ir("a", [A], ["a = 1"]), "1", "Integral(1/x, (x, -1, a)) = 0"),
    (_ir("a", [A], ["a = 1"]), "1", "Integral(1/(x - a), (x, 0, 2)) = 0"),
    (_ir("a", [A], ["a = 0"]), "0", "Integral(1/x, (x, a, 1)) = oo"),
    (_ir("a", [A], ["a = -1"]), "-1", "Integral(sqrt(x), (x, a, 1)) = 2/3"),
    (_ir("a", [A], ["a = 2"]), "2", "Sum(1/(k - a), (k, 1, 3)) = 0"),
])
def test_a_pinned_value_that_leaves_the_claim_undefined_does_not_verify_it(ir, payload, claim):
    st = _steps(_run(ir, payload, [("compute", claim)]))
    assert st[-1]["status"] != "verified", st[-1]


def test_binders_keep_clear_of():
    a, k, n, x = sp.symbols("a k n x")
    assert _binders_keep_clear_of(sp.Eq(sp.Sum(k, (k, 1, n)), 6), {n})
    assert _binders_keep_clear_of(sp.Eq(sp.Product(a * k, (k, 1, n)) + sp.Integral(a * x, (x, 0, a)), 1), {a, n})
    assert _binders_keep_clear_of(sp.Eq(a * n, 6), {a, n})
    for claim, syms in [
        (sp.Eq(a + sp.Sum(a, (a, 1, 3)), 8), {a}),                   # the pinned symbol is also the index
        (sp.Eq(x + sp.Integral(x, (x, 0, 1)), 1), {x}),
        (sp.Eq(sp.Integral(a * x, x), x ** 2), {a, x}),               # indefinite
        (sp.Eq(sp.Integral(a * x, (x, a)), 1), {a}),                  # one limit only
        (sp.Eq(sp.Limit(a * x, x, 1), 2), {a}),
        (sp.Eq(sp.Sum(k, (k, 1, n)) + sp.Limit(x, x, 1), 7), {n}),
        (sp.Eq(sp.Derivative(a * x ** 2, x), 4 * x), {a, x}),
        (sp.Eq(sp.Subs(a * x, x, 1), 2), {a}),                        # any other binder
        (sp.Eq(a * sp.Subs(sp.Sum(k, (k, 1, x)), x, n), 6), {a, n}),
    ]:
        assert not _binders_keep_clear_of(claim, syms), claim


def test_pins_with_a_binder():
    a, k, n, x = sp.symbols("a k n x")
    assert _pins(sp.Eq(sp.Sum(k, (k, 1, n)), 6), [sp.Eq(n, 3)]) == {n: 3}
    assert _pins(sp.Eq(sp.Integral(a * x, (x, 0, a)), 4), [sp.Eq(a, 2)]) == {a: 2}
    assert _pins(sp.Eq(sp.Sum(a * k, (k, 1, n)), 6), [sp.Eq(n, 3)]) is None            # a not pinned
    assert _pins(sp.Eq(a + sp.Sum(a, (a, 1, 3)), 8), [sp.Eq(a, 2)]) is None            # pinned and bound
    assert _pins(sp.Eq(sp.Limit(a * x, x, 1), 2), [sp.Eq(a, 2)]) is None
    assert _pins(sp.Eq(sp.Integral(a * x, x), x ** 2), [sp.Eq(a, 2), sp.Eq(x, 1)]) is None
