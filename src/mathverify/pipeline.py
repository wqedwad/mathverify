"""End-to-end pipeline (F3): raw Turkish question (+ options) and a solution — structured
(path a) or free text (path b) — to a three-valued verdict.

  L0/L1  extract_ir (LLM, two-family round-trip)  unless an IR is supplied
  intake structured solution, or LLM restructuring of free text (+ deterministic cross-check)
  L3/L6  deterministic certificates + step refuter            (verify_layers)
  L4     cross-family re-solve                                 (soft; never a verdict)
  L5     metamorphic method test                               (soft; never a verdict)
  L8     fusion with veto, noisy-OR, abstention                (fuse_layers)
The answer key never enters (D2); every LLM output is validated deterministically before use.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any

from .certify.base import unknown
from .llm import llm_versions, LLMFatalError
from .types import VerificationResult, LayerResult
from .verifier import verify_layers, fuse_layers

__all__ = ["run_pipeline", "PipelineResult"]


@dataclass
class PipelineResult:
    result: VerificationResult | None
    ir: dict[str, Any] | None
    ir_source: str
    solution: dict[str, Any] | None
    solution_source: str
    extraction: dict[str, Any] | None = None
    restructure: dict[str, Any] | None = None
    resolve: dict[str, Any] | None = None
    metamorphic: dict[str, Any] | None = None
    critic: dict[str, Any] | None = None
    formal: dict[str, Any] | None = None
    cost_usd: float = 0.0
    calls: int = 0
    latency_ms: float = 0.0
    stage: str = ""
    flags: list[str] = field(default_factory=list)
    base_verdict: str | None = None          # deterministic verdict before L4/L5

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["result"] = self.result.to_dict() if self.result else None
        return d


def _unknown_result(layer: str, reason: str, flags: list[str], started: float) -> VerificationResult:
    return fuse_layers([unknown(layer, reason, flags=flags)], started=started, versions_extra=llm_versions())


def run_pipeline(question_tr: str, options: dict[str, str] | None = None, level: str | None = None, *,
                 ir: dict[str, Any] | None = None, solution: dict[str, Any] | None = None,
                 solution_text: str | None = None, solver_family: str | None = None,
                 use_l4: bool = True, use_l5: bool = True, use_l6: bool = True, use_l7: bool = False,
                 l7_use_model: bool = True, llm_restructure: bool = True,
                 exclude_exemplar_ids: list[str] | None = None, seed: int = 0,
                 extract_effort: str = "max") -> PipelineResult:
    t0 = time.perf_counter()
    pr = PipelineResult(result=None, ir=None, ir_source="provided" if ir else "extracted", solution=None,
                        solution_source="structured" if solution else ("text" if solution_text else "none"))
    extra_flags: list[str] = []

    # ---- L0/L1: IR -----------------------------------------------------------------
    if ir is None:
        from .extract import extract_ir
        ex = extract_ir(question_tr, options, level, exclude_ids=exclude_exemplar_ids, effort=extract_effort)
        pr.extraction = ex.to_dict()
        pr.cost_usd += ex.cost_usd
        pr.calls += ex.calls
        if not ex.accepted or ex.ir is None:
            pr.stage = "ir_extraction_failed"
            pr.flags = ["ir_unavailable", f"ir_reason:{ex.reason}"]
            pr.result = _unknown_result("ir.extract", f"ir_unavailable:{ex.reason}", pr.flags, t0)
            pr.latency_ms = (time.perf_counter() - t0) * 1000
            return pr
        ir = ex.ir
        extra_flags.append("ir_extracted")
        n_rounds = len(ex.rounds)
        if n_rounds == 2:
            extra_flags.append("ir_repaired_once")
        elif n_rounds >= 3:
            extra_flags.append("ir_repaired_twice")
        last = ex.rounds[-1].get("roundtrip", {}) if ex.rounds else {}
        if any((j.get("score") or 0) == 9 for j in last.get("judges", {}).values()):
            extra_flags.append("roundtrip_borderline")
    pr.ir = ir

    # ---- intake: solution --------------------------------------------------------------
    if solution is None:
        if not solution_text:
            pr.stage = "no_solution"
            pr.result = _unknown_result("intake", "solution_unavailable", ["solution_unavailable"], t0)
            pr.latency_ms = (time.perf_counter() - t0) * 1000
            return pr
        if llm_restructure:
            from .extract.restructure_llm import restructure_solution
            rs = restructure_solution(ir, solution_text)
            pr.restructure = {k: v for k, v in rs.items() if k != "solution"}
            pr.cost_usd += rs.get("cost_usd", 0.0)
            pr.calls += rs.get("calls", 0)
            solution = rs.get("solution")
            extra_flags += rs.get("flags", [])
        if solution is None:
            from .intake.restructure import restructure_deterministic
            det = restructure_deterministic(solution_text, answer_shape=(ir or {}).get("answer_shape"))
            if det is None:
                pr.stage = "restructure_failed"
                pr.result = _unknown_result("intake", "solution_unparseable", ["solution_unavailable"], t0)
                pr.latency_ms = (time.perf_counter() - t0) * 1000
                return pr
            solution = det.to_dict()
            pr.solution_source = "text_deterministic"
            extra_flags.append("restructure_deterministic_only")
        else:
            pr.solution_source = "text_llm"
    pr.solution = solution

    # ---- deterministic layers ------------------------------------------------------------
    layers: list[LayerResult]
    layers, clean_flags = verify_layers(ir, solution, seed=seed)
    extra_flags += clean_flags

    # deterministic verdict before any LLM signal (used to interpret L4 disagreement)
    base = fuse_layers(list(layers), extra_flags=list(extra_flags), started=t0)
    pr.base_verdict = base.verdict

    # DECISIONS §17: the family that produced a solution may not judge it. Every judging layer
    # derives its family from `solver_family`, and with None they all fall back to "anthropic".
    # For the synthetic evaluation set that is harmless — nothing produced those solutions —
    # but against a real Claude solver it would silently mean Claude critiquing Claude. The
    # rule cannot be enforced from here (we do not know who wrote the solution), so the record
    # says it was not enforced instead of pretending it was.
    if solver_family is None and (use_l4 or use_l5 or use_l6 or use_l7):
        extra_flags.append("solver_family_unknown")

    # ---- L4 ------------------------------------------------------------------------------
    if use_l4:
        from .resolve import cross_family_resolve, l4_layer
        rs4 = cross_family_resolve(question_tr, options, ir, solver_family)
        pr.resolve = {k: v for k, v in rs4.items() if k not in ("trace",)}
        pr.cost_usd += rs4.get("cost_usd", 0.0)
        pr.calls += rs4.get("calls", 0)
        layers.append(l4_layer(ir, solution, rs4, original_verdict=base.verdict))

    # ---- L5 ------------------------------------------------------------------------------
    if use_l5:
        from .meta import metamorphic_check, l5_layer
        mt = metamorphic_check(question_tr, ir, solution, solver_family, seed=seed)
        pr.metamorphic = mt
        pr.cost_usd += mt.get("cost_usd", 0.0)
        pr.calls += mt.get("calls", 0)
        layers.append(l5_layer(mt))

    # ---- L7 Lean (F5) --------------------------------------------------------------------
    if use_l7:
        try:
            from .formal import l7_layer
            lr7, rec7 = l7_layer(ir, solution, solver_family, use_model=l7_use_model)
            pr.formal = {k: v for k, v in rec7.items() if k not in ("attempts",)} if isinstance(rec7, dict) else None
            pr.cost_usd += (rec7 or {}).get("cost_usd", 0.0)
            pr.calls += (rec7 or {}).get("calls", 0)
            layers.append(lr7)
        except LLMFatalError:
            raise                       # credit/auth: not a measurement, must reach the harness
        except Exception as e:  # noqa: BLE001
            layers.append(unknown("formal.lean", f"layer_exception: {type(e).__name__}: {str(e)[:120]}",
                                  flags=["lean_unavailable"]))

    # ---- L6 critic + meta-verification (F4) ----------------------------------------------
    if use_l6 and solution.get("steps"):
        from .critic import l6_critic_layer
        step_ev = next((l.evidence for l in layers if l.layer == "steps.refute"), None)
        lr, rec = l6_critic_layer(question_tr, options, ir, solution, solver_family, step_ev,
                                  original_verdict=base.verdict)
        pr.critic = {"cost_usd": rec["cost_usd"], "calls": rec["calls"],
                     "report": (rec.get("critic") or {}).get("report"),
                     "meta": (rec.get("meta") or {}).get("verdict"),
                     "errors": (rec.get("critic") or {}).get("errors")}
        pr.cost_usd += rec["cost_usd"]
        pr.calls += rec["calls"]
        layers.append(lr)

    pr.result = fuse_layers(layers, extra_flags=extra_flags, started=t0, versions_extra=llm_versions())
    pr.flags = pr.result.flags
    pr.stage = "done"
    pr.latency_ms = (time.perf_counter() - t0) * 1000
    return pr
