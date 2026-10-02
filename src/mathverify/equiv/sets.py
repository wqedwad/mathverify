"""Set / interval equivalence for solution sets and domains.

Handles FiniteSet, Interval, Union of intervals and points, EmptySet, Reals, and
Complements that SymPy already evaluates to unions. ImageSet/ConditionSet are NOT
handled here (E1: periodic sets go through certify.trig)."""
from __future__ import annotations

from functools import cmp_to_key
from typing import Any

import sympy as sp
from sympy import S, Interval, FiniteSet, Union, ImageSet, ConditionSet, oo

from .numeric import num_equal
from .symbolic import sym_equal

__all__ = ["set_equal", "normalize_set", "scalar_equal", "unify_endpoints", "EndpointsIncomparable"]


def scalar_equal(a, b) -> bool | None:
    """Equality of two scalars. Two exact constants are decided exactly first (a certified
    evaluation separates different values at once, a proof of zero confirms equal ones) — the
    symbolic battery, tried first before, spent up to its full timeout on every pair of
    different algebraic numbers (measured: 64 s for one cubic with trig-form roots)."""
    from .numeric import exact_equal, has_float
    from .conventions import closed_readings
    try:
        readings = closed_readings(sp.sympify(a), sp.sympify(b))
    except (sp.SympifyError, TypeError, AttributeError):
        readings = None
    if readings is False:
        return None
    if readings is not None:
        # an odd root of a negative number written as a power (equiv.conventions): equal only when
        # both readings agree, the real root and the principal value
        (a1, b1), (a2, b2) = readings
        r1, r2 = scalar_equal(a1, b1), scalar_equal(a2, b2)
        return r1 if r1 == r2 else None
    try:
        sa, sb = sp.sympify(a), sp.sympify(b)
        exact = not (sa.free_symbols or sb.free_symbols) and not has_float(sa, sb) and not any(
            x_.has(oo, -oo, sp.zoo, sp.nan) for x_ in (sa, sb))
    except (sp.SympifyError, TypeError, AttributeError):
        exact = False
    if exact:
        r = exact_equal(sa, sb)
        if r is not None:
            return r
    ok, _ = sym_equal(a, b)
    if ok:
        return True
    okn, _ = num_equal(a, b)
    return okn


class EndpointsIncomparable(ValueError):
    """Two endpoints of one set could not be ordered exactly."""


def _endpoints(s) -> list:
    if isinstance(s, Interval):
        return [s.start, s.end]
    if isinstance(s, FiniteSet):
        return list(s.args)
    if isinstance(s, (Union, sp.Intersection, sp.Complement)):
        return [e for a in s.args for e in _endpoints(a)]
    return []


def _is_const(e) -> bool:
    return isinstance(e, sp.Expr) and bool(e.is_number) and not e.has(oo, -oo, sp.zoo, sp.nan)


_UNIFY_LIMIT = 300


def _near_key(e):
    """A 20-digit value of a constant endpoint, to compare only the pairs that can be equal; None
    when it cannot be had (such an endpoint is compared with every other)."""
    try:
        v = complex(sp.N(e, 20))
    except Exception:  # noqa: BLE001
        return None
    return v if v == v and abs(v) != float("inf") else None


def _near(a, b) -> bool:
    return a is None or b is None or abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def unify_endpoints(sets) -> list:
    """SymPy orders two endpoints by VALUE but tests them for EQUALITY by STRUCTURE (union_sets,
    intersection_sets, Interval.__new__): (-oo, sqrt(11 + 6*sqrt(2)) - sqrt(2)) U (3, oo) became
    the whole line (V14d). Endpoints proved equal get the first spelling seen; a pair neither proved
    equal nor certainly different raises: the set is not read. Only numerically near pairs are
    compared exactly (every pair was: a 1000-element set took 90 s, audit of V14), and a set with
    more than _UNIFY_LIMIT such constants is not read. Rationals count too, although two of them are
    never compared: the limit also bounds the size of a set written as text, and what follows grows
    faster than the comparisons (SymPy's Union of 100, 200 and 350 disjoint intervals took 1.4,
    6.1 and 21 s to build; a claim of 400 points 9.8 s to verify, of 250 points 4.2 s; V16, 30 Sep
    2026)."""
    from .numeric import exact_equal, has_float, certified_sign
    reps: list = []
    keys: list = []
    mapping: dict = {}
    n_const = 0
    for st in sets:
        for e in _endpoints(st):
            if not _is_const(e) or e in mapping or any(e == r for r in reps):
                continue
            n_const += 1
            if n_const > _UNIFY_LIMIT:
                raise EndpointsIncomparable(f"more than {_UNIFY_LIMIT} constants to compare")
            ke = _near_key(e)
            for r, kr in zip(reps, keys):
                if isinstance(e, sp.Rational) and isinstance(r, sp.Rational):
                    continue
                if not _near(ke, kr):
                    continue                   # 1e-9 apart at 20 digits: certainly different
                if has_float(e, r):
                    sg = certified_sign(e - r)
                    if sg in (1, -1):
                        continue
                    raise EndpointsIncomparable(f"{e} and {r}")
                eq = exact_equal(e, r)
                if eq is True:
                    mapping[e] = r
                    break
                if eq is None:
                    raise EndpointsIncomparable(f"{e} and {r}")
            else:
                reps.append(e)
                keys.append(ke)
    return [_remap(st, mapping) for st in sets] if mapping else list(sets)


