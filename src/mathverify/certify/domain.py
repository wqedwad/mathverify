"""Domain guard (E2, E4): definedness conditions, root guarding, domain-of-expression.

The most frequent AYT trap: log argument > 0, even root radicand >= 0, denominator != 0,
tan/cot poles, asin/acos range. Every candidate root produced by ANY solver API is
checked here against (a) the problem's domain of discourse, (b) the definedness
conditions of the ORIGINAL expression, and (c) the original relation itself.
"""
from __future__ import annotations

import itertools
import threading
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
def _outer_nodes(e, var, add):
    """The nodes of `e` in preorder, a range binder's body excepted: its conditions are taken from
    `definedness_conditions` of the body, and those on the bound variable are dropped (they hold on
    the binder's range, not on the problem's variables); its bounds are walked as usual. Walked into,
    ∫_1^e 1/t dt put t != 0 among the conditions of x > ∫…: the solution set collapsed to EmptySet,
    which was certified, and with the bound x of Limit(sin(x)/x, x, 0) the root 0 of x**2 = … was
    dropped (third audit of 30 Sep 2026)."""
    stack = [e]
    while stack:
        n = stack.pop()
        if isinstance(n, (sp.Integral, sp.Sum, sp.Product)) or isinstance(n, sp.Limit):
            if isinstance(n, sp.Limit):
                body, bound, outer = n.args[0], {n.args[1]}, [n.args[2]]
            else:
                body, bound = n.function, {lim[0] for lim in n.limits}
                outer = [x for lim in n.limits for x in lim[1:]]
            for c in definedness_conditions(body, var):
                if not (getattr(c, "free_symbols", set()) & bound):
                    add(c)
            for c in _binder_conditions(n, var):
                add(c)
            stack.extend(reversed(outer))
            continue
        yield n
        if isinstance(n, sp.Basic):
            stack.extend(reversed(n.args))


class definedness_undecided(sp.Function):  # noqa: N801 - a marker read by closed_condition_undecided
    """The value of a condition no check could decide: see DEFINEDNESS_UNDECIDED."""
    nargs = 0


# A condition that stands for "the body of a binder is not proved to exist over its range": closed and
# left standing by SymPy, so `closed_condition_undecided` makes every caller abstain, and never
# false, so no expression is read as undefined (defined NOWHERE) on its account.
DEFINEDNESS_UNDECIDED = Ne(definedness_undecided(), 0)


def is_undecided(c) -> bool:
    return c == DEFINEDNESS_UNDECIDED


# The index values of a Sum/Product checked one by one, and the work one top-level reading may spend
# on binders (a solveset counts as _SOLVE_COST points): a nested finite sum is checked at every
# (outer, inner) pair, and 150 x 150 of them held verify() 33 s, three levels over 400 s (review of
# 30 Sep 2026). Past the budget the body is not proved to exist and the callers abstain.
_POINTS = 200
_BUDGET = 400
_SOLVE_COST = 50
_SOLVE_TIMEOUT = 4.0
_BINDER_STATE = threading.local()


def _spend(n: int) -> bool:
    left = getattr(_BINDER_STATE, "left", None)
    if left is None:
        return True                                 # outside a reading (a direct call)
    if left < n:
        return False
    _BINDER_STATE.left = left - n
    return True


def _evaluated(e):
    """A bound or a point of the as-written tree, evaluated: 10**3 stays Pow(10, 3) there."""
    with sp.evaluate(True):
        return e.func(*[_evaluated(a) for a in e.args]) if isinstance(e, sp.Basic) and e.args else e


def _named_conditions(body, bound, var):
    """The written conditions of a binder's body that name one of its bound variables, read on
    assumption-free dummies (the as-written parse keeps the declared symbol there, and k declared
    positive made k != 0 true), with the map to the dummies."""
    plain = {v: sp.Dummy(v.name) for v in bound}
    with sp.evaluate(False):
        b = body.xreplace(plain)
    dummies = set(plain.values())
    return [c for c in definedness_conditions(b, var) if getattr(c, "free_symbols", set()) & dummies], plain


