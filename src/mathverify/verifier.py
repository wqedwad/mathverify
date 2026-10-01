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
from .ir import MalformedIR, ProblemIR, LeakageError
from .router import route, DEFERRED_KINDS
from .solution import MalformedSolution, Solution
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


_NO_SOLUTION = re.compile(r"çözüm(\s*kümesi)?\s*(yok|boş)|kök\s*yok|boş\s*küme|no\s*(real\s*)?solution|∅|emptyset",
                          re.IGNORECASE)


def _option_and_claim(ir: ProblemIR, solution: Solution, ctx):
    """The chosen option's value and the claim, in the same units. For an angle target of
    synthetic_geometry the certificate measures in degrees, so a degree mark is the unit of the
    number (`70°` is 70), not a conversion to radians: payload "70" with option "70°" was refuted
    while the certificate proved 70 (audit of 25 Sep 2026)."""
    ca = solution.claimed_answer
    target = str((ir.task.params or {}).get("target", ""))
    if ir.task.kind == "synthetic_geometry" and "angle(" in target:
        from .certify.geometry_numeric import has_degree_mark, strip_degree_marks
        from .normalize.parse import parse_expr_str
        opt = str(ir.options[ca.option])
        ov = parse_expr_str(strip_degree_marks(opt), ctx.ns) if has_degree_mark(opt) else ctx.option_value(ca.option)
        pay = ca.payload
        if isinstance(pay, str) and has_degree_mark(pay):
            cv = parse_expr_str(strip_degree_marks(pay), ctx.claim_ns(solution))
        else:
            cv = ctx.claimed(solution)
        return ov, cv
    return ctx.option_value(ca.option), ctx.claimed(solution)


def _mc_consistency(ir: ProblemIR, solution: Solution, ctx) -> LayerResult | None:
    """If the solver picked an option letter, the letter's value must match the claimed value."""
    ca = solution.claimed_answer
    if not ir.options or not ca.option:
        return None
    with Timer() as t:
        if ca.option not in ir.options:
            if not re.fullmatch(r"[A-Z]", str(ca.option)):
                # not a letter at all ("B, C", prose): what the solver chose is unknown, so the
                # payload's certificate cannot stand for the solution — abstain, never refute
                return unknown("mc.consistency", f"option_unreadable: {ca.option!r}", t.ms,
                               flags=["option_unreadable"])
            return result("mc.consistency", "fail", 0.99, True,
                          {"reason": "option_letter_not_in_question", "option": ca.option}, t.ms)
        opt_text = str(ir.options[ca.option]).strip().lower()
        if _NO_SOLUTION.search(opt_text):
            # "Çözüm yok" is the empty solution set, not "does not exist": the generic "yok" test
            # below refuted a correct empty-set answer that chose it (audit of 25 Sep 2026)
            ev = {"option": ca.option, "option_text": opt_text, "claimed": str(ca.payload)}
            try:
                cv = ctx.claimed(solution) if ca.kind != "none" else sp.S.EmptySet
            except Exception as e:  # noqa: BLE001
                return unknown("mc.consistency", f"claim_parse_error: {e}", t.ms, ev)
            if cv == sp.S.EmptySet or ca.kind == "none":
                return result("mc.consistency", "pass", 0.99, True, ev, t.ms, primary=False)
            ev["reason"] = "option_says_no_solution_but_a_solution_was_claimed"
            return result("mc.consistency", "fail", 0.99, True, ev, t.ms, primary=False)
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
            ov, cv = _option_and_claim(ir, solution, ctx)
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


_NEGATION = re.compile(
    r"(?<!\w)(değil|degil|olamaz|olmaz|yanlış|yanlis|hariç|haric|dışında|disinda|hayır|hayir|yok|"
    r"belki|muhtemelen|sanırım|sanirim|galiba|not|no|never|cannot|can't|isn't|wrong|except|maybe|"
    r"perhaps|probably)(?!\w)|\?", re.IGNORECASE)


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
        # prose that negates or doubts the value ("5 değil", "5 olamaz", "belki 5") is not junk:
        # dropping it turned "not 5" into 5 and certified it (audit of 25 Sep 2026). Abstain.
        if _NEGATION.search(" ".join(toks[k:])):
            flags.append("payload_negated")
            return flags
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


