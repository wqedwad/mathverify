"""The vacuity and no-hypothesis audits of formal/prove.py need a real Lean verdict.

Both probes used to be read as `bool(r.clean)`, so a probe that TIMED OUT (or hit a dead REPL)
counted as "did not compile": hypotheses not contradictory, hypotheses used, audit clean. With a
fake Lean that compiles the vacuous junk statement `x = 2 from 1/(x-2) = 0` and times out on both
probes, prove_statement returned audit clean True and l7_layer a primary `pass` (0.995). These
tests pin the fail-closed rule without the toolchain: fake Lean clients script every answer, and
the transport cases drive LeanClient._send_raw against a child process standing in for the REPL.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from mathverify.formal import build_statement
from mathverify.formal import prove as P
from mathverify.formal.lean_client import LeanClient, LeanResult, LeanUnavailable
from mathverify.formal.statement import AUTOIMPLICIT_OFF

TIMEOUT = "lean timeout after 45s"
SAFE_AXIOMS_INFO = "'mv_claim' depends on axioms: [propext, Classical.choice, Quot.sound]"


def _ir(kind, params, vars_=(), givens=(), shape="scalar"):
    return {"task": {"kind": kind, "params": params}, "vars": [dict(v) for v in vars_],
            "givens": list(givens), "answer_shape": shape}


def _junk_stmt():
    """The reviewer's statement: the hypotheses 1/(x-2) = 0 and x - 2 ≠ 0 contradict each other."""
    from harness.run_lean import JUNK_PROBES
    _, ir, ca = next(p for p in JUNK_PROBES if p[0] == "x = 2 from 1/(x-2) = 0")
    st = build_statement(ir, ca)
    assert st is not None and st.vacuity_probe() and st.no_hyp_probe("  norm_num")
    return st


def _hyp_stmt():
    """A legitimate statement with a hypothesis: x - 2 = 0 ⊢ x = 2."""
    st = build_statement(_ir("evaluate", {"expr": "x"}, [{"name": "x"}], ["x - 2 = 0"]),
                         {"kind": "value", "payload": "2"})
    assert st is not None and st.hypotheses and st.vacuity_probe() and st.no_hyp_probe("  linarith")
    return st


def _ok(env=None):
    return LeanResult(ok=True, env=env)


def _lean_error(msg="linarith failed"):
    return LeanResult(ok=False, errors=[msg])


def _timed_out():
    return LeanResult(ok=False, errors=[TIMEOUT], timed_out=True)


class FakeLean:
    """Scripted Lean: the theorem compiles, `#print axioms` answers with the safe axioms, and the
    two audit probes answer whatever the test gives (a LeanResult, or an exception to raise)."""

    def __init__(self, name, *, vacuity=None, nohyp=None, axioms=None):
        self.name = name
        self.answers = {"vacuity": vacuity, "nohyp": nohyp,
                        "axioms": axioms if axioms is not None else LeanResult(ok=True, infos=[SAFE_AXIOMS_INFO])}
        self.calls: list[str] = []

    def _kind(self, code: str) -> str:
        if code.startswith("#print axioms"):
            return "axioms"
        code = code.removeprefix(AUTOIMPLICIT_OFF)          # every statement command opens with it
        if code.startswith(f"theorem {self.name}_vacuity"):
            return "vacuity"
        if code.startswith(f"theorem {self.name}_nohyp"):
            return "nohyp"
        return "proof"

    def run(self, code, timeout=120.0, env=-1):
        kind = self._kind(code)
        self.calls.append(kind)
        if kind == "proof":
            return _ok(env=7)
        ans = self.answers[kind]
        assert ans is not None, f"unexpected {kind} call"
        if isinstance(ans, BaseException):
            raise ans
        return ans


def _prove(stmt, lean):
    return P.prove_statement(stmt, use_model=False, lean=lean, tactic_timeout=45)


# ------------------------------------------------------------------ the reviewer's case
def test_both_probes_timed_out_on_the_vacuous_junk_statement_is_not_clean():
    st = _junk_stmt()
    lean = FakeLean(st.name, vacuity=_timed_out(), nohyp=_timed_out())
    r = _prove(st, lean)
    assert lean.calls == ["proof", "axioms", "vacuity", "nohyp"]
    assert r["proved"] is True
    a = r["audit"]
    assert a["clean"] is False
    assert a["unanswered"] == ["vacuity", "no_hyp"]
    assert a["hypotheses_contradictory"] is None and a["provable_without_hypotheses"] is None
    assert a["vacuity_probe_errors"] == [TIMEOUT] and a["no_hyp_probe_errors"] == [TIMEOUT]
    assert a["axioms_ok"] and a["sorry_free"]            # only the unanswered probes fail it


