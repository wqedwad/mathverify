"""L8 rule fusion (handoff §4 fusion rules, §11/2, §11/10, D6)."""
from mathverify.fuse import fuse, THRESH_POS
from mathverify.types import LayerResult


def L(layer, verdict, conf=0.99, hard=True, primary=True, flags=None, fbs=None):
    return LayerResult(layer=layer, verdict=verdict, confidence=conf, hard=hard, evidence={},
                       latency_ms=1.0, primary=primary, first_bad_step=fbs, flags=flags or [])


def test_hard_fail_vetoes_everything():
    r = fuse([L("certify.algebra", "pass"), L("steps.refute", "fail", 0.97, primary=False, fbs=2)])
    assert r["verdict"] == "INCORRECT" and r["first_bad_step"] == 2


def test_primary_pass_grounds_correct():
    r = fuse([L("certify.algebra", "pass")])
    assert r["verdict"] == "CORRECT" and r["confidence"] >= THRESH_POS


def test_non_primary_pass_alone_is_unknown():
    r = fuse([L("mc.consistency", "pass", primary=False)])
    assert r["verdict"] == "UNKNOWN"


def test_soft_signal_alone_never_decides():
    r = fuse([L("llm.judge", "pass", 0.99, hard=False, primary=False)])
    assert r["verdict"] == "UNKNOWN"
    r = fuse([L("llm.judge", "fail", 0.99, hard=False, primary=False)])
    assert r["verdict"] == "UNKNOWN"


def test_contradiction_between_primary_certificates_is_unknown():
    r = fuse([L("certify.algebra", "pass"), L("certify.wordproblem", "fail")])
    assert r["verdict"] == "UNKNOWN" and "layer_contradiction" in r["flags"]


def test_ir_incomplete_flag_blocks_correct():
    r = fuse([L("certify.algebra", "pass"), L("certify.wordproblem", "unknown", 0.0, hard=False, primary=False,
                                                flags=["ir_incomplete"])])
    assert r["verdict"] == "UNKNOWN"


def test_low_confidence_fail_abstains():
    r = fuse([L("sanity", "fail", 0.5, primary=False)])
    assert r["verdict"] == "UNKNOWN"


def test_no_averaging_noisy_or():
    r = fuse([L("certify.algebra", "pass", 0.9), L("certify.wordproblem", "pass", 0.9)])
    assert r["confidence"] > 0.9            # 1-(0.1*0.1)=0.99, not the average 0.9


def test_timeout_penalty_applied():
    r1 = fuse([L("certify.algebra", "pass", 0.92)])
    r2 = fuse([L("certify.algebra", "pass", 0.92, flags=["cas_timeout"])])
    assert r2["confidence"] < r1["confidence"]


def test_everything_unknown_is_unknown():
    r = fuse([L("certify.limits", "unknown", 0.0, hard=False, primary=False)])
    assert r["verdict"] == "UNKNOWN" and r["confidence"] == 0.0
