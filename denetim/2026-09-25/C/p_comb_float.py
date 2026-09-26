# Predicates are evaluated with Python floats: 0.1 + 0.2 != 0.3, so an exhaustive "exact" count is wrong.
from h import *
from fractions import Fraction
import itertools
if __name__ == "__main__":
    els = [0.1, 0.2, 0.5]
    pir = ir("count_structures", {"space": {"structure": "sequence", "elements": els, "k": 2}, "predicate": "sum(t) == 0.3"}, answer_shape="count")
    truth = sum(1 for t in itertools.product([Fraction(1,10), Fraction(2,10), Fraction(5,10)], repeat=2) if sum(t) == Fraction(3,10))
    print("ground truth (exact rationals):", truth)
    run("float_pred_true2", pir, sol("2", "count"), "CORRECT", show=True)
    run("float_pred_wrong0", pir, sol("0", "count"), "INCORRECT", show=True)
    pp = ir("probability", {"space": {"structure": "sequence", "elements": els, "k": 2}, "event": "sum(t) == 0.3"})
    run("float_prob_true", pp, sol("2/9"), "CORRECT", show=True)
    run("float_prob_wrong0", pp, sol("0"), "INCORRECT", show=True)
