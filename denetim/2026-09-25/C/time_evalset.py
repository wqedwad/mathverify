import json, glob, sys, time
sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify
KINDS = {"equation_of", "synthetic_geometry", "count_structures", "probability", "recurrence_term", "closed_form", "series_sum", "linalg"}
if __name__ == "__main__":
    rows = []
    for f in sorted(glob.glob(str(__import__("pathlib").Path(__file__).resolve().parents[3] / "evalset" / "items" / "*.json"))):
        d = json.load(open(f))
        k = d["problem_ir"]["task"]["kind"]
        if k not in KINDS: continue
        t0 = time.time(); r = verify(d["problem_ir"], d["solution"]); dt = time.time() - t0
        exp = "CORRECT" if d["solution_is_correct"] else "INCORRECT"
        lay = [l for l in r.layers if l.layer.startswith("certify")]
        cms = max((l.latency_ms for l in lay), default=0)
        rows.append((f.split("/")[-1][:-5], k, exp, r.verdict, round(dt, 2), round(cms / 1000, 2)))
    bad = [r for r in rows if r[2] != r[3]]
    print("n", len(rows), "mismatch", len(bad))
    for r in bad: print("MISMATCH", r)
    rows.sort(key=lambda r: -r[5])
    for r in rows[:8]: print("slowest", r)
