"""Solution sets of relations with a trigonometric function, and of the exact classes below, exact or
unsolved (a CAS primitive: no decision logic).

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
  (iii) a product or quotient whose factors (as written, `together` then `fraction`) are each (i), (ii),
        (iv) or (v), with integer powers;
  (iv)  a polynomial in ONE strictly monotone function of a linear argument, g(h(a*x + b)) with h one of
        exp (with the constant powers c**x, c > 0, c != 1: c**(k*x) = (c**x)**k, all powers of one base
        read as powers of one generator), log, sinh, atan: the real roots r of g in the range of h, then
        the one solution of h(u) = r; log is undefined at and below its zero (no relation holds there);
  (v)   a same-frequency combination A*sin(u) + B*cos(u) + D (A, B, D exact numbers, u linear), read as
        R*sin(u + phi) + D with R = sqrt(A**2 + B**2), phi = atan2(B, A), then as (ii).
The readings of (iv) and (v) are checked symbolically (the rewritten expression minus the original is 0),
or the factor is no class. `class_solveset` gives these sets for any relation (round 4 of part d4b,
2 Oct 2026: exp(x) = 2, 4**x - 3*2**x + 2 = 0, sin x = cos x, sqrt(3) sin x - cos x = 1).
Round 5 (same day): SymPy's own set is no proof for a relation without a trigonometric function either
(solve and solveset agreeing certified 3**x = 2**x), so every relation in `var` goes through the classes,
which grew by
  (vii) A*c1**L1 - B*c2**L2 (positive constants, linear exponents): the logs give a linear equation;
  (viii) Abs and sign of polynomials: on the closed cells between the roots of their arguments they are
        +-P and +-1 (`_piecewise`);
  (ix)  a polynomial in var and ONE radical P**(1/n): the resultant eliminates it, each candidate is
        checked (`_sqrt_zeros`);
  (x)   a sum of c_j*log(P_j) and a constant: exponentiated where every P_j > 0 (`_logsum_sets`);
and an identity (numerator 0 over one denominator) holds wherever it is defined AS WRITTEN (the poles
of every written denominator, `_written_poles`). A log argument <= 0 or a negative radicand is outside
the domain on the whole cell (`_log_outside`).
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
    """The exact set of the classes in the module doc, or a ConditionSet: SymPy's own set of a relation
    out of the classes is no proof (solveset and solve agreeing on 3**x = 2**x proved nothing; round 5
    of part d4b, 2 Oct 2026). A relation with no `var` in it, or a conjunction, is left to SymPy only
    when it has no trigonometric function (`at_risk`): its truth does not depend on a solved set."""
    if var not in getattr(rel, "free_symbols", set()):
        return sp.solveset(rel, var, domain)
    if isinstance(rel, (sp.And, sp.Or)):
        parts = [exact_solveset(a, var, domain) for a in rel.args]
        if any(isinstance(q, sp.ConditionSet) or q.has(sp.ConditionSet) for q in parts):
            return sp.ConditionSet(var, rel, domain)
        return sp.Intersection(*parts) if isinstance(rel, sp.And) else sp.Union(*parts)
    if isinstance(rel, sp.Expr):
        rel = sp.Eq(rel, 0)
    exact = None
    if isinstance(rel, sp.core.relational.Relational):
        try:
            exact = _rebuilt(rel, var, domain)
        except Exception:  # noqa: BLE001 - not exact (a class it is not, too many points, ...): unsolved
            exact = None
    return exact if exact is not None else sp.ConditionSet(var, rel, domain)


def class_solveset(rel, var, domain=S.Reals):
    """The exact set of `rel` when it is of the classes in the module doc, whether it has a trigonometric
    function or not (exp(x) = 2, 4**x - 3*2**x + 2 = 0, log(x)**2 = log(x)); None otherwise. For the
    completeness of a solution list (certify.algebra): SymPy's own finite set is no proof."""
    if isinstance(rel, sp.Expr):
        rel = sp.Eq(rel, 0)
    if rel is sp.false:
        # SymPy decided the relation itself (Eq(3**x + 2**x, 0): a sum of positive terms), also when
        # it was rebuilt in the sandbox worker: no point holds it
        return S.EmptySet
    if not isinstance(rel, sp.core.relational.Relational):
        return None
    try:
        return _rebuilt(rel, var, domain)
    except Exception:  # noqa: BLE001
        return None


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


def _linear(arg, var):
    """(a, b) with arg = a*var + b, a != 0, exact numbers; or None."""
    try:
        p = sp.Poly(arg, var)
    except sp.PolynomialError:
        return None
    if p.degree() != 1 or not p.domain.is_Exact or p.free_symbols_in_domain:
        return None
    return p.coeff_monomial(var), p.coeff_monomial(1)


def _combo_parts(base, var):
    """(v): A*sin(u) + B*cos(u) + D with one linear u (A, B, D exact numbers, A and B not 0), read as
    R*sin(u + phi) + D with R = sqrt(A**2 + B**2), phi = atan2(B, A): (sin, a, b + phi, g) as in (ii).
    The rewriting is checked symbolically. sin x = cos x and sqrt(3) sin x - cos x = 1 are this class."""
    atoms = {n for n in base.atoms(TrigonometricFunction) if var in n.free_symbols}
    if not atoms or any(type(n) not in (sp.sin, sp.cos) for n in atoms) or len({n.args[0] for n in atoms}) != 1:
        return None
    u = next(iter(atoms)).args[0]
    ab = _linear(u, var)
    if ab is None:
        return None
    sv, cv = sp.Dummy("s"), sp.Dummy("c")
    bt = sp.expand(base.xreplace({sp.sin(u): sv, sp.cos(u): cv}))
    if not bt.free_symbols <= {sv, cv}:
        return None
    try:
        q = sp.Poly(bt, sv, cv)
    except sp.PolynomialError:
        return None
    if q.total_degree() != 1 or not q.domain.is_Exact or q.free_symbols_in_domain:
        return None
    A, B, D = q.coeff_monomial(sv), q.coeff_monomial(cv), q.coeff_monomial(1)
    if A == 0 or B == 0:
        return None
    R, phi = sp.sqrt(A ** 2 + B ** 2), sp.atan2(B, A)
    if sp.simplify(sp.expand_trig(R * sp.sin(u + phi) + D) - base) != 0:
        return None
    t = sp.Dummy("t")
    return sp.sin, ab[0], ab[1] + phi, sp.Poly(R * t + D, t)


