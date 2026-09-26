"""harness.adversarial split over processes (DECISIONS §59): the report must be the one a single
process writes, but for the timings, and a result the load of the other workers could have
decided must not pass unchecked.

The sweep was 80% of `check.py --full` on one core of four; items now go to a pool of worker
processes and the results are scored in item order. Scoring is shared, so what can differ is only
what the pool does: lose, duplicate or reorder an item, run it in a different state, or swallow a
worker's error. The subset starts with an item that takes longer than the next one, so with two
workers the items finish out of order and a merge in completion order would show here.
"""
import json
import os
import signal
import subprocess
import sys
import time
import types
import uuid
from pathlib import Path

import pytest

import adversarial_fakes
from harness import adversarial as A

ROOT = Path(__file__).resolve().parents[1]

# A slower item first (2.8 s in the 26 Sep sweep; an interval answer), then quick ones (0.1-0.4 s;
# a set answer among them); together they reach every attack surface (answer, option letter kept,
# steps) and the set and interval shapes.
IDS = ["tyt-kap-003", "tyt-ola-004", "tyt-ola-015", "uni-la-007"]


def _comparable(s: dict) -> str:
    s = {k: v for k, v in s.items() if k not in ("seconds", "workers")}
    s["per_item"] = [{k: v for k, v in p.items() if k != "seconds"} for p in s["per_item"]]
    return json.dumps(s, ensure_ascii=False)          # key order counts: the report is written in it


@pytest.fixture(scope="module")
def runs(evalset_items):
    by_id = {it["id"]: it for it in evalset_items}
    items = [by_id[i] for i in IDS]
    return A.run(items, workers=1), A.run(items, workers=2)


def test_the_split_run_reports_what_one_process_reports(runs):
    one, two = runs
    assert one["workers"] == 1 and two["workers"] == 2
    assert _comparable(one) == _comparable(two)
    assert A.render_md(one).split("\n", 3)[3] == A.render_md(two).split("\n", 3)[3]   # all but the time line


def test_results_are_scored_in_item_order(runs):
    one, two = runs
    assert [p["id"] for p in two["per_item"]] == IDS == [p["id"] for p in one["per_item"]]
    first, second = two["per_item"][0], two["per_item"][1]
    # the precondition that makes the test above able to catch a merge in completion order
    assert first["seconds"] > second["seconds"], two["per_item"]


def test_the_subset_reaches_every_surface_and_shape(runs):
    names = runs[0]["per_attack"].keys()
    assert any(k.startswith("mc:") for k in names) and any(k.startswith("step:") for k in names)
    assert any(not k.startswith(("mc:", "step:")) for k in names)
    assert {"drop_set_element", "close_interval_endpoint", "value_bump"} <= set(names)
    assert runs[0]["n_attacks"] == sum(p["attacks"] for p in runs[0]["per_item"]) > 0


def test_a_worker_error_fails_the_sweep(evalset_items):
    """An item that raises must stop the sweep in a worker as it does in one process, not vanish
    from the report."""
    broken = {"id": "bozuk-001"}                      # no problem, no solution
    good = next(it for it in evalset_items if it["id"] == IDS[1])
    for workers in (1, 2):
        with pytest.raises(KeyError, match="problem_ir"):   # the worker's own error, not a later one
            A.run([good, broken], workers=workers)


def test_worker_count(tmp_path, monkeypatch):
    assert 1 <= A.default_workers() <= A.DEFAULT_WORKERS == 4
    for cpus, expected in ((2, 2), (1, 1), (None, 1), (16, 4)):   # never more workers than CPUs
        monkeypatch.setattr(os, "process_cpu_count", lambda: cpus, raising=False)
        assert A.default_workers() == expected, cpus
    assert A.run([], workers=4)["workers"] == 1       # never more workers than items
    with pytest.raises(SystemExit):                   # bounded and kept out of reports/ should the check go
        A.main(["--workers", "0", "--limit", "1", "--out", str(tmp_path)])


FAKE_ITEMS = [{"id": "a"}, {"id": "b"}, {"id": "c"}]


def test_a_result_the_load_decided_fails_the_sweep():
    """A sandbox timeout in a worker sends the item through again alone; different rows there mean
    the load decided a verdict, and the sweep stops instead of reporting it."""
    with pytest.raises(A.LoadDependentResult, match="a: bir işçide 1 sandbox zaman aşımı"):
        A.run(FAKE_ITEMS, workers=2, attack=adversarial_fakes.load_dependent)
    one = A.run(FAKE_ITEMS, workers=1, attack=adversarial_fakes.load_dependent)   # one process: the reference
    assert one["rechecked"] == [] and one["sandbox_timeouts"] == 0


def test_a_recheck_that_agrees_is_kept_and_counted():
    two = A.run(FAKE_ITEMS, workers=2, attack=adversarial_fakes.load_independent)
    one = A.run(FAKE_ITEMS, workers=1, attack=adversarial_fakes.load_independent)
    assert two["rechecked"] == ["a", "b", "c"] and two["sandbox_restarts"] == 3
    assert two["sandbox_timeouts"] == 0 and two["sandbox_errors"] == 0
    assert [(p["sandbox_timeouts"], p["sandbox_restarts"], p["sandbox_errors"]) for p in two["per_item"]] == [(0, 1, 0)] * 3
    assert two["per_attack"] == one["per_attack"] and two["successes"] == one["successes"]


