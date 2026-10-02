"""Solution sets of relations with a trigonometric function, exact or unsolved (a CAS primitive: no decision
logic).

SymPy 1.14 solves an inequality or a `!=` whose expression is periodic on ONE period and returns that
as the answer, also on a bounded domain (it solves on ℝ, cuts the line to [0, P), then intersects):
solveset(sin(x) > 0, x, Reals) = (0, pi); solveset(sin(x) > 0, x, Interval(-10, 10)) = (0, pi);
solveset(Ne(cos(x), 0), x, Reals) = [0, 2*pi) minus {pi/2, 3*pi/2}. A product with a periodic factor
loses the periodic part: Ne(x*cos(x), 0) gave (-oo, 0) ∪ (0, oo). Its equation sets lose roots: with
Q = sqrt(3)*sin(x) - cos(x) - 1, Q = 0 is 2*n*pi + pi/3 on ℝ and {pi/3} on [0, 2*pi], without x = pi,
and so is x*Q = 0 ({0, pi/3}). None of these is a ConditionSet, so every caller took them for the answer
(fourth audit, 1 Oct 2026, G2; its review of 2 Oct 2026, B1-B6). A numeric root search does not repair
this: it misses a multiple root (Q**3 = 0 at pi), so it is no proof of completeness either.

So a set is exact only for an expression whose zeros and poles are known in closed form, completely:
  (i)   a polynomial or rational function of the variable (exact real roots, `Poly.real_roots`);
  (ii)  a polynomial in ONE trigonometric function of a linear argument, g(f(a*x + b)) with g a
        polynomial: the real roots r of g, then the closed general solution of f(u) = r; the poles of
        tan, cot, sec, csc likewise;
  (iii) a product or quotient whose factors (as written, `together` then `fraction`) are each (i) or
        (ii), with integer powers.
Everything else is returned as a ConditionSet: the membership of each point is still decided exactly,
the set is not known. On a bounded domain the zeros and the poles of lhs - rhs cut the hull into cells,
and the sign is certified (`certified_sign`) on each cell and at each point; on an unbounded domain an
equation's set is the union of the progressions, an inequality or `!=` is known only when it holds
nowhere or everywhere on one period. More than `LIMIT` points on a window, or a set that does not fit
these, leaves the set unsolved: the work of one call is bounded (B6: sin(1000*x) > 0 on [0, 30] took over
20 minutes).
"""
from __future__ import annotations

import math

import sympy as sp
from sympy import S
from sympy.functions.elementary.trigonometric import TrigonometricFunction

# more points (zeros, poles, cells) on one window than this: the set is left unsolved
LIMIT = 400
_TRIG = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)
# the functions whose poles cut the cells: (pole function, the function whose zeros they are)
_POLES = ((sp.tan, sp.cos), (sp.sec, sp.cos), (sp.cot, sp.sin), (sp.csc, sp.sin))
_CELL_FUNCS = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.exp, sp.Abs)


class _Unsolved(Exception):
    """The set is not one of the exact classes, or too large: left a ConditionSet."""


def oscillates(e, var) -> bool:
    """Does `e` contain a trigonometric function of `var`?"""
    return any(isinstance(n, TrigonometricFunction) and var in n.free_symbols for n in sp.preorder_traversal(e))


def _relations(rel):
    if isinstance(rel, sp.core.relational.Relational):
        return [rel]
    if isinstance(rel, sp.logic.boolalg.Boolean) and not isinstance(rel, sp.Set):
        out = []
        for a in getattr(rel, "args", ()):
            out += _relations(a)
        return out
    return []


def at_risk(rel, var) -> bool:
    """Is SymPy's solution set of `rel` (a relation, a conjunction, or an expression = 0) open to the
    truncation and loss this module guards against?"""
    if isinstance(rel, sp.Expr):
        return oscillates(rel, var)
    return any(oscillates(r.lhs - r.rhs, var) for r in _relations(rel))


def exact_solveset(rel, var, domain=S.Reals):
    """`sp.solveset(rel, var, domain)` when `rel` has no trigonometric function of `var`; otherwise the
    exact set of the classes in the module doc, or a ConditionSet."""
    if not at_risk(rel, var):
        return sp.solveset(rel, var, domain)
    if isinstance(rel, sp.Expr):
        rel = sp.Eq(rel, 0)
    exact = None
    if isinstance(rel, sp.core.relational.Relational):
        try:
            exact = _rebuilt(rel, var, domain)
        except Exception:  # noqa: BLE001 - not exact (a class it is not, too many points, ...): unsolved
            exact = None
    return exact if exact is not None else sp.ConditionSet(var, rel, domain)


