"""Linear algebra certificates (F2, handoff §7 `linalg`): exact checks, never recomputation
where a check suffices (inverse: M·C = I; eigenvector: M v = λ v; system: A x = b + uniqueness).

Task `linalg`, params {"op": ...}:
  * matrix_expr  {"expr"}                  claimed matrix compared entry-wise
  * eigenvalues  {"matrix"}                claimed set (multiplicity ignored) or list (with multiplicity)
  * eigenvector  {"matrix", "eigenvalue"}  claimed vector: M v = λ v, v ≠ 0
  * inverse      {"matrix"}                claimed matrix: M C = C M = I
  * solve_system {"A", "b"}                claimed vector: A x = b and det(A) ≠ 0 (uniqueness)
  * rank / det / trace                     use `evaluate` with rank()/det()/trace()
"""
from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Matrix, eye, FiniteSet

from ..equiv import answers_equivalent, as_matrix as _as_matrix, matrices_equal
from ..equiv.sets import scalar_equal, set_equal
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.linalg"


def _as_vector(obj) -> Matrix | None:
    m = _as_matrix(obj)
    if m is None:
        return None
    if m.shape[0] == 1:
        return m.T
    if m.shape[1] == 1:
        return m
    return None


def _det_worker(M):
    return Matrix(M).det()


def _eig_worker(M):
    return Matrix(M).eigenvals()


def verify(ir, solution, ctx: Ctx):
    if ir.task.kind != "linalg":
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        op = p.get("op")
        ev: dict[str, Any] = {"op": op}
        if op == "matrix_expr":
            truth, err = parse_or_unknown(LAYER, ctx.expr, p["expr"])
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            T, C = _as_matrix(truth), _as_matrix(claimed)
            if T is None or C is None:
                return unknown(LAYER, "not_matrices")
            ok, cev = matrices_equal(C, T)
            ev.update(cev)
            ev["truth"] = str(T)
        elif op in ("eigenvalues", "eigenvector", "inverse"):
            M, err = parse_or_unknown(LAYER, ctx.expr, p["matrix"])
            if err:
                return err
            M = _as_matrix(M)
            if M is None or M.shape[0] != M.shape[1]:
                return unknown(LAYER, "matrix_not_square")
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            if op == "eigenvalues":
                r = sb_run("mathverify.certify.linalg:_eig_worker", M, timeout=ctx.timeout)
                if not r.ok:
                    return unknown(LAYER, r.error or "eigenvals_failed", 0, flags=r.flags)
                eig = r.value                              # {value: multiplicity}
                ev["eigenvalues"] = {str(k): v for k, v in eig.items()}
                if isinstance(claimed, sp.Set):
                    ok, cev = set_equal(claimed, FiniteSet(*eig.keys()))
                else:
                    cl = list(claimed) if isinstance(claimed, (tuple, list, sp.Tuple)) else [claimed]
                    truth_list = [k for k, m in eig.items() for _ in range(m)]
                    if len(cl) != len(truth_list):
                        ok, cev = False, {"reason": "multiplicity_count_differs"}
                    else:
                        rem = list(truth_list)
                        ok = True
                        for c in cl:
                            hit = next((j for j, v in enumerate(rem) if scalar_equal(c, v) is True), None)
                            if hit is None:
                                ok = False
                                break
                            rem.pop(hit)
                        cev = {"method": "multiset_compare"}
                ev["compare"] = cev
            elif op == "eigenvector":
                lam, err = parse_or_unknown(LAYER, ctx.expr, str(p["eigenvalue"]))
                if err:
                    return err
                v = _as_vector(claimed)
                if v is None or v.shape[0] != M.shape[0]:
                    return unknown(LAYER, "claimed_not_a_vector_of_right_size")
                if all(scalar_equal(x, 0) is True for x in v):
                    ev["reason"] = "zero_vector"
                    ok = False
                else:
                    resid = (M * v - lam * v).applyfunc(sp.simplify)
                    ev["residual"] = str(resid.T)
                    ok = all(scalar_equal(x, 0) is True for x in resid)
                    if not ok and any(scalar_equal(x, 0) is None for x in resid):
                        ok = None
            else:  # inverse
                C = _as_matrix(claimed)
                if C is None or C.shape != M.shape:
                    return unknown(LAYER, "claimed_not_a_matrix_of_right_shape")
                prod1 = (M * C).applyfunc(sp.simplify)
                prod2 = (C * M).applyfunc(sp.simplify)
                ok1, _ = matrices_equal(prod1, eye(M.shape[0]))
                ok2, _ = matrices_equal(prod2, eye(M.shape[0]))
                ev["MC"], ev["CM"] = str(prod1), str(prod2)
                ok = True if (ok1 is True and ok2 is True) else (False if (ok1 is False or ok2 is False) else None)
        elif op == "solve_system":
            A, err = parse_or_unknown(LAYER, ctx.expr, p["A"])
            if err:
                return err
            b, err = parse_or_unknown(LAYER, ctx.expr, p["b"])
            if err:
                return err
            A, b = _as_matrix(A), _as_vector(b)
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            x = _as_vector(claimed)
            if A is None or b is None or x is None or x.shape[0] != A.shape[1]:
                return unknown(LAYER, "bad_shapes")
            resid = (A * x - b).applyfunc(sp.simplify)
            ev["residual"] = str(resid.T)
            satisfied = all(scalar_equal(r_, 0) is True for r_ in resid)
            if not satisfied:
                ok = False if all(scalar_equal(r_, 0) is not None for r_ in resid) else None
            else:
                if A.shape[0] == A.shape[1]:
                    rd = sb_run("mathverify.certify.linalg:_det_worker", A, timeout=ctx.timeout)
                    if rd.ok:
                        ev["det"] = str(rd.value)
                        ok = True if scalar_equal(rd.value, 0) is False else None
                        if ok is None:
                            ev["reason"] = "system_not_uniquely_solvable"
                    else:
                        ok = None
                else:
                    ok = None
                    ev["reason"] = "non_square_uniqueness_not_checked"
        else:
            return unknown(LAYER, f"unknown_op:{op}")
    if ok is True:
        return result(LAYER, "pass", 0.99, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", "undecided"), t.ms, ev)
