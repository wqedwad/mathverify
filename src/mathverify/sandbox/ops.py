"""Pure CAS/numeric primitives executed inside the sandbox worker.

Rules: module-level functions only (spawn-safe), picklable inputs/outputs, no global
state, and no decision logic — decisions live in `certify/` and `equiv/`.
"""
from __future__ import annotations


import mpmath as mp
import sympy as sp
from sympy import S, Interval, Poly, oo


# ----------------------------------------------------------------------------
# test helpers (used only by tests/test_sandbox.py)
# ----------------------------------------------------------------------------
def spin(seconds: float):
    """Busy loop; used to prove the hard timeout kills a runaway computation."""
    import time
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        pass
    return "done"


def hog(mb: int):
    """Allocate `mb` megabytes; used to prove the memory cap."""
    buf = bytearray(mb * 1024 * 1024)
    return len(buf)


def echo_seed():
    import random
    return random.random()


# ----------------------------------------------------------------------------
# symbolic equivalence primitives
# ----------------------------------------------------------------------------
def simplify_diff(a, b):
    return sp.simplify(a - b)


def equals(a, b):
    """sympy's structural+numeric `equals`; may return True/False/None."""
    try:
        return a.equals(b)
    except Exception:
        return None


def zero_test_battery(d):
    """Try several cheap canonicalisers on `d`; return True if any proves d == 0.

    Only EXACT rewrites belong here. `nsimplify` used to be one of them, and it is not a
    rewrite but a numerical snap to the nearest "nice" number: it turned −e^(−1000) into 0, so
    `1/(x−1)` and `1/(x−1) + e^(−1000)` were certified equal by the path documented as
    symbolic proof (measured). A difference this battery cannot prove zero goes on to the
    numeric ladder, which is where tolerances belong."""
    for fn in (lambda e: sp.simplify(e), lambda e: sp.cancel(sp.together(e)),
               lambda e: sp.expand(e), lambda e: sp.trigsimp(e), lambda e: sp.radsimp(e),
               lambda e: sp.powsimp(sp.expand_log(e, force=False)),
               lambda e: sp.logcombine(e), lambda e: sp.expand_trig(e)):
        try:
            r = fn(d)
            if r == 0 or (r.is_number and r.is_zero):
                return True
        except Exception:
            continue
    return False


# ----------------------------------------------------------------------------
# solving
# ----------------------------------------------------------------------------
def solve_list(rel, var):
    return list(sp.solve(rel, var))


def solveset_in(rel, var, domain=S.Reals):
    # a closed relation SymPy left standing is undecided, not false: solveset returned EmptySet for
    # it (certify.domain.DEFINEDNESS_UNDECIDED, and cos(acot(2) + acot(1/2)) != 0; 30 Sep 2026)
    if isinstance(rel, sp.core.relational.Relational) and not rel.free_symbols:
        return sp.ConditionSet(var, rel, domain)
    # a relation with a trigonometric function: SymPy's set may be one period only, or lose roots
    # (sandbox.exactsets); the guarded set is rebuilt and checked, or left a ConditionSet
    from .exactsets import exact_solveset
    return exact_solveset(rel, var, domain)


def solve_system(rels, syms, dict_=True):
    return sp.solve(rels, syms, dict=dict_)


def poly_real_roots(expr, var):
    p = Poly(expr, var)
    return list(p.real_roots())


def poly_count_roots(expr, var, lo=-oo, hi=oo):
    p = Poly(expr, var)
    return int(p.count_roots(lo, hi))


# ----------------------------------------------------------------------------
# calculus
# ----------------------------------------------------------------------------
def doit_expr(expr):
    return expr.doit()


def diff_expr(expr, var, n=1):
    return sp.diff(expr, var, n)


def integrate_symbolic(expr, var, a=None, b=None):
    if a is None:
        return sp.integrate(expr, var)
    return sp.integrate(expr, (var, a, b))


def limit_two_sided(expr, var, point):
    plus = sp.limit(expr, var, point, "+")
    minus = sp.limit(expr, var, point, "-")
    return plus, minus


def limit_default(expr, var, point):
    return sp.limit(expr, var, point)


def quad_breakpoints(expr, var, a, b, points, dps=30, method="tanh-sinh"):
    """mpmath quad with explicit interior breakpoints; returns (value_str, error_str)."""
    mp.mp.dps = dps
    f = sp.lambdify(var, expr, "mpmath")
    pts = [mp.mpf(str(sp.N(a, dps + 5)))] + [mp.mpf(str(sp.N(p, dps + 5))) for p in points] \
        + [mp.mpf(str(sp.N(b, dps + 5)))]
    # sort/dedupe within (a,b)
    lo, hi = pts[0], pts[-1]
    inner = sorted({p for p in pts[1:-1] if lo < p < hi})
    pts = [lo] + inner + [hi]
    val, err = mp.quad(f, pts, method=method, error=True)
    return mp.nstr(val, dps), mp.nstr(err, 5)