def _hull(domain):
    """The closed bounded interval [lo, hi] that holds `domain`, as (lo, hi), or None (SymPy's inf and sup
    raise on a ConditionSet: no hull)."""
    try:
        lo, hi = domain.inf, domain.sup
    except Exception:  # noqa: BLE001
        return None
    if lo.is_number and hi.is_number and lo.is_finite and hi.is_finite and (hi - lo).is_positive is True:
        return lo, hi
    return None


# ------------------------------------------------------------------------------------------------
# the exact classes: zeros and poles as progressions (point, step); step 0 is a single point
# ------------------------------------------------------------------------------------------------
def _poly_roots(base, var):
    """(i): the exact real roots of a polynomial in `var`, or None when `base` is not one."""
    if base.free_symbols != {var}:
        return None
    try:
        p = sp.Poly(base, var)
    except sp.PolynomialError:
        return None
    if not p.domain.is_Exact or p.free_symbols_in_domain or p.is_zero:
        return None
    return _real_roots(p)


def _real_roots(p) -> list:
    """All the real roots of a polynomial with exact coefficients, exactly: `real_roots` over the
    rationals; over an algebraic field (sqrt(3) - t) every root `roots` finds, when they are all of them
    (multiplicities summing to the degree), the real ones kept by a certified sign."""
    try:
        return list(dict.fromkeys(p.real_roots()))
    except Exception:  # noqa: BLE001 - not over ZZ/QQ
        pass
    from ..equiv.numeric import NONREAL, certified_sign
    rs = sp.roots(p)
    if sum(rs.values()) != p.degree():
        raise _Unsolved(f"roots not all found: {p}")
    out = []
    for r_ in rs:
        s_ = certified_sign(r_)
        if s_ is None:
            raise _Unsolved(f"realness undecided: {r_}")
        if s_ != NONREAL:
            out.append(r_)
    return out


def _trig_parts(base, var):
    """(ii): (f, a, b, g) with base = g(f(a*var + b)), g a polynomial with exact coefficients, or None."""
    atoms = [n for n in base.atoms(TrigonometricFunction) if var in n.free_symbols]
    if not atoms:
        return None
    T = atoms[0]                               # another one left in g makes it no polynomial in t
    if type(T) not in _TRIG:
        return None
    try:
        arg = sp.Poly(T.args[0], var)
    except sp.PolynomialError:
        return None
    if arg.degree() != 1 or not arg.domain.is_Exact or arg.free_symbols_in_domain:
        return None
    a, b = arg.coeff_monomial(var), arg.coeff_monomial(1)
    t = sp.Dummy("t")
    bt = base.xreplace({T: t})
    if bt.free_symbols != {t}:
        return None
    try:
        g = sp.Poly(bt, t)
    except sp.PolynomialError:
        return None
    if not g.domain.is_Exact or g.free_symbols_in_domain or g.degree() < 1:
        return None
    return type(T), a, b, g


def _certified(e):
    from ..equiv.numeric import NONREAL, certified_sign
    s_ = certified_sign(e)
    if s_ is None or s_ == NONREAL:
        raise _Unsolved(f"sign undecided: {e}")
    return s_


def _u_solutions(f, r) -> list[tuple]:
    """The solutions u of f(u) = r as progressions (u0, step)."""
    pi = sp.pi
    if f in (sp.sec, sp.csc):
        if _certified(r) == 0:
            return []
        f, r = (sp.cos if f is sp.sec else sp.sin), 1 / r
    if f is sp.cot:
        if _certified(r) == 0:
            return [(pi / 2, pi)]
        f, r = sp.tan, 1 / r
    if f is sp.tan:
        return [(sp.atan(r), pi)]
    if _certified(1 - abs(r)) < 0:
        return []                              # |r| > 1: no real solution
    if f is sp.sin:
        u0 = sp.asin(r)
        return [(u0, 2 * pi), (pi - u0, 2 * pi)]      # one point twice when |r| = 1: merged on a window
    u0 = sp.acos(r)
    return [(u0, 2 * pi), (-u0, 2 * pi)]


def _factor_sets(base, var):
    """(zeros, poles) of one factor as progressions in `var`, or raise _Unsolved."""
    roots = _poly_roots(base, var)
    if roots is not None:
        return [(r_, S.Zero) for r_ in roots], []
    parts = _trig_parts(base, var)
    if parts is None:
        raise _Unsolved(f"not an exact class: {base}")
    f, a, b, g = parts
    zeros = []
    for r_ in _real_roots(g):
        zeros += [((u0 - b) / a, step / abs(a)) for u0, step in _u_solutions(f, r_)]
    poles = []
    if f in (sp.tan, sp.sec):
        poles = [((sp.pi / 2 - b) / a, sp.pi / abs(a))]
    elif f in (sp.cot, sp.csc):
        poles = [((-b) / a, sp.pi / abs(a))]
    return zeros, poles


