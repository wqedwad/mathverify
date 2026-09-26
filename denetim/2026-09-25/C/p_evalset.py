import json, glob, sys
sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify
KINDS = {"equation_of", "synthetic_geometry", "count_structures", "probability", "recurrence_term", "closed_form", "series_sum", "linalg"}
if __name__ == "__main__":
    from collections import Counter
    c = Counter(); bad = []
    for f in sorted(glob.glob(str(__import__("pathlib").Path(__file__).resolve().parents[3] / "evalset" / "items" / "*.json"))):
        d = json.load(open(f))
        k = d["problem_ir"]["task"]["kind"]
        if k not in KINDS:
            continue
        r = verify(d["problem_ir"], d["solution"])
        exp = "CORRECT" if d["solution_is_correct"] else "INCORRECT"
        c[(k, r.verdict == exp)] += 1
        if r.verdict != exp:
            bad.append((f.split("/")[-1], k, exp, r.verdict))
    for key in sorted(c): print(key, c[key])
    for b in bad: print("MISMATCH", b)
