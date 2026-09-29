"""Verdicts, first bad steps, step statuses and K4 answer labels of the 280 evalset solutions and the
278 recorded K4 solutions (Muse Spark 1.3, reports/arsiv/2026-09-28/solver_meta_results.json), without
any LLM. Run it in the checkout under test (the old code in a separate worktree), then compare:

    PYTHONUTF8=1 PYTHONPATH=<checkout>/src:<checkout> .venv/bin/python denetim/2026-09-29/v14/fark.py dump <out.json>
    .venv/bin/python denetim/2026-09-29/v14/fark.py compare <before.json> <after.json>

Kept out of pyflakes and pytest like the rest of denetim/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

K4 = Path("reports/arsiv/2026-09-28/solver_meta_results.json")


def _row(r):
    steps = {}
    for layer in r.layers:
        if layer.layer == "steps.refute":
            steps = {s["id"]: s.get("status") for s in layer.evidence.get("steps", [])}
    return {"verdict": r.verdict, "first_bad_step": r.first_bad_step, "steps": steps}


def dump(out: str) -> None:
    from harness.loader import load_items, split_for_verifier
    from harness.run_solver import answer_label
    from mathverify.verifier import verify
    items = {it["id"]: it for it in load_items(Path("evalset/items"))}
    rows = {}
    for iid, it in sorted(items.items()):
        ir, sol, _ = split_for_verifier(it)
        rows[f"evalset/{iid}"] = _row(verify(ir, sol))
    recs = json.loads(K4.read_text(encoding="utf-8"))["records"]
    for rec in recs:
        if rec.get("solution") is None:
            continue
        it = items[rec["id"]]
        ir, key_solution, labels = split_for_verifier(it)
        row = _row(verify(ir, rec["solution"]))
        gold_kind = (key_solution.get("claimed_answer") or {}).get("kind") or "value"
        row["label"] = list(answer_label(ir, rec["solution"], labels["gold_answer"], gold_kind))
        rows[f"k4/{rec['id']}"] = row
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    ev = [k for k in rows if k.startswith("evalset/")]
    k4 = [k for k in rows if k.startswith("k4/")]
    print(f"evalset {len(ev)}, k4 {len(k4)} -> {out}")


def compare(a: str, b: str) -> None:
    A = json.loads(Path(a).read_text(encoding="utf-8"))
    B = json.loads(Path(b).read_text(encoding="utf-8"))
    assert set(A) == set(B), set(A) ^ set(B)
    n_verdict = n_fbs = n_steps = n_label = 0
    for k in sorted(A):
        x, y = A[k], B[k]
        if x["verdict"] != y["verdict"]:
            n_verdict += 1
            print(f"KARAR {k}: {x['verdict']} -> {y['verdict']}")
        if x["first_bad_step"] != y["first_bad_step"]:
            n_fbs += 1
            print(f"ILK_KOTU {k}: {x['first_bad_step']} -> {y['first_bad_step']}")
        for sid in sorted(set(x["steps"]) | set(y["steps"])):
            if x["steps"].get(sid) != y["steps"].get(sid):
                n_steps += 1
                print(f"ADIM {k}/{sid}: {x['steps'].get(sid)} -> {y['steps'].get(sid)}")
        if x.get("label") != y.get("label"):
            n_label += 1
            print(f"ETIKET {k}: {x.get('label')} -> {y.get('label')}")
    ev = sum(1 for k in A if k.startswith("evalset/"))
    print(f"\n{len(A)} çözüm (evalset {ev}, k4 {len(A) - ev}): karar değişimi {n_verdict}, ilk kötü adım "
          f"değişimi {n_fbs}, adım durumu değişimi {n_steps}, K4 etiket değişimi {n_label}")


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        dump(sys.argv[2])
    else:
        compare(sys.argv[2], sys.argv[3])
