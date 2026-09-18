import json, time, sys
from mathverify.llm import get_client, available_families
from mathverify.llm.schemas import IR_SCHEMA, JUDGE_SCHEMA, ir_from_llm

SYS = "You formalise Turkish math questions into a JSON problem IR. Use canonical SymPy syntax with explicit '*' (e.g. 3*x + 2*y = 12). Fill every field; use null for unused params."
Q = "Bir çiftlikteki tavuk ve koyunların baş sayısı toplamı 30, ayak sayısı toplamı 88'dir. Kaç tavuk vardır? A) 12 B) 14 C) 16 D) 18 E) 20"

if __name__ == "__main__":
    print("families:", available_families())
    for fam in ("anthropic", "meta"):
        c = get_client(fam)
        t0 = time.time()
        try:
            r = c.complete("Answer in JSON.", "Give score 7, faithful true, one discrepancy 'none', notes 'ok'.",
                           schema=JUDGE_SCHEMA, effort="low", max_tokens=2000, tag="smoke_judge")
            print(f"[{fam}:{c.model}] judge ok={r.ok} stop={r.stop_reason} cached={r.cached} parsed={r.parsed} "
                  f"tok={r.input_tokens}/{r.output_tokens} cost=${r.cost_usd:.4f} {time.time()-t0:.1f}s")
        except Exception as e:
            print(f"[{fam}] judge FAILED: {type(e).__name__}: {str(e)[:400]}")
        t0 = time.time()
        try:
            r = c.complete(SYS, Q, schema=IR_SCHEMA, effort="high", max_tokens=12000, tag="smoke_ir")
            ok = r.parsed is not None
            print(f"[{fam}:{c.model}] IR ok={ok} stop={r.stop_reason} tok={r.input_tokens}/{r.output_tokens} "
                  f"cost=${r.cost_usd:.4f} {time.time()-t0:.1f}s")
            if ok:
                ir = ir_from_llm(r.parsed)
                print("   task:", ir["task"], "| vars:", ir["vars"], "| givens:", ir["givens"], "| options:", ir["options"])
        except Exception as e:
            print(f"[{fam}] IR FAILED: {type(e).__name__}: {str(e)[:600]}")