def test_a_base_verdict_the_load_decided_fails_the_sweep_even_without_attacks():
    """An item no attack applies to has no rows: the base verdict is compared too (review)."""
    with pytest.raises(A.LoadDependentResult, match="1 sandbox/katman hatası"):
        A.run(FAKE_ITEMS, workers=2, attack=adversarial_fakes.base_only)


def test_the_log_line_of_the_sweep(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_script_adv_note", ROOT / "scripts" / "check.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    report = tmp_path / "adversarial_results.json"
    report.write_text(json.dumps(A.run(FAKE_ITEMS, workers=2, attack=adversarial_fakes.load_independent)),
                      encoding="utf-8")
    assert check.adversarial_note(report) == ("    adversarial: 2 süreç · sandbox zaman aşımı 0 · yeniden başlatma 3 · "
                                              "sandbox/katman hatası 0 · tek başına yeniden denenen 3")
    assert check.adversarial_note(tmp_path / "yok.json") is None


def test_the_recheck_runs_after_the_pool_is_gone(tmp_path, monkeypatch):
    """"Alone" means alone: a recheck while the workers still ran reproduced their load (review)."""
    log = tmp_path / "log.txt"
    monkeypatch.setenv("ADV_FAKE_LOG", str(log))
    r = A.run([{"id": x} for x in "abcdef"], workers=2, attack=adversarial_fakes.logged)
    assert r["rechecked"] == ["a"]
    rows = [l.split() for l in log.read_text(encoding="utf-8").splitlines()]
    workers = [(float(s), float(e)) for where, _, s, e in rows if where == "worker"]
    main = [(float(s), float(e)) for where, _, s, e in rows if where == "main"]
    assert len(workers) == 6 and len(main) == 1
    assert main[0][0] >= max(e for _, e in workers)


def test_attack_item_counts_the_sandbox_timeouts_and_restarts(evalset_items, monkeypatch):
    import mathverify.sandbox
    import mathverify.verifier
    sb = types.SimpleNamespace(timeouts=5, restarts=7)            # counters from earlier items
    calls = []

    def verify(ir, sol):
        calls.append(1)
        sb.timeouts += 1
        sb.restarts += 2
        layer = types.SimpleNamespace(flags=["layer_exception"] if len(calls) % 3 == 0 else [])
        return types.SimpleNamespace(verdict="CORRECT", flags=["cas_error"] if len(calls) == 1 else [], layers=[layer])

    monkeypatch.setattr(mathverify.sandbox, "get_sandbox", lambda: sb)
    monkeypatch.setattr(mathverify.verifier, "verify", verify)
    r = A.attack_item(next(it for it in evalset_items if it["id"] == IDS[1]))
    assert len(calls) > 1 and r["sandbox_timeouts"] == len(calls) and r["sandbox_restarts"] == 2 * len(calls)
    assert r["sandbox_errors"] == 1 + len(calls) // 3             # call 1: cas_error; every third: layer_exception


def _marked(marker: bytes) -> list[int]:
    pids = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                if marker in Path(f"/proc/{d}/environ").read_bytes():
                    pids.append(int(d))
            except OSError:
                pass
    return pids


def _busy(pid: int) -> bool:
    """Has the process used more than a second of CPU (utime, /proc/<pid>/stat field 14)?"""
    try:
        return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[11]) > os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError):
        return False


@pytest.mark.skipif(not Path("/proc/self/environ").exists(), reason="needs /proc to find the processes")
def test_workers_do_not_outlive_a_killed_sweep(tmp_path):
    """Killed by PID, the sweep's process never shuts its pool down; the workers and their sandboxes
    must end by themselves, not wait for ever (3 + 3 were left in review, one sandbox at 86% CPU).
    The sandboxes are made to compute first: a sandbox still starting ends by itself when its
    worker goes, so killing early proved nothing about killing the children (review)."""
    marker = f"ADV_KILL_TEST={uuid.uuid4().hex}"
    script = tmp_path / "sweep.py"
    script.write_text(
        "import sys\n"
        f"sys.path[:0] = [{str(ROOT)!r}, {str(ROOT / 'src')!r}, {str(ROOT / 'tests')!r}]\n"
        "from harness import adversarial as A\n"
        "import adversarial_fakes\n"
        "if __name__ == '__main__':\n"
        "    A.run([{'id': 'a'}, {'id': 'b'}], workers=2, attack=adversarial_fakes.spin)\n", encoding="utf-8")
    key, value = marker.split("=")
    parent = subprocess.Popen([sys.executable, str(script)], env=dict(os.environ, **{key: value}),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tag = marker.encode()
    try:
        deadline = time.monotonic() + 120
        while sum(_busy(p) for p in _marked(tag) if p != parent.pid) < 2:     # both sandboxes spinning
            assert parent.poll() is None and time.monotonic() < deadline, "the sandboxes did not start computing"
            time.sleep(0.5)
        os.kill(parent.pid, signal.SIGKILL)
        parent.wait()
        deadline = time.monotonic() + 30
        while _marked(tag) and time.monotonic() < deadline:
            time.sleep(0.5)
        assert _marked(tag) == []
    finally:
        for pid in _marked(tag):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        if parent.poll() is None:
            parent.kill()
