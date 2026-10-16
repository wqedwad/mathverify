"""Domain guard (E2, E4): definedness conditions, root guarding, domain-of-expression.

The most frequent AYT trap: log argument > 0, even root radicand >= 0, denominator != 0,
tan/cot poles, asin/acos range. Every candidate root produced by ANY solver API is
checked here against (a) the problem's domain of discourse, (b) the definedness
conditions of the ORIGINAL expression, and (c) the original relation itself.
"""
from __future__ import annotations

import functools
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
from ..sandbox.exactsets import _hull, at_risk, exact_solveset
from .base import Ctx, Timer, result, unknown, parse_or_unknown, condition_not_applied, condition_unsolved

LAYER = "certify.domain"


# ---------------------------------------------------------------------------
def _index_symbols(n) -> dict:
    """The index of a Sum/Product read as what it is: an integer, of the sign its numeric bound gives
    (k >= 0 for a lower bound 0, k >= 1 for 1). Read as a real number, the term a**k asked a > 0 (a real
    power), a condition on the problem's symbol that no index needs: the root -1/2 of
    Sum(x**n, (n, 0, oo)) = 2/3 was dropped and {-1/2} refuted, and with a**2 = 1/4 only a = 1/2 was
    left, so Sum(a**k, (k, 0, oo)) = 2 was certified (local quality, 16 Oct 2026). A backward range
    runs over other indices, but its value there is a convention (ForwardSpans) and decides nothing."""
    out = {}
    for lim in n.limits:
        v = lim[0]
        if not isinstance(v, sp.Symbol):
            continue
        kw: dict[str, bool] = {"integer": True}
        if len(lim) == 3:
            lo, hi = _evaluated(lim[1]), _evaluated(lim[2])
            if lo.is_Integer and lo > 0:
                kw["positive"] = True
            elif lo.is_Integer and lo == 0:
                kw["nonnegative"] = True
            elif hi.is_Integer and hi < 0 and not lo.free_symbols:
                kw["negative"] = True
            elif hi.is_Integer and hi == 0 and not lo.free_symbols:
                kw["nonpositive"] = True
        out[v] = sp.Symbol(v.name, **kw)
    return out


def _zero_powers_in_range(n, body, plain) -> list:
    """0**0 inside a Sum/Product: the base b of a power b**e(k), b free of the indices, is a zero_power
    convention point when e vanishes at an index of the range, or may (a symbolic bound, an exponent that
    is not linear in one index). Σ_{k=0}^{∞} a**k at a = 0 is 0**0 + 0 + …: 1 or undefined (part d4a);
    read on an integer index the term has no condition left to say so."""
    out: list = []
    idx = set(plain.values())
    lims = {plain[lim[0]]: lim for lim in n.limits if lim[0] in plain and len(lim) == 3}
    for p in sp.preorder_traversal(body):
        if not isinstance(p, sp.Pow):
            continue
        b, e = p.args
        ks = e.free_symbols & idx
        if not ks or (b.free_symbols & idx) or not b.free_symbols or b.is_zero is False or e.is_zero is False:
            continue
        if len(ks) == 1 and next(iter(ks)) in lims and e.is_polynomial(*ks):
            k = next(iter(ks))
            poly = sp.Poly(e, k)
            if poly.degree() == 1 and not (set(poly.all_coeffs()[0].free_symbols)
                                           | set(poly.all_coeffs()[1].free_symbols)):
                k0 = -poly.all_coeffs()[1] / poly.all_coeffs()[0]
                lo, hi = _evaluated(lims[k][1]), _evaluated(lims[k][2])
                if k0.is_integer is False or (k0 - lo).is_extended_negative is True \
                        or (hi - k0).is_extended_negative is True:
                    continue
        c = sp.Contains(b, ZERO_POWER_BASE)
        if c not in out:
            out.append(c)
    return out


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
        if isinstance(n, (list, tuple)) or (isinstance(n, sp.MatrixBase) and not isinstance(n, sp.Basic)):
            # a bracketed text ("[1/(1/0), 1]") is a Python list inside the as-written Tuple, a Matrix is no
            # Basic: their elements are expressions too (fourth audit, CAP-F1; review of d4f, YO-2)
            stack.extend(reversed(list(n)))
            continue
        if isinstance(n, (sp.Integral, sp.Sum, sp.Product)) or isinstance(n, sp.Limit):
            if isinstance(n, sp.Limit):
                body, bound, outer = n.args[0], {n.args[1]}, [n.args[2]]
            else:
                body, bound = n.function, {lim[0] for lim in n.limits}
                outer = [x for lim in n.limits for x in lim[1:]]
            # the body is read on assumption-free symbols for its bound variables: the as-written parse
            # keeps the declared symbol there, and with x declared positive sqrt(-x) in
            # ∫_{-1}^{0} sqrt(-x) dx gave the closed condition `false` (-x >= 0), the expression
            # read as defined nowhere and the empty solution set of y + ∫… = 2/3 certified (V16,
            # 30 Sep 2026). Conditions on the bound variables are decided by _binder_conditions.
            # (Symbols, not Dummies: an inner binder of the body keeps one cache key across readings.)
            # A Sum/Product index is an integer of its range (`_index_symbols`).
            if isinstance(n, (sp.Sum, sp.Product)):
                plain = _index_symbols(n)
            else:
                plain = {v: sp.Symbol(v.name) for v in bound if isinstance(v, sp.Symbol)}
            with sp.evaluate(False):
                body = body.xreplace(plain)
            hidden = bound | set(plain.values())
            for c in definedness_conditions(body, plain.get(var, var)):
                if not (getattr(c, "free_symbols", set()) & hidden):
                    add(c)
            if isinstance(n, (sp.Sum, sp.Product)):
                for c in _zero_powers_in_range(n, body, plain):
                    add(c)
            for c in _binder_conditions(n, var):
                add(c)
            stack.extend(reversed(outer))
            continue
        if isinstance(n, sp.Subs):
            # at()/Subs: the body is read at its point, not on its bound variable (see _subs_conditions);
            # its points are walked as usual
            _subs_conditions(n, var, add)
            stack.extend(reversed(n.point.args))
            continue
        if isinstance(n, sp.Piecewise):
            # its branches are read where they are taken (`_piecewise_conditions`), not each everywhere
            _piecewise_conditions(n, var, add)
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


class value_missing(sp.Function):  # noqa: N801 - a marker read by is_no_value
    """The value of a closed operation that has none as written: see NO_VALUE."""
    nargs = 0


# A condition that stands for "a closed operation of the expression has no value as written": n! off the
# natural numbers ((-1)!, (1/2)!), a pole of Γ, SymPy's zoo or nan written out. It comes with `false` (the
# expression is undefined) and says more: an enclosing operation may still be given a value by a reading
# the curriculum does not have (1/Γ is entire, so 1/(-1)! = 0; P(2, 3) = 2!/(-1)! = 0 counts nothing; SymPy
# folds 1/zoo to 0), so the expression is not "defined nowhere" either (no solution, an empty domain): the
# problem is undefined as written and every caller abstains (`Ctx.written_undefined`). Read as a plain
# `false`, x + 1/(-1)! = 2 would have its empty solution set certified, and the right answer under 1/Γ is
# {2} (fourth audit, CAP-F1). Closed and left standing by SymPy, like DEFINEDNESS_UNDECIDED.
NO_VALUE = Ne(value_missing(), 0)


def is_no_value(c) -> bool:
    return c == NO_VALUE


def tree_free_symbols(e) -> set:
    """The free symbols of an as-written tree, whose Tuple may hold a Python list (a bracketed text)."""
    if isinstance(e, (list, tuple)):
        return set().union(*(tree_free_symbols(a) for a in e))
    if isinstance(e, sp.Tuple):
        return set().union(*(tree_free_symbols(a) for a in e.args))
    return set(getattr(e, "free_symbols", None) or ())


# Γ(z) of a real z has a value off its poles 0, -1, -2, ... (latex2sympy reads \Gamma and \gamma as Γ)
_GAMMA_DOMAIN = sp.Complement(S.Reals, sp.Range(-oo, 1))


class ForwardSpans(sp.Set):
    """The values hi - lo + 1 of a Sum/Product range that runs forward or is empty: the nonnegative
    ones. A negative span (the range reversed, hi < lo - 1) is neither in nor out: the value there is a
    convention (SymPy's Karr sum, the empty sum of the Iverson reading), not the curriculum's, so no
    point is dropped or kept on its account (DECISIONS §80). As `Contains(span, FORWARD_SPANS)` (see
    _range_span_conditions) it stays standing at such a point, and `decide_membership` leaves it
    undecided; read as `span >= 0`, it dropped n = -2 like an undefined point, and with n**2 = 4 the
    value 3 of Σ_{k=1}^{n} k was certified (1 Oct 2026)."""
    is_empty = False
    is_finite_set = False

    def _contains(self, other):
        if isinstance(other, sp.Expr) and other.is_extended_nonnegative is True:
            return sp.true
        return None                                 # negative or open: undecided, never false

    def _eval_is_superset(self, other):
        try:
            return True if other.is_subset(Interval(0, oo)) is True else None
        except Exception:  # noqa: BLE001
            return None


FORWARD_SPANS = ForwardSpans()


def is_range_span(c) -> bool:
    """Is `c` the range condition of a Sum/Product (see ForwardSpans)?"""
    return isinstance(c, sp.Contains) and c.args[1] == FORWARD_SPANS


class Convention(sp.Set):
    """The values of an operand where a written operation has the curriculum's one value; elsewhere its
    value is a convention, not the curriculum's, and such a point is neither in nor out, like a reversed
    Sum range (ForwardSpans, DECISIONS §80; fourth audit of 1 Oct 2026, part d4a):

    * `odd_root`: the base of b**(p/q), q odd, is >= 0. At a negative base the power is the real root
      (∛(-8) = -2) or the principal complex value (1 + √3 i); (-8)**(1/3) was certified both ways. The
      written roots (`cbrt`, `root(·, 3)`, `real_root`, `\\sqrt[3]{}`, ∛) are real roots and parse to
      sign(b)·|b|**(1/q) (normalize.parse), whose base is never negative.
    * `zero_power`: the base of b**0 is not 0 (0**0 is 1 or undefined).
    * `binomial`: r and n - r of C(n, r) are natural numbers with 0 (0 <= r <= n integers); outside, the
      generalized binomial (C(-2, 2) = 3) and the 0 above n are extensions the curriculum does not have.
    * `mod_divisor`: the divisor of Mod is positive; below it floored, truncated and Euclidean
      remainders differ (Mod(7, -5) is -3, 2 or 2).
    * `integer_bound`: a Sum/Product bound on the problem's symbols is an integer. At a non-integer bound
      SymPy steps from the lower one (Σ_{k=n}^{n+2} k = 3n + 3 at every real n), the index reading runs
      over the integers between them (3 at n = 1/2) and the curriculum has no such sum: the value is a
      convention with another value AND "undefined" among its readings. Held to the integers like an
      undefined point, a claim equal to the sum on ℤ alone (3n + 3 + sin(πn)) was CORRECT and the root
      7/3 of Σ_{k=x}^{x+2} k = 10 was dropped, refuting {7/3} and the step 3x + 3 = 10 (review of d4f,
      YO-3, RK-F1). No comparison is certified while such points exist (`Ctx.integer_bound_region`), and
      none refutes a claim there.
    * `negative_base`: the exponent of c**e, c a negative number and e not a number, is an integer. Elsewhere
      the real reading has no value or the real root ((-1)**(1/3) = -1), the principal one a complex value
      ((-1)**x = e^(i*pi*x)): x + 0*(-2)**x had the derivative 1 at 1/2, (-1)**x the limit 1 at 0 and
      x + (-1)**x - (-1)**x the primitive x certified (attack on d4e, YO-5).
    * `origin`: the operand (y**2 + x**2 of atan2(y, x), u of arg(u)) is not 0: atan2(0, 0) and arg(0)
      are undefined in mathematics and 0 in some conventions (round 8 of part d4b, YO-1).
    * `real_power`: the operand is the pair (b, e) of a power b**e whose exponent is a variable of the base's
      (x**x, (x - 4)**x): where b > 0 it has its one value; elsewhere its definedness is read from the exact
      values of b and e at the point, BEFORE the power is formed ((x**x).subs(x, 0) is SymPy's 1): an integer
      e and b != 0, or b = 0 and e a positive rational, have the one value ((-2)**(-2) = 1/4, 0**2 = 0); 0**0,
      a negative b at a non-integer e (the real root, the principal value or none) are left undecided. The
      interval rule b > 0 read at a point dropped -2 from {-2, 2}, the solution of (x + 2)(x - 2) = 0 with
      x**x (2 + sin x) > 0 on {-3, ..., 3}, and certified {2} (round 9 attack on part d4b, RK-1). `zero_power`
      covers 0**e of an irrational e > 0 too (0**sqrt(2): 0 by the strict rule, undefined as written).

    As `Contains(operand, CONVENTION)` the condition holds where the operand is proved inside and is
    left standing (undecided) elsewhere, never false: `decide_membership` and `relation_holds_at` leave
    it undecided at such a point, `closed_condition_undecided` makes every caller abstain on a closed
    one, and `Ctx.domain_for` keeps only the points where every one holds while `Ctx.convention_region`
    lists the others, where a candidate is neither kept nor dropped."""
    is_empty = False
    is_finite_set = False

    def __new__(cls, kind):
        return sp.Basic.__new__(cls, kind if isinstance(kind, sp.core.symbol.Str) else sp.core.symbol.Str(kind))

    @property
    def kind(self) -> str:
        return str(self.args[0])

    def _contains(self, other):
        if self.kind == "real_power":
            return _real_power_holds(other)
        if not isinstance(other, sp.Expr):
            return None
        k = self.kind
        if k == "odd_root":
            ok = other.is_extended_nonnegative
        elif k == "zero_power":
            # ∞⁰ is an indeterminate form like 0**0: oo**0 = 1 was certified (review of d4f, YO-7)
            ok = other.is_zero is False and other.is_infinite is False
        elif k == "origin":
            ok = other.is_zero is False
        elif k == "binomial":
            ok = other.is_integer is True and other.is_nonnegative is True
        elif k == "mod_divisor":
            ok = other.is_extended_positive
        elif k in ("integer_bound", "negative_base"):
            ok = other.is_integer
        else:
            ok = None
        return sp.true if ok is True else None      # undecided, never false

    def _eval_is_superset(self, other):
        nonzero = sp.Union(Interval.open(-oo, 0), Interval.open(0, oo))
        inside = {"odd_root": Interval(0, oo), "binomial": S.Naturals0, "mod_divisor": Interval.open(0, oo),
                  "zero_power": nonzero, "origin": nonzero, "negative_base": S.Integers,
                  "integer_bound": S.Integers}.get(self.kind)
        try:
            return True if inside is not None and other.is_subset(inside) is True else None
        except Exception:  # noqa: BLE001
            return None

    def _sympystr(self, printer):
        return f"Convention({self.kind})"