def _remap(st, mapping: dict):
    """Replace whole endpoints only: xreplace also rewrites a SUBexpression (sqrt(2 + sqrt(3))
    inside -sqrt(2 + sqrt(3))) and so gives two spellings to one endpoint again."""
    m = lambda e: mapping.get(e, e)  # noqa: E731
    if isinstance(st, Interval):
        return Interval(m(st.start), m(st.end), st.left_open, st.right_open)
    if isinstance(st, FiniteSet):
        return FiniteSet(*[m(e) for e in st.args])
    if isinstance(st, (Union, sp.Intersection, sp.Complement)):
        return st.func(*[_remap(a, mapping) for a in st.args])
    return st


def _order(a, b):
    """Certified sign of a - b for two endpoints (±oo allowed); None when undecided."""
    from .numeric import certified_sign
    if a == b:
        return 0
    if a == oo or b == -oo:
        return 1
    if a == -oo or b == oo:
        return -1
    if not (_is_const(a) and _is_const(b)):
        return None
    sg = certified_sign(a - b)
    return sg if sg in (-1, 0, 1) else None


class _Unordered(Exception):
    """Two interval starts that `_order` cannot order."""


def _inf_cmp(a: Interval, b: Interval) -> int:
    c = _order(a.inf, b.inf)
    if c is None:
        raise _Unordered(f"{a.inf} and {b.inf}")
    return c


def normalize_set(s: sp.Set) -> tuple[list[Interval], list[Any]] | None:
    """Split a set into (sorted disjoint intervals, isolated points). None if unsupported."""
    if s is S.EmptySet:
        return [], []
    if s == S.Reals:
        return [Interval(-oo, oo)], []
    if isinstance(s, FiniteSet):
        return [], list(s.args)
    if isinstance(s, Interval):
        if s.left == s.right:
            return [], [s.left]
        c = _order(s.right, s.left)
        if c is None:
            if _is_const(s.left) and _is_const(s.right):
                return None                      # a degenerate interval cannot be ruled out
            return [s], []
        if c == 0:                               # Interval(3, sqrt(11 + 6*sqrt(2)) - sqrt(2))
            return ([], []) if (s.left_open or s.right_open) else ([], [s.left])
        return [s], []
    if isinstance(s, Union):
        ivs, pts = [], []
        for a in s.args:
            r = normalize_set(a)
            if r is None:
                return None
            ivs += r[0]
            pts += r[1]
        # points inside intervals are redundant; intervals sorted by inf, exactly: a float key tied two
        # starts 1e-40 apart, and the interval listed first swallowed the one before it in the merge
        # below ([sqrt(2) - 2e-40, sqrt(2) - 1e-40) U (sqrt(2), 5) was (sqrt(2), 5), V16, 30 Sep 2026);
        # a start that cannot be ordered (a symbol, an undecided constant) was put first as -1e300
        try:
            ivs = sorted(ivs, key=cmp_to_key(_inf_cmp))
        except _Unordered:
            return None
        pts2 = []
        for p in pts:
            if not any(iv.contains(p) == True for iv in ivs):  # noqa: E712
                pts2.append(p)
        # merge intervals that touch/overlap (Union already does this, but be safe)
        merged: list[Interval] = []
        for iv in ivs:
            if merged:
                m = merged[-1]
                c = _order(m.sup, iv.inf)
                if c is None:
                    return None
                if c > 0 or (c == 0 and not (m.right_open and iv.left_open)):
                    d = _order(iv.sup, m.sup)
                    if d is None:
                        return None
                    sup, ro = ((iv.sup, iv.right_open) if d > 0 else (m.sup, m.right_open) if d < 0
                               else (m.sup, m.right_open and iv.right_open))
                    merged[-1] = Interval(m.inf, sup, left_open=m.left_open, right_open=ro)
                    continue
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
