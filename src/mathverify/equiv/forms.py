"""SymPy's value of a closed integral, sum or product, taken only when numbers confirm it.

SymPy's `doit` is a CAS computation, not a proof: it integrates |cos x| over [-1, 1] to 0 (the value
is 2 sin 1). Every path that evaluated such a form trusted it: an `evaluate` task with that integral
and the claim 0 was certified CORRECT, a `compute` step claiming it was "verified", and the exact
comparison of a step refuted the true claim 2 sin 1 (audit of 29 Sep 2026). The `definite_integral`
certificate already cross-checks with a numeric integral and abstains on a disagreement; this module
does the same for a form inside any expression.

A form is CLOSED when it has no free symbol (its variable is bound). Each closed form, innermost
first, is replaced by SymPy's value when an independent numeric evaluation of the UNEVALUATED form
agrees with it: tanh-sinh with breakpoints for an integral of one variable (the certificate's
integrator), SymPy's numeric summation for a sum, the product of the terms for a finite product.
SymPy's exact 0 for such an integral, and a 0 it has no value for, is taken only with a symbolic
certificate (`certify.calculus.certified_integral_value`): numbers never show that a value is 0.
An evalf value is taken only with the significant bits evalf itself vouches for.
Otherwise `UnverifiedForm` is raised and the caller abstains. Forms with a free symbol are left as
they are: no number can check them here.
"""
from __future__ import annotations

from typing import Any

import sympy as sp

from ..normalize.parse import entries, map_entries, unhold

__all__ = ["UnverifiedForm", "has_closed_form", "has_parametric_form", "checked_forms"]

_FORMS = (sp.Integral, sp.Sum, sp.Product, sp.Limit)
_MAX_TERMS = 10_000
_MIN_BITS = 100            # significant bits evalf must vouch for (40 digits asked: 136)


class UnverifiedForm(ValueError):
    """A closed integral, sum or product whose SymPy value no numeric evaluation confirms."""


def _closed(n) -> bool:
    return isinstance(n, _FORMS) and not n.free_symbols


def has_closed_form(e) -> bool:
    """Does `e`, or an entry of it (a matrix, a list or a tuple: `normalize.parse.entries`), hold a closed
    form? A Matrix is no Basic, and Matrix([[Limit(2*n*sin(pi/n), n, oo)]]) was compared with SymPy's 0 for
    its entry unconfirmed (fourth audit H1)."""
    return any(_closed(n) for x in entries(e) for n in sp.preorder_traversal(x))


def _innermost(e) -> list:
    return [n for n in sp.preorder_traversal(e) if _closed(n)
            and not any(isinstance(m, _FORMS) for a in n.args for m in sp.preorder_traversal(a))]


def _finite_integral(n) -> bool:
    """A closed integral of one variable over a finite range (the certificate's integrator's case)."""
    return isinstance(n, sp.Integral) and len(n.limits) == 1 and len(n.limits[0]) == 3 \
        and bool(n.limits[0][1].is_finite) and bool(n.limits[0][2].is_finite)


def _numeric(n, timeout: float) -> tuple[Any, float] | None:
    """(value, relative tolerance) of the unevaluated form from numbers alone, or None."""
    from ..sandbox import run as sb_run
    if isinstance(n, sp.Integral):
        if len(n.limits) != 1 or len(n.limits[0]) != 3:
            return None
        var, a, b = n.limits[0]
        if a.is_finite and b.is_finite:
            from ..certify.calculus import definite_integral_numeric
            val, ev = definite_integral_numeric(n.function, var, a, b, timeout=timeout)
            if val is None or not ev.get("converged"):
                return None
            return val, max(float(ev.get("rel_err", "1e-18")), 1e-25)
        # an infinite range: mpmath's own quadrature through evalf (the certificate's integrator
        # takes finite limits); a value it misses disagrees with SymPy's and nothing is decided
        r = sb_run("mathverify.sandbox.ops:numeric_value_bits", n, 40, timeout=timeout)
        tol = 1e-15
    elif isinstance(n, sp.Product):
        if len(n.limits) != 1:
            return None
        k, lo, hi = n.limits[0]
        if not (lo.is_Integer and hi.is_Integer) or hi - lo + 1 > _MAX_TERMS:
            return None
        terms = [n.function.subs(k, i) for i in range(int(lo), int(hi) + 1)]
        r = sb_run("mathverify.sandbox.ops:numeric_value_bits", sp.Mul(*terms, evaluate=False), 40, timeout=timeout)
        tol = 1e-25
    else:
        r = sb_run("mathverify.sandbox.ops:numeric_value_bits", n, 40, timeout=timeout)
        tol = 1e-25
    if not r.ok or not isinstance(r.value, tuple):
        return None
    # evalf's own accuracy: the Dirichlet integral came out '-0.e+0' (1 bit) and ∫_0^oo sin²x/x² as '1.6'
    # (9 bits), each read as a 40-digit value with tolerance 1e-15, and true steps "∫_0^oo sin x/x dx = π/2"
    # were refuted (fourth audit of 1 Oct 2026, S3). No bits (None): an exact number.
    s_, bits = r.value
    if bits is not None and bits < _MIN_BITS:
        return None
    try:
        v = sp.Float(s_, 40)                 # the op prints a number; anything else is no value
    except (TypeError, ValueError):
        return None
    return (v, tol) if v.is_finite else None