ODD_ROOT_BASE = Convention("odd_root")
ZERO_POWER_BASE = Convention("zero_power")
BINOMIAL_ARGUMENT = Convention("binomial")
MOD_DIVISOR = Convention("mod_divisor")
INTEGER_BOUND = Convention("integer_bound")
NEGATIVE_BASE_EXPONENT = Convention("negative_base")
ORIGIN = Convention("origin")
REAL_POWER = Convention("real_power")


def _real_power_holds(pair):
    """`Convention` `real_power` at the pair (b, e) of a power's base and exponent: true where b**e certainly has its
    one real value, None (undecided) elsewhere, never false (see `Convention`)."""
    if not isinstance(pair, sp.Tuple) or len(pair) != 2:
        return None
    b, e = pair
    if not (isinstance(b, sp.Expr) and isinstance(e, sp.Expr)) or e.is_extended_real is not True:
        return None
    if b.is_extended_positive is True:
        ok = True
    elif b.is_extended_real is True and b.is_zero is False:
        ok = e.is_integer is True
    elif b.is_zero is True:
        ok = e.is_rational is True and e.is_extended_positive is True
    else:
        ok = False
    return sp.true if ok else None


def is_convention(c) -> bool:
    """Is `c` a condition whose failure makes the value a convention rather than undefined: a Sum/Product
    range (ForwardSpans) or one of the Convention sets?"""
    return isinstance(c, sp.Contains) and (c.args[1] == FORWARD_SPANS or isinstance(c.args[1], Convention))


def is_value_convention(c) -> bool:
    """Is `c` a convention condition whose other reading is ANOTHER VALUE (a Sum range: Karr's sum or the
    empty one; an odd root: the real root or the principal value; Mod: floored or Euclidean), not
    "undefined" (0**0, C(n, r) outside 0 <= r <= n)? A claim refuted with SymPy's value at such a point
    may be true under the other reading; where the other reading is "undefined" the claim is not true
    either, so a refutation stands (an undefined claim is no true step, `steps.deterministic`)."""
    return is_convention(c) and (c.args[1] == FORWARD_SPANS
                                 or c.args[1].kind in ("odd_root", "mod_divisor", "negative_base", "origin",
                                                       "integer_bound", "real_power"))


def is_integer_bound(c) -> bool:
    """Is `c` the condition that a Sum/Product bound is an integer (`Convention` `integer_bound`)? Its other
    readings are another value AND "undefined": a claim is neither certified nor refuted where it fails."""
    return isinstance(c, sp.Contains) and isinstance(c.args[1], Convention) and c.args[1].kind == "integer_bound"


def convention_split(c, var) -> tuple[sp.Set, sp.Set]:
    """(the values of `var` where the convention condition `c` holds, those where it does not), over ℝ.
    A condition this cannot split gives (ℝ, ℝ): every point is undecided. A closed one (a symbol a given
    fixes, read as its value) holds everywhere or nowhere."""
    e, s = c.args
    kind = "range" if s == FORWARD_SPANS else s.kind
    # guarded (sandbox.exactsets): a trigonometric base (sin(x)**(1/3)) read on one period of ℝ split the
    # line wrongly; unsolved, it stays a ConditionSet and every point is undecided below
    solveset = exact_solveset
    try:
        if var not in e.free_symbols:
            held = sp.Contains(e, s)
            return (S.Reals, S.EmptySet) if held is sp.true else (S.EmptySet, S.Reals)
        if kind in ("range", "odd_root"):
            fwd, back = solveset(sp.Ge(e, 0), var, S.Reals), solveset(sp.Lt(e, 0), var, S.Reals)
        elif kind == "mod_divisor":
            fwd, back = solveset(sp.Gt(e, 0), var, S.Reals), solveset(sp.Le(e, 0), var, S.Reals)
        elif kind in ("zero_power", "origin"):
            fwd, back = solveset(Ne(e, 0), var, S.Reals), solveset(Eq(e, 0), var, S.Reals)
        elif kind == "negative_base":
            if e != var:
                return S.Reals, S.Reals
            fwd, back = S.Integers, sp.Complement(S.Reals, S.Integers)
        elif kind == "real_power":
            # the base's sign splits the line; a point of `back` may still hold (an integer exponent): the
            # caller reads such a point exactly where `back` is finite (Ctx._forward_ranges)
            base = e[0]
            fwd, back = solveset(sp.Gt(base, 0), var, S.Reals), solveset(sp.Le(base, 0), var, S.Reals)
        elif kind == "binomial":
            # e = ±var + k with k an integer: an integer exactly where var is one
            k = e - var if (e - var).free_symbols == set() else e + var
            if k.free_symbols or k.is_integer is not True:
                return S.Reals, S.Reals
            fwd = sp.Intersection(solveset(sp.Ge(e, 0), var, S.Reals), S.Integers)
            back = sp.Complement(S.Reals, fwd)
        elif kind == "integer_bound":
            # e = a*var + b, a and b rational: an integer exactly on the progression (m - b)/a, m in Z
            a, b = sp.diff(e, var), e.xreplace({var: S.Zero})
            if not (a.is_Rational and a != 0 and b.is_Rational) or sp.expand(e - a * var - b) != 0:
                # any other bound: an integer-valued polynomial (n**2, n(n + 1)/2: `_integer_valued`) is an integer
                # at every integer var, and the rest is left undecided (n**2 at n = √2 too); otherwise (sqrt(n),
                # n**2/2) no point is proved to read it as an integer, so the domain keeps none and every point is
                # the convention's. Kept whole (ℝ, ℝ), a comparison on it refuted 3n² + 3 + sin(πn²) for
                # Σ_{k=n²}^{n²+2} k at a point where n² is no integer (attack on d4f round 2, A-RK-1)
                if _integer_valued(e, var):
                    return S.Integers, sp.Complement(S.Reals, S.Integers)
                return S.EmptySet, S.Reals
            t = sp.Dummy("m", integer=True)
            fwd = S.Integers if abs(a) == 1 and b.is_integer else sp.imageset(sp.Lambda(t, (t - b) / a), S.Integers)
            back = sp.Complement(S.Reals, fwd)
        else:
            return S.Reals, S.Reals
    except Exception:  # noqa: BLE001
        return S.Reals, S.Reals
    if fwd.has(sp.ConditionSet) or back.has(sp.ConditionSet):
        return S.Reals, S.Reals
    return fwd, back


# where a convention condition on the operand u may fail (`convention_split`'s `back`), by kind; an integer exponent
# or bound and a binomial argument fail between the integers, on every piece of positive length (a Sum's range on the
# variable comes with its integer bound)
_MAY_FAIL = {"odd_root": lambda u: sp.Lt(u, 0), "mod_divisor": lambda u: sp.Le(u, 0), "zero_power": lambda u: Eq(u, 0),
             "origin": lambda u: Eq(u, 0), "real_power": lambda u: sp.Le(u[0], 0)}


def convention_null_on(c, var, region) -> bool:
    """Does the convention condition `c` on `var` (`is_convention`) fail, or stay undecided, at finitely many points of
    `region` (an integral's [a, b]) at most, for certain (the set exact, sandbox.exactsets)? An integral does not read
    its integrand on a finite set, where it is an improper integral (the isolated points of `calculus.
    integrand_undefined_on_a_subinterval`): ∫_0^1 x**x dx, ∫_0^1 x**sqrt(2) dx and ∫_{-1}^{1} x**0 dx are one number
    whatever 0**0 and 0**sqrt(2) are, and the wrong claim 100 for the first was UNKNOWN (merge of d4b round 10 with d4c
    round 4). A piece of positive length where the convention fails (x**x on (-1, 0)) is no null set: the integral
    has two readings there. The operand's own poles are its definedness conditions, not this one's."""
    st = c.args[1] if isinstance(c, sp.Contains) else None
    fails = _MAY_FAIL.get(st.kind) if isinstance(st, Convention) else None
    if fails is None:
        return False
    try:
        pts = exact_solveset(fails(c.args[0]), var, region)
    except Exception:  # noqa: BLE001 - a set not found exactly proves nothing
        return False
    return isinstance(pts, (sp.FiniteSet, type(S.EmptySet)))


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
        _BINDER_STATE.cut = True                    # this result depends on the budget: not kept
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


def finite_points(region, limit: int = 400):
    """`region` as a FiniteSet when it is one of at most `limit` points (a FiniteSet, or a finite Range: the
    integers -3 <= x <= -1 are Range(-3, 0)), else None."""
    if isinstance(region, sp.FiniteSet):
        return region if len(region) <= limit else None
    if isinstance(region, sp.Range):
        try:
            if region.is_finite_set is True and int(region.size) <= limit:
                return sp.FiniteSet(*region)
        except (TypeError, ValueError):
            return None
    return None


def _violations(c, d, region):
    """Where in `region` the condition `c` on `d` fails, computed in the sandbox under a time limit;
    None when that is not known exactly (solveset over a Range of a transcendental condition did not
    return, review of 30 Sep 2026)."""
    if not _spend(_SOLVE_COST):
        return None
    if isinstance(c, sp.Contains) and isinstance(c.args[1], Convention):
        # where the value is a convention over the region (C(n, k) with k past n): the binder is
        # then undecided, never undefined (_range_conditions reads only a failing term as undefined)
        e, kind = c.args[0], c.args[1].kind
        if kind == "integer_bound":
            # an inner bound on an outer index: over integers an integer-valued polynomial is an integer
            return S.EmptySet if region.is_subset(S.Integers) is True and _integer_valued(e, d) else None
        if kind == "binomial":
            # over integers an argument ±d + k (k an integer) is an integer: only its sign is asked
            k = e - d if (e - d).free_symbols == set() else e + d
            if k.free_symbols or k.is_integer is not True or region.is_subset(S.Integers) is not True:
                return None
            bad = sp.Lt(e, 0)
        elif kind == "negative_base":
            # an exponent that is an integer at every index (k, 2k + 1 over a Range): no convention point
            if region.is_subset(S.Integers) is True and _integer_valued(e, d):
                return S.EmptySet
            if e != d:
                return None
            out = sp.Complement(region, S.Integers)
            return None if isinstance(out, (sp.Complement, sp.ConditionSet)) else out
        elif kind == "real_power":
            # x**x: each point of a finite region read exactly (an integer exponent of a nonzero base holds);
            # elsewhere the base's sign (RK-1)
            pts = finite_points(region)
            if pts is not None:
                return sp.FiniteSet(*[q for q in pts.args if relation_holds_at(c, d, q) is not True])
            bad = sp.Le(e[0], 0)
        else:
            bad = {"odd_root": sp.Lt(e, 0), "zero_power": Eq(e, 0), "mod_divisor": sp.Le(e, 0),
                   "origin": Eq(e, 0)}.get(kind)
        if bad is None:
            return None
        r = sb_run("mathverify.sandbox.ops:solveset_in", bad, d, region, timeout=_SOLVE_TIMEOUT)
        if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
            return None
        return r.value
    if isinstance(c, sp.Contains):
        # a factorial, binomial or gcd argument's set: the argument's values over the region lie in it
        # (1/(k - 1)! from k = 1 was undecided: Not(Contains) is no relation solveset takes)
        try:
            img = region if c.args[0] == d else sp.imageset(sp.Lambda(d, c.args[0]), region)
            inside = img.is_subset(c.args[1])
        except Exception:  # noqa: BLE001
            inside = None
        if inside is True:
            return S.EmptySet
        if c.args[0] == d:
            try:
                out = sp.Complement(region, c.args[1])
            except Exception:  # noqa: BLE001
                return None
            return None if isinstance(out, (sp.Complement, sp.ConditionSet)) else out
        # over integers a polynomial in d with integer coefficients (x - 2, 2x - 3) is an integer: only its
        # sign is asked. (x - 2)! over the positive integers fails at x = 1 alone, and its limit at oo reads
        # only the tail (G14)
        e, s = c.args
        if s in (S.Naturals0, S.Naturals, S.Integers) and region.is_subset(S.Integers) is True \
                and _integer_valued(e, d):
            if s == S.Integers:
                return S.EmptySet
            bad = sp.Lt(e, 0 if s == S.Naturals0 else 1)
            r = sb_run("mathverify.sandbox.ops:solveset_in", bad, d, region, timeout=_SOLVE_TIMEOUT)
            if r.ok and isinstance(r.value, sp.Set) and not r.value.has(sp.ConditionSet):
                return r.value
        return None
    bad = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else sp.Not(c)
    # solved for a variable with the facts of the region (an index is an integer, nonnegative on
    # [0, oo)): factorial(k) != 0 was left a ConditionSet over Range(0, oo) and the exponential
    # series undecided. The conditions themselves are read on the plain variable (with an integer
    # one, 1/sin(pi*k) != 0 would already be false and dropped as naming no variable).
    facts = {}
    if region.is_subset(S.Integers) is True:
        facts["integer"] = True
        if region.inf.is_positive is True:
            facts["positive"] = True                # (k - 1)! from k = 1: k - 1 is nonnegative
        elif region.inf.is_nonnegative is True:
            facts["nonnegative"] = True
    elif region.is_subset(S.Reals) is True:
        facts["real"] = True
    if facts:
        d2 = sp.Dummy(d.name, **facts)
        bad = bad.xreplace({d: d2})
    else:
        d2 = d
    if bad is sp.false:
        return S.EmptySet
    if bad is sp.true:
        return region
    r = sb_run("mathverify.sandbox.ops:solveset_in", bad, d2, region, timeout=_SOLVE_TIMEOUT)
    if not r.ok or not isinstance(r.value, sp.Set) or r.value.has(sp.ConditionSet):
        return None
    return r.value


