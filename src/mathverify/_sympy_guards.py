"""Guards on SymPy's numeric evaluation, installed when mathverify is imported (in the sandbox workers too).

1. A working-precision budget. SymPy's evalf of a sum raises its working precision in ONE step to what a
   cancellation asks for (`evalf_add`: prec + (target - accuracy)), with no ceiling: for
   log(8)/log(2) + exp(-exp(exp(5))) - 3 the step was about 4e64 bits, and computing log(2) to that precision
   never ends. A single verify of x**2 = 4 under x <= log(8)/log(2) + exp(-exp(exp(5))) ran past 90 s in the
   main process, out of every sandbox timeout (round 9 of part d4b). No evaluation runs above `PREC_CEILING`
   bits now. A STRICT evaluation (a certified reading) that would raises PrecisionExhausted, which every
   certified reader takes as undecided; any other evaluation is computed at the ceiling instead and carries
   the accuracy it reached. An exception out of a non-strict evaluation broke the parse of Abs, Max and
   Interval of log(8)/log(2) + exp(-exp(11)) - 3 and of everything holding them (round 9 attack, RK-2).
   2**17 bits keeps that number (86396 bits, 0.4 s) decidable; e^(-e^12) (about 235000 bits) stays undecided.

2. Strict evaluation tracks accuracy everywhere. SymPy's strict evalf checks the accuracy of the nodes it has an
   evaluator for (Add, Mul, Pow, exp, log, sin, cos, tan, atan, Abs, re, im, floor, ceiling, Piecewise and the
   number constants); any other node (asin, acos, acot, sinh, cosh, tanh, asinh, acosh, atanh, erf, gamma,
   atan2, Max, ...) is evaluated by `Function._eval_evalf` with its argument read WITHOUT accuracy tracking and
   reported at full precision: asin(log(6) - log(2) - log(3)), exactly 0, came out -5.8e-129, +1.25e-147 and
   -1.6e-201 at 15, 30 and 60 digits, and the sign of an exact 0 was certified (round 9 attack, YO-1). In strict
   mode such a node is now rewritten EXACTLY into tracked nodes on the part of its domain where its arguments
   are read with a certified sign (sinh u = (e^u - e^-u)/2, asin u = atan(u/sqrt(1 - u^2)) for |u| < 1,
   Max(a, b) = (a + b + |a - b|)/2, f(0) where the argument is exactly 0, exp_polar(z) = exp(z) on the principal
   sheet -pi < im z <= pi, ...), or the evaluation raises
   PrecisionExhausted. Sum, Product and Integral are not tracked either (a quadrature's error estimate is no
   proof): a Sum or Product over finitely many integer indices is written out. sin, cos, tan, atan and log read a complex argument by an untracked path or on a branch cut (log of
   -1 + i*noise is ±i*pi by the sign of the noise), and so does a non-integer power of a complex base: in
   strict mode that argument must be certainly real, and a complex base of a power certainly off the negative
   real axis. SymPy's log of a number near 1 does not check u - 1 (log(1 + e^(-200)) came out an exact 0): it
   is computed again as log1p(u - 1), u - 1 read strictly. A NotImplementedError inside a strict evaluation
   becomes PrecisionExhausted: EvalfMixin.evalf answers it by evaluating the whole expression again WITHOUT
   accuracy tracking and then "checking" the rounded result, which always passes.

3. Relations between numbers decided by a significant difference only. SymPy decides a < b, a <= b, a == b of
   two numbers from (a - b).evalf(2) without asking whether its digits are significant (`relational._n2`), and,
   when that gives nothing, from the assumption system (`is_extended_positive(a - b)`), whose numeric fallback
   (`Expr._eval_is_extended_positive_negative`) reads a non-strict evalf(2) too: Z = 2*atan(tanh(1/2)) -
   atan(sinh(1)) is exactly 0 (gd(1) written two ways) and Z**2 > 0, sin(Z)**2 > 0, tan((log(8)/log(2) - 3)**2)
   > 0 came out True, Piecewise((1, sin(Z)**2 > 0), (0, sin(Z)**2 <= 0)) = 1 was certified and the right 0
   refuted (round 9 of part d4b, YO-4, and its attack, YO-2). The relation, the assumption fallback, the
   numeric step of a relation's simplification and the nonzero test of `Expr.equals` (`_random`) of a closed
   number now read the STRICT value (2.): a relation between numbers is decided by a certified sign only, and
   stays unevaluated otherwise.
"""
from __future__ import annotations

import threading

