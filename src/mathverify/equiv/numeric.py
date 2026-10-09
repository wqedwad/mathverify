"""Numeric equivalence with RELATIVE tolerance and a precision ladder (E3, E9).

Never a fixed 1e-12 absolute threshold (handoff §11/3). Precision is increased when
the comparison is inconclusive; a difference that is stable across precisions is a
genuine difference.
"""
from __future__ import annotations

import threading
from typing import Any

import mpmath as mp
import sympy as sp

__all__ = ["num_equal", "to_mp", "certified_sign", "exact_equal", "exact_zero_test", "has_float",
           "real_odd_roots", "NONREAL", "certified_integer", "certified_floor"]

DPS_LADDER = (30, 50, 80)

# ---------------------------------------------------------------------------
# certified signs and exact equality (audit of 25 Sep 2026)
# ---------------------------------------------------------------------------
# A relation between two EXACT numbers is a fact about exact numbers, and a tolerance cannot
# decide it. Measured before these helpers existed: at x = 1 + √2 the exactly-zero quantity
# x² − 2x − 1 evaluated to −3.5e-192 at 40 digits, so `x² − 2x − 1 ≥ 0` came out False and
# `< 0` True; the correct answer (1 − √2, 1 + √2) to x² − 2x − 1 < 0 was refuted and the empty
# set was certified as the solution of √(x² − 2x − 1) = 0. And the last rung of the precision
# ladder (80 digits) accepted a relative gap below 1e-70 as equality, so √(10¹⁰⁰ + 1) = 10⁵⁰,
# tanh(100) = 1 and a 75-digit decimal for π were certified CORRECT.
#
# A sign is certified by SymPy's adaptive evalf in `strict` mode (it raises instead of returning a
# value it cannot distinguish from zero), and a ZERO only by an exact method: a CAS rewrite to 0,
# or the minimal polynomial (for an algebraic number it is `t` exactly when the number is 0).
# Anything else is undecided — the caller abstains.
NONREAL = "nonreal"
_SIGN_DPS = 30


def has_float(*es) -> bool:
    for e in es:
        if isinstance(e, float):
            return True
        try:
            if sp.sympify(e).has(sp.Float):
                return True
        except (sp.SympifyError, TypeError):
            return True
    return False


def exact_zero_test(d) -> bool | None:
    """Sandbox worker: True when `d` is PROVABLY 0, False when provably nonzero, None undecided.
    Only exact methods: CAS rewrites that reach 0, and the minimal polynomial (for an algebraic
    number it is `t` exactly when the number is 0; tried early because it is fast and decisive
    where `simplify` stalls, e.g. 2·cos(2π/9) − CRootOf(x³ − 3x + 1, 2))."""
    d = sp.sympify(d)
    if d == 0:
        return True

    def cheap(e):
        for fn in (sp.expand, lambda e_: sp.cancel(sp.together(e_))):
            try:
                r = fn(e)
            except Exception:  # noqa: BLE001
                continue
            if r == 0:
                return True
        return None

    if cheap(d):
        return True
    try:
        t = sp.Dummy("t")
        m = sp.minimal_polynomial(d, t)
        return bool(sp.expand(m - t) == 0)
    except Exception:  # noqa: BLE001 - NotAlgebraic, …: try the rewrites
        pass
    if _angle_sum_is_zero(d) or _exp_generator_is_zero(d):
        return True
    for fn in (sp.radsimp, sp.simplify, lambda e: sp.expand_log(e, force=False), sp.logcombine,
               sp.trigsimp, lambda e: sp.simplify(e.rewrite(sp.exp)), sp.expand_complex):
        try:
            r = fn(d)
        except Exception:  # noqa: BLE001
            continue
        if r == 0 or (getattr(r, "is_number", False) and r.is_zero is True):
            return True
    return None


def _unit(theta):
    """e^(iθ) for θ = π or atan/asin/acos of a real number (algebraic in that number), or None."""
    if theta is sp.pi:
        return sp.Integer(-1)
    if not isinstance(theta, (sp.atan, sp.asin, sp.acos)) or len(theta.args) != 1:
        return None
    a = theta.args[0]
    if not (a.is_number and a.is_real is True):
        return None
    if isinstance(theta, sp.atan):
        return (1 + sp.I * a) / sp.sqrt(1 + a**2)
    # asin/acos of a number outside [-1, 1] is complex: its 40-digit value below is no real number
    c = sp.sqrt(1 - a**2)
    return c + sp.I * a if isinstance(theta, sp.asin) else a + sp.I * c


