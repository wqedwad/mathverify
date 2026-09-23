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


def calibrated_score(layers: list[LayerResult], calib: dict[str, Any]) -> float:
    """Posterior log-odds that the solution is valid, from the measured signal weights."""
    model = calib["model"]
    z = model.get("prior", 0.0)
    sigs = set()
    for l in layers:
        if l.verdict in ("pass", "fail"):
            sigs.add(f"{l.layer}:{l.verdict}:{'primary' if l.primary else 'support'}")
        for f in l.flags:
            sigs.add(f"flag:{f}")
    for s in sigs:
        w = model["weights"].get(s)
        if w and w.get("used"):
            z += w["weight"]
    return z

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
                         # the claimed answer is a computation or restates the question: the
                         # certificates would be checking an answer the verifier itself produced
                         "claim_is_not_a_value",
                         # F4: a critic error that survived the deterministic cross-check AND the
                         # other family's meta-verification. It abstains, never flips to INCORRECT:
                         # an LLM signal may not veto a hard certificate (§4), and [10] measures
                         # 75-85% false rejection when step checkers are trusted outright.
                         "critic_error_confirmed"}
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


def fuse(layers: list[LayerResult]) -> dict[str, Any]:
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
        blocked = [f for f in flags if f in _BLOCK_POSITIVE_FLAGS]
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
                z = calibrated_score(layers, calib)
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
