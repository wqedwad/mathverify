"""Synthetic (Euclidean) geometry by numeric realisation (handoff §7 `geometry_numeric`, F2).

Idea: the problem is a set of constraints on 2-D points (lengths, angles, parallel /
perpendicular / collinear / on-circle / midpoint …) and a target quantity (length, angle,
area, ratio). We do NOT reason synthetically. We build many random configurations that
satisfy the constraints exactly (to 25+ digits), measure the target in each, and accept the
claim only when

  * no two points of a realisation coincide,
  * the target agrees across ALL realisations (otherwise the constraints do not determine
    it -> IR incomplete / ill-posed -> UNKNOWN, never a guess), and
  * the common value equals the claim at 80 digits: two realisations are polished by Newton's
    method at 80 digits and the claim must agree to 1e-60 (relative); a difference above 1e-40
    refutes, anything between abstains.

Gauge: point 1 at the origin, point 2 on the x-axis (rotation and translation only — every
constraint helper is invariant under them). The SCALE is never fixed by the gauge: before the
audit of 25 Sep 2026 a heuristic decided whether a length constraint fixed it and otherwise set
dist(P1, P2) = 1, and it missed constants 1, 2, 1/2, sqrt(2) and area constraints — the added
constraint made undetermined targets look determined ("CA = CB = 1, angle C = 60" was certified).
With the scale left free, a scale-dependent target simply varies across realisations. When a
constraint or the target uses absolute coordinates (px, py) no gauge is applied at all.

Angles are in degrees (angle() returns degrees). A degree mark written in a constraint, the
target or the claim (`40°`, `40 derece`) therefore means the plain number: the parser's generic
rule would turn it into radians (40*pi/180) and build a different figure (measured: tyt-geo-002
written as `angle(B,A,C) = 40°` certified 90 - pi/9 and refuted 70).

Every realisation is found with a damped Gauss–Newton / Levenberg–Marquardt solve on the
residuals (symbolic Jacobian from SymPy, mpmath arithmetic). Free parameters (unknowns not
pinned by the constraints) are sampled as exact rationals per realisation with a fixed seed.
"""
from __future__ import annotations

import random
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import Matrix, sqrt, pi, acos, Abs

from ..equiv.numeric import to_mp
from ..normalize.parse import (parse_relation, ParseError, _SAFE_NAMES, preclean, _DEG_NUM_RE,
                               _DEG_PAREN_RE)
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown

LAYER = "certify.geometry_numeric"

_DPS = 30
_RES_TOL = "1e-22"
_N_REAL = 8


# ---------------------------------------------------------------------------
# geometric primitives on 2-vectors (sympy Matrix)
# ---------------------------------------------------------------------------
def _v(p):
    return p if isinstance(p, Matrix) else Matrix(p)


def g_dist(A, B):
    d = _v(A) - _v(B)
    return sqrt(d[0] ** 2 + d[1] ** 2)


def g_angle(A, B, C):
    """angle ABC (at B) in degrees"""
    u, w = _v(A) - _v(B), _v(C) - _v(B)
    return acos((u[0] * w[0] + u[1] * w[1]) / (sqrt(u[0] ** 2 + u[1] ** 2) * sqrt(w[0] ** 2 + w[1] ** 2))) * 180 / pi


def g_area(*pts):
    P = [_v(p) for p in pts]
    s = 0
    for i in range(len(P)):
        j = (i + 1) % len(P)
        s += P[i][0] * P[j][1] - P[j][0] * P[i][1]
    return Abs(s) / 2


def g_signed_area(A, B, C):
    A, B, C = _v(A), _v(B), _v(C)
    return ((B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])) / 2


def g_cross(A, B, C, D):
    """cross product of AB and CD (0 <=> parallel)"""
    u, w = _v(B) - _v(A), _v(D) - _v(C)
    return u[0] * w[1] - u[1] * w[0]


def g_dot(A, B, C, D):
    """dot product of AB and CD (0 <=> perpendicular)"""
    u, w = _v(B) - _v(A), _v(D) - _v(C)
    return u[0] * w[0] + u[1] * w[1]