def _integer_valued(e, d) -> bool:
    """Is `e` a polynomial in `d` alone, an integer at every integer `d`? With rational coefficients it is exactly when
    it is one at deg + 1 consecutive integers (its coefficients in the binomial basis are integers): k*(k + 1)/2 is,
    and (-1)**(k*(k + 1)/2) was read as a convention (attack on d4e round 3, D4E3-RK-4)."""
    if e.free_symbols != {d}:
        return False
    try:
        P = sp.Poly(e, d)
        if not all(a.is_rational is True for a in P.all_coeffs()):
            return False
        return all(P.eval(i).is_integer is True for i in range(P.degree() + 1))
    except Exception:  # noqa: BLE001 - not a polynomial in d
        return False


def _undefined_at(body, index_values: dict, var) -> list[Any] | None:
    """The term of a Sum/Product at concrete index values, read as written: the conditions of a binder
    whose term is undefined there (`_undefined_sum`) when one of its conditions fails, None otherwise.
    Only this makes a sum undefined: a condition read on the symbolic body may be merely sufficient (a
    real power of a symbolic exponent asks base > 0, and (-1)**1 is defined), and turned into `false` it
    made x + Σ_{k=1}^{3} (-k)**k = 0 "defined nowhere" and its empty solution set certified (review of
    30 Sep 2026)."""
    with sp.evaluate(False):
        term = body.xreplace(index_values)
    conds = definedness_conditions(term, var)
    return _undefined_sum(conds) if any(c is sp.false for c in conds) else None


def _undefined_sum(term_conds) -> list[Any]:
    """The conditions of a Sum/Product with a term undefined at some index: `false`, and NO_VALUE when the
    term has a closed operation with no value there (Σ_{k=1}^{4} 1/(k - 3)! is 2 under 1/Γ: not "defined
    nowhere" either, CAP-F1)."""
    return [sp.false] + ([NO_VALUE] if any(is_no_value(c) for c in term_conds) else [])


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


def _range_span_conditions(bounds, idx) -> list[Any]:
    """The range of a Sum/Product as written, for each (lo, hi): hi - lo + 1 >= 0 and, for finite
    bounds, hi - lo an integer. hi = lo - 1 is the empty sum (0) or product (1), as
    `normalize.parse._refuse_reversed_ranges` and `series_sum` read it; below that SymPy's Karr
    convention gives a value the curriculum does not have (Σ_{k=1}^{-2} k = 1, Π_{k=3}^{0} k = 1/2), and
    bounds not an integer apart step from the lower one (Σ_{k=1}^{7/2} k = 63/8). The parse does not
    read such a range written with numbers; a symbolic bound took the value of its given: Σ_{k=1}^{n} k
    with n = -2 was 1 and Σ_{k=1}^{n/2} k with n = 7 was 63/8, CORRECT (V16, 30 Sep 2026). Open on the
    problem's symbols, the conditions drop such a value like any undefined point. A range reversed or
    not an integer apart for certain (an outer index put into an inner bound: Σ_{k=1}^{5} Σ_{j=k}^{2} 1
    at k = 4) is DEFINEDNESS_UNDECIDED, not `false`: its numeric twin is not read, and `false` would
    read the expression as defined nowhere (an empty solution set certified).

    Below the empty range the value is a convention, not undefined: hi - lo + 1 >= 0 is written as
    `Contains(hi - lo + 1, FORWARD_SPANS)`, which a reversed point leaves undecided (see ForwardSpans).
    The domain of a variable still keeps only the forward points (`Ctx.domain_for`: an expression is
    compared where its value is no convention), and a candidate, root or solution where the range runs
    backwards is neither kept nor dropped (`Ctx.reversed_region`, DECISIONS §80).

    SymPy writes a nested sum as one binder, innermost limit first, whose inner bounds may name an
    outer index (Sum(1, (j, k, 2), (k, 1, 5))): such a condition is decided over that index's values
    (_outer_index_conditions); left open, it named the bound index as a problem symbol."""
    out: list[Any] = []
    for i, (lo, hi) in enumerate(bounds):
        try:
            with sp.evaluate(True):
                conds = _one_range_conditions(lo, hi)
                if conds is not None:
                    conds = _outer_index_conditions(conds, i, bounds, idx)
        except Exception:  # noqa: BLE001 - a range no relation reads is not proved to run forward
            conds = None
        if conds is None:
            return [DEFINEDNESS_UNDECIDED]
        out += [c for c in conds if c not in out]
    return out


def _outer_index_conditions(conds, i, bounds, idx) -> list[Any] | None:
    """The range conditions of limit `i` with the outer indices they name decided over those indices'
    values: at each point when the outer bounds are integers (at most _POINTS points), over the index
    range otherwise (one index, a condition on it alone); None when that is not decided, or when one
    fails at some point (the inner range is reversed there for certain)."""
    out: list[Any] = []
    for c in conds:
        named = c.free_symbols & set(idx)
        if not named:
            out.append(c)
            continue
        pos = sorted(idx.index(v) for v in named)
        if pos[0] <= i:
            return None                             # a bound naming its own or an inner index
        if all(bounds[p][0].is_Integer and bounds[p][1].is_Integer for p in pos):
            ranges = [range(int(bounds[p][0]), int(bounds[p][1]) + 1) for p in pos]
            count = 1
            for r in ranges:
                count *= len(r)
            if count > _POINTS or not _spend(count):
                return None
            for point in itertools.product(*ranges):
                v = c.xreplace({idx[p]: sp.Integer(x) for p, x in zip(pos, point)})
                if v is sp.true:
                    continue
                if v is sp.false or not v.free_symbols or v.free_symbols & set(idx):
                    return None
                if v not in out:
                    out.append(v)
            continue
        if len(pos) != 1 or c.free_symbols != named:
            return None
        lo, hi = bounds[pos[0]]
        region = (sp.Range(int(lo), oo) if lo.is_Integer else sp.Range(-oo, int(hi) + 1) if hi.is_Integer
                  else S.Integers)
        # a superset of the index values: when the outer range is reversed its own condition fails
        bad = _violations(c, idx[pos[0]], region)
        if bad is None or bad.is_empty is not True:
            return None
    return out


def _proved_integer(b) -> bool | None:
    """`b.is_integer`, with a closed bound SymPy leaves undecided proved an integer exactly when it is one
    (`certified_integer`): ln 8/ln 2 and log_3 3^4 are 3 and 4, and Σ_{k=1}^{ln 8/ln 2} k = 6 was UNKNOWN (attack on
    d4f round 2, RK-3; the value reading folds log(27, 3) to 3, not these). Never proved not one here."""
    r = b.is_integer
    if r is None and not b.free_symbols and certified_integer(_evaluated(b))[0] is True:
        return True
    return r


def _one_range_conditions(lo, hi) -> list[Any] | None:
    """The open conditions of one range (see _range_span_conditions); None when it is reversed, not an
    integer apart or not on the integers for certain, or not read.

    The finite bounds themselves are integers: bounds an integer apart that are not (Σ_{k=1/2}^{5/2} k)
    step from the lower one in SymPy (1/2 + 3/2 + 5/2 = 9/2) and run over the integers between them in
    the index reading (1 + 2 = 3). The value is a convention, and with a = 1/2 the sum Σ_{k=a}^{a+2} k
    was certified 9/2 and 3 refuted (fourth audit, TAN-10/C1). A bound not proved an integer, or a gap, is
    held to the integers as a convention: Contains(n, INTEGER_BOUND) on one of them (the gap ties the other),
    which holds at an integer and is undecided elsewhere, never false. As Contains(n, Z) it dropped the
    non-integer points like undefined ones (review of d4f, YO-3, RK-F1). A closed one (1/2 written in nested
    roots) stays standing: undecided, and a step refuted with SymPy's stepping value of it refutes nothing
    (review of d4f, YO-1)."""
    span = hi - lo + 1
    if span.has(sp.nan, sp.zoo) or span.is_extended_real is False:
        return None
    conds = []
    if span.is_extended_nonnegative is not True:
        if span.is_extended_negative is True:
            return None
        conds.append(sp.Contains(span, FORWARD_SPANS))
    finite = [b for b in (lo, hi) if not b.has(oo, -oo)]
    if len(finite) == 2:
        gap = hi - lo
        if gap.is_integer is False:
            return None
        if _proved_integer(gap) is not True:
            # on the bound itself when the other one is an integer
            conds.append(sp.Contains(hi if lo.is_Integer else lo if hi.is_Integer else gap, INTEGER_BOUND))
    whole = [_proved_integer(b) for b in finite]
    if False in whole:
        return None
    if finite and True not in whole:
        b = next((b for b in finite if isinstance(b, sp.Symbol)), finite[0])
        conds.append(sp.Contains(b, INTEGER_BOUND))
    out = []
    for c in conds:
        if c is sp.true:
            continue
        if c is sp.false or (not c.free_symbols and not is_integer_bound(c)):
            return None
        if c not in out:
            out.append(c)
    return out


def _range_conditions(n, var) -> list[Any]:
    """Sum/Product: the term, as written, at every index. A finite range of at most _POINTS indices is
    checked index by index (the term's own conditions there: a failing one makes the sum undefined,
    those on the problem's symbols are kept, Σ_{k=1}^{3} 1/(k - x) needs x != 1, 2, 3); a longer or
    infinite range, or a symbolic bound, by solving each condition over the index range, and a
    violation found there makes the sum undefined only where the term itself is undefined at it.
    Before 30 Sep 2026 these conditions were dropped (they name the index, not the problem's
    variables) and Σ_{k=-1}^{1000} k/k = 1002, Σ_{k<=0} 2^k k/k = 2 and Σ_{k=-1}^{n} k/k with n = 3
    were certified; the first V14 checked only finite sums of at most 200 terms.

    The range itself comes first: see _range_span_conditions."""
    limits = n.limits
    if any(len(lim) != 3 for lim in limits):
        return [DEFINEDNESS_UNDECIDED]
    bounds = [(_evaluated(lim[1]), _evaluated(lim[2])) for lim in limits]
    idx = [lim[0] for lim in limits]
    spans = _range_span_conditions(bounds, idx)
    if any(is_undecided(c) for c in spans):
        return spans
    named, plain = _named_conditions(n.function, idx, var)
    if not named:
        return spans
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
                term_conds = definedness_conditions(term, var)
                if any(c is sp.false for c in term_conds):
                    return _undefined_sum(term_conds)
                out += [c for c in term_conds if c not in out]
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
            if points and _spend(len(points)):
                for i in points:
                    failed = _undefined_at(n.function, {idx[0]: sp.Integer(i)}, var)
                    if failed is not None:
                        return failed
        return [DEFINEDNESS_UNDECIDED]
    return spans


def _declared_span(v):
    """(lowest, highest) value a bound may take: itself when it is a real number, from its sign when
    it is a declared symbol; None otherwise."""
    if v.is_number:
        return (v, v) if v.is_real or v in (oo, -oo) else None
    if v.is_positive or v.is_nonnegative:
        return (S.Zero, oo)
    if v.is_negative or v.is_nonpositive:
        return (-oo, S.Zero)
    return None


