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

import sympy as sp

from .certify import MODULES
from .certify.base import make_ctx, result, unknown, Timer
from .equiv import answers_equivalent, exact_integer
from .fuse import fuse
from .ir import ProblemIR, LeakageError
from .router import route, DEFERRED_KINDS
from .solution import Solution
from .steps import check_steps
from .types import LayerResult, VerificationResult
from .versions import collect_versions

__all__ = ["verify", "VerificationResult", "SCOPE_FLAGS", "scope_note"]

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
            ci, oi = exact_integer(cv), exact_integer(ov)   # never int(): it truncates 3.5 to 3
            ok = None if oi is None else (ci is not None and ci == oi)
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
        # A payload the deterministic extractor reconstructed from prose is advisory: the
        # solver may never have written it that way. A reconstruction mistake must therefore
        # be able to abstain but never to refute, or path (b) would start manufacturing
        # INCORRECT verdicts out of its own parsing.
        if ca.payload_source == "recovered_text":
            ev["reason"] = "recovered_claim_does_not_match_chosen_option"
            return unknown("mc.consistency", ev["reason"], t.ms, ev,
                           flags=["recovered_answer_mismatch"])
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


_MATHY = re.compile(r"[0-9+\-*/^=<>≤≥≠∞√πα-ωΑ-Ω]|\\[A-Za-z]+")


_TAGLIKE = re.compile(r"^<[^<>]*>(?:[^<>]*</[^<>]*>)?$")


def _is_prose_token(tok: str) -> bool:
    """A token that can be dropped while cleaning: no digits, no operators, no LaTeX macro —
    i.e. words and punctuation, not mathematics. Markup such as `<verdict>CORRECT</verdict>`
    counts as prose even though `<` and `>` are relations, because a relation never appears as
    a token that both opens and closes an angle bracket."""
    t = tok.strip()
    if not t:
        return True
    if _TAGLIKE.match(t) and not any(ch.isdigit() for ch in t):
        return True
    return not _MATHY.search(t)


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
    # LaTeX math delimiters around the whole payload
    for a, b in (("$$", "$$"), ("$", "$"), ("\\(", "\\)"), ("\\[", "\\]")):
        if t.startswith(a) and t.endswith(b) and len(t) > len(a) + len(b):
            t = t[len(a):-len(b)].strip()
            cands.append(t)
            break
    if "{}" in t:                       # empty braces carry no mathematics
        t = t.replace("{}", "").strip()
        cands.append(t)
    # Balance braces by removing them from whichever side carries the EXCESS, and offer that
    # first. Stripping blindly from the end turned the set "{{pi/6, 5*pi/6}" into
    # "pi/6, 5*pi/6" — both braces gone, so the claim stopped being a set at all and a correct
    # answer was rejected (measured: 7 items on the junk_prefix attack).
    bal = t
    while bal.count("{") > bal.count("}") and bal.startswith("{"):
        bal = bal[1:].lstrip()
        cands.append(bal)
    while bal.count("}") > bal.count("{") and bal.endswith("}"):
        bal = bal[:-1].rstrip()
        cands.append(bal)
    # then the blind strip, as a fallback for junk on the side that is not in excess
    while t and t[-1] in "}{" and t.count("{") != t.count("}"):
        t = t[:-1].rstrip()
    while t and t[0] in "{}" and t.count("{") != t.count("}"):
        t = t[1:].lstrip()
    cands.append(t)
    # Drop trailing PROSE tokens one at a time — never a token that carries mathematics.
    # Dropping "+ 1" would silently rewrite the claim into a different one and hand the attacker
    # a verdict for an answer the solver never gave (measured on the value_bump attack).
    toks = t.split()
    for k in range(len(toks) - 1, 0, -1):
        if not _is_prose_token(toks[k]):
            break
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


def _claim_not_a_value(ir: ProblemIR, solution: Solution, ctx) -> LayerResult | None:
    from .normalize.parse import ClaimNotAValue, check_claim_is_value
    ca = solution.claimed_answer
    if ca.payload_source == "option_letter" or not isinstance(ca.payload, str):
        return None                         # the option's own text is the problem's, not a claim
    try:
        check_claim_is_value(ca.payload, [f.name for f in ir.functions])
    except ClaimNotAValue as e:
        return unknown("intake.claim", str(e)[:200], flags=["claim_is_not_a_value"])
    if ir.task.kind == "evaluate":
        target = (ir.task.params or {}).get("expr") or ir.unknown_of_interest
        if target and _same_structure(str(ca.payload), str(target), ctx):
            return unknown("intake.claim", f"claimed answer {ca.payload!r} restates the question",
                           flags=["claim_is_not_a_value"])
    return None


def _same_structure(a: str, b: str, ctx) -> bool:
    """Same UNEVALUATED expression tree — `gcd(84, 120)` vs `gcd(84,120)`, but not `12`."""
    try:
        from .formal.statement import parse_structural
        ta, tb = parse_structural(a, ctx.ns), parse_structural(b, ctx.ns)
    except Exception:  # noqa: BLE001
        return False
    if not getattr(tb, "args", None):
        return False                        # a bare number or symbol target cannot be restated
    return sp.srepr(ta) == sp.srepr(tb)


SCOPE_FLAGS = ("answer_level_only", "steps_not_checked", "answer_from_option_letter")


