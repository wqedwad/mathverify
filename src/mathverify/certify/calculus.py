"""Calculus certificates (E3, E8): derivative certificate for antiderivatives, breakpoint-aware
tanh-sinh numeric definite integrals with a precision ladder, derivatives, tangent lines."""
from __future__ import annotations

import re
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import S

from ..equiv import answers_equivalent
from ..equiv.numeric import num_equal
from ..equiv.random_point import random_point_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown
from .domain import definedness_conditions

LAYER = "certify.calculus"


# ---------------------------------------------------------------------------
def find_breakpoints(expr, var, a, b, timeout: float = 8.0) -> list:
    r = sb_run("mathverify.sandbox.ops:breakpoints_of", sp.sympify(expr), var, sp.sympify(a), sp.sympify(b),
               timeout=timeout)
    if not r.ok:
        return []
    return [p for p in r.value if a < p < b]


def definite_integral_numeric(integrand, var, a, b, timeout: float = 12.0) -> tuple[sp.Float | None, dict[str, Any]]:
    """tanh-sinh with breakpoints on a precision ladder (30 -> 50 -> 80 digits).

    Converged when two successive levels agree within 10x the larger error estimate and
    that estimate is below 1e-18 relative. The returned evidence carries `rel_err`, the
    relative tolerance the caller must use when comparing a claim with the value —
    never a fixed 1e-12 (E3). Gauss–Legendre is deliberately NOT used: measured to be
    off by 5e-3 on the endpoint-singular ln x/sqrt x.
    """
    ev: dict[str, Any] = {"integrand": str(integrand), "a": str(a), "b": str(b)}
    a, b = sp.sympify(a), sp.sympify(b)
    pts = find_breakpoints(integrand, var, a, b, timeout)
    ev["breakpoints"] = pts
    ladder: list[tuple[int, str, str]] = []
    ev["ladder"] = []
    prev = None
    converged = False
    for dps in (30, 50, 80):
        r = sb_run("mathverify.sandbox.ops:quad_breakpoints", sp.sympify(integrand), var, a, b, pts, dps,
                   "tanh-sinh", timeout=timeout * (2 if dps == 80 else 1))
        if not r.ok:
            if not ladder:
                ev["error"] = r.error
                ev["flags"] = r.flags
                return None, ev
            ev.setdefault("flags", []).extend(r.flags)
            break
        val_s, err_s = r.value
        ladder.append((dps, val_s, err_s))
        ev["ladder"].append({"dps": dps, "value": val_s, "err": err_s})
        with mp.workdps(dps + 10):
            v = mp.mpf(val_s)
            err = abs(mp.mpf(err_s)) if err_s not in (None, "None") else mp.mpf(1)
            scale = max(abs(v), mp.mpf(1))
            if prev is not None:
                pv, perr = prev
                agree = abs(v - pv) / scale <= 10 * max(err, perr) / scale + mp.mpf(10) ** (-(dps - 5))
                if agree and err / scale < mp.mpf("1e-18"):
                    converged = True
                    prev = (v, err)
                    break
            prev = (v, err)
    v, err = prev
    with mp.workdps(90):
        scale = max(abs(v), mp.mpf(1))
        rel_err = max(10 * err / scale, mp.mpf("1e-25"))
    ev["converged"] = converged
    ev["rel_err"] = mp.nstr(rel_err, 5)
    ev["value"] = mp.nstr(v, 40)
    return sp.Float(mp.nstr(v, 60), 60), ev


def antiderivative_certificate(F, integrand, var, domain=None, timeout: float = 8.0
                               ) -> tuple[bool | None, dict[str, Any]]:
    """d/dx F - integrand == 0 ? Constant shifts are automatically accepted (E8)."""
    ev: dict[str, Any] = {"F": str(F), "integrand": str(integrand)}
    F, integrand = sp.sympify(F), sp.sympify(integrand)
    r = sb_run("mathverify.sandbox.ops:diff_expr", F, var, 1, timeout=timeout)
    if not r.ok:
        ev["error"] = r.error
        return None, ev
    dF = r.value
    ev["dF"] = str(dF)
    rs = sb_run("mathverify.sandbox.ops:simplify_diff", dF, integrand, timeout=timeout)
    if rs.ok:
        res = rs.value
        ev["residual"] = res
        if res == 0:
            ev["method"] = "symbolic"
            return True, ev
        if res.is_number and res.is_zero is False:
            ev["method"] = "nonzero_constant_residual"
            return False, ev
    else:
        ev["residual"] = None
        ev["flags"] = rs.flags
    # domain-aware numeric equality of dF and integrand
    if domain is None:
        dom = S.Reals
        for c in definedness_conditions(integrand, var) + definedness_conditions(F, var):
            rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=timeout)
            if rr.ok and not isinstance(rr.value, sp.ConditionSet):
                dom = sp.Intersection(dom, rr.value)
        domain = dom
    ev["domain"] = str(domain)
    ok, rev = random_point_equal(dF, integrand, var, domain, seed=0, n=40)
    ev["random_point"] = rev
    ev["method"] = "random_point"
    return ok, ev