def _reachable(a, b):
    """The points [a, b] can cover when a bound is symbolic: the hull of the values the bounds may
    take, open at 0 when only a strict sign reaches it (x > 0 never makes 0 a bound); R when a
    bound has no declared sign. An infinite bound reaches out to its end: it counted as no point at all,
    so ∫_{-oo}^{x} dt/t with x > 0 was read as running inside (0, oo), its point 0 never reached, and
    the derivative 1/x of that integral, which exists for no x, was certified (fourth audit TAN-07)."""
    parts = []
    ends = set()
    for v in (a, b):
        if v in (oo, -oo):
            ends.add(v)
        elif v.is_number:
            if not v.is_real:
                return S.Reals
            parts.append(sp.FiniteSet(v))
        elif v.is_positive:
            parts.append(Interval.open(0, oo))
        elif v.is_nonnegative:
            parts.append(Interval(0, oo))
        elif v.is_negative:
            parts.append(Interval.open(-oo, 0))
        elif v.is_nonpositive:
            parts.append(Interval(-oo, 0))
        else:
            return S.Reals
    u = sp.Union(*parts)
    lo = -oo if -oo in ends else u.inf
    hi = oo if oo in ends else u.sup
    return Interval(lo, hi, left_open=u.contains(lo) is not sp.true, right_open=u.contains(hi) is not sp.true)


def _bounded_limit(lim) -> bool:
    """Is `lim`, SymPy's limit of a nonnegative quantity, a finite real number, or an AccumBounds whose upper
    end is one (|cos t|/(1 + t**2)·t**2 oscillates in [0, 1] at oo: bounded all the same)?"""
    if isinstance(lim, sp.AccumBounds):
        return lim.max.is_number and lim.max.is_finite is True and lim.max.is_real is True
    return isinstance(lim, sp.Expr) and lim.is_number and lim.is_finite is True and lim.is_real is True \
        and not lim.has(sp.AccumBounds)


# periodic functions: a SymPy limit of an expression holding one of them at an argument without a finite limit is no
# proof (lim t**(3/2)/(1 + t**2*cos(t)**2) at oo is "0", the values at (n + 1/2)*pi grow without bound), and jumps
_PERIODIC = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)
_JUMPS = (sp.sign, sp.frac, sp.Heaviside, sp.floor, sp.ceiling, sp.Mod, sp.Piecewise, sp.Max, sp.Min)


class _NoBound(Exception):
    pass


class _Majorant:
    """Bounds near a point of the variable s (a positive Dummy: s -> oo, or s -> 0+): `upper(e)` is an M >= |e|,
    `ub(e)` >= e and `lb(e)` <= e (e real), each `exact` (no periodic function at an argument without a finite
    limit there, no jump, no symbol but s), so that SymPy's limit of it can be read. An exact part is kept as it
    is; a periodic factor is bounded by its range (|sin| <= 1), any other symbol p by |p| <= P (a positive Dummy:
    the bound holds for every value of p) and by its declared sign on the safe side only (lb(a) = 0 for a >= 0), a
    denominator by a positive lower bound (1 + s**2*cos(s)**2 >= 1). A symbol of declared sign is no exact part:
    SymPy's limit of 1/((x - 1)**2*s**2 + 1) is read for a generic positive x, and ∫_1^oo dt/((x - 1)**2*t**2 + 1),
    which diverges at x = 1, was proved to converge (attack on d4e round 3, D4E3-YO-4 and RK-2). An exponential
    whose exponent is c*r(s), c of proved sign (c < 0 for every value) and r free of every other symbol with
    r -> oo, is bounded per value: e**(c*r) <= (N/(e*|c|))**N * r**(-N) (e**(-a*t) with a > 0 declared, R7).
    The parameters are left in s-free factors only (`parameter_free_terms` reads them). Raises _NoBound when no
    bound is found."""

    _N = 6                         # the power of r an exponential of proved negative rate is bounded by

    def __init__(self, s, point):
        self.s, self.point = s, point
        self.unsigned: dict = {}
        self._safe: dict = {}

    def _limit(self, e):
        return sp.limit(e, self.s, 0, "+") if self.point == 0 else sp.limit(e, self.s, oo)

    def exact(self, e) -> bool:
        if e in self._safe:
            return self._safe[e]
        ok = not (e.free_symbols - {self.s})
        if ok:
            for n in sp.preorder_traversal(e):
                if self.s not in n.free_symbols:
                    continue
                if isinstance(n, _JUMPS):
                    ok = False
                    break
                if isinstance(n, _PERIODIC):
                    arg = n.args[0]
                    if not self.exact(arg):
                        ok = False
                        break
                    try:
                        lim = self._limit(arg)
                    except Exception:  # noqa: BLE001
                        lim = None
                    if not (isinstance(lim, sp.Expr) and lim.is_number and lim.is_finite is True
                            and lim.is_real is True and not lim.has(sp.AccumBounds)):
                        ok = False
                        break
        self._safe[e] = ok
        return ok

    def _constant(self, e) -> bool:
        """Is e free of s, built of other symbols, and finite for every value they may take (by their assumptions)?"""
        return self.s not in e.free_symbols and bool(e.free_symbols) and e.is_finite is True and e.is_real is True

    def sym_bound(self, sym):
        if sym.is_real is not True:
            raise _NoBound(sym)
        if sym not in self.unsigned:
            self.unsigned[sym] = sp.Dummy(f"abs_{sym}", positive=True)
        return self.unsigned[sym]

    def _decaying_exponential(self, arg):
        """(the per-value bound of the factors c*r of the exponent `arg`, c < 0 for every value of its symbols and r
        free of them with r -> oo at the point; the rest of the exponent)."""
        bound, rest = S.One, []
        for term in sp.Add.make_args(sp.expand(arg)):
            c, r = term.as_independent(self.s, as_Add=False)
            if c.free_symbols and self._constant(c) and c.is_negative is True and r.has(self.s) \
                    and not (r.free_symbols - {self.s}) and self.exact(r):
                try:
                    lim = self._limit(r)
                except Exception:  # noqa: BLE001
                    lim = None
                if lim is oo:
                    bound *= (self._N / (sp.E * (-c))) ** self._N * r ** (-self._N)
                    continue
            rest.append(term)
        return bound, sp.Add(*rest)

    def upper(self, e):
        """M >= |e|."""
        if self.exact(e):
            return sp.Abs(e)
        if self._constant(e):
            return sp.Abs(e)                            # a finite number for each value of its symbols
        if isinstance(e, sp.Symbol):
            return self.sym_bound(e)
        if isinstance(e, sp.Add):
            return sp.Add(*[self.upper(a) for a in e.args])
        if isinstance(e, sp.Mul):
            return sp.Mul(*[self.upper(a) for a in e.args])
        if isinstance(e, sp.Abs):
            return self.upper(e.args[0])
        if isinstance(e, (sp.sin, sp.cos, sp.sign, sp.Heaviside, sp.frac)):
            if e.args[0].is_real is not True:
                raise _NoBound(e)
            return S.One
        if isinstance(e, (sp.floor, sp.ceiling)):
            return self.upper(e.args[0]) + 1
        if isinstance(e, sp.exp):
            bound, rest = self._decaying_exponential(e.args[0])
            return bound * sp.exp(self.ub(rest))
        if isinstance(e, sp.Pow):
            b, x = e.args
            if not (x.is_number and x.is_real is True):
                raise _NoBound(e)
            if x.is_positive:
                return self.upper(b) ** x
            return self.lower_abs(b) ** x
        raise _NoBound(e)

    def lower_abs(self, e):
        """L with 0 < L <= |e| near the point."""
        lo = self.lb(e)
        if self._positive(lo):
            return lo
        hi = self.ub(e)
        if self._positive(-hi):
            return -hi
        for v in (lo, -hi):
            floor = self._polynomial_floor(v)
            if floor is not None:
                return floor
        raise _NoBound(e)

    def _polynomial_floor(self, v):
        """(c/2)*s**k with v >= (c/2)*s**k near the point for EVERY value of v's other symbols: v a polynomial in s
        whose leading term (at oo; its lowest one at 0+) is c*s**k, c a positive number, the others' coefficients
        s-free (a bound P of |x|): s**2 - P**2 >= s**2/2 from some s on, whatever P is. None otherwise."""
        if self.s not in v.free_symbols:
            return None
        try:
            poly = sp.Poly(v, self.s)
        except Exception:  # noqa: BLE001 - not a polynomial in s
            return None
        terms = poly.terms()
        if not terms or any(self.s in c.free_symbols for _, c in terms):
            return None
        (k,), c = max(terms) if self.point is oo else min(terms)
        if certified_sign(c) != 1:
            return None
        return c / 2 * self.s ** k

    def _positive(self, e) -> bool:
        if not self.exact(e):
            return False
        if e.is_positive is True:
            return True
        try:
            lim = self._limit(e)
        except Exception:  # noqa: BLE001
            return False
        return lim is oo or (isinstance(lim, sp.Expr) and lim.is_number and lim.is_real is True
                             and not lim.has(sp.AccumBounds) and certified_sign(lim) == 1)

    def _nonnegative(self, e) -> bool:
        """e >= 0 by its form: an even power, an Abs, a product of such, an exact part SymPy calls nonnegative, an
        s-free part nonnegative for every value of its symbols (a declared a > 0)."""
        if isinstance(e, sp.Abs):
            return True
        if isinstance(e, sp.Pow) and e.args[1].is_number and e.args[1].is_even is True:
            return True
        if isinstance(e, sp.Mul):
            return all(self._nonnegative(a) for a in e.args)
        if self.s not in e.free_symbols and e.is_nonnegative is True:
            return True
        return self.exact(e) and e.is_nonnegative is True

    def ub(self, e):
        """U >= e (e real)."""
        if self.exact(e):
            return e
        if self.s not in e.free_symbols and e.is_nonpositive is True:
            return S.Zero                               # a declared a <= 0: its sign, never its value
        if isinstance(e, sp.Add):
            return sp.Add(*[self.ub(a) for a in e.args])
        if isinstance(e, (sp.sin, sp.cos)):
            return S.One
        if isinstance(e, sp.Mul):
            c, rest = e.as_coeff_Mul()
            if c != 1 and c.is_real is True and c.is_zero is False:
                return c * (self.ub(rest) if c.is_positive else self.lb(rest))
        return self.upper(e)

    def lb(self, e):
        """L <= e (e real)."""
        if self.exact(e):
            return e
        if isinstance(e, sp.Add):
            return sp.Add(*[self.lb(a) for a in e.args])
        if isinstance(e, (sp.sin, sp.cos)):
            return -S.One
        if isinstance(e, sp.Mul):
            c, rest = e.as_coeff_Mul()
            if c != 1 and c.is_real is True and c.is_zero is False:
                return c * (self.lb(rest) if c.is_positive else self.ub(rest))
            if all(self._nonnegative(a) for a in e.args):
                return sp.Mul(*[self.lb(a) for a in e.args])
        if self._nonnegative(e):
            return S.Zero
        return -self.upper(e)


def majorant(g, t, point, side=None):
    """(M, s): |g(t)| <= M(s) near `point` (oo or -oo; a finite point c from `side`), t = s (oo), -s (-oo), c + s or
    c - s with s a positive Dummy (s -> oo, or s -> 0+), M free of every periodic function at an argument without a
    finite limit there and of jumps, its other symbols in s-free factors only (`_Majorant`); (None, s) when no
    such M is found. A SymPy limit of M's parameter-free terms is read as a proof (`parameter_free_terms`); one of g
    is not: lim t**(3/2)/(1 + t**2*sin(t)**2) at oo is "0", and the divergent ∫_0^oo dt/(1 + t**2*sin(t)**2) was
    proved convergent (attack on d4e round 2, YO-1)."""
    s = sp.Dummy("s", positive=True)
    if point in (oo, -oo):
        gs, at = g.xreplace({t: s if point == oo else -s}), oo
    else:
        gs, at = g.xreplace({t: point + s if side == "+" else point - s}), S.Zero
    try:
        return _Majorant(s, at).upper(gs), s
    except _NoBound:
        return None, s
    except Exception:  # noqa: BLE001 - a bound SymPy cannot form is none
        return None, s


def parameter_free_terms(M, s) -> list | None:
    """The terms m_i of M = Σ K_i*m_i with each m_i free of every symbol but s and each K_i free of s; None when M has
    no such form. A majorant's K_i is finite for every value of its symbols by construction (`_Majorant`: an s-free
    part is kept only when finite, a bound P of |p| and the exponential's constant are). Then M is bounded near a
    point, for EVERY value of the parameters, when each m_i is: a limit is taken of the m_i alone, never one with a
    parameter in it, which SymPy reads for a generic value (D4E3-YO-4: lim s**(3/2)/((x - 1)**2*s**2 + 1) is 0, and
    at x = 1 the integrand is 1)."""
    try:
        E = sp.expand(M)
    except Exception:  # noqa: BLE001
        return None
    out = []
    for term in sp.Add.make_args(E):
        K, m = term.as_independent(s, as_Add=False)
        if m.free_symbols - {s}:
            return None
        out.append(m)
    return out


def _without_constant_factor(g, t):
    """g with its t-free factor dropped when that factor is finite for every value of its symbols: the integral of
    K*g0 converges where that of g0 does (a*sin(t)/t, a > 0: K = a, round 4 RK-7)."""
    K, g0 = g.as_independent(t, as_Add=False)
    if K != 1 and K.is_finite is True and K.is_real is True and g0.has(t):
        return g0
    return g