def _angle_sum_is_zero(d) -> bool:
    """Is d = Σ c_k·θ_k exactly 0, θ_k = π or atan/asin/acos of real algebraic numbers, c_k rational?
    With N the common denominator, e^(iNd) = Π (e^(iθ_k))^(N c_k) is algebraic: when it is exactly 1
    (minimal polynomial), Nd is a multiple of 2π, and |Nd| < 1 (each θ_k to 40 digits) leaves only 0.
    atan(3/7) + atan(7/3) - π/2 was undecided, and random points had read evalf's '0.e-160' as 0."""
    try:
        d = sp.expand(d.replace(lambda n: type(n).__name__ == "arccot", lambda n: sp.pi / 2 - sp.atan(n.args[0]))
                      .replace(lambda n: isinstance(n, sp.acot), lambda n: sp.atan(1 / n.args[0])))
        terms = sp.Add.make_args(d)
        if not 1 <= len(terms) <= 6:
            return False
        coeffs, units = [], []
        for term in terms:
            c, rest = term.as_coeff_Mul()
            u = _unit(rest)
            if not isinstance(c, sp.Rational) or u is None:
                return False
            coeffs.append(c)
            units.append(u)
        n = sp.ilcm(*[c.q for c in coeffs])
        powers = [int(c * n) for c in coeffs]
        if max(abs(k) for k in powers) > 24:
            return False
        z = sp.Mul(*[u**k for u, k in zip(units, powers)])
        if all(u.is_algebraic for u in units):
            t = sp.Dummy("t")
            if sp.expand(sp.minimal_polynomial(z, t) - (t - 1)) != 0:
                return False
        elif not _one_in_an_exponential(z):
            return False
        with mp.workdps(40):
            total = sum(mp.mpf(str(sp.N(term, 45))) for term in terms)
            return bool(abs(n * total) < 1)
    except Exception:  # noqa: BLE001
        return False


def _in_one_exponential(e):
    """`e` with every e^r (r rational, hyperbolic functions written with exp) replaced by g^k, g = e^(r0)
    a positive symbol (r0 the gcd of the r's), or None."""
    e = e.rewrite(sp.exp)
    args = {a.args[0] for a in e.atoms(sp.exp)}
    if not all(isinstance(r, sp.Rational) for r in args) or len(args) > 8:
        return None
    if not args:
        return e
    r0 = sp.Rational(sp.igcd(*[r.p for r in args]), sp.ilcm(*[r.q for r in args]))
    if any(abs(r / r0) > 64 for r in args):
        return None
    g = sp.Dummy("g", positive=True)
    return e.xreplace({sp.exp(r): g ** int(r / r0) for r in args})


def _one_in_an_exponential(z) -> bool:
    """Is the number z, algebraic in e^(r0) (`_in_one_exponential`), exactly 1? The identity in the
    positive symbol holds at its value: atan(e^c) + atan(e^-c) = π/2, asin(tanh c) = atan(sinh c)."""
    w = _in_one_exponential(z)
    if w is None or w.free_symbols == set() and not w.is_algebraic:
        return False
    def roots(e):
        # sqrt((g² + 1)²) is g² + 1 for g > 0, which SymPy sees only with the radicand factored
        return e.replace(lambda n: isinstance(n, sp.Pow) and n.exp in (sp.S.Half, -sp.S.Half),
                         lambda n: sp.factor(sp.together(n.base)) ** n.exp)

    w = roots(sp.simplify(roots(sp.together(w))))
    return sp.simplify(w - 1) == 0


def _exp_generator_is_zero(d) -> bool:
    """Is d exactly 0 as a rational function of one exponential? Every e^r (r rational, after writing
    the hyperbolic functions with exp) is g^k for g = e^(r0), r0 the gcd of the r's: tanh(c) and
    (e^(2c) - 1)/(e^(2c) + 1) at c = 123/1000 are then the same rational function of g. An identity of
    rational functions holds wherever both sides are defined."""
    try:
        if d.rewrite(sp.exp) == 0:
            return True
        e = _in_one_exponential(d)
        if e is None or not e.free_symbols:
            return False
        return sp.cancel(sp.together(e)) == 0
    except Exception:  # noqa: BLE001
        return False


_MIN_BITS = 20


def _part_state(f):
    """'zero' for an exact 0, 'value' for a part carrying significant bits, 'unknown' for a
    zero-looking Float with no significant bits (evalf could not separate it from 0)."""
    if f == 0 and not isinstance(f, sp.Float):
        return "zero"
    prec = getattr(f, "_prec", None)
    if isinstance(f, sp.Float):
        return "value" if (prec is not None and prec >= _MIN_BITS and f != 0) else "unknown"
    if not getattr(f, "is_Number", False):
        # a residual evalf could not evaluate (re(gcd(pi, 2))): no sign; it was read as a nonzero
        # imaginary part, so gcd(pi, 2) = 1 was refuted and "!= 1" verified (audit of 29 Sep 2026)
        return "unknown"
    return "value" if f != 0 else "zero"