_MONO = (sp.exp, sp.log, sp.sinh, sp.atan)


def _mono_parts(base, var):
    """(iv): g(h(a*x + b)) with h strictly monotone (exp and constant powers a**x, log, sinh, atan),
    g a polynomial: (h, a, b, g). Powers of one base (4**x, 2**(2x), exp(3x)) are read as powers of one
    generator t = exp(c*x) (a negative power is cleared by t**m > 0, which changes no zero or sign); the
    rewriting is checked symbolically."""
    nodes = [n for n in sp.preorder_traversal(base)
             if var in n.free_symbols and (isinstance(n, _MONO) or (isinstance(n, sp.Pow) and var in n.exp.free_symbols))]
    if not nodes:
        return None
    kinds = {type(n) for n in nodes}
    t = sp.Dummy("t", positive=True)           # exp and c**x take positive values only
    if kinds <= {sp.exp, sp.Pow}:
        exps = {}
        for n in nodes:
            if isinstance(n, sp.Pow):
                if not (n.base.is_number and n.base.is_positive is True and n.base != 1):
                    return None
                ex = n.exp * sp.log(n.base)
            else:
                ex = n.args[0]
            ab = _linear(sp.expand(ex), var)
            if ab is None:
                return None
            exps[n] = ab
        c1 = next(iter(exps.values()))[0]
        ratios = {}
        for n, (c, _) in exps.items():
            q = sp.simplify(sp.expand_log(c / c1, force=True))
            if not isinstance(q, sp.Rational):
                return None
            ratios[n] = q
        L = sp.ilcm(*[q.q for q in ratios.values()]) if len(ratios) > 1 else ratios[next(iter(ratios))].q
        c0 = c1 / L
        ks = {n: int(ratios[n] * L) for n in exps}
        m = max(0, -min(ks.values()))
        bt = sp.expand(base.xreplace({n: sp.exp(exps[n][1]) * t ** ks[n] for n in exps}) * t ** m)
        if bt.free_symbols != {t}:
            return None
        g = sp.Poly(bt, t)
        back = bt.subs(t, sp.exp(c0 * var)) - base * sp.exp(m * c0 * var)
        if sp.simplify(sp.expand(sp.powsimp(back.rewrite(sp.exp)))) != 0:
            return None
        return sp.exp, c0, S.Zero, g
    if len(kinds) != 1 or len(set(nodes)) != 1:
        return None
    (h,) = kinds
    if h is sp.Pow:
        return None
    n = nodes[0]
    ab = _linear(n.args[0], var)
    if ab is None:
        return None
    # for log, sinh, atan the generator carries no assumption, and the reading is checked by substituting
    # back: a positive t made Max(t, 0) -> t and sqrt(t**2) -> t, so Max(log x, 0) = 0 gave {1} (the truth
    # is (0, 1]) and sqrt(log(x)**2) = 1 gave {e} (review of round 5, B1)
    tl = sp.Dummy("t")
    bt = base.xreplace({n: tl})
    if bt.free_symbols != {tl}:
        return None
    try:
        g = sp.Poly(bt, tl)
    except sp.PolynomialError:
        return None
    if not g.domain.is_Exact or g.free_symbols_in_domain or sp.simplify(g.as_expr().subs(tl, n) - base) != 0:
        return None
    return h, ab[0], ab[1], g


def _log_of_term(term, var):
    """(sign, L) with term = sign*exp(L), L linear in `var` with exact coefficients, for a product of a
    rational number, positive constants and powers c**(a*x + b) (c > 0 constant, exp included); or
    None. The reading is checked symbolically."""
    c, rest = term.as_coeff_Mul()
    if not isinstance(c, sp.Rational) or c == 0:
        return None
    L = sp.log(abs(c))
    for f in sp.Mul.make_args(rest):
        if var not in f.free_symbols:
            if not (f.is_number and f.is_positive is True):
                return None
            L += sp.log(f)
        elif isinstance(f, sp.exp):
            L += f.args[0]
        elif isinstance(f, sp.Pow) and f.base.is_number and f.base.is_positive is True and var not in f.base.free_symbols:
            L += f.exp * sp.log(f.base)
        else:
            return None
    L = sp.expand(L)
    if var in sp.diff(L, var, 2).free_symbols or sp.diff(L, var, 2) != 0:
        return None                                  # not linear in var
    sign = 1 if c > 0 else -1
    if sp.simplify((term - sign * sp.exp(L)).rewrite(sp.exp)) != 0:
        return None
    return sign, L


def _ratio_zeros(base, var):
    """(vii) two terms, each a constant times powers of positive constants with linear exponents:
    A*c1**(a*x + b) - B*c2**(c*x + d). Where both terms have one sign the zeros are those of the
    logarithms' difference, a linear function (log is strictly increasing): 3**x = 2**x at x = 0 only.
    With the same sign the sum has none. None when not this class; raise _Unsolved for an identity."""
    terms = sp.Add.make_args(base)
    if len(terms) != 2 or not any(var in t.free_symbols for t in terms):
        return None
    parts = [_log_of_term(t, var) for t in terms]
    if any(p_ is None for p_ in parts):
        return None
    (s1, L1), (s2, L2) = parts
    if s1 == s2:
        return []                                    # two positive (or two negative) terms: no zero
    d = sp.expand(L1 - L2)
    a, b = sp.diff(d, var), d.subs(var, 0)
    if var in a.free_symbols or sp.expand(d - (a * var + b)) != 0:
        return None
    if _certified(a) == 0:                           # log(4)*x - 2*log(2)*x: no x after all
        if _certified(b) == 0:
            raise _Unsolved(f"an identity: {base}")
        return []
    return [(-b / a, S.Zero)]


