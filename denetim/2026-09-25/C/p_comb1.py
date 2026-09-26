from h import *
import math, itertools
from fractions import Fraction
if __name__ == "__main__":
    # 1. multiset_combination with space > ENUM_CAP: MC sampling is not uniform over multisets
    sp_ = {"structure": "multiset_combination", "n": 100, "k": 5}
    size = math.comb(104, 5)
    truth = math.comb(100, 5)   # all-distinct multisets = ordinary 5-subsets
    print("size", size, "truth all-distinct", truth, "p", truth/size)
    pir = ir("count_structures", {"space": sp_, "predicate": "len(set(t)) == 5"}, answer_shape="count")
    run("mscomb_mc_correct", pir, sol(str(truth), "count"), "UNKNOWN", show=True)
    # probability version
    pir2 = ir("probability", {"space": sp_, "event": "len(set(t)) == 5"})
    run("mscomb_mc_prob_correct", pir2, sol(f"{truth}/{size}"), "UNKNOWN", show=True)
    # 2. arrangements of a word with repeated letters (ANKARA): distinct arrangements = 6!/3! = 120
    pir3 = ir("count_structures", {"space": {"structure": "arrangement_all", "elements": list("ANKARA")}, "predicate": ""}, answer_shape="count")
    distinct = len(set(itertools.permutations("ANKARA")))
    print("distinct ANKARA arrangements", distinct)
    run("ankara_720", pir3, sol("720", "count"), None, show=True)
    run("ankara_120", pir3, sol("120", "count"), None, show=True)
    # 3. combinations from multiset elements
    pir4 = ir("count_structures", {"space": {"structure": "combination", "elements": [1,1,2,3], "k": 2}, "predicate": ""}, answer_shape="count")
    print("distinct 2-subsets of multiset {1,1,2,3}:", len(set(itertools.combinations([1,1,2,3],2))))
    run("mcomb_6", pir4, sol("6", "count"), None)
    run("mcomb_4", pir4, sol("4", "count"), None)
    # 4. permutation with k > n: size 0 -> probability 0/0
    pir5 = ir("probability", {"space": {"structure": "permutation", "n": 3, "k": 5}, "event": ""})
    run("perm_k_gt_n_p1", pir5, sol("1"), "UNKNOWN", show=True)
    run("perm_k_gt_n_p0", pir5, sol("0"), "UNKNOWN", show=True)
    # 5. probability decimals
    pir6 = ir("probability", {"space": {"structure": "sequence", "elements": [1,2,3,4,5,6], "k": 1}, "event": "t[0] <= 2"})
    run("p_third_exact", pir6, sol("1/3"), "CORRECT")
    run("p_third_033", pir6, sol("0.33"), "INCORRECT")
    run("p_third_0333", pir6, sol("0.333333333333333"), None, show=True)
    run("p_third_pct", pir6, sol("%33.3"), None)
    run("p_neg", pir6, sol("-1/3"), "INCORRECT")
    run("p_gt1", pir6, sol("4/3"), "INCORRECT")
    run("p_complex", pir6, sol("1/3 + 0*I"), "CORRECT")
    run("p_sqrt", pir6, sol("sqrt(1/9)"), "CORRECT")
    run("p_near", pir6, sol("1/3 + 10**(-40)"), "INCORRECT", show=True)
