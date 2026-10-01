"""A step refuted where a Sum/Product range OF THE CLAIM runs backwards (part 11, 1 Oct 2026).

Below the empty range (hi < lo - 1) SymPy reads a Sum or Product by Karr's convention (Σ_{k=3}^{1} k = -2,
Π_{k=3}^{1} k = 1/2); the curriculum reads the empty sum (0) or nothing at all. The value there is a
convention, so it neither verifies nor refutes (DECISIONS §80-§81). Part 9 and part 10 abstained at the
problem's own reversed points (`Ctx.reversed_region`), and a step that wrote Karr's value was already
unknown (`claim_undefined_at_the_premises_point`); but the refutation was not guarded. Measured on 65b699e
and again on 69d9ec2: with the given n = 1 the eq step `Sum(k, (k, 3, n)) = 0` was refuted at {n: 1} with
Karr's -2 and a solution with the right answer was INCORRECT; the same for n = -2 and `Sum(k, (k, 1, n)) = 0`,
`Product(k, (k, 3, n)) = 1`, the LaTeX `\\sum_{k=3}^{n} k = 0` and the compute step
`floor(Sum(k, (k, 3, n))) = 0` (floor evaluates the pinned Sum, so the parser's range check never saw it).

Now (`steps.deterministic`): a point where a range of the claim is not proved to run forward
(`_range_spans`, `_runs_backwards_at`; `certify.domain.is_range_span`) is skipped by the premises' routes
(`_check_eq_in`, `_set_counterexample`) and by the check at a point (`_check_at`), so another point may
still refute the step; and a refutation found there anyway (a pinned value, a random point) is withdrawn
in `check_steps` (`_refuted_where_backwards`).

The tests marked "69d9ec2" fail there (measured: see the commit message).
"""
from __future__ import annotations

import pytest
import sympy as sp

from mathverify.verifier import verify

N = {"name": "n", "domain": "integer"}
K = {"name": "k", "domain": "integer"}
X = {"name": "x", "domain": "real"}