def g_mid(A, B):
    return (_v(A) + _v(B)) / 2


def g_perimeter(*pts):
    P = [_v(p) for p in pts]
    return sum(g_dist(P[i], P[(i + 1) % len(P)]) for i in range(len(P)))


def g_x(A):
    return _v(A)[0]


def g_y(A):
    return _v(A)[1]


# relation-producing helpers (used in constraints)
def c_collinear(A, B, C):
    return sp.Eq(g_signed_area(A, B, C), 0, evaluate=False)


def c_parallel(A, B, C, D):
    return sp.Eq(g_cross(A, B, C, D), 0, evaluate=False)


def c_perpendicular(A, B, C, D):
    return sp.Eq(g_dot(A, B, C, D), 0, evaluate=False)


def c_midpoint(M, A, B):
    m, ab = _v(M), g_mid(A, B)
    return [sp.Eq(m[0], ab[0], evaluate=False), sp.Eq(m[1], ab[1], evaluate=False)]


def c_on_segment(P, A, B, t=None):
    """P on segment AB: P = A + t (B - A), 0 < t < 1 (t is a fresh unknown unless given)"""
    p, a, b = _v(P), _v(A), _v(B)
    if t is None:
        t = sp.Symbol(f"t_{P.name if hasattr(P, 'name') else 'seg'}", real=True)
    return [sp.Eq(p[0], a[0] + t * (b[0] - a[0]), evaluate=False),
            sp.Eq(p[1], a[1] + t * (b[1] - a[1]), evaluate=False)]


def c_equidistant(P, A, B):
    return sp.Eq(g_dist(P, A) ** 2, g_dist(P, B) ** 2, evaluate=False)


GEO_FUNCS = {
    "dist": g_dist, "angle": g_angle, "area": g_area, "perimeter": g_perimeter, "mid": g_mid,
    "px": g_x, "py": g_y, "signed_area": g_signed_area,
    "collinear": c_collinear, "parallel": c_parallel, "perpendicular": c_perpendicular,
    "midpoint": c_midpoint, "equidistant": c_equidistant,
}


# ---------------------------------------------------------------------------
# degree marks
# ---------------------------------------------------------------------------
def has_degree_mark(s: str) -> bool:
    return isinstance(s, str) and bool(_DEG_NUM_RE.search(s) or _DEG_PAREN_RE.search(s))


def strip_degree_marks(s: str) -> str:
    """`40°` -> `40`, `(a+b)°` -> `(a+b)`: angle() is measured in degrees, so a degree mark is
    the unit of the plain number, not a conversion to radians."""
    s = _DEG_PAREN_RE.sub(r"(\1)", s)
    return _DEG_NUM_RE.sub(r"\1", s)


def _uses_coordinates(texts) -> bool:
    import re
    return any(re.search(r"(?<![\w.])p[xy]\s*\(", t) for t in texts if isinstance(t, str))


# ---------------------------------------------------------------------------
# realisation engine
# ---------------------------------------------------------------------------
_HI_DPS = 80                   # precision of the polished realisations used for the comparison
_HI_EQUAL = mp.mpf("1e-60")    # |claim - value| <= this * max(1, |value|)  -> equal
_HI_DIFFERENT = mp.mpf("1e-40")  # above this (same scale) -> genuinely different
_LO_DIFFERENT = mp.mpf("1e-8")   # without a polished value only a gross difference refutes


def _to_mpf(v):
    if isinstance(v, sp.Rational):
        return mp.mpf(v.p) / v.q
    if isinstance(v, (mp.mpf, mp.mpc)):
        return v
    return mp.mpf(str(v))