def decays_at(g, t, end) -> bool:
    """Worker: is |g(t)| <= C/|t|**p near `end` (±oo) for some p > 1, for EVERY value of g's other symbols? Then
    ∫ g converges absolutely at that end. Read off a majorant M of |g| (`majorant`: periodic factors bounded by their
    range, another symbol by its absolute value and its sign on the safe side, so the task's own variable may stand
    in the integrand: e^(-t)*(x + t), e^(-t)*cos(x*t); round 3 RK-4), split into parameter-free terms
    (`parameter_free_terms`), each with a bounded limit of s**p * m (p = 2, 3/2, 11/10) or the exponent q of its
    decay, q = lim -log m/log s > 1 (m = s**(-q + o(1)): t**(-21/20); review of d4e, R7), or, not absolutely, by
    Dirichlet's test (`_dirichlet_test`: sin(t)/t). A SymPy limit of an oscillating g is no proof (round 3, YO-1),
    nor one with a parameter in it (round 4, YO-4). False when none is found (a divergent integral, or one these
    tests cannot prove: sin(t**2), 1/(1 + t**4*sin(t)**2), 1/((x - 1)**2*t**2 + 1))."""
    g = _without_constant_factor(g, t)
    m, s = majorant(g, t, end)
    terms = parameter_free_terms(m, s) if m is not None else None
    if terms is not None and all(_term_decays(mi, s) for mi in terms):
        return True
    return _dirichlet_test(g, t, end)


def _term_decays(m, s) -> bool:
    """Is |m(s)| <= C/s**p for large s, some p > 1 (m free of every symbol but s)?"""
    for p in (S(2), sp.Rational(3, 2), sp.Rational(11, 10)):
        if _bounded_limit(sp.limit(s ** p * m, s, oo)):
            return True
    q = sp.limit(-sp.log(m) / sp.log(s), s, oo)
    if q is oo:
        return True
    return isinstance(q, sp.Expr) and q.is_number and q.is_real is True and certified_sign(q - 1) == 1


def _dirichlet_test(g, t, end) -> bool:
    """Dirichlet's test at `end` (±oo): g = sin(a*t + b) * h(t) (or cos), a != 0 a number, h free of every function,
    real out there, tending to 0 and eventually monotone. Then ∫ g converges there, not absolutely: sin(t)/t,
    cos(t)/sqrt(t). Read as absolute convergence only, the Dirichlet integral was undefined as written and a true step
    about it went unchecked (d4c, measured after the attack on d4e, YO-2). sin(t)**2/t is no such product. With h
    free of every other symbol (its t-free finite factor dropped first: a*sin(t)/t), h'/h a rational function of t
    has one sign from some point on (t**q times a rational function). With other symbols (t = ±s, s > 0), for EVERY
    value of them: h >= 0 (or <= 0) and h nonincreasing in s (nondecreasing) for every s > 0 by their assumptions,
    and |h| <= K*m(s) with m free of them tending to 0 (`parameter_free_terms`): sin(t)/(t + a) with a > 0
    (1/(s + a) <= 1/s, round 4 RK-7). SymPy's limit of t/(x**2*t**2 + 1) is 0 for a generic x, not at x = 0, where
    ∫ t*sin(t) diverges (attack on d4e round 3, D4E3-YO-1)."""
    for osc in g.atoms(sp.sin, sp.cos):
        arg = osc.args[0]
        k = sp.diff(arg, t)
        if not (k.is_number and k.is_real is True and k.is_zero is False and sp.diff(arg, t, 2) == 0):
            continue
        h = _without_constant_factor(sp.simplify(g / osc), t)
        if t not in h.free_symbols or h.atoms(sp.Function):
            continue
        side = sp.Dummy("s", positive=True)
        hs = h.subs(t, side if end == oo else -side)
        if hs.is_real is not True:
            continue
        if h.free_symbols == {t}:
            r = sp.simplify(sp.diff(h, t) / h)
            if not r.is_rational_function(t):
                continue
            if sp.limit(h, t, end) == 0:
                return True
            continue
        sgn = 1 if hs.is_nonnegative is True else -1 if hs.is_nonpositive is True else 0
        if not sgn or sp.diff(sgn * hs, side).is_nonpositive is not True:
            continue
        try:
            M = _Majorant(side, oo).upper(sgn * hs)
        except Exception:  # noqa: BLE001 - _NoBound, or a bound SymPy cannot form
            continue
        terms = parameter_free_terms(M, side)
        if terms is not None and all(sp.limit(mi, side, oo) == 0 for mi in terms):
            return True
    return False


def integrable_near(g, t, c, side) -> bool:
    """Worker: is |g(t)| <= C/|t - c|**p on the `side` ('+', '-') of the finite point c for some p < 1, for EVERY
    value of g's other symbols, read off the parameter-free terms of a majorant M of |g| (`majorant`, t = c ± s,
    `parameter_free_terms`), each with a bounded limit of s**p * m (p = 0, 1/2, 2/3, 9/10)? Then ∫ g converges
    absolutely there: 1/sqrt(t) and log(t) at 0 do, 1/t and 1/(t - 1/2) do not (attack on d4e, YO-2), and a SymPy
    limit of 1/(t**2 + cos(1/t)**2) is no proof (round 3, YO-1)."""
    g = _without_constant_factor(g, t)
    m, s = majorant(g, t, c, side)
    terms = parameter_free_terms(m, s) if m is not None else None
    if terms is None:
        return False
    return all(any(_bounded_limit(sp.limit(s ** p * mi, s, 0, "+"))
                   for p in (S(0), S.Half, sp.Rational(2, 3), sp.Rational(9, 10))) for mi in terms)


def _integrand_on(body, x, d):
    """The integrand on a real dummy for its bound variable, evaluated; None when it holds an IR function's marker.
    Another symbol is read for all its values by `majorant` (the task's variable in ∫_0^oo e^(-t)*(x + t), round 3
    RK-4; one not declared real has no bound) and by `_dirichlet_test` (sin(t)/(t + a), a > 0)."""
    t = sp.Dummy(d.name, real=True)
    try:
        with sp.evaluate(False):
            g = body.xreplace({x: t})
        g = _evaluated(g)
    except Exception:  # noqa: BLE001
        return None, t
    if not isinstance(g, sp.Expr) or any(type(m).__name__ == "written_domain" for m in sp.preorder_traversal(g)):
        return None, t
    return g, t


def _converges_at(body, x, d, end) -> bool:
    """Is the integral of `body` (as written, in its bound variable `x`) proved to converge at `end` (±oo)? A
    parameter of declared sign is read with it (e^(-a*t), a > 0)."""
    if not _spend(_SOLVE_COST):
        return False
    g, t = _integrand_on(body, x, d)
    if g is None:
        return False
    if t not in g.free_symbols:
        return g.is_zero is True                     # a constant converges at an infinite end only if 0
    r = sb_run("mathverify.certify.domain:decays_at", g, t, end, timeout=_SOLVE_TIMEOUT)
    return bool(r.ok and r.value is True)


def _integrable_at(body, x, d, c, side) -> bool:
    """Is the integral of `body` proved to converge at its finite point c, from `side`?"""
    if not _spend(_SOLVE_COST):
        return False
    g, t = _integrand_on(body, x, d)
    if g is None:
        return False
    r = sb_run("mathverify.certify.domain:integrable_near", g, t, c, side, timeout=_SOLVE_TIMEOUT)
    return bool(r.ok and r.value is True)


def _integral_conditions(n, var) -> list[Any]:
    """A definite integral: the integrand, as written, exists on [a, b] up to finitely many points (an
    improper point is the value's business). ∫_{-1}^{1} (√x)² dx = 0 was certified (30 Sep 2026)."""
    definite = [lim for lim in n.limits if len(lim) == 3]
    if not definite:
        return []                                   # an antiderivative: its variable is not bounded
    if len(n.limits) != 1:
        named, _ = _named_conditions(n.function, [lim[0] for lim in n.limits], var)
        improper = any(len(lim) == 3 and {_evaluated(lim[1]), _evaluated(lim[2])} & {oo, -oo}
                       and not (_evaluated(lim[1]).is_number and _evaluated(lim[2]).is_number) for lim in n.limits)
        return [DEFINEDNESS_UNDECIDED] if named or improper else []
    x, a, b = n.limits[0]
    named, plain = _named_conditions(n.function, [x], var)
    d = plain[x]
    region = S.Reals
    a, b = _evaluated(a), _evaluated(b)
    if not (a.is_number and b.is_number):
        # an infinite bound next to a symbolic one: no value is computed, and a derivative of the integral
        # is taken by the fundamental theorem, so the integral must be proved to converge at that end.
        # The derivative -1/(x + 1) of ∫_x^oo dt/(t + 1), which diverges for every x, was certified
        # (fourth audit TAN-07)
        for end in (a, b):
            if end in (oo, -oo) and not _converges_at(n.function, x, d, end):
                return [DEFINEDNESS_UNDECIDED]
        # a symbolic bound: the integral runs inside the hull of the values the bounds may take by
        # their declarations (∫_0^x √t dt and ∫_1^x ln t dt with x > 0 lie in [0, oo); read over R
        # they were undecided, review of 30 Sep 2026)
        spans = [_declared_span(v) for v in (a, b)]
        if all(sp_ is not None for sp_ in spans):
            region = Interval(min(sp_[0] for sp_ in spans), max(sp_[1] for sp_ in spans))
    if a.is_number and b.is_number:
        order = certified_sign(b - a) if not (a.has(oo, -oo) or b.has(oo, -oo)) else None
        if a.has(oo, -oo) or b.has(oo, -oo):
            region = Interval(min(a, b), max(a, b)) if a != b else S.EmptySet
        elif order in (-1, 0, 1):
            region = Interval(b, a) if order == -1 else Interval(a, b)
        else:
            return [DEFINEDNESS_UNDECIDED] if named else []
    symbolic = not (a.is_number and b.is_number)
    if not symbolic:
        # numbers for bounds: the integral exists only when it is proved to converge at an infinite end and at
        # each point between the bounds where the integrand has no value. It was "the value's business", but
        # the value is folded away first: 0*∫_1^oo dt/t + 1 = 1, ∫_1^oo dt/t - ∫_1^oo dt/t = 0 and
        # x + 0*∫_0^1 dt/(t - 1/2) with the derivative 1 were certified (attack on d4e, YO-2)
        for end in (a, b):
            if end in (oo, -oo) and not _converges_at(n.function, x, d, end):
                return [DEFINEDNESS_UNDECIDED]
    for c in named:
        bad = _violations(c, d, region)
        if bad is None or not (bad.is_empty is True or bad.is_finite_set is True):
            return [DEFINEDNESS_UNDECIDED]
        if not symbolic:
            for p_ in bad:
                sides = [s_ for s_, on in (("-", certified_sign(p_ - region.inf) == 1),
                                            ("+", certified_sign(region.sup - p_) == 1)) if on]
                if not sides or any(not _integrable_at(n.function, x, d, p_, s_) for s_ in sides):
                    return [DEFINEDNESS_UNDECIDED]
        if symbolic and bad.is_empty is not True:
            # an improper point is the value's business only when a value is computed: with a
            # symbolic bound the value is SymPy's parametric integral, and a derivative of it is
            # taken by the fundamental theorem without it. diff(∫_1^x dt/t, x) = -1 had {-1}
            # certified (∫_1^{-1} dt/t does not exist), and diff(∫_0^x dt/t, x) = 1 with x > 0 had
            # {1} (V16, 30 Sep 2026). A point the bounds may reach leaves the integral undecided.
            reach = _reachable(a, b)
            if any(reach.contains(p) is not sp.false for p in bad):
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
            # a sequence runs over the declared integers (n positive: from 1): 2**n/n! as n -> oo was
            # undecided over all the integers (review of 30 Sep 2026)
            if getattr(z, "is_integer", None):
                over = sp.Range(1, oo) if z.is_positive else sp.Range(0, oo) if z.is_nonnegative else S.Integers
            else:
                over = Interval(0, oo) if z.is_nonnegative else S.Reals
            bad = _violations(c, zd, over)
            if bad is None:
                return [DEFINEDNESS_UNDECIDED]
            if bad.is_empty is not True and (bad.sup if z0 == oo else bad.inf).is_finite is not True:
                return [DEFINEDNESS_UNDECIDED]
            continue
        sides = ("+", "-") if str(direction) == "+-" else (str(direction),)
        if sides == ("+", "-") and z0 == 0 and getattr(z, "is_nonnegative", None):
            sides = ("+",)                          # the limit over the declared domain (certify.limits)
        for side in sides:
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


