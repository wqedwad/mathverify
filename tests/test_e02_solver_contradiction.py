"""E2 — `solve` and `solveset` contradict each other; every candidate root must be
checked against the ORIGINAL expression and the definedness conditions.

Measured (SymPy 1.14.0): log(x-1)+log(x-3)=log 3 -> solve [4], solveset {0, 4}.
sqrt(x+4)=x-2 -> naive squaring gives [0, 5]; 0 is extraneous.
"""
import sympy as sp
from sympy import S, log, sqrt, Eq, FiniteSet

from mathverify.certify.domain import definedness_conditions, guard_roots
from mathverify.certify.algebra import solve_guarded

x = sp.Symbol("x", real=True)


def test_raw_solve_vs_solveset_disagree_on_log_equation():
    eq = log(x - 1) + log(x - 3) - log(3)
    assert sp.solve(eq, x) == [4]
    assert sp.solveset(eq, x, S.Reals) == FiniteSet(0, 4)    # extraneous 0


def test_raw_naive_squaring_gives_extraneous_root():
    assert sorted(sp.solve((x + 4) - (x - 2) ** 2, x)) == [0, 5]


def test_definedness_conditions_are_collected():
    conds = definedness_conditions(log(x - 1) + log(x - 3), x)
    assert any(c == (x - 1 > 0) for c in conds)
    assert any(c == (x - 3 > 0) for c in conds)
    conds = definedness_conditions(sqrt(x + 4) / (x - 2), x)
    assert any(c == (x + 4 >= 0) for c in conds)
    assert any(c == sp.Ne(x - 2, 0) for c in conds)


def test_guard_removes_extraneous_log_root():
    rel = Eq(log(x - 1) + log(x - 3), log(3))
    kept, rejected = guard_roots(rel, x, [0, 4])
    assert kept == [4]
    assert [r for r, _ in rejected] == [0]


def test_guard_removes_extraneous_sqrt_root():
    rel = Eq(sqrt(x + 4), x - 2)
    kept, rejected = guard_roots(rel, x, [0, 5])
    assert kept == [5]


def test_solve_guarded_returns_only_true_roots():
    roots, ev = solve_guarded(Eq(log(x - 1) + log(x - 3), log(3)), x)
    assert roots == [4]
    # SymPy's own solveset gave {0, 4} (the trap); since round 5 of part d4b (2 Oct 2026) the guarded
    # solveset is the class set of a sum of logs, {4}, and SymPy's set is no longer read
    assert set(ev["solveset"]) == {"4"}
    roots, ev = solve_guarded(Eq(sqrt(x + 4), x - 2), x)
    assert roots == [5]


def test_guard_respects_domain_of_discourse():
    # x^2 = 4 over the problem domain x > 0 keeps only 2
    kept, rejected = guard_roots(Eq(x ** 2, 4), x, [-2, 2], domain=sp.Interval.open(0, sp.oo))
    assert kept == [2]