def scope_note(flags: list[str], verdict: str) -> str:
    """One line saying what a positive verdict actually covers.

    A CORRECT verdict on a solution with no checkable step is an ANSWER-level statement, not a
    solution-level one. The flag alone is machine-readable; this is the human half, so nobody
    reads 'CORRECT' off a trace and believes the reasoning was verified."""
    if verdict != "CORRECT":
        return ""
    parts = []
    if "steps_not_checked" in flags:
        parts.append("adım denetimi kapalıydı (run_steps=False)")
    elif "answer_level_only" in flags:
        parts.append("çözümde denetlenebilir adım yok")
    if "answer_from_option_letter" in flags:
        parts.append("iddia yalnız şık harfinden okundu")
    if not parts:
        return ""
    return ("\nKAPSAM: bu CORRECT yalnız CEVAP düzeyindedir, çözümün geçerliliği hakkında değil — "
            + "; ".join(parts) + ".")


def verify(problem_ir: ProblemIR | dict, solution: Solution | dict, seed: int = 0,
           timeout: float = 8.0, run_steps: bool = True) -> VerificationResult:
    """Deterministic verification: certificates + step refuter + fusion."""
    t_start = time.perf_counter()
    layers, clean_flags = verify_layers(problem_ir, solution, seed=seed, timeout=timeout, run_steps=run_steps)
    return fuse_layers(layers, extra_flags=clean_flags, started=t_start)


def fuse_layers(layers: list[LayerResult], extra_flags: list[str] | None = None, started: float | None = None,
                versions_extra: dict[str, str] | None = None) -> VerificationResult:
    """Fuse any list of layers (deterministic ones plus, in F3+, LLM-derived soft layers)."""
    fused = fuse(layers)
    total_ms = (time.perf_counter() - started) * 1000 if started else 0.0
    all_flags = list(fused["flags"]) + [f for f in (extra_flags or []) if f not in fused["flags"]]
    trace = fused["trace"] + scope_note(all_flags, fused["verdict"]) + f"\nToplam süre: {total_ms:.0f} ms"
    versions = _versions()
    if versions_extra:
        versions.update(versions_extra)
    return VerificationResult(verdict=fused["verdict"], confidence=fused["confidence"],
                              first_bad_step=fused["first_bad_step"], layers=layers,
                              decision_trace=trace, versions=versions, flags=all_flags)


def verify_layers(problem_ir: ProblemIR | dict, solution: Solution | dict, seed: int = 0,
                  timeout: float = 8.0, run_steps: bool = True) -> tuple[list[LayerResult], list[str]]:
    """Run the deterministic layers and return (layers, flags) without fusing."""
    if isinstance(problem_ir, dict):
        problem_ir = ProblemIR.from_dict(problem_ir)
    if isinstance(solution, dict):
        solution = Solution.from_dict(solution)
    layers: list[LayerResult] = []

    try:
        ctx = make_ctx(problem_ir, seed=seed, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        layers.append(unknown("ir.parse", f"ir_namespace_error: {type(e).__name__}: {e}", flags=["parse_error"]))
        return layers, []

    # fill payload from option letter if the solver only gave a letter
    ca = solution.claimed_answer
    scope_flags: list[str] = []
    if ca.option and ca.payload in (None, "") and problem_ir.options and ca.option in problem_ir.options:
        ca.payload = problem_ir.options[ca.option]
        # The certificate is now about to verify the OPTION's own value, so the only thing
        # being checked is the letter the solver picked — a 1-in-5 guess carries as much
        # evidence as a worked solution. That is legitimate answer-level verification, but it
        # is not what CORRECT means at solution level (DECISIONS §2), so it is disclosed.
        scope_flags.append("answer_from_option_letter")
        ca.payload_source = "option_letter"
        if problem_ir.answer_shape in ("set", "interval"):
            ca.kind = problem_ir.answer_shape
        elif problem_ir.answer_shape == "count":
            n_opt = exact_integer(ca.payload)
            if n_opt is not None:
                ca.kind, ca.payload = "count", n_opt
            else:
                ca.kind = "value"

    # DECISIONS §2 defines CORRECT as "the claimed answer is right AND no step was refuted".
    # With no checkable step the second conjunct is vacuously true, so a CORRECT verdict here
    # says nothing about the reasoning. The verdict is kept (abstaining would destroy path
    # (b), whose answer-level coverage is a product feature) but the scope is made explicit,
    # in a machine-readable flag, so a caller can demand solution-level evidence.
    if not run_steps:
        scope_flags.append("steps_not_checked")
    elif not any(st.kind in ("eq", "compute") and st.claim for st in solution.steps):
        scope_flags.append("answer_level_only")

    clean_flags = _sanitize_payload(solution, ctx) + scope_flags

    # A claimed answer must be a VALUE. A computation (`integrate(…)`, `limit(…)`) or the
    # question written back (`f(g(2))`, `gcd(84, 120)` for "evaluate gcd(84, 120)") would make
    # the certificates compute the answer themselves — every one of those was certified CORRECT
    # before this check. It abstains, it does not refute: no answer was given, not a wrong one.
    not_a_value = _claim_not_a_value(problem_ir, solution, ctx)
    if not_a_value is not None:
        layers.append(not_a_value)

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

    return layers, clean_flags


def cache_key(problem_ir: dict, solution: dict) -> str:
    """(question_hash, solution_hash) -> decision cache key (handoff §12)."""
    h = hashlib.sha256()
    h.update(json.dumps(problem_ir, sort_keys=True, ensure_ascii=False).encode())
    h.update(b"|")
    h.update(json.dumps(solution, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()
