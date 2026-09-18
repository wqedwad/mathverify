"""L7: prove the deterministically generated statement in Lean 4 + Mathlib, then audit.

Order (positive evidence only — handoff §3 rule 4):
  1. statement from the IR (deterministic; no model involved)          formal/statement.py
  2. tactic ladder: cheap Mathlib automation first, no model at all
  3. if that fails, a cross-family model writes a proof, with a bounded repair loop fed the
     real Lean error messages
  4. audits before any `pass`: no `sorry`, axioms ⊆ {propext, Classical.choice, Quot.sound},
     hypotheses not contradictory (vacuity probe), hypotheses actually used (no-hyp probe)
A failed proof is NEVER evidence against the claim ("kanıtlayamadım" ≠ "yanlış").
"""
from __future__ import annotations

import re
import time
from typing import Any

from ..certify.base import Timer, result, unknown
from ..llm import get_client, other_family, LLMError
from ..llm.schemas import _obj, _s
from .lean_client import LeanClient, LeanResult, get_lean, LeanUnavailable
from .statement import LeanStatement, build_statement

__all__ = ["prove_statement", "l7_layer", "TACTIC_LADDER", "IFF_LADDER", "ladder_for", "PROOF_SCHEMA",
           "SAFE_AXIOMS"]

LAYER = "formal.lean"

SAFE_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

TACTIC_LADDER = [
    "  norm_num",
    "  omega",
    "  linarith",
    "  nlinarith",
    "  nlinarith [sq_nonneg (a - b), sq_nonneg (a + b)]",
    "  field_simp at *; linarith",
    "  field_simp at *; nlinarith",
    "  norm_num; linarith",
    "  simp_all; linarith",
    "  decide",
]

# solution-set goals: (∀ x, conds → (eq ↔ x = r ∨ ...)) ∧ conds[r] ∧ eq[r] ∧ ...
IFF_LADDER = [
    "  refine ⟨fun x hx => ?_, by norm_num⟩ <;> constructor <;> intro h <;> [linarith; linarith]",
    "  refine ⟨fun x hx => ?_, ?_, ?_⟩ <;> [skip; norm_num; norm_num] <;>\n"
    "    rw [div_eq_iff hx] <;> constructor <;> intro h <;> linarith",
    "  constructor\n"
    "  · intro x hx\n"
    "    rw [div_eq_iff hx]\n"
    "    constructor <;> intro h <;> linarith\n"
    "  · norm_num",
    "  refine ⟨fun x hx => ?_, by norm_num, by norm_num⟩\n"
    "  field_simp\n"
    "  constructor <;> intro h <;> linarith",
    "  refine ⟨fun x => ?_, by norm_num⟩\n"
    "  constructor <;> intro h <;> [linarith; linarith]",
    "  norm_num\n"
    "  intro x\n"
    "  constructor <;> intro h <;> linarith",
    "  constructor <;> intro x <;> norm_num <;> intro h <;> linarith",
    "  refine ⟨fun x hx => ?_, ?_⟩ <;> norm_num <;> intro h <;> nlinarith",
]


def ladder_for(kind: str) -> list[str]:
    if kind in ("solve_equation_set", "solve_equation_iff"):
        return IFF_LADDER + TACTIC_LADDER
    return TACTIC_LADDER

PROOF_SCHEMA = _obj({
    "proof": _s("Lean 4 tactic block, each line indented by two spaces, no 'theorem' header, no sorry"),
    "explanation": _s(),
})

PROOF_SYSTEM = """You write Lean 4 (Mathlib, recent toolchain) tactic proofs. You are given a complete theorem statement — do NOT restate or change it, and do not introduce new hypotheses. Return only the tactic block that goes after `:= by`, with every line indented by two spaces.

Rules: Mathlib 4 syntax only (`Real.sqrt`, `Real.log`, `Nat.choose`, `Int.gcd`, `omega`, `linarith`, `nlinarith`, `norm_num`, `field_simp`, `ring_nf`, `positivity`, `decide`, `constructor`, `rcases`, `intro`). Never write `sorry`, `admit`, `native_decide`, or an `axiom`. Prefer short robust proofs: for linear arithmetic over ℝ use `linarith` (over ℤ `omega`), for numeric goals `norm_num`, for iff goals `constructor <;> intro h` then close each side. If a hypothesis is named h1, h2, ... use those names. Reply in JSON."""


def _mk_proof_user(stmt_text: str, previous: str | None, errors: list[str] | None) -> str:
    parts = [f"## Theorem to prove\n```lean\n{stmt_text}\n```"]
    if previous:
        parts.append(f"## Your previous proof (rejected)\n```lean\n{previous}\n```\n## Lean errors\n"
                     + "\n".join(f"- {e}" for e in (errors or [])[:6]))
        parts.append("Fix the proof. Keep the statement untouched.")
    parts.append("## Tactic block (JSON)")
    return "\n\n".join(parts)


def _axioms_of(lean: LeanClient, name: str, env: int | None, timeout: float) -> tuple[set[str], str]:
    r = lean.run(f"#print axioms {name}", timeout=timeout, env=env)
    txt = " ".join(r.infos) or " ".join(r.errors)
    m = re.search(r"depends on axioms: \[(.*?)\]", txt, re.DOTALL)
    if not m:
        if "does not depend on any axioms" in txt:
            return set(), txt.strip()
        return {"<unknown>"}, txt.strip()
    return {a.strip() for a in m.group(1).split(",") if a.strip()}, txt.strip()


