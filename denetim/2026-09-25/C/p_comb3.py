from h import *
import time
if __name__ == "__main__":
    base = {"structure": "combination", "n": 5, "k": 2}
    for label, pred in [("bigpow", "2**(10**9) > 0"),
                        ("biglist", "len([0]*(10**10)) > 0"),
                        ("longrange", "sum(range(10**11)) > 0"),
                        ("deep_paren", "(" * 300 + "1" + ")" * 300 + " == 1"),
                        ("nested_gen", "sum(1 for a in range(10**4) for b in range(10**4)) > 0"),
                        ("str_mul", "len(str(t) * (10**10)) > 0")]:
        t0 = time.time()
        pir = ir("count_structures", {"space": base, "predicate": pred}, answer_shape="count")
        run(label, pir, sol("10", "count"), None, show=True)
        print("   elapsed %.1fs" % (time.time() - t0))
