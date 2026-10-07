"""Sequences, recurrences and series (F2, handoff §7 `series`).

* `recurrence_term`: iterate the recurrence exactly from the initial terms. The recurrence holds
  for the indices after the last given term (as it is read everywhere in this module). When it is
  implicit in a(n) (`a(n)**2 = 4*a(n-1)`), every real branch is followed and a value is certified
  only if it is the same on all of them; a branch is never picked silently.
* `closed_form`: CORRECT only with a PROOF — the claim reproduces every given term, the
  recurrence (explicit, uniquely solvable) holds for the claim symbolically for all n, the last
  `order` given terms are consecutive, and both the claim and the recurrence are defined as
  written at every index they are used. A finite window of terms is evidence for a refutation
  only (a concrete n where the recurrence fails), never for acceptance. rsolve is an
  independent derivation: if it contradicts a proved claim the verdict abstains.
* `series_sum`: finite sums exactly; infinite sums by symbolic summation cross-checked with
  mpmath `nsum` (numeric); both must agree before the claim is compared.

Audit of 25 Sep 2026 (measured before the change): `3*n - 1 + 3*floor(n/22)` and
`3*2**(n-1) + (n-1)*exp(-100*n)` were certified as closed forms (20-term window, abs_tol 1e-25);
every correct closed form of an arithmetic sequence crashed (`Eq(...)` evaluated to True);
`a(n) = a(n-1)*(n-3)/(n-3) + 1` gave a(5) = 5 although a(3) does not exist as written;
Σ_{k=-1}^{1} k/k = 3 was certified when k was declared positive; a lower bound 1/2 was truncated
to 0 by int(); the negative branch of a(n)**2 = 4*a(n-1) gave a(3) = -4*I.
"""
from __future__ import annotations

from typing import Any

import mpmath as mp
import sympy as sp
from sympy import oo, Function, Lambda

from ..equiv import answers_equivalent
from ..equiv.numeric import num_equal
from ..normalize.parse import parse_relation, parse_expr_str, ParseError, substitute_free
from ..sandbox import run as sb_run
from ..sandbox.exactsets import exact_solveset
from .base import Ctx, Timer, result, unknown, parse_or_unknown

LAYER = "certify.series"
N_CHECK = 20
MAX_BRANCHES = 64


def _rec_ns(ctx: Ctx, fname: str, var: str):
    """Namespace for a recurrence. The index is an integer and nothing more: a declared
    `positive_integer` would let SymPy drop definedness conditions (n/n) and simplify with the
    wrong sign at indices outside the declared range."""
    ns = dict(ctx.ns)
    ns[fname] = Function(fname)
    n = sp.Symbol(var, integer=True)
    ns[var] = n
    return ns, ns[fname], n


def _exact_index(v, ns) -> int:
    """An index given in the IR, read exactly (never int() on a non-integer, never sympify)."""
    if isinstance(v, bool):
        raise ValueError(f"index {v!r} is not an integer")
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v.is_integer():
            return int(v)
        raise ValueError(f"index {v!r} is not an integer")
    e = parse_expr_str(str(v), ns)
    if isinstance(e, sp.Integer):
        return int(e)
    raise ValueError(f"index {v!r} is not an integer")


def _parse_initial(initial: dict, ns) -> dict[int, Any]:
    out = {}
    for k, v in initial.items():
        out[_exact_index(k, ns)] = parse_expr_str(str(v), ns)
    return out


def _written_conditions(src: str, ns, pins: dict | None = None) -> list[Any] | None:
    """Definedness conditions of the recurrence AS WRITTEN, with the values `pins` holds put in; None when
    it cannot be read so."""
    from ..normalize.parse import parse_as_written
    from .domain import written_definedness
    if parse_as_written(src, ns) is None:
        return None
    conds, nowhere = written_definedness(src, ns, pins)
    if nowhere:
        return [sp.false]
    return list(conds)


def _shifts(expr_or_rel, f, n) -> list[int]:
    return sorted({int(a.args[0] - n) for a in expr_or_rel.atoms(sp.core.function.AppliedUndef) if a.func == f})


