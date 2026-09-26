"""Bir olc.sh çıktı dizinindeki hatalı kararları denetçi grubuna göre sayar.

İşaretler betiklerin kendi etiketlerinden gelir: `[BUG]`, `BUG ` (tekrar betikleri), `!!!FALSE_CORRECT`,
`!!FALSE_INCORRECT`, `!!CRASH` (A sonda derlemi), `!!! MISMATCH` (C), `bad N` (E). D betiği işaret
basmaz; çıktısı elle okunur. Etiketlerin kendisi de yanlış olabilir (README'deki bilinen 4 etiket)."""
import re
import sys
from pathlib import Path

out = Path(sys.argv[1])
tot: dict[str, dict[str, int]] = {}
for f in sorted(out.glob("*.txt")):
    grp = f.name.split("__", 1)[0]
    t = f.read_text(errors="replace")
    e = tot.setdefault(grp, {"dosya": 0, "hatali": 0, "yanlis_onay": 0, "yanlis_ret": 0, "zaman_asimi": 0})
    e["dosya"] += 1
    e["zaman_asimi"] += "EXIT 124" in t
    if grp == "E":
        m = re.search(r"^bad (\d+)", t, re.M)
        e["hatali"] += int(m.group(1)) if m else 0
        continue
    e["hatali"] += len(re.findall(r"^(\[BUG\]|BUG |!!!FALSE_CORRECT|!!FALSE_INCORRECT|!!CRASH)", t, re.M))
    e["hatali"] += len(re.findall(r"!!! MISMATCH", t))
    e["yanlis_onay"] += len(re.findall(r"^!!!FALSE_CORRECT", t, re.M))
    e["yanlis_ret"] += len(re.findall(r"^!!FALSE_INCORRECT", t, re.M))
for k, v in tot.items():
    print(k, v)