import sympy as sp
import sympy.core.evalf as _evalf
import sympy.core.relational as _relational
from sympy.core.evalf import PrecisionExhausted
from sympy.core.expr import Expr

PREC_CEILING = 1 << 17          # bits of working precision any one SymPy evaluation may use

_LOCAL = threading.local()      # depth of the assumption fallback below (a strict reading may ask assumptions)
_MAX_DEPTH = 6
_SIGN_PREC = 64                 # bits a sign read inside a strict evaluation is certified to
# significant bits a part of a strict value needs to decide its sign: each part's accuracy measured against the error
# of the whole number (`_part_accuracies`); the threshold of `equiv.numeric._part_state` too
_PART_BITS = 20
# the working precision a rewritten node may climb to (SymPy's default for evalf(30) is 332 bits): asin(tanh(x)) at
# x = 300 asks 1 - tanh(x)**2 = 4e^(-600), some 870 bits of cancellation, to read |u| < 1
_REWRITE_MAXPREC = 1 << 11
_TRACKED: frozenset = frozenset()
_REAL_ARGUMENT = (sp.sin, sp.cos, sp.tan, sp.atan, sp.log)


def _tracked_types() -> frozenset:
    """The node types SymPy's evalf tracks the accuracy of (its evaluator table), less Sum, Product, Integral."""
    if not _evalf.evalf_table:
        _evalf._create_evalf_table()
    return frozenset(t for t in _evalf.evalf_table if t not in (sp.Sum, sp.Product, sp.Integral))


def tracked(x) -> bool:
    """Does SymPy's strict evalf track the accuracy of the node `x` itself (its evaluator table)?"""
    return type(x) in _TRACKED


def _exact_leaf(x) -> bool:
    """A number SymPy computes to the precision asked with no argument to lose it in: pi, E, GoldenRatio,
    EulerGamma, Catalan (NumberSymbol), oo, and a CRootOf (refined on an isolating interval)."""
    return (x.is_Atom and x.is_number) or isinstance(x, sp.CRootOf)


def _at_exact_arguments(x, prec):
    """A function of exact arguments (rationals and the number constants: erf(20000/3), gamma(1/3)) that no exact
    rewriting reads: mpmath's value at two working precisions, taken where they agree, at an accuracy short of that
    agreement (an argument rounded to the working precision moves the value by the condition number, and the two then
    disagree). YO-1 is an argument read off noise; these have none. The tuple of strict evalf, or None (a value not
    real, or 0: an exact zero is left to the exact tests)."""
    from mpmath.libmp import mpf_abs, mpf_lt, mpf_shift, mpf_sub
    if not isinstance(x, sp.Function) or not x.args or not all(
            a.is_Rational or isinstance(a, sp.NumberSymbol) for a in x.args):
        return None
    try:
        lo, hi = x._eval_evalf(prec + 30), x._eval_evalf(prec + 90)
    except Exception:  # noqa: BLE001 - no mpmath function, a pole, ...
        return None
    if not (getattr(lo, "is_Float", False) and getattr(hi, "is_Float", False)) or not hi:
        return None
    if mpf_lt(mpf_shift(mpf_abs(hi._mpf_), -(prec + 20)), mpf_abs(mpf_sub(lo._mpf_, hi._mpf_, prec + 100))):
        return None
    return hi._mpf_, None, prec + 20, None


def _sign(u, options):
    """-1, 0 or 1 when a strict evaluation of `u` certifies it, "nonreal" when its imaginary part is certainly
    nonzero, None otherwise (read inside a strict evaluation, through these guards)."""
    opts = {"maxprec": max(options.get("maxprec", 0), _REWRITE_MAXPREC), "strict": True, "chop": False, "room": True}
    if "subs" in options:
        opts["subs"] = options["subs"]
    try:
        r = _evalf.evalf(u, _SIGN_PREC, opts)
    except (PrecisionExhausted, NotImplementedError, ValueError, TypeError, ArithmeticError):
        return None
    if r is sp.S.ComplexInfinity:
        return None
    re_, im_, _, im_acc = r
    if im_ and im_[1]:
        return "nonreal" if im_acc is not None and im_acc >= _PART_BITS else None
    if not re_ or not re_[1]:
        return None if im_ else 0
    if re_ in (_evalf.fnan, _evalf.finf, _evalf.fninf):
        return None
    return -1 if re_[0] else 1


def _u(f, *args):
    return f(*args, evaluate=False)


def _half(e):
    return _u(sp.Mul, sp.S.Half, e)


