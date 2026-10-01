"""fark.py dump in chunks (each run <= 5 min): same rows as denetim/2026-09-29/v14/fark.py dump.

    python denetim/2026-10-01/fark_parca.py <part.json> <start> <stop>   # rows [start, stop) of the evalset+k4 order
    python denetim/2026-10-01/fark_parca.py merge <out.json> <part.json>...
Run from the checkout root (fark.py's paths are relative), with PYTHONPATH=<checkout>/src:<checkout>.
A single dump passed 5 min on 1 Oct 2026 and the cloud container is restarted by the platform; five
chunks (0-112, 112-224, 224-336, 336-448, 448-558) stay under it. Kept out of pyflakes and pytest
like the rest of denetim/.
"""
import importlib.util
import json
import sys
from pathlib import Path


def _fark():
    spec = importlib.util.spec_from_file_location("fark", Path("denetim/2026-09-29/v14/fark.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def jobs():
    from harness.loader import load_items
    fark = _fark()
    items = {it["id"]: it for it in load_items(Path("evalset/items"))}
    out = [("evalset", iid, None) for iid in sorted(items)]
    recs = json.loads(fark.K4.read_text(encoding="utf-8"))["records"]
    out += [("k4", rec["id"], rec) for rec in recs if rec.get("solution") is not None]
    return fark, items, out


def part(path, start, stop):
    from harness.loader import split_for_verifier
    from harness.run_solver import answer_label
    from mathverify.verifier import verify
    fark, items, js = jobs()
    rows = {}
    for kind, iid, rec in js[start:stop]:
        it = items[iid]
        if kind == "evalset":
            ir, sol, _ = split_for_verifier(it)
            rows[f"evalset/{iid}"] = fark._row(verify(ir, sol))
        else:
            ir, key_solution, labels = split_for_verifier(it)
            row = fark._row(verify(ir, rec["solution"]))
            gold_kind = (key_solution.get("claimed_answer") or {}).get("kind") or "value"
            row["label"] = list(answer_label(ir, rec["solution"], labels["gold_answer"], gold_kind))
            rows[f"k4/{iid}"] = row
    Path(path).write_text(json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(js)} jobs, rows {start}:{stop} -> {len(rows)} in {path}")


def merge(out, parts):
    rows = {}
    for p in parts:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        assert not (set(d) & set(rows)), set(d) & set(rows)
        rows.update(d)
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(rows)} rows -> {out}")


if __name__ == "__main__":
    if sys.argv[1] == "merge":
        merge(sys.argv[2], sys.argv[3:])
    else:
        part(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
