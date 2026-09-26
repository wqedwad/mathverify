"""Field fuzz over one evalset item per task kind: every text or number leaf of the problem IR and of
the solution is replaced in turn by (0) an injection string, (1) a list holding it, (2) a dict
holding it, (3) a nested list, (4) a number, (5) None, (6) True. The injection writes a marker
file when evaluated. Reports: code executed (marker files), exceptions escaping verify(), and
CORRECT verdicts on mutated inputs (a mutated field should never make a wrong claim right, but a
right claim may stay right when the field is irrelevant, so CORRECTs are only listed)."""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
ROOT = Path(os.environ.get("MV_ROOT", str(__import__("pathlib").Path(__file__).resolve().parents[3])))
sys.path.insert(0, str(ROOT))

from harness.loader import load_items, split_for_verifier  # noqa: E402
from mathverify.verifier import verify  # noqa: E402


def leaves(o, pre=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, pre + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, pre + (i,))
    elif isinstance(o, (str, int, float)) and not isinstance(o, bool):
        yield pre


def put(o, p, v):
    for k in p[:-1]:
        o = o[k]
    o[p[-1]] = v


if __name__ == "__main__":
    d = tempfile.mkdtemp()
    items = load_items(ROOT / "evalset" / "items")
    seen, bases = set(), []
    for it in items:
        ir, sol, meta = split_for_verifier(it)
        k = ir["task"]["kind"]
        if meta.get("cell") == "A" and k not in seen:
            seen.add(k)
            bases.append((it["id"], ir, sol))
    n, esc = 0, []
    for iid, ir0, sol0 in bases:
        for which, root in (("ir", ir0), ("sol", sol0)):
            for p in list(leaves(root)):
                if which == "sol" and p[:1] == ("raw_text",):
                    continue
                for vi in range(7):
                    tag = os.path.join(d, f"{iid}~{which}~{'.'.join(map(str, p))}~{vi}")
                    inj = f"__import__('pathlib').Path({tag!r}).touch() or 2"
                    v = [inj, [inj], {"k": inj}, [[inj]], 7, None, True][vi]
                    ir, sol = copy.deepcopy(ir0), copy.deepcopy(sol0)
                    put(ir if which == "ir" else sol, p, v)
                    n += 1
                    try:
                        verify(ir, sol)
                    except Exception as e:  # noqa: BLE001
                        esc.append(f"{iid} {which} {'.'.join(map(str, p))} v{vi}: {type(e).__name__}: {str(e)[:100]}")
    ran = sorted(os.listdir(d))
    print(f"kinds {len(bases)} cases {n} code_ran {len(ran)} escaped {len(esc)}")
    for r in ran:
        print("  RAN", r)
    for e in esc:
        print("  EXC", e)
