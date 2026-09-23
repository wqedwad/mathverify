"""End-to-end NL -> IR extraction on a few NON-exemplar eval items, then verify the item's structured
solution against the extracted IR and compare with the hand-IR verdict."""
import json, sys, time
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from harness.loader import load_items, split_for_verifier
from mathverify.extract import extract_ir, EXEMPLAR_IDS, render_ir
from mathverify.verifier import verify

IDS = sys.argv[1:] or ["tyt-prob-003", "ayt-lim-001", "tyt-geo-004", "tyt-ola-006"]

if __name__ == "__main__":
    items = {it["id"]: it for it in load_items("evalset/items")}
    total_cost = 0.0
    for iid in IDS:
        it = items[iid]
        assert iid not in EXEMPLAR_IDS
        t0 = time.time()
        res = extract_ir(it["question_tr"], it.get("options"), it["level"])
        total_cost += res.cost_usd
        print(f"\n===== {iid}  accepted={res.accepted} reason={res.reason} calls={res.calls} cost=${res.cost_usd:.3f} {time.time()-t0:.0f}s")
        for r in res.rounds:
            rt = r.get("roundtrip", {})
            js = {f: (j.get("score"), j.get("discrepancies")) for f, j in rt.get("judges", {}).items()}
            print(f"  round {r['round']}: val_err={r.get('validation_errors')} judges={js} conf={r.get('confidence')} assumptions={r.get('assumptions')}")
        if res.ir:
            print("  extracted task:", json.dumps(res.ir["task"], ensure_ascii=False))
            print("  vars:", res.ir["vars"], "| givens:", res.ir["givens"], "| dod:", res.ir.get("domain_of_discourse"), "| shape:", res.ir["answer_shape"])
            print("  rendered:", render_ir(res.ir).replace("\n", " | ")[:300])
            ir_hand, sol, labels = split_for_verifier(it)
            v_hand = verify(ir_hand, sol)
            try:
                v_ext = verify(res.ir, sol)
                print(f"  verdict hand-IR={v_hand.verdict}  extracted-IR={v_ext.verdict} (label solution_is_correct={labels['solution_is_correct']})")
                if v_ext.verdict != v_hand.verdict:
                    print("  TRACE:", v_ext.decision_trace.replace("\n", " || ")[:600])
            except Exception as e:
                print("  verify(extracted) raised:", type(e).__name__, str(e)[:200])
    print(f"\nTOTAL COST ${total_cost:.3f}")
