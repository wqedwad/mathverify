"""Analytic geometry certificates (AYT): equations of lines/circles derived from stated
conditions and compared with the claimed equation AS POINT SETS OF THE PLANE.

Numeric analytic-geometry quantities (distance, slope, area) are `evaluate` tasks using the
dist/slope/tri_area helpers in the parse namespace.

Decision rules (audit of 25 Sep 2026; before it, the claim was compared by `solveset(.., x)` with
y as a parameter, and a circle by five coefficients only):
  * CORRECT only with a proof that both zero sets are equal: the claimed polynomial is a nonzero
    constant multiple of the true one, or a constant times a power of it. A claim whose written
    form has a definedness condition (a denominator, a root, a logarithm) is never CORRECT here:
    its solution set is the curve minus the points where it is undefined.
  * INCORRECT only with a witness point: a point of the true curve that is not on the claimed
    one (exact evaluation, or undefined there as written), or a real point of the claimed
    polynomial curve that is not on the true one.
  * Anything else is UNKNOWN. Measured before the change: `y**3 = 27` for the line y = 2,
    `y*(2*x - y + 1) = 0` for y = 2x + 1 and `x**2 + y**2 - 2*x - 4*y - 4 + x**3 = 0` for a circle
    were all certified CORRECT.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Eq, Rational

from ..equiv.numeric import num_equal
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.geometry"

# parameters of the sample points (exact rationals; the circle uses the rational parametrisation)
_T_SAMPLES = (Rational(-3), Rational(-1), Rational(0), Rational(1, 2), Rational(1), Rational(2),
              Rational(5), Rational(-7, 3), Rational(13, 5))
_X0_SAMPLES = (Rational(-7, 3), Rational(-1), Rational(0), Rational(1, 2), Rational(2),
               Rational(13, 5), Rational(5), Rational(11))


def _pt(ctx: Ctx, p):
    return sp.Matrix([ctx.expr(str(p[0])), ctx.expr(str(p[1]))])


def _linear_coeffs(ctx: Ctx, line: str, x, y):
    L = ctx.rel(line)
    if not isinstance(L, sp.Equality):
        raise ValueError(f"line {line!r} is not an equation")
    d = sp.expand(L.lhs - L.rhs)
    poly = sp.Poly(d, x, y)
    if poly.total_degree() != 1:
        raise ValueError(f"line {line!r} is not of degree 1 in {x}, {y}")
    return d.coeff(x, 1), d.coeff(y, 1)


def truth_equation(ctx: Ctx, params: dict[str, Any], x, y):
    obj = params["object"]
    if obj == "line_points":
        A, B = _pt(ctx, params["p1"]), _pt(ctx, params["p2"])
        return Eq((y - A[1]) * (B[0] - A[0]), (B[1] - A[1]) * (x - A[0]))
    if obj == "line_point_slope":
        A = _pt(ctx, params["p"])
        m = ctx.expr(str(params["slope"]))
        if m in (sp.oo, -sp.oo, sp.zoo):
            # an infinite / undefined slope is the vertical line through the point; before the
            # audit Eq(y - 4, oo*(x - 3)) was built and the right answer `x = 3` was refuted
            return Eq(x, A[0])
        if m.has(sp.oo, -sp.oo, sp.zoo, sp.nan) or m.is_real is False:
            raise ValueError(f"slope {params['slope']!r} is not a real number")
        return Eq(y - A[1], m * (x - A[0]))
    if obj in ("line_point_parallel", "line_point_perpendicular"):
        A = _pt(ctx, params["p"])
        a_, b_ = _linear_coeffs(ctx, params["line"], x, y)
        if obj == "line_point_parallel":
            return Eq(a_ * (x - A[0]) + b_ * (y - A[1]), 0)
        return Eq(b_ * (x - A[0]) - a_ * (y - A[1]), 0)
    if obj == "circle_center_radius":
        C = _pt(ctx, params["center"])
        r = ctx.expr(str(params["radius"]))
        if r.is_real is False or r.is_negative:
            # a radius is a nonnegative real; `radius: -2` used to be read as radius 2
            raise ValueError(f"radius {params['radius']!r} is not a nonnegative real number")
        return Eq((x - C[0]) ** 2 + (y - C[1]) ** 2, r ** 2)
    if obj == "circle_center_point":
        C, P = _pt(ctx, params["center"]), _pt(ctx, params["point"])
        r2 = (P[0] - C[0]) ** 2 + (P[1] - C[1]) ** 2
        return Eq((x - C[0]) ** 2 + (y - C[1]) ** 2, r2)
    if obj == "circle_diameter":
        A, B = _pt(ctx, params["p1"]), _pt(ctx, params["p2"])
        C = (A + B) / 2
        r2 = ((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2) / 4
        return Eq((x - C[0]) ** 2 + (y - C[1]) ** 2, r2)
    if obj == "perpendicular_bisector":
        A, B = _pt(ctx, params["p1"]), _pt(ctx, params["p2"])
        M = (A + B) / 2
        return Eq((B[0] - A[0]) * (x - M[0]) + (B[1] - A[1]) * (y - M[1]), 0)
    if obj == "tangent_to_circle_at_point":
        C, P = _pt(ctx, params["center"]), _pt(ctx, params["point"])
        return Eq((P[0] - C[0]) * (x - P[0]) + (P[1] - C[1]) * (y - P[1]), 0)
    raise ValueError(f"unknown geometric object {obj!r}")


# ---------------------------------------------------------------------------------------------
# point-set comparison
# ---------------------------------------------------------------------------------------------
def _poly_xy(d, x, y):
    """sp.Poly of `d` in x, y with NUMBER coefficients, else None."""
    if d.has(sp.oo, -sp.oo, sp.zoo, sp.nan):
        return None
    try:
        P = sp.Poly(d, x, y)
    except sp.PolynomialError:
        return None
    if not all(c.is_number for c in P.coeffs()):
        return None
    return P


def _definitely_nonzero(v) -> bool:
    """True only when the exact number `v` is provably nonzero (or not a real number at all)."""
    if v.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        return True                                 # undefined there: not a solution
    v = sp.expand(v)
    if v == 0:
        return False
    if v.is_number and v.is_zero is False:
        return True
    ok, _ = num_equal(v, 0)
    return ok is False


def _truth_points(T, x, y) -> list[tuple[Any, Any]]:
    """Exact points of the true curve T(x, y) = 0 (a line or a circle)."""
    P = sp.Poly(T, x, y)
    deg = P.total_degree()
    pts: list[tuple[Any, Any]] = []
    if deg == 1:
        a, b, c = T.coeff(x, 1), T.coeff(y, 1), T.subs({x: 0, y: 0})
        for t in _T_SAMPLES:
            pts.append((t, sp.simplify(-(a * t + c) / b)) if b != 0 else (sp.simplify(-c / a), t))
    elif deg == 2:
        a2 = T.coeff(x, 2)
        Tn = sp.expand(T / a2)
        cx, cy = -Tn.coeff(x, 1) / 2, -Tn.coeff(y, 1) / 2
        R = sp.simplify(cx ** 2 + cy ** 2 - Tn.subs({x: 0, y: 0}))
        if R.is_negative:
            return []
        r = sp.sqrt(R)
        for t in _T_SAMPLES:
            den = 1 + t ** 2
            pts.append((cx + r * (1 - t ** 2) / den, cy + r * 2 * t / den))
        pts.append((cx - r, cy))                      # the point t -> infinity
    return pts


def _claim_holds_at(claim_d, conds, pt, x, y) -> bool | None:
    """Tri-state: is `pt` a solution of the claim AS WRITTEN? False = certainly not."""
    sub = {x: pt[0], y: pt[1]}
    for c in conds:
        try:
            cv = c.subs(sub)
        except Exception:  # noqa: BLE001
            return None
        if cv is sp.false:
            return False                             # undefined there as written
        if cv is not sp.true:
            return None
    try:
        v = claim_d.subs(sub)
    except Exception:  # noqa: BLE001
        return None
    if _definitely_nonzero(v):
        return False
    return True if sp.expand(v) == 0 else None


def _is_power_of(Pd, PT, x, y) -> bool:
    """Is the claimed polynomial c * T**k (k >= 1, c a nonzero number)? Same zero set then."""
    try:
        _, fs_d = sp.factor_list(Pd.as_expr(), x, y)
        _, fs_t = sp.factor_list(PT.as_expr(), x, y)
    except Exception:  # noqa: BLE001
        return False
    if len(fs_t) != 1 or fs_t[0][1] != 1 or not fs_d:
        return False
    g = fs_t[0][0]
    for f, _m in fs_d:
        q = sp.cancel(f / g)
        if not (q.is_number and q != 0):
            return False
    return True


def _claim_point_off_truth(Pd, T, x, y):
    """A real point of the claimed polynomial curve that is not on T = 0, or None."""
    for (u, v) in ((x, y), (y, x)):
        for u0 in _X0_SAMPLES:
            q = sp.expand(Pd.as_expr().subs(u, u0))
            if q == 0:
                # the whole line u = u0 lies on the claimed curve
                for v0 in _X0_SAMPLES:
                    pt = {u: u0, v: v0}
                    if _definitely_nonzero(T.subs(pt)):
                        return (pt[x], pt[y])
                continue
            try:
                roots = sp.Poly(q, v).real_roots()
            except Exception:  # noqa: BLE001
                continue
            for r0 in roots:
                pt = {u: u0, v: r0}
                if _definitely_nonzero(T.subs(pt)):
                    return (pt[x], pt[y])
    return None


def _undefined_points_on_line(T, conds, x, y) -> list[tuple[Any, Any]]:
    """Points of the true LINE where a written condition of the claim fails (a denominator of
    the claim vanishes there, a root's radicand is negative...). Candidates only: the caller
    re-checks each one exactly."""
    P = sp.Poly(T, x, y)
    if P.total_degree() != 1:
        return []
    a, b, c = T.coeff(x, 1), T.coeff(y, 1), T.subs({x: 0, y: 0})
    t = sp.Symbol("_t", real=True)
    X, Y = (t, -(a * t + c) / b) if b != 0 else (-c / a, t)
    out: list[tuple[Any, Any]] = []
    for cond in conds:
        try:
            ct = cond.subs({x: X, y: Y})
            bad = sp.Eq(ct.lhs, ct.rhs) if isinstance(ct, sp.Ne) else sp.Not(ct)
            s = sp.solveset(bad, t, sp.S.Reals)
        except Exception:  # noqa: BLE001
            continue
        cand = []
        if isinstance(s, sp.FiniteSet):
            cand = [v for v in s.args if v.is_real]
        elif isinstance(s, sp.Interval):
            lo, hi = s.inf, s.sup
            if lo.is_finite and hi.is_finite:
                cand = [(lo + hi) / 2]
            elif lo.is_finite:
                cand = [lo + 1]
            elif hi.is_finite:
                cand = [hi - 1]
            else:
                cand = [sp.Integer(0)]
        for v in cand[:3]:
            out.append((sp.simplify(X.subs(t, v)), sp.simplify(Y.subs(t, v))))
    return out


def compare_curves(claimed, truth, x, y, conds, nowhere) -> tuple[bool | None, dict[str, Any]]:
    """Is {claimed} == {truth} as subsets of R^2? Proof or witness only; otherwise None."""
    ev: dict[str, Any] = {}
    T = sp.expand(truth.lhs - truth.rhs)
    PT = _poly_xy(T, x, y)
    if PT is None or T == 0 or PT.total_degree() not in (1, 2) or T.free_symbols - {x, y}:
        ev["reason"] = "true_object_not_a_line_or_circle"
        return None, ev
    D = claimed.lhs - claimed.rhs
    if D.free_symbols - {x, y}:
        ev["reason"] = "claim_has_other_symbols"
        return None, ev
    if nowhere & {x, y}:
        ev["reason"] = "claim_defined_nowhere_as_written"
        return False, ev
    Dx = sp.expand(D)
    Pd = _poly_xy(Dx, x, y) if not conds else None
    if Pd is not None and not Pd.is_zero:
        # proof: proportional polynomials, or a constant times a power of the true polynomial
        k0 = next(iter(PT.monoms()))
        q = sp.simplify(Pd.coeff_monomial(k0) / PT.coeff_monomial(k0))
        if q != 0 and sp.expand(Dx - q * T) == 0:
            ev["method"] = "proportional_polynomials"
            ev["ratio"] = str(q)
            return True, ev
        if _is_power_of(Pd, PT, x, y):
            ev["method"] = "constant_times_power_of_true_polynomial"
            return True, ev
    elif Pd is not None and Pd.is_zero:
        ev["reason"] = "claim_is_an_identity (the whole plane)"
        return False, ev
    # witness 1: a point of the true curve that is not a solution of the claim
    for pt in _truth_points(T, x, y) + (_undefined_points_on_line(T, conds, x, y) if conds else []):
        h = _claim_holds_at(D, conds, pt, x, y)
        if h is False:
            ev["method"] = "witness_on_true_curve"
            ev["witness"] = [str(pt[0]), str(pt[1])]
            return False, ev
    # witness 2: a real point of the claimed (polynomial) curve that is not on the true one
    if Pd is not None:
        w = _claim_point_off_truth(Pd, T, x, y)
        if w is not None:
            ev["method"] = "witness_on_claimed_curve"
            ev["witness"] = [str(w[0]), str(w[1])]
            return False, ev
    ev["reason"] = "no_proof_and_no_witness"
    return None, ev


def verify(ir, solution, ctx: Ctx):
    if ir.task.kind != "equation_of":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        x, y = ctx.sym(p.get("x", "x")), ctx.sym(p.get("y", "y"))
        try:
            truth = truth_equation(ctx, p, x, y)
        except Exception as e:  # noqa: BLE001
            return unknown(LAYER, f"truth_construction_failed: {e}", flags=["parse_error"])
        if not isinstance(truth, sp.Equality):
            return unknown(LAYER, "truth_is_not_an_equation (degenerate object)")
        claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
        if err:
            return err
        if isinstance(claimed, sp.Expr) and not isinstance(claimed, sp.Equality):
            claimed = Eq(claimed, 0, evaluate=False) if claimed.free_symbols & {x, y} else None
        if not isinstance(claimed, sp.Equality):
            return unknown(LAYER, "claimed_not_equation")
        # definedness of the claim as written (principle 12): `(y - 1)/x = 2` is not the line
        conds, nowhere = [], set()
        payload = solution.claimed_answer.payload
        if isinstance(payload, str):
            from .domain import written_definedness
            try:
                conds, nowhere = written_definedness(payload, ctx.claim_ns(solution))
            except Exception:  # noqa: BLE001
                conds, nowhere = [], set()
        ev: dict[str, Any] = {"truth": str(truth), "claimed": str(claimed),
                              "claim_conditions": [str(c) for c in conds]}
        try:
            ok, cev = compare_curves(claimed, truth, x, y, conds, nowhere)
        except Exception as e:  # noqa: BLE001
            ok, cev = None, {"reason": f"compare_failed: {type(e).__name__}: {e}"}
        ev.update(cev)
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", "undecided"), t.ms, ev)
