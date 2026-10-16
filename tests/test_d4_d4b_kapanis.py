"""The close of round 10 of part d4b (16 Oct 2026): the eight mutations that survived d4b's full mutation list at
9d60d17 (D08, N08 to N12, N40, N41). Round 10 made SymPy's own numeric decisions strict in the whole process
(mathverify._sympy_guards: relations of numbers, the assumption system's numeric fallback, floor and ceiling at
construction), and the tests the mutations named passed without the round-9 guards they remove. Each guard is
pinned here by an input it still decides or, where a process-wide guard now shadows it, by its mechanism.

* N40, N41, N09 (inputs): a CLOSED step is decided by `steps.deterministic._decide`, whose numeric sign is
  SymPy's NON-strict value (`to_mp`): with Z = gd(1) - gd(1) exactly 0, ceiling(Z**2) and sign(|Z|) come out 1.0
  at every precision. The true steps "ceiling(Z**2) = 0", "ceiling(Z**2) <= 0", "sign(|Z|) = 0" were refuted and
  the right answer INCORRECT without the jump guard of the compute step (N40), of the eq step (N41), or of
  `_jumps_resolved` above an Abs no certified sign settles (N09, which made sign(|Z|) no jump at all).
* N08 (input): the jump of a number not certainly real has no value (a convention: SymPy's sign(z) = z/|z|,
  `jump_value`); simplify reads SymPy's, and sym_equal certified sign(1 + I) = (1 + I)/sqrt(2) without the guard.
* N10 (input): a Piecewise of constant conditions is resolved from certified signs; without it certified_sign of
  Piecewise((2, L > 3), (5, L <= 3)) - 1, L = log(8)/log(2) exactly 3, was undecided. Its guard role is shadowed:
  evalf has no numeric value for a Piecewise, and a strict evaluation that has none raises (round 10).
* N11, N12, D08 (mechanism): shadowed by round 10's guards and kept as a second line; each is tested with the
  process-wide guard taken away. `_replaced` and the LaTeX reader keep a jump of an unproved zero held with
  SymPy's non-strict get_integer_part restored (ceiling(Z**2) is 1 there); `in_domain` decides membership in a
  ConditionSet by certified comparisons at the point, never by SymPy's `contains` (which reads the condition by
  substitution, without the definedness at the point).

The tests marked "kapanış" fail with the mutation of the guard they name (measured: see the commit message).
"""
from __future__ import annotations

import pytest
import sympy as sp
from sympy.core.cache import clear_cache

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
x = sp.Symbol("x", real=True)
S = sp.S

Z = "(2*atan(tanh(1/2)) - atan(sinh(1)))"          # exactly 0 (gd(1) twice)


def _ir(kind, params, vars_=(X,), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens), "answer_shape": shape}


def _step(kind, claim):
    r = verify(_ir("evaluate", {"expr": "x + 1"}, (X,), ["x = 2"]),
               {"claimed_answer": {"kind": "value", "payload": "3"},
                "steps": [{"id": "s1", "kind": kind, "claim": claim, "from": [], "text": ""}]})
    layer = next(la for la in r.layers if la.layer == "steps.refute")
    return r.verdict, layer.evidence["steps"][-1]["status"]


@pytest.fixture
def sympy_integer_part_unguarded(monkeypatch):
    """SymPy's own floor/ceiling at construction (a non-strict evaluation: ceiling(Z**2) is 1 off the noise), as
    before round 10's guard; SymPy's cache is cleared before and after, so no node formed here outlives the test."""
    import sympy.functions.elementary.integers as integers
    from mathverify import _sympy_guards
    monkeypatch.setattr(integers, "get_integer_part", _sympy_guards._INTEGER_PART)
    clear_cache()
    yield
    monkeypatch.undo()
    clear_cache()


# --- N40, N41: a closed step with a jump of an unproved zero ---------------------------------------------------------

@pytest.mark.parametrize("kind,claim", [
    ("eq", f"ceiling({Z}**2) = 0"), ("eq", f"sign({Z}**2) = 0"), ("eq", f"floor(-{Z}**2) = 0"),
    ("eq", f"ceiling({Z}**2) <= 0"),
    ("compute", f"ceiling({Z}**2) <= 0"), ("compute", f"sign({Z}**2) <= 0"), ("compute", f"floor(-{Z}**2) >= 0"),
])
def test_a_true_closed_step_with_a_jump_of_an_unproved_zero_is_not_refuted(kind, claim):    # kapanış: N40 N41
    verdict, status = _step(kind, claim)
    assert status != "refuted" and verdict != "INCORRECT"


