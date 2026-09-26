"""count_solutions brute force evaluates givens with lambdify('math') floats: 1/x + 1/y = 1/6 loses solutions."""
from _r import show
from fractions import Fraction as F
import itertools, sympy as sp
if __name__ == "__main__":
    gt = [(x, y) for x in range(1, 51) for y in range(1, 51) if F(1, x) + F(1, y) == F(1, 6)]
    print("GT (exact Fractions) 1/x+1/y=1/6, 1<=x,y<=50:", len(gt), gt)
    ir = {"task": {"kind": "count_solutions", "params": {"bounds": {"x": ["1", "50"], "y": ["1", "50"]}}},
          "vars": [{"name": "x", "domain": "positive_integer"}, {"name": "y", "domain": "positive_integer"}], "givens": ["1/x + 1/y = 1/6"]}
    show("claim 7 (wrong)", ir, {"claimed_answer": {"kind": "count", "payload": 7}, "steps": []}, False)
    show("claim 9 (right)", ir, {"claimed_answer": {"kind": "count", "payload": 9}, "steps": []}, True)
    gt2 = [(x, y) for x in range(0, 4) for y in range(0, 4) if F(x, 10) + F(y, 10) == F(3, 10)]
    print("GT x/10 + y/10 = 3/10, 0..3:", len(gt2), gt2)
    ir2 = {"task": {"kind": "count_solutions", "params": {"bounds": {"x": ["0", "3"], "y": ["0", "3"]}}},
           "vars": [{"name": "x", "domain": "nonneg_integer"}, {"name": "y", "domain": "nonneg_integer"}], "givens": ["x/10 + y/10 = 3/10"]}
    show("claim 0 (wrong)", ir2, {"claimed_answer": {"kind": "count", "payload": 0}, "steps": []}, False)
    gt3 = [(x, y) for x in range(0, 19) for y in range(0, 19) if sp.simplify(sp.sqrt(x) + sp.sqrt(y) - sp.sqrt(18)) == 0]
    print("GT sqrt(x)+sqrt(y)=sqrt(18), 0..18:", len(gt3), gt3)
    ir3 = {"task": {"kind": "count_solutions", "params": {"bounds": {"x": ["0", "18"], "y": ["0", "18"]}}},
           "vars": [{"name": "x", "domain": "nonneg_integer"}, {"name": "y", "domain": "nonneg_integer"}], "givens": ["sqrt(x) + sqrt(y) = sqrt(18)"]}
    show("claim 2 (wrong)", ir3, {"claimed_answer": {"kind": "count", "payload": 2}, "steps": []}, False)
