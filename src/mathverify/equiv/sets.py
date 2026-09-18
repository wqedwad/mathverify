"""Set / interval equivalence for solution sets and domains.

Handles FiniteSet, Interval, Union of intervals and points, EmptySet, Reals, and
Complements that SymPy already evaluates to unions. ImageSet/ConditionSet are NOT
handled here (E1: periodic sets go through certify.trig)."""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Interval, FiniteSet, Union, ImageSet, ConditionSet, oo

from .numeric import num_equal
from .symbolic import sym_equal

__all__ = ["set_equal", "normalize_set", "scalar_equal"]


def scalar_equal(a, b) -> bool | None:
    ok, _ = sym_equal(a, b)
    if ok:
        return True
    okn, _ = num_equal(a, b)
    return okn


def normalize_set(s: sp.Set) -> tuple[list[Interval], list[Any]] | None:
    """Split a set into (sorted disjoint intervals, isolated points). None if unsupported."""
    if s is S.EmptySet:
        return [], []
    if s == S.Reals:
        return [Interval(-oo, oo)], []
    if isinstance(s, FiniteSet):
        return [], list(s.args)
    if isinstance(s, Interval):
        if s.measure == 0 and s.left == s.right:
            return [], [s.left]
        return [s], []
    if isinstance(s, Union):
        ivs, pts = [], []
        for a in s.args:
            r = normalize_set(a)
            if r is None:
                return None
            ivs += r[0]
            pts += r[1]
        # points inside intervals are redundant; intervals sorted by inf
        ivs = sorted(ivs, key=lambda i: (float(i.inf) if i.inf.is_number and i.inf != -oo else -1e300))
        pts2 = []
        for p in pts:
            if not any(iv.contains(p) == True for iv in ivs):  # noqa: E712
                pts2.append(p)
        # merge intervals that touch/overlap (Union already does this, but be safe)
        merged: list[Interval] = []
        for iv in ivs:
            if merged and (merged[-1].sup >= iv.inf) and not (merged[-1].right_open and iv.left_open and merged[-1].sup == iv.inf):
                m = merged.pop()
                merged.append(Interval(m.inf, max(m.sup, iv.sup),
                                       left_open=m.left_open,
                                       right_open=(iv.right_open if iv.sup >= m.sup else m.right_open)))
            else:
                merged.append(iv)
        return merged, pts2
    if isinstance(s, (ImageSet, ConditionSet)):
        return None
    if s in (S.Integers, S.Naturals, S.Naturals0, S.Complexes):
        return None
    return None


def _interval_equal(a: Interval, b: Interval) -> bool | None:
    if a.left_open != b.left_open or a.right_open != b.right_open:
        return False
    r1 = scalar_equal(a.inf, b.inf)
    r2 = scalar_equal(a.sup, b.sup)
    if r1 is False or r2 is False:
        return False
    if r1 is None or r2 is None:
        return None
    return True


def _finite_equal(pa: list, pb: list) -> bool | None:
    if len(pa) != len(pb):
        return False
    remaining = list(pb)
    undecided = False
    for a in pa:
        hit = None
        for j, b in enumerate(remaining):
            r = scalar_equal(a, b)
            if r is True:
                hit = j
                break
            if r is None:
                undecided = True
        if hit is None:
            return None if undecided else False
        remaining.pop(hit)
    return True


def set_equal(A: sp.Set, B: sp.Set) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"A": str(A), "B": str(B)}
    A, B = sp.sympify(A), sp.sympify(B)
    if A == B:
        ev["method"] = "structural"
        return True, ev
    na, nb = normalize_set(A), normalize_set(B)
    if na is None or nb is None:
        # last resort: sympy's own decision (tri-state)
        try:
            r = A.is_subset(B)
            r2 = B.is_subset(A)
            if r is True and r2 is True:
                ev["method"] = "is_subset_both"
                return True, ev
            if r is False or r2 is False:
                ev["method"] = "is_subset_refuted"
                return False, ev
        except Exception:
            pass
        ev["method"] = "unsupported_set_type"
        return None, ev
    ia, pa = na
    ib, pb = nb
    if len(ia) != len(ib):
        ev["method"] = "interval_count_differs"
        return False, ev
    undecided = False
    for x_, y_ in zip(ia, ib):
        r = _interval_equal(x_, y_)
        if r is False:
            ev["method"] = "interval_differs"
            ev["pair"] = (str(x_), str(y_))
            return False, ev
        if r is None:
            undecided = True
    r = _finite_equal(pa, pb)
    if r is False:
        ev["method"] = "points_differ"
        return False, ev
    if r is None or undecided:
        ev["method"] = "undecided_endpoints"
        return None, ev
    ev["method"] = "normalized_compare"
    return True, ev
