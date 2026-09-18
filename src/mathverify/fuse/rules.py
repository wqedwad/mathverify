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

from typing import Any

from ..types import LayerResult

THRESH_POS = 0.90
THRESH_NEG = 0.90

# Flags that by themselves forbid a CORRECT verdict (the certificate may be computed on
# a wrong problem object). F3 additions: an IR that failed its round-trip audit, a
# restructured solution whose answer disagrees with the deterministic extractor, and an
# L4 re-solve whose *certified* answer differs from the claim (two certified answers for
# one IR means the IR does not pin the problem).
_BLOCK_POSITIVE_FLAGS = {"ir_incomplete", "ir_inconsistent", "contradiction", "parse_error",
                         "ir_unfaithful", "restructure_answer_mismatch", "l4_disagree_certified",
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