def _structure(e, var):
    """(zeros, poles, periods) of e as progressions: e = (product of factors) / (product of factors),
    each factor an integer power of a class (i) or (ii) base; raise _Unsolved otherwise. `periods` is
    None when a factor that depends on `var` is not periodic."""
    num, den = sp.fraction(sp.together(e))
    zeros, poles, periods = [], [], []
    for part, is_num in ((num, True), (den, False)):
        for arg in sp.Mul.make_args(part):
            if var not in arg.free_symbols:
                if _certified(arg) == 0:
                    raise _Unsolved("a zero factor")
                continue
            base, ex = arg.as_base_exp()
            if not (ex.is_Integer and ex > 0):
                raise _Unsolved(f"not an integer power: {arg}")
            z, p = _factor_sets(base, var)
            (zeros if is_num else poles).extend(z)
            poles.extend(p)
            parts = _trig_parts(base, var)
            if parts is None:
                periods = None
            elif periods is not None:
                f, a, _, _ = parts
                periods.append((sp.pi if f in (sp.tan, sp.cot) else 2 * sp.pi) / abs(a))
    return zeros, poles, periods


def _on(progs, lo, hi) -> list:
    """The points of the progressions in [lo, hi], exact, each membership certified."""
    out = []
    flo, fhi = float(sp.N(lo, 30)), float(sp.N(hi, 30))
    for p0, step in progs:
        if step == 0:
            cand = [p0]
        else:
            fp, fs = float(sp.N(p0, 30)), float(sp.N(step, 30))
            n0, n1 = math.floor((flo - fp) / fs) - 1, math.ceil((fhi - fp) / fs) + 1
            if n1 - n0 > LIMIT:
                raise _Unsolved("too many points on the window")
            cand = [p0 + step * k for k in range(n0, n1 + 1)]
        for c in cand:
            if _certified(c - lo) >= 0 and _certified(hi - c) >= 0:
                out.append(c)
    return out


def _sorted_unique(pts):
    keyed = sorted(((sp.N(p, 50), p) for p in pts), key=lambda t: t[0])
    out: list = []
    for k, p in keyed:
        if out and abs(k - out[-1][0]) < sp.Float("1e-40", 50):
            if _certified(p - out[-1][1]) != 0:
                raise _Unsolved("points too close to order")
            continue
        out.append((k, p))
    return [p for _, p in out]


def _holds(op, s) -> bool:
    return {sp.StrictGreaterThan: s > 0, sp.GreaterThan: s >= 0, sp.StrictLessThan: s < 0,
            sp.LessThan: s <= 0, sp.Unequality: s != 0, sp.Equality: s == 0}[op]


def _same(p, pts) -> bool:
    """Is `p` one of `pts` (exactly)? Only the numerically close ones are compared exactly."""
    fp = sp.N(p, 30)
    return any(_certified(p - q) == 0 for q in pts if abs(sp.N(q, 30) - fp) < sp.Float("1e-20", 30))


def _on_window(rel, var, lo, hi):
    """(the points of [lo, hi] where `rel` holds, as a set; the zeros; the poles) for a relation of the
    exact classes, or raise _Unsolved."""
    e = rel.lhs - rel.rhs
    zp, pp, _ = _structure(e, var)
    poles = _sorted_unique(_on(pp, lo, hi))
    zeros = [z for z in _sorted_unique(_on(zp, lo, hi)) if not _same(z, poles)]
    op = type(rel)
    if op is sp.Equality:
        return sp.FiniteSet(*zeros), zeros, poles
    edges = _sorted_unique([lo, hi] + zeros + poles)
    pieces: list = []
    for a, b in zip(edges[:-1], edges[1:]):
        s_ = _certified(e.subs(var, (a + b) / 2))
        if s_ == 0:
            raise _Unsolved("a zero inside a cell")       # cannot happen with the classes: refuse
        if _holds(op, s_):
            pieces.append(sp.Interval.open(a, b))
    for p in edges:
        if _same(p, poles):
            continue
        if _holds(op, 0 if _same(p, zeros) else _certified(e.subs(var, p))):
            pieces.append(sp.FiniteSet(p))
    return (sp.Union(*pieces) if pieces else S.EmptySet), zeros, poles