def _conds_hold(conds, f, n, k, values: dict[int, Any]) -> bool | None:
    """Do the written conditions hold at n = k with the known terms? Tri-state."""
    for c in conds:
        if c is sp.false:
            return False
        try:
            cv = c.subs(n, k)
            sub = {a: values[int(a.args[0])] for a in cv.atoms(sp.core.function.AppliedUndef)
                   if a.func == f and a.args[0].is_Integer and int(a.args[0]) in values}
            cv = cv.subs(sub)
        except Exception:  # noqa: BLE001
            return None
        if cv is sp.false:
            return False
        if cv is not sp.true:
            return None
    return True


def _is_real_value(v) -> bool | None:
    if v.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        return False
    r = v.is_real
    if r is not None:
        return r
    ok, _ = num_equal(sp.im(v), 0)
    return ok


def iterate_recurrence(rel, f, n, initial: dict[int, Any], index: int, conds: list | None = None
                       ) -> tuple[Any | None, dict]:
    """Solve rel for f(n) and iterate to `index`, following every real branch of an implicit
    recurrence; the value is returned only when it is unique."""
    ev: dict[str, Any] = {}
    conds = conds or []
    fn = f(n)
    sol = sp.solve(rel, fn)
    if not sol:
        ev["error"] = "cannot_isolate_f(n)"
        return None, ev
    explicit = len(sol) == 1
    ev["branches_per_step"] = len(sol)
    shifts = sorted({s for e in sol for s in _shifts(e, f, n)}, reverse=True)
    if not shifts or max(shifts) >= 0:
        ev["error"] = "recurrence_not_explicit"
        return None, ev
    if not initial:
        ev["error"] = "no_initial_terms"
        return None, ev
    start = max(initial) + 1
    states: list[dict[int, Any]] = [dict(initial)]
    for k in range(start, index + 1):
        new_states: list[dict[int, Any]] = []
        for known in states:
            sub = {f(k + s): known.get(k + s) for s in shifts}
            if any(v is None for v in sub.values()):
                ev["error"] = f"missing_initial_term_for_{k}"
                return None, ev
            cands: list[Any] = []
            for e in sol:
                # exact simplification only: `nsimplify` snaps to the nearest "nice" number
                # (measured: 500000003/3000000000 -> 1/6), which would change the TRUTH computed
                val = sp.simplify(e.subs(n, k).subs(sub))
                if not explicit:
                    rv = _is_real_value(val)
                    if rv is None:
                        ev["error"] = f"branch_reality_undecided_at_{k}"
                        return None, ev
                    if rv is False:
                        continue
                if not any(sp.simplify(val - c) == 0 for c in cands):
                    cands.append(val)
            for val in cands:
                nxt = dict(known)
                nxt[k] = val
                h = _conds_hold(conds, f, n, k, nxt)
                if h is None:
                    ev["error"] = f"recurrence_definedness_undecided_at_{k}"
                    return None, ev
                if h is False:
                    if explicit:
                        ev["error"] = f"recurrence_undefined_as_written_at_{k}"
                        return None, ev
                    continue
                new_states.append(nxt)
        if not new_states:
            ev["error"] = f"no_real_defined_branch_at_{k}"
            return None, ev
        if len(new_states) > MAX_BRANCHES:
            ev["error"] = "too_many_branches"
            return None, ev
        states = new_states
    if index not in states[0]:
        ev["error"] = "index_before_initial_terms"
        return None, ev
    finals: list[Any] = []
    for st in states:
        v = st[index]
        if not any(sp.simplify(v - c) == 0 for c in finals):
            finals.append(v)
    ev["terms"] = {str(k): str(v) for k, v in sorted(states[0].items())[:12]}
    if len(finals) != 1:
        ev["error"] = "value_not_unique_among_real_branches"
        ev["values"] = [str(v) for v in finals[:6]]
        return None, ev
    return finals[0], ev


def _bad_indices(conds, lo) -> bool | None:
    """Is some condition (in n only) False at an integer n >= lo? None when undecided."""
    for c in conds:
        if c is sp.true:
            continue
        if c is sp.false:
            return True
        syms = c.free_symbols
        if len(syms) != 1:
            return None
        v = next(iter(syms))
        bad = sp.Eq(c.lhs, c.rhs) if isinstance(c, sp.Ne) else sp.Not(c)
        try:
            # guarded: SymPy reads a trigonometric relation on ℝ on one period (sandbox.exactsets)
            s = exact_solveset(bad, v, sp.S.Reals)
            s = sp.Intersection(s, sp.Range(lo, oo))
        except Exception:  # noqa: BLE001
            return None
        if isinstance(s, sp.ConditionSet) or s.is_empty is None:
            return None
        if s.is_empty is False:
            return True
    return False


