"""equiv/ — the shared comparison engine.

Under D2 the verifier never sees an answer key, so `equiv` is not a "compare with
gold" layer; it is the primitive every certificate uses to compare a *claimed*
object with a *derived* object (an option value, a computed maximum, an interval).

Order of evidence (handoff §3 rule 2): symbolic proof -> numeric -> domain-aware
random points; Math-Verify is consulted as an independent second opinion for
scalars and recorded in the evidence.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import S

from .numeric import num_equal, to_mp
from .symbolic import sym_equal
from .random_point import random_point_equal, sample_points
from .sets import set_equal, normalize_set, scalar_equal

__all__ = ["answers_equivalent", "num_equal", "sym_equal", "random_point_equal", "set_equal",
           "normalize_set", "scalar_equal", "sample_points", "to_mp", "math_verify_opinion"]


def _mv_verify(a, b) -> bool:
    """Worker-side Math-Verify call. Its own timeout is disabled: on Windows it would
    spawn a fresh process per call (measured: orphaned-bootstrap noise + big latency);
    our sandbox already enforces the hard timeout."""
    from math_verify import verify as mv_verify
    return bool(mv_verify(a, b, timeout_seconds=None))


def math_verify_opinion(a, b, timeout: float = 5.0) -> bool | None:
    """Independent oracle (Math-Verify 0.9) run inside the sandbox. None = undecided/failed."""
    from ..sandbox import run as sb_run
    try:
        r = sb_run("mathverify.equiv:_mv_verify", sp.sympify(a), sp.sympify(b), timeout=timeout)
    except Exception:
        return None
    return bool(r.value) if r.ok else None


def answers_equivalent(claimed, truth, shape: str = "scalar", domain=None, var=None,
                       rel_tol: float | None = None, abs_tol: float | None = None,
                       seed: int = 0) -> tuple[bool | None, dict[str, Any]]:
    """Compare a claimed answer with a derived one. Returns (True|False|None, evidence).

    shape: scalar | expression | set | interval | count | dne | equation
    domain: sympy Set (or dict) for expression-shaped answers — from the IR (E4).
    """
    ev: dict[str, Any] = {"shape": shape, "claimed": str(claimed), "truth": str(truth)}
    if claimed is None or truth is None:
        ev["method"] = "missing"
        return None, ev
    if shape == "dne":
        r = (str(claimed) == "DNE") == (str(truth) == "DNE")
        ev["method"] = "dne_flag"
        return bool(r), ev
    if shape == "count":
        try:
            r = int(claimed) == int(truth)
        except Exception:
            return None, ev
        ev["method"] = "int_compare"
        return r, ev
    if shape in ("set", "interval"):
        if not isinstance(claimed, sp.Set) or not isinstance(truth, sp.Set):
            ev["method"] = "not_a_set"
            return None, ev
        ok, sev = set_equal(claimed, truth)
        ev.update(sev)
        return ok, ev
    if shape == "equation":
        return _equation_equivalent(claimed, truth, domain, var, seed, ev)

    claimed, truth = sp.sympify(claimed), sp.sympify(truth)
    free = claimed.free_symbols | truth.free_symbols
    if not free:
        okS, sev = sym_equal(claimed, truth)
        ev["symbolic"] = sev
        if okS is True:
            ev["method"] = "symbolic"
            ev["math_verify"] = math_verify_opinion(claimed, truth)
            return True, ev
        okN, nev = num_equal(claimed, truth, rel_tol=rel_tol, abs_tol=abs_tol)
        ev["numeric"] = nev
        ev["math_verify"] = math_verify_opinion(claimed, truth)
        if okN is not None:
            ev["method"] = "numeric"
            return okN, ev
        if ev["math_verify"] is True:
            ev["method"] = "math_verify_only"
            return True, ev
        ev["method"] = "undecided"
        return None, ev

    # expression-shaped: symbolic proof, else domain-aware random points
    okS, sev = sym_equal(claimed, truth)
    ev["symbolic"] = sev
    if okS is True:
        ev["method"] = "symbolic"
        return True, ev
    syms = sorted(free, key=lambda s_: s_.name)
    if domain is None:
        domain = {s_: (S.Integers if s_.is_integer else S.Reals) for s_ in syms}
        ev["domain_defaulted_from_assumptions"] = True
    elif not isinstance(domain, dict):
        domain = {s_: domain for s_ in syms}
    else:
        domain = {s_: domain.get(s_, S.Reals) for s_ in syms}
    okR, rev = random_point_equal(claimed, truth, syms, domain, seed=seed)
    ev["random_point"] = rev
    ev["method"] = "random_point" if okR is not None else "undecided"
    return okR, ev


def _equation_equivalent(claimed, truth, domain, var, seed, ev):
    """Two equations are equivalent when they have the same solution set in `var`.

    For linear/polynomial equations we compare (lhs-rhs) up to a nonzero constant
    factor; otherwise we compare solution sets over the domain."""
    from ..sandbox import run as sb_run
    if not (isinstance(claimed, sp.Equality) and isinstance(truth, sp.Equality)):
        ev["method"] = "not_equations"
        return None, ev
    d1 = sp.expand(claimed.lhs - claimed.rhs)
    d2 = sp.expand(truth.lhs - truth.rhs)
    if d1 == 0 or d2 == 0:
        ev["method"] = "trivial_equation"
        return (d1 == 0 and d2 == 0), ev
    syms = sorted(d1.free_symbols | d2.free_symbols, key=lambda s_: s_.name)
    try:
        p1, p2 = sp.Poly(d1, *syms), sp.Poly(d2, *syms)
        # proportional polynomials <=> same zero set (over reals, for nonzero constant ratio)
        q = sp.cancel(sp.together(d1 / d2))
        if q.is_number and q != 0:
            ev["method"] = "proportional_polynomials"
            ev["ratio"] = str(q)
            return True, ev
        if p1.total_degree() <= 1 and p2.total_degree() <= 1:
            ev["method"] = "linear_not_proportional"
            return False, ev
    except sp.PolynomialError:
        pass
    if var is None:
        ev["method"] = "no_variable_for_solution_sets"
        return None, ev
    dom = domain if isinstance(domain, sp.Set) else S.Reals
    r1 = sb_run("mathverify.sandbox.ops:solveset_in", claimed, var, dom, timeout=5)
    r2 = sb_run("mathverify.sandbox.ops:solveset_in", truth, var, dom, timeout=5)
    if not (r1.ok and r2.ok):
        ev["method"] = "solveset_failed"
        return None, ev
    ok, sev = set_equal(r1.value, r2.value)
    ev["method"] = "solution_sets"
    ev["sets"] = sev
    return ok, ev