def _ir(expr, vars_, givens=()):
    return {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": "scalar"}


def _run(ir, payload, kind, claim):
    sol = {"claimed_answer": {"kind": "value", "payload": payload},
           "steps": [{"id": "s1", "kind": kind, "claim": claim, "from": [], "text": ""}]}
    return verify(ir, sol)


def _step(r):
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return layer.evidence["steps"][-1]


def _x5(n):
    """x + 1 with x = 5 and the given n: two symbols, the premises' solutions (route 1)."""
    return _ir("x + 1", [X, K, N], ["x = 5", f"n = {n}"])


def _alone(n):
    """n + 1 with the given n: one symbol, the premises' solution set (route 0)."""
    return _ir("n + 1", [K, N], [f"n = {n}"])


# ------------------------------------------------------------------ the claim's range backwards: no refutation
BACKWARDS = [
    (_x5(1), "6", "eq", "Sum(k, (k, 3, n)) = 0"),                    # the finding
    (_x5(-2), "6", "eq", "Sum(k, (k, 1, n)) = 0"),
    (_x5(1), "6", "eq", "Product(k, (k, 3, n)) = 1"),
    (_x5(1), "6", "eq", r"\sum_{k=3}^{n} k = 0"),
    (_x5(1), "6", "eq", "Sum(k, (k, 3, n)) + 1 = 1"),
    (_x5(1), "6", "eq", "2*Sum(k, (k, 3, n)) = 0"),
    (_x5(1), "6", "compute", "floor(Sum(k, (k, 3, n))) = 0"),        # the pinned value
    (_x5(-2), "6", "compute", "floor(Sum(k, (k, 1, n))) = 0"),
    (_x5(1), "6", "compute", "floor(Product(k, (k, 3, n))) = 1"),
    (_alone(1), "2", "eq", "Sum(k, (k, 3, n)) = 0"),
    (_alone(-2), "-1", "eq", "Sum(k, (k, 1, n)) = 0"),
    (_alone(1), "2", "compute", "floor(Sum(k, (k, 3, n))) = 0"),
    (_alone(1), "2", "eq", "Product(k, (k, 3, n)) = 1"),             # route 0's set: {1}
    (_alone(1), "2", "eq", "floor(Sum(k, (k, 3, n))) = 0"),
    # wrong under every reading, but the value there is a convention: no counterexample
    (_x5(1), "6", "eq", "Sum(k, (k, 3, n)) = 7"),
    (_x5(1), "6", "compute", "floor(Sum(k, (k, 3, n))) = 7"),
]


@pytest.mark.parametrize("ir,payload,kind,claim", BACKWARDS, ids=[f"{c[1]}|{c[2]}|{c[3]}" for c in BACKWARDS])
def test_a_step_where_its_range_runs_backwards_is_not_refuted(ir, payload, kind, claim):
    """69d9ec2: refuted with Karr's value, INCORRECT."""
    r = _run(ir, payload, kind, claim)
    st = _step(r)
    assert st["status"] == "unknown", st
    assert r.verdict != "INCORRECT", (r.verdict, st)


def test_karrs_value_is_neither_verified_nor_refuted():
    """Unknown before and after: the guard on verification (`claim_undefined_at_the_premises_point`)."""
    for kind, claim in (("eq", "Sum(k, (k, 3, n)) = -2"), ("compute", "floor(Sum(k, (k, 3, n))) = -2")):
        st = _step(_run(_x5(1), "6", kind, claim))
        assert st["status"] == "unknown", (claim, st)


# ------------------------------------------------------------------ forward or empty: decided as before
FORWARD = [
    (_x5(5), "6", "eq", "Sum(k, (k, 3, n)) = 0", "refuted"),
    (_x5(5), "6", "eq", "Sum(k, (k, 3, n)) = 12", "verified"),
    (_x5(2), "6", "eq", "Sum(k, (k, 3, n)) = 0", "verified"),        # the empty sum: 0 in every reading
    (_x5(2), "6", "eq", "Sum(k, (k, 3, n)) = 1", "refuted"),
    (_x5(2), "6", "eq", "Product(k, (k, 3, n)) = 1", "verified"),    # the empty product
    (_x5(5), "6", "eq", "Product(k, (k, 3, n)) = 1", "refuted"),
    (_x5(5), "6", "eq", r"\sum_{k=3}^{n} k = 0", "refuted"),
    (_x5(5), "6", "compute", "floor(Sum(k, (k, 3, n))) = 0", "refuted"),
    (_x5(5), "6", "compute", "floor(Sum(k, (k, 3, n))) = 12", "verified"),
    (_alone(5), "6", "eq", "Sum(k, (k, 3, n)) = 0", "refuted"),
    (_alone(5), "6", "eq", "Sum(k, (k, 3, n)) = 12", "verified"),
    (_x5(3), "6", "eq", "Sum(k, (k, 3, n)) = 3", "verified"),
    (_x5(1), "6", "eq", "x = 4", "refuted"),                          # no range in the claim
    (_ir("n**2", [K, N]), "n**2", "compute", "Sum(k, (k, 1, n)) = n**2", "refuted"),   # a random point, forward
    (_x5(1), "6", "eq", "Sum(k, (k, 1, 4)) = 11", "refuted"),         # closed
]


@pytest.mark.parametrize("ir,payload,kind,claim,status", FORWARD,
                         ids=[f"{c[1]}|{c[2]}|{c[3]}" for c in FORWARD])
def test_a_range_that_runs_forward_or_is_empty_decides_as_before(ir, payload, kind, claim, status):
    r = _run(ir, payload, kind, claim)
    st = _step(r)
    assert st["status"] == status, st
    assert (r.verdict == "INCORRECT") == (status == "refuted"), (r.verdict, st)


# ------------------------------------------------------------------ several premise points, one backwards
P25 = ["n**2 = 25"]


@pytest.mark.parametrize("ir,kind,claim,route", [
    (_ir("x + 1", [X, K, N], ["x = 5"] + P25), "eq", "Sum(k, (k, 3, n)) = 0", None),        # route 1
    (_ir("n**2", [K, N], P25), "eq", "Sum(k, (k, 3, n)) = 0", None),                         # route 1, alone
    (_ir("n**2", [K, N], P25), "eq", "floor(Sum(k, (k, 3, n))) = 0", "premise_set"),         # route 0
    (_ir("n**2", [K, N], P25), "compute", "floor(Sum(k, (k, 3, n))) = 0", None),             # each instance
    (_ir("n**2", [K, N], P25), "compute", "floor(Sum(k, (k, 3, n))) = 7", None),             # Karr's 7 at -5
], ids=["route1", "route1-alone", "route0", "instances", "instances-karr"])
def test_the_forward_point_still_refutes_a_wrong_step(ir, kind, claim, route):
    """n = ±5: at -5 the range runs backwards and is skipped; at 5 the step is wrong (Σ = 12). 69d9ec2
    refuted at -5; a skip that only withdrew it would leave the step unknown."""
    r = _run(ir, "6" if "x" in ir["task"]["params"]["expr"] else "25", kind, claim)
    st = _step(r)
    assert st["status"] == "refuted", st
    assert st["evidence"]["counterexample"]["n"] == "5", st
    if route is not None:
        assert st["evidence"].get("route") == route, st
    assert r.verdict == "INCORRECT"


@pytest.mark.parametrize("ir,kind,claim", [
    (_ir("x + 1", [X, K, N], ["x = 5"] + P25), "eq", "Sum(k, (k, 3, n)) = 12"),
    (_ir("n**2", [K, N], P25), "eq", "Sum(k, (k, 3, n)) = 12"),
    (_ir("n**2", [K, N], P25), "eq", "floor(Sum(k, (k, 3, n))) = 12"),
    (_ir("n**2", [K, N], P25), "compute", "floor(Sum(k, (k, 3, n))) = 12"),
], ids=["route1", "route1-alone", "route0", "instances"])
def test_a_step_true_at_the_forward_point_is_not_refuted_at_the_backwards_one(ir, kind, claim):
    """69d9ec2: refuted at -5 (Karr's 7), INCORRECT."""
    r = _run(ir, "6" if "x" in ir["task"]["params"]["expr"] else "25", kind, claim)
    st = _step(r)
    assert st["status"] != "refuted", st
    assert r.verdict != "INCORRECT", (r.verdict, st)


# ------------------------------------------------------------------ the helpers
def test_the_helpers_read_the_claims_own_ranges():
    from mathverify.steps.deterministic import _range_spans, _refuted_where_backwards, _runs_backwards_at
    n, k = sp.Symbol("n", integer=True), sp.Symbol("k", integer=True)
    claim = sp.Eq(sp.Sum(k, (k, 3, n)), 0)
    spans = _range_spans(claim)
    assert len(spans) == 1, spans
    assert _runs_backwards_at(spans, {n: sp.Integer(1)}) is True
    assert _runs_backwards_at(spans, {"n": sp.Integer(-4)}) is True        # matched by name
    assert _runs_backwards_at(spans, {n: sp.Integer(2)}) is False           # the empty range
    assert _runs_backwards_at(spans, {n: sp.Integer(7)}) is False
    assert _runs_backwards_at(spans, {}) is True                            # n not fixed: undecided
    assert _range_spans(sp.Eq(sp.Sum(k, (k, 3, 5)), 12)) == []              # closed: the parser's check
    assert _range_spans(sp.Eq(n + 1, 2)) == []
    # the point read back from each route's evidence
    assert _refuted_where_backwards(claim, {"counterexample": {"n": "1", "x": "5"}}) is True
    assert _refuted_where_backwards(claim, {"counterexample": {"n": "5"}}) is False
    assert _refuted_where_backwards(claim, {"pinned_by_premises": {"n": "-2"}}) is True
    assert _refuted_where_backwards(claim, {"pinned_by_premises": {"n": "5"}}) is False
    rp = {"compare": {"random_point": {"counterexample": {"point": {"n": "48"}}}}}
    assert _refuted_where_backwards(claim, rp) is False
    rp = {"compare": {"random_point": {"counterexample": {"point": {"n": "-48"}}}}}
    assert _refuted_where_backwards(claim, rp) is True
    # no point read back while the claim has such a range: not known to be a forward point
    assert _refuted_where_backwards(claim, {}) is True
    assert _refuted_where_backwards(sp.Eq(n + 1, 2), {}) is False