class GeoProblem:
    def __init__(self, points: list[str], constraints: list[str], target: str, seed: int = 0,
                 extra_ns: dict | None = None):
        self.points = list(points)
        self.seed = seed
        self.syms: dict[str, sp.Symbol] = {}
        ns: dict[str, Any] = dict(_SAFE_NAMES)
        ns.update(GEO_FUNCS)
        if extra_ns:
            ns.update(extra_ns)
        for p in self.points:
            sx, sy = sp.Symbol(f"{p}_x", real=True), sp.Symbol(f"{p}_y", real=True)
            self.syms[f"{p}_x"], self.syms[f"{p}_y"] = sx, sy
            ns[p] = Matrix([sx, sy])
        self.ns = ns
        self.raw_constraints = list(constraints)
        # gauge (rotation + translation only): P1 = (0, 0), P2 on the x-axis. Never the scale.
        self.fixed: dict[sp.Symbol, Any] = {}
        self.gauge = not _uses_coordinates(list(constraints) + [target])
        if self.gauge:
            p1, p2 = self.points[0], self.points[1]
            self.fixed[self.syms[f"{p1}_x"]] = sp.Integer(0)
            self.fixed[self.syms[f"{p1}_y"]] = sp.Integer(0)
            self.fixed[self.syms[f"{p2}_y"]] = sp.Integer(0)
        self.residuals: list[Any] = []
        for c in constraints:
            rel = self._parse(c)
            rels = rel if isinstance(rel, list) else [rel]
            for r in rels:
                self.residuals.append(self._to_residual(r))
        self.target = self._parse_expr(strip_degree_marks(target))
        # informational only: nothing is decided from it any more (see the module docstring)
        self.scale_fixed = self._scale_is_fixed()
        self.unknowns = [s for s in self.syms.values() if s not in self.fixed]
        # constraint-introduced parameters (e.g. t for on-segment)
        extra = set()
        for r in self.residuals:
            extra |= {s for s in r.free_symbols if s not in self.syms.values()}
        self.params = sorted(extra, key=lambda s: s.name)
        self.unknowns += self.params
        self.n_free = len(self.unknowns) - len(self.residuals)

    # ---- parsing -----------------------------------------------------------
    def _parse(self, s: str):
        s2 = preclean(strip_degree_marks(s))
        if any(op in s2 for op in ("<", ">", "!=")):
            raise ParseError("inequality constraints are not supported in geometry_numeric")
        if "=" in s2:
            return parse_relation(s2, self.ns)
        val = self._parse_expr(s2)
        return val

    def _parse_expr(self, s: str):
        from ..normalize.parse import parse_expr_str
        return parse_expr_str(s, self.ns)

    def _to_residual(self, rel):
        if isinstance(rel, sp.Equality):
            lhs, rhs = rel.lhs, rel.rhs
            # squared distances keep residuals polynomial
            return sp.expand(lhs - rhs)
        raise ParseError(f"constraint must be an equation: {rel}")

    def _scale_is_fixed(self) -> bool:
        for r in self.residuals:
            if r.has(sp.sqrt) or any(isinstance(a, sp.Pow) for a in r.atoms(sp.Pow)):
                consts = [a for a in r.atoms(sp.Number) if a not in (0, 1, -1, 2, -2, sp.Rational(1, 2))]
                if consts or (r.is_polynomial() and any(t.is_number and t != 0 for t in sp.Add.make_args(r))):
                    return True
        return False

    # ---- numeric solve ----------------------------------------------------
    def _free_value(self, s, rng):
        # exact rationals: the same realisation can then be polished at any precision
        if s.name.startswith("t_"):
            return sp.Rational(rng.randint(150, 850), 1000)
        return sp.Rational(rng.randint(-3000, 3000), 1000)

    def realise(self, n: int = _N_REAL, dps: int = _DPS, n_polish: int = 2
                ) -> tuple[list[Any], dict[str, Any]]:
        """Return list of target values (mpf) from independent realisations + evidence.
        `ev["hi_values"]` holds up to `n_polish` of them recomputed at _HI_DPS digits."""
        rng = random.Random(self.seed)
        ev: dict[str, Any] = {"n_unknowns": len(self.unknowns), "n_constraints": len(self.residuals),
                              "n_free": self.n_free, "scale_fixed": self.scale_fixed, "gauge": self.gauge,
                              "attempts": 0, "realisations": 0, "degenerate": 0}
        subs_fixed = dict(self.fixed)
        res = [r.subs(subs_fixed) for r in self.residuals]
        tgt = self.target.subs(subs_fixed)
        values = []
        solved: list[tuple[list, list, dict, dict]] = []
        if self.n_free < 0:
            ev["error"] = "overdetermined"
            return values, ev
        with mp.workdps(dps):
            attempts = 0
            while len(values) < n and attempts < n * 6:
                attempts += 1
                free = rng.sample(self.unknowns, self.n_free) if self.n_free else []
                fv = {s: self._free_value(s, rng) for s in free}
                solve_for = [s for s in self.unknowns if s not in free]
                res_k = [r.subs(fv) for r in res]
                sol = _newton(res_k, solve_for, rng, dps)
                if sol is None:
                    continue
                full = {s: _to_mpf(v) for s, v in fv.items()}
                full.update(sol)
                # degeneracy: all points distinct
                pts = {}
                for p in self.points:
                    sx, sy = self.syms[f"{p}_x"], self.syms[f"{p}_y"]
                    pts[p] = (_to_mpf(subs_fixed.get(sx, full.get(sx))), _to_mpf(subs_fixed.get(sy, full.get(sy))))
                degenerate = False
                names = list(pts)
                for i in range(len(names)):
                    for j in range(i + 1, len(names)):
                        if mp.hypot(pts[names[i]][0] - pts[names[j]][0], pts[names[i]][1] - pts[names[j]][1]) < mp.mpf("1e-6"):
                            degenerate = True
                if degenerate:
                    ev["degenerate"] += 1
                    continue
                val = _eval_target(tgt, full)
                if val is None:
                    continue
                values.append(val)
                solved.append((res_k, solve_for, sol, fv))
            ev["attempts"] = attempts
            ev["realisations"] = len(values)
            ev["sample_values"] = [mp.nstr(v, 15) for v in values[:4]]
        # polish the first realisations at high precision (Newton converges quadratically from
        # a 1e-22 solution of a regular system; a singular one does not polish and is reported)
        hi = []
        for res_k, solve_for, sol, fv in solved[:n_polish]:
            with mp.workdps(_HI_DPS):
                sol_hi = _polish(res_k, solve_for, sol, _HI_DPS)
                if sol_hi is None:
                    continue
                full = {s: _to_mpf(v) for s, v in fv.items()}
                full.update(sol_hi)
                v = _eval_target(tgt, full)
                if v is not None:
                    hi.append(mp.nstr(v, _HI_DPS))
        ev["hi_values"] = hi
        return values, ev


