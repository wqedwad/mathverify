"""A `compute` step whose symbols the premises confine to finitely many values, or only narrow (part 10,
1 Oct 2026; part 9's finding).

`check_steps` checks a `compute` step as an identity in its free symbols. When that fails, part 3 and
part 8 re-checked it at the values the premises pin its symbols to (`_pins`), but only for a premise
`s = c`. With n an integer and the givens n**2 = 4, n > 0 (n = 2), the right step `n**3 = 8` was refuted
at n = 48, and with the given x > 0 the right step `Abs(x) = x` at x = -0.00919: no instance of the
problem either time (principle 5), and the verdict was INCORRECT. Now (`steps.deterministic._on_premises`):

  * premises (givens, constraints, the domain, `eq` steps proved in the same branch) that confine the
    symbols, and every symbol a premise links them to, to finitely many exact values: the step is checked
    at each value; refuted only at one where every premise holds, verified only when it holds at all;
  * a point where a range of the problem runs backwards decides nothing (part 9, DECISIONS §80);
  * otherwise the identity's counterexample stands only when it satisfies the premises on the claim's
    symbols; when it does not, the claim is compared again on the region they leave.

The tests marked "65b699e" fail there (measured: see the commit message).
"""
from __future__ import annotations

import pytest

from mathverify.verifier import verify

N = {"name": "n", "domain": "integer"}
NP = {"name": "n", "domain": "positive_integer"}
K = {"name": "k", "domain": "integer"}
X = {"name": "x", "domain": "real"}
Y = {"name": "y", "domain": "real"}
A = {"name": "a", "domain": "real"}
S = "Sum(k, (k, 1, n))"


def _ir(expr, vars_, givens=()):
    return {"task": {"kind": "evaluate", "params": {"expr": expr}}, "vars": list(vars_), "givens": list(givens),
            "answer_shape": "scalar"}


