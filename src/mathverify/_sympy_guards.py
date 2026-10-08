"""Two guards on SymPy's numeric evaluation, installed when mathverify is imported (in the sandbox workers too).

1. A working-precision budget. SymPy's evalf of a sum raises its working precision in ONE step to what a
   cancellation asks for (`evalf_add`: prec + (target - accuracy)), with no ceiling: for
   log(8)/log(2) + exp(-exp(exp(5))) - 3 the step was about 4e64 bits, and computing log(2) to that precision
   never ends. A single verify of x**2 = 4 under x <= log(8)/log(2) + exp(-exp(exp(5))) ran past 90 s in the
   main process, out of every sandbox timeout (round 9 of part d4b). No evaluation runs above `PREC_CEILING`
   bits now: one that would raises PrecisionExhausted, which every certified reader takes as undecided
   (a strict evalf raises it anyway when the precision it may use does not separate a value from 0).
   2**16 bits keeps log(8)/log(2) + exp(-exp(10)) - 3 (about 31800 bits, 0.1 s) decidable; e^(-e^11) took
   0.4 s, e^(-e^12) 3.2 s and e^(-e^13) 22 s with the pure-Python mpmath backend (measured 8 Oct 2026).

2. Relations between numbers decided by a significant difference only. SymPy decides a < b, a <= b, a == b of
   two numbers from (a - b).evalf(2) without asking whether its digits are significant (`relational._n2`), and
   a power loses the "no significance" mark of its base: Z = 2*atan(tanh(1/2)) - atan(sinh(1)) is exactly 0
   (gd(1) written two ways), Z.evalf(2) is 0.e-111 without significance, but (Z**2).evalf(2) came out
   6.1e-238 carrying 10 bits, so Z**2 > 0 was True and Piecewise((1, Z**2 > 0), (0, Z**2 <= 0)) = 1 was
   certified, the right 0 refuted (round 9 of part d4b, a sibling of YO-4). The difference is now evaluated
   strictly, as SymPy's own `Pow._eval_power` does: an evaluation that cannot be trusted to 2 digits decides
   nothing and the relation stays unevaluated.
"""
from __future__ import annotations

import sympy.core.evalf as _evalf
import sympy.core.relational as _relational
from sympy.core.evalf import PrecisionExhausted

PREC_CEILING = 1 << 16          # bits of working precision any one SymPy evaluation may use


def _budgeted(inner):
    def evalf(x, prec, options):
        if prec > PREC_CEILING:
            raise PrecisionExhausted(f"a working precision of {prec} bits is over the budget of {PREC_CEILING}")
        return inner(x, prec, options)
    evalf.mathverify_guard = True        # type: ignore[attr-defined]
    evalf.inner = inner                  # type: ignore[attr-defined]
    return evalf


def _n2(a, b):
    """(a - b) evaluated to 2 significant digits when a and b are comparable and those digits are
    significant (a strict evaluation), else None: SymPy's own reading of the relation's truth. When a - b
    cannot be evaluated so, -(b - a) is: SymPy evaluates the two writings of one difference differently
    (log(8)/log(2) + exp(-exp(10)) - 3 to 1.1e-9566, its negation not at all), and N > 3 stayed unevaluated
    while N >= 3 was True (the relation reads b - a; equiv.numeric reads both writings too, YO-1)."""
    if not (a.is_comparable and b.is_comparable):
        return None
    for dif, sign in ((a - b, 1), (b - a, -1)):
        try:
            v = dif.evalf(2, strict=True)
        except PrecisionExhausted:
            continue
        if v.is_comparable:
            return v if sign == 1 else -v
    return None


_n2.mathverify_guard = True              # type: ignore[attr-defined]


def install() -> None:
    """Install both guards (idempotent)."""
    if not getattr(_evalf.evalf, "mathverify_guard", False):
        _evalf.evalf = _budgeted(_evalf.evalf)
    if not getattr(_relational._n2, "mathverify_guard", False):
        _relational._n2 = _n2


install()
