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


def _label(items, item_id, kind, payload, option=None):
    from harness.loader import split_for_verifier
    ir, key, labels = split_for_verifier(items[item_id])
    sol = {"claimed_answer": {"kind": kind, "payload": payload, "option": option}, "steps": []}
    return run_solver.answer_label(ir, sol, labels["gold_answer"], key["claimed_answer"]["kind"])


@pytest.mark.parametrize("payload,expected", [("x*log(x) - x", "right"), ("x*log(x) - x + C", "right"),
                                              ("x*log(x) - x + c", "right"), ("x*log(x) - x + 7", "right"),
                                              ("C + x*log(x) - x", "right"),
                                              ("x*log(x) + x", "wrong"), ("x*log(x) + x + C", "wrong")])
def test_an_antiderivative_is_labelled_up_to_the_constant_of_the_key(items, payload, expected):
    """The key is `x*log(x) - x + C`; `C` is the binomial in the parser's namespace and the key was
    never read, so every antiderivative stayed `undecided` (K4, 28 Sep 2026: ayt-int-005)."""
    label, why = _label(items, "ayt-int-005", "expression", payload)
    assert label == expected, why


@pytest.mark.parametrize("kind,payload,option,expected", [
    ("dne", None, "E", "right"), ("dne", None, None, "right"), ("value", "limit yoktur", None, "right"),
    ("value", "", "E", "right"), ("value", "DNE.", None, "right"),
    ("value", "1", "C", "wrong"), ("value", "0", None, "wrong"),
    ("infinite", "oo", None, "undecided")])
def test_a_limit_that_does_not_exist_is_labelled_whatever_its_wording(items, kind, payload, option, expected):
    """Key `DNE` (kind value), option E `limit yoktur` (ayt-lim-009 was `undecided`). A finite value
    against nonexistence is a proved difference; an infinite limit is a convention and not decided."""
    label, why = _label(items, "ayt-lim-009", kind, payload, option)
    assert label == expected, why


def test_a_constant_inside_the_key_is_set_to_zero(items):
    from harness.loader import split_for_verifier
    ir, _, _ = split_for_verifier(items["ayt-int-005"])
    sol = {"claimed_answer": {"kind": "expression", "payload": "x*log(x) - x"}, "steps": []}
    assert run_solver.answer_label(ir, sol, "C + x*log(x) - x", "expression")[0] == "right"


def test_nonexistence_against_a_finite_key_is_wrong_and_e_is_a_number(items):
    assert _label(items, "ayt-lim-001", "dne", None)[0] == "wrong"          # key 4
    assert _label(items, "ayt-lim-001", "value", "limit yoktur")[0] == "wrong"
    assert not run_solver._is_dne("value", "E") and not run_solver._is_dne("value", "limit yoktur ya da 2")


def test_one_request_is_never_paid_for_twice_at_once(tmp_path):
    """ayt-tur-003 and -010 ask the same question, so they send the same request; the second must
    wait for the first (whose answer the cache then serves) instead of paying in parallel. A
    different question still runs alongside."""
    import threading
    import time as _t
    lock, inflight, peak, overlap = threading.Lock(), {}, {}, []

    class _Tracked(ScriptedClient):
        def complete(self, system, user, **kw):
            with lock:
                inflight[user] = inflight.get(user, 0) + 1
                peak[user] = max(peak.get(user, 0), inflight[user])
                overlap.append(sum(inflight.values()))
            _t.sleep(0.3)
            with lock:
                inflight[user] -= 1
            return super().complete(system, user, **kw)

    client = _Tracked("meta", {"solver_meta": solution_reply("equation", "y = 2*x - 1", option="A")})
    set_client_override("meta", client)
    s = run_solver.main(["--family", "meta", "--max-cost", "5", "--workers", "3", "--out", str(tmp_path),
                         "--ids", "ayt-tur-003,ayt-tur-010,ayt-ana-002"])
    assert s["n"] == 3 and len(client.calls) == 3
    assert len(peak) == 2 and max(peak.values()) == 1, peak
    assert max(overlap) == 2                        # the other question ran alongside


def test_an_item_waiting_for_its_request_starts_no_call_after_a_stop(tmp_path, monkeypatch):
    """The first of two identical requests fails on billing and stops the run; the second, which
    was waiting for it, must not start a paid call of its own. The stop is set before the lock is
    released: a slow `_account` widens the window in which the other order let the call through."""
    import threading
    import time as _t
    first_in = threading.Event()
    real_account = run_solver._account

    def slow_account(args, rec):
        _t.sleep(0.3)
        real_account(args, rec)

    monkeypatch.setattr(run_solver, "_account", slow_account)

    class _Broke(ScriptedClient):
        def complete(self, system, user, **kw):
            self.calls.append((kw.get("tag"), user))
            first_in.set()
            _t.sleep(0.3)                           # the second item is now waiting on the lock
            raise LLMCreditError("insufficient balance")

    client = _Broke("meta", {})
    set_client_override("meta", client)
    s = run_solver.main(["--family", "meta", "--max-cost", "5", "--workers", "2", "--out", str(tmp_path),
                         "--ids", "ayt-tur-003,ayt-tur-010"])
    assert first_in.is_set() and len(client.calls) == 1, client.calls
    assert s["aborted"] == "LLMCreditError: insufficient balance" and s["n"] == 1


@pytest.mark.parametrize("payload,expected", [("70°", "right"), ("70", "right"), ("70 derece", "right"),
                                              ("80°", "wrong"), ("7*pi/18", "wrong")])
def test_an_angle_in_degrees_is_labelled_as_the_certificate_reads_it(items, payload, expected):
    """angle() is in degrees: `70°` is 70. The generic parser made it 7*pi/18 and three right answers
    became false acceptances in the report (tyt-geo-002/-008/-013, 28 Sep 2026)."""
    label, why = _label(items, "tyt-geo-002", "value", payload)
    assert label == expected, why


@pytest.mark.parametrize("payload,expected", [("{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "right"),
                                              ("{pi/6 + 2*n*pi, 5*pi/6 + 2*n*pi}", "right"),
                                              ("{pi/6 + 2*k*pi}", "undecided"),
                                              ("{5*pi/6 + 2*k*pi, pi/6 + 2*k*pi}", "right")])
def test_a_general_trig_solution_is_labelled_only_when_it_is_the_same_set(items, payload, expected):
    """The key's `k` was undeclared (ayt-trig-002). Two sets with a symbolic integer parameter are
    never proved different: that path would call {pi/6 + 2*n*pi} wrong against {pi/6 + 2*k*pi}."""
    label, why = _label(items, "ayt-trig-002", "set", payload)
    assert label == expected, why


@pytest.mark.parametrize("item,payload,expected", [
    ("uni-la-004", "(16, 14)", "right"), ("uni-la-004", "[16, 14]", "right"), ("uni-la-004", "(16, 15)", "wrong"),
    ("uni-la-004", "(16, 14, 0)", "wrong"),
    ("uni-la-003", "[1, 1]", "right"), ("uni-la-003", "(2, 2)", "undecided"), ("uni-la-003", "(1, -1)", "undecided")])
def test_a_tuple_answer_is_labelled_element_by_element(items, item, payload, expected):
    """(16,14) against (16, 14) was `undecided` (uni-la-*). An eigenvector is right up to a factor."""
    label, why = _label(items, item, "expression", payload)
    assert label == expected, why