def breakpoints_of(expr, var, a, b):
    """Zeros of Abs/sign/floor/ceiling/Piecewise arguments and singularities in (a,b)."""
    pts = set()
    dom = Interval(a, b)
    for node in sp.preorder_traversal(expr):
        if isinstance(node, (sp.Abs, sp.sign)):
            arg = node.args[0]
            try:
                for r in sp.solveset(arg, var, dom):
                    if r.is_number:
                        pts.add(r)
            except Exception:
                pass
        elif isinstance(node, (sp.floor, sp.ceiling)):
            arg = node.args[0]
            try:
                lo, hi = sp.floor(arg.subs(var, a)), sp.ceiling(arg.subs(var, b))
                for k in range(int(lo), int(hi) + 1):
                    for r in sp.solveset(sp.Eq(arg, k), var, dom):
                        if r.is_number:
                            pts.add(r)
            except Exception:
                pass
        elif isinstance(node, sp.Piecewise):
            for _, cond in node.args:
                for atom in sp.preorder_traversal(cond):
                    if isinstance(atom, sp.core.relational.Relational):
                        try:
                            for r in sp.solveset(sp.Eq(atom.lhs, atom.rhs), var, dom):
                                if r.is_number:
                                    pts.add(r)
                        except Exception:
                            pass
    try:
        from sympy.calculus.singularities import singularities
        for s_ in singularities(expr, var, dom):
            if s_.is_number:
                pts.add(s_)
    except Exception:
        pass
    return sorted(pts, key=lambda p: float(p))


def continuous_domain(expr, var, domain=S.Reals):
    from sympy.calculus.util import continuous_domain as cd
    from .exactsets import continuity_set, oscillates
    if oscillates(expr, var):
        # SymPy solves the conditions of a trigonometric expression on one period, both ways wrong
        # (sandbox.exactsets.continuity_set): rebuilt and checked, or refused
        out = continuity_set(expr, var, domain)
        if out is None:
            raise ValueError("continuous domain of a trigonometric expression not trusted")
        return out
    return cd(expr, var, domain)


def critical_points(expr, var, interval):
    d = sp.diff(expr, var)
    cps = []
    try:
        for c in sp.solveset(d, var, interval):
            if c.is_number:
                cps.append(c)
    except Exception:
        pass
    # points where derivative is undefined (e.g. |x|, cbrt)
    try:
        from sympy.calculus.singularities import singularities
        for s_ in singularities(d, var, interval):
            if s_.is_number:
                cps.append(s_)
    except Exception:
        pass
    return cps


def emptiness_of_superlevel(expr, var, interval, bound, strict=True):
    rel = expr > bound if strict else expr >= bound
    return sp.solveset(rel, var, interval)


# ----------------------------------------------------------------------------
# numeric evaluation
# ----------------------------------------------------------------------------
def eval_points(expr, syms, points, dps=30):
    """Evaluate expr at each point (tuple aligned with syms). Returns list of mpc/mpf strings."""
    mp.mp.dps = dps
    f = sp.lambdify(syms, expr, "mpmath")
    out = []
    for pt in points:
        try:
            v = f(*[mp.mpf(str(c)) if not isinstance(c, complex) else mp.mpc(c) for c in pt])
            out.append(mp.nstr(v, dps))
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            out.append(None)
        except Exception:
            out.append(None)
    return out


def numeric_value(expr, dps=30):
    mp.mp.dps = dps
    v = sp.N(expr, dps)
    return str(v)


# ----------------------------------------------------------------------------
# z3
# ----------------------------------------------------------------------------
def z3_check(constraints, syms_info, extra=None, timeout_ms=4000):
    """Check satisfiability of sympy relations translated to z3.

    syms_info: {name: "int"|"real"}. Returns ("sat"|"unsat"|"unknown", model_dict|None).
    """
    from ..certify._z3bridge import check_sat
    return check_sat(constraints, syms_info, extra or [], timeout_ms)


def z3_enumerate(constraints, syms_info, target, timeout_ms=4000, max_models=50):
    from ..certify._z3bridge import enumerate_target
    return enumerate_target(constraints, syms_info, target, timeout_ms, max_models)
