# Principle 12 (definedness as written) in certify.series:
#  (a) series_sum: the k/k guard (written_undefined_in) is bypassed when the index variable is declared
#      positive_integer (as the evalset's diziler items do): Sum_{k=-1}^{1} k/k is certified = 3.
#  (b) recurrence_term / closed_form have no written-definedness guard at all: (n-3)/(n-3) cancels at
#      parse time, a(3) does not exist as written, a(5) = 5 is certified.
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify

def V(pir, payload):
    r = verify(pir, {"claimed_answer": {"kind": "value", "payload": payload}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f}"

if __name__ == "__main__":
    for vars_ in ([], [{"name": "k", "domain": "positive_integer"}]):
        pir = {"task": {"kind": "series_sum", "params": {"term": "k/k", "var": "k", "lo": -1, "hi": 1}},
               "vars": vars_, "givens": [], "answer_shape": "scalar"}
        print("series_sum k/k, k=-1..1, vars =", vars_ or "none", "-> claim 3:", V(pir, "3"),
              "  (ground truth: term 0/0 at k=0 is undefined -> expected UNKNOWN)")
    pir = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1)*(n-3)/(n-3) + 1",
                                                           "initial": {"1": "1"}, "index": 5, "var": "n"}},
           "vars": [{"name": "n", "domain": "positive_integer"}], "givens": [], "answer_shape": "scalar"}
    print("recurrence a(n) = a(n-1)*(n-3)/(n-3) + 1, a(1)=1, a(5) -> claim 5:", V(pir, "5"),
          "  (ground truth: at n=3 the factor is 0/0, a(3) and hence a(5) undefined as written)")
