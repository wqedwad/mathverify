"""Top-level entry: verify(problem_ir, solution) -> VerificationResult.

Pipeline (Phase 1): L0/L1 are the structured inputs themselves; L3 certificates are
selected by the router; L6 deterministic step refutation runs on the structured steps;
L8 rule fusion produces the three-valued verdict. No answer key is ever accepted here
(ProblemIR.from_dict / Solution.from_dict raise LeakageError on key-like fields).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

import sympy as sp

from .certify import MODULES
from .certify.base import make_ctx, result, unknown, Timer
from .equiv import answers_equivalent
from .fuse import fuse
from .ir import ProblemIR, LeakageError
from .router import route, DEFERRED_KINDS
from .solution import Solution
from .steps import check_steps
from .types import LayerResult, VerificationResult
from .versions import collect_versions

__all__ = ["verify", "VerificationResult"]

_VERSIONS: dict[str, str] | None = None


def _versions() -> dict[str, str]:
    global _VERSIONS
    if _VERSIONS is None:
        _VERSIONS = collect_versions()
    return dict(_VERSIONS)


def _mc_consistency(ir: ProblemIR, solution: Solution, ctx) -> LayerResult | None:
    """If the solver picked an option letter, the letter's value must match the claimed value."""
    ca = solution.claimed_answer
    if not ir.options or not ca.option:
        return None
    with Timer() as t:
        if ca.option not in ir.options:
            return result("mc.consistency", "fail", 0.99, True,
                          {"reason": "option_letter_not_in_question", "option": ca.option}, t.ms)
        opt_text = str(ir.options[ca.option]).strip().lower()
        if ca.kind == "dne":
            ok = bool(re.search(r"yok|dne|tanımsız|mevcut değil|does not exist", opt_text))
            ev = {"option": ca.option, "option_text": opt_text, "claimed": "DNE"}
            if ok:
                return result("mc.consistency", "pass", 0.99, True, ev, t.ms, primary=False)
            ev["reason"] = "claimed_DNE_but_option_is_a_value"
            return result("mc.consistency", "fail", 0.99, True, ev, t.ms, primary=False)
        if re.search(r"yok|dne|tanımsız|mevcut değil|does not exist", opt_text):
            ev = {"option": ca.option, "option_text": opt_text, "claimed": str(ca.payload)}
            ev["reason"] = "option_says_DNE_but_a_value_was_claimed"
            return result("mc.consistency", "fail", 0.99, True, ev, t.ms, primary=False)
        if ca.payload in (None, ""):
            return unknown("mc.consistency", "no_payload_to_compare", t.ms)
        try:
            ov = ctx.option_value(ca.option)
            cv = ctx.claimed(solution)
        except Exception as e:  # noqa: BLE001
            return unknown("mc.consistency", f"option_parse_error: {e}", t.ms)
        shape = "set" if isinstance(cv, sp.Set) else ("count" if ca.kind == "count" else "scalar")
        from .certify.linalg import _as_matrix, matrices_equal
        if shape == "count":
            ok = int(cv) == int(ov)
            ev = {"option": ca.option, "option_value": str(ov), "claimed": str(cv)}
        elif _as_matrix(cv) is not None or _as_matrix(ov) is not None:
            mc_, mo_ = _as_matrix(cv), _as_matrix(ov)
            ok = False if (mc_ is None) != (mo_ is None) else matrices_equal(mc_, mo_)[0]
            ev = {"option": ca.option, "option_value": str(ov), "claimed": str(cv), "compare": "matrix_entrywise"}
        elif isinstance(cv, sp.Equality) or isinstance(ov, sp.Equality):
            ok, cev = answers_equivalent(cv, ov, shape="equation", var=next(iter(ctx.syms()), None))
            ev = {"option": ca.option, "option_value": str(ov), "claimed": str(cv), "compare": cev}
        else:
            ok, cev = answers_equivalent(cv, ov, shape=shape)
            ev = {"option": ca.option, "option_value": str(ov), "claimed": str(cv), "compare": cev}
    if ok is True:
        return result("mc.consistency", "pass", 0.99, True, ev, t.ms, primary=False)
    if ok is False:
        ev["reason"] = "claimed_value_does_not_match_chosen_option"
        return result("mc.consistency", "fail", 0.99, True, ev, t.ms, primary=False)
    return unknown("mc.consistency", "undecided", t.ms, ev)


def _sanity(ir: ProblemIR, solution: Solution, ctx) -> LayerResult | None:
    if not ir.sanity:
        return None
    with Timer() as t:
        try:
            cv = ctx.claimed(solution)
        except Exception:
            return None
        if isinstance(cv, sp.Set) or cv is None:
            return None
        ns = dict(ctx.ns)
        ns["ans"] = cv
        from .normalize.parse import parse_relation
        from .certify.domain import relation_holds_at
        checks = {}
        bad = None
        for s_ in ir.sanity:
            try:
                rel = parse_relation(s_, ns)
            except Exception:
                checks[s_] = "unparsed"
                continue
            if rel is sp.true:
                checks[s_] = True
                continue
            if rel is sp.false:
                checks[s_] = False
                bad = s_
                continue
            h = relation_holds_at(rel, sp.Symbol("_d"), 0) if not rel.free_symbols else None
            checks[s_] = h
            if h is False:
                bad = s_
    ev = {"checks": checks, "claimed": str(cv)}
    if bad is not None:
        ev["reason"] = f"sanity_violated: {bad}"
        return result("sanity", "fail", 0.95, True, ev, t.ms)
    return unknown("sanity", "all_sanity_checks_hold_or_unparsed", t.ms, ev)