def _eval_target(tgt, full):
    try:
        f = sp.lambdify(list(full.keys()), tgt, "mpmath")
        val = f(*[_to_mpf(v) for v in full.values()])
    except Exception:  # noqa: BLE001
        return None
    if isinstance(val, mp.mpc):
        if abs(val.imag) > mp.mpf(10) ** (-(mp.mp.dps - 10)):
            return None
        val = val.real
    return val


def _newton(residuals, unknowns, rng, dps, tries: int = 12, iters: int = 80):
    """Damped Newton / Levenberg–Marquardt on a square (or over-determined) system."""
    if not unknowns:
        # nothing to solve: check residuals vanish
        with mp.workdps(dps):
            if all(abs(mp.mpf(str(sp.N(r, dps)))) < mp.mpf(_RES_TOL) for r in residuals):
                return {}
        return None
    F = sp.Matrix(residuals)
    J = F.jacobian(unknowns)
    fF = sp.lambdify(unknowns, F, "mpmath")
    fJ = sp.lambdify(unknowns, J, "mpmath")
    for _ in range(tries):
        x = mp.matrix([mp.mpf(rng.uniform(-3, 3)) if not u.name.startswith("t_") else mp.mpf(rng.uniform(0.15, 0.85))
                       for u in unknowns])
        x = _lm(fF, fJ, x, len(unknowns), mp.mpf(_RES_TOL), iters)
        if x is not None:
            return {u: x[i] for i, u in enumerate(unknowns)}
    return None