def _violations(c, d, region):
    """Where in `region` the condition `c` on `d` fails, computed in the sandbox under a time limit;
    None when that is not known exactly (solveset over a Range of a transcendental condition did not
    return, review of 30 Sep 2026)."""
    if not _spend(_SOLVE_COST):
        return None
    if isinstance(c, sp.Contains) and c.args[0] == d:
        try:
            inside = region.is_subset(c.args[1])
        except Exception:  # noqa: BLE001
            inside = None
        return S.EmptySet if inside is True else None
    bad = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else sp.Not(c)
    r = sb_run("mathverify.sandbox.ops:solveset_in", bad, d, region, timeout=_SOLVE_TIMEOUT)
    if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
        return None
    return r.value


def _undefined_at(body, index_values: dict, var) -> bool | None:
    """The term of a Sum/Product at concrete index values, read as written: False when one of its
    conditions fails there (the term itself is undefined), None otherwise. Only this makes a sum
    undefined: a condition read on the symbolic body may be merely sufficient (a real power of a
    symbolic exponent asks base > 0, and (-1)**1 is defined), and turned into `false` it made
    x + Σ_{k=1}^{3} (-k)**k = 0 "defined nowhere" and its empty solution set certified (review of
    30 Sep 2026)."""
    with sp.evaluate(False):
        term = body.xreplace(index_values)
    conds = definedness_conditions(term, var)
    return False if any(c is sp.false for c in conds) else None


def _index_region(lo, hi):
    """The integers a Sum/Product index runs over (exact), or a superset of them when a bound is
    symbolic and the range cannot be reversed (hi - lo + 1 >= 0 from the declarations: reversed,
    SymPy's Karr sum runs over indices outside the superset, review of 30 Sep 2026); None otherwise."""
    lo_i = lo.is_Integer or lo == -oo
    hi_i = hi.is_Integer or hi == oo
    if lo_i and hi_i:
        start = -oo if lo == -oo else int(lo)
        stop = oo if hi == oo else int(hi) + 1
        if start == -oo and stop == oo:
            return S.Integers, True
        return sp.Range(start, stop), True
    if (hi - lo + 1).is_nonnegative is not True:
        return None, False
    if lo.is_Integer:
        return sp.Range(int(lo), oo), False
    if hi.is_Integer:
        return sp.Range(-oo, int(hi) + 1), False
    return S.Integers, False


def _range_conditions(n, var) -> list[Any]:
    """Sum/Product: the term, as written, at every index. A finite range of at most _POINTS indices is
    checked index by index (the term's own conditions there: a failing one makes the sum undefined,
    those on the problem's symbols are kept, Σ_{k=1}^{3} 1/(k - x) needs x != 1, 2, 3); a longer or
    infinite range, or a symbolic bound, by solving each condition over the index range, and a
    violation found there makes the sum undefined only where the term itself is undefined at it.
    Before 30 Sep 2026 these conditions were dropped (they name the index, not the problem's
    variables) and Σ_{k=-1}^{1000} k/k = 1002, Σ_{k<=0} 2^k k/k = 2 and Σ_{k=-1}^{n} k/k with n = 3
    were certified; the first V14 checked only finite sums of at most 200 terms."""
    limits = n.limits
    if any(len(lim) != 3 for lim in limits):
        return [DEFINEDNESS_UNDECIDED]
    idx = [lim[0] for lim in limits]
    named, plain = _named_conditions(n.function, idx, var)
    if not named:
        return []
    bounds = [(_evaluated(lim[1]), _evaluated(lim[2])) for lim in limits]
    if all(lo.is_Integer and hi.is_Integer for lo, hi in bounds):
        ranges = [range(int(lo), int(hi) + 1) for lo, hi in bounds]
        count = 1
        for r in ranges:
            count *= len(r)
        if count <= _POINTS:
            if not _spend(count):
                return [DEFINEDNESS_UNDECIDED]
            out: list[Any] = []
            for point in itertools.product(*ranges):
                with sp.evaluate(False):
                    term = n.function.xreplace({v: sp.Integer(i) for v, i in zip(idx, point)})
                for c in definedness_conditions(term, var):
                    if c is sp.false:
                        return [sp.false]
                    if c not in out:
                        out.append(c)
            return out
    if len(limits) != 1:
        return [DEFINEDNESS_UNDECIDED]
    (lo, hi), = bounds
    region, exact = _index_region(lo, hi)
    if region is None:
        return [DEFINEDNESS_UNDECIDED]
    d = plain[idx[0]]
    for c in named:
        if c.free_symbols != {d}:
            return [DEFINEDNESS_UNDECIDED]          # also names the problem's symbols or another index
        bad = _violations(c, d, region)
        if bad is None:
            return [DEFINEDNESS_UNDECIDED]
        if bad.is_empty is True:
            continue
        if exact and bad.is_finite_set is True:
            points = list(itertools.islice(iter(bad), 5))
            if points and _spend(len(points)) and any(
                    _undefined_at(n.function, {idx[0]: sp.Integer(i)}, var) is False for i in points):
                return [sp.false]
        return [DEFINEDNESS_UNDECIDED]
    return []


