"""Solution sets of relations with an oscillating function, guarded (a CAS primitive: no decision logic).

SymPy 1.14 solves an inequality or a `!=` whose expression is periodic on ONE period and returns that
as the answer, also on a bounded domain (it solves on ℝ, cuts the line to [0, P), then intersects):
solveset(sin(x) > 0, x, Reals) = (0, pi); solveset(sin(x) > 0, x, Interval(-10, 10)) = (0, pi);
solveset(Ne(cos(x), 0), x, Reals) = [0, 2*pi) minus {pi/2, 3*pi/2}; solveset(tan(x) > 1, x, Reals) =
(pi/4, pi/2). A product with a periodic factor loses the periodic part: Ne(x*cos(x), 0) gave
(-oo, 0) ∪ (0, oo). None of these is a ConditionSet, so every caller took them for the answer: the
domain of log(sin x) was certified to be (0, pi), {} the solutions of x**2 = 49 with sin x > 0, 3 the
integers of [0, 10] with sin x > 0 (fourth audit, 1 Oct 2026, G2; measured on sympy 1.14.0). Its
equation sets lose roots too: sqrt(3)*sin(x) - cos(x) = 1 is 2*n*pi + pi/3 on ℝ and {pi/3} on
[0, 2*pi], without x = pi (measured; certify.trig found it first).

`exact_solveset` returns SymPy's set only when the relation has no oscillating function of the
variable. Otherwise the set is rebuilt and checked, or a ConditionSet (exact, unsolved) is returned:
  * on a bounded domain (its hull [inf, sup]): the zeros and the poles of lhs - rhs on the hull, each
    set solved as an equation on the hull and confirmed by a numeric root search there
    (`numeric_roots`: a root SymPy lacks makes the set unproved), cut the hull into cells; the sign
    on each cell and at each point is certified (`certified_sign`);
  * on an unbounded domain, an equation whose expression has a period P: its zeros on [0, P), checked
    the same way, repeated as n*P progressions;
  * an inequality or a `!=` on an unbounded domain, a non-periodic expression on an unbounded domain,
    or an expression with a function the cells do not cover (log, sqrt, floor, ...): a ConditionSet,
    which decides the membership of every point exactly.
"""
from __future__ import annotations

import mpmath as mp
import sympy as sp
from sympy import S
from sympy.functions.elementary.trigonometric import TrigonometricFunction