def _evalf_strict(e):
    """(real part, imaginary part, state_re, state_im) of a constant, or None when evalf fails.
    A part is trusted only when it carries significant bits: strict evalf may return a
    no-significance zero such as '-0.e-38' for the imaginary part of a real number written with
    complex radicals (the casus irreducibilis roots of x³ − 3x + 1) instead of raising."""
    from sympy.core.evalf import PrecisionExhausted
    try:
        v = e.evalf(_SIGN_DPS, strict=True)
    except PrecisionExhausted:
        return None
    except Exception:  # noqa: BLE001
        return None
    if not getattr(v, "is_number", False) or v.has(sp.nan, sp.zoo):
        return None
    try:
        re_, im_ = v.as_real_imag()
    except Exception:  # noqa: BLE001
        return None
    if not (re_.is_number and im_.is_number):
        return None
    return re_, im_, _part_state(re_), _part_state(im_)


_JUMPS = (sp.sign, sp.Abs, sp.floor, sp.ceiling, sp.frac, sp.Heaviside, sp.Mod)


def _closed_jump(n) -> bool:
    """Is `n` a sign, Abs, floor, ceiling, frac, Heaviside or Mod node whose arguments are constants, or a
    Piecewise whose conditions are (its branch is chosen by numbers: a jump too)?"""
    if isinstance(n, sp.Piecewise):
        return not any(getattr(c, "free_symbols", None) for _, c in n.args)
    return isinstance(n, _JUMPS) and not any(getattr(a, "free_symbols", None) for a in n.args)


def _jump_inputs(n) -> list:
    """What decides the jump node `n`: the conditions of a Piecewise, the arguments of the others."""
    return [c for _, c in n.args] if isinstance(n, sp.Piecewise) else list(n.args)


def _closed_truth(c, timeout: float):
    """The truth of a condition between constants (`Piecewise`), from CERTIFIED signs only; None when one is
    undecided. A relation of two numbers that are not certainly real decides only == and !=."""
    if c is sp.true or c is sp.false:
        return bool(c)
    if isinstance(c, sp.Not):
        t = _closed_truth(c.args[0], timeout)
        return None if t is None else not t
    if isinstance(c, (sp.And, sp.Or)):
        ts = [_closed_truth(a, timeout) for a in c.args]
        stop = isinstance(c, sp.Or)                # the value that decides the whole
        if stop in ts:
            return stop
        return (not stop) if all(t is (not stop) for t in ts) else None
    if not isinstance(c, sp.core.relational.Relational) or not isinstance(c.lhs, sp.Expr) \
            or not isinstance(c.rhs, sp.Expr):
        return None
    s = certified_sign(c.lhs - c.rhs, timeout)
    if s is None:
        return None
    if s == NONREAL:
        return False if isinstance(c, sp.Eq) else True if isinstance(c, sp.Ne) else None
    if isinstance(c, sp.Eq):
        return s == 0
    if isinstance(c, sp.Ne):
        return s != 0
    if isinstance(c, sp.StrictLessThan):
        return s < 0
    if isinstance(c, sp.LessThan):
        return s <= 0
    if isinstance(c, sp.StrictGreaterThan):
        return s > 0
    if isinstance(c, sp.GreaterThan):
        return s >= 0
    return None


def jump_value(n, timeout: float = 5.0):
    """The exact value of the jump node `n` (sign, floor, ceiling, frac, Heaviside, Mod of constant arguments;
    see `_closed_jump`), read from CERTIFIED signs and floors only; None when one is undecided. SymPy reads such
    a node off rounding noise: (2*atan(tanh(1/2)) - atan(sinh(1)))**2 is exactly 0 and its ceiling came out 1,
    its sign 1 (round 9 of part d4b, YO-4). Heaviside(0) is a convention (0, 1/2 or 1): undecided; so is a
    jump of a number not certainly real. A Piecewise takes the first branch whose condition is certainly true
    (Piecewise((1, Z**2 > 0), (0, Z**2 <= 0)) was certified 1 off the noise: a sibling of YO-4); no branch
    is undefined: undecided too."""
    if isinstance(n, sp.Piecewise):
        for v, c in n.args:
            t = _closed_truth(c, timeout)
            if t is None:
                return None
            if t:
                return v
        return None
    if isinstance(n, sp.Mod):
        p, q = n.args
        if certified_sign(q, timeout) not in (-1, 1):
            return None
        k = _certified_floor(p / q, timeout)
        return None if k is None else p - q * k
    u = n.args[0]
    if isinstance(n, (sp.sign, sp.Heaviside)):
        s = certified_sign(u, timeout)
        if s is None or s == NONREAL or (s == 0 and isinstance(n, sp.Heaviside)):
            return None
        return sp.Integer(s) if isinstance(n, sp.sign) else sp.Integer(1 if s > 0 else 0)
    k = _certified_floor(u, timeout)
    if k is None:
        return None
    if isinstance(n, sp.floor):
        return k
    if isinstance(n, sp.frac):
        return u - k
    return k if certified_sign(u - k, timeout) == 0 else k + 1