def prove_statement(stmt: LeanStatement, *, solver_family: str | None = None, lean: LeanClient | None = None,
                    tactic_timeout: float = 60.0, model_attempts: int = 3, effort: str = "xhigh",
                    use_model: bool = True) -> dict[str, Any]:
    """Return a full record: proof found?, audits, cost. Never raises for Lean failures."""
    out: dict[str, Any] = {"statement": None, "kind": stmt.kind, "proved": False, "proof": None,
                           "source": None, "attempts": [], "audit": {}, "calls": 0, "cost_usd": 0.0,
                           "errors": [], "ms": 0.0}
    t0 = time.perf_counter()
    try:
        lean = lean or get_lean()
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"lean_unavailable: {type(e).__name__}: {e}")
        return out
    # 1/2 deterministic tactic ladder
    for tac in ladder_for(stmt.kind):
        code = stmt.theorem(tac)
        out["statement"] = code.split(":= by")[0].strip()
        try:
            r = lean.run(code, timeout=tactic_timeout)
        except LeanUnavailable as e:
            out["errors"].append(f"lean_unavailable: {e}")
            out["ms"] = (time.perf_counter() - t0) * 1000
            return out
        out["attempts"].append({"source": "tactic", "proof": tac, "ok": r.clean,
                                "errors": r.errors[:2], "ms": round(r.ms)})
        if r.clean:
            out.update({"proved": True, "proof": tac, "source": "tactic_ladder", "env": r.env})
            break
    # 3 model-written proof with repair loop
    if not out["proved"] and use_model:
        family = other_family(solver_family) if solver_family else "anthropic"
        client = get_client(family)
        prev, errs = None, None
        for attempt in range(model_attempts):
            try:
                resp = client.complete(PROOF_SYSTEM, _mk_proof_user(stmt.theorem("  sorry").replace("  sorry", "  <your proof here>"), prev, errs),
                                       schema=PROOF_SCHEMA, effort=effort, max_tokens=6000, tag="lean_proof")
            except LLMError as e:
                out["errors"].append(f"llm: {str(e)[:150]}")
                break
            out["calls"] += 1
            out["cost_usd"] += resp.cost_usd
            proof = (resp.parsed or {}).get("proof") if isinstance(resp.parsed, dict) else None
            if not proof:
                errs = ["no proof returned"]
                continue
            if re.search(r"\b(sorry|admit|native_decide|axiom)\b", proof):
                out["attempts"].append({"source": "model", "proof": proof[:200], "ok": False,
                                        "errors": ["contains sorry/admit/native_decide/axiom"]})
                prev, errs = proof, ["the proof must not contain sorry, admit, native_decide or axiom"]
                continue
            code = stmt.theorem(proof)
            r = lean.run(code, timeout=tactic_timeout * 2)
            out["attempts"].append({"source": "model", "proof": proof[:300], "ok": r.clean,
                                    "errors": r.errors[:2], "ms": round(r.ms)})
            if r.clean:
                out.update({"proved": True, "proof": proof, "source": f"model:{family}", "env": r.env})
                break
            prev, errs = proof, r.errors or ["unknown failure"]
    # 4 audits
    if out["proved"]:
        audit: dict[str, Any] = {}
        ax, ax_txt = _axioms_of(lean, stmt.name, out.get("env"), tactic_timeout)
        audit["axioms"] = sorted(ax)
        audit["axioms_raw"] = ax_txt[:300]
        audit["axioms_ok"] = bool(ax <= SAFE_AXIOMS)
        audit["sorry_free"] = "sorryAx" not in ax
        vp = stmt.vacuity_probe()
        if vp:
            rv = lean.run(vp, timeout=tactic_timeout)
            audit["hypotheses_contradictory"] = bool(rv.clean)
            audit["vacuity_probe_errors"] = rv.errors[:1]
        else:
            audit["hypotheses_contradictory"] = False
        nh = stmt.no_hyp_probe(out["proof"])
        if nh:
            rn = lean.run(nh, timeout=tactic_timeout)
            audit["provable_without_hypotheses"] = bool(rn.clean)
        else:
            audit["provable_without_hypotheses"] = None
        audit["clean"] = bool(audit["axioms_ok"] and audit["sorry_free"]
                              and not audit["hypotheses_contradictory"]
                              and audit.get("provable_without_hypotheses") is not True)
        out["audit"] = audit
    out["ms"] = (time.perf_counter() - t0) * 1000
    return out


def l7_layer(ir: dict[str, Any], solution: dict[str, Any], solver_family: str | None = None, *,
             use_model: bool = True, tactic_timeout: float = 60.0):
    """Positive-only formal layer. Returns (LayerResult, record)."""
    with Timer() as t:
        stmt = build_statement(ir, solution["claimed_answer"])
        if stmt is None:
            return unknown(LAYER, "no_deterministic_lean_statement_for_this_task", t.ms,
                           {"reason": "out_of_scope"}), {"cost_usd": 0.0, "calls": 0}
        rec = prove_statement(stmt, solver_family=solver_family, use_model=use_model,
                              tactic_timeout=tactic_timeout)
        ev: dict[str, Any] = {"kind": stmt.kind, "statement": rec.get("statement"), "proved": rec["proved"],
                              "source": rec.get("source"), "audit": rec.get("audit"),
                              "attempts": len(rec.get("attempts") or []), "errors": rec.get("errors"),
                              "lean_ms": round(rec.get("ms", 0))}
    if rec["proved"] and rec.get("audit", {}).get("clean"):
        return result(LAYER, "pass", 0.995, True, ev, t.ms, primary=True, flags=["lean_proved"]), rec
    if rec["proved"]:
        ev["reason"] = "audit_failed"
        return result(LAYER, "unknown", 0.0, False, ev, t.ms, flags=["lean_audit_failed"]), rec
    ev["reason"] = "not_proved"
    return unknown(LAYER, "lean_could_not_prove", t.ms, ev, flags=["lean_unproved"]), rec
