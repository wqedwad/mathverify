"""Sequences, recurrences and series (F2, handoff §7 `series`).

* `recurrence_term`: iterate the recurrence exactly from the initial terms.
* `closed_form`: the claimed general term must reproduce the initial terms AND satisfy the
  recurrence — symbolically when SymPy can prove it, else on n = 1..20 exactly (for a linear
  recurrence of order r, agreement on r initial terms plus the recurrence holding is a proof;
  the 20-term check is the fallback and is reported as such). `rsolve` is recorded as an
  independent derivation but never decides on its own.
* `series_sum`: finite sums exactly; infinite sums by symbolic summation cross-checked with
  mpmath `nsum` (numeric); both must agree before the claim is compared.
"""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp
from sympy import oo, Function, Lambda

from ..equiv import answers_equivalent
from ..equiv.numeric import num_equal
from ..normalize.parse import parse_relation, parse_expr_str, ParseError
from ..sandbox import run as sb_run
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.series"
N_CHECK = 20


def _rec_ns(ctx: Ctx, fname: str, var: str):
    ns = dict(ctx.ns)
    ns[fname] = Function(fname)
    n = ns.get(var)
    if not isinstance(n, sp.Symbol):
        n = sp.Symbol(var, integer=True)
        ns[var] = n
    return ns, ns[fname], n


def _parse_initial(initial: dict, ns) -> dict[int, Any]:
    out = {}
    for k, v in initial.items():
        idx = int(sp.sympify(str(k)))
        out[idx] = parse_expr_str(str(v), ns)
    return out


def iterate_recurrence(rel, f, n, initial: dict[int, Any], index: int) -> tuple[Any | None, dict]:
    """Solve rel (an equation involving f(n), f(n-1), ...) for f(n) and iterate to `index`."""
    ev: dict[str, Any] = {}
    fn = f(n)
    sol = sp.solve(rel, fn)
    if not sol:
        ev["error"] = "cannot_isolate_f(n)"
        return None, ev
    expr = sol[0]
    known = dict(initial)
    shifts = sorted({int(a.args[0] - n) for a in expr.atoms(sp.core.function.AppliedUndef) if a.func == f},
                    reverse=True)
    if not shifts or max(shifts) >= 0:
        ev["error"] = "recurrence_not_explicit"
        return None, ev
    start = max(known) + 1 if known else None
    if start is None:
        ev["error"] = "no_initial_terms"
        return None, ev
    for k in range(start, index + 1):
        sub = {f(k + s): known.get(k + s) for s in shifts}
        if any(v is None for v in sub.values()):
            ev["error"] = f"missing_initial_term_for_{k}"
            return None, ev
        val = expr.subs(n, k).subs(sub)
        known[k] = sp.nsimplify(sp.simplify(val))
    if index not in known:
        ev["error"] = "index_before_initial_terms"
        return None, ev
    ev["terms"] = {str(k): str(v) for k, v in sorted(known.items())[:12]}
    return known[index], ev


def check_closed_form(rel, f, n, initial: dict[int, Any], closed, timeout: float = 8.0
                      ) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"closed": str(closed)}
    # initial terms
    for k, v in initial.items():
        val = closed.subs(n, k)
        ok, _ = answers_equivalent(val, v, shape="scalar")
        if ok is False:
            ev["reason"] = f"initial_term_{k}_mismatch"
            ev["got"] = str(val)
            return False, ev
        if ok is None:
            ev["reason"] = f"initial_term_{k}_undecided"
            return None, ev
    # symbolic recurrence check
    sub = rel.replace(f, Lambda(n, closed))
    diff = sub.lhs - sub.rhs
    r = sb_run("mathverify.sandbox.ops:zero_test_battery", diff, timeout=timeout)
    if r.ok and r.value is True:
        ev["method"] = "symbolic_recurrence"
        return True, ev
    # exact term-by-term check on n = start..N_CHECK
    start = min(initial) if initial else 1
    shifts = [int(a.args[0] - n) for a in rel.atoms(sp.core.function.AppliedUndef) if a.func == f]
    lo = start + max(0, -min(shifts)) if shifts else start
    for k in range(lo, lo + N_CHECK):
        val = diff.subs(n, k)
        ok, _ = num_equal(val, 0, abs_tol=1e-25)
        if ok is False:
            ev["reason"] = f"recurrence_fails_at_n={k}"
            ev["residual"] = str(sp.simplify(val))
            return False, ev
        if ok is None:
            ev["reason"] = f"recurrence_undecided_at_n={k}"
            return None, ev
    ev["method"] = f"exact_terms_{lo}..{lo + N_CHECK - 1}"
    return True, ev


def _rsolve_worker(rel, f, n, initial):
    fn = f(n)
    try:
        r = sp.rsolve(rel, fn, {f(k): v for k, v in initial.items()})
        return r
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}: {e}"


def _nsum_worker(term, var, lo, hi, dps=30):
    mp.mp.dps = dps
    fn = sp.lambdify(var, term, "mpmath")
    a = mp.mpf(str(sp.N(lo, dps + 5)))
    b = mp.inf if hi == oo else mp.mpf(str(sp.N(hi, dps + 5)))
    return mp.nstr(mp.nsum(fn, [a, b]), dps)


