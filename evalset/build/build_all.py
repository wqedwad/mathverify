"""Build every evaluation item: python evalset/build/build_all.py"""
from __future__ import annotations

import importlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_items, ITEMS_DIR  # noqa: E402

MODULES = ["tyt_problemler", "tyt_sayilar", "tyt_denklem", "tyt_esitsizlik_fonksiyon",
           "ayt_limit", "ayt_turev", "ayt_integral", "ayt_trig", "ayt_analitik", "uni",
           # F2
           "tyt_geometri", "tyt_olasilik", "ayt_diziler", "uni_linalg",
           # router'da tanımlı olup sette hiç ölçülmemiş üç görev türü + LaTeX kapsamı
           "tyt_kapsam"]


def main() -> None:
    items = []
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError as e:
            if e.name == m:
                print(f"(skip {m}: not written yet)")
                continue
            raise
        items += mod.ITEMS
    for f in ITEMS_DIR.glob("*.json"):
        f.unlink()
    n = write_items(items)
    cells = Counter(it["cell"] for it in items)
    levels = Counter(it["level"] for it in items)
    print(f"wrote {n} items -> {ITEMS_DIR}")
    print("cells :", dict(sorted(cells.items())), {c: f"{cells[c]/n:.1%}" for c in sorted(cells)})
    print("levels:", dict(sorted(levels.items())))
    print("topics:", dict(sorted(Counter(it["topic"] for it in items).items())))


if __name__ == "__main__":
    main()