def _neg(e):
    return _u(sp.Mul, sp.S.NegativeOne, e)


def _sub(a, b):
    return _u(sp.Add, a, _neg(b))


def _div(a, b):
    return _u(sp.Mul, a, _u(sp.Pow, b, sp.S.NegativeOne))


def _sqrt(e):
    return _u(sp.Pow, e, sp.S.Half)


def _exp(e):
    return _u(sp.exp, e)


def _asin_like(kind, u, s, options):
    """asin(u) / acos(u) of a real u of sign s: atan(u/sqrt(1 - u^2)) where |u| < 1, ±pi/2 (0, pi) at |u| = 1, None
    where |u| > 1 (not real) or undecided."""
    one_minus = _sub(sp.S.One, _u(sp.Pow, u, 2))
    d = _sign(one_minus, options)
    if d == 1:
        a = _u(sp.atan, _div(u, _sqrt(one_minus)))
        return a if kind == "asin" else _sub(sp.pi / 2, a)
    if d == 0:
        if kind == "asin":
            return sp.pi / 2 if s == 1 else -sp.pi / 2
        return sp.S.Zero if s == 1 else sp.pi
    return None


def _finite(x):
    """A Sum or Product over finitely many integer indices (at most 1000 terms), written out exactly; None otherwise
    (an infinite series is evaluated by an error estimate, no proof)."""
    n = 1
    for lim in x.limits:
        if len(lim) != 3 or not (lim[1].is_Integer and lim[2].is_Integer):
            return None
        n *= max(int(lim[2] - lim[1]) + 1, 0)
        if n > 1000:
            return None
    try:
        v = x.doit()
    except Exception:  # noqa: BLE001
        return None
    return v if getattr(v, "is_number", False) and not v.has(sp.Sum, sp.Product, sp.Integral) else None