def undecided_jumps(*es, timeout: float = 5.0) -> bool:
    """Does one of `es` hold a sign, floor, ceiling, frac, Heaviside or Mod of constant arguments, or a Piecewise
    of constant conditions (`_closed_jump`), whose value no certified sign gives (`jump_value`)? Its rounded or simplified value is noise: sign((gd(1) - gd(1))**2) = 1
    was "proved" by simplify and 1 certified (round 9 of part d4b, YO-4); an equality with it decides nothing."""
    for e in es:
        try:
            e = sp.sympify(e)
        except (sp.SympifyError, TypeError):
            continue
        if not isinstance(e, sp.Basic):
            continue
        if any(_closed_jump(n) and not isinstance(n, sp.Abs) for n in sp.preorder_traversal(e)) \
                and _jumps_resolved(e, timeout) is None:
            return True
    return False


def _replaced(e, rep: dict):
    """`e` with the nodes of `rep` replaced, every jump node above them rebuilt unevaluated: a rebuilt ceiling of
    a constant would be read off rounding noise by SymPy again (it is resolved on the next pass instead)."""
    if e in rep:
        return rep[e]
    if not e.args:
        return e
    args = [_replaced(a, rep) for a in e.args]
    if all(a is b for a, b in zip(args, e.args)):
        return e
    return e.func(*args, evaluate=False) if isinstance(e, _JUMPS + (sp.Piecewise,)) else e.func(*args)


def _jumps_resolved(e, timeout: float):
    """`e` with every sign, Abs, floor, ceiling, frac, Heaviside, Mod of constant arguments and every Piecewise of
    constant conditions replaced by its exact value, read from the CERTIFIED sign of the argument (innermost first); None when one is undecided. Strict
    evalf of sign(z) gave 1.0 for a z that is exactly 0 written log(8)/log(2) - 3 (no precision is left to tell),
    so sign(x - 3) > 0 held at x = log(8)/log(2), and Abs of such a z left -1 + |z| undecided (round 8 of part
    d4b, RK-1 and RK-3). An Abs whose argument's sign is undecided is left to evalf (it is continuous), but not
    inside a jump: sign(|z|) for that z was read 1 off the noise, and the right 0 refuted (round 9, YO-4)."""
    for _ in range(64):
        nodes = [n for n in sp.preorder_traversal(e) if _closed_jump(n)
                 and not any(isinstance(m, _JUMPS + (sp.Piecewise,)) for a in _jump_inputs(n)
                             for m in sp.preorder_traversal(a))]
        rep = {}
        for n in dict.fromkeys(nodes):
            if isinstance(n, sp.Abs):
                s = certified_sign(n.args[0], timeout)
                if s in (-1, 0, 1):
                    rep[n] = s * n.args[0]
                continue
            v = jump_value(n, timeout)
            if v is None:
                return None
            rep[n] = v
        if not rep:
            # left: undecided Abs nodes only; no jump may stand above them
            if any(_closed_jump(n) and not isinstance(n, sp.Abs) for n in sp.preorder_traversal(e)):
                return None
            return e
        e = _replaced(e, rep)
    return None


def _certified_floor(u, timeout: float):
    """The integer floor of the real constant `u`, each comparison certified; None when undecided."""
    try:
        k = sp.Integer(int(sp.floor(sp.N(u, _SIGN_DPS))))
    except Exception:  # noqa: BLE001
        return None
    for cand in (k, k - 1, k + 1):
        lo, hi = certified_sign(u - cand, timeout), certified_sign(u - cand - 1, timeout)
        if lo is None or hi is None or NONREAL in (lo, hi):
            return None
        if lo >= 0 and hi < 0:
            return cand
    return None


_SESSION = threading.local()     # the certified signs read so far in one outermost call (nested readers ask again)


def certified_sign(e, timeout: float = 5.0):
    """Sign of a constant: -1, 0 or 1 when certified, NONREAL when it is certainly not real,
    None when it cannot be decided. Never a sign read off rounding noise."""
    try:
        e = sp.sympify(e)
    except (sp.SympifyError, TypeError):
        return None
    memo = getattr(_SESSION, "memo", None)
    if memo is None:
        _SESSION.memo = {}
        try:
            return _certified_sign(e, timeout)
        finally:
            _SESSION.memo = None
    try:
        return memo[e]
    except KeyError:
        s = memo[e] = _certified_sign(e, timeout)
        return s
    except TypeError:
        return _certified_sign(e, timeout)