def _mono_zeros(h, a, b, g):
    """The zeros (points) of g(h(a*x + b)) and the points where it is undefined (log of 0)."""
    zeros = []
    for r_ in _real_roots(g):
        if h is sp.exp:
            if _certified(r_) <= 0:
                continue                       # exp takes no value <= 0
            u = sp.log(r_)
        elif h is sp.log:
            u = sp.exp(r_)
        elif h is sp.sinh:
            u = sp.asinh(r_)
        else:                                  # atan: values in (-pi/2, pi/2)
            if _certified(sp.pi / 2 - abs(r_)) <= 0:
                continue
            u = sp.tan(r_)
        zeros.append(((u - b) / a, S.Zero))
    poles = []          # log of 0: `_breaks` makes it an edge, `_log_outside` leaves it out of the set
    return zeros, poles


def _factor_sets(base, var):
    """(zeros, poles, period) of one factor: zeros and poles as progressions in `var`, the period None
    when the factor is not periodic; or raise _Unsolved."""
    roots = _poly_roots(base, var)
    if roots is not None:
        return [(r_, S.Zero) for r_ in roots], [], None
    parts = _trig_parts(base, var) or _combo_parts(base, var)
    if parts is not None:
        f, a, b, g = parts
        zeros = []
        for r_ in _real_roots(g):
            zeros += [((u0 - b) / a, step / abs(a)) for u0, step in _u_solutions(f, r_)]
        poles = []
        if f in (sp.tan, sp.sec):
            poles = [((sp.pi / 2 - b) / a, sp.pi / abs(a))]
        elif f in (sp.cot, sp.csc):
            poles = [((-b) / a, sp.pi / abs(a))]
        return zeros, poles, (sp.pi if f in (sp.tan, sp.cot) else 2 * sp.pi) / abs(a)
    mono = _mono_parts(base, var)
    if mono is not None:
        return (*_mono_zeros(*mono), None)
    ratio = _ratio_zeros(base, var)
    if ratio is not None:
        return ratio, [], None
    for fn in (_abs_zeros, _sqrt_zeros, _logsum_sets):
        got = fn(base, var)
        if got is not None:
            return got[0], got[1], None
    raise _Unsolved(f"not an exact class: {base}")


def _poly_of(e, var):
    """Poly of e in var with exact coefficients and no other symbol, or None."""
    if e.free_symbols - {var}:
        return None
    try:
        q = sp.Poly(e, var)
    except sp.PolynomialError:
        return None
    if not q.domain.is_Exact or q.free_symbols_in_domain:
        return None
    return q


def _in_open(c, a, b) -> bool:
    return (a == -sp.oo or _certified(c - a) > 0) and (b == sp.oo or _certified(b - c) > 0)


def _abs_zeros(base, var):
    """(viii) a polynomial in var and in |P_k| (P_k polynomials): between consecutive real roots of the
    P_k each |P_k| is +P_k or -P_k (its sign at one point of the cell), so base is a polynomial there,
    whose real roots in the open cell are exact; the roots of the P_k are checked one by one.
    (zeros, []) or None; raise _Unsolved when base vanishes on a whole cell."""
    atoms = sorted({n for n in base.atoms(sp.Abs) if var in n.free_symbols}, key=sp.default_sort_key)
    if not atoms:
        return None
    ds = [sp.Dummy(f"a{i}") for i in range(len(atoms))]
    bt = base.xreplace(dict(zip(atoms, ds)))
    if bt.free_symbols - set(ds) - {var}:
        return None
    try:
        q = sp.Poly(bt, var, *ds)
    except sp.PolynomialError:
        return None
    if not q.domain.is_Exact or q.free_symbols_in_domain:
        return None
    args = [_poly_of(a.args[0], var) for a in atoms]
    if any(a is None for a in args):
        return None
    cuts = _sorted_unique([r_ for a in args for r_ in _real_roots(a)])
    edges = [S.NegativeInfinity] + cuts + [S.Infinity]
    zeros = []
    for a, b in zip(edges[:-1], edges[1:]):
        mid = (a + b) / 2 if a.is_finite and b.is_finite else (b - 1 if b.is_finite else a + 1 if a.is_finite else S.Zero)
        signs = [_certified(at.args[0].subs(var, mid)) for at in atoms]
        cell = sp.expand(bt.xreplace({d: sg * at.args[0] for d, sg, at in zip(ds, signs, atoms)}))
        pc = _poly_of(cell, var)
        if pc is None:
            return None
        if pc.is_zero:
            raise _Unsolved(f"zero on a whole cell: {base}")
        zeros += [r_ for r_ in _real_roots(pc) if _in_open(r_, a, b)]
    zeros += [c for c in cuts if _certified(base.subs(var, c)) == 0]
    return [(z, S.Zero) for z in zeros], []


def _roots_of(e, var):
    return [n for n in sp.preorder_traversal(e) if isinstance(n, sp.Pow) and var in n.base.free_symbols
            and n.exp.is_Rational and not n.exp.is_Integer]