def _integral_conditions(n, var) -> list[Any]:
    """A definite integral: the integrand, as written, exists on [a, b] up to finitely many points (an
    improper point is the value's business). ∫_{-1}^{1} (√x)² dx = 0 was certified (30 Sep 2026)."""
    definite = [lim for lim in n.limits if len(lim) == 3]
    if not definite:
        return []                                   # an antiderivative: its variable is not bounded
    if len(n.limits) != 1:
        named, _ = _named_conditions(n.function, [lim[0] for lim in n.limits], var)
        return [DEFINEDNESS_UNDECIDED] if named else []
    x, a, b = n.limits[0]
    named, plain = _named_conditions(n.function, [x], var)
    d = plain[x]
    region = S.Reals
    a, b = _evaluated(a), _evaluated(b)
    if a.is_number and b.is_number:
        order = certified_sign(b - a) if not (a.has(oo, -oo) or b.has(oo, -oo)) else None
        if a.has(oo, -oo) or b.has(oo, -oo):
            region = Interval(min(a, b), max(a, b)) if a != b else S.EmptySet
        elif order in (-1, 0, 1):
            region = Interval(b, a) if order == -1 else Interval(a, b)
        else:
            return [DEFINEDNESS_UNDECIDED] if named else []
    for c in named:
        bad = _violations(c, d, region)
        if bad is None or not (bad.is_empty is True or bad.is_finite_set is True):
            return [DEFINEDNESS_UNDECIDED]
    return []


def _limit_conditions(n, var) -> list[Any]:
    """A limit: its expression, as written, exists on a punctured neighbourhood of the point on the
    approached side(s), and near ±oo from some point on. lim_{x→-∞} (√x)²/x = 1 was certified
    (30 Sep 2026). A condition that names the problem's symbols too is solved with them as
    parameters: the hole of (x² - a²)/(x - a) at x = a is no violation near a."""
    e, z, z0, direction = n.args
    named, plain = _named_conditions(e, [z], var)
    if not named:
        return []
    zd = plain[z]
    z0 = _evaluated(z0)
    if getattr(z, "is_integer", None) and z0 not in (oo, -oo):
        return [DEFINEDNESS_UNDECIDED]
    for c in named:
        if z0 in (oo, -oo):
            bad = _violations(c, zd, S.Integers if getattr(z, "is_integer", None) else S.Reals)
            if bad is None:
                return [DEFINEDNESS_UNDECIDED]
            if bad.is_empty is not True and (bad.sup if z0 == oo else bad.inf).is_finite is not True:
                return [DEFINEDNESS_UNDECIDED]
            continue
        for side in (("+", "-") if str(direction) == "+-" else (str(direction),)):
            near = Interval.open(z0, z0 + 1) if side == "+" else Interval.open(z0 - 1, z0)
            bad = _violations(c, zd, near)
            if bad is None:
                return [DEFINEDNESS_UNDECIDED]
            if bad.is_empty is True:
                continue
            try:
                gap = certified_sign(bad.inf - z0 if side == "+" else z0 - bad.sup)
            except Exception:  # noqa: BLE001
                gap = None
            if gap != 1:
                return [DEFINEDNESS_UNDECIDED]
    return []