def _subs_conditions(n, var, add) -> None:
    """Subs(body, v, p), at(): the body's conditions hold AT the point. Walked into, they stood on the bound
    variable, which nothing constrains, so Subs(sqrt(x - 2), x, 1)**2 = -1 and Subs(1/(x - 1), x, 1)*0 = 0
    were verified compute steps (attack on d4e, YO-3). Without a derivative in v the body is read with p
    written in for v: the same conditions as the text with the point in place. A derivative in v at p needs
    its function defined on a neighbourhood of p, read as `_limit_conditions` reads one (a condition that
    fails at p, or next to it, leaves the expression undecided, never undefined: a one-sided derivative or
    a removable gap is a convention): at(diff(sqrt(x)**2, x), x, -1) = 1 and at(diff(sqrt(x)**2, x), x, 0) = 1
    were verified."""
    from ..normalize.parse import substitute_free
    body, vs, pts = n.expr, tuple(n.variables), tuple(n.point)
    if not any(set(vs) & set(d_.variables) for d_ in body.atoms(sp.Derivative)):
        with sp.evaluate(False):
            at_point = substitute_free(body, dict(zip(vs, pts)))
        for c in definedness_conditions(at_point, var):
            add(c)
        return
    plain = {v: sp.Dummy(getattr(v, "name", "v")) for v in vs}
    with sp.evaluate(False):
        b = body.xreplace(plain)
    dummies = set(plain.values())
    for c in definedness_conditions(b, var):
        named = getattr(c, "free_symbols", set()) & dummies
        if not named:
            add(c)
            continue
        if len(vs) != 1:
            add(DEFINEDNESS_UNDECIDED)
            continue
        d, p_ = plain[vs[0]], _evaluated(pts[0])
        if not (isinstance(p_, sp.Expr) and p_.is_number and p_.is_real is True and p_.is_finite is True):
            add(DEFINEDNESS_UNDECIDED)          # a symbolic point: no neighbourhood is read
            continue
        bad = _violations(c, d, Interval.open(p_ - 1, p_ + 1))
        if bad is None:
            # not solved near p (x - cos(x) != 0, cos(x**2) != 0): a condition that holds strictly at p, of
            # operations continuous where defined, holds on a neighbourhood of it (`calculus.strict_at`, R1); the
            # compute step at(diff(1/(x - cos(x)), x), x, pi) = -1/(pi + 1)**2 was left unknown (round 3, RK-7)
            from .calculus import strict_at
            if not strict_at(c, d, p_):
                add(DEFINEDNESS_UNDECIDED)
            continue
        if bad.is_empty is True:
            continue
        try:
            left, right = sp.Intersection(bad, Interval(p_ - 1, p_)), sp.Intersection(bad, Interval(p_, p_ + 1))
            clear = (left.is_empty is True or certified_sign(p_ - left.sup) == 1) and \
                (right.is_empty is True or certified_sign(right.inf - p_) == 1)
        except Exception:  # noqa: BLE001
            clear = False
        if not clear:
            add(DEFINEDNESS_UNDECIDED)


_BINDER_CACHE: dict = {}
_BINDER_CACHE_LOCK = threading.Lock()
_BINDER_CACHE_SIZE = 512


def _piecewise_conditions(pw, var, add) -> None:
    """The written definedness of a Piecewise, branch by branch: at x the first branch whose condition holds is the
    value, so its expression must be defined there, each condition up to it too (a condition with no value stops
    the evaluation), and a point no condition covers has no value at all (SymPy's subs gives nan). Read on every
    branch alike, Piecewise((0, Eq(x, 0)), (x/|x|, Ne(x, 0))), which is sign(x), had no value at 0: the derivative
    of |x| with the value 0 at the corner was certified, the right Piecewise((2*x**2/x, Ne(x, 0)), (0, Eq(x, 0)))
    for (x**2)' refuted (attack on d4e round 3, D4E3-YO-6); and the gap 0 of Piecewise((x**2 - 1, x < 1),
    (x**2 - 1, x > 1)) was a root (D4E3-YO-7). On one symbol v the set D where it has a value is computed exactly:
    ℝ ∖ {p, ...} gives v != p, any other set Contains(v, D) (a membership: the certificates abstain on it). A
    membership of a branch (n!, an odd root) holds as before, on every branch; anything else not read exactly
    (two symbols, a periodic condition) is DEFINEDNESS_UNDECIDED."""
    from .base import Ctx
    branches = []
    for val, cond in pw.args:
        vc = definedness_conditions(val, var)
        cc = [] if cond in (sp.true, sp.false) else definedness_conditions(cond, var)
        branches.append((cond, vc, cc))
    if all(not (cond.free_symbols if cond not in (sp.true, sp.false) else set())
           and not any(getattr(c, "free_symbols", None) for c in cc) for cond, _, cc in branches):
        _closed_piecewise_conditions(branches, add)
        return
    rel: list = []
    for _, vc, cc in branches:
        for c in vc + cc:
            if isinstance(c, sp.Contains) and c.free_symbols:
                add(c)                                   # a membership or a convention: on every branch, as before
            elif c is sp.false or c not in rel:
                rel.append(c)
    if not rel and branches and branches[-1][0] is sp.true:
        return                                           # every branch defined wherever it is reached
    syms = set().union(*[c.free_symbols for c in rel if c is not sp.false],
                       *[b[0].free_symbols for b in branches if b[0] not in (sp.true, sp.false)])
    if any(c.free_symbols == set() and c not in (sp.false, sp.true) for c in rel) or len(syms) != 1:
        add(DEFINEDNESS_UNDECIDED)                       # a closed condition left standing, two symbols, none
        return
    (v,) = syms

    def where(conds):
        out = S.Reals
        for c in conds:
            if isinstance(c, sp.Contains):
                continue                                 # added above
            st = Ctx.condition_set(c, v)
            if st is None:
                return None
            out = sp.Intersection(out, st)
        return out
    covered, D = S.EmptySet, S.EmptySet
    for cond, vc, cc in branches:
        Ci = S.Reals if cond is sp.true else S.EmptySet if cond is sp.false else Ctx.condition_set(cond, v)
        Ec, Ev = where(cc), where(vc)
        if Ci is None or Ec is None or Ev is None:
            add(DEFINEDNESS_UNDECIDED)
            return
        avail = sp.Complement(S.Reals, covered)
        sel = sp.Intersection(avail, Ec, Ci)
        D = sp.Union(D, sp.Intersection(sel, Ev))
        covered = sp.Union(covered, sp.Complement(avail, Ec), sel)
    U = sp.Complement(S.Reals, D)
    if U is S.EmptySet:
        return
    if isinstance(U, sp.FiniteSet) and all(p.is_real is True for p in U):
        for p in U:
            add(Ne(v, p))
        return
    if isinstance(U, (sp.Complement, sp.ConditionSet)) or U.has(sp.ConditionSet):
        add(DEFINEDNESS_UNDECIDED)
        return
    add(sp.Contains(v, D))


def _closed_piecewise_conditions(branches, add) -> None:
    """A Piecewise whose conditions name no symbol (f(2) for a piecewise f, or x = 2 put in): the branch taken is read
    exactly, condition by condition (`_closed_truth`), each condition up to it having a value; the taken branch's
    expression has its own conditions (a symbol a given leaves free among them); no branch taken: no value. Read as
    a Piecewise on one symbol, it was undecided and f(2) = 4 left UNKNOWN (attack on d4e round 4, D4E4-U2)."""
    for cond, vc, cc in branches:
        for c in cc:
            t = _closed_truth(c)
            if t is None:
                add(DEFINEDNESS_UNDECIDED)
                return
            if t is False:
                _no_value_off(add, sp.false)             # a condition with no value stops the evaluation
                return
        t = _closed_truth(cond)
        if t is None:
            add(DEFINEDNESS_UNDECIDED)
            return
        if t:
            for c in vc:
                add(c)
            return
    _no_value_off(add, sp.false)                         # no branch is taken (SymPy's nan)


def _closed_truth(c) -> bool | None:
    """Does the closed condition c hold, by the exact sign of each relation (`certified_sign`: never SymPy's own
    evaluation, which reads rounding noise)? None when a sign or a membership is not decided."""
    if c is sp.true or c is sp.false:
        return c is sp.true
    if isinstance(c, (sp.And, sp.Or)):
        parts = [_closed_truth(a) for a in c.args]
        stop = isinstance(c, sp.Or)                      # the value that decides: True for Or, False for And
        if any(t is stop for t in parts):
            return stop
        return None if any(t is None for t in parts) else not stop
    if isinstance(c, sp.Not):
        t = _closed_truth(c.args[0])
        return None if t is None else not t
    if not isinstance(c, (Eq, Ne, sp.StrictLessThan, sp.LessThan, sp.StrictGreaterThan, sp.GreaterThan)):
        return None
    sg = certified_sign(c.lhs - c.rhs)
    if sg not in (-1, 0, 1):
        return None
    return {Eq: sg == 0, Ne: sg != 0, sp.StrictLessThan: sg < 0, sp.LessThan: sg <= 0,
            sp.StrictGreaterThan: sg > 0, sp.GreaterThan: sg >= 0}[type(c)]


def _binder_conditions(n, var) -> list[Any]:
    """The conditions a binder's body puts on its bound variable, decided over the binder's range
    (see _range_conditions, _integral_conditions, _limit_conditions): `false` when the body is proved
    undefined there, DEFINEDNESS_UNDECIDED when it is not proved to exist, conditions on the
    problem's own symbols otherwise. A reading shares one budget and stops at its first undecided
    binder (the callers abstain on one); a result is kept per binder unless the budget cut it short,
    because verify() reads one text several times: ten inner limits with a condition solveset cannot
    decide held it 92 s (review of 30 Sep 2026)."""
    if getattr(_BINDER_STATE, "undecided", False):
        return [DEFINEDNESS_UNDECIDED]
    key = (n, var)
    with _BINDER_CACHE_LOCK:
        hit = _BINDER_CACHE.get(key)
    if hit is not None:
        out = list(hit)
    else:
        cut = getattr(_BINDER_STATE, "cut", False)
        _BINDER_STATE.cut = False
        try:
            if isinstance(n, (sp.Sum, sp.Product)):
                out = _range_conditions(n, var)
            elif isinstance(n, sp.Integral):
                out = _integral_conditions(n, var)
            elif isinstance(n, sp.Limit):
                out = _limit_conditions(n, var)
            else:
                out = []
        except Exception:  # noqa: BLE001 - a check that fails proves nothing
            out = [DEFINEDNESS_UNDECIDED]
        if not getattr(_BINDER_STATE, "cut", False):
            with _BINDER_CACHE_LOCK:
                if len(_BINDER_CACHE) >= _BINDER_CACHE_SIZE:
                    _BINDER_CACHE.clear()
                _BINDER_CACHE[key] = tuple(out)
        _BINDER_STATE.cut = cut or getattr(_BINDER_STATE, "cut", False)
    if any(is_undecided(c) for c in out):
        _BINDER_STATE.undecided = True
    return out


def definedness_conditions(expr, var) -> list[Any]:
    """Collect conditions under which `expr` is a well-defined real number. Never raises: a reading that
    fails proves nothing and gives DEFINEDNESS_UNDECIDED (see `_definedness_conditions`)."""
    if getattr(_BINDER_STATE, "left", None) is not None:
        return _definedness_conditions(expr, var)
    _BINDER_STATE.left, _BINDER_STATE.undecided, _BINDER_STATE.cut = _BUDGET, False, False
    try:
        return _definedness_conditions(expr, var)
    finally:
        _BINDER_STATE.left, _BINDER_STATE.undecided, _BINDER_STATE.cut = None, False, False


def _definedness_conditions(expr, var) -> list[Any]:
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

    # A rule that fails while it builds its condition proves nothing: SymPy evaluates Ne((-1)!, 0) and
    # mpmath raises "gamma function pole", and the callers read the exception as "no condition", so
    # 1/(-1)! = 0 (SymPy's 1/zoo) was certified and the step "1/factorial(-1) = 0" verified (fourth audit,
    # CAP-F1). Each failure is DEFINEDNESS_UNDECIDED, never "defined", and the walk goes on: the pole's own
    # rule (n!: a natural number) then reads the operation as undefined.
    try:
        nodes = _outer_nodes(sp.sympify(expr), var, add)
        while True:
            try:
                node = next(nodes)
            except StopIteration:
                break
            try:
                _node_conditions(node, var, add)
            except Exception:  # noqa: BLE001 - see above
                add(DEFINEDNESS_UNDECIDED)
    except Exception:  # noqa: BLE001 - the walk itself failed: nothing is proved
        add(DEFINEDNESS_UNDECIDED)
    return conds


def _no_number(v) -> bool:
    """Is the evaluated closed expression `v` SymPy's zoo, nan or ±oo (a pole, not a value)? An infinite bound of
    a Sum inside it is no pole."""
    return v in (S.ComplexInfinity, S.NaN, oo, -oo) or (isinstance(v, sp.Basic) and v.has(S.ComplexInfinity, S.NaN))


def _no_value_off(add, c):
    """The condition `c` of an operation that has no value where it fails; a closed operation off it
    (`c` false) is NO_VALUE too."""
    add(c)
    if c is sp.false:
        add(NO_VALUE)


def _plus_one_positive(e) -> bool:
    """Is e + 1 > 0, read with SymPy's evaluation on (an exponent written n - 1 is an unevaluated sum, and under an
    as-written reading even e + 1 stays one)?"""
    with sp.evaluate(True):
        return (e + 1).is_positive is True


def _infinite_argument(node) -> bool:
    """Is a closed argument of the function `node` (or the exponent of a power) infinite? sin(oo) is no real number
    (SymPy's AccumBounds: 0*sin(oo) was its 0, and certified), and exp(-oo), atan(oo), 2**(-oo), (1/2)**oo are values
    only where oo is read as a number, as 1/oo already is not (attack on d4f round 2, A-YO-5). A limit's point and
    a binder's bound are no arguments."""
    if isinstance(node, sp.Pow):
        args = (node.exp,)
    elif isinstance(node, sp.Function):
        args = node.args
    else:
        return False
    return any(isinstance(a, sp.Expr) and not a.free_symbols and a.has(oo, -oo) and _no_number(_evaluated(a))
               for a in args)


