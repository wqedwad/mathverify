"""Verdicts, first bad steps, step statuses and K4 answer labels of the 280 evalset solutions and the
278 recorded K4 solutions (Muse Spark 1.3, reports/arsiv/2026-09-28/solver_meta_results.json), without
any LLM, for a before/after comparison of a verifier change:

    [MV_SRC=<src dir>] PYTHONUTF8=1 .venv/bin/python denetim/2026-09-29/v14/fark.py dump <out.json> [-j N]
                                                                          [--start S] [--stop E]
    .venv/bin/python denetim/2026-09-29/v14/fark.py compare <before.json> <after.json>

`MV_SRC` selects the source tree of the verifier (default: this checkout's src); the K4 labels come from
the harness of the same checkout (MV_SRC's parent when it has one, otherwise this checkout). The data
(evalset items, K4 records) always come from this checkout, so a "before" snapshot of an old commit is
taken with MV_SRC=<a separate git worktree of it>/src, never in a checkout that changes while it runs.
Without MV_SRC, a PYTHONPATH that names another source tree stops the dump instead of being ignored.
`-j N` runs the solutions in a pool of N spawned worker processes (default 1: in this process); the
rows do not depend on N. `--start/--stop` dump rows [S, E) of the evalset+k4 order (the order of
denetim/2026-10-01/fark_parca.py, which runs `_row` in chunks).

Per solution the snapshot keeps the verdict, the first bad step, every step's status (`steps`) and the
K4 label; since 16 Oct 2026 (taken over from denetim/2026-09-30/karar_farki.py of the franklin branch)
also the solution's flags, every layer's verdict, hardness, reason and flags (`layers`) and every
step's reason (`step_reasons`). Timings are left out. A verify (or label) exception is recorded as
`exception` and the dump goes on; LeakageError and LLMFatalError are not measurements and stop it
(principles 1 and 10).

`compare` prints every verdict, first bad step, step status, K4 label and exception difference, then
the counts and the first examples of the flag, layer and reason differences (information only), and
exits 1 if a verdict, first bad step, step status, K4 label, exception or the set of solutions differs,
0 otherwise. A field missing from either snapshot (one written before 16 Oct 2026, or a row whose
verify raised) is skipped. Scripts read the last line (`tail -1`) and the first line holding the word
"çözüm" (`grep -m1`): the last line keeps its form and is the only one printed with that word.

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = Path(os.environ.get("MV_SRC") or REPO / "src").resolve()
CODE = SRC.parent if (SRC.parent / "harness").is_dir() else REPO
ITEMS = REPO / "evalset" / "items"
K4 = REPO / "reports" / "arsiv" / "2026-09-28" / "solver_meta_results.json"
SHORT = 300         # characters kept of a reason or an exception message
EXAMPLES = 3        # examples printed per information category
INFO = (("flags", "BAYRAK", "bayrak"), ("layer_set", "KATMAN", "katman kümesi"),
        ("layer_verdict", "KATMAN_KARAR", "katman kararı"), ("layer_reason", "KATMAN_GEREKCE", "katman gerekçesi"),
        ("layer_flags", "KATMAN_BAYRAK", "katman bayrağı"), ("step_reason", "ADIM_GEREKCE", "adım gerekçesi"))

_JOBS: list = []    # a pool worker's slice of _jobs()


def _setup() -> None:
    """SRC and CODE first on sys.path, and the verifier imported from SRC (checked)."""
    if not os.environ.get("MV_SRC"):
        for e in filter(None, os.environ.get("PYTHONPATH", "").split(os.pathsep)):
            if (Path(e) / "mathverify").is_dir() and Path(e).resolve() != SRC:
                sys.exit(f"PYTHONPATH names the source tree {e}, this dump would read {SRC}: select it with MV_SRC")
    for p in (str(CODE), str(SRC)):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)
    import mathverify
    got = Path(mathverify.__file__).resolve().parents[1]
    if got != SRC:
        sys.exit(f"mathverify was imported from {got}, not from {SRC}")


def _short(x) -> str:
    return str(x)[:SHORT]


def _fatal() -> tuple[type[BaseException], ...]:
    from mathverify.ir import LeakageError
    from mathverify.llm.base import LLMFatalError
    return LeakageError, LLMFatalError


def _row(r) -> dict:
    """The snapshot of one VerificationResult (denetim/2026-10-01/fark_parca.py calls it too)."""
    steps, reasons, layers = {}, {}, []
    for layer in r.layers:
        ev = layer.evidence or {}
        layers.append([layer.layer, layer.verdict, layer.hard, _short(ev.get("reason", "")), sorted(layer.flags)])
        if layer.layer == "steps.refute":
            rows = ev.get("steps") or []
            steps = {s["id"]: s.get("status") for s in rows}
            reasons = {s["id"]: _short(s.get("reason") or (s.get("evidence") or {}).get("reason", "")) for s in rows}
    return {"verdict": r.verdict, "first_bad_step": r.first_bad_step, "steps": steps,
            "flags": sorted(r.flags), "layers": layers, "step_reasons": reasons}


def _jobs() -> list[tuple[str, dict, dict | None]]:
    """(key, item, K4 record or None): the evalset by id, then the K4 records that hold a solution."""
    from harness.loader import load_items
    items = {it["id"]: it for it in load_items(ITEMS)}
    out = [(f"evalset/{iid}", items[iid], None) for iid in sorted(items)]
    recs = json.loads(K4.read_text(encoding="utf-8"))["records"]
    out += [(f"k4/{rec['id']}", items[rec["id"]], rec) for rec in recs if rec.get("solution") is not None]
    return out


def _record(it: dict, rec: dict | None) -> dict:
    from harness.loader import split_for_verifier
    from harness.run_solver import answer_label
    from mathverify.verifier import verify
    fatal = _fatal()
    ir, key_solution, labels = split_for_verifier(it)       # outside the try: a leaked key stops the dump
    row, errors = {}, []
    try:
        row = _row(verify(ir, key_solution if rec is None else rec["solution"]))
    except fatal:
        raise
    except Exception as e:  # noqa: BLE001 - recorded and compared like any outcome
        errors.append(f"verify: {type(e).__name__}: {_short(e)}")
    if rec is not None:
        gold_kind = (key_solution.get("claimed_answer") or {}).get("kind") or "value"
        try:
            row["label"] = list(answer_label(ir, rec["solution"], labels["gold_answer"], gold_kind))
        except fatal:
            raise
        except Exception as e:  # noqa: BLE001
            errors.append(f"label: {type(e).__name__}: {_short(e)}")
    if errors:
        row["exception"] = "; ".join(errors)
    return row


def _init_worker(start: int, stop: int | None) -> None:
    global _JOBS
    _setup()
    _JOBS = _jobs()[start:stop]


def _work(i: int) -> tuple[str, dict]:
    key, it, rec = _JOBS[i]
    return key, _record(it, rec)


def dump(out: str, workers: int = 1, start: int = 0, stop: int | None = None) -> None:
    _setup()
    jobs = _jobs()[start:stop]
    rows, ex = {}, None
    if workers <= 1:
        results = ((key, _record(it, rec)) for key, it, rec in jobs)
    else:
        ex = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"),
                                 initializer=_init_worker, initargs=(start, stop))
        results = ex.map(_work, range(len(jobs)))
    try:
        for i, (key, row) in enumerate(results):
            assert key == jobs[i][0], (key, jobs[i][0])
            rows[key] = row
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(jobs)}", flush=True)
    finally:
        if ex is not None:
            ex.shutdown(wait=True, cancel_futures=True)
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    c = Counter((k.split("/")[0], v.get("verdict", "-")) for k, v in rows.items())
    n_exc = sum(1 for v in rows.values() if "exception" in v)
    print(f"src {SRC} (harness {CODE}), -j {workers}, satır [{start}:{'' if stop is None else stop}]")
    print("karar: " + ", ".join(f"{a} {b} {n}" for (a, b), n in sorted(c.items())) + f"; istisna {n_exc}")
    ev = [k for k in rows if k.startswith("evalset/")]
    k4 = [k for k in rows if k.startswith("k4/")]
    print(f"evalset {len(ev)}, k4 {len(k4)} -> {out}")


def _load(path: str) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(d) == {"src", "n", "results"}:
        sys.exit(f"{path}: a karar_farki snapshot (no K4 labels, another row form); dump it again with this script")
    return d


def _both(x: dict, y: dict, f: str) -> bool:
    return f in x and f in y


def _layers(row: dict) -> dict:
    """name -> [verdict, hard, reason, flags]; a repeated layer name is numbered (name#2, ...)."""
    out, seen = {}, Counter()
    for lay in row["layers"]:
        seen[lay[0]] += 1
        out[lay[0] if seen[lay[0]] == 1 else f"{lay[0]}#{seen[lay[0]]}"] = lay[1:]
    return out


def _show(v) -> str:
    # JSON with the summary line's search word escaped (ç is ç), so no other line carries it
    s = json.dumps(v, ensure_ascii=False).replace("çözüm", "\\u00e7özüm")
    return s if len(s) <= 160 else s[:157] + "..."


def compare(a: str, b: str) -> int:
    A, B = _load(a), _load(b)
    only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
    n_verdict = n_fbs = n_steps = n_label = n_exc = n_skip = 0
    info, examples = Counter(), {cat: [] for cat, _, _ in INFO}

    def note(cat: str, where: str, p, q) -> None:
        info[cat] += 1
        if len(examples[cat]) < EXAMPLES:
            examples[cat].append(f"{where}: {_show(p)} -> {_show(q)}")

    for k in sorted(set(A) & set(B)):
        x, y = A[k], B[k]
        if x.get("exception") != y.get("exception"):
            n_exc += 1
            print(f"ISTISNA {k}: {_show(x.get('exception'))} -> {_show(y.get('exception'))}")
        if _both(x, y, "verdict") and x["verdict"] != y["verdict"]:
            n_verdict += 1
            print(f"KARAR {k}: {x['verdict']} -> {y['verdict']}")
        if _both(x, y, "first_bad_step") and x["first_bad_step"] != y["first_bad_step"]:
            n_fbs += 1
            print(f"ILK_KOTU {k}: {x['first_bad_step']} -> {y['first_bad_step']}")
        if _both(x, y, "steps"):
            for sid in sorted(set(x["steps"]) | set(y["steps"])):
                if x["steps"].get(sid) != y["steps"].get(sid):
                    n_steps += 1
                    print(f"ADIM {k}/{sid}: {x['steps'].get(sid)} -> {y['steps'].get(sid)}")
        if _both(x, y, "label") and x["label"] != y["label"]:
            n_label += 1
            print(f"ETIKET {k}: {x['label']} -> {y['label']}")
        if not all(_both(x, y, f) for f in ("flags", "layers", "step_reasons")):
            n_skip += 1
            continue
        if x["flags"] != y["flags"]:
            note("flags", k, x["flags"], y["flags"])
        la, lb = _layers(x), _layers(y)
        for name in sorted(set(la) | set(lb)):
            p, q = la.get(name), lb.get(name)
            if p is None or q is None:
                note("layer_set", f"{k}/{name}", p, q)
                continue
            if p[:2] != q[:2]:
                note("layer_verdict", f"{k}/{name}", p[:2], q[:2])
            if p[2] != q[2]:
                note("layer_reason", f"{k}/{name}", p[2], q[2])
            if p[3] != q[3]:
                note("layer_flags", f"{k}/{name}", p[3], q[3])
        ra, rb = x["step_reasons"], y["step_reasons"]
        for sid in sorted(set(ra) | set(rb)):
            if ra.get(sid) != rb.get(sid):
                note("step_reason", f"{k}/{sid}", ra.get(sid), rb.get(sid))

    print("bilgi (çıkış kodunu etkilemez): " + ", ".join(f"{name} {info[cat]}" for cat, _, name in INFO))
    for cat, tag, _ in INFO:
        for line in examples[cat]:
            print(f"  {tag} {line}")
    if n_skip:
        print(f"gerekçe/bayrak alanı bir yanda olmayan {n_skip} kayıtta bu alanlar atlandı (eski döküm ya da istisna)")
    exc_a = sum(1 for v in A.values() if "exception" in v)
    exc_b = sum(1 for v in B.values() if "exception" in v)
    print(f"istisna farkı {n_exc} (istisnalı kayıt: önce {exc_a}, sonra {exc_b})")
    if only_a or only_b:
        for tag, keys in (("YALNIZ_ONCE", only_a), ("YALNIZ_SONRA", only_b)):
            for k in keys[:10]:
                print(f"{tag} {k}")
        print(f"anahtar farkı: yalnız önce {len(only_a)}, yalnız sonra {len(only_b)} "
              f"(karşılaştırılan {len(set(A) & set(B))})")
    ev = sum(1 for k in A if k.startswith("evalset/"))
    print(f"\n{len(A)} çözüm (evalset {ev}, k4 {len(A) - ev}): karar değişimi {n_verdict}, ilk kötü adım "
          f"değişimi {n_fbs}, adım durumu değişimi {n_steps}, K4 etiket değişimi {n_label}")
    return 1 if (n_verdict or n_fbs or n_steps or n_label or n_exc or only_a or only_b) else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("out")
    d.add_argument("-j", type=int, default=1, help="worker processes (default 1: in this process)")
    d.add_argument("--start", type=int, default=0)
    d.add_argument("--stop", type=int, default=None)
    c = sub.add_parser("compare", aliases=["diff"])
    c.add_argument("before")
    c.add_argument("after")
    args = ap.parse_args()
    if args.cmd == "dump":
        dump(args.out, args.j, args.start, args.stop)
        return 0
    return compare(args.before, args.after)


if __name__ == "__main__":
    sys.exit(main())
