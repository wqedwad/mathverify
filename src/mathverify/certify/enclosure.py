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

import time

import mpmath as mp
import sympy as sp

__all__ = ["iv_eval", "Unsupported", "rigorous_enclosure", "constant_interval", "from_raw"]

_DPS = 30


class Unsupported(ValueError):
    """An expression with no interval extension here."""


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
        return iv.mpf(mp.mpf(v._mpf_))          # the Float's own binary value, exactly
    raise Unsupported(f"no interval for {v}")


def _monotone(fn, x, increasing=True):
    """[fn(lo), fn(hi)] widened by a margin for mpmath's last-digit error (fn at a higher precision)."""
    lo, hi = _ends(x)
    if not (mp.isfinite(lo) and mp.isfinite(hi)):
        raise Unsupported("unbounded argument")
    with mp.workdps(_DPS + 15):
        a, b = fn(lo), fn(hi)
        if not increasing:
            a, b = b, a
        eps = mp.mpf(10) ** (-(_DPS + 5))
        return _hull(a - eps * (1 + abs(a)), b + eps * (1 + abs(b)))


def _mig_mag(x):
    lo, hi = _ends(x)
    if lo <= 0 <= hi:
        return mp.mpf(0), max(-lo, hi)
    return (lo, hi) if lo > 0 else (-hi, -lo)


def iv_eval(e, env: dict):
    """The interval value of the SymPy expression `e` with the symbols of `env` (Symbol -> interval)."""
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
            out = out + iv_eval(a, env)
        return out
    if isinstance(e, sp.Mul):
        out = iv.mpf(1)
        for a in e.args:
            out = out * iv_eval(a, env)
        return out
    if isinstance(e, sp.Pow):
        base, ex = e.args
        if ex.is_Integer:
            b = iv_eval(base, env)
            n = int(ex)
            return iv.mpf(1) / (b ** (-n)) if n < 0 else b ** n     # 1/[0, c] is [1/c, +inf]
        if ex.is_Rational:
            b = iv_eval(base, env)
            lo, hi = _ends(b)
            if ex == sp.S.Half and lo >= 0:
                return iv.sqrt(b)
            if lo > 0:
                return iv.exp(_point(ex) * iv.log(b))
            raise Unsupported("fractional power of a base that is not positive")
        if base is sp.E:
            return iv.exp(iv_eval(ex, env))
        b = iv_eval(base, env)
        lo, _ = _ends(b)
        if lo > 0:
            return iv.exp(iv_eval(ex, env) * iv.log(b))
        raise Unsupported("real power of a base that is not positive")
    if not isinstance(e, sp.Function) or len(e.args) != 1:
        if isinstance(e, (sp.Max, sp.Min)):
            vals = [_ends(iv_eval(a, env)) for a in e.args]
            pick = max if isinstance(e, sp.Max) else min
            return _hull(pick(v[0] for v in vals), pick(v[1] for v in vals))
        raise Unsupported(f"no interval extension for {type(e).__name__}")
    x = iv_eval(e.args[0], env)
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
        return _hull(*_mig_mag(x))
    if isinstance(e, sp.sign):
        return _hull(-1 if lo < 0 else (0 if lo == 0 else 1), 1 if hi > 0 else (0 if hi == 0 else -1))
    if isinstance(e, sp.atan):
        return _monotone(mp.atan, x)
    if isinstance(e, (sp.asin, sp.acos)):
        if lo < -1 or hi > 1:
            raise Unsupported("asin/acos outside [-1, 1]")
        return _monotone(mp.asin, x) if isinstance(e, sp.asin) else _monotone(mp.acos, x, increasing=False)
    if isinstance(e, sp.sinh):
        return _monotone(mp.sinh, x)
    if isinstance(e, sp.tanh):
        return _monotone(mp.tanh, x)
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


def _cell(f, d2f, var, l, r):
    """An interval holding ∫_l^r f (l, r mpf): (r - l)·f([l, r]), intersected, when f'' is given, with
    (r - l)·f(m) + f''([l, r])·(r - l)³/24 (Taylor at the midpoint m with Lagrange remainder: the linear
    term integrates to 0, and (x - m)²/2 >= 0 integrates to (r - l)³/24)."""
    iv = _iv()
    L, R = iv.mpf(l), iv.mpf(r)
    h = R - L
    try:
        whole = h * iv_eval(f, {var: _hull(l, r)})
    except (ArithmeticError, ValueError):
        whole = iv.mpf([-mp.inf, mp.inf])
    if d2f is None:
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


def _raw(x):
    return tuple(x._mpf_) if mp.isfinite(x) else ("-inf" if x < 0 else "inf")


def from_raw(t):
    """An mpf from `rigorous_enclosure`'s output (an exact binary number, or 'inf'/'-inf')."""
    if isinstance(t, str):
        return mp.mpf(t)
    return mp.make_mpf(tuple(t))


def rigorous_enclosure(integrand, var, a, b, outside=None, inside=None, max_cells: int = 4000,
                       seconds: float = 12.0):
    """Sandbox worker: (lo, hi), the ends of an interval holding ∫_a^b f as exact binary numbers (see
    `from_raw`), refined until it misses `outside` (an interval holding the claim, as (lo, hi) of `_raw`
    ends), lies within `inside` (a tolerance window), the cells run out or the time does. None when
    there is no enclosure: an infinite range, an end that is not a real number, an operation with no
    interval extension."""
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

        def cell(l, r, d):
            try:
                return _cell(f, d, var, l, r)
            except Unsupported:
                return iv.mpf([-mp.inf, mp.inf])

        # an end that is not a binary number (π) is an interval [lo, hi]: ∫ from the true end to the
        # interval's inner end is (a number in [0, hi - lo])·f([lo, hi])
        edge = [iv.mpf([0, 1]) * cell(lo_, hi_, None) for lo_, hi_ in (ia, ib) if hi_ > lo_]
        cells = [(ia[1], ib[0], cell(ia[1], ib[0], df))]
        out_lo, out_hi = (from_raw(outside[0]), from_raw(outside[1])) if outside else (None, None)
        in_lo, in_hi = (from_raw(inside[0]), from_raw(inside[1])) if inside else (None, None)
        t0 = time.monotonic()

        def width(c):
            lo, hi = _ends(c)
            return hi - lo

        while True:
            s = iv.mpf(0)
            for c in [c_ for _, _, c_ in cells] + edge:
                s = s + c
            slo, shi = _ends(s)
            if outside is not None and (shi < out_lo or slo > out_hi):
                break
            if inside is not None and in_lo <= slo and shi <= in_hi:
                break
            if len(cells) >= max_cells or time.monotonic() - t0 > seconds:
                break
            if outside is None and inside is None and mp.isfinite(slo) and mp.isfinite(shi) \
                    and shi - slo <= mp.mpf(10) ** (-(_DPS - 8)) * (1 + abs(slo)):
                break
            cells.sort(key=lambda c: width(c[2]), reverse=True)
            k = max(1, len(cells) // 8)
            new = []
            for l, r, c in cells[:k]:
                m = (l + r) / 2
                if not l < m < r:
                    new.append((l, r, c))
                    continue
                new += [(l, m, cell(l, m, df)), (m, r, cell(m, r, df))]
            if len(new) == k:
                break                             # no cell can be split further
            cells = new + cells[k:]
        if sign < 0:
            slo, shi = -shi, -slo
        return _raw(slo), _raw(shi)