def _rewritten(x, options):
    """`x`, a node SymPy's evalf does not track, rewritten EXACTLY into tracked nodes where its arguments are read
    with a certified sign; None when it cannot be (the strict evaluation then decides nothing)."""
    if isinstance(x, sp.UnevaluatedExpr):
        return x.args[0]
    if isinstance(x, (sp.Sum, sp.Product)):
        return _finite(x)
    if isinstance(x, (sp.Max, sp.Min)):
        if any(_sign(a, options) not in (-1, 0, 1) for a in x.args):
            return None                          # a lattice operation of real numbers only
        out = x.args[0]
        for a in x.args[1:]:
            d = _u(sp.Abs, _sub(out, a))
            out = _half(_u(sp.Add, out, a, d if isinstance(x, sp.Max) else _neg(d)))
        return out
    if isinstance(x, sp.atan2):
        y, z = x.args
        sy, sz = _sign(y, options), _sign(z, options)
        if sy not in (-1, 0, 1) or sz not in (-1, 0, 1):
            return None
        if sz == 0:
            return None if sy == 0 else (sp.pi / 2 if sy == 1 else -sp.pi / 2)
        a = _u(sp.atan, _div(y, z))
        if sz == 1:
            return a
        return _u(sp.Add, a, sp.pi) if sy >= 0 else _sub(a, sp.pi)
    if isinstance(x, sp.exp_polar):
        # a polar number on the principal sheet (-pi < im z <= pi) is the complex number exp(z), there and only there
        # (SymPy's own evalf of exp_polar reads it so): SymPy's exact exp (exp(I*pi) = -1). Off that sheet a log or a
        # root of it is not the principal one: undecided. Summation (hyperexpand, polar_lift) asks arg.eval whether
        # Mod(im(exp_polar(I*pi)), 2*pi) > pi; left standing, the sum of (-1)**k/k! = 1/e fell to UNKNOWN (merged
        # state of the fourth audit, d4e sonda W, 16 Oct 2026)
        z = x.args[0]
        try:
            iz = sp.im(z)
        except Exception:  # noqa: BLE001
            return None
        if _sign(iz + sp.pi, options) != 1 or _sign(sp.pi - iz, options) not in (0, 1):     # SymPy's exact sums
            return None
        return sp.exp(z)
    if not isinstance(x, sp.Function) or len(x.args) != 1:
        return None
    u = x.args[0]
    s = _sign(u, options)
    if s is None:
        return None
    if s == 0:
        try:
            v = x.func(sp.S.Zero)
        except Exception:  # noqa: BLE001
            return None
        if not getattr(v, "is_number", False) or v.has(x.func, sp.oo, -sp.oo, sp.zoo, sp.nan):
            return None
        return v
    f = type(x)
    if f in (sp.sinh, sp.cosh, sp.tanh, sp.coth, sp.sech, sp.csch):
        e1, e2 = _exp(u), _exp(_neg(u))
        if f is sp.sinh:
            return _half(_sub(e1, e2))
        if f is sp.cosh:
            return _half(_u(sp.Add, e1, e2))
        if f is sp.sech:
            return _div(sp.Integer(2), _u(sp.Add, e1, e2))
        if f is sp.csch:
            return _div(sp.Integer(2), _sub(e1, e2))
        e = _exp(_u(sp.Mul, sp.Integer(2), u))
        num, den = _sub(e, sp.S.One), _u(sp.Add, e, sp.S.One)
        return _div(num, den) if f is sp.tanh else _div(den, num)
    if s not in (-1, 1):
        return None                              # the rest: real arguments only (branch cuts)
    if f is sp.cot:
        return _div(_u(sp.cos, u), _u(sp.sin, u))
    if f is sp.sec:
        return _div(sp.S.One, _u(sp.cos, u))
    if f is sp.csc:
        return _div(sp.S.One, _u(sp.sin, u))
    if f is sp.acot:
        return _u(sp.atan, _div(sp.S.One, u))   # SymPy's acot of a real u != 0
    if f.__name__ == "arccot":                   # normalize.parse.arccot: values in (0, pi)
        return _sub(sp.pi / 2, _u(sp.atan, u))
    if f in (sp.asin, sp.acos):
        return _asin_like(f.__name__, u, s, options)
    if f in (sp.asec, sp.acsc):                  # asec u = acos(1/u), acsc u = asin(1/u)
        return _asin_like("acos" if f is sp.asec else "asin", _div(sp.S.One, u), s, options)
    if f is sp.asinh:                            # odd: the logarithm of a sum with no cancellation
        r = _u(sp.log, _u(sp.Add, _u(sp.Mul, sp.Integer(s), u), _sqrt(_u(sp.Add, _u(sp.Pow, u, 2), sp.S.One))))
        return r if s == 1 else _neg(r)
    if f is sp.acosh:
        d = _sign(_sub(u, sp.S.One), options)
        if d == 1:
            return _u(sp.log, _u(sp.Add, u, _sqrt(_sub(_u(sp.Pow, u, 2), sp.S.One))))
        return sp.S.Zero if d == 0 else None
    if f is sp.atanh:
        if _sign(_sub(sp.S.One, _u(sp.Pow, u, 2)), options) != 1:
            return None
        return _half(_sub(_u(sp.log, _u(sp.Add, sp.S.One, u)), _u(sp.log, _sub(sp.S.One, u))))
    if f is sp.acoth:
        if _sign(_sub(_u(sp.Pow, u, 2), sp.S.One), options) != 1:
            return None
        return _half(_u(sp.log, _div(_u(sp.Add, u, sp.S.One), _sub(u, sp.S.One))))
    return None


def _strict_inner(inner, x, prec, options):
    try:
        return _part_accuracies(inner(x, prec, options))
    except NotImplementedError as ex:
        raise PrecisionExhausted(f"no tracked evaluation of {type(x).__name__}") from ex


def _part_accuracies(r):
    """A strict evaluation's complex value with each part's accuracy measured against the absolute error of the
    WHOLE number: the bits a part has above the larger absolute error of the two (SymPy's `finalize_complex`
    accounts so, its product does not). SymPy's product of complex factors gives both parts the relative accuracy of
    the whole ("we aren't computing exact accuracies of the product", `evalf_mul`): -(1 + sqrt(3)*I)**3, exactly 8,
    came out 8.0 - 2.8e-26*I with 64 bits claimed for an imaginary part that is rounding noise of an exact 0 (its
    absolute error is the real part's, 2^-60). Read as significant it made -(1 + sqrt(3)*I)**3 "certainly not
    real" and "certainly not an integer", and a sum holding it inherited the claim (A+ final attack, G1YO-1, 16 Oct
    2026). The accuracy of the whole (`complex_accuracy`) is unchanged: no reading that decided fails here."""
    if not isinstance(r, tuple) or len(r) != 4:
        return r
    re_, im_, re_acc, im_acc = r
    if not (re_ and im_ and re_[1] and im_[1]) or re_acc is None or im_acc is None:
        return r                    # a real or imaginary number, an exact 0 part, nan or an infinity: nothing to share
    size_re, size_im = _evalf.fastlog(re_), _evalf.fastlog(im_)
    err = max(size_re - re_acc, size_im - im_acc)
    return re_, im_, min(re_acc, size_re - err), min(im_acc, size_im - err)