def certify_series_sum(term, var, lo, hi, claimed, timeout: float = 10.0) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"term": str(term), "lo": str(lo), "hi": str(hi), "claimed": str(claimed)}
    if hi != oo and lo != -oo:
        try:
            lo_i, hi_i = int(lo), int(hi)
        except TypeError:
            ev["error"] = "non_integer_bounds"
            return None, ev
        if hi_i - lo_i > 200_000:
            ev["error"] = "finite_sum_too_long"
            return None, ev
        total = sp.Add(*[term.subs(var, k) for k in range(lo_i, hi_i + 1)]) if hi_i - lo_i < 2000 else \
            sp.summation(term, (var, lo_i, hi_i))
        total = sp.nsimplify(sp.simplify(total)) if hi_i - lo_i < 2000 else total
        ev["sum"] = str(total)
        ev["method"] = "exact_finite"
        ok, cev = answers_equivalent(claimed, total, shape="scalar")
        ev["compare"] = cev
        return ok, ev
    rs = sb_run("mathverify.certify.series:_summation_worker", term, var, lo, hi, timeout=timeout)
    rn = sb_run("mathverify.certify.series:_nsum_worker", term, var, lo, hi, 30, timeout=timeout * 2)
    sym_val = rs.value if rs.ok and not isinstance(rs.value, str) and not rs.value.has(sp.Sum) else None
    num_val = sp.Float(rn.value, 30) if rn.ok else None
    ev["symbolic"] = str(sym_val) if sym_val is not None else (rs.error if not rs.ok else "unevaluated")
    ev["numeric"] = str(num_val) if num_val is not None else rn.error
    if sym_val is not None and num_val is not None:
        agree, _ = num_equal(sym_val, num_val, rel_tol=1e-15)
        ev["symbolic_numeric_agree"] = agree
        if agree is False:
            ev["reason"] = "symbolic_numeric_disagreement"
            return None, ev
        ok, cev = answers_equivalent(claimed, sym_val, shape="scalar")
        ev["compare"] = cev
        ev["method"] = "symbolic+numeric"
        return ok, ev
    if num_val is not None:
        ok, cev = num_equal(claimed, num_val, rel_tol=1e-15)
        ev["compare"] = cev
        ev["method"] = "numeric_only"
        if ok is False:
            return False, ev
        ev["reason"] = "numeric_only_no_symbolic_confirmation"
        return None, ev
    ev["reason"] = "summation_failed"
    return None, ev


def _summation_worker(term, var, lo, hi):
    try:
        return sp.summation(term, (var, lo, hi))
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}: {e}"


def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("recurrence_term", "closed_form", "series_sum"):
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        ev: dict[str, Any] = {}
        if kind in ("recurrence_term", "closed_form"):
            fname, var = p.get("name", "a"), p.get("var", "n")
            try:
                ns, f, n = _rec_ns(ctx, fname, var)
                rel = parse_relation(p["recurrence"], ns)
                initial = _parse_initial(p.get("initial", {}), ns)
            except (ParseError, Exception) as e:  # noqa: BLE001
                return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
            if not isinstance(rel, sp.Equality):
                return unknown(LAYER, "recurrence_not_an_equation")
            if kind == "recurrence_term":
                claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
                if err:
                    return err
                r = sb_run("mathverify.certify.series:_iterate_worker", rel, f, n, initial, int(p["index"]),
                           timeout=ctx.timeout)
                if not r.ok:
                    return unknown(LAYER, r.error or "iteration_failed", 0, flags=r.flags)
                val, iev = r.value
                ev.update(iev)
                if val is None:
                    return unknown(LAYER, iev.get("error", "iteration_failed"), 0, ev)
                ev["value"] = str(val)
                ok, cev = answers_equivalent(claimed, val, shape="scalar")
                ev["compare"] = cev
                conf = 0.99
            else:
                from ..normalize.parse import parse_expr_str as _pe
                try:
                    closed = _pe(str(solution.claimed_answer.payload), ns)
                except Exception as e:  # noqa: BLE001
                    return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
                ok, cev = check_closed_form(rel, f, n, initial, closed, timeout=ctx.timeout)
                ev.update(cev)
                rr = sb_run("mathverify.certify.series:_rsolve_worker", rel, f, n, initial, timeout=ctx.timeout)
                ev["rsolve"] = str(rr.value) if rr.ok else rr.error
                conf = 0.99 if ev.get("method") == "symbolic_recurrence" else 0.96
        else:
            var = ctx.sym(p.get("var", "k"))
            term, err = parse_or_unknown(LAYER, ctx.expr, p["term"])
            if err:
                return err
            lo, err = parse_or_unknown(LAYER, ctx.expr, str(p.get("lo", "1")))
            if err:
                return err
            hi, err = parse_or_unknown(LAYER, ctx.expr, str(p.get("hi", "oo")))
            if err:
                return err
            claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
            if err:
                return err
            ok, cev = certify_series_sum(term, var, lo, hi, claimed, timeout=ctx.timeout)
            ev.update(cev)
            conf = 0.99 if ev.get("method") in ("exact_finite", "symbolic+numeric") else 0.95
    if ok is True:
        return result(LAYER, "pass", conf, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", "undecided"), t.ms, ev)


def _iterate_worker(rel, f, n, initial, index):
    return iterate_recurrence(rel, f, n, initial, index)