def _zero_arguments_resolved(e, timeout: float):
    """`e` with every node SymPy's evalf does not track the accuracy of (asin, sinh, tanh, erf, ...: see
    `_sympy_guards`) whose argument is CERTIFIED 0 replaced by its exact value there (asin 0 = sinh 0 = tanh 0 =
    erf 0 = 0, cosh 0 = 1, acos 0 = pi/2), innermost first; a Max/Min whose arguments certified signs order, and
    an atan2 on an axis, by their value. Strict evalf read asin(log(6) - log(2) - log(3)) off rounding noise of
    its argument (a sign that changed with the precision), and ceiling(asin(Q)) = 1 was certified (round 9
    attack, YO-1); a guarded strict evaluation reads such a node only where its argument has a certified sign,
    and an argument that is exactly 0 has none there: its exact zero test is here."""
    from .._sympy_guards import tracked

    def picked(n):
        best = n.args[0]
        for a in n.args[1:]:
            s = certified_sign(a - best, timeout)
            if s not in (-1, 0, 1):
                return None
            if (s > 0) == isinstance(n, sp.Max) and s != 0:
                best = a
        return best

    def go(n):
        if not isinstance(n, sp.Expr) or not n.args or isinstance(n, (sp.CRootOf, sp.AlgebraicNumber)):
            return n
        args = [go(a) for a in n.args]
        if any(a is not b for a, b in zip(args, n.args)):
            n = n.func(*args)
        if tracked(n) or n.free_symbols or not isinstance(n, (sp.Function, sp.Max, sp.Min)):
            return n
        if isinstance(n, (sp.Max, sp.Min)):
            v = picked(n)
        elif isinstance(n, sp.atan2):
            sy, sx = certified_sign(n.args[0], timeout), certified_sign(n.args[1], timeout)
            v = {(0, 1): sp.S.Zero, (0, -1): sp.pi, (1, 0): sp.pi / 2, (-1, 0): -sp.pi / 2}.get((sy, sx))
        elif len(n.args) == 1 and certified_sign(n.args[0], timeout) == 0:
            v = n.func(sp.S.Zero)
        else:
            v = None
        if v is None or not v.is_number or v.has(type(n), sp.oo, sp.S.NegativeInfinity, sp.zoo, sp.nan):
            return n
        return v

    return go(e)


def _certified_sign(e, timeout: float):
    if getattr(e, "free_symbols", None):
        return None
    if e.has(sp.nan, sp.zoo):
        return None
    if e is sp.oo:
        return 1
    if e is sp.S.NegativeInfinity:
        return -1
    if e.has(sp.oo, sp.S.NegativeInfinity):
        return None
    if isinstance(e, sp.Rational):
        return int(sp.sign(e))
    e = real_odd_roots(e)
    e = _jumps_resolved(e, timeout)
    if e is None:
        return None
    e = _zero_arguments_resolved(e, timeout)
    if isinstance(e, sp.Rational):
        return int(sp.sign(e))
    s = _evalf_sign(e, timeout)
    if s is not _NOT_READ:
        return s
    if _in_sandbox_worker():
        # already inside the worker (e.g. the z3 translation): its caller holds the timeout, and
        # a daemonic worker cannot start a worker of its own
        try:
            return 0 if exact_zero_test(e) is True else None
        except Exception:  # noqa: BLE001
            return None
    from ..sandbox import run as sb_run
    r = sb_run("mathverify.equiv.numeric:exact_zero_test", e, timeout=timeout)
    if r.ok and r.value is True:
        return 0
    return None


_NOT_READ = object()       # strict evalf decided nothing: the exact zero test is left


def _evalf_sign(e, timeout: float):
    """The sign strict evalf certifies for `e`, read off `e` AND off `-e` when `e` is a sum: SymPy evaluates
    the two writings of one sum differently, and 3 - log(8)/log(2) - exp(-exp(10)) had no certified sign while
    its negation had 1, so exact_equal(3, b) was undecided and exact_equal(b, 3) False; an intersection then
    raised in one order only, and the domain dropped the constraint x >= 3 (round 9 of part d4b, YO-1). Two
    readings that disagree decide nothing (None). NONREAL for a part certainly not real; `_NOT_READ` when
    neither reading decides (the caller's exact zero test is left)."""
    reads = [p for p in (_evalf_strict(e),) if p is not None]
    if isinstance(e, sp.Add):
        q = _evalf_strict(-e)
        if q is not None:
            reads.append((-q[0], -q[1], q[2], q[3]))
    if not reads:
        return _NOT_READ
    ims = {p[3] for p in reads}
    if "value" in ims:
        return None if "zero" in ims else NONREAL
    if "zero" not in ims and not _imaginary_part_is_zero(e, timeout):
        return None
    signs = {1 if p[0] > 0 else -1 for p in reads if p[2] == "value"}
    if signs:
        # an exact zero against a sign, or two signs: no reading is certified
        return signs.pop() if len(signs) == 1 and not any(p[2] == "zero" for p in reads) else None
    if any(p[2] == "zero" and p[3] == "zero" for p in reads) and e.is_zero is True:
        return 0
    return _NOT_READ