def check_closed_form(rel, f, n, initial: dict[int, Any], closed, rec_conds=None, claim_conds=None,
                      timeout: float = 8.0) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"closed": str(closed)}
    if not initial:
        ev["reason"] = "no_initial_terms"
        return None, ev
    # initial terms
    for k, v in sorted(initial.items()):
        val = closed.subs(n, k)
        ok, _ = answers_equivalent(val, v, shape="scalar")
        if ok is False:
            ev["reason"] = f"initial_term_{k}_mismatch"
            ev["got"] = str(val)
            return False, ev
        if ok is None:
            ev["reason"] = f"initial_term_{k}_undecided"
            return None, ev
    # the relation with the claim substituted, as an EXPRESSION: replacing inside Eq(...) let SymPy
    # evaluate the equation to True/False and `.lhs` crashed on every arithmetic sequence
    diff = (rel.lhs - rel.rhs).replace(f, Lambda(n, closed))
    shifts = _shifts(rel, f, n)
    if not shifts:
        ev["reason"] = "recurrence_has_no_terms"
        return None, ev
    m, M = min(shifts), max(shifts)
    order = M - m
    L = max(initial)
    start = min(initial)
    # the recurrence determines the terms after the last given one, and it is read only where
    # every term it mentions has an index >= the first given one
    lo = max(L + 1 - M, start - m)
    # refutation first: a concrete n >= lo where the claim violates the recurrence. The two sides
    # are compared with each other (strict precision ladder, relative to their size): a difference
    # compared with 0 has no scale, and its rounding noise would refute a true identity (Binet)
    lhs_c = rel.lhs.replace(f, Lambda(n, closed))
    rhs_c = rel.rhs.replace(f, Lambda(n, closed))
    for k in range(lo, lo + N_CHECK):
        a_k, b_k = lhs_c.subs(n, k), rhs_c.subs(n, k)
        ok, _ = num_equal(a_k, b_k)
        if ok is False:
            ev["reason"] = f"recurrence_fails_at_n={k}"
            ev["residual"] = str(sp.simplify(a_k - b_k))
            return False, ev
    # proof obligations
    try:
        sol = sp.solve(rel, f(n + M))
    except Exception:  # noqa: BLE001
        sol = []
    if len(sol) != 1:
        ev["reason"] = "recurrence_not_uniquely_solvable_for_its_newest_term"
        return None, ev
    if not all(i in initial for i in range(L - order + 1, L + 1)):
        ev["reason"] = "given_terms_do_not_determine_the_sequence"
        return None, ev
    if rec_conds is None or claim_conds is None:
        ev["reason"] = "definedness_as_written_unreadable"
        return None, ev
    if claim_conds:
        b = _bad_indices(claim_conds, start)
        if b is not False:
            ev["reason"] = "claim_undefined_at_some_index" if b else "claim_definedness_undecided"
            return None, ev
    if rec_conds:
        sub_conds = []
        for c in rec_conds:
            if c is sp.false:
                ev["reason"] = "recurrence_defined_nowhere_as_written"
                return None, ev
            sub_conds.append(c.replace(f, Lambda(n, closed)))
        b = _bad_indices(sub_conds, lo)
        if b is not False:
            ev["reason"] = "recurrence_undefined_at_some_index" if b else "recurrence_definedness_undecided"
            return None, ev
    r = sb_run("mathverify.sandbox.ops:zero_test_battery", diff, timeout=timeout)
    if r.ok and r.value is True:
        ev["method"] = "symbolic_recurrence"
        return True, ev
    # a window of agreeing terms is not a proof (measured: floor(n/22) and exp(-100 n) terms)
    ev["reason"] = f"no_symbolic_proof (recurrence holds on n={lo}..{lo + N_CHECK - 1} only)"
    return None, ev


def _rsolve_worker(rel, f, n, initial):
    fn = f(n)
    try:
        r = sp.rsolve(rel, fn, {f(k): v for k, v in initial.items()})
        return r
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}: {e}"


def _rsolve_contradicts(rs, closed, n, lo) -> bool:
    """Does an independent rsolve result differ from the claim at a concrete index?"""
    if rs is None or isinstance(rs, str) or not isinstance(rs, sp.Expr):
        return False
    if rs.free_symbols - {n}:
        return False                      # arbitrary constants left: rsolve did not pin it
    for k in range(lo, lo + 6):
        ok, _ = num_equal(rs.subs(n, k), closed.subs(n, k))
        if ok is False:
            return True
    return False


