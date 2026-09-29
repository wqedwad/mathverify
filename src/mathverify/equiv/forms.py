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
Otherwise `UnverifiedForm` is raised and the caller abstains. Forms with a free symbol are left as
they are: no number can check them here.
"""
from __future__ import annotations

from typing import Any

import sympy as sp

__all__ = ["UnverifiedForm", "has_closed_form", "checked_forms"]

_FORMS = (sp.Integral, sp.Sum, sp.Product)
_MAX_TERMS = 10_000


class UnverifiedForm(ValueError):
    """A closed integral, sum or product whose SymPy value no numeric evaluation confirms."""


def _closed(n) -> bool:
    return isinstance(n, _FORMS) and not n.free_symbols


def has_closed_form(e) -> bool:
    return isinstance(e, sp.Basic) and any(_closed(n) for n in sp.preorder_traversal(e))


def _innermost(e) -> list:
    return [n for n in sp.preorder_traversal(e) if _closed(n)
            and not any(isinstance(m, _FORMS) for a in n.args for m in sp.preorder_traversal(a))]


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
        r = sb_run("mathverify.sandbox.ops:numeric_value", n, 40, timeout=timeout)
        tol = 1e-15
    elif isinstance(n, sp.Product):
        if len(n.limits) != 1:
            return None
        k, lo, hi = n.limits[0]
        if not (lo.is_Integer and hi.is_Integer) or hi - lo + 1 > _MAX_TERMS:
            return None
        terms = [n.function.subs(k, i) for i in range(int(lo), int(hi) + 1)]
        r = sb_run("mathverify.sandbox.ops:numeric_value", sp.Mul(*terms, evaluate=False), 40, timeout=timeout)
        tol = 1e-25
    else:
        r = sb_run("mathverify.sandbox.ops:numeric_value", n, 40, timeout=timeout)
        tol = 1e-25
    if not r.ok or not isinstance(r.value, str):
        return None
    try:
        v = sp.Float(r.value, 40)            # the op prints a number; anything else is no value
    except (TypeError, ValueError):
        return None
    return (v, tol) if v.is_finite else None


def checked_forms(e, timeout: float = 8.0):
    """`e` with every closed Integral/Sum/Product replaced by SymPy's value confirmed by numbers
    (see the module docstring). Raises UnverifiedForm when SymPy has no value for one or the numbers
    do not confirm it."""
    from ..sandbox import run as sb_run
    from .numeric import num_equal
    if not has_closed_form(e):
        return e
    for _ in range(8):
        inner = _innermost(e)
        if not inner:
            return e
        reps = {}
        for n in inner:
            r = sb_run("mathverify.sandbox.ops:doit_expr", n, timeout=timeout)
            if not r.ok or not isinstance(r.value, sp.Basic) or r.value.has(*_FORMS) \
                    or r.value.has(sp.nan, sp.zoo) or r.value.free_symbols:
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
            reps[n] = r.value
        e = e.xreplace(reps)
    if has_closed_form(e):
        raise UnverifiedForm(f"too deeply nested: {e}")
    return e
