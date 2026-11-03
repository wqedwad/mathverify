"""Rigorous enclosures of definite integrals by interval arithmetic (fourth audit, 1 Oct 2026, d4c).

A quadrature's error estimate is no proof: tanh-sinh and Gauss-Legendre share their blind spot at a narrow
peak, both "converge" with a small nonzero error estimate, and a true value of ∫_0^1 (x² + 10^4 sech²(10^4
(x - 1/3))) dx was refuted (review of d4c, 2 Oct 2026). Here an integral over a finite [a, b] is bounded by
interval arithmetic (`mpmath.iv`, outward rounding): on a cell [l, r], f takes its values in f([l, r]),
so ∫_l^r f ∈ (r - l)·f([l, r]); with f' evaluable too, ∫_l^r f ∈ (r - l)·f(m) ± max|f'([l, r])|·(r - l)²/4
(mean value theorem, m the midpoint). The sum over the cells encloses the integral; the widest cells are
bisected until the enclosure decides the question or the budget runs out. A peak cannot be missed: the
interval value of the cell that holds it holds the peak.

Only operations whose interval extension is written out below are evaluated; anything else (an unknown
function, a complex value, a point where f is undefined, an unbounded cell) gives no enclosure, or an
unbounded one that decides nothing. No infinite range is enclosed.
"""
from __future__ import annotations

import threading
import time

import mpmath as mp
import sympy as sp

__all__ = ["iv_eval", "Unsupported", "rigorous_enclosure", "constant_interval", "constant_sign", "from_raw"]

_DPS = 30


class Unsupported(ValueError):
    """An expression with no interval extension here."""


class NotAnalytic(Unsupported):
    """`iv_eval(..., analytic=True)`: an operation not proved analytic on its argument's interval."""


def _iv():
    return mp.iv


def _ends(x):
    lo, hi = x._mpi_
    return mp.make_mpf(lo), mp.make_mpf(hi)


def _hull(lo, hi):
    iv = _iv()
    return iv.mpf([lo, hi])


def _point(v):
    """A rational or a binary Float as a (tight) interval."""
    iv = _iv()
    if isinstance(v, sp.Integer):
        return iv.mpf(int(v))
    if isinstance(v, sp.Rational):
        return iv.mpf(int(v.p)) / iv.mpf(int(v.q))
    if isinstance(v, sp.Float):
        return iv.mpf(mp.make_mpf(v._mpf_))     # the Float's own binary value, exactly (mp.mpf would round it)
    raise Unsupported(f"no interval for {v}")


def _monotone(fn, x, increasing=True, limits=None):
    """[fn(lo), fn(hi)] widened by a margin for mpmath's last-digit error (fn at a higher precision). An
    unbounded argument only for a bounded fn, with `limits` = (fn(-oo), fn(oo)): atan of every real number is
    in [-π/2, π/2], so atan(tan x) on a cell holding a pole of tan is bounded there (YO-A)."""
    lo, hi = _ends(x)
    if not (mp.isfinite(lo) and mp.isfinite(hi)):
        if limits is None:
            raise Unsupported("unbounded argument")
        with mp.workdps(_DPS + 15):
            eps = mp.mpf(10) ** (-(_DPS + 5))
            a = limits[0]() if lo == -mp.inf else fn(lo)
            b = limits[1]() if hi == mp.inf else fn(hi)
            return _hull(a - eps * (1 + abs(a)), b + eps * (1 + abs(b)))
    with mp.workdps(_DPS + 15):
        a, b = fn(lo), fn(hi)
        if not increasing:
            a, b = b, a
        eps = mp.mpf(10) ** (-(_DPS + 5))
        return _hull(a - eps * (1 + abs(a)), b + eps * (1 + abs(b)))


