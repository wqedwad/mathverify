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
SymPy's exact 0 for such an integral is taken when the quadrature's residue stays below the
integrand's scale ∫|f| at every precision (`certify.calculus.definite_integral_is_zero`).
Otherwise `UnverifiedForm` is raised and the caller abstains. Forms with a free symbol are left as
they are: no number can check them here.
"""
from __future__ import annotations

from typing import Any

import sympy as sp

__all__ = ["UnverifiedForm", "has_closed_form", "checked_forms"]

_FORMS = (sp.Integral, sp.Sum, sp.Product, sp.Limit)
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
            if has_closed_form(e):
                # a closed form whose inner forms are open (their variable is the outer one's):
                # nothing checks it, and SymPy's doit of it was certified (third audit, 30 Sep 2026)
                raise UnverifiedForm(f"a closed form over open inner forms: {e}")
            return e
        reps = {}
        for n in inner:
            if isinstance(n, sp.Limit):
                # SymPy's limit, corroborated numerically near the point and two-sided unless a side
                # is written (certify.limits): with n an integer SymPy says lim n·sin(π/n) = 0 (π)
                from ..certify.limits import classify_limit
                e_, v_, p_, d_ = n.args
                cls = classify_limit(e_, v_, p_, None if str(d_) in ("+-", "real") else str(d_), timeout=timeout)
                if cls.get("kind") not in ("VAR", "INF") or cls.get("value") is None:
                    raise UnverifiedForm(f"{n}: {cls.get('kind')}")
                reps[n] = cls["value"]
                continue
            r = sb_run("mathverify.sandbox.ops:doit_expr", n, timeout=timeout)
            if not r.ok or not isinstance(r.value, sp.Basic) or r.value.has(*_FORMS) \
                    or r.value.has(sp.nan, sp.zoo) or r.value.free_symbols:
                raise UnverifiedForm(f"SymPy has no closed value for {n}")
            if r.value == 0 and _finite_integral(n):
                # a relative tolerance never confirms an exact 0 against a quadrature residue of
                # 1e-51...1e-59: SymPy's right 0 for ∫_0^3 (x² - 2x) dx was never taken (third audit of
                # 30 Sep 2026, N2); the residue is measured against the integrand's scale instead
                from ..certify.calculus import definite_integral_is_zero
                var, a, b = n.limits[0]
                zero, zev = definite_integral_is_zero(n.function, var, a, b, timeout=timeout)
                if zero is not True:
                    raise UnverifiedForm(f"{n}: SymPy 0, numbers {zev.get('decided_by') or zev.get('error')}")
                reps[n] = r.value
                continue
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