def _binder_conditions(n, var) -> list[Any]:
    """The conditions a binder's body puts on its bound variable, decided over the binder's range
    (see _range_conditions, _integral_conditions, _limit_conditions): `false` when the body is proved
    undefined there, DEFINEDNESS_UNDECIDED when it is not proved to exist, conditions on the
    problem's own symbols otherwise. The whole reading shares one budget."""
    top = getattr(_BINDER_STATE, "left", None) is None
    if top:
        _BINDER_STATE.left = _BUDGET
    try:
        if isinstance(n, (sp.Sum, sp.Product)):
            return _range_conditions(n, var)
        if isinstance(n, sp.Integral):
            return _integral_conditions(n, var)
        if isinstance(n, sp.Limit):
            return _limit_conditions(n, var)
        return []
    except Exception:  # noqa: BLE001 - a check that fails proves nothing
        return [DEFINEDNESS_UNDECIDED]
    finally:
        if top:
            _BINDER_STATE.left = None


def definedness_conditions(expr, var) -> list[Any]:
    """Collect conditions under which `expr` is a well-defined real number."""
    conds: list[Any] = []
    seen: set = set()

    def add(c):
        if isinstance(c, sp.Basic) and c.has(sp.Function) and any(
                type(n).__name__ == "written_domain" for n in sp.preorder_traversal(c)):
            # the marker's own condition is taken where it stands; around it, its body is the value
            # (1/f(2) for f on x > 2 was read as undecidable, third audit of 30 Sep 2026)
            c = c.replace(lambda n: type(n).__name__ == "written_domain", lambda n: n.args[0])
        if c is sp.true:
            return
        if c not in seen:
            seen.add(c)
            conds.append(c)

    for node in _outer_nodes(sp.sympify(expr), var, add):
        if type(node).__name__ == "written_domain":
            # an IR function's declared domain at its call (normalize.parse.written_domain)
            rel = node.args[1]
            for c in (rel.args if isinstance(rel, sp.And) else (rel,)):
                add(c)
        elif isinstance(node, sp.log):
            add(node.args[0] > 0)
            if len(node.args) > 1:
                add(node.args[1] > 0)
                add(Ne(node.args[1], 1))
        elif isinstance(node, sp.Pow):
            base, ex = node.args
            ex = _numeric_exponent(ex)
            if isinstance(ex, sp.Rational) and not ex.is_Integer:
                if ex.q % 2 == 0:
                    add(base >= 0 if ex > 0 else base > 0)
                elif ex < 0:
                    add(Ne(base, 0))
            elif ex.is_Integer and ex < 0:
                add(Ne(base, 0))
            elif ex.is_number and not ex.is_rational:
                add(base > 0)
            elif not ex.is_number and base.free_symbols and (var is None or var in ex.free_symbols):
                add(base > 0)          # x^y style real power (var None: every symbol counts)
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
        elif type(node).__name__ in ("gcd", "lcm"):
            # normalize.parse.gcd/lcm have a value only at rational numbers: x + gcd(x, 2) - gcd(2, x)
            # read as x was certified a simplification of x on all of R, and its value at
            # x = sqrt(2) was certified (30 Sep 2026). No interval rule decides the condition: the
            # callers abstain unless a point makes it true or false.
            for a in node.args:
                add(sp.Contains(a, S.Rationals))
        elif isinstance(node, sp.factorial):
            # n! of the curriculum: n a natural number. x + x! - x! at x = -3 was certified -3, and
            # (x + 3)(x - 2) = x! - x! had its root -3 certified (30 Sep 2026)
            add(sp.Contains(node.args[0], S.Naturals0))
        elif isinstance(node, sp.binomial):
            # C(n, r) of the curriculum, like n!: C(x, 2) at x = -3 was certified while P(x, 2),
            # built on factorial, was not (review of 30 Sep 2026)
            for a in node.args:
                add(sp.Contains(a, S.Naturals0))
        elif isinstance(node, sp.acosh):
            add(node.args[0] >= 1)
        elif isinstance(node, sp.atanh):
            add(node.args[0] > -1)
            add(node.args[0] < 1)
    return conds


_NUMBER_SETS = (S.Rationals, S.Integers, S.Naturals0, S.Naturals)