def _in_sandbox_worker() -> bool:
    import multiprocessing
    try:
        return bool(multiprocessing.current_process().daemon)
    except Exception:  # noqa: BLE001
        return False


def _imaginary_part_is_zero(e, timeout: float) -> bool:
    """Is Im(e) PROVED to be 0? (a real number written with complex radicals)."""
    try:
        im_e = sp.im(e)
    except Exception:  # noqa: BLE001
        return False
    if im_e == 0:
        return True
    if _in_sandbox_worker():
        try:
            return exact_zero_test(im_e) is True
        except Exception:  # noqa: BLE001
            return False
    from ..sandbox import run as sb_run
    r = sb_run("mathverify.equiv.numeric:exact_zero_test", im_e, timeout=timeout)
    return bool(r.ok and r.value is True)


def exact_equal(a, b, timeout: float = 5.0) -> bool | None:
    """Exact equality of two constants: True only when a − b is PROVED to be 0, False when a
    certified evaluation separates them, None otherwise."""
    try:
        a, b = sp.sympify(a), sp.sympify(b)
    except (sp.SympifyError, TypeError):
        return None
    if a == b:
        return True
    try:
        d = a - b
    except Exception:  # noqa: BLE001
        return None
    s = certified_sign(d, timeout=timeout)
    if s is None:
        return None
    return s == 0


def certified_integer(c, timeout: float = 5.0):
    """(True, k) when the constant c is PROVED to equal the integer k, (False, None) when it is
    certainly not an integer, (None, None) when undecided. `is_integer` of an expression such as
    log(8)/log(2) is None, and treating None as "not an integer" dropped the only solution of
    x·log 2 = log 8 from an integer count (audit of 25 Sep 2026)."""
    try:
        c = sp.sympify(c)
    except (sp.SympifyError, TypeError):
        return None, None
    if isinstance(c, sp.Integer):
        return True, c
    if isinstance(c, sp.Rational):
        return False, None
    if getattr(c, "free_symbols", None) or c.has(sp.oo, sp.S.NegativeInfinity, sp.zoo, sp.nan):
        return None, None
    if c.is_integer is False:
        return False, None
    parts = _evalf_strict(real_odd_roots(c))
    if parts is None or parts[2] != "value":
        return None, None
    if parts[3] == "value":
        return False, None
    if parts[3] == "unknown" and not _imaginary_part_is_zero(real_odd_roots(c), timeout):
        return None, None
    re_ = parts[0]
    k = sp.Integer(int(sp.floor(re_ + sp.Rational(1, 2))))    # nearest integer to the value
    s = certified_sign(c - k, timeout=timeout)
    if s == 0:
        return True, k
    if s in (-1, 1):
        # c != k and |c - k| < 1 (certified): no other integer is that close
        far = certified_sign(sp.Abs(c - k) - 1, timeout=timeout)
        return (False, None) if far == -1 else (None, None)
    return None, None


def certified_floor(v, timeout: float = 5.0):
    """floor(v) for a real constant, certified (an exact integer value gives itself, never the
    integer below it through rounding); None when undecided or not a finite real."""
    try:
        v = sp.sympify(v)
    except (sp.SympifyError, TypeError):
        return None
    if isinstance(v, sp.Rational):
        return sp.floor(v)
    if getattr(v, "free_symbols", None) or v.has(sp.oo, sp.S.NegativeInfinity, sp.zoo, sp.nan):
        return None
    parts = _evalf_strict(real_odd_roots(v))
    if parts is None or parts[2] != "value" or parts[3] == "value" or (
            parts[3] == "unknown" and not _imaginary_part_is_zero(real_odd_roots(v), timeout)):
        is_int, k = certified_integer(v, timeout=timeout)
        return k if is_int else None
    re_ = parts[0]
    k = sp.Integer(int(sp.floor(re_ + sp.Rational(1, 2))))
    s = certified_sign(v - k, timeout=timeout)
    if s == 0:
        return k
    if s == 1 and certified_sign(v - k - 1, timeout=timeout) == -1:
        return k
    if s == -1 and certified_sign(v - k + 1, timeout=timeout) == 1:
        return k - 1
    return None


