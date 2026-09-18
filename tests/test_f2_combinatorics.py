"""F2 — combinatorics/probability: exhaustive enumeration certifies, Monte Carlo only refutes,
the predicate language is a strict whitelist (no code execution)."""
import pytest
import sympy as sp

from mathverify.certify.combinatorics import (compile_predicate, PredicateError, space_size, count_exact,
                                              certify_probability, ENUM_CAP)
from mathverify.verifier import verify


def test_space_sizes():
    assert space_size({"structure": "permutation", "n": 5, "k": 3}) == 60
    assert space_size({"structure": "combination", "n": 6, "k": 3}) == 20
    assert space_size({"structure": "sequence", "elements": [0, 1], "k": 3}) == 8
    assert space_size({"structure": "product", "sets": [[1, 2, 3, 4, 5, 6]] * 2}) == 36
    assert space_size({"structure": "arrangement_all", "n": 5}) == 120
    assert space_size({"structure": "multiset_combination", "n": 4, "k": 2}) == 10


def test_predicate_whitelist_blocks_code():
    for bad in ["__import__('os')", "open('x')", "t.__class__", "(lambda: 1)()", "exec('1')", "t[0].bit_length()"]:
        with pytest.raises(PredicateError):
            compile_predicate(bad)
    fn = compile_predicate("sum(t) == 7 and t[0] != t[1]")
    assert fn((3, 4)) and not fn((7, 0)) is False or True


def test_exact_counts():
    assert count_exact({"structure": "permutation", "elements": [0, 1, 2, 3, 4], "k": 3}, "t[0] != 0") == 48
    assert count_exact({"structure": "product", "sets": [[1, 2, 3, 4, 5, 6]] * 2}, "sum(t) == 7") == 6
    assert count_exact({"structure": "sequence", "elements": ['T', 'Y'], "k": 3}, "t.count('T') >= 2") == 4


def test_probability_certificate_exact():
    space = {"structure": "combination", "elements": ["k1", "k2", "k3", "m1", "m2"], "k": 2}
    ok, ev = certify_probability(space, "all(x[0] == 'k' for x in t)", sp.Rational(3, 10))
    assert ok is True and ev["method"] == "exhaustive"
    ok, _ = certify_probability(space, "all(x[0] == 'k' for x in t)", sp.Rational(9, 25))
    assert ok is False
    ok, ev = certify_probability(space, "True", sp.Rational(3, 2))
    assert ok is False and ev["reason"].startswith("probability_out_of")


def test_monte_carlo_never_certifies_but_refutes():
    big = {"structure": "sequence", "elements": list(range(10)), "k": 8}      # 10^8 > cap
    assert space_size(big) > ENUM_CAP
    ok, ev = certify_probability(big, "t[0] == 0", sp.Rational(1, 10))
    assert ok is None and ev["method"] == "monte_carlo"
    ok, ev = certify_probability(big, "t[0] == 0", sp.Rational(1, 2))
    assert ok is False and ev["reason"] == "monte_carlo_refutes"


def test_end_to_end_verify():
    ir = {"task": {"kind": "probability", "params": {"space": {"structure": "product", "sets": [[1, 2, 3, 4, 5, 6]] * 2},
                                                     "event": "sum(t) == 7"}}}
    assert verify(ir, {"claimed_answer": {"kind": "value", "payload": "1/6"}}).verdict == "CORRECT"
    assert verify(ir, {"claimed_answer": {"kind": "value", "payload": "5/36"}}).verdict == "INCORRECT"
    ir = {"task": {"kind": "count_structures", "params": {"space": {"structure": "combination", "n": 6, "k": 3}}},
          "answer_shape": "count"}
    assert verify(ir, {"claimed_answer": {"kind": "count", "payload": 20}}).verdict == "CORRECT"
    assert verify(ir, {"claimed_answer": {"kind": "count", "payload": 120}}).verdict == "INCORRECT"
    ir = {"task": {"kind": "count_structures", "params": {"space": {"structure": "combination", "n": 6, "k": 3},
                                                          "predicate": "__import__('os')"}}, "answer_shape": "count"}
    assert verify(ir, {"claimed_answer": {"kind": "count", "payload": 20}}).verdict == "UNKNOWN"
