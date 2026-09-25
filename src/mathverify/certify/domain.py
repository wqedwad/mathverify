"""Domain guard (E2, E4): definedness conditions, root guarding, domain-of-expression.

The most frequent AYT trap: log argument > 0, even root radicand >= 0, denominator != 0,
tan/cot poles, asin/acos range. Every candidate root produced by ANY solver API is
checked here against (a) the problem's domain of discourse, (b) the definedness
conditions of the ORIGINAL expression, and (c) the original relation itself.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S, Eq, Ne, Interval, oo

from ..equiv.numeric import (num_equal, to_mp, certified_sign, certified_integer, has_float,
                             real_odd_roots, NONREAL)
from ..equiv.symbolic import sym_equal
from ..equiv.sets import set_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.domain"


# ---------------------------------------------------------------------------
def definedness_conditions(expr, var) -> list[Any]:
    """Collect conditions under which `expr` is a well-defined real number."""
    conds: list[Any] = []
    seen: set = set()

    def add(c):
        if c is sp.true:
            return
        if c not in seen:
            seen.add(c)
            conds.append(c)

    for node in sp.preorder_traversal(sp.sympify(expr)):
        if isinstance(node, sp.log):
            add(node.args[0] > 0)
            if len(node.args) > 1:
                add(node.args[1] > 0)
                add(Ne(node.args[1], 1))
        elif isinstance(node, sp.Pow):
            base, ex = node.args
            if isinstance(ex, sp.Rational) and not ex.is_Integer:
                if ex.q % 2 == 0:
                    add(base >= 0 if ex > 0 else base > 0)
                elif ex < 0:
                    add(Ne(base, 0))
            elif ex.is_Integer and ex < 0:
                add(Ne(base, 0))
            elif ex.is_number and not ex.is_rational:
                add(base > 0)
            elif not ex.is_number and base.free_symbols and var in ex.free_symbols:
                add(base > 0)          # x^y style real power
        elif isinstance(node, sp.tan):
            add(Ne(sp.cos(node.args[0]), 0))
        elif isinstance(node, sp.sec):
            add(Ne(sp.cos(node.args[0]), 0))
        elif isinstance(node, sp.cot):
            add(Ne(sp.sin(node.args[0]), 0))
        elif isinstance(node, sp.csc):
            add(Ne(sp.sin(node.args[0]), 0))
        elif isinstance(node, (sp.asin, sp.acos)):
            add(node.args[0] >= -1)
            add(node.args[0] <= 1)
        elif isinstance(node, sp.acosh):
            add(node.args[0] >= 1)
        elif isinstance(node, sp.atanh):
            add(node.args[0] > -1)
            add(node.args[0] < 1)
    return conds


def _certified_compare(lhs, rhs) -> int | str | None:
    """Certified sign of lhs − rhs for two real constants (see equiv.numeric.certified_sign);
    NONREAL when either side is certainly not real, None when undecided."""
    for side in (lhs, rhs):
        s = certified_sign(side)
        if s == NONREAL:
            return NONREAL
        if s is None:
            return None
    return certified_sign(sp.sympify(lhs) - sp.sympify(rhs))


def _num_relation_holds(rel, var, c) -> bool | None:
    """Evaluate a relational at var=c. Exact values are decided exactly: a sign is certified
    (strict adaptive evalf) and a zero proved (CAS rewrite / minimal polynomial), never read off
    rounding noise — at x = 1 + √2 the exact zero x² − 2x − 1 evaluated to −3.5e-192 and decided
    `≥ 0` False (audit of 25 Sep 2026). Undecidable -> None. Odd roots are real roots."""
    if rel is sp.true:
        return True
    if rel is sp.false:
        return False
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    lhs = real_odd_roots(rel.lhs.subs(var, c))
    rhs = real_odd_roots(rel.rhs.subs(var, c))
    if isinstance(rel, Eq):
        # exact structural first, then numeric
        okS, _ = sym_equal(lhs, rhs)
        if okS:
            return True
        okN, _ = num_equal(lhs, rhs)
        return okN
    if isinstance(rel, Ne):
        okS, _ = sym_equal(lhs, rhs)
        if okS:
            return False
        okN, _ = num_equal(lhs, rhs)
        return None if okN is None else (not okN)
    if not has_float(lhs, rhs):
        s = _certified_compare(lhs, rhs)
        if s == NONREAL:
            return False                  # non-real value: relation is not satisfied in R
        if s is None:
            return None
        if isinstance(rel, sp.StrictLessThan):
            return s < 0
        if isinstance(rel, sp.LessThan):
            return s <= 0
        if isinstance(rel, sp.StrictGreaterThan):
            return s > 0
        if isinstance(rel, sp.GreaterThan):
            return s >= 0
        return None
    # inexact (Float) operands: tolerant comparison at their own precision
    try:
        a, b = to_mp(lhs, 40), to_mp(rhs, 40)
    except Exception:
        return None
    import mpmath as mp
    if isinstance(a, mp.mpc) or isinstance(b, mp.mpc):
        return False                      # non-real value: relation is not satisfied in R
    eq, _ = num_equal(lhs, rhs)
    if isinstance(rel, sp.StrictLessThan):
        return (a < b) and not eq
    if isinstance(rel, sp.LessThan):
        return (a < b) or bool(eq)
    if isinstance(rel, sp.StrictGreaterThan):
        return (a > b) and not eq
    if isinstance(rel, sp.GreaterThan):
        return (a > b) or bool(eq)
    return None


def relation_holds_at(rel, var, c) -> bool | None:
    """Does the (original) relation hold at var=c? Tri-state."""
    if isinstance(rel, (sp.And, sp.Or)):
        parts = [relation_holds_at(a, var, c) for a in rel.args]
        if isinstance(rel, sp.And):
            if any(p is False for p in parts):
                return False
            return True if all(p is True for p in parts) else None
        if any(p is True for p in parts):
            return True
        return False if all(p is False for p in parts) else None
    if rel is sp.true:
        return True
    if rel is sp.false:
        return False
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    # never let `rel.subs` auto-evaluate a numeric Eq/inequality: Float rounding would
    # turn a true identity into False. Substitute the sides and compare tolerantly.
    return _num_relation_holds(rel, var, c)


def _cmp_le(a, b, strict: bool) -> bool | None:
    """a < b (strict) or a <= b, certified; None when undecided."""
    if a == -oo or b == oo:
        return True
    if a == oo or b == -oo:
        return False
    s = _certified_compare(a, b)
    if s is None or s == NONREAL:
        return None
    return s < 0 if strict else s <= 0


def _in_set_certified(dom, c) -> bool | None:
    if dom == S.Reals:
        return True
    if dom is S.EmptySet:
        return False
    if isinstance(dom, Interval):
        lo = _cmp_le(dom.inf, c, dom.left_open)
        hi = _cmp_le(c, dom.sup, dom.right_open)
        if lo is False or hi is False:
            return False
        return True if (lo and hi) else None
    if isinstance(dom, sp.FiniteSet):
        hits = [_certified_compare(c, p) for p in dom.args]
        if any(h == 0 for h in hits):
            return True
        return False if all(h in (-1, 1, NONREAL) for h in hits) else None
    if isinstance(dom, sp.Union):
        parts = [_in_set_certified(p, c) for p in dom.args]
        if any(p is True for p in parts):
            return True
        return False if all(p is False for p in parts) else None
    if isinstance(dom, sp.Intersection):
        parts = [_in_set_certified(p, c) for p in dom.args]
        if any(p is False for p in parts):
            return False
        return True if all(p is True for p in parts) else None
    if isinstance(dom, sp.Complement):
        a_, b_ = (_in_set_certified(dom.args[0], c), _in_set_certified(dom.args[1], c))
        if a_ is False or b_ is True:
            return False
        return True if (a_ is True and b_ is False) else None
    if dom in (S.Integers, S.Naturals, S.Naturals0):
        is_int, k = certified_integer(c)
        if is_int is None:
            return None
        return bool(dom.contains(k)) if is_int else False
    return None


def in_domain(dom: sp.Set, c) -> bool | None:
    """Membership of a constant in a domain set. SymPy's own `contains` first; where it cannot
    decide, every comparison is certified (see _certified_compare) — the old fallback compared
    40-digit values, and returned False for any part that was not an Interval."""
    try:
        r = dom.contains(c)
    except Exception:
        r = None
    if r is sp.true:
        return True
    if r is sp.false:
        return False
    try:
        cs = certified_sign(c)
    except Exception:  # noqa: BLE001
        return None
    if cs == NONREAL:
        return False
    try:
        return _in_set_certified(dom, c)
    except Exception:  # noqa: BLE001
        return None


def guard_roots(rel, var, candidates, domain: sp.Set = S.Reals) -> tuple[list, list[tuple[Any, str]]]:
    """Return (kept, rejected[(candidate, reason)]) for candidate roots of `rel`."""
    conds = definedness_conditions(rel, var)
    kept, rejected = [], []
    for c in candidates:
        c = sp.sympify(c)
        if c.is_real is False or (c.is_number and not c.is_real and c.is_real is not None):
            rejected.append((c, "not_real"))
            continue
        d = in_domain(domain, c)
        if d is False:
            rejected.append((c, "outside_domain_of_discourse"))
            continue
        bad = None
        for cond in conds:
            h = relation_holds_at(cond, var, c)
            if h is False:
                bad = f"definedness_violated: {cond}"
                break
            if h is None:
                bad = f"definedness_undecided: {cond}"
                break
        if bad:
            rejected.append((c, bad))
            continue
        h = relation_holds_at(rel, var, c)
        if h is True:
            kept.append(c)
        elif h is False:
            rejected.append((c, "does_not_satisfy_original"))
        else:
            rejected.append((c, "undecided_original"))
    return kept, rejected


def written_definedness(src: str, ns: dict[str, Any]) -> tuple[list[Any], set]:
    """Definedness of an IR expression or relation AS WRITTEN (see `parse_as_written`): the open
    conditions, and the symbols of an expression that is defined NOWHERE (a closed condition
    that fails, e.g. `1/(x - x)`). Empty when the text cannot be read that way."""
    from ..normalize.parse import parse_as_written
    e = parse_as_written(src, ns)
    if e is None:
        return [], set()
    conds, nowhere = [], set()
    try:
        found = definedness_conditions(e, None)
    except Exception:  # noqa: BLE001
        return [], set()
    for c in found:
        if c is sp.false:
            nowhere |= e.free_symbols
        elif getattr(c, "free_symbols", None) and c not in conds:
            conds.append(c)
    return conds, nowhere


def written_undefined_in(src: str, ns: dict[str, Any], var, region: sp.Set) -> bool | None:
    """Is the expression, AS WRITTEN, undefined somewhere in `region` (a point set, an interval, an
    index Range)? None when that cannot be decided. Measured 23 Sep 2026 on kinds that keep their
    own domain handling: "(x²/x)' at 0 is 1", "max of x/x − x² on [−1, 1] is 1" (never attained)
    and "Σ_{k=−1}^{1} k/k = 3" were certified CORRECT."""
    conds, nowhere = written_definedness(src, ns)
    if var in nowhere:
        return True
    for c in conds:
        if c.free_symbols - {var}:
            return None
        bad = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else sp.Not(c)
        try:
            s = sp.solveset(bad, var, region)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(s, sp.ConditionSet):
            return None
        if s != S.EmptySet:
            return True
    return False


def domain_of_expression(expr, var, base: sp.Set = S.Reals, timeout: float = 8.0) -> tuple[sp.Set | None, dict]:
    """Domain where `expr` is real-valued: conditions -> solveset intersection; fallback continuous_domain."""
    ev: dict[str, Any] = {"conditions": [str(c) for c in definedness_conditions(expr, var)]}
    dom = base
    for cond in definedness_conditions(expr, var):
        r = sb_run("mathverify.sandbox.ops:solveset_in", cond, var, S.Reals, timeout=timeout)
        if not r.ok or isinstance(r.value, sp.ConditionSet):
            ev["fallback"] = "continuous_domain"
            r2 = sb_run("mathverify.sandbox.ops:continuous_domain", expr, var, base, timeout=timeout)
            if r2.ok and not isinstance(r2.value, sp.ConditionSet):
                return r2.value, ev
            ev["error"] = r.error or r2.error
            return None, ev
        dom = sp.Intersection(dom, r.value)
    ev["domain"] = str(dom)
    return dom, ev


# ---------------------------------------------------------------------------
def verify(ir, solution, ctx: Ctx):
    """Task kind `domain_of`: params {"expr": str, "var": str}. Claimed: set/interval."""
    if ir.task.kind != "domain_of":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        var = ctx.sym(ir.task.params.get("var", "x"))
        expr, err = parse_or_unknown(LAYER, ctx.expr, ir.task.params["expr"])
        if err:
            return err
        claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
        if err:
            return err
        if not isinstance(claimed, sp.Set):
            return unknown(LAYER, "claimed_answer_is_not_a_set", t.ms if hasattr(t, "ms") else 0)
        base = ctx.domain_for(var)
        truth, ev = domain_of_expression(expr, var, base, ctx.timeout)
        if truth is None:
            return unknown(LAYER, "domain_undecidable", 0, ev, flags=["cas_failed"])
        ok, sev = set_equal(claimed, truth)
        ev["compare"] = sev
        ev["truth"] = str(truth)
        ev["claimed"] = str(claimed)
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "set_comparison_undecided", t.ms, ev)
