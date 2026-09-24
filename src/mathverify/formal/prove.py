"""L7: prove the deterministically generated statement in Lean 4 + Mathlib, then audit.

Order (positive evidence only — handoff §3 rule 4):
  1. statement from the IR (deterministic; no model involved)          formal/statement.py
     every command sent for it (proof attempts, both probes) has autoImplicit off
  2. tactic ladder: cheap Mathlib automation first, no model at all
  3. if that fails, a cross-family model writes a proof, with a bounded repair loop fed the
     real Lean error messages
  4. audits before any `pass`: no `sorry`, axioms ⊆ {propext, Classical.choice, Quot.sound},
     hypotheses not contradictory (vacuity probe), hypotheses actually used (no-hyp probe);
     a probe Lean never answered (timeout, dead REPL) fails the audit
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
from .statement import AUTOIMPLICIT_OFF, LeanStatement, build_statement

__all__ = ["prove_statement", "l7_layer", "TACTIC_LADDER", "IFF_LADDER", "ladder_for", "PROOF_SCHEMA",
           "SAFE_AXIOMS", "NO_VERDICT", "lean_judged"]

LAYER = "formal.lean"

SAFE_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

# LeanClient._send_raw's own errors: Lean gave no verdict on the code because the call timed out
# (REPL killed), the REPL died, the pipe broke, or the reply was not JSON. harness/run_lean.py keeps
# no copy: it imports NO_VERDICT and lean_judged from here (a test checks they are these objects).
NO_VERDICT = ("lean timeout after", "empty reply (REPL died)", "write failed", "bad JSON from REPL")


def lean_judged(r: LeanResult) -> bool:
    """Did Lean itself judge this code? It did when the code compiled clean, or when it failed
    with at least one Lean error that is not a transport failure (NO_VERDICT). A timeout, a dead
    REPL, or a failure with no error at all is no verdict: fail closed. harness.run_lean's
    attempt_answered applies this function to a ladder attempt as prove_statement stored it
    (`ok` = the result's `clean`, its first two errors)."""
    if r.timed_out:
        return False
    if r.clean:
        return True
    return any(not str(e).startswith(NO_VERDICT) for e in r.errors)


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


# ∀ x y, (claimed curve equation) ↔ (the one the conditions determine)
EQUATION_OF_LADDER = [
    "  intro x y\n  constructor <;> intro h <;> linarith",
    "  intro x y\n  constructor <;> intro h <;> nlinarith [h, sq_nonneg x, sq_nonneg y]",
    "  intro x y\n  constructor <;> intro h <;> ring_nf at h ⊢ <;> linarith",
    "  intro x y\n  constructor <;> intro h <;> ring_nf at h ⊢ <;> nlinarith [h]",
]

# ∀ x, (inequality) ↔ (a < x ∧ x < b), and the rational case ∀ x, d ≠ 0 → (p/d ≥ 0 ↔ ...)
INEQ_LADDER = [
    "  intro x\n  constructor\n  · intro h\n    constructor <;> nlinarith\n  · rintro ⟨h1, h2⟩\n    nlinarith",
    "  intro x\n  constructor\n  · intro h\n    refine ⟨by nlinarith, by nlinarith⟩\n  · rintro ⟨h1, h2⟩\n    nlinarith [h1, h2, mul_pos (sub_pos.mpr h1) (sub_pos.mpr h2)]",
    "  intro x hx\n  rw [ge_iff_le, div_nonneg_iff]\n  constructor\n"
    "  · rintro (⟨h1, h2⟩ | ⟨h1, h2⟩)\n    · right; linarith\n"
    "    · left\n      rcases lt_or_eq_of_le h2 with h3 | h3\n      · linarith\n      · exact absurd h3 hx\n"
    "  · rintro (h | h)\n    · right; constructor <;> linarith\n    · left; constructor <;> linarith",
    "  intro x hx\n  rw [ge_iff_le, div_nonneg_iff]\n  constructor\n"
    "  · rintro (⟨h1, h2⟩ | ⟨h1, h2⟩)\n    · left; linarith\n"
    "    · right\n      rcases lt_or_eq_of_le h2 with h3 | h3\n      · linarith\n      · exact absurd h3 hx\n"
    "  · rintro (h | h)\n    · left; constructor <;> linarith\n    · right; constructor <;> linarith",
    "  intro x\n  constructor <;> intro h <;> [skip; skip] <;> nlinarith",
]

# matrix goals over Fin n: entry-wise after `ext` / `funext`. Measured in this toolchain:
# `dotProduct` lives at the root (not `Matrix.dotProduct`), and every matrix literal needs its
# element type ascribed or it elaborates as ℕ.
MATRIX_LADDER = [
    "  constructor <;>\n    (ext i j; fin_cases i <;> fin_cases j <;>\n"
    "      norm_num [Matrix.mul_apply, Matrix.one_apply, Fin.sum_univ_succ])",
    "  ext i j\n  fin_cases i <;> fin_cases j <;>\n"
    "    norm_num [Matrix.mul_apply, Matrix.one_apply, Fin.sum_univ_succ, pow_succ]",
    "  refine ⟨?_, ?_⟩\n"
    "  · funext i\n    fin_cases i <;> norm_num [Matrix.mulVec, dotProduct, Fin.sum_univ_succ]\n"
    "  · intro h\n    have h0 := congrFun h 0\n    norm_num at h0",
    "  refine ⟨?_, by norm_num [Matrix.det_fin_two]⟩\n"
    "  funext i\n  fin_cases i <;> norm_num [Matrix.mulVec, dotProduct, Fin.sum_univ_succ]",
    "  norm_num [Matrix.det_fin_two, Matrix.mul_fin_two, Matrix.one_fin_two]",
]

COUNT_LADDER = [
    "  refine ⟨fun x hx => ?_, by decide⟩\n  simp only [Finset.mem_Icc, abs_lt] at *\n  omega",
    "  refine ⟨fun x hx => ?_, by decide⟩\n  simp only [Finset.mem_Icc] at *\n  nlinarith [hx]",
    "  refine ⟨fun x hx => ?_, by decide⟩\n  simp only [Finset.mem_Icc]\n  constructor <;> nlinarith [hx]",
]

SUM_LADDER = ["  decide", "  norm_num [Finset.sum_Icc_succ_top]", "  simp [Finset.sum_Icc_succ_top]; norm_num"]

# ∫ x in a..b, f x = v — Mathlib's interval integral, with the closed-form lemmas
_INT_LEMMAS = ("integral_pow, integral_id, intervalIntegral.integral_const, integral_sin, integral_cos, "
               "integral_exp, integral_one_div, intervalIntegral.integral_const_mul, "
               "intervalIntegral.integral_add, intervalIntegral.integral_sub, "
               "intervalIntegral.integral_smul")
INTEGRAL_LADDER = [
    f"  norm_num [{_INT_LEMMAS}]",
    f"  simp [{_INT_LEMMAS}]\n  norm_num",
    f"  rw [intervalIntegral.integral_add (by fun_prop) (by fun_prop)]\n  norm_num [{_INT_LEMMAS}]",
    f"  norm_num [{_INT_LEMMAS}, mul_comm, mul_assoc]",
]

EXTREMUM_LADDER = [
    "  constructor\n  · norm_num\n  · intro x hx\n    obtain ⟨h1, h2⟩ := hx\n    nlinarith [h1, h2, sq_nonneg x]",
]

_BY_KIND = {
    "solve_equation_set": IFF_LADDER,
    "solve_equation_iff": IFF_LADDER,
    "solve_inequality_iff": INEQ_LADDER,
    "equation_of_iff": EQUATION_OF_LADDER,
    "linalg_inverse": MATRIX_LADDER,
    "linalg_matrix_expr": MATRIX_LADDER,
    "linalg_eigenvector": MATRIX_LADDER,
    "linalg_solve_system": MATRIX_LADDER,
    "linalg_eigenvalues": MATRIX_LADDER,
    "count_integers_finset": COUNT_LADDER,
    "series_sum_finite": SUM_LADDER,
    "definite_integral": INTEGRAL_LADDER,
    "extremum_max": EXTREMUM_LADDER,
    "extremum_min": EXTREMUM_LADDER,
}


def ladder_for(kind: str, hints: tuple[str, ...] = ()) -> list[str]:
    """Statement-specific hints first, then the ladder for that template, then the generic one."""
    return list(hints) + _BY_KIND.get(kind, []) + TACTIC_LADDER

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


def _shown(code: str) -> str:
    """A rendered command as the record (`statement`) and the proof model show it: without the
    compile option every command carries (AUTOIMPLICIT_OFF). What Lean compiles keeps it."""
    return code.removeprefix(AUTOIMPLICIT_OFF)


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
    for tac in ladder_for(stmt.kind, getattr(stmt, "hints", ())):
        code = stmt.theorem(tac)
        out["statement"] = _shown(code).split(":= by")[0].strip()
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
                resp = client.complete(PROOF_SYSTEM, _mk_proof_user(_shown(stmt.theorem("  sorry")).replace("  sorry", "  <your proof here>"), prev, errs),
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
        out["audit"] = _audit(stmt, out, lean, tactic_timeout)
    out["ms"] = (time.perf_counter() - t0) * 1000
    return out


def _audit(stmt: LeanStatement, out: dict[str, Any], lean: LeanClient, timeout: float) -> dict[str, Any]:
    """Axiom, vacuity and no-hypothesis audits of a compiled proof. Each probe needs a real Lean
    verdict: a probe Lean never judged (timeout, dead REPL, broken pipe, bad JSON, Lean gone for
    good) is listed in `unanswered` and the audit is not clean. Reading a timed-out probe as
    "did not compile" once gave the vacuous junk statement `x = 2 from 1/(x-2) = 0` a clean
    certificate: both probes timed out, so its hypotheses counted as consistent and used."""
    audit: dict[str, Any] = {}
    unanswered: list[str] = []

    def probe(code: str) -> tuple[bool, LeanResult]:
        """(did Lean judge it?, result). Lean gone for good (LeanUnavailable) is no verdict, and
        is recorded in out["errors"] so that run_lean's lean_reached sees it."""
        try:
            r = lean.run(code, timeout=timeout)
        except LeanUnavailable as e:
            msg = f"lean_unavailable: {e}"
            out["errors"].append(msg)
            return False, LeanResult(ok=False, errors=[msg])
        return lean_judged(r), r

    try:
        ax, ax_txt = _axioms_of(lean, stmt.name, out.get("env"), timeout)
    except LeanUnavailable as e:
        ax_txt = f"lean_unavailable: {e}"
        out["errors"].append(ax_txt)
        ax = {"<unknown>"}
    audit["axioms"] = sorted(ax)
    audit["axioms_raw"] = ax_txt[:300]
    audit["axioms_ok"] = bool(ax <= SAFE_AXIOMS)       # "<unknown>" (no verdict) is never safe
    audit["sorry_free"] = "sorryAx" not in ax
    vp = stmt.vacuity_probe()
    if vp:
        judged, rv = probe(vp)
        if judged:
            audit["hypotheses_contradictory"] = bool(rv.clean)
        else:
            audit["hypotheses_contradictory"] = None
            unanswered.append("vacuity")
        audit["vacuity_probe_errors"] = rv.errors[:1]
    else:
        audit["hypotheses_contradictory"] = False
    nh = stmt.no_hyp_probe(out["proof"])
    if nh:
        judged, rn = probe(nh)
        if judged:
            audit["provable_without_hypotheses"] = bool(rn.clean)
        else:
            audit["provable_without_hypotheses"] = None
            unanswered.append("no_hyp")
        audit["no_hyp_probe_errors"] = rn.errors[:1]
    else:
        audit["provable_without_hypotheses"] = None
    audit["unanswered"] = unanswered
    audit["clean"] = bool(audit["axioms_ok"] and audit["sorry_free"] and not unanswered
                          and not audit["hypotheses_contradictory"]
                          and audit.get("provable_without_hypotheses") is not True)
    return audit


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