def _read_real(z, prec, options) -> bool:
    """Is `z` real by a strict evaluation (an imaginary part that is exactly none, the real part significant)? Where
    the assumptions cannot tell: u/sqrt(1 - u**2) of asin's rewriting at u = tanh(486), 1 - u**2 = 1e-422."""
    opts = {"maxprec": max(options.get("maxprec", 0), _REWRITE_MAXPREC), "strict": True, "chop": False, "room": True}
    try:
        r = _evalf.evalf(z, prec + 10, opts)
    except (PrecisionExhausted, NotImplementedError, ValueError, TypeError, ArithmeticError):
        return False
    return r is not sp.S.ComplexInfinity and not r[1] and bool(r[0]) and r[0] not in (_evalf.fnan, _evalf.finf,
                                                                                        _evalf.fninf)


def _off_the_cut(z, prec, options) -> bool:
    """Is the complex number `z` certainly off the negative real axis (the branch cut of a power): its imaginary part
    read with significant bits of its own? A part of noise ((-1 + i*(log 6 - log 2 - log 3))**(1/2)) is ±i by its sign;
    the cube roots of a casus irreducibilis ((27/2 + 27*sqrt(3)*I/2)**(1/3)) have one."""
    opts = {"maxprec": max(options.get("maxprec", 0), _REWRITE_MAXPREC), "strict": True, "chop": False, "room": True}
    try:
        r = _evalf.evalf(z, prec + 10, opts)
    except (PrecisionExhausted, NotImplementedError, ValueError, TypeError, ArithmeticError):
        return False
    if r is sp.S.ComplexInfinity:
        return False
    _, im_, _, im_acc = r
    return bool(im_ and im_[1] and im_acc is not None and im_acc >= _PART_BITS)


def _log_near_one(inner, x, prec, options):
    """log(u) where SymPy's evaluator reads u - 1 without checking it: at u = 1 + e^(-200) it returned an exact 0, and
    log(1 + e^(-200)) - e^(-200)/2 > 0 was certified negative; at u = 1 + (an exact 0 written as a sum) a value read
    off noise. A logarithm smaller than 2**-8 is computed again as log1p(u - 1), u - 1 read strictly (undecided when it
    cannot be told from 0)."""
    r = _strict_inner(inner, x, prec, options)
    if r is sp.S.ComplexInfinity or r[1]:
        return r                                  # a negative argument: log|u| + i*pi, |u| = -u
    re_ = r[0]
    if re_ and re_[1] and _evalf.fastlog(re_) > -8:
        return r
    u = x.args[0]
    if u == 1:
        return r
    opts = {"maxprec": max(options.get("maxprec", 0), _REWRITE_MAXPREC), "strict": True, "chop": False, "room": True}
    d = _evalf.evalf(sp.Add(u, sp.S.NegativeOne, evaluate=False), prec + 20, opts)   # raises if u - 1 is not read
    if d is sp.S.ComplexInfinity or d[1]:
        raise PrecisionExhausted("log near 1 of a number not certainly real")
    if not d[0] or not d[0][1]:
        return None, None, None, None             # u - 1 exactly 0
    import mpmath
    with mpmath.workprec(prec + 30):
        v = mpmath.log1p(mpmath.mpf(d[0]))
    return v._mpf_, None, prec, None


def _evaluated_real(r) -> bool:
    """Is the strict value `r` real: no imaginary part at all (SymPy's exact 0)?"""
    return r is not sp.S.ComplexInfinity and not r[1]


def _clear_of_the_cut(r) -> bool:
    """Is the strict value `r` of a REAL base clear of the branch cut of a power: real (SymPy's power reads a real
    base exactly, a negative one on the principal branch), or with a real part certainly positive (a part of noise
    beside it moves the power by noise only)? A real base evaluated with an imaginary part of noise and a negative real
    part is ±i by the sign of that noise."""
    if r is sp.S.ComplexInfinity:
        return False
    re_, im_, re_acc, _ = r
    if not im_:
        return True
    return bool(re_ and re_[1] and not re_[0] and re_acc is not None and re_acc >= _PART_BITS)


# options key: (node, test, reason) a node's strict evaluation asks of the strict value of one of its arguments, read
# where that argument is evaluated (SymPy's evaluator evaluates it with the options it was given)
_ASKED = "mathverify_asked"


