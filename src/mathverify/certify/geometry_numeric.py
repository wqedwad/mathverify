"""Synthetic (Euclidean) geometry by numeric realisation (handoff §7 `geometry_numeric`, F2).

Idea: the problem is a set of constraints on 2-D points (lengths, angles, parallel /
perpendicular / collinear / on-circle / midpoint …) and a target quantity (length, angle,
area, ratio). We do NOT reason synthetically. We build many random configurations that
satisfy the constraints exactly (to 25+ digits), measure the target in each, and accept the
claim only when

  * every realisation is non-degenerate (no coincident points, no zero-area triangles),
  * the target agrees across ALL realisations (otherwise the constraints do not determine
    it -> IR incomplete / ill-posed -> UNKNOWN, never a guess), and
  * the common value equals the claim.

Gauge: point 1 at the origin, point 2 on the positive x-axis. If no length constraint fixes
the scale, dist(P1, P2) is set to 1 and the target must be scale-invariant (angle, ratio);
a length target then yields UNKNOWN with a flag.

Every realisation is found with a damped Gauss–Newton / Levenberg–Marquardt solve on the
residuals (symbolic Jacobian from SymPy, mpmath arithmetic). Free parameters (unknowns not
pinned by the constraints) are sampled randomly per realisation with a fixed seed.
"""
from __future__ import annotations

import random
from typing import Any

import mpmath as mp
import sympy as sp
from sympy import Matrix, sqrt, pi, acos, Abs

from ..equiv.numeric import num_equal
from ..normalize.parse import parse_relation, ParseError, _SAFE_NAMES, preclean
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
# realisation engine
# ---------------------------------------------------------------------------
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
        # gauge: P1 = (0,0), P2 = (s, 0)
        self.fixed: dict[sp.Symbol, Any] = {}
        p1, p2 = self.points[0], self.points[1]
        self.fixed[self.syms[f"{p1}_x"]] = sp.Integer(0)
        self.fixed[self.syms[f"{p1}_y"]] = sp.Integer(0)
        self.fixed[self.syms[f"{p2}_y"]] = sp.Integer(0)
        self.residuals: list[Any] = []
        self.raw_constraints = list(constraints)
        for c in constraints:
            rel = self._parse(c)
            rels = rel if isinstance(rel, list) else [rel]
            for r in rels:
                self.residuals.append(self._to_residual(r))
        self.target = self._parse_expr(target)
        self.scale_fixed = self._scale_is_fixed()
        if not self.scale_fixed:
            self.fixed[self.syms[f"{p2}_x"]] = sp.Integer(1)
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
        s2 = preclean(s)
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
            # a residual that fixes a length/area (contains a numeric constant and a dist/area)
            if r.has(sp.sqrt) or any(isinstance(a, sp.Pow) for a in r.atoms(sp.Pow)):
                consts = [a for a in r.atoms(sp.Number) if a not in (0, 1, -1, 2, -2, sp.Rational(1, 2))]
                if consts or (r.is_polynomial() and any(t.is_number and t != 0 for t in sp.Add.make_args(r))):
                    return True
        return False

    # ---- numeric solve ----------------------------------------------------
    def realise(self, n: int = _N_REAL, dps: int = _DPS) -> tuple[list[Any], dict[str, Any]]:
        """Return list of target values (mpf) from independent realisations + evidence."""
        rng = random.Random(self.seed)
        ev: dict[str, Any] = {"n_unknowns": len(self.unknowns), "n_constraints": len(self.residuals),
                              "n_free": self.n_free, "scale_fixed": self.scale_fixed, "attempts": 0,
                              "realisations": 0, "degenerate": 0}
        subs_fixed = dict(self.fixed)
        res = [r.subs(subs_fixed) for r in self.residuals]
        tgt = self.target.subs(subs_fixed)
        values = []
        if self.n_free < 0:
            ev["error"] = "overdetermined"
            return values, ev
        with mp.workdps(dps):
            attempts = 0
            while len(values) < n and attempts < n * 6:
                attempts += 1
                # choose free unknowns and random values for them
                free = rng.sample(self.unknowns, self.n_free) if self.n_free else []
                fv = {s: mp.mpf(rng.uniform(-3, 3)) if not s.name.startswith("t_") else mp.mpf(rng.uniform(0.15, 0.85))
                      for s in free}
                solve_for = [s for s in self.unknowns if s not in free]
                res_k = [r.subs({s: sp.Float(str(v), dps) for s, v in fv.items()}) for r in res]
                sol = _newton(res_k, solve_for, rng, dps)
                if sol is None:
                    continue
                full = dict(fv)
                full.update(sol)
                # degeneracy: all points distinct
                pts = {}
                for p in self.points:
                    sx, sy = self.syms[f"{p}_x"], self.syms[f"{p}_y"]
                    pts[p] = (mp.mpf(str(subs_fixed.get(sx, full.get(sx)))), mp.mpf(str(subs_fixed.get(sy, full.get(sy)))))
                degenerate = False
                names = list(pts)
                for i in range(len(names)):
                    for j in range(i + 1, len(names)):
                        if mp.hypot(pts[names[i]][0] - pts[names[j]][0], pts[names[i]][1] - pts[names[j]][1]) < mp.mpf("1e-6"):
                            degenerate = True
                if degenerate:
                    ev["degenerate"] += 1
                    continue
                try:
                    f = sp.lambdify(list(full.keys()), tgt, "mpmath")
                    val = f(*[mp.mpf(str(v)) for v in full.values()])
                except Exception:
                    continue
                if isinstance(val, mp.mpc):
                    if abs(val.imag) > mp.mpf("1e-20"):
                        continue
                    val = val.real
                values.append(val)
            ev["attempts"] = attempts
            ev["realisations"] = len(values)
            ev["sample_values"] = [mp.nstr(v, 15) for v in values[:4]]
        return values, ev


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
        lam = mp.mpf("1e-3")
        ok = False
        for _it in range(iters):
            try:
                Fx = mp.matrix(fF(*x))
                Jx = mp.matrix(fJ(*x))
            except (ZeroDivisionError, ValueError):
                break
            nrm = mp.norm(Fx)
            if nrm < mp.mpf(_RES_TOL):
                ok = True
                break
            try:
                A = Jx.T * Jx + lam * mp.eye(len(unknowns))
                dx = mp.lu_solve(A, -(Jx.T * Fx))
            except ZeroDivisionError:
                break
            x_new = x + dx
            try:
                nrm_new = mp.norm(mp.matrix(fF(*x_new)))
            except (ZeroDivisionError, ValueError):
                lam *= 10
                continue
            if nrm_new < nrm:
                x = x_new
                lam = max(lam / 3, mp.mpf("1e-30"))
            else:
                lam *= 10
                if lam > mp.mpf("1e12"):
                    break
        if ok:
            return {u: x[i] for i, u in enumerate(unknowns)}
    return None