def _lipschitz(fn, x, bound=1):
    """fn(lo) ± bound·(hi - lo) for an fn with |fn'| <= bound on the whole real line, widened by the margin of
    `_monotone` and by the rounding of the argument to the working precision. Si (Si' = sin t/t), the Fresnel
    integrals S and C (S' = sin(πt²/2), C' = cos(πt²/2)): |fn'| <= 1. Without them the value ∫_0^1 sin(x²) dx =
    S(√2/√π)·√(π/2) of a certificate had no interval, and no declared tolerance was decided against it (son saldırı
    G2RK-2)."""
    lo, hi = _ends(x)
    if not (mp.isfinite(lo) and mp.isfinite(hi)):
        raise Unsupported("unbounded argument")
    with mp.workdps(_DPS + 15):
        v = fn(lo)
        eps = mp.mpf(10) ** (-(_DPS + 5))
        r = bound * ((hi - lo) * (1 + eps) + eps * (1 + abs(lo) + abs(hi)))
        return _hull(v - r - eps * (1 + abs(v)), v + r + eps * (1 + abs(v)))


def _neg(v):
    """-v exactly: mpf negation rounds to the working precision, and an end carrying more bits than that
    was rounded INWARD, so |atan(2x)| on a negative cell missed its own lower end by 3e-32 (attack on d4c
    round 2, YO-5)."""
    return mp.make_mpf(mp.libmp.mpf_neg(v._mpf_))


def _mig_mag(x):
    """(min |x|, max |x|) over the interval x, exactly."""
    lo, hi = _ends(x)
    if lo <= 0 <= hi:
        return mp.mpf(0), max(_neg(lo), hi)
    return (lo, hi) if lo > 0 else (_neg(hi), _neg(lo))


def _bounded(v):
    lo, hi = _ends(v)
    if not (mp.isfinite(lo) and mp.isfinite(hi)):
        raise NotAnalytic("an unbounded value")
    return v


def _off_zero(v, what):
    lo, hi = _ends(v)
    if not (lo > 0 or hi < 0):
        raise NotAnalytic(f"{what} may be 0")


def iv_eval(e, env: dict, analytic: bool = False):
    """The interval value of the SymPy expression `e` with the symbols of `env` (Symbol -> interval).

    analytic=True also PROVES `e` analytic on the box, read as written: every operation is applied inside the
    open set where it is analytic (log of a positive number, tan where cos is not 0, a fractional power of a
    positive base, asin inside (-1, 1), ...) and every intermediate value is bounded; NotAnalytic otherwise. A
    pole (1/x, tan, log at 0) shows as an unbounded value, a log below 0 as an error; a function that stays
    bounded where it is not analytic (√x and asin at an end, |x| and sign at 0, Max/Min) is refused by name.
    SymPy's derivatives of `e` are then its true derivatives on the box. Without that proof they are not:
    SymPy reduces d/dx atan(tan x) to 1, so f'' = 0 hid the jump of -π at π/2, and the Taylor bound of a cell
    holding it was one wrong point (attack on d4c round 3, YO-A)."""
    v = _iv_node(e, env, analytic)
    return _bounded(v) if analytic else v