def period(e, var):
    """A period of `e` in `var` from its exact class (a common period of its trigonometric factors), or
    None when it is not of the classes or has a factor that is not periodic."""
    try:
        _, _, periods = _structure(e, var)
    except Exception:  # noqa: BLE001
        return None
    return _common_period(periods) if periods else None


def _rebuilt(rel, var, domain):
    e = rel.lhs - rel.rhs
    if isinstance(domain, sp.FiniteSet) and all(p.is_number for p in domain):
        keep = _on_points(rel, var, domain)            # point by point
        if keep is not None:
            return sp.FiniteSet(*keep)
    hull = _hull(domain)
    if hull is not None:
        return sp.Intersection(_on_window(rel, var, hull[0], hull[1])[0], domain)
    P = period(e, var)
    if P is not None:
        discrete = _on_periodic_points(rel, var, domain, P)
        if discrete is not None:
            return discrete
    if isinstance(rel, sp.Equality):
        zp, pp, _ = _structure(e, var)
        n = sp.Dummy("n", integer=True)

        def union(progs):
            return sp.Union(*[sp.FiniteSet(p0) if step == 0 else sp.ImageSet(sp.Lambda(n, p0 + step * n), S.Integers)
                              for p0, step in progs]) if progs else S.EmptySet
        zs = union(zp)
        return sp.Intersection(sp.Complement(zs, union(pp)) if pp else zs, domain)
    if P is None:
        return None
    # an inequality or `!=` on an unbounded domain: its set on one whole period decides only "nowhere"
    # and "everywhere" (sin(x) > 2, cos(x) + 2 != 0); anything else is a union over all periods, and
    # ℝ minus progressions is a set no sampler draws from: the ConditionSet decides each point exactly
    w = _on_window(rel, var, S.Zero, P)[0]
    if w is S.EmptySet:
        return S.EmptySet
    if w == sp.Interval(0, P):
        return domain
    return None


def continuity_set(expr, var, domain):
    """Where on `domain` the expression is continuous, for an expression the cells cover (sums,
    products, integer powers, exp, trigonometric functions, Abs: continuous except at their poles,
    which must be of the exact classes), or None. SymPy's continuous_domain solves the conditions of a
    trigonometric expression on one period: log(cos(x)) on [5, 8] gave [5, 2*pi) (the truth is
    [5, 5*pi/2)) and log(x*cos(x)) on [2, 3], undefined everywhere there, gave [2, 3] (measured 1 Oct
    2026)."""
    if not _cells_supported(expr, var):
        return None
    out = domain
    for u in _poles(expr, var):
        s_ = exact_solveset(sp.Ne(u, 0), var, out)
        if isinstance(s_, sp.ConditionSet) or s_.has(sp.ConditionSet):
            return None
        out = s_
    return out


def _cells_supported(e, var) -> bool:
    """Is `e` continuous wherever it is defined, with its points of undefinedness the poles `_poles`
    lists? Sums, products, integer powers, exp, trigonometric functions and Abs of such."""
    for n in sp.preorder_traversal(e):
        if var not in n.free_symbols or n.is_Symbol or isinstance(n, (sp.Add, sp.Mul)):
            continue
        if isinstance(n, sp.Pow):
            b, x_ = n.args
            if var in x_.free_symbols:
                if not (b.is_number and b.is_positive is True):
                    return False
            elif not x_.is_Integer:
                return False
            continue
        if isinstance(n, _CELL_FUNCS):
            continue
        return False
    return True


def _poles(e, var) -> list:
    """The expressions whose zeros are the points where `e` is undefined (for `_cells_supported` ones)."""
    out = []
    for n in sp.preorder_traversal(e):
        if isinstance(n, sp.Pow) and var in n.base.free_symbols and n.exp.is_negative:
            out.append(n.base)
        for f, z in _POLES:
            if isinstance(n, f) and var in n.free_symbols:
                out.append(z(n.args[0]))
    return list(dict.fromkeys(out))


def _common_period(steps) -> sp.Expr | None:
    """The least common multiple of positive periods whose ratios are rational, or None."""
    if not steps:
        return None
    L = steps[0]
    for a in steps[1:]:
        q = sp.simplify(a / L)                # exact: an irrational ratio has no common period
        if not isinstance(q, sp.Rational):
            return None
        L = L * abs(q.p)                      # lcm(L, (p/q) L) = p L for p/q in lowest terms
    return L


