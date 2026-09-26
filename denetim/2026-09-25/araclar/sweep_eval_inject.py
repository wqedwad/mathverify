"""For every evalset item whose claimed answer is correct (cells A/B), wrap the payload in a
harmless Python call that only a real eval would resolve: __import__('os').getpid()*0 + (<payload>).
A safe parser rejects it ('__', 'import'); CORRECT means some path evaluated Python code."""
import sys, copy, json
from pathlib import Path
import os; sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src"))); sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from harness.loader import load_items, split_for_verifier
from mathverify.verifier import verify

if __name__ == "__main__":
    items = load_items((__import__("pathlib").Path(__file__).resolve().parents[3] / "evalset" / "items"))
    hits, tried, kinds = [], 0, {}
    for it in items:
        ir, sol, meta = split_for_verifier(it)
        ca = sol.get("claimed_answer") or {}
        p = ca.get("payload")
        if meta.get("cell") not in ("A", "B") or not isinstance(p, str) or not p.strip():
            continue
        for wrap in ("__import__('os').getpid()*0 + ({p})", "0 or ({p})"):
            s2 = copy.deepcopy(sol)
            s2["claimed_answer"]["payload"] = wrap.format(p=p)
            s2["claimed_answer"].pop("option", None)
            tried += 1
            k = ir["task"]["kind"]
            kinds[k] = kinds.get(k, 0) + 1
            try:
                r = verify(copy.deepcopy(ir), s2)
                v = r.verdict
            except Exception as e:  # noqa: BLE001
                v = f"EXC {type(e).__name__}"
            if v == "CORRECT":
                hits.append((it["id"], k, wrap.split(" ")[0], ca.get("kind")))
    print("tried", tried, "by kind", kinds)
    print("CORRECT on injected payloads:", len(hits))
    for h in hits: print("  ", h)