def _guarded(inner):
    def evalf(x, prec, options):
        if prec > PREC_CEILING:
            if options.get("strict"):
                raise PrecisionExhausted(f"a working precision of {prec} bits is over the budget of {PREC_CEILING}")
            prec = PREC_CEILING
        if not options.get("strict"):
            return inner(x, prec, options)
        asked = options.get(_ASKED)
        r = strict(x, prec, options)
        if asked is not None and asked[0] is x and not asked[1](r):
            raise PrecisionExhausted(asked[2])
        return r

    def strict(x, prec, options):
        t = type(x)
        if t not in _TRACKED:
            if _exact_leaf(x):
                return _strict_inner(inner, x, prec, options)
            y = _rewritten(x, options)
            if y is None:
                r = _at_exact_arguments(x, prec)
                if r is None:
                    raise PrecisionExhausted(f"{t.__name__} does not track the accuracy of its value")
                return r
            # with room for the cancellation the rewriting itself makes (1 - u**2 of asin): every sum below gets it
            # (SymPy's sum lowers the bound of the sums inside it to twice its own precision)
            return evalf(y, prec, dict(options, maxprec=max(options.get("maxprec", 0), _REWRITE_MAXPREC), room=True))
        # An argument SymPy knows real is still evaluated as SymPy writes it: (1 + sqrt(3)*I)**3, exactly -8, is
        # -8.0 + 0.e-22*I, and sin, cos, tan read such an argument by the untracked complex path (sin(pi*z**3/8), exactly
        # 0, came out -6.6e-22 with 53 bits), log and a power on the branch cut by the sign of the noise
        # (log(z**3) = log(8) - i*pi, sqrt(-z**3 - 16) = -2*sqrt(2)*i). Where it is evaluated, its strict value must
        # be real (a power's base: real, or off the cut by a real part certainly positive); A+ final attack, G1YO-1.
        if t in _REAL_ARGUMENT:
            if x.args[0].is_extended_real is not True:
                if not _read_real(x.args[0], prec, options):
                    raise PrecisionExhausted(f"{t.__name__} of an argument not certainly real")
            else:
                options = dict(options, **{_ASKED: (x.args[0], _evaluated_real,
                                                    f"{t.__name__} of a real argument evaluated with an imaginary part")})
        if t is sp.Pow and not x.exp.is_Integer:
            if x.base.is_extended_real is not True:
                if not _off_the_cut(x.base, prec, options):
                    raise PrecisionExhausted("a non-integer power of a base on or near the negative real axis")
            else:
                options = dict(options, **{_ASKED: (x.base, _clear_of_the_cut,
                                                    "a non-integer power of a real base evaluated on the branch cut")})
        if t is sp.log:
            return _log_near_one(inner, x, prec, options)
        if t is sp.Add and options.get("room"):
            options = dict(options, maxprec=max(options.get("maxprec", 0), _REWRITE_MAXPREC))
        return _strict_inner(inner, x, prec, options)

    evalf.mathverify_guard = True        # type: ignore[attr-defined]
    evalf.inner = inner                  # type: ignore[attr-defined]
    return evalf


def strict_value(e, dps: int):
    """`e` evaluated strictly to `dps` digits (through the guards above), or None when that decides nothing."""
    try:
        v = e.evalf(dps, strict=True)
    except (PrecisionExhausted, NotImplementedError, ValueError, TypeError, ArithmeticError, RecursionError):
        return None
    return v if getattr(v, "is_number", False) and not v.has(sp.nan, sp.zoo) else None


def strict_sign(e):
    """1, -1, 0 (strictly read), "nonreal", or None: what every guarded relation of numbers decides from.

    A part decides only with significant bits of its own (`_part_sign`, the threshold of `_sign` and of
    `equiv.numeric._part_state`). SymPy measures the accuracy of a complex value by its larger part: an integer
    power of a complex base that is real came out -8.0 + 0.e-22*I for (1 + sqrt(3)*I)**3, an imaginary part of
    1 bit, pure rounding noise. Read as "nonreal", the assumption fallback below called the number neither positive
    nor negative while SymPy knows it real (arg/pi rational), so (1 + sqrt(3)*I)**3 - 5 was zero: Eq(X, 5) was True,
    simplify(X - 5) was 0, Abs(X + 30) was 0, and (1 + i*sqrt(3))**3 = 5 was certified CORRECT (A+ final attack,
    G1YO-1, 16 Oct 2026). An imaginary part of noise is neither real nor nonreal: undecided."""
    v = strict_value(e, 15)
    if v is None:
        return None
    try:
        re_, im_ = v.as_real_imag()
    except Exception:  # noqa: BLE001
        return None
    if not ((re_.is_Rational or re_.is_Float) and (im_.is_Rational or im_.is_Float)):
        return None
    s_im = _part_sign(im_)
    if s_im is None:
        return None
    if s_im:
        return "nonreal"
    return _part_sign(re_)