def _run(ir, payload, steps):
    sol = {"claimed_answer": {"kind": "value", "payload": payload},
           "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                     for i, (k, c) in enumerate(steps)]}
    return verify(ir, sol)


def _last(r):
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return layer.evidence["steps"][-1]


def _c(claim):
    return [("compute", claim)]


# ---------------------------------------------------------------------------- a finite set, the step right
RIGHT = [
    (_ir("n**3", [N], ["n**2 = 4", "n > 0"]), "8", _c("n**3 = 8")),                      # the finding
    (_ir("n + 1", [N], ["n**2 = 4", "n > 0"]), "3", _c("n + 1 = 3")),
    (_ir("n*(n + 1)/2", [NP], ["n**2 = 4"]), "3", _c(f"{S} = 3")),
    (_ir("n*(n + 1)/2", [NP, K], ["n**2 = 4"]), "3", _c(f"{S} = 3")),
    (_ir("n*(n + 1)/2", [NP], ["n**2 = 9"]), "6", _c(f"{S} = 6")),                        # part 8's control
    (_ir("n*(n + 1)/2", [N], ["n**2 = 9", "n > 0"]), "6", _c(f"{S} = 6")),
    (_ir("factorial(n)", [N], ["n**2 = 9", "n > 0"]), "6", _c("Product(k, (k, 1, n)) = 6")),
    (_ir("n**4", [N], ["n**2 = 4"]), "16", _c("n**4 = 16")),                               # true at -2 and 2
    (_ir("x**2 - 5*x + 7", [X], ["x**2 - 5*x + 6 = 0"]), "1", _c("x**2 - 5*x + 7 = 1")),   # {2, 3}
    (_ir("x*(5 - x)", [X], ["x**2 - 5*x + 6 = 0"]), "6", _c("x*(5 - x) = 6")),
    (_ir("x**4", [X], ["x**2 = 2", "x > 0"]), "4", _c("x**4 = 4")),                        # sqrt(2)
    (_ir("n**3", [N], ["n**2 = 4", "0 < n < 5"]), "8", _c("n**3 = 8")),                    # a chain
    (_ir("floor(n/6)", [N], ["1 <= n", "n <= 5"]), "0", _c("floor(n/6) = 0")),             # five values
    # two symbols: each its own, linked by a premise, and through a verified eq step
    (_ir("x + y", [X, Y], ["x**2 = 4", "y**2 = 9", "x > 0", "y > 0"]), "5", _c("x + y = 5")),
    (_ir("x**2 + y**2", [X, Y], ["x**2 = 4", "y**2 = 9"]), "13", _c("x**2 + y**2 = 13")),
    (_ir("x*y", [X, Y], ["x**2 = 4", "y = x + 1", "x > 0"]), "6", _c("x*y = 6")),
    (_ir("y**2", [X, Y], ["x**2 = 4", "y = x + 1", "x > 0"]), "9", _c("y**2 = 9")),
    (_ir("x*y", [X, Y], ["x + y = 5", "x - y = 1"]), "6", [("eq", "x = 3"), ("compute", "x*y = 6")]),
    # no symbol confined alone: the polynomial system determines both
    (_ir("x*y", [X, Y], ["x + y = 5", "x - y = 1"]), "6", _c("x*y = 6")),
    (_ir("x*y", [X, Y], ["x**2 + y**2 = 25", "y = x + 1"]), "12", _c("x*y = 12")),        # (3, 4), (-4, -3)
]


@pytest.mark.parametrize("ir,payload,steps", RIGHT)
def test_a_right_step_on_a_finite_premise_set_is_verified(ir, payload, steps):
    """65b699e: refuted at a point no premise allows, INCORRECT."""
    r = _run(ir, payload, steps)
    last = _last(r)
    assert last["status"] == "verified" and r.verdict == "CORRECT", (r.verdict, last.get("evidence"))
    assert last["evidence"]["instances_by_premises"]["certain"]


# ---------------------------------------------------------------------------- a finite set, the step wrong
WRONG = [
    (_ir("n**3", [N], ["n**2 = 4", "n > 0"]), "8", _c("n**3 = 9"), {"n": "2"}),
    (_ir("n**4", [N], ["n**2 = 4"]), "16", _c("n**3 = 8"), {"n": "-2"}),                   # false at -2 only
    (_ir("n*(n + 1)/2", [NP], ["n**2 = 4"]), "3", _c(f"{S} = 4"), {"n": "2"}),
    (_ir("factorial(n)", [N], ["n**2 = 9", "n > 0"]), "6", _c("Product(k, (k, 1, n)) = 7"), {"n": "3"}),
    (_ir("x**2 - 5*x + 7", [X], ["x**2 - 5*x + 6 = 0"]), "1", _c("x**2 = 4"), {"x": "3"}),
    (_ir("floor(n/6)", [N], ["1 <= n", "n <= 5"]), "0", _c("floor(n/5) = 0"), {"n": "5"}),
    (_ir("x + y", [X, Y], ["x**2 = 4", "y**2 = 9", "x > 0", "y > 0"]), "5", _c("x + y = 6"), {"x": "2", "y": "3"}),
    (_ir("x**2 + y**2", [X, Y], ["x**2 = 4", "y**2 = 9"]), "13", _c("x + y = 5"), {"x": "-2", "y": "-3"}),
    (_ir("x*y", [X, Y], ["x**2 = 4", "y = x + 1"]), "6", _c("y**2 = 9"), {"y": "-1"}),
    (_ir("x*y", [X, Y], ["x + y = 5", "x - y = 1"]), "6", [("eq", "x = 3"), ("compute", "x*y = 7")],
     {"x": "3", "y": "2"}),
    (_ir("x*y", [X, Y], ["x + y = 5", "x - y = 1"]), "6", _c("x*y = 7"), {"x": "3", "y": "2"}),
    (_ir("x*y", [X, Y], ["x**2 + y**2 = 25", "y = x + 1"]), "12", _c("x + y = 7"), {"x": "-4", "y": "-3"}),
]


@pytest.mark.parametrize("ir,payload,steps,point", WRONG)
def test_a_wrong_step_on_a_finite_premise_set_is_refuted_at_an_instance(ir, payload, steps, point):
    """65b699e refuted these too, but at a point no premise allows (no `counterexample` among the instances)."""
    r = _run(ir, payload, steps)
    last = _last(r)
    assert r.verdict == "INCORRECT" and last["status"] == "refuted"
    assert last["evidence"]["counterexample"] == point
    assert point in last["evidence"]["instances_by_premises"]["certain"]


# ---------------------------------------------------------------------------- a reversed range (part 9)
@pytest.mark.parametrize("claim,status,point", [
    (f"{S} = 3", "unknown", None),             # right at 2; n = -2 runs the problem's range backwards
    ("n**3 = 8", "unknown", None),             # wrong only at the reversed n = -2: not refuted there
    ("n**4 = 16", "verified", None),           # right at both: n = -2 changes nothing
    ("n**2 = 4", "verified", None),
    (f"{S} = 1", "refuted", {"n": "2"}),       # Karr's value at -2, wrong at 2
    ("n**3 = -8", "refuted", {"n": "2"}),
])
def test_a_point_where_the_problems_range_runs_backwards_decides_nothing(claim, status, point):
    r = _run(_ir(S, [N, K], ["n**2 = 4"]), "3", _c(claim))
    last = _last(r)
    assert last["status"] == status, (last["status"], last.get("evidence"))
    inst = last["evidence"]["instances_by_premises"]
    assert inst == {"certain": [{"n": "2"}], "undecided": [{"n": "-2"}]}
    if point is not None:
        assert last["evidence"]["counterexample"] == point and r.verdict == "INCORRECT"
    else:
        assert r.verdict == "UNKNOWN"


def test_a_step_whose_own_range_runs_backwards_at_an_instance_is_not_decided():
    """The problem has no range; the step's Sum runs backwards at n = -2, which the parser does not read."""
    r = _run(_ir("n*(n + 1)/2", [N], ["n**2 = 4"]), "3", _c(f"{S} = 3"))
    assert _last(r)["status"] == "unknown" and r.verdict != "INCORRECT"
    r = _run(_ir("n*(n + 1)/2", [N], ["n**2 = 4"]), "3", _c(f"{S} = 1"))
    assert _last(r)["status"] == "refuted" and _last(r)["evidence"]["counterexample"] == {"n": "2"}


# ---------------------------------------------------------------------------- premises that only narrow
@pytest.mark.parametrize("ir,payload,claim", [
    (_ir("Abs(x) + 1", [X], ["x > 0"]), "x + 1", "Abs(x) = x"),
    (_ir("sqrt(x**2)", [X], ["x > 3"]), "x", "sqrt(x**2) = x"),
    (_ir("Max(n, 5)", [N], ["n > 5"]), "n", "Max(n, 5) = n"),
    (_ir("Abs(x) + 1", [X], ["x**2 > 4", "x > 0"]), "x + 1", "Abs(x) = x"),
    (_ir("Abs(n)", [N], ["0 <= n", "n <= 30"]), "n", "Abs(n) = n"),                       # 31 values
    (_ir("Abs(x - y)", [X, Y], ["x > y"]), "x - y", "Abs(x - y) = x - y"),
])
def test_a_counterexample_the_premises_exclude_refutes_nothing(ir, payload, claim):
    """65b699e: refuted at a point outside the premises (x = -919/100000 under x > 0), INCORRECT."""
    r = _run(ir, payload, _c(claim))
    assert _last(r)["status"] in ("verified", "unknown") and r.verdict != "INCORRECT"


def test_a_counterexample_the_premises_exclude_is_replaced_by_one_they_allow():
    """65b699e: refuted at x = -919/100000; now re-compared on (0, oo) and verified."""
    last = _last(_run(_ir("Abs(x) + 1", [X], ["x > 0"]), "x + 1", _c("Abs(x) = x")))
    assert last["status"] == "verified" and last["evidence"]["premise_region"] == {"x": "Interval.open(0, oo)"}


@pytest.mark.parametrize("ir,payload,claim", [
    (_ir("Abs(x) + 1", [X], ["x > 0"]), "x + 1", "Abs(x) = -x"),
    (_ir("Abs(x) + 1", [X], ["x > 0"]), "x + 1", "Abs(x) = x + 1"),
    (_ir("x**2", [X], ["x > 0"]), "x**2", "x**2 = x"),
    (_ir("Abs(x)", [X], ["x < 0"]), "-x", "Abs(x) = x"),
    (_ir("Max(n, 5)", [N], ["n > 5"]), "n", "Max(n, 5) = 5"),
    (_ir("Abs(n - 1)", [N], ["0 <= n", "n <= 30"]), "n - 1", "Abs(n - 1) = n - 1"),
])
def test_a_wrong_step_under_narrowing_premises_stays_refuted_at_a_point_they_allow(ir, payload, claim):
    r = _run(ir, payload, _c(claim))
    last = _last(r)
    assert r.verdict == "INCORRECT" and last["status"] == "refuted"
    ev = last["evidence"]
    assert ev.get("counterexample_satisfies_premises") is True or "counterexample" in ev, ev


@pytest.mark.parametrize("ir,payload,claim,refuted", [
    (_ir("y - 2*x", [X, Y], ["y = 2*x + 1"]), "1", "y - 2*x = 2", True),
    (_ir("x*y", [X, Y], ["x + y = 10"]), "x*(10 - x)", "x*y = 21", True),
    (_ir("y - 2*x", [X, Y], ["y = 2*x + 1"]), "1", "y - 2*x = 1", False),
    (_ir("x*y", [X, Y], ["x + y = 10"]), "x*(10 - x)", "x*y = x*(10 - x)", False),
])
def test_a_counterexample_is_searched_where_the_premises_hold(ir, payload, claim, refuted):
    """An equation in two symbols that determines neither (the line y = 2x + 1): the identity's counterexample
    is off the line, and one on it is searched. 65b699e refuted all four at a point off the line."""
    r = _run(ir, payload, _c(claim))
    last = _last(r)
    if refuted:
        assert r.verdict == "INCORRECT" and last["status"] == "refuted"
        ev = last["evidence"]
        assert ev["premise_region"] == {} and "counterexample" in ev, ev
    else:
        assert last["status"] == "unknown" and r.verdict != "INCORRECT"


@pytest.mark.parametrize("givens,status", [(["n**2 = 9"], "unknown"), (["n**2 = 9", "n > 0"], "verified")])
def test_a_region_with_reversed_range_points_verifies_nothing(givens, status):
    """A Limit keeps the claim out of the finite route (no substitution), so the region route compares it:
    n**2 = 9 leaves n = 3 forward and n = -3 reversed for the problem's Σ_{k=1}^{n} k. The claim holds at 3
    and fails at -3, which may be an instance (DECISIONS §80): not verified. With n > 0 nothing is reversed."""
    last = _last(_run(_ir(S, [N, K, X], givens), "6", _c("n*Limit(x, x, 1) = 3")))
    assert last["status"] == status, last.get("evidence")
    if status == "unknown":
        assert last["evidence"]["reason"] == "reversed_range_points_undecided"


@pytest.mark.parametrize("givens,claim,status", [
    (["a**2 = 4", "a > 0"], "a*Limit(x**2, x, 1) = 2", "verified"),
    (["a**2 = 4", "a > 0"], "Derivative(a*x**2, x) = 4*x", "verified"),
    (["a**2 = 4"], "a*Limit(x**2, x, 1) = 2", "refuted"),                  # false at a = -2
    (["a**2 = 4"], "a**2*Limit(x**2, x, 1) = 4", "verified"),             # true at a = -2 and a = 2
])
def test_a_limit_or_a_derivative_is_compared_at_each_value_without_substitution(givens, claim, status):
    """A Limit or a Derivative is never substituted into (`_binders_keep_clear_of`); the region route
    compares the claim with a confined to each of its values alone (`_region_cells`). 65b699e: all
    refuted at an a the premises exclude."""
    last = _last(_run(_ir("a", [A, X], givens), "2", _c(claim)))
    assert last["status"] == status, last.get("evidence")
    if status == "refuted":
        assert last["evidence"]["counterexample"] == {"a": "-2"} or \
            last["evidence"].get("counterexample_satisfies_premises") is True


# ---------------------------------------------------------------------------- what does not change
@pytest.mark.parametrize("ir,payload,steps,verdict,status", [
    (_ir("Abs(x)", [X]), "Abs(x)", _c("Abs(x) = x"), "INCORRECT", "refuted"),              # no premise
    (_ir("n*(n + 1)/2", [NP], ["n = 3"]), "6", _c(f"{S} = 6"), "CORRECT", "verified"),      # part 8
    (_ir("n*(n + 1)/2", [NP], ["n = 3"]), "6", _c(f"{S} = 7"), "INCORRECT", "refuted"),
    (_ir("n*(n + 1)/2", [NP], ["n > 2"]), "6", _c(f"{S} = 6"), "INCORRECT", "refuted"),
    (_ir("a", [A], ["a = 3", "a = 2"]), "6", _c("Sum(a*k, (k, 1, 2)) = 9"), None, "refuted"),  # no instance
    (_ir("n**3", [N], ["n**2 = 4", "n > 0"]), "9", _c("n**3 = 8"), "INCORRECT", "verified"),  # wrong answer
    # an eq step that is not proved does not confine n: n = -2 is still an instance
    (_ir("n**3", [N], ["n**2 = 4"]), "8", [("eq", "n > 0"), ("compute", "n**3 = 8")], "INCORRECT", "refuted"),
    # known limit: x > 0 follows from x > y > 0, which no premise on x alone says
    (_ir("Abs(x) + y", [X, Y], ["x > y", "y > 0"]), "x + y", _c("Abs(x) = x"), "INCORRECT", "refuted"),
])
def test_controls(ir, payload, steps, verdict, status):
    r = _run(ir, payload, steps)
    assert _last(r)["status"] == status and (verdict is None or r.verdict == verdict), \
        (r.verdict, _last(r)["status"], _last(r).get("evidence"))


def test_region_cells():
    import sympy as sp
    from mathverify.steps.deterministic import _region_cells
    a, b = sp.symbols("a b", real=True)
    assert _region_cells({a: sp.FiniteSet(-2, 2)}) == [{a: sp.FiniteSet(-2)}, {a: sp.FiniteSet(2)}]
    assert _region_cells({a: sp.Range(1, 4)}) == [{a: sp.FiniteSet(k)} for k in (1, 2, 3)]
    iv = sp.Interval.open(0, sp.oo)
    assert _region_cells({a: sp.FiniteSet(1, 2), b: iv}) == [{a: sp.FiniteSet(1), b: iv}, {a: sp.FiniteSet(2), b: iv}]
    assert _region_cells({a: sp.Range(0, 31)}) == [{a: sp.Range(0, 31)}]             # too many: one cell