def _sqrt_zeros(base, var):
    """(ix) a polynomial in var and in r = P**(1/n) for ONE polynomial radicand P (r**n = P): every
    zero is a root of the resultant of base(r) and r**n - P in r (eliminating r loses none); each
    candidate is kept only when P >= 0 there (the root real, as written) and base is certified 0 there.
    sqrt(x + 4) = x - 2 → {5}. (zeros, []) or None."""
    rad = _roots_of(base, var)
    if not rad:
        return None
    Ps = {n.base for n in rad}
    if len(Ps) != 1 or any(n.exp < 0 for n in rad):
        return None
    (P,) = Ps
    if _poly_of(P, var) is None:
        return None
    n_ = sp.ilcm(*[n.exp.q for n in rad]) if len(rad) > 1 else rad[0].exp.q
    r = sp.Dummy("r")
    bt = base.xreplace({n: r ** int(n.exp * n_) for n in rad})
    if bt.free_symbols - {r, var}:
        return None
    try:
        q = sp.Poly(bt, r, var)
    except sp.PolynomialError:
        return None
    if not q.domain.is_Exact or q.free_symbols_in_domain:
        return None
    if sp.simplify(bt.subs(r, P ** sp.Rational(1, n_)) - base) != 0:
        return None
    res = sp.resultant(sp.Poly(bt, r), sp.Poly(r ** n_ - P, r))
    cand = _poly_of(sp.expand(res), var)
    if cand is None:
        return None
    if cand.is_zero:
        raise _Unsolved(f"eliminated to an identity: {base}")
    zeros = []
    for c in _real_roots(cand):
        if _certified(P.subs(var, c)) < 0:
            # not real (even index), or a convention (odd index, part d4a): a window holding it is cut
            # off or left unsolved by `_log_outside`, so it is no zero of this reading
            continue
        if _certified(base.subs(var, c)) == 0:
            zeros.append((c, S.Zero))
    return zeros, []


def _logsum_sets(base, var):
    """(x) sum of c_j*log(P_j) (c_j rational, P_j polynomials) and a constant R: where every P_j > 0
    it is (1/q)*log(N/D) + R with N/D the product of the P_j**(q*c_j), so its zeros there are the roots
    of N - exp(-q*R)*D (log is one-to-one); the roots of the P_j are poles (log of 0). (zeros, poles) or
    None. log(x - 1) + log(x - 3) = log(3): x = 4 (x = 0 is outside)."""
    logs, R = [], S.Zero
    for t in sp.Add.make_args(base):
        if var not in t.free_symbols:
            R += t
            continue
        c, rest = t.as_coeff_Mul()
        if not (isinstance(rest, sp.log) and isinstance(c, sp.Rational)):
            return None
        pj = _poly_of(rest.args[0], var)
        if pj is None:
            return None
        logs.append((c, rest.args[0]))
    if not logs:
        return None
    qd = sp.ilcm(*[c.q for c, _ in logs]) if len(logs) > 1 else logs[0][0].q
    N, D = S.One, S.One
    for c, Pj in logs:
        m = int(c * qd)
        if m > 0:
            N *= Pj ** m
        else:
            D *= Pj ** (-m)
    T = sp.exp(-qd * R)
    if _certified(T) <= 0:
        return None
    cand = _poly_of(sp.expand(N - T * D), var)
    if cand is None:
        return None
    if cand.is_zero:
        raise _Unsolved(f"an identity where defined: {base}")
    # a root where a P_j <= 0 is no zero: `_log_outside` cuts it (and every cell there) wherever zeros are read
    zeros = [(c, S.Zero) for c in _real_roots(cand)]
    poles = [(r_, S.Zero) for _, Pj in logs for r_ in _real_roots(_poly_of(Pj, var))]
    return zeros, poles