def _n2(a, b):
    """(a - b) evaluated to 2 significant digits when a and b are comparable and those digits are
    significant (a strict evaluation), else None: SymPy's own reading of the relation's truth. When a - b
    cannot be evaluated so, -(b - a) is: SymPy evaluates the two writings of one difference differently
    (log(8)/log(2) + exp(-exp(10)) - 3 to 1.1e-9566, its negation not at all), and N > 3 stayed unevaluated
    while N >= 3 was True (the relation reads b - a; equiv.numeric reads both writings too, YO-1). A strict
    reading is certified: the second writing is read only when the first decides nothing (a relation is asked
    often: SymPy joins the intervals of a union pair by pair)."""
    if not (a.is_comparable and b.is_comparable):
        return None
    for dif, sign in ((a - b, 1), (b - a, -1)):
        v = strict_value(dif, 2)
        if v is not None and (v.is_Rational or v.is_Float):
            return v if sign == 1 else -v
    return None


def _number_sign(v) -> int:
    """The sign of a Rational or Float, read off its value (no relation: a relation would come back here)."""
    if v.is_Rational:
        return (v.p > 0) - (v.p < 0)
    m = v._mpf_
    return 0 if not m[1] else (-1 if m[0] else 1)



def _part_sign(v):
    """The sign of one part of a strict value: a Rational's (an exact part, evalf's exact 0 included), a Float's
    only when it carries `_PART_BITS` significant bits; None for a Float of noise (its digits, its sign, even its
    being nonzero, are rounding) and for a Float 0 (strict evalf writes an exact 0 as the Integer 0)."""
    if v.is_Rational:
        return _number_sign(v)
    m = v._mpf_
    if not m[1] or getattr(v, "_prec", 0) < _PART_BITS:
        return None
    return -1 if m[0] else 1


_n2.mathverify_guard = True              # type: ignore[attr-defined]


def _positive_negative(self, positive):
    """SymPy's numeric fallback of `is_extended_positive`/`is_extended_negative` of a number, from a STRICT
    reading (it read a non-strict evalf(2): sin(Z) of an exact 0 Z came out -9.3e-156 with 10 bits, so
    sin(Z)**2 > 0; round 9 attack, YO-2). An algebraic number with no function whose minimal polynomial is t
    is 0 (SymPy's own exact test, kept). For a number SymPy knows real, neither positive nor negative is ZERO (its
    deduction): a strict reading that calls such a number not real contradicts SymPy and decides nothing
    ((1 + sqrt(3)*I)**3 - 5 was 0 so, off an imaginary part of noise; A+ final attack, G1YO-1)."""
    if not self.is_number:
        return None
    depth = getattr(_LOCAL, "depth", 0)
    if depth >= _MAX_DEPTH:
        return None
    _LOCAL.depth = depth + 1
    try:
        s = strict_sign(self)
        if s == "nonreal" and self.is_extended_real is True:
            s = None
    finally:
        _LOCAL.depth = depth
    if s == "nonreal":
        return False
    if s is not None:
        return s == (1 if positive else -1)
    from sympy.polys.numberfields import minimal_polynomial
    from sympy.polys.polyerrors import BasePolynomialError
    try:
        if self._eval_is_algebraic() and not self.has(sp.Function) and minimal_polynomial(self).is_Symbol:
            return False
    except (BasePolynomialError, NotImplementedError, ValueError, TypeError, AttributeError):
        # any failure of the polynomial machinery decides nothing: its PolynomialError on a power whose exponent
        # SymPy's cache kept from an as-written reading (x**(2/1**1)) escaped here and failed the whole
        # as-written parse of at(diff(Abs(x**2 - 4), x), x, 3), now and then (attack on the last diff, lens 3)
        pass
    return None


_positive_negative.mathverify_guard = True   # type: ignore[attr-defined]


