"""V15 L1 (DECISIONS §72): a problem function whose body takes `Mod` of its formal argument.

The formal argument is a real symbol (`parse._make_function`), so `Mod(n, 3)` in the body is no
`_safe_mod`, and `_functions_faithful` refused every such function: no Lean statement for
"a_n = n mod 3, Σ_{k=1}^{10} a_k = 10". Its question is only whether the parse changed the body's
domain, and a Mod by a positive integer literal is total. Whether the Mod is stated faithfully is
decided at each call, with the argument in place, by the template's own `_definedness`: an integer
argument prints in ℤ, a real or rational one is refused as before (C4, audit of 25 Sep 2026)."""
from __future__ import annotations

import pytest

from mathverify.formal import prove as P
from mathverify.formal.statement import build_statement

PI = [{"name": "n", "domain": "positive_integer"}, {"name": "k", "domain": "positive_integer"}]
X = [{"name": "x"}]


def _ir(kind, params, vars_, body, args=("n",), shape="scalar", givens=()):
    return {"task": {"kind": kind, "params": params}, "vars": vars_, "givens": list(givens),
            "functions": [{"name": "f", "expr": body, "args": list(args)}], "answer_shape": shape}


def _series(body, hi, vars_=PI, lo="1"):
    return _ir("series_sum", {"term": "f(k)", "var": "k", "lo": lo, "hi": hi}, vars_, body)


REC = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1) + f(n)", "initial": {"1": "1"},
                                                      "index": 5, "var": "n"}},
       "vars": [{"name": "n", "domain": "positive_integer"}],
       "functions": [{"name": "f", "expr": "Mod(n, 2)", "args": ["n"]}], "answer_shape": "scalar"}
EV = _ir("evaluate", {"expr": "f(-7)"}, X, "Mod(x, 3)", ("x",))

# (label, ir, claim, right?): 1+2+0+1+2+0+1+2+0+1 = 10; a_5 = 1 + 0 + 1 + 0 + 1 = 3; -7 mod 3 = 2
# (floored, as Lean's Int.emod for a positive divisor); (1 + k mod 3) mod 2 over k = 1..3 is 0 + 1 + 1
STATED = [
    ("sum of n mod 3 = 10", _series("Mod(n, 3)", "10"), "10", True),
    ("sum of n mod 3 = 9", _series("Mod(n, 3)", "10"), "9", False),
    ("recurrence with n mod 2 = 3", REC, "3", True),
    ("recurrence with n mod 2 = 4", REC, "4", False),
    ("f(-7) = 2 for f(x) = x mod 3", EV, "2", True),
    ("f(-7) = -1 (truncated division)", EV, "-1", False),
    ("nested mod = 2", _series("Mod(Mod(n, 3) + 1, 2)", "3"), "2", True),
    ("nested mod = 3", _series("Mod(Mod(n, 3) + 1, 2)", "3"), "3", False),
]

REFUSED = [
    # a real argument at the call: ℝ `%` is identically 0 in Mathlib (C4)
    ("simplify f(x) to 0, f(x) = x mod 2", _ir("simplify_expression", {"expr": "f(x)"}, X, "Mod(x, 2)", ("x",),
                                                 shape="expression"), "expression", "0"),
    ("f(7/2), f(x) = x mod 3", _ir("evaluate", {"expr": "f(7/2)"}, X, "Mod(x, 3)", ("x",)), "value", "1/2"),
    # no positive literal divisor
    ("body n mod -3", _series("Mod(n, -3)", "3"), "value", "-3"),
    ("body n mod m, m = 2", _ir("series_sum", {"term": "f(k)", "var": "k", "lo": "1", "hi": "3"},
                                PI + [{"name": "m", "domain": "positive_integer"}], "Mod(n, m)", givens=["m = 2"]),
     "value", "2"),
    # a summand undefined at k = 2; a body whose parse changed its domain (n**2/n at n = 0)
    ("body (n mod 3)/(n - 2)", _series("Mod(n, 3)/(n - 2)", "4"), "value", "0"),
    ("body (n**2/n) mod 3 from 0", _series("Mod(n**2/n, 3)", "3", [{"name": "n", "domain": "integer"},
                                                                   {"name": "k", "domain": "integer"}], lo="0"),
     "value", "3"),
]


def _build(ir, claim, kind="value"):
    return build_statement(ir, {"kind": kind, "payload": claim})


def test_a_function_mod_by_a_positive_literal_is_stated_in_the_integers():
    st = _build(*STATED[0][1:3])
    assert st is not None and st.goal == "(∑ k ∈ Finset.Icc (1 : ℤ) 10, ((k % 3 : ℤ) : ℤ)) = 10", st and st.goal
    st = _build(*STATED[2][1:3])
    assert st is not None and "(n % 2 : ℤ)" in " ".join(st.hypotheses), st and st.hypotheses
    for label, ir, claim, _right in STATED:
        assert _build(ir, claim) is not None, label


@pytest.mark.parametrize("label,ir,kind,claim", REFUSED, ids=[r[0] for r in REFUSED])
def test_a_function_mod_outside_the_safe_subset_is_still_refused(label, ir, kind, claim):
    assert _build(ir, claim, kind) is None, label


def test_a_body_whose_parse_changes_its_domain_is_still_refused():
    ir = _ir("evaluate", {"expr": "f(3)"}, [{"name": "x", "domain": "positive_real"}], "x**2/x + 1", ("x",))
    assert _build(ir, "4") is None


@pytest.fixture(scope="module")
def lean():
    from mathverify.formal import get_lean, lean_available
    if not lean_available(timeout=300):
        pytest.skip("Lean/Mathlib toolchain not available")
    return get_lean()


@pytest.mark.parametrize("label,ir,claim,right", STATED, ids=[s[0] for s in STATED])
def test_live_function_mod_certifies_exactly_the_right_answers(lean, label, ir, claim, right):
    st = _build(ir, claim)
    assert st is not None, label
    r = P.prove_statement(st, use_model=False, lean=lean, tactic_timeout=45)
    certified = bool(r["proved"] and r["audit"]["clean"])
    if right:
        assert certified, (label, [a.get("errors") for a in r["attempts"]][:3], r.get("audit"))
    else:
        assert not certified, (label, r.get("proof"), r.get("audit"))
