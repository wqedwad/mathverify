"""Verify one (problem_ir, solution) pair from JSON files or a single eval item.

    python scripts/verify_cli.py --ir problem.json --solution solution.json
    python scripts/verify_cli.py --item evalset/items/tyt-prob-001.json
    python scripts/verify_cli.py --item evalset/items/tyt-prob-001.json --text "…Cevap: C"   # path (b)

Prints the three-valued verdict, confidence, first bad step, and the decision trace.
Gold labels inside an eval item are stripped before the verifier sees anything (D2).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def _with_lean(result, ir, sol):
    """Re-fuse with the formal layer added. L7 is positive-only and model-free here: it can add a
    certificate, never take one away, so a missing or failing Lean toolchain leaves the verdict
    exactly as it was."""
    from mathverify.formal import l7_layer
    from mathverify.verifier import fuse_layers
    ir_d = ir if isinstance(ir, dict) else ir.to_dict()
    sol_d = sol if isinstance(sol, dict) else sol.to_dict()
    try:
        lr, _rec = l7_layer(ir_d, sol_d, solver_family=None, use_model=False)
    except Exception as e:  # noqa: BLE001
        print(f"(Lean katmanı çalışmadı: {type(e).__name__}: {str(e)[:120]})")
        return result
    return fuse_layers(list(result.layers) + [lr])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir")
    ap.add_argument("--solution")
    ap.add_argument("--item")
    ap.add_argument("--text", help="free-text solution (path b): only the final answer is extracted")
    ap.add_argument("--json", action="store_true", help="print the full VerificationResult as JSON")
    ap.add_argument("--no-steps", action="store_true")
    ap.add_argument("--lean", action="store_true",
                    help="L7 formal katmanını da koştur (yerel Lean/Mathlib gerekir, model yok)")
    args = ap.parse_args(argv)

    from mathverify.verifier import verify
    from mathverify.intake import load_problem_ir, load_solution, restructure_deterministic

    if args.item:
        from harness.loader import split_for_verifier
        it = json.loads(Path(args.item).read_text(encoding="utf-8"))
        ir_d, sol_d, _labels = split_for_verifier(it)
        ir = load_problem_ir(ir_d)
        sol = load_solution(sol_d)
    else:
        if not args.ir:
            ap.error("--ir or --item is required")
        ir = load_problem_ir(Path(args.ir).read_text(encoding="utf-8"))
        if args.solution:
            sol = load_solution(Path(args.solution).read_text(encoding="utf-8"))
        else:
            sol = None
    if args.text:
        sol = restructure_deterministic(args.text)
        if sol is None:
            print("Serbest metinden nihai cevap çıkarılamadı (yol b).")
            return 2
    if sol is None:
        ap.error("--solution or --text is required")

    r = verify(ir, sol, run_steps=not args.no_steps)
    if args.lean:
        r = _with_lean(r, ir_d if args.item else ir, sol)
    if args.json:
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=1, default=str))
    else:
        print(f"VERDICT: {r.verdict}   confidence={r.confidence:.3f}   first_bad_step={r.first_bad_step}")
        if r.flags:
            print("flags:", ", ".join(r.flags))
        print(r.decision_trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