def _guarded_simplify(inner):
    def _eval_simplify(self, **kwargs):
        """A relation of two numbers keeps its truth to a certified sign (SymPy reads (lhs - rhs).n(2))."""
        lhs, rhs = (self.args + (None, None))[:2]
        if not (isinstance(lhs, Expr) and isinstance(rhs, Expr)) or lhs.free_symbols or rhs.free_symbols:
            return inner(self, **kwargs)
        r = self.func(*[i.simplify(**kwargs) for i in self.args])
        if not r.is_Relational or not (isinstance(r.lhs, Expr) and isinstance(r.rhs, Expr)):
            return r
        dif = r.lhs - r.rhs
        s = strict_sign(dif)
        if s is None and dif.is_number and dif.equals(0):
            s = 0
        if s in (-1, 0, 1):
            return r.func(sp.Integer(s), sp.S.Zero)
        if s == "nonreal" and isinstance(r, (sp.Eq, sp.Ne)):
            return sp.false if isinstance(r, sp.Eq) else sp.true
        return r
    _eval_simplify.mathverify_guard = True   # type: ignore[attr-defined]
    _eval_simplify.inner = inner             # type: ignore[attr-defined]
    return _eval_simplify


def _guarded_random(inner):
    def _random(self, n=None, re_min=-1, im_min=-1, re_max=1, im_max=1):
        """A closed number's value only when strictly read (`Expr.equals` calls a number nonzero off it)."""
        if self.free_symbols:
            return inner(self, n, re_min, im_min, re_max, im_max)
        return strict_value(self, 15)
    _random.mathverify_guard = True          # type: ignore[attr-defined]
    _random.inner = inner                    # type: ignore[attr-defined]
    return _random


def _strict_integer_part(expr, no, options, return_ints=False):
    """SymPy's floor/ceiling of a number formed at construction (RoundFunction.eval passes empty options, so a
    non-strict evaluation): the integer part read STRICTLY, through the guards; where none decides it,
    PrecisionExhausted leaves the node unevaluated. Off rounding noise ceiling(Z**2), Z = 2*atan(tanh(1/2)) -
    atan(sinh(1)) exactly 0, came out 1, and the true step y = ceiling(x**2) at x = Z, y = 0 was refuted (round 9
    attack on part d4b, e9 S2; the evaluation of floor/ceiling by evalf is the guarded one already)."""
    return _INTEGER_PART(expr, no, dict(options, strict=True), return_ints)


_strict_integer_part.mathverify_guard = True     # type: ignore[attr-defined]
_INTEGER_PART = _evalf.get_integer_part


def _guarded_mul_even(inner):
    def _eval_is_even(self):
        """A product with an exactly-0 factor is 0, and 0 is even, when every other factor is finite; None when one
        may be infinite (0*oo). SymPy 1.14's Mul._eval_is_even said False for the unevaluated 0*x that a reading as
        written builds, and asked before is_zero it made the cached 0*x nonzero (not even => not zero): the
        written definedness of later verifies then depended on what an earlier one had asked (the order of the
        cases, PYTHONHASHSEED; d4e round 5 and the d4b closure, 16 Oct 2026). Every other assumption handler of
        Mul agrees with 0 on such a product (measured)."""
        if any(a is sp.S.Zero for a in self.args):
            return True if all(a.is_finite is True for a in self.args if a is not sp.S.Zero) else None
        return inner(self)
    _eval_is_even.mathverify_guard = True    # type: ignore[attr-defined]
    _eval_is_even.inner = inner              # type: ignore[attr-defined]
    return _eval_is_even


def install() -> None:
    """Install the guards (idempotent)."""
    import sympy.functions.elementary.integers as _integers
    global _TRACKED
    _TRACKED = _tracked_types()
    if not getattr(_evalf.evalf, "mathverify_guard", False):
        _evalf.evalf = _guarded(_evalf.evalf)
    if not getattr(_relational._n2, "mathverify_guard", False):
        _relational._n2 = _n2
    if not getattr(Expr._eval_is_extended_positive_negative, "mathverify_guard", False):
        Expr._eval_is_extended_positive_negative = _positive_negative
    rel = _relational.Relational
    if not getattr(rel._eval_simplify, "mathverify_guard", False):
        rel._eval_simplify = _guarded_simplify(rel._eval_simplify)
    if not getattr(Expr._random, "mathverify_guard", False):
        Expr._random = _guarded_random(Expr._random)
    if not getattr(_integers.get_integer_part, "mathverify_guard", False):
        _integers.get_integer_part = _strict_integer_part
    if not getattr(sp.Mul._eval_is_even, "mathverify_guard", False):
        sp.Mul._eval_is_even = _guarded_mul_even(sp.Mul._eval_is_even)
        sp.Mul._prop_handler["even"] = sp.Mul._eval_is_even    # the handler table is built with the class


install()