def decide_membership(a, s) -> bool | None:
    """Membership of the constant `a` in one of the number sets the definedness conditions name.
    SymPy decides it for sqrt(2) but leaves it standing for sqrt(2) + sqrt(3), and the value
    x + gcd(x, 2) - gcd(2, x) at that x was certified (review of 30 Sep 2026). An algebraic number is
    rational exactly when its minimal polynomial is linear; that polynomial then gives its value.
    Anything else (pi + E) stays undecided."""
    try:
        r = s.contains(a)
    except Exception:  # noqa: BLE001
        return None
    if r is sp.true or r is sp.false:
        return bool(r)
    if s not in _NUMBER_SETS or not isinstance(a, sp.Expr) or a.free_symbols or a.is_algebraic is not True \
            or sp.count_ops(a) > 40:
        return None
    try:
        p = sp.minimal_polynomial(a, sp.Dummy("t"), polys=True)
    except Exception:  # noqa: BLE001
        return None
    if p.degree() != 1:
        return False                                  # irrational: in none of these sets
    c1, c0 = p.all_coeffs()
    r = s.contains(sp.Rational(-c0, c1))
    return bool(r) if r in (sp.true, sp.false) else None


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


def _numeric_exponent(ex):
    """An exponent that is a number but was left unevaluated (`x**(1/2)` read as written is
    Pow(x, Mul(1, Pow(2, -1)))), evaluated exactly so that the Rational rules above apply.
    Measured 25 Sep 2026: read as written, `x**(1/2)` produced NO condition, and the formal layer
    certified "the domain of x**(1/2) is ℝ"."""
    if getattr(ex, "is_number", False) and not ex.is_Atom:
        try:
            return sp.simplify(ex)
        except Exception:  # noqa: BLE001
            return ex
    return ex


# Functions defined on all of ℝ (no condition), and the ones the rules above bound. Anything
# else — factorial or gamma of a variable, Mod, atan2, an undefined function, an integral — has a
# real domain these rules do not describe.
_TOTAL_FUNCS = (sp.sin, sp.cos, sp.exp, sp.Abs, sp.atan, sp.acot, sp.sinh, sp.cosh, sp.tanh,
                sp.asinh, sp.floor, sp.ceiling, sp.frac, sp.sign, sp.Max, sp.Min)
_BOUNDED_FUNCS = (sp.log, sp.tan, sp.sec, sp.cot, sp.csc, sp.asin, sp.acos, sp.acosh, sp.atanh)
# sets are containers: their elements are checked (an ImageSet's Lambda is not, so it refuses)
_CONTAINERS = (sp.Tuple, sp.Set, sp.core.relational.Relational, sp.And, sp.Or, sp.Not)


def _closed_int(e) -> int | None:
    try:
        v = sp.simplify(e)
    except Exception:  # noqa: BLE001
        return None
    return int(v) if isinstance(v, sp.Integer) else None


def _closed_rational(e):
    try:
        v = sp.simplify(e)
    except Exception:  # noqa: BLE001
        return None
    return v if isinstance(v, sp.Rational) else None