def test_l7_layer_gives_no_certificate_when_the_audit_timed_out(monkeypatch):
    """The layer result the fusion sees: before the fix this was a primary pass at 0.995."""
    from harness.run_lean import JUNK_PROBES
    from mathverify.fuse import fuse
    _, ir, ca = next(p for p in JUNK_PROBES if p[0] == "x = 2 from 1/(x-2) = 0")
    st = _junk_stmt()
    monkeypatch.setattr(P, "get_lean", lambda: FakeLean(st.name, vacuity=_timed_out(), nohyp=_timed_out()))
    lr, rec = P.l7_layer(ir, {"claimed_answer": ca, "steps": []}, use_model=False, tactic_timeout=45)
    assert rec["proved"] and not rec["audit"]["clean"]
    assert lr.verdict == "unknown" and not lr.primary and "lean_audit_failed" in lr.flags
    assert lr.evidence["reason"] == "audit_failed"
    assert fuse([lr])["verdict"] == "UNKNOWN"


# ------------------------------------------------------------------ one probe unanswered
@pytest.mark.parametrize("no_verdict", [
    _timed_out(),
    LeanResult(ok=False, errors=["empty reply (REPL died)"]),
    LeanResult(ok=False, errors=["write failed: [Errno 32] Broken pipe"]),
    LeanResult(ok=False, errors=["bad JSON from REPL: Expecting value: {"]),
    LeanResult(ok=False),                                   # failure with no error at all
], ids=["timeout", "died", "write_failed", "bad_json", "no_error"])
def test_unanswered_vacuity_probe_fails_the_audit(no_verdict):
    st = _hyp_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=no_verdict, nohyp=_lean_error()))
    a = r["audit"]
    assert a["unanswered"] == ["vacuity"] and a["hypotheses_contradictory"] is None
    assert a["provable_without_hypotheses"] is False       # the other probe was answered
    assert a["clean"] is False


@pytest.mark.parametrize("no_verdict", [
    _timed_out(),
    LeanResult(ok=False, errors=["empty reply (REPL died)"]),
    LeanResult(ok=False, errors=["write failed: [Errno 32] Broken pipe"]),
    LeanResult(ok=False, errors=["bad JSON from REPL: Expecting value: {"]),
    LeanResult(ok=False),
], ids=["timeout", "died", "write_failed", "bad_json", "no_error"])
def test_unanswered_no_hyp_probe_fails_the_audit(no_verdict):
    st = _hyp_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=_lean_error(), nohyp=no_verdict))
    a = r["audit"]
    assert a["unanswered"] == ["no_hyp"] and a["provable_without_hypotheses"] is None
    assert a["hypotheses_contradictory"] is False
    assert a["clean"] is False


# ------------------------------------------------------------------ real answers: unchanged
def test_both_probes_rejected_by_lean_is_clean():
    st = _hyp_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=_lean_error("linarith failed"),
                            nohyp=_lean_error("unsolved goals")))
    a = r["audit"]
    assert a["clean"] is True and a["unanswered"] == []
    assert a["hypotheses_contradictory"] is False and a["provable_without_hypotheses"] is False
    assert a["vacuity_probe_errors"] == ["linarith failed"] and a["no_hyp_probe_errors"] == ["unsolved goals"]


def test_a_real_error_next_to_a_timeout_is_a_verdict():
    """Same rule as harness.run_lean.attempt_answered: any real Lean error counts as an answer."""
    st = _hyp_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=LeanResult(ok=False, errors=[TIMEOUT, "unsolved goals"]),
                            nohyp=_lean_error()))
    assert r["audit"]["clean"] is True and r["audit"]["unanswered"] == []


def test_contradictory_hypotheses_still_fail_the_audit():
    st = _junk_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=_ok(), nohyp=_lean_error()))
    a = r["audit"]
    assert a["hypotheses_contradictory"] is True and a["unanswered"] == [] and a["clean"] is False


def test_provable_without_hypotheses_still_fails_the_audit():
    st = _hyp_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=_lean_error(), nohyp=_ok()))
    a = r["audit"]
    assert a["provable_without_hypotheses"] is True and a["unanswered"] == [] and a["clean"] is False


def test_statement_without_hypotheses_runs_no_probe_and_stays_clean():
    st = build_statement(_ir("evaluate", {"expr": "gcd(84, 120)"}), {"kind": "value", "payload": "12"})
    assert st is not None and not st.hypotheses
    lean = FakeLean(st.name)
    r = _prove(st, lean)
    assert lean.calls == ["proof", "axioms"]
    a = r["audit"]
    assert a["clean"] is True and a["unanswered"] == []
    assert a["hypotheses_contradictory"] is False and a["provable_without_hypotheses"] is None