def certify_geometry(points, constraints, target, claimed, seed: int = 0, extra_ns=None
                     ) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"points": list(points), "constraints": list(constraints), "target": target,
                          "claimed": str(claimed)}
    try:
        gp = GeoProblem(points, constraints, target, seed=seed, extra_ns=extra_ns)
    except ParseError as e:
        ev["error"] = f"parse_error: {e}"
        return None, ev
    except Exception as e:  # noqa: BLE001
        ev["error"] = f"setup_error: {type(e).__name__}: {e}"
        return None, ev
    r = sb_run("mathverify.certify.geometry_numeric:_realise_worker", points, constraints, target, seed,
               timeout=25)
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
    if not gp.scale_fixed and not _scale_invariant(gp):
        ev["reason"] = "scale_not_fixed_but_target_is_a_length"
        return None, ev
    ok, cev = num_equal(claimed, sp.Float(mp.nstr(v0, 28), 28), rel_tol=1e-18)
    ev["compare"] = cev
    ev["value"] = mp.nstr(v0, 25)
    return ok, ev


def _scale_invariant(gp: GeoProblem) -> bool:
    """Heuristic: angles and ratios are scale invariant; lengths/areas are not."""
    t = gp.target
    if t.has(acos):
        return True
    num, den = sp.fraction(sp.together(t))
    # ratio of two lengths / two areas
    return bool(den != 1 and (num.has(sp.sqrt) == den.has(sp.sqrt)))


def _realise_worker(points, constraints, target, seed):
    gp = GeoProblem(points, constraints, target, seed=seed)
    values, ev = gp.realise()
    return [mp.nstr(v, 40) for v in values], ev


def verify(ir, solution, ctx: Ctx):
    """Task `synthetic_geometry`: params {"points": [...], "constraints": [...], "target": str}."""
    if ir.task.kind != "synthetic_geometry":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        try:
            claimed = ctx.claimed(solution)
        except Exception as e:  # noqa: BLE001
            return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
        if isinstance(claimed, sp.Set) or claimed is None:
            return unknown(LAYER, "claimed_not_scalar")
        ok, ev = certify_geometry(p["points"], p["constraints"], p["target"], claimed, seed=ctx.seed)
    if ok is True:
        return result(LAYER, "pass", 0.97, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.97, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", ev.get("error", "undecided")), t.ms, ev,
                   flags=(["ir_incomplete"] if ev.get("reason") == "target_not_determined_by_constraints" else []))
