"""Independent audit of the dataset's answer keys (K4 (f), 29 Sep 2026; DECISIONS §69).

The 280 items share 86 distinct questions (`sorular.json`: question text and options, no key, no IR).
Each question was solved twice, by two solvers that saw only their group file (`grup1..4.json`) and
worked in their own directory (`cozucu_<group><a|b>/`: their scripts and `sonuc.json`). This script
compares both answers with the key: the key's option is the option whose text is the key, else the
option claimed by an A/B item (the right-answer cells). Kept out of pyflakes and pytest like the
rest of denetim/.

    .venv/bin/python denetim/2026-09-29/anahtar/karsilastir.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _key_option(items) -> str | None:
    it = items[0]
    opts = it.get("options") or {}
    exact = [k for k, v in opts.items() if v.replace(" ", "") == str(it["gold_answer"]).replace(" ", "")]
    if len(exact) == 1:
        return exact[0]
    claimed = {i["solution"]["claimed_answer"].get("option") for i in items if i["cell"] in ("A", "B")}
    claimed.discard(None)
    return claimed.pop() if len(claimed) == 1 else None


def main() -> int:
    groups: dict[tuple, list] = {}
    for p in sorted((ROOT / "evalset" / "items").glob("*.json")):
        it = json.loads(p.read_text(encoding="utf-8"))
        groups.setdefault((it["question_tr"], json.dumps(it.get("options"), sort_keys=True)), []).append(it)
    questions = json.loads((HERE / "sorular.json").read_text(encoding="utf-8"))
    solved: dict[str, dict] = {}
    for d in sorted(HERE.glob("cozucu_*")):
        for r in json.loads((d / "sonuc.json").read_text(encoding="utf-8")):
            solved.setdefault(r["qid"], {})[d.name[-1]] = r
    agree = 0
    for q in questions:
        items = groups[(q["question"], json.dumps(q["options"], sort_keys=True))]
        key, key_opt = items[0]["gold_answer"], _key_option(items)
        got = solved.get(q["qid"], {})
        letters = {k: r.get("option") for k, r in got.items()}
        multi = any(len(r.get("options_matching") or []) > 1 for r in got.values())
        unsure = any(not r.get("confident", True) for r in got.values())
        if q["options"]:
            ok = len(got) == 2 and key_opt is not None and set(letters.values()) == {key_opt}
        else:
            ok = len(got) == 2          # no options: compared by hand (DECISIONS §69)
        ok = ok and not multi and not unsure
        agree += ok
        mark = "UYUŞUYOR" if ok else "İNCELE  "
        print(f"{mark} {q['qid']} {items[0]['id']:12} anahtar={key!r} şık={key_opt} çözücüler={letters}"
              + ("" if q["options"] else f" cevaplar={[r.get('answer') for r in got.values()]}"))
    print(f"uyuşan: {agree} / {len(questions)}")
    return 0 if agree == len(questions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