def _nsum_worker(term, var, lo, hi, dps=30):
    mp.mp.dps = dps
    fn = sp.lambdify(var, term, "mpmath")
    a = -mp.inf if lo == -oo else mp.mpf(str(sp.N(lo, dps + 5)))
    b = mp.inf if hi == oo else mp.mpf(str(sp.N(hi, dps + 5)))
    return mp.nstr(mp.nsum(fn, [a, b]), dps)


def certify_series_sum(term, var, lo, hi, claimed, timeout: float = 10.0) -> tuple[bool | None, dict[str, Any]]:
    ev: dict[str, Any] = {"term": str(term), "lo": str(lo), "hi": str(hi), "claimed": str(claimed)}
    ok_lo = isinstance(lo, sp.Integer) or lo == -oo
    ok_hi = isinstance(hi, sp.Integer) or hi == oo
    if not (ok_lo and ok_hi):
        # an index bound is an integer: int() truncated 1/2 to 0 and certified the wrong sum
        ev["error"] = "non_integer_bounds"
        ev["reason"] = "non_integer_bounds"
        return None, ev
    if hi != oo and lo != -oo:
        lo_i, hi_i = int(lo), int(hi)
        if hi_i - lo_i > 200_000:
            ev["error"] = "finite_sum_too_long"
            return None, ev
        total = sp.Add(*[term.subs(var, k) for k in range(lo_i, hi_i + 1)]) if hi_i - lo_i < 2000 else \
            sp.summation(term, (var, lo_i, hi_i))
        # exact simplification only: `nsimplify` snaps to the nearest "nice" number (measured:
        # 500000003/3000000000 -> 1/6), which would silently change the TRUTH it computes
        total = sp.simplify(total) if hi_i - lo_i < 2000 else total
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
        # nsum refutes only a series it sums reliably: terms that never vanish and keep one sign, and
        # a value that stands at a higher precision too. Σ sin(πk/2)/k came out 263/315 = 0.8349 at
        # every precision (the zero terms end its extrapolation early), and π/4 was refuted (audit
        # of 29 Sep 2026).
        rt = sb_run("mathverify.certify.series:_one_signed_terms", term, var, lo, timeout=timeout)
        one_signed = bool(rt.ok and rt.value is True)
        rn2 = sb_run("mathverify.certify.series:_nsum_worker", term, var, lo, hi, 50, timeout=timeout * 2)
        num2 = sp.Float(rn2.value, 50) if rn2.ok else None
        converged = num2 is not None and num_equal(num_val, num2, rel_tol=1e-20)[0] is True
        ev["numeric_reliable"] = one_signed and converged
        if ok is False and one_signed and converged:
            return False, ev
        ev["reason"] = "numeric_only_no_symbolic_confirmation"
        return None, ev
    ev["reason"] = "summation_failed"
    return None, ev


def _one_signed_terms(term, var, lo, n=200) -> bool:
    """Are the first `n` terms nonzero and of one sign (the series nsum sums reliably)?"""
    if lo == -oo:
        return False
    f = sp.lambdify(var, term, "mpmath")
    sign = 0
    with mp.workdps(30):
        for k in range(int(lo), int(lo) + n):
            v = f(mp.mpf(k))
            if isinstance(v, mp.mpc) or not mp.isfinite(v) or abs(v) < mp.mpf(10) ** -25:
                return False
            s = 1 if v > 0 else -1
            if sign and s != sign:
                return False
            sign = s
    return True


def _summation_worker(term, var, lo, hi):
    try:
        return sp.summation(term, (var, lo, hi))
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}: {e}"


MAX_STEP_INDEX = 200                     # steps name early terms; a far index is not iterated