def definedness_conditions_strict(expr, var=None) -> list[Any] | None:
    """`definedness_conditions`, but EXACT or nothing: None when the expression contains an
    operation whose real domain the rules do not describe (factorial/gamma/gcd of a variable,
    `Mod`, a power with a variable exponent whose base is not a positive constant, an undefined
    function, ...). Measured 25 Sep 2026 (formal-layer audit): `0**x`, `(-2)**x` and
    `factorial(x)` produced no condition, so "the domain is ℝ" was certified both by Lean and by
    the deterministic domain_of certificate. A caller that has to be exact abstains on None."""
    if isinstance(expr, str):
        return None                               # never sympify raw text here
    try:
        e = sp.sympify(expr)
    except (sp.SympifyError, TypeError):
        return None
    for node in sp.preorder_traversal(e):
        if node.is_Atom or isinstance(node, (sp.Add, sp.Mul) + _CONTAINERS + _TOTAL_FUNCS + _BOUNDED_FUNCS):
            continue
        if type(node).__name__ == "arccot":            # normalize.parse.arccot read as written: total
            continue
        if type(node).__name__ == "written_domain":    # its condition is read by definedness_conditions
            continue
        if isinstance(node, sp.Pow):
            base, ex = node.args
            ex = _numeric_exponent(ex)
            if ex.is_number:
                if ex.is_real is True:
                    continue                      # the rules of definedness_conditions apply
                return None
            if base.is_number:
                try:
                    b = sp.simplify(base)
                except Exception:  # noqa: BLE001
                    return None
                if b.is_positive is True:
                    continue                      # c**x with c > 0: defined for every real x
            return None                           # 0**x, (-2)**x, x**x, x**y: no interval rule
        name = type(node).__name__
        if name in ("factorial", "binomial"):
            if node.free_symbols:
                return None
            ints = [_closed_int(a) for a in node.args]
            if any(i is None for i in ints) or any(i < 0 for i in ints):
                return None
            continue
        if name in ("gcd", "lcm"):
            # defined for any rational numbers (normalize.parse.gcd); read as written, lcm(-4, 6)
            # stays unevaluated and a nonnegative-integer rule refused it (audit of 29 Sep 2026)
            if node.free_symbols or not all(isinstance(_closed_rational(a), sp.Rational) for a in node.args):
                return None
            continue
        return None                               # unknown operation: no exact domain
    conds = definedness_conditions(e, var)
    for node in sp.preorder_traversal(e):
        if isinstance(node, sp.Pow):
            ex = _numeric_exponent(node.args[1])
            if ex.is_number and not ex.is_rational and ex.is_positive is True:
                # 0**pi = 0: a positive irrational exponent needs base >= 0, not > 0
                strict = node.args[0] > 0
                conds = [node.args[0] >= 0 if c == strict else c for c in conds]
    return conds


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
    if isinstance(rel, sp.Contains):
        # a gcd/lcm or factorial argument's set (definedness_conditions): SymPy decides membership
        # of an exact number (sqrt(2) is not rational) and leaves it standing when it cannot
        try:
            r = rel.subs(var, c)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(r, sp.Contains):
            return decide_membership(r.args[0], r.args[1])
        return True if r is sp.true else False if r is sp.false else None
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
    if isinstance(r, sp.Basic) and r.has(sp.Contains):
        # a domain cut by a gcd/lcm or factorial condition (Ctx.domain_for): decide each membership
        decided = {m: decide_membership(*m.args) for m in r.atoms(sp.Contains)}
        try:
            r = r.xreplace({m: sp.true if d else sp.false for m, d in decided.items() if d is not None})
        except Exception:  # noqa: BLE001
            pass
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


def closed_condition_undecided(conds) -> bool:
    """Is one of these definedness conditions CLOSED (no free symbol), left standing by SymPy and
    proved by no exact check? tan(arccot(2) + arccot(1/2)) is tan(pi/2): its condition
    cos(arccot(2) + arccot(1/2)) != 0 stays symbolic, carries no symbol, and was dropped, so the
    maximum of x + 0*tan(...) on [0, 1] and the root of x + tan(...) - tan(...) = 1 were certified
    (audit of 29 Sep 2026). The expression may be undefined everywhere; the caller abstains."""
    from ..equiv.forms import checked_forms, has_closed_form
    for c in conds:
        if isinstance(c, sp.Contains) and not c.free_symbols:
            return True                     # a membership SymPy could not decide (closed, left standing)
        if isinstance(c, sp.core.relational.Relational) and not c.free_symbols:
            try:
                if has_closed_form(c):
                    # Limit(sin(2x)/x, x, 0) != 0 is read with the limit's confirmed value
                    c = checked_forms(c)
                    if c is sp.true:
                        continue
                    if c is sp.false:
                        return True
                if relation_holds_at(c, sp.Dummy("_closed"), 0) is not True:
                    return True
            except Exception:  # noqa: BLE001 - a check that fails (or a form no number confirms) proves nothing
                return True
    return False


def written_closed_undecided(src: str, ns: dict[str, Any]) -> bool:
    """`closed_condition_undecided` for an IR text read as written (see `written_definedness`)."""
    from ..normalize.parse import parse_as_written
    e = parse_as_written(src, ns)
    if e is None:
        return False
    try:
        return closed_condition_undecided(definedness_conditions(e, None))
    except Exception:  # noqa: BLE001
        return False