def set_periods(s_) -> list | None:
    """The periods of a set built from ℝ, progressions over the integers and conditions with a period
    (by Union, Intersection, Complement), or None when a part has none (an interval, the integers)."""
    if s_ is S.Reals or s_ is S.EmptySet:
        return []
    if isinstance(s_, sp.ImageSet):
        lam = s_.lamda
        if len(lam.variables) != 1 or s_.base_set != S.Integers:
            return None
        n = lam.variables[0]
        a = sp.expand(lam.expr).coeff(n, 1)
        if a == 0 or sp.expand(lam.expr - a * n).has(n) or not a.is_number:
            return None
        return [abs(a)]
    if isinstance(s_, sp.FiniteSet) and len(s_) == 0:
        return []
    if isinstance(s_, sp.ConditionSet):
        c = s_.condition
        if not isinstance(c, sp.core.relational.Relational):
            return None
        Pc = period(c.lhs - c.rhs, s_.sym)
        rest = set_periods(s_.base_set)
        if Pc is None or rest is None:
            return None
        return [Pc] + rest
    if isinstance(s_, (sp.Union, sp.Intersection, sp.Complement)):
        out: list = []
        for a in s_.args:
            pa = set_periods(a)
            if pa is None:
                return None
            out += pa
        return out
    return None


def _on_period(s_, L):
    """The set cut to [0, L), for a set `set_periods` reads and a common period L of its parts: each
    progression becomes a finite set. Raises when a part is not finite there."""
    window = sp.Interval.Ropen(0, L)

    def cut(t):
        if t is S.Reals:
            return window
        if t is S.EmptySet:
            return t
        if isinstance(t, sp.ImageSet):
            out = sp.Intersection(t, window)
            if not isinstance(out, sp.FiniteSet) and out is not S.EmptySet:
                raise ValueError("progression not finite on the window")
            if len(out) > LIMIT:
                raise ValueError("too many points on the window")
            return out
        if isinstance(t, sp.ConditionSet):
            return sp.ConditionSet(t.sym, t.condition, cut(t.base_set))
        if isinstance(t, (sp.Union, sp.Intersection, sp.Complement)):
            return type(t)(*[cut(a) for a in t.args])
        raise ValueError(f"not periodic: {type(t).__name__}")

    return cut(s_)


def set_is_empty(s_) -> bool | None:
    """Is the set empty? SymPy's own answer, else, for a set built of progressions over the integers
    (the sets `exact_solveset` returns on an unbounded domain) and periodic conditions with
    commensurable periods, the answer on one common period [0, L), where each progression is a finite
    set: SymPy leaves {pi/2 + 2*n*pi} minus {pi/2 + n*pi} undecided."""
    if s_ is S.EmptySet:
        return True
    try:
        e = s_.is_empty
    except Exception:  # noqa: BLE001
        e = None
    if e is not None:
        return bool(e)
    periods = set_periods(s_)
    L = _common_period(periods) if periods else None
    if L is None:
        return None
    try:
        w = _on_period(s_, L)
    except Exception:  # noqa: BLE001
        return None
    if w is S.EmptySet:
        return True
    if isinstance(w, sp.FiniteSet):
        return len(w) == 0
    try:
        e = w.is_empty
    except Exception:  # noqa: BLE001
        return None
    return None if e is None else bool(e)


def _on_periodic_points(rel, var, domain, P):
    """`rel` on a domain that is a set of points repeating with a period (progressions, cut by periodic
    conditions): the points of one common period L of the domain and of `rel`, each decided, repeated
    as progressions of step L. None when the domain is no such set."""
    periods = set_periods(domain)
    if not periods:
        return None
    L = _common_period(periods + [P])
    if L is None:
        return None
    try:
        pts = _on_period(domain, L)
    except Exception:  # noqa: BLE001
        return None
    if pts is S.EmptySet:
        return S.EmptySet
    if not isinstance(pts, sp.FiniteSet) or not all(p.is_number for p in pts):
        return None
    keep = _on_points(rel, var, pts)
    if keep is None:
        return None
    if not keep:
        return S.EmptySet
    n = sp.Dummy("n", integer=True)
    return sp.Union(*[sp.ImageSet(sp.Lambda(n, p + L * n), S.Integers) for p in keep])


def _on_points(rel, var, pts):
    """The points of the finite set `pts` where `rel` holds, each sign certified; a pole is no point
    of the set. None when a point cannot be decided (or there are too many)."""
    if len(pts) > LIMIT:
        return None
    e = rel.lhs - rel.rhs
    poles = _poles(e, var)
    keep = []
    try:
        for p in pts:
            if any(_certified(u.subs(var, p)) == 0 for u in poles):
                continue
            if _holds(type(rel), _certified(e.subs(var, p))):
                keep.append(p)
    except _Unsolved:
        return None
    return keep