def _iv_node(e, env: dict, an: bool):
    iv = _iv()
    if e in env:
        return env[e]
    if e.is_Rational or isinstance(e, sp.Float):
        return _point(e)
    if e is sp.pi:
        return iv.pi
    if e is sp.E:
        return iv.e
    if isinstance(e, sp.Add):
        out = iv.mpf(0)
        for a in e.args:
            out = out + iv_eval(a, env, an)
        return out
    if isinstance(e, sp.Mul):
        out = iv.mpf(1)
        for a in e.args:
            out = out * iv_eval(a, env, an)
        return out
    if isinstance(e, sp.Pow):
        base, ex = e.args
        if ex.is_Integer:
            b = iv_eval(base, env, an)
            n = int(ex)
            return iv.mpf(1) / (b ** (-n)) if n < 0 else b ** n     # 1/[0, c] is [1/c, +inf]
        if ex.is_Rational:
            b = iv_eval(base, env, an)
            lo, hi = _ends(b)
            if _EVEN_ROOTS.on and ex.q % 2 == 0 and lo < 0 <= hi:
                # (an edge cell of a range on which the integrand is defined almost everywhere: see
                # `rigorous_enclosure`) the base of an even root is >= 0 at almost every point of the range
                b = _hull(mp.mpf(0), hi)
                lo = mp.mpf(0)
            if an and not lo > 0:
                raise NotAnalytic("a fractional power of a base that may be 0")
            if ex == sp.S.Half and lo >= 0:
                return iv.sqrt(b)
            if lo >= 0:
                # b^e = exp(e·log b); at b = 0, log b = -oo gives 0 for e > 0 and +oo for e < 0
                return iv.exp(_point(ex) * iv.log(b))
            raise Unsupported("fractional power of a base that is not positive")
        if base is sp.E:
            return iv.exp(iv_eval(ex, env, an))
        b = iv_eval(base, env, an)
        lo, _ = _ends(b)
        if an and not lo > 0:
            raise NotAnalytic("a real power of a base that may be 0")
        if lo >= 0:
            # a cell touching b = 0 (x^x on [0, h]): exp(e·log b) is bounded where the power is (RK-B)
            return iv.exp(iv_eval(ex, env, an) * iv.log(b))
        raise Unsupported("real power of a base that is not positive")
    if not isinstance(e, sp.Function) or len(e.args) != 1:
        if isinstance(e, (sp.Max, sp.Min)):
            if an:
                raise NotAnalytic("Max/Min")
            vals = [_ends(iv_eval(a, env, an)) for a in e.args]
            pick = max if isinstance(e, sp.Max) else min
            return _hull(pick(v[0] for v in vals), pick(v[1] for v in vals))
        raise Unsupported(f"no interval extension for {type(e).__name__}")
    x = iv_eval(e.args[0], env, an)
    lo, hi = _ends(x)
    if isinstance(e, sp.exp):
        return iv.exp(x)
    if isinstance(e, sp.log):
        return iv.log(x)                      # [-inf, ...] at 0, ComplexResult below it
    if isinstance(e, sp.sin):
        return iv.sin(x)
    if isinstance(e, sp.cos):
        return iv.cos(x)
    if isinstance(e, (sp.tan, sp.sec, sp.cot, sp.csc)):
        s, c = iv.sin(x), iv.cos(x)
        num, den = {sp.tan: (s, c), sp.sec: (iv.mpf(1), c), sp.cot: (c, s), sp.csc: (iv.mpf(1), s)}[type(e)]
        dlo, dhi = _ends(den)
        if dlo <= 0 <= dhi:
            return iv.mpf([-mp.inf, mp.inf])
        return num / den
    if isinstance(e, sp.Abs):
        if an:
            _off_zero(x, "the argument of Abs")
        return _hull(*_mig_mag(x))
    if isinstance(e, sp.sign):
        if an:
            _off_zero(x, "the argument of sign")
        return _hull(-1 if lo < 0 else (0 if lo == 0 else 1), 1 if hi > 0 else (0 if hi == 0 else -1))
    if isinstance(e, sp.atan):
        return _monotone(mp.atan, x, limits=(lambda: -mp.pi / 2, lambda: mp.pi / 2))
    if isinstance(e, (sp.asin, sp.acos)):
        if lo < -1 or hi > 1:
            raise Unsupported("asin/acos outside [-1, 1]")
        if an and not (-1 < lo and hi < 1):
            raise NotAnalytic("asin/acos at -1 or 1")
        return _monotone(mp.asin, x) if isinstance(e, sp.asin) else _monotone(mp.acos, x, increasing=False)
    if isinstance(e, sp.erf):
        return _monotone(mp.erf, x, limits=(lambda: mp.mpf(-1), lambda: mp.mpf(1)))
    if isinstance(e, sp.erfc):
        return iv.mpf(1) - _monotone(mp.erf, x, limits=(lambda: mp.mpf(-1), lambda: mp.mpf(1)))
    if isinstance(e, sp.Si):
        return _lipschitz(mp.si, x)
    if isinstance(e, sp.fresnels):
        return _lipschitz(mp.fresnels, x)
    if isinstance(e, sp.fresnelc):
        return _lipschitz(mp.fresnelc, x)
    if isinstance(e, sp.sinh):
        return _monotone(mp.sinh, x)
    if isinstance(e, sp.tanh):
        return _monotone(mp.tanh, x, limits=(lambda: mp.mpf(-1), lambda: mp.mpf(1)))
    if isinstance(e, sp.cosh):
        m, M = _mig_mag(x)
        return _monotone(mp.cosh, _hull(m, M))
    if isinstance(e, sp.sech):
        m, M = _mig_mag(x)
        return _monotone(mp.sech, _hull(m, M), increasing=False)
    raise Unsupported(f"no interval extension for {type(e).__name__}")


