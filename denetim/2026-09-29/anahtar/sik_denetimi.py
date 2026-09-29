"""Mechanical check of the 86 distinct questions (DECISIONS §69): the key equals exactly one option,
with the K4 labeller's comparison (proved equality `right`, proved difference `wrong`, else
`undecided`). Options are read as values when the key is DNE. `undecided` is the labeller's limit
(it proves no difference between two expressions in a free symbol), read by hand.

    PYTHONPATH=src .venv/bin/python denetim/2026-09-29/anahtar/sik_denetimi.py

Kept out of pyflakes and pytest like the rest of denetim/."""
import collections
import json
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root))
    from harness.run_solver import answer_label
    groups = collections.OrderedDict()
    for p in sorted((root / "evalset" / "items").glob("*.json")):
        it = json.loads(p.read_text(encoding="utf-8"))
        groups.setdefault((it["question_tr"], json.dumps(it.get("options"), sort_keys=True)), []).append(it)
    problems = 0
    for n, items in enumerate(groups.values(), start=1):
        it = next((i for i in items if i["cell"] == "A"), items[0])
        ir, gold = it["problem_ir"], it["gold_answer"]
        gold_kind = (it["solution"].get("claimed_answer") or {}).get("kind") or "value"
        opts = it.get("options") or {}
        labels = {}
        for letter, text in opts.items():
            kind = "value" if gold_kind == "dne" else gold_kind
            sol = {"claimed_answer": {"kind": kind, "payload": text}, "steps": []}
            labels[letter] = answer_label(ir, sol, gold, gold_kind)[0]
        right = [k for k, v in labels.items() if v == "right"]
        und = [k for k, v in labels.items() if v == "undecided"]
        opt = next((i["solution"]["claimed_answer"].get("option") for i in items if i["cell"] == "A"), None)
        ok = (not opts) or (len(right) == 1 and not und and (opt is None or right == [opt]))
        if not ok:
            problems += 1
        print(f"Q{n:02d} {it['id']:12} {'TAMAM' if ok else 'SORUN'} anahtar={gold!r} doğru={right} karar_yok={und}"
              f" A-şıkkı={opt} şık_sayısı={len(opts)}")
    print(f"sorunlu: {problems} / {len(groups)}")


if __name__ == "__main__":
    main()
