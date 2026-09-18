"""Try candidate tactics against concrete goals in the live REPL (F5 tactic development)."""
import sys
sys.path.insert(0, "src")
from mathverify.formal import get_lean

CASES = {
"eigenvector": ("(Matrix.mulVec !![2, 1; 1, 2] ![1, 1] = 3 • ![1, 1]) ∧ ((![1, 1] : Fin 2 → ℝ) ≠ 0)", [
  "  refine ⟨?_, ?_⟩\n  · funext i\n    fin_cases i <;> norm_num [Matrix.mulVec, Matrix.dotProduct, Fin.sum_univ_succ]\n  · intro h\n    have := congrFun h 0\n    norm_num at this",
  "  constructor\n  · funext i\n    fin_cases i <;> simp [Matrix.mulVec, Matrix.dotProduct, Fin.sum_univ_succ]\n  · intro h\n    have := congrFun h 0\n    simp at this",
  "  refine ⟨by funext i; fin_cases i <;> norm_num [Matrix.mulVec, Matrix.dotProduct, Fin.sum_univ_succ], ?_⟩\n  intro h\n  have h0 := congrFun h 0\n  norm_num at h0",
]),
"solve_system": ("(Matrix.mulVec !![1, 1; 2, 4] ![16, 14] = ![30, 88]) ∧ (!![1, 1; 2, 4].det ≠ 0)", [
  "  refine ⟨?_, by norm_num [Matrix.det_fin_two]⟩\n  funext i\n  fin_cases i <;> norm_num [Matrix.mulVec, Matrix.dotProduct, Fin.sum_univ_succ]",
  "  constructor\n  · funext i\n    fin_cases i <;> simp [Matrix.mulVec, Matrix.dotProduct, Fin.sum_univ_succ] <;> norm_num\n  · norm_num [Matrix.det_fin_two]",
]),
"eigenvalues": ("∀ t : ℝ, ((!![2, 1; 1, 2] - t • (1 : Matrix (Fin 2) (Fin 2) ℝ)).det = 0) ↔ (t = 1 ∨ t = 3)", [
  "  norm_num [Matrix.det_fin_two, Matrix.one_fin_two]\n  intro t\n  constructor\n  · intro h\n    have hf : (t - 1) * (t - 3) = 0 := by nlinarith\n    rcases mul_eq_zero.mp hf with h1 | h1\n    · left; linarith\n    · right; linarith\n  · rintro (h | h) <;> subst h <;> norm_num",
  "  intro t\n  simp [Matrix.det_fin_two, Matrix.one_fin_two]\n  constructor\n  · intro h\n    have hf : (t - 1) * (t - 3) = 0 := by nlinarith\n    rcases mul_eq_zero.mp hf with h1 | h1\n    · left; linarith\n    · right; linarith\n  · rintro (h | h) <;> subst h <;> norm_num",
]),
"extremum": ("(∃ x : ℝ, ((-2 : ℝ) ≤ x ∧ x ≤ 3) ∧ ((x ^ 3) + ((-3 : ℝ) * x)) = 18) ∧ (∀ x : ℝ, ((-2 : ℝ) ≤ x ∧ x ≤ 3) → ((x ^ 3) + ((-3 : ℝ) * x)) ≤ 18)", [
  "  refine ⟨⟨3, by norm_num, by norm_num⟩, fun x hx => ?_⟩\n  obtain ⟨h1, h2⟩ := hx\n  nlinarith [sq_nonneg (x - 3), sq_nonneg (x + 3), h1, h2]",
  "  refine ⟨⟨3, by norm_num, by norm_num⟩, fun x hx => ?_⟩\n  obtain ⟨h1, h2⟩ := hx\n  nlinarith [sq_nonneg (x + 3/2), mul_nonneg (sub_nonneg.mpr h2) (sq_nonneg (x + 3/2)), h1, h2]",
  "  refine ⟨⟨3, by norm_num, by norm_num⟩, fun x hx => ?_⟩\n  obtain ⟨h1, h2⟩ := hx\n  nlinarith [h1, h2, sq_nonneg x, sq_nonneg (x - 1), sq_nonneg (x + 1), mul_nonneg (sub_nonneg.mpr h2) (sq_nonneg (x + 1))]",
]),
"sqrt_ineq": ("∀ x : ℝ, ((0 ≤ (4 + x))) → ((Real.sqrt (4 + x) = ((-2 : ℝ) + x)) ↔ (x = 5))", [
  "  intro x hx\n  constructor\n  · intro h\n    have h2 : (0:ℝ) ≤ -2 + x := h ▸ Real.sqrt_nonneg _\n    have := Real.sq_sqrt hx\n    nlinarith [h, this]\n  · rintro rfl\n    rw [show (4:ℝ) + 5 = 3 ^ 2 by norm_num, Real.sqrt_sq (by norm_num : (0:ℝ) ≤ 3)]\n    norm_num",
]),
}
if __name__ == "__main__":
    lean = get_lean()
    want = sys.argv[1:] or list(CASES)
    for name in want:
        goal, tactics = CASES[name]
        print(f"\n===== {name}")
        for i, tac in enumerate(tactics):
            code = f"theorem try_{name}_{i} : {goal} := by\n{tac}"
            r = lean.run(code, timeout=90)
            print(f"  [{i}] clean={r.clean} {r.ms:.0f}ms", "" if r.clean else f"err={[e[:170] for e in r.errors][:1]}")
            if r.clean:
                break
