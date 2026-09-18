import json, sys, time
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from harness.loader import load_items, split_for_verifier
from mathverify.formal import get_lean, build_statement, prove_statement, lean_available, sympy_to_lean
import sympy as sp

if __name__ == "__main__":
    t0 = time.time()
    print("lean_available:", lean_available(), f"{time.time()-t0:.0f}s")
    x = sp.Symbol('x'); a = sp.Symbol('a')
    for e in [sp.Integer(3), sp.Rational(1,2), 2*a+4, a**2 - 3*a, sp.sqrt(a), sp.Abs(a-1), sp.pi]:
        try: print("  print:", e, "->", sympy_to_lean(e))
        except Exception as ex: print("  print:", e, "-> ERR", ex)
    items = {it["id"]: it for it in load_items("evalset/items")}
    for iid in ["tyt-prob-001", "tyt-say-001", "tyt-prob-004", "tyt-prob-013", "tyt-esf-005", "ayt-tur-007"]:
        it = items[iid]
        ir, sol, labels = split_for_verifier(it)
        st = build_statement(ir, sol["claimed_answer"])
        if st is None:
            print(f"\n{iid}: no statement (kind={ir['task']['kind']})"); continue
        print(f"\n{iid} [{st.kind}] label_correct={labels['solution_is_correct']}")
        print("  stmt:", st.theorem("  <proof>").split(":= by")[0].strip()[:220])
        rec = prove_statement(st, use_model=False, tactic_timeout=60)
        print(f"  proved={rec['proved']} source={rec.get('source')} attempts={len(rec['attempts'])} {rec['ms']/1000:.1f}s")
        if rec["proved"]:
            print("  audit:", json.dumps(rec["audit"], ensure_ascii=False)[:300])
        else:
            print("  last errors:", [a["errors"] for a in rec["attempts"][-2:]])