def sequence_term_values(ir, ctx: Ctx, indices) -> tuple[str | None, dict[int, Any]]:
    """The task's sequence name and its exact terms at the given integer indices (only the ones
    the recurrence determines uniquely), for checking a step such as `a(3) = 6`. The step layer
    skipped every such step as an undeclared name, so a wrong intermediate term under a right
    final answer was certified (audit of 25 Sep 2026). Same iteration as the certificate below."""
    p = ir.task.params or {}
    if ir.task.kind not in ("recurrence_term", "closed_form") or not isinstance(p.get("recurrence"), str):
        return None, {}
    fname, var = p.get("name", "a"), p.get("var", "n")
    try:
        ns, f, n = _rec_ns(ctx, fname, var)
        rel = parse_relation(p["recurrence"], ns)
        initial = _parse_initial(p.get("initial", {}), ns)
    except Exception:  # noqa: BLE001 - the certificate reports the parse error itself
        return fname, {}
    if not isinstance(rel, sp.Equality) or not initial:
        return fname, {}
    rec_conds = _written_conditions(p["recurrence"], ns)
    if rec_conds is None:
        return fname, {}
    sh = _shifts(rel, f, n)
    if sh and max(sh) != 0:
        M = max(sh)
        rel = rel.subs(n, n - M)
        rec_conds = [c.subs(n, n - M) for c in rec_conds]
    out: dict[int, Any] = {}
    for k in sorted(set(indices)):
        if k in initial:
            out[k] = initial[k]
            continue
        if k < min(initial) or k > MAX_STEP_INDEX:
            continue
        r = sb_run("mathverify.certify.series:_iterate_worker", rel, f, n, initial, k, rec_conds,
                   timeout=ctx.timeout)
        if r.ok and r.value[0] is not None:
            out[k] = r.value[0]
    return fname, out


