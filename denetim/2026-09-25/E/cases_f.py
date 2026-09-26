"""Batch F: closed `evaluate` goals whose literals carry no type ascription elaborate over ℕ
(Lean's default numeral type): `/` truncates, `2^(-1)` prints as `1 / 2` = 0."""
from cases_a import ir

CASES = [
    dict(label="F01 evaluate 7/2, claim 3", ir=ir("evaluate", {"expr": "7/2"}),
         claim={"kind": "value", "payload": "3"}, right=False, truth="7/2"),
    dict(label="F02 evaluate 1/2 + 1/3, claim 0", ir=ir("evaluate", {"expr": "1/2 + 1/3"}),
         claim={"kind": "value", "payload": "0"}, right=False, truth="5/6"),
    dict(label="F03 evaluate 10/4, claim 2", ir=ir("evaluate", {"expr": "10/4"}),
         claim={"kind": "value", "payload": "2"}, right=False, truth="5/2"),
    dict(label="F04 evaluate 2**(-1), claim 0", ir=ir("evaluate", {"expr": "2**(-1)"}),
         claim={"kind": "value", "payload": "0"}, right=False, truth="1/2"),
    dict(label="F05 evaluate 3, claim 7/2 (claim-side ℕ division)", ir=ir("evaluate", {"expr": "3"}),
         claim={"kind": "value", "payload": "7/2"}, right=False, truth="3"),
    dict(label="F06 evaluate (1 + 2)/(2*2), claim 0", ir=ir("evaluate", {"expr": "(1 + 2)/(2*2)"}),
         claim={"kind": "value", "payload": "0"}, right=False, truth="3/4"),
    dict(label="F07 evaluate 7/2, claim 7/2 (right)", ir=ir("evaluate", {"expr": "7/2"}),
         claim={"kind": "value", "payload": "7/2"}, right=True, truth="7/2"),
    dict(label="F08 evaluate 12/4 + 1, claim 4 (right)", ir=ir("evaluate", {"expr": "12/4 + 1"}),
         claim={"kind": "value", "payload": "4"}, right=True, truth="4"),
    dict(label="F09 evaluate 2**10/1000, claim 1", ir=ir("evaluate", {"expr": "2**10/1000"}),
         claim={"kind": "value", "payload": "1"}, right=False, truth="128/125"),
    dict(label="F10 evaluate (5/2)*2, claim 4", ir=ir("evaluate", {"expr": "(5/2)*2"}),
         claim={"kind": "value", "payload": "4"}, right=False, truth="5"),
]