def _normalize_set_notation(ir: ProblemIR, solution: Solution, ctx) -> list[str]:
    """Notation only, never values (principle 3): for a set/interval answer, "x ∈ S" is S, a bare
    list "2, 3" is {2, 3}, and a condition on the task variable alone ("x >= 3") is its exact
    solution set. Each was refuted as written (audit of 25 Sep 2026). A bare "2,3" (no space) is
    also the Turkish decimal 2.3 and is left alone: the decimal-comma check abstains on it."""
    ca = solution.claimed_answer
    # the claim's own kind says it is a set; the IR's answer_shape is often left at its default
    set_task = ir.answer_shape in ("set", "interval") or ir.task.kind in ("solve_equation", "solve_inequality",
                                                                          "domain_of")
    if not set_task or ca.kind not in ("set", "interval", "condition") \
            or not isinstance(ca.payload, str) or ca.payload_source == "option_letter":
        return []
    names = {v.name for v in ir.vars}
    tvar = (ir.task.params or {}).get("var")
    if isinstance(tvar, str):
        names.add(tvar)
    text = ca.payload.strip()
    flags: list[str] = []
    m = re.match(r"^([A-Za-z]\w*)\s*(?:∈|\bin\b)\s*(.+)$", text)
    if m and m.group(1) in names:
        text = m.group(2).strip()
        flags.append("payload_notation_normalized")
    if (ca.kind == "set" or ir.answer_shape == "set") and ca.kind != "interval" and "," in text \
            and not re.search(r"[{}\[\]()]", text) and not re.search(r"\d,\d", text):
        text = "{" + text + "}"
        flags.append("payload_notation_normalized")
    if isinstance(tvar, str) and re.search(r"[<>]", text) and not re.search(r"[{}\[\]]", text):
        from .normalize.parse import parse_relation
        try:
            rel = parse_relation(text, ctx.ns)
            if {str(x) for x in rel.free_symbols} == {tvar}:
                text = str(rel.as_set())
                flags.append("payload_notation_normalized")
        except Exception:  # noqa: BLE001 - left as written; the certificates report it
            pass
    if flags:
        ca.payload = text
        if ca.kind == "condition":
            ca.kind = "set"
    return flags


def _claim_convention(solution: Solution, ctx, task_kind: str = "") -> list[str]:
    """The texts of the claimed answer that, read as written, hold a closed operation whose value is a
    convention (`certify.domain.Convention`). An odd root of a negative number is compared under both
    readings by the evaluate and simplify certificates (equiv.conventions); anywhere else it is read
    one way: the root (-8)**(1/3) of x**3 = -8 was "not real" and {(-8)**(1/3)} INCORRECT (part d4a)."""
    from .certify.domain import Convention, definedness_conditions
    from .normalize.parse import parse_as_written
    payload = solution.claimed_answer.payload
    out: list[str] = []
    try:
        ns = ctx.claim_ns()
    except Exception:  # noqa: BLE001
        return out
    for txt in (payload if isinstance(payload, list) else [payload]):
        if not isinstance(txt, str):
            continue
        try:
            w = parse_as_written(txt, ns)
            conds = definedness_conditions(w, None) if w is not None else []
        except Exception:  # noqa: BLE001 - not read as written: the certificates read it
            continue
        both_ways = task_kind in ("evaluate", "simplify_expression")
        if any(isinstance(c, sp.Contains) and isinstance(c.args[1], Convention) and not c.free_symbols
               and not (both_ways and c.args[1].kind == "odd_root") for c in conds):
            out.append(txt)
    return out