def has_parametric_form(e) -> bool:
    """Does `e` hold an Integral or a Limit with a free symbol (a parameter, or the variable of an
    antiderivative)? No number checks SymPy's value of one: agreement at sample points of the
    parameter is no proof (DECISIONS §80, principle 4)."""
    return any(isinstance(n, (sp.Integral, sp.Limit)) and n.free_symbols
               for x in entries(e) for n in sp.preorder_traversal(x))


def checked_forms(e, timeout: float = 8.0):
    """`e` with every closed Integral/Sum/Product replaced by SymPy's value confirmed by numbers
    (see the module docstring). Raises UnverifiedForm when SymPy has no value for one or the numbers
    do not confirm it."""
    from ..sandbox import run as sb_run
    from .numeric import num_equal
    if not has_closed_form(e):
        return e
    if not isinstance(e, sp.Basic):
        return map_entries(e, lambda x: checked_forms(x, timeout))
    for _ in range(8):
        inner = _innermost(e)
        if not inner:
            if has_closed_form(e):
                # a closed form whose inner forms are open (their variable is the outer one's):
                # nothing checks it, and SymPy's doit of it was certified (third audit, 30 Sep 2026)
                raise UnverifiedForm(f"a closed form over open inner forms: {e}")
            return e
        reps = {}
        for key in inner:
            # a held form (normalize.parse.HeldIntegral/HeldLimit: written with a parameter that now
            # has a value) is checked as the plain form; its own doit never computes
            n = unhold(key)
            if isinstance(n, sp.Limit):
                # SymPy's limit, corroborated numerically near the point and two-sided unless a side
                # is written (certify.limits): with n an integer SymPy says lim n·sin(π/n) = 0 (π)
                from ..certify.limits import classify_limit
                e_, v_, p_, d_ = n.args
                cls = classify_limit(e_, v_, p_, None if str(d_) in ("+-", "real") else str(d_), timeout=timeout)
                if cls.get("kind") not in ("VAR", "INF") or cls.get("value") is None:
                    raise UnverifiedForm(f"{n}: {cls.get('kind')}")
                reps[key] = cls["value"]
                continue
            r = sb_run("mathverify.sandbox.ops:doit_expr", n, timeout=timeout)
            closed = r.ok and isinstance(r.value, sp.Basic) and not r.value.has(*_FORMS) \
                and not r.value.has(sp.nan, sp.zoo) and not r.value.free_symbols
            if isinstance(n, sp.Integral) and len(n.limits) == 1 and len(n.limits[0]) == 3 \
                    and (not closed or r.value == 0):
                # an exact 0 needs a symbolic certificate: no number shows a value is 0 (2π·I_50(1) =
                # 1.8e-79 passed the residue test) and SymPy's 0 for ∫_{-1}^{1} (x + |cos x|/10^80) dx
                # is wrong (fourth audit of 1 Oct 2026, S1); the certificate also finds a value SymPy
                # has none for (∫_0^{2π} sin(sin x) dx = 0, odd about π)
                from ..certify.calculus import certified_integral_value
                var, a, b = n.limits[0]
                cval, cev = certified_integral_value(n.function, var, a, b, timeout=timeout)
                if cval is not None:
                    reps[key] = cval
                    continue
                if closed:
                    raise UnverifiedForm(f"{n}: SymPy 0 without a certificate ({cev.get('reason')})")
            if not closed:
                raise UnverifiedForm(f"SymPy has no closed value for {n}")
            num = _numeric(n, timeout)
            if num is None:
                raise UnverifiedForm(f"no numeric value checks SymPy's value of {n}")
            val, tol = num
            if r.value in (sp.oo, -sp.oo) or val in (sp.oo, -sp.oo):
                if r.value != val:
                    raise UnverifiedForm(f"{n}: SymPy {r.value}, numbers {val}")
            else:
                ok, _ = num_equal(r.value, val, rel_tol=tol)
                if ok is not True:
                    raise UnverifiedForm(f"{n}: SymPy {r.value}, numbers {sp.N(val, 20)}")
            reps[key] = r.value
        e = e.xreplace(reps)
    if has_closed_form(e):
        raise UnverifiedForm(f"too deeply nested: {e}")
    return e
