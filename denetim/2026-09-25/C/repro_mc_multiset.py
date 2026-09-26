# combinatorics Monte Carlo (space > 3e6): sample_space('multiset_combination') draws a SEQUENCE and sorts
# it, which is not uniform over multisets, while the exhaustive path counts each multiset once. The MC
# refuter therefore rejects the count that the verifier's own exact semantics would certify.
# Same inconsistency for arrangement_all with an explicit k (exact: full permutations; MC: k-samples).
import sys; sys.path.insert(0, __import__("os").environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
import math, itertools
from mathverify.verifier import verify

def V(kind, params, payload, pkind):
    pir = {"task": {"kind": kind, "params": params}, "vars": [], "givens": [], "answer_shape": "count" if kind == "count_structures" else "scalar"}
    r = verify(pir, {"claimed_answer": {"kind": pkind, "payload": payload}, "steps": []})
    return f"{r.verdict} {r.confidence:.2f} " + str([(l.layer, l.evidence.get('method'), l.evidence.get('reason')) for l in r.layers if l.layer.startswith('certify')])

if __name__ == "__main__":
    # independent ground truth: multisets of size k from n with all-distinct elements are exactly the k-subsets
    small = sum(1 for t in itertools.combinations_with_replacement(range(10), 3) if len(set(t)) == 3)
    print("brute force n=10,k=3:", small, "= C(10,3) =", math.comb(10, 3))
    n, k = 100, 5
    size, truth = math.comb(n + k - 1, k), math.comb(n, k)
    print(f"n={n},k={k}: space size {size} (> 3e6), all-distinct multisets = C(100,5) = {truth}, p = {truth/size:.4f}; "
          f"sequence-sampling estimate = {math.perm(n, k)/n**k:.4f}")
    sp_ = {"structure": "multiset_combination", "n": n, "k": k}
    print("count_structures claim", truth, "->", V("count_structures", {"space": sp_, "predicate": "len(set(t)) == 5"}, str(truth), "count"))
    print("probability claim", f"{truth}/{size}", "->", V("probability", {"space": sp_, "event": "len(set(t)) == 5"}, f"{truth}/{size}", "value"))
    sp2 = {"structure": "arrangement_all", "n": 12, "k": 3}
    print("arrangement_all n=12 (k=3 given), predicate len(t)==12, claim 12! ->",
          V("count_structures", {"space": sp2, "predicate": "len(t) == 12"}, str(math.factorial(12)), "count"))