def verify(ir, solution, ctx: Ctx):
    kind = ir.task.kind
    if kind not in ("recurrence_term", "closed_form", "series_sum"):
        return unknown(LAYER, "not_applicable")
    with Timer() as t:
        p = ir.task.params
        ev: dict[str, Any] = {}
        if kind in ("recurrence_term", "closed_form"):
            fname, var = p.get("name", "a"), p.get("var", "n")
            # a symbol a given or a declared constraint fixes is read as its value in the recurrence, the
            # initial values, their written conditions and the claim (`Ctx.task_pins`): with c = 0 the claim
            # c**(n - 1) of a(n) = c*a(n - 1), a(1) = 1, is 0**0 at n = 1 and was certified, and with c = 2
            # 2**(n - 1) was left undecided (attack on d4e, YO-1)
            pins = {s_: v for s_, v in ctx.task_pins(ctx.sym(var)).items() if s_.name != fname}
            try:
                ns, f, n = _rec_ns(ctx, fname, var)
                rel = substitute_free(parse_relation(p["recurrence"], ns), pins)
                initial = {k: substitute_free(v, pins) for k, v in _parse_initial(p.get("initial", {}), ns).items()}
            except (ParseError, Exception) as e:  # noqa: BLE001
                return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
            if not isinstance(rel, sp.Equality):
                return unknown(LAYER, "recurrence_not_an_equation")
            rec_conds = _written_conditions(p["recurrence"], ns, pins)
            if kind == "recurrence_term":
                if rec_conds is None:
                    return unknown(LAYER, "recurrence_unreadable_as_written", flags=["written_domain"])
                claimed, err = parse_or_unknown(LAYER, ctx.claimed, solution)
                if err:
                    return err
                claimed, err = parse_or_unknown(LAYER, ctx.with_pins, claimed, pins)
                if err:
                    return err
                try:
                    index = _exact_index(p["index"], ns)
                except Exception as e:  # noqa: BLE001
                    return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
                # forward form `a(n+1) = 2*a(n) + 1`: re-index so that the newest term is a(n)
                sh = _shifts(rel, f, n)
                if sh and max(sh) != 0:
                    M = max(sh)
                    rel = rel.subs(n, n - M)
                    rec_conds = [c.subs(n, n - M) for c in rec_conds]
                r = sb_run("mathverify.certify.series:_iterate_worker", rel, f, n, initial, index, rec_conds,
                           timeout=ctx.timeout)
                if not r.ok:
                    return unknown(LAYER, r.error or "iteration_failed", 0, flags=r.flags)
                val, iev = r.value
                ev.update(iev)
                if val is None:
                    flags = ["written_domain"] if "undefined_as_written" in str(iev.get("error")) else []
                    return unknown(LAYER, iev.get("error", "iteration_failed"), 0, ev, flags=flags)
                ev["value"] = str(val)
                ok, cev = answers_equivalent(claimed, val, shape="scalar")
                ev["compare"] = cev
                conf = 0.99
            else:
                from ..normalize.parse import parse_expr_str as _pe
                claim_ns = dict(ctx.claim_ns(solution), **{n.name: n})
                try:
                    # the index variable only — the sequence symbol itself would let a claim
                    # restate the recurrence (`a(n-1) + 3`) instead of giving a closed form
                    closed = substitute_free(_pe(str(solution.claimed_answer.payload), claim_ns), pins)
                except Exception as e:  # noqa: BLE001
                    return unknown(LAYER, f"parse_error: {e}", flags=["parse_error"])
                claim_conds: list | None = []
                payload = solution.claimed_answer.payload
                if isinstance(payload, str):
                    claim_conds = _written_conditions(payload, claim_ns, pins)
                ok, cev = check_closed_form(rel, f, n, initial, closed, rec_conds, claim_conds,
                                            timeout=ctx.timeout)
                ev.update(cev)
                rr = sb_run("mathverify.certify.series:_rsolve_worker", rel, f, n, initial, timeout=ctx.timeout)
                ev["rsolve"] = str(rr.value) if rr.ok else rr.error
                if ok is True and rr.ok:
                    shifts = _shifts(rel, f, n)
                    lo = max(max(initial) + 1 - max(shifts), min(initial) - min(shifts))
                    if _rsolve_contradicts(rr.value, closed, n, lo):
                        ok = None
                        ev["reason"] = "rsolve_contradicts_the_proved_claim"
                        ev["flags"] = ["contradiction"]
                conf = 0.99
        else:
            var_name = p.get("var", "k")
            # the summation index is an integer and nothing more (see _rec_ns): a declared
            # positive k made `k/k` defined at k = 0 and the guard below certified Σ_{-1}^{1} k/k = 3
            ns2 = dict(ctx.ns)
            var = sp.Symbol(var_name, integer=True)
            ns2[var_name] = var
            # a symbol a given or a declared constraint fixes is read as its value in the term, the bounds,
            # the term's written conditions and the claim (`Ctx.task_pins`): with a = 2 the sum 3 of
            # (k - a)/(k - a) over k = 1..3 (0/0 at k = 2) was certified, and the right 12 of a*k refuted
            # against 6*a (attack on d4e, YO-1, R9)
            pins = ctx.task_pins(ctx.sym(var_name))
            term, err = parse_or_unknown(LAYER, parse_expr_str, p["term"], ns2)
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
            (term, lo, hi, claimed), err = parse_or_unknown(
                LAYER, lambda es: tuple(ctx.with_pins(e, pins) for e in es), (term, lo, hi, claimed))
            if err:
                return err
            # an upper bound below lo - 1 is SymPy's Karr convention (Σ_{k=1}^{-2} k = 1) or an empty
            # sum (0, certified 30 Sep 2026); the curriculum has neither, and the same sum written as
            # Sum(k, (k, 1, -2)) is not read (normalize.parse._refuse_reversed_ranges)
            if (hi - lo + 1).is_extended_negative is True:
                return unknown(LAYER, "reversed_bounds", t.ms, {"lo": str(lo), "hi": str(hi)},
                               flags=["reversed_bounds"])
            # every term as written must exist: k/k parses to 1, so Σ_{k=-1}^{1} k/k was "3"
            from .domain import written_undefined_in
            if (lo.is_Integer or lo == -oo) and (hi.is_Integer or hi == oo):
                if lo.is_Integer and hi.is_Integer:
                    idx = sp.Range(int(lo), int(hi) + 1)
                elif lo.is_Integer:
                    idx = sp.Range(int(lo), oo)
                elif hi.is_Integer:
                    idx = sp.Range(-oo, int(hi) + 1)
                else:
                    idx = sp.S.Integers
                und = written_undefined_in(p["term"], ns2, var, idx, pins)
                if und is True:
                    return unknown(LAYER, "term_undefined_in_range_as_written", t.ms, {"term": p["term"]},
                                   flags=["written_domain"])
            ok, cev = certify_series_sum(term, var, lo, hi, claimed, timeout=ctx.timeout)
            ev.update(cev)
            conf = 0.99 if ev.get("method") in ("exact_finite", "symbolic+numeric") else 0.95
    if ok is True:
        return result(LAYER, "pass", conf, True, ev, t.ms, primary=True)
    if ok is False:
        return result(LAYER, "fail", 0.99, True, ev, t.ms, primary=True)
    return unknown(LAYER, ev.get("reason", "undecided"), t.ms, ev, flags=ev.pop("flags", []))


def _iterate_worker(rel, f, n, initial, index, conds=None):
    return iterate_recurrence(rel, f, n, initial, index, conds)