_TRAILING_C = re.compile(r"\s*\+\s*[Cc]\s*$")


# ---------------------------------------------------------------------------
def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("antiderivative", "definite_integral", "derivative", "tangent_line"):
        return unknown(LAYER, "not_applicable")
    p = ir.task.params
    with Timer() as t:
        var = ctx.sym(p.get("var", "x"))
        ev: dict[str, Any] = {}
        if kind == "antiderivative":
            integrand, err = parse_or_unknown(LAYER, ctx.expr, p["integrand"])
            if err:
                return err
            ns2 = dict(ctx.ns)
            ns2["C"] = sp.Symbol("C")
            from ..normalize.parse import parse_expr_str
            payload = _TRAILING_C.sub("", str(solution.claimed_answer.payload))
            F, err = parse_or_unknown(LAYER, parse_expr_str, payload, ns2)
            if err:
                return err
            F = F.subs(sp.Symbol("C"), 0)
            ok, ev = antiderivative_certificate(F, integrand, var, timeout=ctx.timeout)
            conf = 0.99 if ev.get("method") == "symbolic" else 0.97
        elif kind == "definite_integral":
            integrand, err = parse_or_unknown(LAYER, ctx.expr, p["integrand"])
            if err:
                return err
            a, err = parse_or_unknown(LAYER, ctx.expr, str(p["a"]))
            if err:
                return err
            b, err = parse_or_unknown(LAYER, ctx.expr, str(p["b"]))
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            val, ev = definite_integral_numeric(integrand, var, a, b, timeout=ctx.timeout * 1.5)
            if val is None:
                return unknown(LAYER, "numeric_integration_failed", 0, ev, flags=ev.get("flags", []))
            # symbolic support (timeout-guarded, evidence only)
            rs = sb_run("mathverify.sandbox.ops:integrate_symbolic", integrand, var, a, b, timeout=ctx.timeout)
            if rs.ok and not rs.value.has(sp.Integral) and not rs.value.free_symbols:
                ev["symbolic"] = str(rs.value)
                okS, _ = num_equal(rs.value, val)
                ev["symbolic_agrees_numeric"] = okS
            tol = max(float(p.get("rel_tol") or 0.0), float(ev.get("rel_err", "1e-25")))
            ok, cev = num_equal(claimed, val, rel_tol=tol)
            ev["compare"] = cev
            ev["claimed"] = str(claimed)
            ev["rel_tol_used"] = tol
            if not ev.get("converged", False) and ok is True:
                # accepted only within a loose tolerance: not a certificate
                if tol > 1e-12:
                    return unknown(LAYER, "numeric_not_converged", t.ms, ev, flags=["numeric_not_converged"])
            conf = 0.99 if ev.get("converged") else 0.95
        elif kind == "derivative":
            f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
            if err:
                return err
            order = int(p.get("order", 1))
            r = sb_run("mathverify.sandbox.ops:diff_expr", f, var, order, timeout=ctx.timeout)
            if not r.ok:
                return unknown(LAYER, "diff_failed", 0, flags=r.flags)
            truth = r.value
            ev["derivative"] = str(truth)
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            if "at" in p:
                at, err = parse_or_unknown(LAYER, ctx.expr, str(p["at"]))
                if err:
                    return err
                truth_at = sp.simplify(truth.subs(var, at))
                ev["value_at"] = str(truth_at)
                ok, cev = answers_equivalent(claimed, truth_at, shape="scalar")
            else:
                dom = ctx.domain_for(var)
                for c in definedness_conditions(f, var):
                    rr = sb_run("mathverify.sandbox.ops:solveset_in", c, var, S.Reals, timeout=ctx.timeout)
                    if rr.ok and not isinstance(rr.value, sp.ConditionSet):
                        dom = sp.Intersection(dom, rr.value)
                ok, cev = answers_equivalent(claimed, truth, shape="expression", domain=dom, var=var)
            ev["compare"] = cev
            conf = 0.99 if cev.get("method") in ("symbolic", "numeric") else 0.97
        else:  # tangent_line
            f, err = parse_or_unknown(LAYER, ctx.expr, p["f"])
            if err:
                return err
            at, err = parse_or_unknown(LAYER, ctx.expr, str(p["at"]))
            if err:
                return err
            y = ctx.sym(p.get("dep", "y"))
            r = sb_run("mathverify.sandbox.ops:diff_expr", f, var, 1, timeout=ctx.timeout)
            if not r.ok:
                return unknown(LAYER, "diff_failed", 0, flags=r.flags)
            m = sp.simplify(r.value.subs(var, at))
            y0 = sp.simplify(f.subs(var, at))
            truth = sp.Eq(y, m * (var - at) + y0)
            ev["truth"] = str(truth)
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            if not isinstance(claimed, sp.Equality):
                # allow "m*x + c" expression form meaning y = ...
                claimed = sp.Eq(y, claimed)
            ok, cev = answers_equivalent(claimed, truth, shape="equation", var=var)
            ev["compare"] = cev
            conf = 0.99
    if ok is True:
        return result(LAYER, "pass", conf, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, "undecided", t.ms, ev)
