import os, sys, json, importlib.util
sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
E = str(__import__("pathlib").Path(__file__).resolve().parent)
from mathverify.verifier import verify
IDS = os.environ.get("IDS", "A03 A07 A13 A41 A42 B40 B42 B50 B51 C03 C32 E01 E03 E10").split()
if __name__ == "__main__":
    allc = []
    for f in ("cases_a", "cases_b", "cases_c", "cases_e", "cases_f"):
        spec = importlib.util.spec_from_file_location(f, f"{E}/{f}.py"); m = importlib.util.module_from_spec(spec)
        sys.path.insert(0, E); spec.loader.exec_module(m)
        allc += m.CASES
    bad = 0
    for c in allc:
        cid = c["label"].split()[0]
        if IDS != ["ALL"] and cid not in IDS:
            continue
        r = verify(c["ir"], {"claimed_answer": c["claim"], "steps": []})
        wrong = (c["right"] is False and r.verdict == "CORRECT") or (c["right"] is True and r.verdict == "INCORRECT")
        bad += wrong
        if IDS != ["ALL"] or wrong:
            print(("BUG " if wrong else "ok  ") + f"{c['label'][:80]:80} -> {r.verdict} {r.flags}")
    print("bad", bad)