def _lm(fF, fJ, x, n_unk, tol, iters):
    lam = mp.mpf("1e-3")
    for _it in range(iters):
        try:
            Fx = mp.matrix(fF(*x))
            Jx = mp.matrix(fJ(*x))
        except (ZeroDivisionError, ValueError):
            return None
        nrm = mp.norm(Fx)
        if nrm < tol:
            return x
        try:
            A = Jx.T * Jx + lam * mp.eye(n_unk)
            dx = mp.lu_solve(A, -(Jx.T * Fx))
        except ZeroDivisionError:
            return None
        x_new = x + dx
        try:
            nrm_new = mp.norm(mp.matrix(fF(*x_new)))
        except (ZeroDivisionError, ValueError):
            lam *= 10
            continue
        if nrm_new < nrm:
            x = x_new
            lam = max(lam / 3, mp.mpf("1e-60"))
        else:
            lam *= 10
            if lam > mp.mpf("1e12"):
                return None
    return None


def _polish(residuals, unknowns, sol, dps):
    """Refine a solution found at _DPS to `dps` digits; None when it does not converge."""
    if not unknowns:
        with mp.workdps(dps):
            if all(abs(_to_mpf(sp.N(r, dps + 5))) < mp.mpf(10) ** (-(dps - 10)) for r in residuals):
                return {}
        return None
    F = sp.Matrix(residuals)
    J = F.jacobian(unknowns)
    fF = sp.lambdify(unknowns, F, "mpmath")
    fJ = sp.lambdify(unknowns, J, "mpmath")
    x = mp.matrix([mp.mpf(sol[u]) for u in unknowns])
    x = _lm(fF, fJ, x, len(unknowns), mp.mpf(10) ** (-(dps - 10)), 60)
    return None if x is None else {u: x[i] for i, u in enumerate(unknowns)}


def compare_claim(claimed, hi_values: list[str], v0) -> tuple[bool | None, dict[str, Any]]:
    """Claim vs the realised target value. Exact claims are never snapped to a tolerance: at
    _HI_DPS digits the claim must agree to 1e-60 (relative to max(1, |value|)); a claim with a
    nonzero imaginary part is not a real length/angle."""
    ev: dict[str, Any] = {}
    if hi_values:
        with mp.workdps(_HI_DPS):
            vh = [mp.mpf(s) for s in hi_values]
            scale = max(abs(vh[0]), mp.mpf(1))
            if any(abs(v - vh[0]) > _HI_EQUAL * scale for v in vh[1:]):
                ev["reason"] = "polished_realisations_disagree"
                return None, ev
            try:
                cv = to_mp(claimed, _HI_DPS)
            except Exception as e:  # noqa: BLE001
                ev["reason"] = f"claim_not_numeric: {e}"
                return None, ev
            diff = abs(cv - vh[0])
            ev["abs_diff@80"] = mp.nstr(diff, 5)
            if isinstance(cv, mp.mpc) and cv.imag != 0:
                ev["reason"] = "claim_is_not_real"
                return False, ev
            if diff <= _HI_EQUAL * scale:
                ev["decided_by"] = "agree_to_1e-60_at_80_digits"
                return True, ev
            if diff > _HI_DIFFERENT * scale:
                ev["decided_by"] = "differ_above_1e-40_at_80_digits"
                return False, ev
            ev["reason"] = "difference_between_1e-60_and_1e-40"
            return None, ev
    # no polished value (singular system): only a gross difference is evidence
    with mp.workdps(_DPS):
        try:
            cv = to_mp(claimed, _DPS)
        except Exception as e:  # noqa: BLE001
            ev["reason"] = f"claim_not_numeric: {e}"
            return None, ev
        diff = abs(cv - v0)
        if diff > _LO_DIFFERENT * max(abs(v0), mp.mpf(1)):
            ev["decided_by"] = "gross_difference_without_polish"
            return False, ev
    ev["reason"] = "not_polished_no_decision"
    return None, ev