def _structure(e, var):
    """(zeros, poles, periods) of e as progressions: e = (product of factors) / (product of factors),
    each factor an integer power of a base of the classes (i), (ii), (iv), (v); raise _Unsolved otherwise.
    `periods` is
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
                base = arg                     # exp(x) or 2**x as a factor: classified whole
            z, p, per = _factor_sets(base, var)
            (zeros if is_num else poles).extend(z)
            poles.extend(p)
            if per is None:
                periods = None
            elif periods is not None:
                periods.append(per)
    return zeros, poles, periods


def _on(progs, lo, hi) -> list:
    """The points of the progressions in [lo, hi], exact, each membership certified."""
    out = []
    flo, fhi = float(sp.N(lo, 30)), float(sp.N(hi, 30))
    for p0, step in progs:
        if step == 0:
            cand = [p0]
        elif not (lo.is_finite and hi.is_finite):
            raise _Unsolved("a progression on an unbounded window")
        else:
            fp, fs = float(sp.N(p0, 30)), float(sp.N(step, 30))
            n0, n1 = math.floor((flo - fp) / fs) - 1, math.ceil((fhi - fp) / fs) + 1
            if n1 - n0 > LIMIT:
                raise _Unsolved("too many points on the window")
            cand = [p0 + step * k for k in range(n0, n1 + 1)]
        for c in cand:
            if (lo == -sp.oo or _certified(c - lo) >= 0) and (hi == sp.oo or _certified(hi - c) >= 0):
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


def _real_sign(e):
    """The certified sign of a real number; raise _Unsolved when undecided or not real (the cells where
    a log is not real are cut off by `_log_outside` first: a sign read at one point says nothing there,
    log(x)**2 is the real -pi**2 at x = -1 and not real at x = -2)."""
    from ..equiv.numeric import NONREAL, certified_sign
    s_ = certified_sign(e)
    if s_ is None or s_ == NONREAL:
        raise _Unsolved(f"sign undecided or not real: {e}")
    return s_


def _log_outside(e, var):
    """A test of a point: is it outside the real domain of `e`, a log argument <= 0 or an even root's
    radicand < 0 there? The classes have only polynomial arguments and radicands, whose real roots are
    edges of every cell (`_breaks`): the sign at one point of a cell is the sign on the whole cell."""
    args = [n.args[0] for n in e.atoms(sp.log) if var in n.free_symbols]
    rads = [n.base for n in _roots_of(e, var) if n.exp.q % 2 == 0]
    odd = [n.base for n in _roots_of(e, var) if n.exp.q % 2 == 1]

    if _PRINCIPAL[0]:
        rads = rads + odd

    # an odd root of a negative number as written is a convention (part d4a): `_convention_free` leaves
    # such a window unsolved before any cell is read (under `principal_solveset` it is not real)

    def outside(pt) -> bool:
        return any(_certified(a.subs(var, pt)) <= 0 for a in args) or any(
            _certified(r_.subs(var, pt)) < 0 for r_ in rads)
    return outside


_PRINCIPAL = [False]       # set by `principal_solveset`: an odd root of a negative number is not real


def principal_solveset(rel, var, domain=S.Reals):
    """`exact_solveset` under the principal reading of a written odd root: x**(1/3) at x < 0 is not real
    (SymPy's own reading). For a caller that takes both readings itself (steps._solved_both_readings);
    every other caller gets no set where the reading is a convention."""
    _PRINCIPAL[0] = True
    try:
        return exact_solveset(rel, var, domain)
    finally:
        _PRINCIPAL[0] = False


def _convention_free(e, var, lo, hi) -> None:
    """Raise _Unsolved when a written odd root of `e` has a negative radicand somewhere on [lo, hi]:
    its value there is a convention (principal or real root, part d4a), so no set is exact. x**(2/3) = 1
    is {1} on x >= 0 and no set on the reals."""
    odd = [n.base for n in _roots_of(e, var) if n.exp.q % 2 == 1]
    if not odd or _PRINCIPAL[0]:
        return
    for r_ in odd:
        q = _poly_of(r_, var)
        if q is None:
            raise _Unsolved(f"an odd root of no polynomial: {r_}")
        inner = [c for c in _sorted_unique(_on([(c, S.Zero) for c in _real_roots(q)], lo, hi)) if c != lo and c != hi]
        edges = [lo] + inner + [hi]
        pts = [p_ for p_ in edges if p_.is_finite] + [
            (a + b) / 2 if a.is_finite and b.is_finite else (b - 1 if b.is_finite else a + 1 if a.is_finite else S.Zero)
            for a, b in zip(edges[:-1], edges[1:])]
        if any(_certified(r_.subs(var, p_)) < 0 for p_ in pts):
            raise _Unsolved("an odd root of a negative number: a convention (part d4a)")


def _restricted(e, var) -> bool:
    """Has `e` points where it is not real (a log, an even root of `var`)?"""
    return any(var in n.free_symbols for n in e.atoms(sp.log)) or bool(_roots_of(e, var))


def _breaks(e, var) -> list:
    """The points where the formula of `e` changes or its domain ends: the real roots of the arguments
    of Abs and log and of the even roots' radicands (polynomials, or raise _Unsolved)."""
    out = []
    for a in ([n.args[0] for n in e.atoms(sp.Abs, sp.sign, sp.log) if var in n.free_symbols]
              + [n.base for n in _roots_of(e, var)]):
        q = _poly_of(a, var)
        if q is None:
            raise _Unsolved(f"a cut that is no polynomial: {a}")
        out += _real_roots(q)
    return out


def _mid(a, b):
    return (a + b) / 2 if a.is_finite and b.is_finite else (b - 1 if b.is_finite else a + 1 if a.is_finite else S.Zero)


def _cell_sub(atoms, var, mid) -> dict:
    """Each Abs, sign, Max, Min of `atoms` as its formula on the open cell holding `mid` (their arguments keep
    their sign there: the cells are cut at their roots)."""
    sub = {}
    for at in atoms:
        if isinstance(at, (sp.Max, sp.Min)):  # Max(A, B) is A where A > B on the cell
            sg = _certified((at.args[0] - at.args[1]).subs(var, mid))
            sub[at] = at.args[0] if (sg > 0) == isinstance(at, sp.Max) else at.args[1]
            continue
        sg = _certified(at.args[0].subs(var, mid))
        sub[at] = sg * at.args[0] if isinstance(at, sp.Abs) else sp.Integer(sg)
    return sub


def _on_cell(f, sub):
    """`f` with every atom of `sub` replaced, nested ones too (|x - |x||)."""
    for _ in range(8):
        g = f.xreplace(sub)
        if g == f:
            return g
        f = g
    return f


def _piecewise(rel, var, lo, hi):
    """(xi) Abs and sign of polynomials: between consecutive real roots of their arguments each |P| is
    +P or -P and sign(P) is +1 or -1 (the sign at one point of the cell), and on the CLOSED cell the
    expression equals the one with them replaced (at a root both sides are 0, or the cell's own sign
    where the root is a window end); its set there is solved as any other. |2x - 3| = 5 → {-1, 4};
    |2x - 3| = 2x - 3 → [3/2, oo); the real cube root sign(x)*|x|**(1/3). None when `rel` has neither."""
    e = rel.lhs - rel.rhs
    # sqrt(A**2) is |A| wherever A is real; where it is not (log of a negative number) the cell is outside
    e = e.replace(lambda n: isinstance(n, sp.Pow) and n.exp == S.Half and isinstance(n.base, sp.Pow)
                  and n.base.exp == 2 and var in n.free_symbols, lambda n: sp.Abs(n.base.base))
    atoms = sorted({n for n in e.atoms(sp.Abs, sp.sign, sp.Max, sp.Min) if var in n.free_symbols},
                   key=sp.default_sort_key)
    if not atoms:
        return None
    if any(isinstance(at, (sp.Max, sp.Min)) and len(at.args) != 2 for at in atoms):
        raise _Unsolved("Max or Min of more than two")
    rel = type(rel)(e, 0)
    cuts = []
    for at in atoms:
        arg = at.args[0] if isinstance(at, (sp.Abs, sp.sign)) else at.args[0] - at.args[1]
        q = _poly_of(arg, var)
        if q is not None:
            cuts += [(r_, S.Zero) for r_ in _real_roots(q)]
        else:                                  # |log x|: the zeros, poles and domain edges of the argument
            z, p_, _ = _structure(arg, var)
            cuts += z + p_ + [(c, S.Zero) for c in _breaks(arg, var)]
    # The cells are cut where the domain ends too: at the roots of every log argument and radicand (round 7:
    # a cell whose MIDPOINT was outside was dropped whole, |x|*log(x - 1) = 0 lost x = 2 on (0, oo) and
    # |x| = sqrt(2x + 1) lost 1 - sqrt(2) on (-oo, 0)), and at the written poles. An argument, radicand or
    # denominator with Abs/sign/Max/Min in it is read on each cell, where it is of the classes (sign(x) is
    # +-1 there; x - |x| is 0 on [0, oo), undefined on that whole cell: 1/(x - |x|) = -1/2 → {-1})
    dep_cuts = []
    for a in [n.args[0] for n in e.atoms(sp.log) if var in n.free_symbols] + [n.base for n in _roots_of(e, var)]:
        if a.has(*atoms):
            dep_cuts.append(a)
            continue
        q = _poly_of(a, var)
        if q is None:
            raise _Unsolved(f"a cut that is no polynomial: {a}")
        cuts += [(r_, S.Zero) for r_ in _real_roots(q)]
    dep_dens = list(dict.fromkeys(n.base for n in sp.preorder_traversal(e) if isinstance(n, sp.Pow)
                                  and n.exp.is_number and n.exp.is_negative and n.base.has(*atoms)))
    outside = _log_outside(e, var)
    bad = _sorted_unique(_on(_written_poles(e, var, skip=atoms), lo, hi))
    inner = [c for c in _sorted_unique(_on(cuts, lo, hi) + bad) if c != lo and c != hi]
    edges = [lo] + inner + [hi]
    if dep_cuts or dep_dens:
        more, more_bad = [], []
        for a, b in zip(edges[:-1], edges[1:]):
            sub = _cell_sub(atoms, var, _mid(a, b))
            for f in dep_cuts:
                q = _poly_of(_on_cell(f, sub), var)
                if q is None:
                    raise _Unsolved(f"a cut that is no polynomial on a cell: {f}")
                if not q.is_zero:
                    more += [r_ for r_ in _real_roots(q) if _in_open(r_, a, b)]
            for f in dep_dens:
                fc = _on_cell(f, sub)
                if _identity(fc, var):
                    continue                   # 0 on the whole cell: the cell is dropped below
                z, p_, _ = _structure(fc, var)
                more_bad += [c for c in _on(z + p_, a, b) if _in_open(c, a, b)]
        bad = _sorted_unique(bad + more_bad)
        inner = [c for c in _sorted_unique(inner + more + more_bad) if c != lo and c != hi]
        edges = [lo] + inner + [hi]
    cells = list(zip(edges[:-1], edges[1:]))
    # a written odd root of a negative number: its value is a convention (part d4a), on a cell whose relation
    # folds to True or False too ((x + |x|)*x**(1/3) = 0 is (-oo, 0] read with the real root, {0} on the
    # principal branch; round 7, YO-2). Every radicand keeps its sign on each open cell (cut at its roots)
    odd = [n.base for n in _roots_of(e, var) if n.exp.q % 2 == 1]
    if odd and not _PRINCIPAL[0]:
        pts = [p_ for p_ in edges if p_.is_finite] + [_mid(a, b) for a, b in cells]
        if any(_certified(r_.subs(var, p_)) < 0 for r_ in odd for p_ in pts):
            raise _Unsolved("an odd root of a negative number: a convention (part d4a)")
    pieces = []
    for a, b in cells:
        mid = _mid(a, b)
        if outside(mid):
            continue
        sub = _cell_sub(atoms, var, mid)
        if any(_identity(_on_cell(f, sub), var) for f in dep_dens):
            continue                           # a written denominator 0 on the whole cell: undefined there
        # on the OPEN cell the arguments keep their sign: sign(P) is +-1 there only (sign(0) = 0, review
        # of round 5, B2: sign(x) = 0 gave {}); the relation with them replaced may fold to True or False,
        # and then it no longer shows where the written expression is undefined (B3: |x|/x = 1 gave
        # [0, oo), |x|tan x = x tan x on [0, 3] held pi/2): those points are cut out of every cell
        cell = type(rel)(e.xreplace(sub), 0)
        if cell is sp.true:
            got = sp.Interval.open(a, b)
        elif cell is sp.false:
            got = S.EmptySet
        else:
            got = sp.Intersection(_on_window(cell, var, a, b)[0], sp.Interval.open(a, b))
        pieces.append(got)
    for p_ in edges:                           # each cut point and window end on `rel` as written
        if not p_.is_finite or _same(p_, bad) or outside(p_):
            continue
        if any(_certified(f.subs(var, p_)) == 0 for f in dep_dens):
            continue
        val = e.subs(var, p_)
        if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            continue
        if _holds(type(rel), _real_sign(val)):
            pieces.append(sp.FiniteSet(p_))
    return sp.Union(*pieces) if pieces else S.EmptySet


def _identity(e, var) -> bool:
    """Is e identically 0 where it is defined (its numerator, written over one denominator, is 0)?"""
    try:
        return sp.expand(sp.fraction(sp.together(e))[0]) == 0
    except Exception:  # noqa: BLE001
        return False


def _written_poles(e, var, skip=()) -> list:
    """The points where a denominator AS WRITTEN vanishes or is undefined: the zeros and poles of the base
    of every negative power. Combining the terms may cancel them: (2*x**2 + 1)/(x**2 - 5) -
    (2 + 1/x**2)/(1 - 5/x**2) is 0 over one denominator, but undefined at 0 and +-sqrt(5). A base with one
    of `skip` in it (Abs, sign, Max, Min) is left to `_piecewise`, which reads it on each cell."""
    out = []
    for n in sp.preorder_traversal(e):
        if isinstance(n, sp.Pow) and n.exp.is_number and n.exp.is_negative and var in n.base.free_symbols:
            if skip and n.base.has(*skip):
                continue
            z, p_, _ = _structure(n.base, var)
            out += z + p_
    for n in e.atoms(sp.tan, sp.cot, sp.sec, sp.csc):         # and the poles of these, as written
        if var in n.free_symbols:
            f = sp.cos if isinstance(n, (sp.tan, sp.sec)) else sp.sin
            out += _structure(f(n.args[0]), var)[0]
    return out


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
    pw = _piecewise(rel, var, lo, hi)
    if pw is not None:
        return pw, [], []
    ident = _identity(e, var)              # x**2 - 5*x - 14 = (x - 7)*(x + 2): every defined point
    if ident:
        # over one denominator an identity is 0/1: its poles are those of the denominators as written
        zp, pp = [], _written_poles(e, var)
    else:
        zp, pp, _ = _structure(e, var)     # `together` keeps every denominator (it cancels nothing)
    poles = _sorted_unique(_on(pp, lo, hi))
    outside = _log_outside(e, var)
    zeros = [z for z in _sorted_unique(_on(zp, lo, hi)) if not _same(z, poles) and not outside(z)]
    op = type(rel)
    _convention_free(e, var, lo, hi)
    if op is sp.Equality and not ident:
        return sp.FiniteSet(*zeros), zeros, poles
    cuts = _on([(c, S.Zero) for c in _breaks(e, var)], lo, hi)
    ends = [q for q in (lo, hi) if q.is_finite]
    edges = _sorted_unique(ends + zeros + poles + cuts)
    edges = ([lo] if not lo.is_finite else []) + edges + ([hi] if not hi.is_finite else [])
    pieces: list = []
    for a, b in zip(edges[:-1], edges[1:]):
        mid = (a + b) / 2 if a.is_finite and b.is_finite else (b - 1 if b.is_finite else a + 1 if a.is_finite else S.Zero)
        if outside(mid):
            continue                                    # a log is not real on this cell: nothing holds
        s_ = 0 if ident else _real_sign(e.subs(var, mid))
        if s_ == 0 and not ident:
            raise _Unsolved("a zero inside a cell")       # cannot happen with the classes: refuse
        if _holds(op, s_):
            pieces.append(sp.Interval.open(a, b))
    for p in edges:
        if not p.is_finite or _same(p, poles) or outside(p):
            continue
        s_ = 0 if ident or _same(p, zeros) else _real_sign(e.subs(var, p))
        if _holds(op, s_):
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


def _parametric(rel, var, domain):
    """(xii) a polynomial in `var` whose coefficients hold other symbols (parameters) and whose leading
    coefficient is a nonzero number: an equation's set is its roots (`roots`, all of them: multiplicities
    summing to the degree), each real by the symbols' assumptions or dropped when certainly not real; an
    inequality or `!=` only of degree 1 (one root, the side read from the leading coefficient's sign).
    x - a = 1 → {a + 1}; (x - 1)(x - a) = 0 → {1, a}; x**2 = a, a >= 0 → {-sqrt(a), sqrt(a)}; x > b →
    (b, oo). Raise _Unsolved otherwise (a root whose realness depends on the parameter, degree 2
    inequalities, a leading coefficient that may vanish)."""
    e = sp.expand(rel.lhs - rel.rhs)
    if _roots_of(e, var) and isinstance(rel, sp.Equality):
        return _parametric_radical(e, var, domain)
    try:
        q = sp.Poly(e, var)
    except sp.PolynomialError:
        raise _Unsolved(f"not a polynomial in {var}: {e}")
    if q.degree() < 1 or var in q.LC().free_symbols:
        raise _Unsolved(f"no degree in {var}: {e}")
    lc = q.LC()
    if lc.free_symbols or _certified(lc) == 0:
        raise _Unsolved(f"a leading coefficient that may vanish: {lc}")
    op = type(rel)
    if op is sp.Equality:
        rs = sp.roots(q)
        if sum(rs.values()) != q.degree():
            raise _Unsolved(f"roots not all found: {e}")
        keep = []
        for r_ in rs:
            if r_.is_real is True:
                keep.append(r_)
            elif r_.is_real is not False:
                raise _Unsolved(f"realness depends on the parameters: {r_}")
        return sp.Intersection(sp.FiniteSet(*keep), domain)
    if q.degree() != 1:
        raise _Unsolved(f"a parametric inequality of degree {q.degree()}")
    r0 = -q.coeff_monomial(1) / lc
    if r0.is_real is not True:
        raise _Unsolved(f"a root whose realness is not known: {r0}")
    pos = _certified(lc) > 0
    if op is sp.Unequality:
        out = sp.Union(sp.Interval.open(-sp.oo, r0), sp.Interval.open(r0, sp.oo))
    elif op in (sp.StrictGreaterThan, sp.GreaterThan):
        out = (sp.Interval(r0, sp.oo, op is sp.StrictGreaterThan, True) if pos
               else sp.Interval(-sp.oo, r0, True, op is sp.StrictGreaterThan))
    else:
        out = (sp.Interval(-sp.oo, r0, True, op is sp.StrictLessThan) if pos
               else sp.Interval(r0, sp.oo, op is sp.StrictLessThan, True))
    return sp.Intersection(out, domain)


def _parametric_radical(e, var, domain):
    """(xii) with ONE radical P**(1/n) of a polynomial in `var` (parameters allowed): eliminating it
    gives a polynomial whose roots hold every zero; a candidate is kept only when, for every value of
    the parameters, it is real, the radicand is >= 0 and e vanishes there (simplified to 0); dropped when
    one of these certainly fails; otherwise raise _Unsolved. sqrt(x - a) = 2 → {a + 4}."""
    rad = _roots_of(e, var)
    Ps = {n.base for n in rad}
    if len(Ps) != 1 or any(n.exp < 0 for n in rad):
        raise _Unsolved(f"not one radical: {e}")
    (P,) = Ps
    n_ = sp.ilcm(*[n.exp.q for n in rad]) if len(rad) > 1 else rad[0].exp.q
    r = sp.Dummy("r")
    bt = e.xreplace({n: r ** int(n.exp * n_) for n in rad})
    try:
        sp.Poly(bt, r, var)
        sp.Poly(P, var)
    except sp.PolynomialError:
        raise _Unsolved(f"not polynomial around the radical: {e}")
    if sp.simplify(bt.subs(r, P ** sp.Rational(1, n_)) - e) != 0:
        raise _Unsolved(f"the radical's reading does not check: {e}")
    q = sp.Poly(sp.expand(sp.resultant(sp.Poly(bt, r), sp.Poly(r ** n_ - P, r))), var)
    lc = q.LC() if q.degree() >= 1 else S.Zero
    if q.degree() < 1 or lc.free_symbols or _certified(lc) == 0:
        raise _Unsolved(f"an eliminated polynomial with no fixed degree: {q}")
    rs = sp.roots(q)
    if sum(rs.values()) != q.degree():
        raise _Unsolved(f"roots not all found: {q}")
    keep = []
    for c in rs:
        rad_c = sp.simplify(P.subs(var, c))
        val = sp.simplify(e.subs(var, c))
        if c.is_real is False or rad_c.is_negative is True:
            continue
        if c.is_real is not True or rad_c.is_nonnegative is not True:
            raise _Unsolved(f"undecided for some parameter value: {c}")
        if val == 0:
            keep.append(c)
        elif not (val.is_number and _certified(val) != 0):
            raise _Unsolved(f"a candidate that may be a zero: {c}")
    return sp.Intersection(sp.FiniteSet(*keep), domain)


def sign_range(var) -> sp.Set:
    """The reals the sign assumptions of `var` leave it: (0, oo) for a positive symbol, ℝ for a plain one. The
    sets of `exact_solveset` lie in it (round 7); a caller that takes their complement takes it there."""
    if var.is_positive:
        return sp.Interval.open(0, S.Infinity)
    if var.is_nonnegative:
        return sp.Interval(0, S.Infinity)
    if var.is_negative:
        return sp.Interval.open(S.NegativeInfinity, 0)
    if var.is_nonpositive:
        return sp.Interval(S.NegativeInfinity, 0)
    return S.Reals


def _rebuilt(rel, var, domain):
    e = rel.lhs - rel.rhs
    if e.free_symbols - {var}:
        return _parametric(rel, var, domain)
    if isinstance(domain, sp.FiniteSet) and all(p.is_number for p in domain):
        keep = _on_points(rel, var, domain)            # point by point
        if keep is not None:
            return sp.FiniteSet(*keep)
    # the sign the variable itself carries (a positive integer of count_integers) bounds its domain: no point
    # outside it is a value of the variable, and x**(1/3) < 2 was left unsolved for its x < 0 (round 7)
    signed = sign_range(var)
    if signed is not S.Reals:
        domain = sp.Intersection(domain, signed)
    hull = _hull(domain)
    if hull is not None:
        return sp.Intersection(_on_window(rel, var, hull[0], hull[1])[0], domain)
    # the window of a domain bounded on one side is its own (inf, sup), not the whole line: on x > 0 no odd
    # root of x has a negative radicand, and x**(1/3) < 1 was left unsolved for its x < 0 (round 7, RK3)
    try:
        wlo, whi = domain.inf, domain.sup
    except Exception:  # noqa: BLE001 - no bounds (a ConditionSet): the whole line
        wlo, whi = S.NegativeInfinity, S.Infinity
    if not (wlo.is_number and whi.is_number and (wlo.is_finite or wlo == S.NegativeInfinity)
            and (whi.is_finite or whi == S.Infinity)):
        wlo, whi = S.NegativeInfinity, S.Infinity
    P = period(e, var)
    if P is not None:
        discrete = _on_periodic_points(rel, var, domain, P)
        if discrete is not None:
            return discrete
    if (_identity(e, var) or e.has(sp.Abs, sp.sign, sp.Max, sp.Min) or any(
            isinstance(n, sp.Pow) and n.exp == S.Half and isinstance(n.base, sp.Pow) and n.base.exp == 2
            for n in sp.preorder_traversal(e))) and P is None:
        return sp.Intersection(_on_window(rel, var, wlo, whi)[0], domain)
    if isinstance(rel, sp.Equality):
        zp, pp, _ = _structure(e, var)
        try:
            dlo, dhi = domain.inf, domain.sup
        except Exception:  # noqa: BLE001
            dlo, dhi = S.NegativeInfinity, S.Infinity
        _convention_free(e, var, dlo, dhi)
        if _restricted(e, var):
            # a zero where a log or an even root is not real is no zero ((x + 1)*log(x) = 0 at x = -1);
            # a progression crosses that region, so only points are cut here
            if any(step != 0 for _, step in zp + pp):
                raise _Unsolved("a progression with a log factor on an unbounded domain")
            outside = _log_outside(e, var)
            zp = [(p0, step) for p0, step in zp if not outside(p0)]
        n = sp.Dummy("n", integer=True)

        def union(progs):
            return sp.Union(*[sp.FiniteSet(p0) if step == 0 else sp.ImageSet(sp.Lambda(n, p0 + step * n), S.Integers)
                              for p0, step in progs]) if progs else S.EmptySet
        zs = union(zp)
        return sp.Intersection(sp.Complement(zs, union(pp)) if pp else zs, domain)
    if P is None:
        # not periodic: with finitely many zeros and poles, the cells cover the whole line
        return sp.Intersection(_on_window(rel, var, wlo, whi)[0], domain)
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