def real_odd_roots(e):
    """Odd roots read as REAL roots, the curriculum's convention: ∛(−8) = −2, x^(2/3) = ∛(x²).

    SymPy's x**(1/3) is the principal complex root, so ∛(−8) evaluated to 1 + 1.73i. The domain
    rules (`definedness_conditions`) and the z3 translation already treat an odd root as defined
    for negative bases; evaluating it on the principal branch contradicted them: the right answer
    ∛(−8) = −2 was refuted and x^(1/3) + 2 = 0 was certified to have no solution (audit of
    25 Sep 2026). A negative base becomes (−1)^p·|b|^(p/q); a base of unknown sign becomes
    sign(b)^p·|b|^(p/q)."""
    try:
        e = sp.sympify(e)
    except (sp.SympifyError, TypeError):
        return e
    if not getattr(e, "has", None) or not e.has(sp.Pow):
        return e

    def rewrite(p):
        b, ex = p.base, p.exp
        if not (isinstance(ex, sp.Rational) and not ex.is_Integer and ex.q % 2 == 1):
            return p
        if b.is_nonnegative:
            return p
        if b.is_negative:
            return sp.Pow(-b, ex) if ex.p % 2 == 0 else -sp.Pow(-b, ex)
        if b.is_extended_real is False:
            return p
        # even p: the real root of b^p is |b|^(p/q) (both vanish at b = 0); odd p: sign(b)·|b|^(p/q)
        return sp.Pow(sp.Abs(b), ex) if ex.p % 2 == 0 else sp.sign(b) * sp.Pow(sp.Abs(b), ex)

    return e.replace(lambda n: isinstance(n, sp.Pow), rewrite)


def to_mp(expr, dps: int):
    """Evaluate a constant sympy expression to mpf/mpc at `dps` digits. Raises on failure."""
    with mp.workdps(dps):
        if isinstance(expr, (int, float)):
            return mp.mpmathify(expr)
        expr = real_odd_roots(sp.sympify(expr))
        if expr.free_symbols:
            raise ValueError(f"expression has free symbols: {expr.free_symbols}")
        if expr.has(sp.Derivative):
            expr = expr.replace(lambda n: isinstance(n, sp.Derivative), lambda n: n.doit())
        if expr.has(sp.Integral, sp.Sum, sp.Product, sp.Limit):
            # neither SymPy's closed form (|cos x| on [-1, 1] integrates to 0) nor a bare numeric
            # evaluation (Euler-Maclaurin misses oscillating sums: Σ sin(πk/2)/k came out -2) is a
            # value here; callers confirm forms first (equiv.forms; audit of 29 Sep 2026)
            raise ValueError("an unevaluated integral, sum, product or limit has no confirmed value")
        if expr is sp.nan or expr is sp.zoo:
            raise ValueError("nan/zoo")
        if expr in (sp.oo, -sp.oo):
            return mp.inf if expr is sp.oo else -mp.inf
        # arbitrary-precision evalf first (lambdify would go through double-precision
        # Python complex for constants such as I**I — measured: only 15 digits)
        n = sp.N(expr, dps + 5)
        if n.has(sp.zoo, sp.nan):
            raise ValueError("nan/zoo")
        if n in (sp.oo, -sp.oo):
            return mp.inf if n is sp.oo else -mp.inf
        re_, im_ = n.as_real_imag()
        re_n, im_n = sp.N(re_, dps + 5), sp.N(im_, dps + 5)
        if not (re_n.is_number and im_n.is_number) or re_n.free_symbols or im_n.free_symbols:
            raise ValueError(f"could not evaluate {expr} numerically")
        try:
            v = mp.mpc(mp.mpf(str(re_n)), mp.mpf(str(im_n)))
        except Exception as e:  # pragma: no cover
            raise ValueError(f"mpmath conversion failed for {n}: {e}") from e
        if abs(v.imag) <= mp.mpf(10) ** (-(dps - 6)) * max(1, abs(v.real)):
            v = v.real
        return v


def _rel_diff(a, b):
    diff = abs(a - b)
    scale = max(abs(a), abs(b))
    if scale == 0:
        return mp.mpf(0)
    return diff / scale


