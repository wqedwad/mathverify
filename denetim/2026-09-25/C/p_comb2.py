from h import *
import itertools, time
from fractions import Fraction
if __name__ == "__main__":
    # dice: two dice, unordered outcome modelled as multiset_combination -> doubles
    pir = ir("probability", {"space": {"structure": "multiset_combination", "n": 6, "k": 2}, "event": "t[0] == t[1]"})
    truth_physical = Fraction(sum(1 for a in range(1,7) for b in range(1,7) if a == b), 36)
    print("physical P(doubles) =", truth_physical)
    run("dice_multiset_1_6", pir, sol("1/6"), None, show=True)
    run("dice_multiset_2_7", pir, sol("2/7"), None, show=True)
    # pitfall: t is a tuple; sorted(t) returns a list
    pir2 = ir("count_structures", {"space": {"structure": "permutation", "n": 4, "k": 3}, "predicate": "sorted(t) == t"}, answer_shape="count")
    truth_inc = sum(1 for t in itertools.permutations(range(1,5), 3) if list(t) == sorted(t))
    print("increasing 3-perms of 4:", truth_inc)
    run("sorted_eq_tuple_0", pir2, sol("0", "count"), None, show=True)
    run("sorted_eq_tuple_4", pir2, sol("4", "count"), None, show=True)
    # string elements with sum -> TypeError
    pir3 = ir("count_structures", {"space": {"structure": "sequence", "elements": ["1","2","3"], "k": 2}, "predicate": "sum(t) == 4"}, answer_shape="count")
    run("str_elements_sum", pir3, sol("3", "count"), None, show=True)
    # product with string sets
    pir4 = ir("probability", {"space": {"structure": "product", "sets": ["HT", "HT"]}, "event": "t.count('H') == 1"})
    run("product_strsets", pir4, sol("1/2"), "CORRECT")
    # count claimed as float/rational kinds
    pir5 = ir("count_structures", {"space": {"structure": "combination", "n": 5, "k": 2}, "predicate": ""}, answer_shape="count")
    run("count_float_json", pir5, sol(10.0, "count"), "CORRECT")
    run("count_float_json_bad", pir5, sol(10.5, "count"), "INCORRECT")
    run("count_value_kind", pir5, sol("binomial(5,2)"), "CORRECT")
    run("count_value_kind_bad", pir5, sol("21/2"), "INCORRECT")
    run("count_value_pow", pir5, sol("10**1"), "CORRECT")
    # arrangement_all with k given and big space: MC samples k-tuples, exact uses full perms
    pir6 = ir("count_structures", {"space": {"structure": "arrangement_all", "n": 12, "k": 3}, "predicate": "len(t) == 12"}, answer_shape="count")
    import math
    run("arr_all_k_mc", pir6, sol(str(math.factorial(12)), "count"), None, show=True)