# --- N09: a jump above an Abs no certified sign settles --------------------------------------------------------------

@pytest.mark.parametrize("kind,claim", [
    ("eq", f"sign(Abs({Z})) = 0"), ("compute", f"sign(Abs({Z})) <= 0"), ("eq", f"ceiling(sqrt(Abs({Z}))) = 0"),
])
def test_a_jump_above_an_undecided_abs_stays_a_jump(kind, claim):                           # kapanış: N09
    from mathverify.equiv.numeric import undecided_jumps
    from mathverify.normalize.parse import parse_expr_str
    assert undecided_jumps(parse_expr_str(f"sign(Abs({Z}))"))
    verdict, status = _step(kind, claim)
    assert status != "refuted" and verdict != "INCORRECT"


# --- N08: the jump of a number not certainly real --------------------------------------------------------------------

@pytest.mark.parametrize("e,claim", [("sign(1 + I)", "(1 + I)/sqrt(2)"), ("sign(sqrt(2)*I)", "I")])
def test_sym_equal_does_not_take_sympys_jump_of_a_nonreal_number(e, claim):                 # kapanış: N08
    from mathverify.equiv.symbolic import sym_equal
    from mathverify.normalize.parse import parse_expr_str
    assert sym_equal(parse_expr_str(e), parse_expr_str(claim))[0] is None
    r = verify(_ir("evaluate", {"expr": e}, ()), {"claimed_answer": {"kind": "value", "payload": claim}, "steps": []})
    assert r.verdict != "CORRECT"


# --- N10: a Piecewise of constant conditions -------------------------------------------------------------------------

def test_a_piecewise_of_numbers_takes_the_branch_certified_signs_choose():                  # kapanış: N10
    from mathverify.equiv.numeric import certified_sign
    from mathverify.normalize.parse import parse_expr_str
    pw = parse_expr_str("Piecewise((2, log(8)/log(2) > 3), (5, log(8)/log(2) <= 3))")      # 5: log(8)/log(2) = 3
    assert isinstance(pw, sp.Piecewise)              # SymPy does not decide log(8)/log(2) > 3 (no certified sign)
    assert certified_sign(pw - 1) == 1 and certified_sign(pw - 6) == -1


# --- N11, N12: a jump rebuilt by SymPy, without SymPy's strict integer part ------------------------------------------

def test_a_rebuilt_jump_is_held_without_sympys_strict_integer_part(sympy_integer_part_unguarded):   # kapanış: N11
    from mathverify.equiv.numeric import certified_sign
    z2 = sp.sympify(Z) ** 2
    assert sp.ceiling(z2) == 1                       # the noise: what the unevaluated rebuild keeps out
    clear_cache()
    assert certified_sign(sp.ceiling(z2 + sp.floor(sp.pi, evaluate=False) - 3, evaluate=False) - 1) is None


def test_a_latex_jump_is_the_namespaces_without_sympys_strict_integer_part(sympy_integer_part_unguarded):  # N12
    from mathverify.normalize.parse import _SAFE_NAMES, parse_expr_str
    xs = sp.Symbol("x", real=True)
    e = parse_expr_str(r"\lceil (2\arctan(\tanh(1/3)) - \arctan(\sinh(2/3)))^2 \cdot x \rceil", dict(_SAFE_NAMES, x=xs))
    assert e.subs(xs, 1) != 1                        # gd(2/3) twice: exactly 0, ceiling 0 (kapanış: N12)


# --- D08: membership in a ConditionSet -------------------------------------------------------------------------------

def test_membership_in_a_condition_set_is_not_sympys(monkeypatch):                           # kapanış: D08
    from mathverify.certify.domain import in_domain
    cs = sp.ConditionSet(x, sp.sin(x) > 0, S.Reals)
    monkeypatch.setattr(sp.ConditionSet, "_contains", lambda self, other: sp.true)   # a reading SymPy could get wrong
    assert in_domain(cs, sp.Integer(-7)) is False and in_domain(cs, sp.Integer(7)) is True
    assert in_domain(sp.Intersection(sp.Interval(-10, 10), cs, evaluate=False), sp.Integer(-7)) is False