def certify_geometry(points, constraints, target, claimed, seed: int = 0, extra_ns=None,
                     timeout: float = 25.0) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"points": list(points), "constraints": list(constraints), "target": target,
                          "claimed": str(claimed)}
    try:
        # parsed here first so that a malformed IR is reported without starting the sandbox
        GeoProblem(points, constraints, target, seed=seed, extra_ns=extra_ns)
    except ParseError as e:
        ev["error"] = f"parse_error: {e}"
        return None, ev
    except Exception as e:  # noqa: BLE001
        ev["error"] = f"setup_error: {type(e).__name__}: {e}"
        return None, ev
    r = sb_run("mathverify.certify.geometry_numeric:_realise_worker", points, constraints, target, seed,
               timeout=timeout)
    if not r.ok:
        ev["error"] = r.error
        ev["flags"] = r.flags
        return None, ev
    values, rev = r.value
    ev.update(rev)
    if len(values) < 3:
        ev["reason"] = "too_few_realisations"
        return None, ev
    # target must be configuration-independent
    with mp.workdps(_DPS):
        v0 = mp.mpf(values[0])
        scale = max(abs(v0), mp.mpf(1))
        spread = max(abs(mp.mpf(v) - v0) for v in values) / scale
    ev["spread"] = mp.nstr(spread, 5)
    if spread > mp.mpf("1e-15"):
        ev["reason"] = "target_not_determined_by_constraints"
        return None, ev
    ok, cev = compare_claim(claimed, rev.get("hi_values") or [], v0)
    ev["compare"] = cev
    if cev.get("reason"):
        ev["reason"] = cev["reason"]
    ev["value"] = mp.nstr(v0, 25)
    return ok, ev


def _realise_worker(points, constraints, target, seed):
    gp = GeoProblem(points, constraints, target, seed=seed)
    values, ev = gp.realise()
    return [mp.nstr(v, 40) for v in values], ev


def _claim_for_angle_units(ctx: Ctx, solution, target: str):
    """The claim, read with degree marks meaning degrees (angle targets only)."""
    from ..normalize.parse import parse_expr_str
    payload = solution.claimed_answer.payload
    if not has_degree_mark(payload):
        return ctx.claimed(solution), False
    if "angle(" not in target:
        raise ValueError("a degree mark on a claim whose target is not an angle")
    v = parse_expr_str(strip_degree_marks(payload), ctx.claim_ns(solution))
    calc = (sp.Integral, sp.Derivative, sp.Limit, sp.Sum, sp.Product)
    if getattr(v, "has", None) and v.has(*calc):
        raise ValueError("claimed answer is an unevaluated computation")
    return v, True


def verify(ir, solution, ctx: Ctx):
    """Task `synthetic_geometry`: params {"points": [...], "constraints": [...], "target": str}."""
    if ir.task.kind != "synthetic_geometry":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        try:
            claimed, _deg = _claim_for_angle_units(ctx, solution, str(p.get("target", "")))
        except Exception as e:  # noqa: BLE001
            return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
        if isinstance(claimed, sp.Set) or claimed is None or not isinstance(claimed, sp.Expr):
            return unknown(LAYER, "claimed_not_scalar")
        ok, ev = certify_geometry(p["points"], p["constraints"], p["target"], claimed, seed=ctx.seed,
                                  timeout=ctx.timeout)
        if ok is False and "angle(" in str(p["target"]) and claimed.has(pi) and ev.get("hi_values"):
            # `pi/2` for a 90-degree target: right in radians, the unit is the only question
            alt, _ = compare_claim(claimed * 180 / pi, ev["hi_values"], mp.mpf(0))
            if alt is True:
                ok = None
                ev["reason"] = "claim_matches_in_radians_target_is_in_degrees"
    if ok is True:
        return result(LAYER, "pass", 0.97, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.97, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", ev.get("error", "undecided")), t.ms, ev,
                   flags=(["ir_incomplete"] if ev.get("reason") == "target_not_determined_by_constraints" else []))