def _node_conditions(node, var, add) -> None:
    """The definedness conditions of one node of the as-written tree (see `_definedness_conditions`)."""
    if _infinite_argument(node):
        add(sp.false)
        add(NO_VALUE)
    if node is S.ComplexInfinity or node is S.NaN:
        # SymPy's zoo and nan, written out (`zoo` is in the namespace): no real number, and 1/zoo is
        # SymPy's 0 (CAP-F1)
        add(sp.false)
        add(NO_VALUE)
    elif type(node).__name__ == "written_domain":
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
        if ex.is_number and ex.is_extended_negative is True and not base.free_symbols \
                and _no_number(_evaluated(base)):
            # the reciprocal of a closed pole (1/(1/0), 1/tan(pi/2), 1/log(0)): 0 under a reading that gives
            # the pole a value (the Riemann sphere, cot = 1/tan), SymPy's 1/zoo: no value, and no "defined
            # nowhere" either, like 1/(-1)! (review of d4f, RK-F4, YO-6)
            add(sp.false)
            add(NO_VALUE)
        if isinstance(ex, sp.Rational) and not ex.is_Integer:
            if ex.q % 2 == 0:
                add(base >= 0 if ex > 0 else base > 0)
            else:
                if ex < 0:
                    add(Ne(base, 0))
                # a negative base: the real root or the principal value (Convention); a base that
                # is not real has the principal value only
                if base.is_extended_real is not False:
                    add(sp.Contains(base, ODD_ROOT_BASE))
        elif ex.is_Integer and ex < 0:
            add(Ne(base, 0))
        elif ex.is_zero is True:
            # 0**0: 1 or undefined (Convention); an infinite base (oo*x) is oo**0's convention wherever x is
            add(sp.Contains(S.Infinity if base.has(S.Infinity, S.NegativeInfinity) else base, ZERO_POWER_BASE))
        elif ex.is_number and not ex.is_rational:
            if ex.is_extended_positive is True:
                # 0**sqrt(2): 0 by the strict rule, undefined as written: a convention point; a negative base
                # has no real value either way (round 9 attack on part d4b, RK-1)
                add(base >= 0)
                add(sp.Contains(base, ZERO_POWER_BASE))
            else:
                add(base > 0)
        elif not ex.is_number and base.free_symbols and (var is None or var in ex.free_symbols):
            if ex.free_symbols <= base.free_symbols:
                # x**x: b > 0 is the rule on an interval; at a point the exact base and exponent decide (an
                # integer exponent of a nonzero base has its value): Convention real_power (RK-1)
                add(sp.Contains(sp.Tuple(base, ex), REAL_POWER))
            elif ex.is_integer is not True:
                add(base > 0)          # x^y style real power (var None: every symbol counts)
            elif not (ex.is_nonnegative is True or _plus_one_positive(ex)):
                # an exponent declared an integer is a power of the curriculum for every base: x != 0 when it may
                # be negative, nothing when it may not (n a positive integer: (x**2)**n and x**(2*n - 1); an integer
                # e is >= 0 when e + 1 > 0, which SymPy reads on the unevaluated n - 1 as written). Read as
                # x > 0, the textbook derivative 2*n*x**(2*n - 1) of (x**2)**n was refuted (attack on d4e round 4,
                # D4E4-U5)
                add(Ne(base, 0))
        elif not ex.is_number and base.is_number and base.is_zero is False and base.is_positive is not True \
                and ex.is_integer is not True:
            # a negative base, a variable exponent: the curriculum's value at an integer exponent only
            # (Convention negative_base)
            add(sp.Contains(ex, NEGATIVE_BASE_EXPONENT))
        elif not ex.is_number and base.is_zero is not False:
            # 0**k at k = 0 (a Sum's term at its first index): 1 or undefined (Convention, part d4a)
            add(sp.Contains(ex, ZERO_POWER_BASE))
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
    elif isinstance(node, (sp.Ci, sp.Chi, sp.li)):
        add(node.args[0] > 0)                    # complex for x < 0 (a log term), -oo at 0
        if isinstance(node, sp.li):
            add(Ne(node.args[0], 1))             # li(1) = -oo
    elif isinstance(node, sp.Ei):
        add(Ne(node.args[0], 0))
    elif isinstance(node, sp.polylog):
        s_, z = node.args
        if s_.is_Integer and s_ >= 2:
            add(z <= 1)                          # real for z <= 1, complex past 1
        elif s_ == 1:
            add(z < 1)                           # -log(1 - z)
        else:
            add(DEFINEDNESS_UNDECIDED)
    elif type(node).__name__ in ("gcd", "lcm"):
        # normalize.parse.gcd/lcm have a value only at rational numbers: x + gcd(x, 2) - gcd(2, x)
        # read as x was certified a simplification of x on all of R, and its value at
        # x = sqrt(2) was certified (30 Sep 2026). No interval rule decides the condition: the
        # callers abstain unless a point makes it true or false.
        for a in node.args:
            add(sp.Contains(a, S.Rationals))
        if type(node).__name__ == "gcd":
            # gcd(0, 0) has no value in the curriculum (the greatest common divisor of numbers not all 0):
            # the binding a = gcd(0, 0) + 1 read as a = 1 (review of d4d)
            add(Ne(sp.Add(*[sp.Abs(a) for a in node.args]), 0))
    elif isinstance(node, (sp.factorial, sp.factorial2, sp.subfactorial)):
        # n! of the curriculum: n a natural number. x + x! - x! at x = -3 was certified -3, and
        # (x + 3)(x - 2) = x! - x! had its root -3 certified (30 Sep 2026). A closed one off them has no
        # value: (-1)! is a pole of Γ, and 1/(-1)! is 0 only under 1/Γ or SymPy's 1/zoo (CAP-F1). n!! and
        # !n (SymPy's own, no notation of the parse reads them) are held to the same numbers.
        _no_value_off(add, sp.Contains(node.args[0], S.Naturals0))
    elif isinstance(node, sp.gamma):
        # Γ (LaTeX \Gamma, \gamma): a value off its poles 0, -1, -2, ...; 1/Γ(0) = 0 was certified (CAP-F1)
        _no_value_off(add, sp.Contains(node.args[0], _GAMMA_DOMAIN))
    elif isinstance(node, (sp.RisingFactorial, sp.FallingFactorial)):
        # a polynomial in x when k is a natural number; otherwise a quotient of Γ values with poles
        _no_value_off(add, sp.Contains(node.args[1], S.Naturals0))
    elif isinstance(node, sp.binomial):
        # C(n, r) of the curriculum: 0 <= r <= n integers. C(x, 2) at x = -3 was certified while
        # P(x, 2), built on factorial, was not (review of 30 Sep 2026); read as undefined there, the
        # root -2 of C(n, 2) = 3 was dropped and {-2, 3} refuted, while the generalized binomial
        # (C(-2, 2) = 3) and the 0 above n are conventions (Convention, part d4a)
        n_, r_ = node.args
        conds = [sp.Contains(r_, BINOMIAL_ARGUMENT), sp.Contains(n_ - r_, BINOMIAL_ARGUMENT)]
        for c in conds:
            add(c)
        if not node.free_symbols and not all(c is sp.true for c in conds):
            # outside them the generalized binomial may be a pole of Γ (binomial(-1, 1/2) is zoo): no
            # value under either reading (CAP-F1)
            with sp.evaluate(True):
                v = sp.binomial(_evaluated(n_), _evaluated(r_))
            if v.has(S.ComplexInfinity, S.NaN, oo, -oo):
                add(sp.false)
                add(NO_VALUE)
    elif isinstance(node, sp.Mod):
        # a divisor that is not positive: floored, truncated or Euclidean (Convention, part d4a)
        add(sp.Contains(node.args[1], MOD_DIVISOR))
    elif isinstance(node, sp.atan2):
        # atan2(0, 0): undefined, or 0 by some conventions (Convention); (|x| - x)*atan2(x - 1, 0) >= 0 on
        # x >= 0 had [0, oo) certified (round 8 of part d4b, YO-1)
        add(sp.Contains(node.args[0] ** 2 + node.args[1] ** 2, ORIGIN))
    elif isinstance(node, sp.arg):
        add(sp.Contains(node.args[0], ORIGIN))          # arg(0): undefined, or 0 (Convention)
    elif isinstance(node, sp.acosh):
        add(node.args[0] >= 1)
    elif isinstance(node, sp.atanh):
        add(node.args[0] > -1)
        add(node.args[0] < 1)


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
    # in the sandbox, under a time limit: six square roots make a polynomial of degree 64, and a small
    # claimed root held verify() over 200 s in the calling process (review of 30 Sep 2026)
    from ..equiv.numeric import _in_sandbox_worker
    if _in_sandbox_worker():
        return None                                   # a daemonic worker cannot start one of its own
    r = sb_run("mathverify.certify.domain:_rational_value", a, timeout=_SOLVE_TIMEOUT)
    if not r.ok:
        return None
    if r.value is False:
        return False                                  # irrational: in none of these sets
    got = s.contains(r.value)
    return bool(got) if got in (sp.true, sp.false) else None


def _rational_value(a):
    """The rational value of the algebraic number `a`, or False when it is irrational (its minimal
    polynomial is not linear). Run in the sandbox."""
    p = sp.minimal_polynomial(a, sp.Dummy("t"), polys=True)
    if p.degree() != 1:
        return False
    c1, c0 = p.all_coeffs()
    return sp.Rational(-c0, c1)


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
    if isinstance(ex, sp.Expr) and not ex.is_Atom:
        # an exponent with symbols that is identically 0 (x - x, floor(x) - floor(x), sin(x)**2 + cos(x)**2 - 1) is
        # 0 as written: 0**(x - x) and oo**(x - x) are the conventions 0**0 and oo**0, and were certified 1 (attack on
        # d4f round 2, A-YO-2); x**(x - x) is x**0, 2**(x - x) is 2**0 = 1
        try:
            if sp.simplify(_evaluated(ex)) == 0:
                return S.Zero
        except Exception:  # noqa: BLE001 - not proved 0: the exponent as written
            pass
    return ex


# Functions defined on all of ℝ (no condition), and the ones the rules above bound. Anything
# else — factorial or gamma of a variable, Mod, atan2, an undefined function, an integral — has a
# real domain these rules do not describe.
# The error function family, the sine/hyperbolic sine integrals and the Fresnel integrals are entire and real
# on ℝ; the cosine integrals and li need x > 0, Ei x ≠ 0, polylog(s, z) (s an integer >= 2) z <= 1. They are
# the primitives of e^(-x²), sin x/x, log(1+x)/x, ...: without them no fundamental-theorem certificate was
# built and ∫_R e^(-x²) dx = √π was UNKNOWN (attack on d4c round 2, RK-A/RK-B).
_TOTAL_FUNCS = (sp.sin, sp.cos, sp.exp, sp.Abs, sp.atan, sp.acot, sp.sinh, sp.cosh, sp.tanh,
                sp.asinh, sp.floor, sp.ceiling, sp.frac, sp.sign, sp.Max, sp.Min,
                sp.erf, sp.erfc, sp.erfi, sp.Si, sp.Shi, sp.fresnels, sp.fresnelc)
_BOUNDED_FUNCS = (sp.log, sp.tan, sp.sec, sp.cot, sp.csc, sp.asin, sp.acos, sp.acosh, sp.atanh,
                  sp.Ci, sp.Chi, sp.Ei, sp.li, sp.polylog)
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
    # an equality of a Float operand within its own precision is no proof (principle 4): Eq(x, 1) "held" at
    # x = 1.00000000000001 and Ne(x, 1) failed there (fourth audit GAP-NE). A difference beyond it decides
    tolerant = has_float(lhs, rhs)
    if isinstance(rel, Eq):
        # exact structural first, then numeric
        okS, _ = sym_equal(lhs, rhs)
        if okS:
            return True
        okN, _ = num_equal(lhs, rhs)
        return None if okN and tolerant else okN
    if isinstance(rel, Ne):
        okS, _ = sym_equal(lhs, rhs)
        if okS:
            return False
        okN, _ = num_equal(lhs, rhs)
        return None if okN is None or (okN and tolerant) else (not okN)
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
    if eq and sp.sympify(lhs - rhs).is_zero is not True:
        return None                       # equal within the Floats' precision only: the order is rounding (GAP-NE)
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
    h = _num_relation_holds(rel, var, c)
    if h is False:
        return False
    # a side undefined at the point as written holds nothing there, though its value may fold: 0*acos(4) is
    # SymPy's 0, and (|x| - x)*acos(2**x + x - 2) <= 0 "held" at x = 2 (round 8 of part d4b, YO-1). The
    # conventions (an odd root of a negative number, ...) are read where they stand, not here
    d = _defined_at(rel, var, c)
    if d is False:
        return False
    return None if d is None else h


def _defined_at(rel, var, c) -> bool | None:
    """Is every side of `rel` defined at var = c (its definedness conditions other than the conventions
    hold there)? None when one is undecided."""
    undecided = False
    for side in (rel.lhs, rel.rhs):
        if var not in getattr(side, "free_symbols", set()):
            continue
        for cond in _side_conditions(side, var):
            if is_convention(cond):
                continue
            if is_no_value(cond):
                return False
            if is_undecided(cond):
                undecided = True
                continue
            r = relation_holds_at(cond, var, c)
            if r is False:
                return False
            if r is None:
                undecided = True
    return None if undecided else True


@functools.lru_cache(maxsize=1024)
def _side_conditions(side, var) -> tuple:
    return tuple(definedness_conditions(side, var))


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
    if isinstance(dom, sp.ConditionSet):
        # a condition Ctx.domain_for could not solve (one with a trigonometric function on ℝ): decided
        # at the point, with the certified comparisons
        base = _in_set_certified(dom.base_set, c)
        if base is False:
            return False
        h = relation_holds_at(dom.condition, dom.sym, c)
        if h is False:
            return False
        return True if (base is True and h is True) else None
    return None