def constant_interval(c):
    """An interval holding the constant `c`, or None."""
    try:
        with mp.workdps(_DPS):
            mp.iv.dps = _DPS
            out = iv_eval(sp.sympify(c), {})
            lo, hi = _ends(out)
            return (lo, hi) if mp.isfinite(lo) and mp.isfinite(hi) else None
    except (Unsupported, ArithmeticError, ValueError, TypeError):
        return None


def constant_sign(c, ladder=(30, 60, 120, 240)):
    """-1 or 1 when an interval holding the closed constant `c` (outward rounding) excludes 0 at one of the
    precisions of `ladder`; None otherwise (0 is never certified here, nor anything with no interval extension).
    Strict evalf is no such proof: asin(tanh x) - atan(sinh x), which is 0, came out 2.36e-125 at 30 and at 70
    digits at x = π/3·10^-6 + 287652374/999983 (asin near 1 amplifies the error of tanh by 10^125)."""
    saved = mp.iv.dps
    try:
        for dps in ladder:
            mp.iv.dps = dps
            with mp.workdps(dps):
                try:
                    lo, hi = _ends(iv_eval(sp.sympify(c), {}))
                except (ArithmeticError, ValueError, TypeError, AttributeError, NotImplementedError):
                    return None
                if lo > 0:
                    return 1
                if hi < 0:
                    return -1
        return None
    finally:
        mp.iv.dps = saved


def _cell(f, d2f, var, l, r):
    """An interval holding ∫_l^r f (l, r mpf): (r - l)·f([l, r]), intersected, when f'' is given and f is
    PROVED analytic on [l, r] (`iv_eval(..., analytic=True)`), with (r - l)·f(m) + f''([l, r])·(r - l)³/24
    (Taylor at the midpoint m with Lagrange remainder: the linear term integrates to 0, and (x - m)²/2 >= 0
    integrates to (r - l)³/24). Taylor's theorem needs f in C² on the cell: SymPy's f'' of atan(tan x) is 0,
    and a cell holding the jump at π/2 gave one wrong point (attack on d4c round 3, YO-A)."""
    iv = _iv()
    L, R = iv.mpf(l), iv.mpf(r)
    h = R - L
    box = {var: _hull(l, r)}
    smooth = True
    try:
        whole = h * iv_eval(f, box, analytic=True)
    except (ArithmeticError, ValueError):
        smooth = False
        try:
            whole = h * iv_eval(f, box)
        except (ArithmeticError, ValueError):
            whole = iv.mpf([-mp.inf, mp.inf])
    if d2f is None or not smooth:
        return whole
    try:
        d2 = iv_eval(d2f, {var: _hull(l, r)})          # unbounded near a singularity: no help, no harm
        second = h * iv_eval(f, {var: (L + R) / 2}) + d2 * h * h * h / 24
    except (ArithmeticError, ValueError):
        return whole
    a1, b1 = _ends(whole)
    a2, b2 = _ends(second)
    lo, hi = max(a1, a2), min(b1, b2)
    return _hull(lo, hi) if lo <= hi else _hull(min(a1, a2), max(b1, b2))


# a function with a jump: SymPy's derivative of it ignores the jump (Piecewise) and Taylor's theorem does not hold
_JUMPS = (sp.floor, sp.ceiling, sp.frac, sp.Piecewise, sp.Heaviside, sp.sign, sp.Mod, sp.DiracDelta)


def _removable(f, var, c):
    """(P, P^(k), k!) when f = P/(var - c)^k near the end c with P^(j)(c) = 0 exactly for j < k (k <= 3), so that
    f(x) = P^(k)(ξ)/k! for some ξ between c and x where P is C^k (the caller proves P analytic there); None
    otherwise."""
    for k in (1, 2, 3):
        try:
            P = sp.cancel(f * (var - c) ** k)
            if not all(sp.simplify(sp.diff(P, var, j).subs(var, c)) == 0 for j in range(k)):
                continue
            return P, sp.diff(P, var, k), int(sp.factorial(k))
        except Exception:  # noqa: BLE001 - no rule
            continue
    return None