_ZERO_WIDTH = re.compile(r"[​‌‍﻿⁠]")
_BOXED = re.compile(r"^\\boxed\{(.*)\}$")


def _sanitize_payload(solution: Solution, ctx) -> list[str]:
    """Adversarial robustness (§9): junk prefixes/suffixes around the claimed answer must not
    flip a verdict. Cleaning is conservative and only attempted when the raw payload does
    not parse: zero-width characters, \\boxed{}, unbalanced braces and trailing prose are
    stripped until the remaining text parses. The mathematical token is what gets verified,
    so a wrong answer stays wrong ("11 bu çözüm doğrudur" -> 11)."""
    ca = solution.claimed_answer
    flags: list[str] = []
    if ca.payload is None or not isinstance(ca.payload, str):
        return flags
    try:
        ctx.claimed(solution)
        return flags
    except Exception:  # noqa: BLE001
        pass
    s = _ZERO_WIDTH.sub("", ca.payload).strip()
    m = _BOXED.match(s)
    if m:
        s = m.group(1).strip()
    cands = [s]
    t = s
    # strip unbalanced braces at the ends
    while t and t[-1] in "}{" and t.count("{") != t.count("}"):
        t = t[:-1].rstrip()
    while t and t[0] in "{}" and t.count("{") != t.count("}"):
        t = t[1:].lstrip()
    cands.append(t)
    # drop trailing whitespace-separated tokens (prose) one at a time
    toks = t.split()
    for k in range(len(toks) - 1, 0, -1):
        cands.append(" ".join(toks[:k]))
    original = ca.payload
    for c in cands:
        if not c or c == original:
            continue
        ca.payload = c
        try:
            ctx.claimed(solution)
            flags.append("payload_cleaned")
            return flags
        except Exception:  # noqa: BLE001
            continue
    ca.payload = original
    return flags


def verify(problem_ir: ProblemIR | dict, solution: Solution | dict, seed: int = 0,
           timeout: float = 8.0, run_steps: bool = True) -> VerificationResult:
    t_start = time.perf_counter()
    if isinstance(problem_ir, dict):
        problem_ir = ProblemIR.from_dict(problem_ir)
    if isinstance(solution, dict):
        solution = Solution.from_dict(solution)
    layers: list[LayerResult] = []
    flags: list[str] = []

    try:
        ctx = make_ctx(problem_ir, seed=seed, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        layers.append(unknown("ir.parse", f"ir_namespace_error: {type(e).__name__}: {e}", flags=["parse_error"]))
        fused = fuse(layers)
        return VerificationResult(verdict="UNKNOWN", confidence=0.0, first_bad_step=None, layers=layers,
                                  decision_trace=fused["trace"], versions=_versions(), flags=fused["flags"])

    # fill payload from option letter if the solver only gave a letter
    ca = solution.claimed_answer
    if ca.option and ca.payload in (None, "") and problem_ir.options and ca.option in problem_ir.options:
        ca.payload = problem_ir.options[ca.option]
        if problem_ir.answer_shape in ("set", "interval"):
            ca.kind = problem_ir.answer_shape
        elif problem_ir.answer_shape == "count":
            ca.kind = "count"
            try:
                ca.payload = int(sp.sympify(ca.payload))
            except Exception:
                ca.kind = "value"

    clean_flags = _sanitize_payload(solution, ctx)

    mc = _mc_consistency(problem_ir, solution, ctx)
    if mc is not None:
        layers.append(mc)
    sn = _sanity(problem_ir, solution, ctx)
    if sn is not None:
        layers.append(sn)

    modules = route(problem_ir)
    if not modules:
        why = DEFERRED_KINDS.get(problem_ir.task.kind, "unknown task kind")
        layers.append(unknown("router", f"unsupported_task_kind:{problem_ir.task.kind} ({why})",
                              flags=["unsupported_task_kind"]))
    for name in modules:
        mod = MODULES[name]
        try:
            lr = mod.verify(problem_ir, solution, ctx)
        except LeakageError:
            raise
        except Exception as e:  # noqa: BLE001
            lr = unknown(name, f"layer_exception: {type(e).__name__}: {str(e)[:200]}", flags=["layer_exception"])
        layers.append(lr)

    if run_steps and solution.steps:
        try:
            layers.append(check_steps(problem_ir, solution, ctx))
        except Exception as e:  # noqa: BLE001
            layers.append(unknown("steps.refute", f"layer_exception: {type(e).__name__}: {str(e)[:200]}",
                                  flags=["layer_exception"]))

    fused = fuse(layers)
    total_ms = (time.perf_counter() - t_start) * 1000
    trace = fused["trace"] + f"\nToplam süre: {total_ms:.0f} ms"
    all_flags = list(fused["flags"]) + [f for f in clean_flags if f not in fused["flags"]]
    return VerificationResult(verdict=fused["verdict"], confidence=fused["confidence"],
                              first_bad_step=fused["first_bad_step"], layers=layers,
                              decision_trace=trace, versions=_versions(), flags=all_flags)


def cache_key(problem_ir: dict, solution: dict) -> str:
    """(question_hash, solution_hash) -> decision cache key (handoff §12)."""
    h = hashlib.sha256()
    h.update(json.dumps(problem_ir, sort_keys=True, ensure_ascii=False).encode())
    h.update(b"|")
    h.update(json.dumps(solution, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()
