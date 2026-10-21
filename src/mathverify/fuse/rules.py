"""L8 fusion — Phase-1 rule-based version with hard veto and abstention (handoff §4, D6).

Rules (all mandatory per the handoff):
  * a hard `fail` cannot be overridden by anything soft; there are no soft layers yet,
    but the structure is already the one F6 will calibrate;
  * no soft signal alone produces CORRECT/INCORRECT;
  * layer outputs are NOT averaged — independent hard certificates are combined
    with a noisy-OR (calibrated Naive-Bayes weights arrive in F6);
  * confidence is reduced by: CAS timeouts, layer contradictions, IR-incomplete flags;
  * abstention thresholds favour precision (D6): CORRECT needs >= THRESH_POS,
    INCORRECT needs >= THRESH_NEG; otherwise UNKNOWN.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from ..types import LayerResult

THRESH_POS = 0.90
THRESH_NEG = 0.90

# --------------------------------------------------------------------------- calibration
# Measured signal reliabilities (harness/calibrate.py) refine the POSITIVE decision only: a
# calibrated score below the fitted threshold turns CORRECT into UNKNOWN, and it can never
# turn a deterministic refutation into an acceptance (§4: a hard layer keeps its veto).
#
# OFF BY DEFAULT, because that is what the measurement says. On the 260-item set the fitted
# model costs 13 items of coverage (1.000 -> 0.950) and removes no false positive: the single
# remaining FP (a true-but-unjustified step) emits exactly the signals of a correct item, so no
# weighting can separate it. The machinery is kept because it is the layer that will matter
# once the soft LLM signals are measurable — [7] measures naive averaging 17.1 points behind a
# calibrated combination, and those weights cannot be guessed.
# Enable with MATHVERIFY_CALIBRATION=on, or by passing a path to load_calibration().
_CALIB: dict[str, Any] | None = None
_CALIB_TRIED = False
CALIBRATION_PATH = Path(__file__).resolve().parents[3] / "reports" / "calibration.json"


class CalibrationUnavailable(RuntimeError):
    """Calibration was asked for and could not be loaded. Raised rather than ignored: a silent
    fallback would run the default thresholds while the caller believes the fitted ones are in
    force, and `reports/*.json` is git-ignored, so a fresh clone hits this by default."""


def load_calibration(path: Path | str | None = None, force: bool = False) -> dict[str, Any] | None:
    global _CALIB, _CALIB_TRIED
    if force:
        _CALIB, _CALIB_TRIED = None, False
    if _CALIB_TRIED and path is None:
        return _CALIB
    _CALIB_TRIED = True
    if path is None and os.environ.get("MATHVERIFY_CALIBRATION", "off").lower() not in ("on", "1", "true"):
        _CALIB = None
        return None
    p = Path(path) if path is not None else CALIBRATION_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if "model" in data and "thresholds" in data:
            _CALIB = data
        else:
            raise ValueError(f"{p} has no 'model'/'thresholds'")
    except Exception as e:
        _CALIB = None
        # Asking for calibration and silently getting none is the worst outcome: the caller
        # believes the fitted thresholds are in force. `reports/*.json` is git-ignored, so a
        # fresh clone has no calibration.json at all and this is the normal way to hit it.
        raise CalibrationUnavailable(
            f"MATHVERIFY_CALIBRATION is on but the fitted model could not be loaded from {p}: {e}. "
            "Run `python -m harness.calibrate` to produce it, or unset MATHVERIFY_CALIBRATION."
        ) from e
    return _CALIB


def calibrated_score(layers: list[LayerResult], calib: dict[str, Any],
                     extra_flags: list[str] | tuple[str, ...] = ()) -> float:
    """Posterior log-odds that the solution is valid, from the measured signal weights.

    The signals are the ones harness/calibrate.py fitted: the layers' verdicts and flags AND the
    flags the verifier adds next to the layers (`extra_flags`: the scope flags such as
    answer_level_only). Without the latter the running model was not the measured one: on 16 of
    the 280 items it scored 0.41 higher than the fit, and tyt-geo-009 passed a threshold the fitted
    model held it under (measured 27 Sep 2026). The sum is exact (math.fsum), so the order of the
    signals cannot move a score across a threshold."""
    model = calib["model"]
    sigs = set()
    for l in layers:
        if l.verdict in ("pass", "fail"):
            sigs.add(f"{l.layer}:{l.verdict}:{'primary' if l.primary else 'support'}")
        for f in l.flags:
            sigs.add(f"flag:{f}")
    sigs.update(f"flag:{f}" for f in extra_flags)
    terms = [model.get("prior", 0.0)]
    for s in sorted(sigs):
        w = model["weights"].get(s)
        if w and w.get("used"):
            terms.append(w["weight"])
    return math.fsum(terms)

# Flags that by themselves forbid a CORRECT verdict (the certificate may be computed on
# a wrong problem object). F3 additions: an IR that failed its round-trip audit, a
# restructured solution whose answer disagrees with the deterministic extractor, and an
# L4 re-solve whose *certified* answer differs from the claim (two certified answers for
# one IR means the IR does not pin the problem).
_BLOCK_POSITIVE_FLAGS = {"ir_incomplete", "ir_inconsistent", "contradiction", "parse_error",
                         "ir_unfaithful", "restructure_answer_mismatch", "l4_disagree_certified",
                         # path (b): the answer reconstructed from the prose disagrees with the
                         # option letter. One of the two is not what the solver meant, so the
                         # certificate is about the wrong claim — abstain, never refute.
                         "recovered_answer_mismatch",
                         # a step claim that is not well-formed at all: the solution does not meet
                         # the structured contract, so skipping it silently would let an attacker
                         # cancel a refutation by corrupting the claim (measured on 4 items)
                         "malformed_step_claim",
                         # a layer that crashed decided nothing, so its silence is not agreement:
                         # a crash in the step layer used to let the certificate alone ground
                         # CORRECT and every refutation in the solution vanished (audit 25 Sep)
                         "layer_exception", "malformed_solution", "option_unreadable",
                         "decimal_comma_ambiguous", "recovered_answer_refuted",
                         # the prose around the value negates or doubts it ("5 değil")
                         "payload_negated", "problem_undefined_as_written", "var_domain_unsupported", "ir_malformed", "given_not_applied",
                         # the problem's definedness rests on a closed condition no exact check decides
                         # (fourth audit TAN-12: kept apart from "undefined", abstains all the same)
                         "problem_definedness_undecided",
                         "function_domain_not_applied", "constraint_unreadable",
                         # the claimed answer is a computation or restates the question: the
                         # certificates would be checking an answer the verifier itself produced
                         "claim_is_not_a_value",
                         # F4: a critic error that survived the deterministic cross-check AND the
                         # other family's meta-verification. It abstains, never flips to INCORRECT:
                         # an LLM signal may not veto a hard certificate (§4), and [10] measures
                         # 75-85% false rejection when step checkers are trusted outright.
                         "critic_error_confirmed",
                         # the chosen option and the claim are not shown to be one object (verifier._mc_undecided): a
                         # wrong letter beside a right value is a wrong solution (fourth audit, d4j addendum)
                         "option_claim_undecided",
                         # a '%' or '°' read as the unit and as the plain number decides differently: the question's
                         # convention (verifier._certify, final attack G1RK-3)
                         "unit_convention",
                         # several options lie in the declared tolerance window: the letter names none alone
                         # (verifier._options_in_tolerance, final attack G2YO-5)
                         "options_within_declared_tolerance"}
# The abstentions of a layer that decided nothing (verdict unknown), in two written kinds (fourth audit CAP-K1, d4i;
# denetim/2026-10-01/d4/kararlar_fhi.txt). A MEANING or convention abstention (the problem's meaning, a convention,
# a free parameter) keeps its UNKNOWN when the only CORRECT comes from a layer outside the deterministic ones (Lean,
# L7, a cross-family re-solve): that layer's template picks a meaning too (Lean's Finset.sum is 0 on a reversed range,
# intervalIntegral is defined at a free parameter), and a stand-in Lean pass turned the reversed series_sum -2, the
# derivative of x**2 at the end 0 of x > 0 and the limit of factorial(x) at 0 into CORRECT. A NOT PROVED abstention
# (no certificate, a membership or a solve left undecided) does not: another layer's proof stands, as the 3 Lean
# rescues of 89 runs did (count_integers with Mod, recurrences). A flag of neither list blocks like a meaning one
# (fail-closed); `tests/test_d4_d4j_kalan.py` catches a flag the code emits that no list here names.
_MEANING_FLAGS = {"point_not_interior", "membership_condition", "reversed_bounds", "condition_not_applied",
                  "constraint_not_applied", "parametric_limit", "parametric_form", "sequence_undefined_on_the_tail",
                  "approach_outside_declared_domain", "expression_undefined_as_written", "naturals_convention",
                  "claim_convention", "claim_unreadable", "variable_declared_integer", "written_domain",
                  "malformed_tolerance", "domain_list_ambiguous", "unit_convention",
                  "options_within_declared_tolerance"}
_NOT_PROVEN_FLAGS = {"cas_failed", "cas_unreliable", "cas_timeout", "completeness_uncertified", "no_certified_value",
                     "no_exact_value", "brute_force_limit", "symbolic_numeric_disagreement", "numeric_not_converged",
                     "relative_tolerance_undecided", "z3_unsupported", "condition_unsolved", "unsupported_task_kind",
                     "l4_undecided", "l4_disagree_uncertified", "l5_inconclusive", "l5_method_failed", "lean_unproved",
                     "lean_audit_failed", "lean_unavailable", "critic_cannot_judge", "critic_unavailable",
                     "ir_unavailable", "solver_family_unknown"}
# what a layer notes, no abstention: the scope of a verdict, a notation read, the pipeline's steps, a layer's own result
_NOTE_FLAGS = {"answer_from_option_letter", "answer_level_only", "steps_not_checked", "payload_cleaned",
               "payload_notation_normalized", "naturals_readings_agree", "domain_list_readings_agree", "ir_extracted",
               "ir_repaired_once", "ir_repaired_twice", "roundtrip_borderline", "restructure_deterministic_only",
               "l4_agree", "l4_confirms_refutation", "l5_method_ok", "lean_proved", "critic_clean",
               "critic_overruled_by_certificate", "calibrated_below_threshold", "layer_contradiction", "step_refuted"}
# the layers of `verifier.verify_layers`: a CORRECT one of them grounds is theirs, whatever the others abstained on
_DETERMINISTIC_LAYERS = ("certify.", "intake.", "steps.", "mc.", "ir.", "router", "sanity")


def _meaning_blocks(flags: list[str], primary_pass: list[LayerResult]) -> list[str]:
    """The flags that keep a CORRECT grounded only by layers outside the deterministic ones (see `_MEANING_FLAGS`):
    every one that is no NOT PROVED kind and no note."""
    if any(l.layer.startswith(_DETERMINISTIC_LAYERS) for l in primary_pass):
        return []
    return [f for f in flags if f not in _NOT_PROVEN_FLAGS and f not in _NOTE_FLAGS]


# Soft confidence reducers (handoff §4: long repair trajectories, timeouts, contradictions,
# L4 disagreement, L5 method failure). Never averaged with hard layers.
_CONFIDENCE_PENALTY = {"cas_timeout": 0.03, "symbolic_numeric_disagreement": 0.10,
                       "numeric_not_converged": 0.05, "completeness_uncertified": 0.0,
                       "l4_disagree_uncertified": 0.03, "l4_undecided": 0.0, "l5_method_failed": 0.08,
                       "ir_repaired_once": 0.02, "ir_repaired_twice": 0.05, "roundtrip_borderline": 0.02}


def _noisy_or(confs: list[float]) -> float:
    p = 1.0
    for c in confs:
        p *= (1.0 - max(0.0, min(1.0, c)))
    return 1.0 - p


def fuse(layers: list[LayerResult], extra_flags: list[str] | None = None) -> dict[str, Any]:
    """`extra_flags` (the verifier's flags next to the layers) only enter the calibrated score."""
    flags: list[str] = []
    for l in layers:
        for f in l.flags:
            if f not in flags:
                flags.append(f)
    hard_fail = [l for l in layers if l.hard and l.verdict == "fail"]
    hard_pass = [l for l in layers if l.hard and l.verdict == "pass"]
    primary_pass = [l for l in hard_pass if l.primary]
    primary_fail = [l for l in hard_fail if l.primary]
    trace: list[str] = []

    for l in layers:
        trace.append(f"[{l.layer}] {l.verdict} conf={l.confidence:.2f} hard={l.hard} "
                     f"primary={l.primary} {('flags=' + ','.join(l.flags)) if l.flags else ''} "
                     f"({l.latency_ms:.0f} ms)" + (f" reason={l.evidence.get('reason')}" if l.evidence.get('reason') else ""))

    # 1. contradiction among answer-level primary certificates -> UNKNOWN
    if primary_pass and primary_fail:
        flags.append("layer_contradiction")
        trace.append("Birincil sertifikalar çelişiyor (biri geçti, biri kaldı): karar verilemez -> UNKNOWN.")
        return {"verdict": "UNKNOWN", "confidence": 0.0, "first_bad_step": None,
                "trace": "\n".join(trace), "flags": flags}

    # 2. any hard fail -> INCORRECT (veto)
    if hard_fail:
        conf = max(l.confidence for l in hard_fail)
        fbs = None
        for l in hard_fail:
            if l.first_bad_step is not None:
                fbs = l.first_bad_step if fbs is None else min(fbs, l.first_bad_step)
        names = ", ".join(sorted({l.layer for l in hard_fail}))
        if conf >= THRESH_NEG:
            trace.append(f"Deterministik red: {names}. Verdict INCORRECT (conf={conf:.2f}).")
            return {"verdict": "INCORRECT", "confidence": round(conf, 4), "first_bad_step": fbs,
                    "trace": "\n".join(trace), "flags": flags}
        trace.append(f"Red sinyali var ({names}) ama güven eşik altında ({conf:.2f} < {THRESH_NEG}): UNKNOWN.")
        return {"verdict": "UNKNOWN", "confidence": round(conf, 4), "first_bad_step": fbs,
                "trace": "\n".join(trace), "flags": flags}

    # 3. positive evidence must be grounded by a primary certificate
    if primary_pass:
        blocked = [f for f in flags if f in _BLOCK_POSITIVE_FLAGS] or _meaning_blocks(flags, primary_pass)
        if blocked:
            fbs = next((l.first_bad_step for l in layers if l.first_bad_step is not None and not l.hard), None)
            trace.append(f"Pozitif sertifika var ama engelleyici bayrak(lar) mevcut: {blocked} -> UNKNOWN."
                         + (f" İşaretlenen adım: {fbs}." if fbs else ""))
            return {"verdict": "UNKNOWN", "confidence": 0.0, "first_bad_step": fbs,
                    "trace": "\n".join(trace), "flags": flags}
        conf = _noisy_or([l.confidence for l in primary_pass])
        conf = min(conf, 0.995)
        penalty = sum(_CONFIDENCE_PENALTY.get(f, 0.0) for f in flags)
        conf = max(0.0, conf - penalty)
        # certificate on a claim + unrefuted steps: no extra credit, no penalty
        if conf >= THRESH_POS:
            calib = load_calibration()
            if calib is not None:
                z = calibrated_score(layers, calib, extra_flags or ())
                hi = calib["thresholds"]["hi"]
                if z < hi:
                    flags.append("calibrated_below_threshold")
                    trace.append(f"Kalibre skor eşik altında (z={z:.2f} < {hi:.2f}): UNKNOWN. "
                                 "(Ölçülmüş sinyal güvenilirlikleri; kalibrasyon yalnızca "
                                 "temkinli yapar, reddi geçersizleştiremez.)")
                    return {"verdict": "UNKNOWN", "confidence": round(conf, 4), "first_bad_step": None,
                            "trace": "\n".join(trace), "flags": flags}
                trace.append(f"Kalibre skor eşiği geçti (z={z:.2f} ≥ {hi:.2f}).")
            names = ", ".join(sorted({l.layer for l in primary_pass}))
            trace.append(f"Birincil sertifika(lar) geçti: {names}. Verdict CORRECT (conf={conf:.3f}).")
            return {"verdict": "CORRECT", "confidence": round(conf, 4), "first_bad_step": None,
                    "trace": "\n".join(trace), "flags": flags}
        trace.append(f"Pozitif sertifika güveni eşik altında ({conf:.3f} < {THRESH_POS}): UNKNOWN.")
        return {"verdict": "UNKNOWN", "confidence": round(conf, 4), "first_bad_step": None,
                "trace": "\n".join(trace), "flags": flags}

    # 4. nothing decisive
    reasons = [f"{l.layer}: {l.evidence.get('reason')}" for l in layers if l.verdict == "unknown" and l.evidence.get("reason")]
    trace.append("Hiçbir deterministik sertifika karar veremedi -> UNKNOWN. " + ("; ".join(reasons) if reasons else ""))
    return {"verdict": "UNKNOWN", "confidence": 0.0, "first_bad_step": None,
            "trace": "\n".join(trace), "flags": flags}