def _weights(f, var, c) -> list:
    """f = g·w near the end c with w an integrable singular weight of one sign on a cell at c: log(u), u^p or
    |u|^p (-1 < p < 0), u linear in var with u(c) = 0; f itself may be the weight (g = 1: ∫_0^1 x^(-99/100) dx = 100
    had a half-infinite enclosure, son denetim SI-YO-2). Returned as (g, 'log' | 'pow' | 'abspow', |u'|, p, sign of
    u')."""
    out = []
    factors = f.args if isinstance(f, sp.Mul) else (f,)
    for w in factors:
        if isinstance(w, sp.log):
            u, kind, p_ = w.args[0], "log", None
        elif isinstance(w, sp.Pow) and w.exp.is_Rational and -1 < w.exp < 0:
            u, kind, p_ = w.base, "pow", w.exp
            if isinstance(u, sp.Abs):
                u, kind = u.args[0], "abspow"
        else:
            continue
        try:
            poly = sp.Poly(u, var)
        except sp.PolynomialError:
            continue
        if poly.degree() != 1 or not all(co.is_Rational for co in poly.all_coeffs()) or u.subs(var, c) != 0:
            continue
        g = sp.Mul(*[a for a in factors if a is not w])
        slope = poly.all_coeffs()[0]
        out.append((g, kind, abs(slope), p_, 1 if slope > 0 else -1))
    return out


def _weighted(g, kind, alpha, p_, var, l, r, h, side=1):
    """∫ over the cell [l, r] at the weight's zero of g·w: g([l, r])·∫ w (w of one sign there: the mean value
    theorem for integrals); None when the weight changes sign on the cell (log u with |u| past 1) or u < 0 on it
    (`side`, the sign of u on the cell): log u and u^p are no real numbers there, or have the other sign (the real
    cube root), and ∫_{-1}^{0} 2·x^(-1/3) dx had the enclosure [3, 3] (son denetim, 21 Oct 2026)."""
    if kind != "abspow" and side < 0:
        return None
    iv = _iv()
    H = h * (int(alpha.p) if alpha.q == 1 else iv.mpf(int(alpha.p)) / int(alpha.q))      # |u| runs over [0, H]
    if kind == "log":
        if not _ends(H)[1] < 1:
            return None
        W = (H * iv.log(H) - H) / (iv.mpf(int(alpha.p)) / int(alpha.q))
    else:
        q1 = iv.mpf(int((p_ + 1).p)) / int((p_ + 1).q)
        W = iv.exp(q1 * iv.log(H)) / (q1 * (iv.mpf(int(alpha.p)) / int(alpha.q)))
    return iv_eval(g, {var: _hull(l, r)}) * W


def _meet(u, v):
    """Two enclosures of one integral: their intersection is one too. Disjoint, one of them rests on a false
    premise: neither is picked, their hull holds the true one (the end rule's bound had been picked, YO-A)."""
    (a1, b1), (a2, b2) = _ends(u), _ends(v)
    lo_, hi_ = max(a1, a2), min(b1, b2)
    return _hull(lo_, hi_) if lo_ <= hi_ else _hull(min(a1, a2), max(b1, b2))


def _raw(x):
    return tuple(x._mpf_) if mp.isfinite(x) else ("-inf" if x < 0 else "inf")


def from_raw(t):
    """An mpf from `rigorous_enclosure`'s output (an exact binary number, or 'inf'/'-inf')."""
    if isinstance(t, str):
        return mp.mpf(t)
    return mp.make_mpf(tuple(t))


_SETTLE_GAIN = mp.mpf(1) / 8   # the narrowing a finite sum must show over `settle` rounds (`rigorous_enclosure`)


class _EvenRoots(threading.local):
    on = False


_EVEN_ROOTS = _EvenRoots()