def in_domain(dom: sp.Set, c) -> bool | None:
    """Membership of a constant in a domain set. SymPy's own `contains` first; where it cannot
    decide, every comparison is certified (see _certified_compare) — the old fallback compared
    40-digit values, and returned False for any part that was not an Interval. A domain with a
    condition no solver could turn into a set (a ConditionSet, Ctx.domain_for) is decided by the
    certified comparisons only: SymPy reads the condition at the point uncertified, and took
    cos(arccot(1/2) + arccot(2)) != 0 for true (the cosine is cos(pi/2) = 0; measured 2 Oct 2026)."""
    if isinstance(dom, sp.Set) and dom.has(sp.ConditionSet):
        try:
            if certified_sign(c) == NONREAL:
                return False
            return _in_set_certified(dom, c)
        except Exception:  # noqa: BLE001
            return None
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


def membership_undecided(dom: sp.Set, c) -> bool:
    """Does the membership of the constant `c` in `dom` rest on a number-set membership no check
    decides: a gcd/lcm argument rational, a factorial argument natural (Ctx.domain_for cuts the domain
    by them), at pi + E? `in_domain` then says None, which the callers read as inside, and the value
    x + gcd(x, 2) - gcd(2, x) at x = pi + E was certified, and so was the root pi + E of
    (x - pi - E)(x - 1/2) = gcd(x, 2) - gcd(2, x) (V16, 30 Sep 2026)."""
    try:
        r = dom.contains(c)
    except Exception:  # noqa: BLE001
        return False
    if not isinstance(r, sp.Basic) or r is sp.true or r is sp.false:
        return False
    return any(decide_membership(*m.args) is None for m in r.atoms(sp.Contains))


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
        if d is None:
            # no exact check decides it (a number-set membership at pi + E, membership_undecided, or a
            # comparison: x = 2*(atan(1/3) + ...), pi exactly, against x > pi): the root is neither kept
            # nor dropped. Kept, {T} was certified and the right {} refuted (fourth audit G10, review B)
            rejected.append((c, "definedness_undecided: membership in the domain"))
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


def written_definedness(src: str, ns: dict[str, Any], pins: dict | None = None) -> tuple[list[Any], set]:
    """Definedness of an IR expression or relation AS WRITTEN (see `parse_as_written`): the open
    conditions, and the symbols of an expression that is defined NOWHERE (a closed condition
    that fails, e.g. `1/(x - x)`). Empty when the text cannot be read that way.

    `pins`: symbols a given fixes, put in the written text (unevaluated, never a bound variable) BEFORE
    its conditions are read. A condition can depend on the value itself: x**a has the condition x > 0
    while a is free, none once a = 2, and the right (−2, 2) for x**a < 4 was refuted with a = 2 (TAN-09)."""
    from ..normalize.parse import parse_as_written, substitute_free
    e = parse_as_written(src, ns)
    if e is None:
        return [], set()
    if pins:
        try:
            with sp.evaluate(False):
                e = substitute_free(e, pins)
        except Exception:  # noqa: BLE001 - read without the values (the old reading)
            pass
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


def hold_nowhere(cs, s_) -> bool:
    """Worker: do the relations `cs` on the one symbol `s_` hold nowhere together, PROVED by an exact empty set?
    On ℝ first; then the periodic ones on one common period, where `sandbox.exactsets` solves them exactly (on
    ℝ SymPy leaves sin(x) > 0 and -sin(x) > 0 a ConditionSet). A periodic set empty on one period is empty."""
    from sympy.calculus.util import lcim
    rel = sp.And(*cs)
    if rel is sp.false or exact_solveset(rel, s_, S.Reals) is S.EmptySet:
        return True
    periodic, periods = [], []
    for c in cs:
        try:
            p_ = sp.periodicity(c.lhs - c.rhs, s_)
        except Exception:  # noqa: BLE001 - no period found: the relation is left out of this proof
            p_ = None
        if p_ is not None and p_.is_positive is True:
            periodic.append(c)
            periods.append(p_)
    if not periodic:
        return False
    try:
        # lcim: None when two periods have no common multiple (2*pi and 1), and then no proof
        period = lcim(periods) if len(periods) > 1 else periods[0]
        return exact_solveset(sp.And(*periodic), s_, Interval.Ropen(0, period)) is S.EmptySet
    except Exception:  # noqa: BLE001
        return False


def open_conditions_empty(conds, timeout: float = 8.0) -> bool:
    """Do the open definedness conditions on one symbol hold nowhere together? x + log(x) - log(x) + log(-x) -
    log(-x) needs x > 0 and -x > 0: each alone has points, so no condition fails outright and the expression
    passed as defined: its derivative 1, the antiderivative x of 1 + ..., the simplification x and its limit
    1 at 1 were certified or refuted as if it had values (fourth audit TAN-06). Only a proof counts
    (`hold_nowhere`); the expression is then defined nowhere, like one whose condition fails."""
    by_sym: dict = {}
    for c in conds:
        fs = getattr(c, "free_symbols", set())
        if isinstance(c, sp.core.relational.Relational) and len(fs) == 1:
            by_sym.setdefault(next(iter(fs)), []).append(c)
    for s_, cs in by_sym.items():
        r = sb_run("mathverify.certify.domain:hold_nowhere", cs, s_, timeout=timeout)
        if r.ok and r.value is True:
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


def _region_facts(d, region):
    """`d` as a Dummy with the facts of `region` (an index Range: an integer, nonnegative or positive), or `d`
    itself."""
    facts = {}
    try:
        if region.is_subset(S.Integers) is True:
            facts["integer"] = True
            if region.inf.is_positive is True:
                facts["positive"] = True
            elif region.inf.is_nonnegative is True:
                facts["nonnegative"] = True
        elif region.is_subset(S.Reals) is True:
            facts["real"] = True
    except Exception:  # noqa: BLE001
        return d
    return sp.Dummy(d.name, **facts) if facts else d


def written_undefined_in(src: str, ns: dict[str, Any], var, region: sp.Set, pins: dict | None = None,
                         params: dict | None = None) -> bool | None:
    """Is the expression, AS WRITTEN, undefined somewhere in `region` (a point set, an interval, an
    index Range)? None when that cannot be decided. Measured 23 Sep 2026 on kinds that keep their
    own domain handling: "(x²/x)' at 0 is 1", "max of x/x − x² on [−1, 1] is 1" (never attained)
    and "Σ_{k=−1}^{1} k/k = 3" were certified CORRECT. `pins`: the values the givens fix
    (`written_definedness`); without them a condition naming a parameter decided nothing, and with b = 1/2
    the maximum 1 of x + 0*sqrt(b - x) on [0, 1] was certified (review of d4e)."""
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
    conds, nowhere = written_definedness(src, ns, pins)
    if var in nowhere or written_closed_undecided(src, ns):
        return True                    # a closed condition no check proves: the callers abstain
    d2 = _region_facts(var, region)
    for c in conds:
        other = c.free_symbols - {var}
        if other:
            # a parameter is read with the facts of its region (`params`: Dummies, a > 0 positive) and the variable
            # with the region's (k >= 1 an integer): k + a != 0 holds for every value. Left undecided, the sums of
            # 1/(k + a) with a > 0 were UNKNOWN (attack on d4e round 3, D4E3-RK-4)
            if not params or not other <= set(params) or isinstance(c, sp.Contains) \
                    or not isinstance(c, sp.core.relational.Relational):
                return None
            held = c.xreplace({**params, var: d2})
            if held is sp.true:
                continue
            return True if held is sp.false and var not in c.free_symbols else None
        if isinstance(c, sp.Contains):
            # a membership or a convention (0**k at k = 0: 1 or undefined): where it fails over the region
            # (`_violations`). Read as a relation it was never decided, and Σ_{k=0}^{3} 0**k = 1 and, with
            # a = 0, Σ_{k=0}^{3} a**k = 1 were certified (attack on d4e, YO-1)
            bad = _violations(c, var, region)
            if bad is None:
                return None
            if bad.is_empty is not True:
                return True
            continue
        bad = Eq(c.lhs, c.rhs) if isinstance(c, Ne) else sp.Not(c)
        # first with the region's facts (an index k >= 0: factorial(k) != 0 at every one, which exact_solveset left a
        # ConditionSet even on Range(0, 4); round 4, RK-4)
        if d2 is not var and bad.xreplace({var: d2}) is sp.false:
            continue
        try:
            # a trigonometric condition is read on the region itself, not on one period of ℝ: the
            # violations of sin(x) >= 0 on [10, 12] were empty (sandbox.exactsets)
            s = exact_solveset(bad, var, region)
        except Exception:  # noqa: BLE001
            return None
        if isinstance(s, sp.ConditionSet) or s.has(sp.ConditionSet):
            # no proof that the condition holds on the whole region is no proof of definedness: the maximum 0
            # of -(x - pi)**2 + (x + 1)Q/((x + 1)Q) - 1 on [2, 4] (undefined at pi) was certified (review of
            # 2 Oct 2026, B5). Undecided: every caller abstains on None as on True (d4e round 3), and a
            # trigonometric condition read True here added nothing (round 9 of part d4b, mutation K10)
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
    if any(is_convention(c) for c in conds):
        # a point where the value is a convention (x**(1/3) below 0, (x - 1)**0 at 1) is neither in nor
        # out of the domain; solveset does not read the condition and continuous_domain would decide it
        ev["error"] = "convention_dependent_domain"
        return None, ev
    dom = base
    for cond in conds:
        # a trigonometric condition on a bounded base is solved on it (sandbox.exactsets rebuilds and
        # checks it there); otherwise on ℝ, where the exact check below reads SymPy's own set (the base
        # may carry SymPy's mistake: cos(arccot(x) + arccot(2)) != 0 read as x != -2)
        within = base if at_risk(cond, var) and _hull(base) is not None else S.Reals
        r = sb_run("mathverify.sandbox.ops:solveset_in", cond, var, within, timeout=timeout)
        if not r.ok or isinstance(r.value, sp.ConditionSet):
            ev["fallback"] = "continuous_domain"
            r2 = sb_run("mathverify.sandbox.ops:continuous_domain", expr, var, base, timeout=timeout)
            if r2.ok and not isinstance(r2.value, sp.ConditionSet):
                return r2.value, ev
            ev["error"] = r.error or r2.error
            return None, ev
        if _solveset_contradicted(cond, var, r.value, within):
            ev["error"] = f"solveset_contradicted_by_exact_check: {cond}"
            return None, ev
        dom = sp.Intersection(dom, r.value)
    ev["domain"] = str(dom)
    return dom, ev


def _probe_points(iv) -> list:
    """Points inside an interval piece: several, spread over it, and far out on an unbounded side.
    One point per piece missed a set cut to one period: (0, pi) for sin(x) > 0 left [pi, oo), whose
    probe pi + 1 fails the condition as it should, though 2*pi + 1 meets it (fourth audit G2)."""
    lo, hi = iv.inf, iv.sup
    if lo.is_finite and hi.is_finite:
        return [lo + (hi - lo) * sp.Rational(k, 8) for k in (1, 3, 4, 5, 7)]
    steps = (1, 2, 3, 5, 8, 13, 21)
    if lo.is_finite:
        return [lo + d for d in steps]
    if hi.is_finite:
        return [hi - d for d in steps]
    return [sp.Integer(0)] + [sp.Integer(d) for d in steps] + [-sp.Integer(d) for d in steps]


def _solveset_contradicted(cond, var, s, within=S.Reals) -> bool:
    """Does an exact check contradict SymPy's solution set of `cond`? Each excluded isolated point must
    fail the condition, and a point inside each interval piece must meet it (or fail it, outside).
    solveset reads cos(atan(x) + atan(2)) != 0 as x != -2, where the cosine is 1 (the root is 1/2), and
    that domain was certified (audit of 29 Sep 2026). Only a contradiction counts: an undecided check
    leaves SymPy's set as it was. `within`: the set `s` was solved on (its complement is taken there)."""
    from ..sandbox.exactsets import sign_range
    try:
        # the set lies in the reals the variable's sign leaves (a positive x: 0 is no point of it)
        out = sp.Complement(sp.Intersection(within, sign_range(var)), s)
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
            elif isinstance(p, sp.Interval) and p.measure.is_extended_positive:
                # extended: oo.is_positive is False (sympy >= 1.13), and an unbounded piece was
                # never probed at all
                checks += [(q, inside) for q in _probe_points(p)]
    for q, inside in checks[:48]:
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
        if ctx.unsolved_conditions(var):
            # the domain is cut by a condition with no closed form on ℝ (sin(x) > 0 given): the
            # expression's domain within it is no set the comparison can read (fourth audit G2)
            return condition_unsolved(LAYER, ctx.unsolved_conditions(var), t.ms)
        # the expression's own conditions are what domain_of_expression solves ([a, oo) for √(x − a))
        unbound = ctx.unapplied_conditions(var, enforced=definedness_conditions_strict(expr, var) or ())
        if unbound:
            # a condition on x that names a symbol no given fixes (x > b): read on ℝ, [-2, 2] was
            # certified as the domain of √(4 − x²) under x > b (part vi, 30 Sep 2026)
            return condition_not_applied(LAYER, unbound, t.ms)
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