def _claim_not_a_value(ir: ProblemIR, solution: Solution, ctx) -> LayerResult | None:
    from .normalize.parse import ClaimNotAValue, check_claim_is_value
    ca = solution.claimed_answer
    if ca.payload_source == "option_letter":
        return None                         # the option's own text is the problem's, not a claim
    if ca.kind in ("value", "count", "expression", "interval", "condition", "equation") \
            and isinstance(ca.payload, list):
        # only a set may be written as a list of elements; any other kind would be read as a set
        # or refused as "not an integer" — a verdict about a claim of the wrong shape
        return unknown("intake.claim", f"a {ca.kind} answer written as a list: not read",
                       flags=["parse_error", "claim_unreadable"])
    if not isinstance(ca.payload, str):
        # a set written as a list: its elements are claims too (GCD-10 was skipped: [gcd(84, 120)] for
        # the roots of x - 12 = 0 was certified, V16, 30 Sep 2026)
        return _claim_computes_integer_op(solution, ctx) if isinstance(ca.payload, list) else None
    try:
        check_claim_is_value(ca.payload, [f.name for f in ir.functions])
    except ClaimNotAValue as e:
        return unknown("intake.claim", str(e)[:200], flags=["claim_is_not_a_value"])
    # A count written as text is read like any claim: with the guarded parser. Unreadable text
    # (`3 or 4`, a Python expression) abstains; the count certificates would refute it as "not an
    # integer", which is a verdict about a claim nobody could read.
    if ca.kind == "count":
        from .normalize.parse import ParseError, parse_expr_str
        try:
            parse_expr_str(ca.payload, ctx.claim_ns(solution))
        except ParseError as e:
            return unknown("intake.claim", f"claimed count {ca.payload!r} is not readable: {str(e)[:120]}",
                           flags=["parse_error", "claim_unreadable"])
    # "3,5" is 3.5 in Turkish and the pair (3, 5) in the structured syntax. Reading it either way
    # would be a guess (principle 3), and the pair reading turned a right 3.5 into INCORRECT.
    if ca.kind in ("value", "count", "set") and not re.search(r"[{}\[\]()]", ca.payload) \
            and re.search(r"\d,\d", ca.payload):
        return unknown("intake.claim", f"claimed answer {ca.payload!r}: decimal comma or pair? not guessed",
                       flags=["decimal_comma_ambiguous"])
    # A value-shaped answer that still contains the problem's unknowns is not a value: `{x}` for
    # "solve x**2 - 5x + 6 = 0" was certified (z3 found Eq(x, x) satisfiable), and `10 - b` for
    # "evaluate a" restates a given (audit of 25 Sep 2026). The unknown is the task's variable
    # when it names one; otherwise a variable the givens pin down. A free parameter (`k` in
    # "solve x² = k") may appear in a right answer.
    if ir.answer_shape in ("scalar", "set", "count") and ca.kind in ("value", "set", "count"):
        tvar = (ir.task.params or {}).get("var")
        if isinstance(tvar, str):
            unknowns = {tvar}
        else:
            in_givens = set(re.findall(r"[A-Za-z_]\w*", " ".join(str(g) for g in ir.givens)))
            unknowns = {v.name for v in ir.vars} & in_givens
        try:
            claimed = ctx.claimed(solution)
            names = {s.name for s in getattr(claimed, "free_symbols", set())}
        except Exception:  # noqa: BLE001 - the certificates report an unreadable claim themselves
            names = set()
        hit = sorted(names & unknowns)
        if hit:
            return unknown("intake.claim", f"claimed answer {ca.payload!r} still contains the unknown(s) {hit}",
                           flags=["claim_is_not_a_value"])
    if ir.task.kind == "evaluate":
        target = (ir.task.params or {}).get("expr") or ir.unknown_of_interest
        if target and _same_structure(str(ca.payload), str(target), ctx):
            return unknown("intake.claim", f"claimed answer {ca.payload!r} restates the question",
                           flags=["claim_is_not_a_value"])
    return _claim_computes_integer_op(solution, ctx)


def _claim_computes_integer_op(solution: Solution, ctx) -> LayerResult | None:
    """A gcd/lcm of numbers is evaluated by the parser, so a claim written as one is a computation the
    verifier would do itself (principle 2): for "evaluate gcd(84, 120)" the claims gcd(120, 84),
    igcd(84, 120) and \\gcd(84, 120) were certified; only the literal restatement was caught (GCD-10,
    30 Sep 2026). A gcd of the problem's symbols (gcd(4, n) for gcd(n, 4)) is a value and stays."""
    ca = solution.claimed_answer
    texts = ca.payload if isinstance(ca.payload, list) else [ca.payload]
    if any(_INTEGER_OP_TEXT.search(str(t)) for t in texts):
        try:
            closed = not getattr(ctx.claimed(solution), "free_symbols", {None})
        except LeakageError:
            raise
        except Exception:  # noqa: BLE001 - the certificates report an unreadable claim themselves
            closed = False
        if closed:
            return unknown("intake.claim", f"claimed answer {ca.payload!r} computes a gcd/lcm, not a value",
                           flags=["claim_is_not_a_value"])
    return None