def rigorous_enclosure(integrand, var, a, b, outside=None, inside=None, max_cells: int = 4000,
                       seconds: float = 120.0, defined: bool = False, settle: int = 0):
    """Sandbox worker: (lo, hi), the ends of an interval holding ∫_a^b f as exact binary numbers (see
    `from_raw`), refined until it misses `outside` (an interval holding the claim, as (lo, hi) of `_raw`
    ends), lies within `inside` (a tolerance window) or `max_cells` cells are reached; with `settle` > 0, also
    once a finite sum has not narrowed by `_SETTLE_GAIN` over the last `settle` rounds. None when there is
    no enclosure: an infinite range, an end that is not a real number, an operation with no interval
    extension, or `seconds` (a safety stop, not a budget) running out."""
    iv = _iv()
    iv.dps = _DPS
    with mp.workdps(_DPS):
        f, A, B = sp.sympify(integrand), sp.sympify(a), sp.sympify(b)
        if f.free_symbols - {var}:
            return None
        ia, ib = constant_interval(A), constant_interval(B)
        if ia is None or ib is None:
            return None
        sign = 1
        if ia[0] > ib[1]:
            ia, ib, sign = ib, ia, -1
        elif not ia[1] < ib[0]:
            return ("0", "0") if A == B else None
        try:
            iv_eval(f, {var: _hull(ia[0], ib[1])})
        except Unsupported as e:
            if str(e).startswith("no interval extension"):
                return None
        except (ArithmeticError, ValueError):
            pass
        df = None                                 # f'' (Taylor), when f is smooth and f'' evaluable
        if not f.has(sp.Abs, sp.sign, sp.Max, sp.Min):
            try:
                df = sp.diff(f, var, 2)
                iv_eval(df, {var: _hull(ia[0], ib[1])})
            except Unsupported as e:
                if str(e).startswith("no interval extension"):
                    df = None
            except (ArithmeticError, ValueError):
                pass

        # an exact end where f is unbounded or undefined but the singularity is removable (sin x/x at 0):
        # f = P/(x - c)^k with P^(j)(c) = 0 for j < k, so on a cell at c, f = P^(k)(ξ)/k! (Taylor with Lagrange
        # remainder) and the cell holds h·P^(k)([l, r])/k!; the plain cell was unbounded and no claim was
        # refuted, not even ∫_0^1 sinh x/x dx = -100 (attack on d4c round 2, RK-B)
        ends = {}
        lo_end, hi_end = (A, B) if sign > 0 else (B, A)
        for end, (e_lo, e_hi), here in ((lo_end, ia, ia[1]), (hi_end, ib, ib[0])):
            if e_lo == e_hi and not f.has(*_JUMPS):
                ends[here] = (_removable(f, var, end), _weights(f, var, end))

        def finite(b_):
            blo, bhi = _ends(b_)
            return mp.isfinite(blo) and mp.isfinite(bhi)

        def cell(l, r, d):
            try:
                c_ = _cell(f, d, var, l, r)
            except Unsupported:
                c_ = iv.mpf([-mp.inf, mp.inf])
            h = iv.mpf(r) - iv.mpf(l)
            for at, (rule, weights) in ends.items():
                if rule is not None:
                    # Taylor at the end c holds on the whole side: f(x) = P^(k)(ξ)/k! with ξ between c and x, so
                    # on any cell, f is in P^(k)([c, r])/k! (or [l, c]); near c it is far tighter than the plain
                    # value (sin x/x on [h, 2h]: [1/2, 2] against [cos 2h, 1]). Taylor needs P in C^k from c to the
                    # cell: P proved analytic there, read as written (sin x/x + atan(tan x) past π/2: YO-A)
                    P, pk, kf = rule
                    try:
                        side = {var: _hull(min(at, l), max(at, r))}
                        iv_eval(P, side, analytic=True)
                        b_ = h * iv_eval(pk, side) / kf
                    except (Unsupported, ArithmeticError, ValueError, NotImplementedError):
                        b_ = None
                    if b_ is not None and finite(b_):
                        c_ = _meet(b_, c_) if finite(c_) else b_
                if at in (l, r) and not finite(c_):
                    for g, kind, alpha, p_, s_ in weights:
                        try:
                            b_ = _weighted(g, kind, alpha, p_, var, l, r, h, s_ if at == l else -s_)
                        except (Unsupported, ArithmeticError, ValueError, NotImplementedError):
                            continue
                        if b_ is not None and finite(b_):
                            c_ = b_
                            break
            return c_

        # an end that is not a binary number (π) is an interval [lo, hi]: ∫ from the true end to the
        # interval's inner end is (a number in [0, hi - lo])·f([lo, hi])
        # with `defined` (the caller proved the integrand's conditions fail on a null set of [a, b] at most), the base
        # of an even root is >= 0 almost everywhere on the part of the end's interval inside [a, b], and is read so
        # there: √cos x at the end π/2 had an interval value past π/2, where cos x < 0, the edge had none, and the
        # enclosure of ∫_0^{π/2} √(cos x)·sin x dx was (-oo, oo) (son saldırı G2RK-7)
        _EVEN_ROOTS.on = bool(defined)
        try:
            edge = [iv.mpf([0, 1]) * cell(lo_, hi_, None) for lo_, hi_ in (ia, ib) if hi_ > lo_]
        finally:
            _EVEN_ROOTS.on = False
        cells = [(ia[1], ib[0], cell(ia[1], ib[0], df))]
        out_lo, out_hi = (from_raw(outside[0]), from_raw(outside[1])) if outside else (None, None)
        in_lo, in_hi = (from_raw(inside[0]), from_raw(inside[1])) if inside else (None, None)
        t0 = time.monotonic()
        finest = (ib[0] - ia[1]) * mp.mpf(2) ** -110

        def width(c):
            lo, hi = _ends(c)
            return hi - lo

        widths = []                               # of the finite sums of the last rounds (`settle`)
        while True:
            s = iv.mpf(0)
            for c in [c_ for _, _, c_ in cells] + edge:
                s = s + c
            slo, shi = _ends(s)
            # `outside` and `inside` are about ∫_a^b: with a > b the sum is ∫_b^a, compared with its sign
            # turned (the unturned sum missed every window, KK-2)
            clo, chi = (slo, shi) if sign > 0 else (_neg(shi), _neg(slo))
            if outside is not None and (chi < out_lo or clo > out_hi):
                break
            if inside is not None and in_lo <= clo and chi <= in_hi:
                break
            if len(cells) >= max_cells:
                break
            if settle and mp.isfinite(clo) and mp.isfinite(chi):
                # a finite sum that holds `outside` and has stopped narrowing: cells of a fast oscillation (cos²
                # 1000πx) are [0, 1]·h until they are shorter than its period, and 4000 of them spent 4 to 30 s for
                # an enclosure that changed no decision of the certificate's check (son denetim SON-INT-RK-2)
                widths.append(chi - clo)
                if len(widths) > settle and widths[-1] > (1 - _SETTLE_GAIN) * widths[-1 - settle]:
                    break
            else:
                widths.clear()
            if time.monotonic() - t0 > seconds:
                # a safety stop only: the enclosure's budget is the number of cells, so that one input gets
                # one enclosure on any machine; under load a time budget left it wider and the claim it would
                # have refuted undecided (attack on d4c round 2, RK-C). Past the safety stop, no enclosure
                return None
            if outside is None and inside is None and mp.isfinite(slo) and mp.isfinite(shi) \
                    and shi - slo <= mp.mpf(10) ** (-(_DPS - 8)) * (1 + abs(slo)):
                break
            cells.sort(key=lambda c: width(c[2]), reverse=True)
            # while a cell is unbounded the sum is, and only splitting such cells can bound it: they alone are
            # split, until each is bounded or is split no further (a pole in it: no bound to be had, and none
            # narrower than 2^-110 of the range, where a pole at an end would be halved forever; the budget of
            # cells used to run out first, 4000 cells for nothing)
            k = sum(1 for _, _, c_ in cells if not finite(c_)) or max(1, len(cells) // 8)
            new = []
            for l, r, c in cells[:k]:
                m = (l + r) / 2
                if not l < m < r or (not finite(c) and r - l < finest):
                    new.append((l, r, c))
                    continue
                new += [(l, m, cell(l, m, df)), (m, r, cell(m, r, df))]
            if len(new) == k:
                break                             # no cell can be split further (an unbounded one: no bound at all)
            cells = new + cells[k:]
        if sign < 0:
            slo, shi = _neg(shi), _neg(slo)
        return _raw(slo), _raw(shi)