# the functions whose poles cut the cells: (pole function, the function whose zeros they are)
_POLES = ((sp.tan, sp.cos), (sp.sec, sp.cos), (sp.cot, sp.sin), (sp.csc, sp.sin))
_CELL_FUNCS = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc, sp.exp, sp.Abs)


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
    set rebuilt and checked, or a ConditionSet (module doc). SymPy is then only asked for equations on
    a bounded interval."""
    if not at_risk(rel, var):
        return sp.solveset(rel, var, domain)
    if isinstance(rel, sp.Expr):
        rel = sp.Eq(rel, 0)
    exact = None
    if isinstance(rel, sp.core.relational.Relational):
        try:
            exact = _rebuilt(rel, var, domain)
        except Exception:  # noqa: BLE001 - a failed rebuild proves nothing: the set stays unsolved
            exact = None
    return exact if exact is not None else sp.ConditionSet(var, rel, domain)


def _bounds(s_):
    """(lower, upper) bounds of a set, -oo/oo when not known: SymPy's inf/sup raise on a ConditionSet,
    which the domain carries for a condition it could not solve, so the parts are read one by one."""
    if isinstance(s_, sp.ConditionSet):
        return _bounds(s_.base_set)
    if isinstance(s_, sp.Complement):
        return _bounds(s_.args[0])
    if isinstance(s_, sp.Intersection):
        bs = [_bounds(a) for a in s_.args]
        return max((b[0] for b in bs), key=lambda v: sp.N(v, 30)), min((b[1] for b in bs), key=lambda v: sp.N(v, 30))
    if isinstance(s_, sp.Union):
        bs = [_bounds(a) for a in s_.args]
        return min((b[0] for b in bs), key=lambda v: sp.N(v, 30)), max((b[1] for b in bs), key=lambda v: sp.N(v, 30))
    try:
        lo, hi = s_.inf, s_.sup
    except Exception:  # noqa: BLE001
        return S.NegativeInfinity, S.Infinity
    ok = lo.is_number and hi.is_number and lo.is_extended_real and hi.is_extended_real
    return (lo, hi) if ok else (S.NegativeInfinity, S.Infinity)


def _hull(domain):
    """The closed bounded interval [lo, hi] that holds `domain`, as (lo, hi), or None."""
    try:
        lo, hi = _bounds(domain)
    except Exception:  # noqa: BLE001
        return None
    if lo.is_number and hi.is_number and lo.is_finite and hi.is_finite and (hi - lo).is_positive is True:
        return lo, hi
    return None


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
    """The expressions whose zeros are the points where `e` is undefined."""
    out = []
    for n in sp.preorder_traversal(e):
        if isinstance(n, sp.Pow) and var in n.base.free_symbols and n.exp.is_negative:
            out.append(n.base)
        for f, z in _POLES:
            if isinstance(n, f) and var in n.free_symbols:
                out.append(z(n.args[0]))
    return list(dict.fromkeys(out))


def _zeros_on(u, var, lo, hi, period=None):
    """The zeros of `u` on [lo, hi] as a list of exact numbers, when SymPy's finite set is confirmed
    by a numeric root search on [lo, hi] (each numeric root must be one of them), else None."""
    s = sp.solveset(sp.Eq(u, 0), var, sp.Interval(lo, hi))
    if s is not S.EmptySet and not isinstance(s, sp.FiniteSet):
        return None
    pts = [p for p in s if p.is_number]
    if len(pts) != len(s):
        return None
    n = 4000
    if period is not None:
        n = min(20000, max(n, int(400 * float((hi - lo) / period))))
    found = numeric_roots(u, var, sp.N(lo, 30), sp.N(hi, 30), n, closed=True)
    vals = [mp.mpf(str(sp.N(p, 30))) for p in pts]
    for q in found:
        if not any(abs(mp.mpf(q) - v) < mp.mpf("1e-6") for v in vals):
            return None
    return pts


def _sorted_unique(pts):
    keyed = sorted(((sp.N(p, 50), p) for p in pts), key=lambda t: t[0])
    out: list = []
    for k, p in keyed:
        if out and abs(k - out[-1][0]) < sp.Float("1e-40", 50):
            if sp.simplify(p - out[-1][1]) != 0:
                raise ValueError("breakpoints too close to order")
            continue
        out.append((k, p))
    return [p for _, p in out]


def _holds(op, s) -> bool:
    return {sp.StrictGreaterThan: s > 0, sp.GreaterThan: s >= 0, sp.StrictLessThan: s < 0,
            sp.LessThan: s <= 0, sp.Unequality: s != 0, sp.Equality: s == 0}[op]


def _sign(e, var, p):
    from ..equiv.numeric import NONREAL, certified_sign
    s = certified_sign(e.subs(var, p))
    if s is None or s == NONREAL:
        raise ValueError(f"sign undecided at {p}")
    return s


def _on_window(rel, var, lo, hi, period=None):
    """(the points of [lo, hi] where `rel` holds, as a set; the zeros; the poles), or None."""
    e = rel.lhs - rel.rhs
    if not _cells_supported(e, var):
        return None
    zeros = _zeros_on(e, var, lo, hi, period)
    if zeros is None:
        return None
    poles: list = []
    for u in _poles(e, var):
        z = _zeros_on(u, var, lo, hi, period)
        if z is None:
            return None
        poles += z
    poles = _sorted_unique(poles)
    zeros = [z for z in _sorted_unique(zeros) if not any(sp.simplify(z - q) == 0 for q in poles)]
    op = type(rel)
    if op is sp.Equality:
        return sp.FiniteSet(*zeros), zeros, poles
    edges = _sorted_unique([lo, hi] + zeros + poles)
    pieces: list = []
    for a, b in zip(edges[:-1], edges[1:]):
        s = _sign(e, var, (a + b) / 2)
        if s == 0:
            return None                       # a zero inside a cell: the zeros are not all known
        if _holds(op, s):
            pieces.append(sp.Interval.open(a, b))
    for p in edges:
        if any(sp.simplify(p - q) == 0 for q in poles):
            continue
        if _holds(op, _sign(e, var, p)):
            pieces.append(sp.FiniteSet(p))
    return (sp.Union(*pieces) if pieces else S.EmptySet), zeros, poles


def _finite_critical_points(e, var) -> bool:
    """Are the zeros of `e` and of what makes it undefined finitely many on ℝ (no progression)? With
    a progression among them SymPy's inequality solver keeps only the finite part: Ne(x*cos(x), 0)
    was (-oo, 0) ∪ (0, oo)."""
    for u in [e] + _poles(e, var) + [d for d in _denominators(e, var)]:
        try:
            z = sp.solveset(sp.Eq(u, 0), var, S.Reals)
        except Exception:  # noqa: BLE001
            return False
        if z.has(sp.ImageSet) or isinstance(z, sp.ConditionSet) or z.has(sp.ConditionSet):
            return False
    return True


def _denominators(e, var) -> list:
    from sympy.solvers.solvers import denoms
    try:
        return [d for d in denoms(e, var) if var in d.free_symbols]
    except Exception:  # noqa: BLE001
        return []


def _rebuilt(rel, var, domain):
    from sympy.calculus.util import periodicity
    e = rel.lhs - rel.rhs
    try:
        P = periodicity(e, var)
    except Exception:  # noqa: BLE001
        P = None
    if P is not None and not (P.is_number and P.is_positive is True):
        P = None
    if isinstance(domain, sp.FiniteSet) and all(p.is_number for p in domain):
        keep = _on_points(rel, var, domain)            # point by point
        if keep is not None:
            return sp.FiniteSet(*keep)
    if P is None and (isinstance(rel, sp.Equality) or _finite_critical_points(e, var)):
        # not periodic: SymPy does not cut it to one period, and with finitely many zeros and poles
        # its inequality solver sees every point where the sign can change (an equation's set,
        # progressions included, is SymPy's own: 1/sin(arccot(x) + arccot(2)) is defined off -2)
        return sp.solveset(rel, var, domain)
    hull = _hull(domain)
    if hull is not None:
        w = _on_window(rel, var, hull[0], hull[1], P)
        return None if w is None else sp.Intersection(w[0], domain)
    if P is None:
        return None
    discrete = _on_periodic_points(rel, var, domain, P)
    if discrete is not None:
        return discrete
    w = _on_window(rel, var, S.Zero, P, P)
    if w is None:
        return None
    if not isinstance(rel, sp.Equality):
        # an inequality or `!=` on an unbounded domain: its set on one whole period decides only
        # "nowhere" and "everywhere" (sin(x) > 2, cos(x) + 2 != 0); anything else is a union over
        # all periods, and ℝ minus progressions is a set no sampler draws from (SymPy leaves the
        # membership of a rational point symbolic): the ConditionSet decides each point exactly
        if w[0] is S.EmptySet:
            return S.EmptySet
        if w[0] == sp.Interval(0, P):
            return domain
        return None
    n = sp.Dummy("n", integer=True)
    pts = [z for z in w[1] if (z - P).is_negative is True]
    if not pts:
        return S.EmptySet
    return sp.Intersection(sp.Union(*[sp.ImageSet(sp.Lambda(n, p + P * n), S.Integers) for p in pts]), domain)


def continuity_set(expr, var, domain):
    """Where on `domain` the expression is continuous, for an expression the cells cover (sums,
    products, integer powers, exp, trigonometric functions, Abs: continuous except at their poles),
    or None. SymPy's continuous_domain solves the conditions of a trigonometric expression on one
    period: log(cos(x)) on [5, 8] gave [5, 2*pi) (the truth is [5, 5*pi/2)) and log(x*cos(x)) on
    [2, 3], undefined everywhere there, gave [2, 3] (measured 1 Oct 2026)."""
    if not _cells_supported(expr, var):
        return None
    poles = _poles(expr, var)
    if not poles:
        return domain
    holes = [sp.Ne(u, 0) for u in poles]
    out = domain
    for h in holes:
        s_ = exact_solveset(h, var, out)
        if isinstance(s_, sp.ConditionSet) or s_.has(sp.ConditionSet):
            return None
        out = s_
    return out


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
    from sympy.calculus.util import periodicity
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
        Pc = periodicity(c.lhs - c.rhs, s_.sym)
        rest = set_periods(s_.base_set)
        if Pc is None or rest is None or not (Pc.is_number and Pc.is_positive is True):
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
    """The set cut to [0, L), for a set `_set_periods` reads and a common period L of its parts: each
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
    of the set. None when the expression is not one the cells cover."""
    e = rel.lhs - rel.rhs
    if not _cells_supported(e, var):
        return None
    poles = _poles(e, var)
    keep = []
    for p in pts:
        if any(_sign(u, var, p) == 0 for u in poles):
            continue
        if _holds(type(rel), _sign(e, var, p)):
            keep.append(p)
    return keep


def numeric_roots(expr, var, lo, hi, n: int = 4000, closed: bool = False) -> list[str]:
    """Worker: real roots of expr on [lo, hi) ([lo, hi] when `closed`) found numerically (sign changes
    and near-zero minima of |expr|, refined, then confirmed with |expr| < 1e-20 at 40 digits).
    Evidence against a CAS solution set that missed a root; it proves nothing when it finds none."""
    f = sp.lambdify(var, expr, "mpmath")
    roots: list = []

    def real_val(t):
        try:
            v = f(t)
            if isinstance(v, mp.mpc):
                if abs(v.imag) > mp.mpf(10) ** -20 * max(1, abs(v.real)):
                    return None
                v = v.real
            v = mp.mpf(v)
            return v if mp.isfinite(v) else None
        except Exception:  # noqa: BLE001
            return None

    def confirm(t):
        with mp.workdps(40):
            v = real_val(t)
            return v is not None and abs(v) < mp.mpf(10) ** -20

    with mp.workdps(30):
        lo_, hi_ = mp.mpf(str(lo)), mp.mpf(str(hi))
        step = (hi_ - lo_) / n
        xs = [lo_ + step * k for k in range(n + (1 if closed else 0))]
        m = len(xs)
        vs = [real_val(t) for t in xs]
        seeds = []
        for k in range(m):
            v = vs[k]
            if v is None:
                continue
            if v == 0:
                seeds.append((xs[k], None))
                continue
            if k + 1 < m and vs[k + 1] is not None and v * vs[k + 1] < 0:
                seeds.append((xs[k], xs[k + 1]))
            if 0 < k < m - 1 and vs[k - 1] is not None and vs[k + 1] is not None \
                    and abs(v) <= abs(vs[k - 1]) and abs(v) <= abs(vs[k + 1]) and abs(v) < mp.mpf("1e-3"):
                seeds.append((xs[k], None))
        for a, b in seeds:
            try:
                with mp.workdps(40):
                    if b is None:
                        r = a if real_val(a) == 0 else mp.findroot(f, a)
                    else:
                        r = mp.findroot(f, (a, b), solver="anderson")
                if isinstance(r, mp.mpc):
                    if abs(r.imag) > mp.mpf(10) ** -15:
                        continue
                    r = r.real
            except Exception:  # noqa: BLE001
                continue
            inside = lo_ <= r <= hi_ if closed else lo_ <= r < hi_
            if inside and confirm(r) and not any(abs(r - q) < mp.mpf("1e-8") for q in roots):
                roots.append(r)
    return [mp.nstr(r, 25) for r in roots]