def test_timed_out_axiom_print_still_fails_the_audit():
    st = _hyp_stmt()
    r = _prove(st, FakeLean(st.name, vacuity=_lean_error(), nohyp=_lean_error(), axioms=_timed_out()))
    a = r["audit"]
    assert a["axioms"] == ["<unknown>"] and a["axioms_ok"] is False and a["clean"] is False


# ------------------------------------------------------------------ Lean gone during the audit
def test_lean_lost_during_the_vacuity_probe_is_recorded_not_raised():
    """REPL killed by a timeout and not respawnable: LeanClient.run raises LeanUnavailable on the
    next call. prove_statement used to let that escape from the audit (crashing a run_lean
    sweep); now the audit fails and the record says Lean was not reached."""
    from harness.run_lean import lean_fields
    st = _hyp_stmt()
    gone = LeanUnavailable("REPL did not start: ['boom']")
    r = _prove(st, FakeLean(st.name, vacuity=gone, nohyp=gone))
    a = r["audit"]
    assert a["clean"] is False and a["unanswered"] == ["vacuity", "no_hyp"]
    assert any(e.startswith("lean_unavailable") for e in r["errors"])
    assert lean_fields(r)["lean_reached"] is False


def test_lean_lost_before_the_axiom_print_is_recorded_not_raised():
    st = _hyp_stmt()
    gone = LeanUnavailable("REPL did not start: ['boom']")
    r = _prove(st, FakeLean(st.name, vacuity=gone, nohyp=gone, axioms=gone))
    a = r["audit"]
    assert a["axioms_ok"] is False and a["clean"] is False
    assert a["axioms_raw"].startswith("lean_unavailable")
    assert sum(e.startswith("lean_unavailable") for e in r["errors"]) == 3


# ------------------------------------------------------------------ the classification itself
def test_no_verdict_prefixes_match_the_harness():
    from harness import run_lean
    assert P.NO_VERDICT == run_lean.NO_VERDICT


@pytest.mark.parametrize("r, judged", [
    (_ok(), True),
    (_lean_error(), True),
    (LeanResult(ok=False, errors=[TIMEOUT, "unsolved goals"]), True),
    (_timed_out(), False),
    (LeanResult(ok=False, errors=["empty reply (REPL died)"]), False),
    (LeanResult(ok=False, errors=["write failed: [Errno 32] Broken pipe"]), False),
    (LeanResult(ok=False, errors=["bad JSON from REPL: Expecting value: {"]), False),
    (LeanResult(ok=False), False),
    (LeanResult(ok=True, sorries=[{"pos": 1}]), False),     # compiled with sorry, no error: fail closed
], ids=["compiled", "lean_error", "timeout_and_error", "timeout", "died", "write_failed", "bad_json",
        "no_error", "sorry_only"])
def test_lean_judged_matches_attempt_answered(r, judged):
    from harness import run_lean
    assert P.lean_judged(r) is judged
    assert run_lean.attempt_answered({"ok": r.clean, "errors": r.errors[:2]}) is judged


_FAKE_REPL = {  # child script standing in for the REPL -> did Lean judge the code?
    "compiled": ('print(json.dumps({"env": 1})); print("")', True),
    "lean_error": ('print(json.dumps({"messages": [{"severity": "error", "data": "linarith failed"}]})); print("")',
                   True),
    "timeout": ("time.sleep(60)", False),
    "died": ("sys.exit(0)", False),
    "bad_json": ('print("not json"); print("")', False),
    "repl_message": ('print(json.dumps({"message": "Unknown environment."})); print("")', False),
    "write_failed": (None, False),
}


@pytest.mark.parametrize("case", sorted(_FAKE_REPL))
def test_lean_judged_on_what_lean_client_really_returns(case):
    """NO_VERDICT must match the errors LeanClient._send_raw actually produces."""
    body, judged = _FAKE_REPL[case]
    script = ("import json, sys, time\n" + ("" if body is None else "sys.stdin.readline()\n" + body
                                           + "\nsys.stdout.flush()\ntime.sleep(5)\n"))
    extra = {"start_new_session": True} if sys.platform != "win32" else {}
    client = LeanClient()
    client._proc = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1, **extra)
    proc = client._proc
    try:
        if body is None:
            proc.wait(timeout=30)                    # gone before anything is sent
        r = client._send_raw({"cmd": "example : True := trivial", "env": 0}, timeout=3.0)
    finally:
        client._kill()
        try:
            proc.stdin.close()
        except OSError:
            pass
    assert P.lean_judged(r) is judged, (case, r.errors)
    assert r.timed_out is (case == "timeout")