_INTEGER_OP_TEXT = re.compile(r"(?<![A-Za-z_])i?(?:gcd|lcm)\s*\(|\\(?:gcd|lcm)(?![A-Za-z])|"
                              r"\\(?:operatorname|mathrm|text|textrm)\s*\{\s*(?:gcd|lcm)\s*\}")


def _same_structure(a: str, b: str, ctx) -> bool:
    """Same UNEVALUATED expression tree — `gcd(84, 120)` vs `gcd(84,120)`, but not `12`."""
    try:
        from .formal.statement import parse_structural
        ta, tb = parse_structural(a, ctx.ns), parse_structural(b, ctx.ns)
    except Exception:  # noqa: BLE001
        return False
    try:
        if not getattr(tb, "args", None):
            return False                    # a bare number or symbol target cannot be restated
        return sp.srepr(ta) == sp.srepr(tb)
    except Exception:  # noqa: BLE001 - InconsistentAssumptions escaped here (third audit, 30 Sep 2026)
        return False


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
    fused = fuse(layers, extra_flags=extra_flags)
    total_ms = (time.perf_counter() - started) * 1000 if started else 0.0
    all_flags = list(fused["flags"]) + [f for f in (extra_flags or []) if f not in fused["flags"]]
    trace = fused["trace"] + scope_note(all_flags, fused["verdict"]) + f"\nToplam süre: {total_ms:.0f} ms"
    versions = _versions()
    if versions_extra:
        versions.update(versions_extra)
    return VerificationResult(verdict=fused["verdict"], confidence=fused["confidence"],
                              first_bad_step=fused["first_bad_step"], layers=layers,
                              decision_trace=trace, versions=versions, flags=all_flags)


# ℕ written without a mark: {1, 2, ...} or {0, 1, 2, ...}. The Turkish curriculum (and ISO 80000-2) puts 0
# in ℕ, other texts do not; the parser read ℕ, N and Naturals as {1, 2, ...} and certified {3} for
# x² − 3x = 0 over ℕ and refuted {0, 3} (fourth audit of 1 Oct 2026, CAP-N1). A problem or solution that
# writes it is verified under both readings and decided only when the verdicts agree. ℕ⁺, N+, Z+, ℕ0, N0,
# Naturals0 and the IR keywords (`natural` >= 1, `nonneg_integer`) are unambiguous and not rewritten.
_NAT_UNICODE = re.compile(r"ℕ(?!\s*(?:[⁺+₀0*]|_\{?[0+]|\^\{?[+*]))")
_NAT_NAME = re.compile(r"(?<![\w.])((?:S\.)?Naturals)(?![\w+*⁺₀])")
_NAT_LATEX = re.compile(r"\\mathbb\s*(?:\{\s*N\s*\}|N)(?!\s*(?:[⁺+₀0*]|_\{?[0+]|\^\{?[+*]))")
_NAT_BARE = re.compile(r"(?<![\w.])N(?![\w(⁺+₀0*_^])")


def _bare_n_as_set(s: str) -> str:
    """`s` with each bare `N` that stands for a set (`x in N`, `N`, `N U {-1}`) written `N0`; an `N`
    between two set operands is the intersection keyword (`A N B`, from ∩) and stays."""
    out, last = [], 0
    for m in _NAT_BARE.finditer(s):
        before, after = s[:m.start()].rstrip(), s[m.end():].lstrip()
        if re.search(r"\\mathbb\s*\{?$", before):
            continue                                   # \mathbb{N}: read by _NAT_LATEX
        prev_ok = before == "" or before.endswith(("(", ",", "∈", "∪", "{")) or re.search(r"(?:\bin|\bU)$", before)
        next_ok = after == "" or after.startswith((")", ",", "∪", "}")) or re.match(r"U\b", after)
        if prev_ok and next_ok:
            out.append(s[last:m.start()] + "N0")
            last = m.end()
    return "".join(out) + s[last:]


