"""harness/run_solver.py (K4): a real solver's own solutions through the deterministic verifier,
labelled against the key only in the harness. Offline: the solver family is a scripted client."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest_llm import ScriptedClient, solution_reply
from harness import run_solver
from mathverify.llm import LLMCreditError, LLMResponse, clear_client_overrides, set_client_override
from mathverify.resolve.cross_family import _solver_user_prompt

ROOT = Path(__file__).resolve().parents[1]
ITEM = "tyt-prob-001"          # gold 16, options A..E = 12, 14, 16, 18, 20


@pytest.fixture
def items(evalset_items):
    return {it["id"]: it for it in evalset_items}


@pytest.fixture(autouse=True)
def _unpin():
    yield
    clear_client_overrides()


def _args(**kw):
    import argparse
    d = dict(family="meta", effort="xhigh", workers=1, max_cost=5.0)
    d.update(kw)
    return argparse.Namespace(**d)


def _solve(items, payload, item_id=ITEM):
    fake = ScriptedClient("meta", {"solver_meta": payload})
    set_client_override("meta", fake)
    return run_solver.run_item(items[item_id], _args()), fake


def test_the_solver_sees_the_question_and_never_the_key(items):
    it = items[ITEM]
    rec, fake = _solve(items, solution_reply("value", "16", option="C"))
    ((tag, user),) = fake.calls
    assert tag == "solver_meta"
    assert user == _solver_user_prompt(it["question_tr"], it["options"], it["problem_ir"])
    for k in ("gold_answer", "solution_is_correct", "first_bad_step"):
        assert k not in user


def test_the_items_own_steps_are_certified_and_labelled_right(items):
    sol = items[ITEM]["solution"]
    rec, _ = _solve(items, solution_reply("value", "16", option="C", steps=sol["steps"]))
    assert rec["verdict"] == "CORRECT" and rec["answer"] == "right" and rec["n_steps"] == 4


def test_a_wrong_answer_is_refuted_and_labelled_wrong(items):
    rec, _ = _solve(items, solution_reply("value", "14", option="B"))
    assert rec["verdict"] == "INCORRECT" and rec["answer"] == "wrong"


@pytest.mark.parametrize("payload,expected", [(solution_reply("value", "", option="C"), "right"),
                                              (solution_reply("value", "32/2"), "right"),
                                              (solution_reply("value", "", option="A"), "wrong"),
                                              (solution_reply("value", "a lot"), "undecided")])
def test_the_answer_label_reads_letters_and_equal_forms(items, payload, expected):
    rec, _ = _solve(items, payload)
    assert rec["answer"] == expected, rec.get("answer_why")


def test_no_json_is_recorded_as_no_solution(items):
    rec, _ = _solve(items, None)
    assert rec["solution"] is None and "no_json" in rec["errors"] and "answer" not in rec


class _Paid(ScriptedClient):
    def __init__(self, cost, fail_at=None):
        super().__init__("meta", {"solver_meta": solution_reply("value", "14")})
        self.cost, self.fail_at = cost, fail_at

    def complete(self, system, user, **kw):
        if self.fail_at is not None and len(self.calls) + 1 >= self.fail_at:
            self.calls.append((kw.get("tag"), user))
            raise LLMCreditError("insufficient balance")
        r = super().complete(system, user, **kw)
        return LLMResponse(**{**r.__dict__, "cost_usd": self.cost})


@pytest.mark.parametrize("client,why", [(_Paid(1.0), "spend cap reached: $2.00 >= $1.50"),
                                        (_Paid(0.0, fail_at=2), "LLMCreditError: insufficient balance")])
def test_the_run_stops_at_the_cap_and_on_a_billing_failure(tmp_path, client, why):
    set_client_override("meta", client)
    s = run_solver.main(["--family", "meta", "--max-cost", "1.5", "--limit", "5", "--workers", "1",
                         "--out", str(tmp_path)])
    assert s["aborted"] == why and s["n"] == 2 and len(client.calls) == 2, client.calls
    report = (tmp_path / "solver_meta_report.md").read_text(encoding="utf-8")
    assert f"**DURDURULDU: {why}**" in report
    data = json.loads((tmp_path / "solver_meta_results.json").read_text(encoding="utf-8"))
    assert data["summary"]["aborted"] == why and len(data["records"]) == 2


def test_the_report_counts_false_acceptances_and_lists_them():
    recs = [{"id": "a", "solution": {}, "verdict": "CORRECT", "answer": "right", "cost_usd": 0.1},
            {"id": "b", "solution": {}, "verdict": "CORRECT", "answer": "wrong", "claimed": "3", "gold": "4"},
            {"id": "c", "solution": {}, "verdict": "INCORRECT", "answer": "right", "first_bad_step": "s2"},
            {"id": "d", "solution": {}, "verdict": "INCORRECT", "answer": "wrong"},
            {"id": "e", "solution": {}, "verdict": "UNKNOWN", "answer": "undecided", "claimed": "x", "gold": "4",
             "answer_why": "not proved"},
            {"id": "f", "solution": None, "errors": ["no_json"]}]
    s = run_solver.summarize(recs)
    assert (s["n"], s["solved"], s["no_solution"], s["false_accepts"]) == (6, 5, 1, 1)
    assert s["pos_precision"] == 0.5 and s["coverage"] == 0.8 and s["wrong_answer_caught"] == 0.5
    assert s["solver_accuracy"] == 0.5
    s["total_ms"], s["aborted"] = 0.0, None
    md = run_solver.render_md(s, recs, _args())
    assert "- `b`: iddia `3`, anahtar `4`" in md and "- `c`: ilk kötü adım s2" in md
    assert "- `e` (UNKNOWN)" in md and "- `f`: no_json" in md


def test_calls_running_when_the_run_stops_are_still_reported(tmp_path):
    """Four workers: a call already in flight when the cap is reached is paid for, so it is in the
    report and its total; after the stop no call starts."""
    import threading
    gate = threading.Barrier(4)
    lock = threading.Lock()

    class _Slow(_Paid):
        started = 0

        def complete(self, system, user, **kw):
            with lock:
                _Slow.started += 1
                first = _Slow.started <= 4
            if first:
                gate.wait(timeout=30)                # the first four calls finish together
            return super().complete(system, user, **kw)

    client = _Slow(1.0)
    set_client_override("meta", client)
    s = run_solver.main(["--family", "meta", "--max-cost", "1.5", "--limit", "12", "--workers", "4",
                         "--out", str(tmp_path)])
    assert s["aborted"].startswith("spend cap reached")
    # every call made is reported and paid for; at most one per worker ran past the second cost
    assert s["n"] == len(client.calls) == _Slow.started and s["cost_usd"] == float(s["n"])
    assert 4 <= s["n"] <= 4 + 3, s["n"]
