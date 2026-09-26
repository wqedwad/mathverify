from common import *
import sympy as sp, itertools
from fractions import Fraction as Fr

def cs(givens, bounds, claim, truth_ok, vars_=None, name=""):
    vs = vars_ or [{"name": k, "domain": "integer"} for k in bounds]
    return run(f"count_solutions[{name or givens}]={claim}", ir("count_solutions", {"bounds": bounds}, vars_=vs, givens=givens, shape="count"),
               sol("count", claim), truth_ok)

def exact_count(pred, ranges):
    return sum(1 for t in itertools.product(*ranges) if pred(*t))

if __name__ == "__main__":
    # float rounding: x/10 + y/10 = 3/10 ; exact: x + y = 3, x,y in 0..3 -> 4 solutions
    t = exact_count(lambda x, y: Fr(x, 10) + Fr(y, 10) == Fr(3, 10), [range(0, 4)] * 2)
    print("exact truth x/10+y/10=3/10:", t)
    cs(["x/10 + y/10 = 3/10"], {"x": ["0", "3"], "y": ["0", "3"]}, t, True)
    for k in range(0, 5):
        if k != t: cs(["x/10 + y/10 = 3/10"], {"x": ["0", "3"], "y": ["0", "3"]}, k, False)
    # 0.1*x + 0.2*y = 0.3 (decimals -> rationals by parser)
    t = exact_count(lambda x, y: Fr(1, 10)*x + Fr(2, 10)*y == Fr(3, 10), [range(-5, 6)] * 2)
    print("exact truth 0.1x+0.2y=0.3:", t)
    for k in range(max(0, t-3), t+2):
        cs(["0.1*x + 0.2*y = 0.3"], {"x": ["-5", "5"], "y": ["-5", "5"]}, k, k == t)
    # sqrt(x) + sqrt(y) = sqrt(18), x,y in 0..18 ; exact truth: (0,18),(2,8),(8,2),(18,0) -> 4
    def pred(x, y):
        return sp.simplify(sp.sqrt(x) + sp.sqrt(y) - sp.sqrt(18)) == 0
    t = exact_count(pred, [range(0, 19)] * 2)
    print("exact truth sqrt:", t)
    for k in range(0, 6):
        cs(["sqrt(x) + sqrt(y) = sqrt(18)"], {"x": ["0", "18"], "y": ["0", "18"]}, k, k == t)
    # x/3 + y/7 = 1 with x,y in 0..21  -> exact: 7x + 3y = 21 -> (0,7),(3,0)
    t = exact_count(lambda x, y: Fr(x, 3) + Fr(y, 7) == 1, [range(0, 22)] * 2)
    print("exact truth x/3+y/7=1:", t)
    for k in range(0, 4):
        cs(["x/3 + y/7 = 1"], {"x": ["0", "21"], "y": ["0", "21"]}, k, k == t)
    # 1/x + 1/y = 1/2 ; x,y in 1..10 -> (3,6),(4,4),(6,3) = 3
    t = exact_count(lambda x, y: Fr(1, x) + Fr(1, y) == Fr(1, 2), [range(1, 11)] * 2)
    print("exact truth 1/x+1/y=1/2:", t)
    for k in range(1, 5):
        cs(["1/x + 1/y = 1/2"], {"x": ["1", "10"], "y": ["1", "10"]}, k, k == t)
    # 1/x + 1/y = 1/6 on 1..50
    t = exact_count(lambda x, y: Fr(1, x) + Fr(1, y) == Fr(1, 6), [range(1, 51)] * 2)
    print("exact truth 1/x+1/y=1/6:", t)
    for k in range(t-2, t+2):
        cs(["1/x + 1/y = 1/6"], {"x": ["1", "50"], "y": ["1", "50"]}, k, k == t)
    # 1/x + 1/y + 1/z = 1 on 1..10
    t = exact_count(lambda x, y, z: Fr(1, x) + Fr(1, y) + Fr(1, z) == 1, [range(1, 11)] * 3)
    print("exact truth 1/x+1/y+1/z=1:", t)
    for k in range(t-2, t+2):
        cs(["1/x + 1/y + 1/z = 1"], {"x": ["1", "10"], "y": ["1", "10"], "z": ["1", "10"]}, k, k == t)
    # x/y = 0.1*(...)  written defs: x/x
    t = exact_count(lambda x: x != 0 and Fr(x, x) + x**2 <= 5, [range(-5, 6)])
    print("exact truth x/x + x^2 <= 5:", t)
    for k in (t, t+1):
        cs(["x/x + x**2 <= 5"], {"x": ["-5", "5"]}, k, k == t)
    # cube root negative: (x)**(1/3) with Python complex -> TypeError?
    cs(["x**(1/3) < 2"], {"x": ["-5", "5"]}, 5, None, name="cbrt_neg")
    cs(["root(x, 3) < 1"], {"x": ["-5", "5"]}, 5, None, name="root3_neg")
    cs(["cbrt(x) <= 1"], {"x": ["-5", "5"]}, 5, None, name="cbrt_fn")
    summary()