def written_undefined_in(src: str, ns: dict[str, Any], var, region: sp.Set) -> bool | None:
    """Is the expression, AS WRITTEN, undefined somewhere in `region` (a point set, an interval, an
    index Range)? None when that cannot be decided. Measured 23 Sep 2026 on kinds that keep their
    own domain handling: "(x²/x)' at 0 is 1", "max of x/x − x² on [−1, 1] is 1" (never attained)
    and "Σ_{k=−1}^{1} k/k = 3" were certified CORRECT."""
    # the task's interval or point must lie where the variable is declared: with x declared positive
    # the parse folds |x| to x, and on [-1, 1] the minimum of |x| - x**2 was certified to be -2, the
    # derivative of x*|x| at -1 too (-2; it is 2); no reading gives these (second audit of 29 Sep 2026)
    # (the closure for a positive variable: an interval [0, 2] is the common way to write it)
    decl = Interval(0, oo) if getattr(var, "is_nonnegative", None) else S.Reals
    try:
        inside = region.is_subset(decl)
    except Exception:  # noqa: BLE001
        inside = None
    if inside is not True:
        return True
    conds, nowhere = written_definedness(src, ns)
    if var in nowhere or written_closed_undecided(src, ns):
        return True                    # a closed condition no check proves: the callers abstain
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
    conds = definedness_conditions_strict(expr, var)
    if conds is None:
        # an operation whose real domain the rules do not describe (0**x, (-2)**x, factorial(x)):
        # no domain rather than ℝ (measured 25 Sep 2026: "the domain of factorial(x) is ℝ" CORRECT)
        return None, {"error": "definedness_unknown", "expr": str(expr)}
    ev: dict[str, Any] = {"conditions": [str(c) for c in conds]}
    dom = base
    for cond in conds:
        r = sb_run("mathverify.sandbox.ops:solveset_in", cond, var, S.Reals, timeout=timeout)
        if not r.ok or isinstance(r.value, sp.ConditionSet):
            ev["fallback"] = "continuous_domain"
            r2 = sb_run("mathverify.sandbox.ops:continuous_domain", expr, var, base, timeout=timeout)
            if r2.ok and not isinstance(r2.value, sp.ConditionSet):
                return r2.value, ev
            ev["error"] = r.error or r2.error
            return None, ev
        if _solveset_contradicted(cond, var, r.value):
            ev["error"] = f"solveset_contradicted_by_exact_check: {cond}"
            return None, ev
        dom = sp.Intersection(dom, r.value)
    ev["domain"] = str(dom)
    return dom, ev


def _solveset_contradicted(cond, var, s) -> bool:
    """Does an exact check contradict SymPy's solution set of `cond`? Each excluded isolated point must
    fail the condition, and a point inside each interval piece must meet it (or fail it, outside).
    solveset reads cos(atan(x) + atan(2)) != 0 as x != -2, where the cosine is 1 (the root is 1/2), and
    that domain was certified (audit of 29 Sep 2026). Only a contradiction counts: an undecided check
    leaves SymPy's set as it was."""
    try:
        out = sp.Complement(S.Reals, s)
    except Exception:  # noqa: BLE001
        return False
    checks = []
    for piece, inside in ((s, True), (out, False)):
        parts = piece.args if isinstance(piece, sp.Union) else (piece,)
        for p in parts:
            if isinstance(p, sp.FiniteSet) and len(p) <= 12:
                # SymPy cannot always tell a closed point is real: -tan(atan(2) + atan(3)) (= 1, the
                # point it wrongly excludes for 1/sin(arccot(x) + arccot(2) + arccot(3))) has is_real
                # None, went unchecked, and the true domain R minus {-1} was refuted
                checks += [(q, inside) for q in p if q.is_real or (q.is_number and q.is_real is None)]
            elif isinstance(p, sp.Interval) and p.measure.is_positive:
                lo, hi = p.inf, p.sup
                q = (lo + hi) / 2 if lo.is_finite and hi.is_finite else (hi - 1 if lo.is_infinite and hi.is_finite
                                                                         else lo + 1 if lo.is_finite else sp.Integer(0))
                checks.append((q, inside))
    for q, inside in checks[:24]:
        h = relation_holds_at(cond, var, q)
        if h is not None and h is not inside:
            return True
    return False


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
        # the expression AS WRITTEN must have a domain the rules describe exactly, too: the normal
        # parse folds `factorial(x)/factorial(x)` to 1 before any rule sees it
        from ..normalize.parse import parse_as_written
        written = parse_as_written(ir.task.params["expr"], ctx.ns)
        if written is not None and any(definedness_conditions_strict(w, var) is None for w in written):
            return unknown(LAYER, "domain_undecidable", 0, {"error": "definedness_unknown_as_written"},
                           flags=["cas_failed"])
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