def _naturals_zero_reading(problem_ir: dict, solution: dict) -> tuple[dict, dict] | None:
    """The problem and the solution with every ℕ written without a mark read as {0, 1, 2, ...}, or None
    when they write none. ℕ, `Naturals` (also SymPy's `S.Naturals`) and \\mathbb{N} anywhere; a bare `N`
    where a set is read (the domain of discourse, a constraint, a claimed answer, an option), unless the
    problem declares a variable N."""
    names = {str((v or {}).get("name")) for v in problem_ir.get("vars") or [] if isinstance(v, dict)}

    def every(s: str) -> str:
        s = _NAT_UNICODE.sub("ℕ0", s)
        s = _NAT_NAME.sub(lambda m: m.group(1) + "0", s)
        return _NAT_LATEX.sub("Naturals0", s)

    def walk(o, set_text: bool):
        if isinstance(o, str):
            o = every(o)
            return _bare_n_as_set(o) if set_text and "N" not in names else o
        if isinstance(o, dict):
            return {k: walk(v, set_text or k in ("domain_of_discourse", "constraints", "payload", "options"))
                    for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return type(o)(walk(v, set_text) for v in o)
        return o

    ir2, sol2 = walk(problem_ir, False), walk(solution, False)
    if ir2 == problem_ir and sol2 == solution:
        return None
    return ir2, sol2


def verify_layers(problem_ir: ProblemIR | dict, solution: Solution | dict, seed: int = 0,
                  timeout: float = 8.0, run_steps: bool = True) -> tuple[list[LayerResult], list[str]]:
    """Run the deterministic layers and return (layers, flags) without fusing. A problem that writes ℕ
    without a mark is read both ways (see _naturals_zero_reading)."""
    import copy
    try:
        ir_d = problem_ir if isinstance(problem_ir, dict) else problem_ir.to_dict()
        sol_d = solution if isinstance(solution, dict) else solution.to_dict()
        zero = _naturals_zero_reading(copy.deepcopy(ir_d), copy.deepcopy(sol_d))
    except LeakageError:
        raise
    except Exception:  # noqa: BLE001 - not readable as dicts: the reading below reports it
        zero = None
    layers, flags = _verify_layers(problem_ir, solution, seed, timeout, run_steps)
    if zero is None:
        return layers, flags
    layers0, flags0 = _verify_layers(zero[0], zero[1], seed, timeout, run_steps)
    v_pos = fuse(layers, extra_flags=flags)["verdict"]
    v_zero = fuse(layers0, extra_flags=flags0)["verdict"]
    if v_pos == v_zero:
        return layers, flags + ["naturals_readings_agree"]
    return [unknown("intake.naturals", f"naturals_convention: with ℕ = {{1, 2, ...}} {v_pos}, with ℕ = "
                    f"{{0, 1, 2, ...}} {v_zero}", flags=["naturals_convention"])], flags


def _verify_layers(problem_ir: ProblemIR | dict, solution: Solution | dict, seed: int = 0,
                   timeout: float = 8.0, run_steps: bool = True) -> tuple[list[LayerResult], list[str]]:
    layers: list[LayerResult] = []
    if isinstance(problem_ir, dict):
        try:
            problem_ir = ProblemIR.from_dict(problem_ir)
        except MalformedIR as e:                   # LeakageError is not caught: it must stop
            layers.append(unknown("intake.ir", f"ir_malformed: {e}", flags=["ir_malformed"]))
            return layers, []
    if isinstance(solution, dict):
        try:
            solution = Solution.from_dict(solution)
        except MalformedSolution as e:
            layers.append(unknown("intake.solution", f"malformed_solution: {e}", flags=["malformed_solution"]))
            return layers, []

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
        if problem_ir.answer_shape in ("set", "interval") and _NO_SOLUTION.search(str(ca.payload).lower()):
            ca.payload = "{}"
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

    scope_flags += _normalize_set_notation(problem_ir, solution, ctx)

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

    # Every certificate reasons over the real numbers (symbols are real, z3 sorts are Real/Int, the
    # domain starts at ℝ). A variable declared complex or rational was silently read as real:
    # "x² = −1 over ℂ has no solution" and "x⁴ = 1 over ℂ gives x² + 1 = 2" were certified, and the
    # right answers would have been refuted (audit of 25 Sep 2026). There is no sound verdict here.
    unsupported = sorted(v.name for v in problem_ir.vars if v.domain in ("complex", "rational"))
    if problem_ir.vars and str(problem_ir.domain_of_discourse or "").strip().lower() in (
            "complex", "complexes", "c", "ℂ"):
        unsupported = unsupported or ["domain_of_discourse"]
    if unsupported:
        layers.append(unknown("intake.domain", f"var_domain_unsupported: {unsupported} (the certificates "
                              "reason over the reals)", flags=["var_domain_unsupported"]))
        return layers, clean_flags

    # A side condition (a given inequality next to the task's own relation) that cannot be solved
    # exactly would be dropped from the domain: the certificates would answer another question.
    try:
        tvar = (problem_ir.task.params or {}).get("var")
        unapplied = ctx.side_conditions(ctx.sym(tvar))[1] if isinstance(tvar, str) else []
    except Exception:  # noqa: BLE001 - a failed probe adds no fact
        unapplied = []
    if unapplied:
        layers.append(unknown("intake.domain", f"given_not_applied: {unapplied[:3]}",
                              flags=["given_not_applied"]))
        return layers, clean_flags

    # A function's declared domain that names a symbol no given fixes (f on x > a) is a condition
    # on that symbol too: the certificates read it on the variable alone and dropped it, so {-2, 2}
    # was certified for f(x) = 5 with f = x**2 + 1 on x > a (third audit of 30 Sep 2026, N5).
    unbound = [f"{f.name}: {', '.join(getattr(ctx.ns.get(f.name), 'domain_unbound', ()))}"
               for f in problem_ir.functions if getattr(ctx.ns.get(f.name), "domain_unbound", ())]
    if unbound:
        layers.append(unknown("intake.domain", f"function_domain_not_applied: {unbound[:3]}",
                              flags=["function_domain_not_applied"]))
        return layers, clean_flags
    # the same for a declared constraint that does not read as relations (`(0, oo)`, `x in (0, oo)`)
    unreadable = ctx.unreadable_constraints()
    if unreadable:
        layers.append(unknown("intake.domain", f"constraint_unreadable: {unreadable[:3]}",
                              flags=["constraint_unreadable"]))
        return layers, clean_flags

    # The problem's own expression is undefined as written at a point with nothing left to choose
    # (`f(-1)` for f(x) = log(x) − log(x) + x). SymPy simplified it to a value, and that value was
    # certified. There is no answer to check against.
    try:
        undefined = ctx.written_undefined()
    except Exception:  # noqa: BLE001 - a failed probe adds no fact
        undefined = []
    if undefined:
        layers.append(unknown("intake.definedness", f"problem_undefined_as_written: {undefined[:3]}",
                              flags=["problem_undefined_as_written"]))
        return layers, clean_flags
    # The claim itself, read as written, holds a value that is a convention (0**0, C(2, 5), Mod(7, -5)):
    # the parse computed it SymPy's way, and "0**0" for 5**0 was certified like 1 (part d4a). An odd
    # root of a negative number is compared under both readings instead (equiv.conventions).
    conv = _claim_convention(solution, ctx, problem_ir.task.kind)
    if conv:
        layers.append(unknown("intake.definedness", f"claim_value_is_a_convention: {conv[:3]}",
                              flags=["claim_convention"]))
        return layers, clean_flags

    # A claimed answer must be a VALUE. A computation (`integrate(…)`, `limit(…)`) or the
    # question written back (`f(g(2))`, `gcd(84, 120)` for "evaluate gcd(84, 120)") would make
    # the certificates compute the answer themselves — every one of those was certified CORRECT
    # before this check. It abstains, it does not refute: no answer was given, not a wrong one.
    not_a_value = _claim_not_a_value(problem_ir, solution, ctx)
    if not_a_value is not None:
        layers.append(not_a_value)
        # the certificates would read these claims one way and refute them: nothing to check
        if {"decimal_comma_ambiguous", "claim_unreadable"} & set(not_a_value.flags):
            return layers, clean_flags

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
        # A payload reconstructed from prose is advisory (SOLVER_FORMAT.md): a recovery mistake may
        # abstain but never refute. Only mc.consistency honoured that; the certificates refuted the
        # recovered claim directly, so a solution that chose the right letter was INCORRECT when
        # the extractor picked up an intermediate set from the prose (audit of 25 Sep 2026).
        if solution.claimed_answer.payload_source == "recovered_text" and lr.verdict == "fail":
            lr = unknown(name, "recovered_claim_refuted: the reconstructed payload is advisory, not refuted",
                         lr.latency_ms, lr.evidence, flags=["recovered_answer_refuted"])
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