def num_equal(a, b, rel_tol: float | None = None, abs_tol: float | None = None,
              dps_ladder=DPS_LADDER) -> tuple[bool | None, dict[str, Any]]:
    """Return (True|False|None, evidence).

    rel_tol: caller-declared tolerance (e.g. a problem that asks for 2 decimals). When
    None, the effective tolerance is 10^-(dps-10) at each rung of the ladder, i.e. the
    comparison is 'exact up to working precision'.
    """
    ev: dict[str, Any] = {"ladder": [], "rel_tol": rel_tol, "abs_tol": abs_tol}
    # Exact numbers are compared exactly. Measured: 10^30 + 1 and 10^30 were declared equal,
    # because their relative difference (1e-30) sits below the first rung's tolerance.
    try:
        sa, sb = sp.sympify(a), sp.sympify(b)
        if isinstance(sa, sp.Rational) and isinstance(sb, sp.Rational):
            ev["decided_by"] = "exact_rational"
            return bool(sa == sb), ev
    except (sp.SympifyError, TypeError):
        pass
    if undecided_jumps(a, b):
        # a jump at a constant no certified sign settles: its value at any precision is the noise's
        ev["decided_by"] = "jump_undecided"
        return None, ev
    prev_rel = None
    # Without a declared tolerance, EQUALITY must survive every rung: a true identity's
    # computed difference is rounding noise that shrinks as precision grows, a genuine small
    # difference does not. Stopping at the first rung that looked equal is how
    # e^(π√163) (= 262537412640768743.99999999999925…) was certified equal to the integer
    # 262537412640768744: relative gap 3e-30, under the 30-digit tolerance of 1e-20.
    strict = rel_tol is None and abs_tol is None
    # Two EXACT constants and no declared tolerance: equality is a fact about exact numbers and
    # is decided exactly (see certified_sign). Agreement at every rung was still accepted as
    # equality, and the 80-digit rung passes any relative gap below 1e-70: √(10¹⁰⁰ + 1) = 10⁵⁰,
    # tanh(100) = 1, atan(10⁸⁰) = π/2 and a 75-digit decimal for π were certified CORRECT
    # (audit of 25 Sep 2026). When neither a proof of zero nor a certified difference exists,
    # the answer is None — the caller abstains.
    if strict and not has_float(a, b):
        try:
            sa, sb = sp.sympify(a), sp.sympify(b)
            exact_ok = not (sa.free_symbols or sb.free_symbols) and not any(
                x_.has(sp.oo, sp.S.NegativeInfinity, sp.zoo, sp.nan) for x_ in (sa, sb))
        except (sp.SympifyError, TypeError, AttributeError):
            exact_ok = False
        if exact_ok:
            r = exact_equal(sa, sb)
            ev["decided_by"] = "exact" if r is not None else "exact_undecided"
            return r, ev
    passed_rungs = 0
    # inputs that are already finite-precision Floats cannot be compared tighter than
    # their own precision (a 15-digit Float vs pi: at most ~1e-15 agreement is possible)
    float_digits = [int(f._prec * 0.30103) for e in (a, b) if hasattr(e, "atoms")
                    for f in sp.sympify(e).atoms(sp.Float)]
    if float_digits:
        lim = mp.mpf(10) ** (-(min(float_digits) - 3))
        rel_tol = max(float(lim), rel_tol or 0.0)
        ev["float_precision_floor"] = mp.nstr(lim, 3)
    for dps in dps_ladder:
        try:
            va, vb = to_mp(a, dps), to_mp(b, dps)
        except Exception as e:
            ev["error"] = f"{type(e).__name__}: {e}"
            return None, ev
        with mp.workdps(dps):
            if (va in (mp.inf, -mp.inf)) or (vb in (mp.inf, -mp.inf)):
                same = (va == vb)
                ev["ladder"].append({"dps": dps, "a": str(va), "b": str(vb)})
                return bool(same), ev
            rel = _rel_diff(va, vb)
            absd = abs(va - vb)
            eff = mp.mpf(10) ** (-(dps - 10))
            if rel_tol is not None:
                eff = max(eff, mp.mpf(rel_tol))
            ev["ladder"].append({"dps": dps, "a": mp.nstr(va, 20), "b": mp.nstr(vb, 20),
                                 "rel_diff": mp.nstr(rel, 5), "eff_tol": mp.nstr(eff, 5)})
            if abs_tol is not None and absd <= mp.mpf(abs_tol):
                ev["decided_by"] = "abs_tol"
                return True, ev
            if rel <= eff:
                if not strict:
                    ev["decided_by"] = f"rel<=tol@dps{dps}"
                    return True, ev
                passed_rungs += 1
                if passed_rungs == len(dps_ladder):
                    ev["decided_by"] = f"rel<=tol at every rung (dps {dps_ladder})"
                    return True, ev
                prev_rel = rel
                continue
            if passed_rungs:
                # equal at a lower precision, different at this one: a genuine tiny difference
                ev["decided_by"] = f"difference_emerged@dps{dps}"
                return False, ev
            if rel > mp.mpf("1e-6"):
                ev["decided_by"] = f"clearly_different@dps{dps}"
                return False, ev
            # inconclusive: is the difference stable across precisions?
            if prev_rel is not None and mp.nstr(prev_rel, 3) == mp.nstr(rel, 3):
                ev["decided_by"] = "stable_difference"
                return False, ev
            prev_rel = rel
    ev["decided_by"] = "ladder_exhausted"
    return None, ev
