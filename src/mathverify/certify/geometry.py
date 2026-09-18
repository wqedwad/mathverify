"""Analytic geometry certificates (AYT): equations of lines/circles derived from stated
conditions and compared as equations (proportional polynomials / same solution set).
Numeric analytic-geometry quantities (distance, slope, area) are `evaluate` tasks
using the dist/slope/tri_area helpers in the parse namespace.
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Eq, sqrt

from ..equiv import answers_equivalent
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.geometry"


def _pt(ctx: Ctx, p):
    return sp.Matrix([ctx.expr(str(p[0])), ctx.expr(str(p[1]))])


def truth_equation(ctx: Ctx, params: dict[str, Any], x, y):
    obj = params["object"]
    if obj == "line_points":
        A, B = _pt(ctx, params["p1"]), _pt(ctx, params["p2"])
        return Eq((y - A[1]) * (B[0] - A[0]), (B[1] - A[1]) * (x - A[0]))
    if obj == "line_point_slope":
        A = _pt(ctx, params["p"])
        m = ctx.expr(str(params["slope"]))
        return Eq(y - A[1], m * (x - A[0]))
    if obj in ("line_point_parallel", "line_point_perpendicular"):
        A = _pt(ctx, params["p"])
        L = ctx.rel(params["line"])
        d = sp.expand(L.lhs - L.rhs)
        a_, b_ = d.coeff(x, 1), d.coeff(y, 1)
        if obj == "line_point_parallel":
            return Eq(a_ * (x - A[0]) + b_ * (y - A[1]), 0)
        return Eq(b_ * (x - A[0]) - a_ * (y - A[1]), 0)
    if obj == "circle_center_radius":
        C = _pt(ctx, params["center"])
        r = ctx.expr(str(params["radius"]))
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
        claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
        if err:
            return err
        if not isinstance(claimed, Eq):
            claimed = Eq(claimed, 0) if not isinstance(claimed, sp.Set) else None
        if claimed is None:
            return unknown(LAYER, "claimed_not_equation")
        ev: dict[str, Any] = {"truth": str(truth), "claimed": str(claimed)}
        if p["object"].startswith("circle"):
            # circle equations: compare centre & radius^2 after completing the square
            def cr(eq):
                d = sp.expand(eq.lhs - eq.rhs)
                a = d.coeff(x, 2)
                if a == 0 or d.coeff(y, 2) != a or d.coeff(x * y) != 0:
                    return None
                d = sp.expand(d / a)
                cx, cy = -d.coeff(x, 1) / 2, -d.coeff(y, 1) / 2
                k = d.subs({x: 0, y: 0})
                return cx, cy, sp.simplify(cx ** 2 + cy ** 2 - k)
            ct, cc = cr(truth), cr(claimed)
            if cc is None:
                ev["reason"] = "claimed_is_not_a_circle"
                return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
            oks = [answers_equivalent(a_, b_, shape="scalar")[0] for a_, b_ in zip(cc, ct)]
            ev["centre_radius2_truth"] = [str(v) for v in ct]
            ev["centre_radius2_claimed"] = [str(v) for v in cc]
            ok = True if all(o is True for o in oks) else (False if any(o is False for o in oks) else None)
        else:
            ok, cev = answers_equivalent(claimed, truth, shape="equation", var=x)
            ev["compare"] = cev
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "undecided", t.ms, ev)
