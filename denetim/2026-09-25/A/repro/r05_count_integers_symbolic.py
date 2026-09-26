"""count_integers: a solution point whose integrality SymPy cannot decide is not counted, and an open endpoint
that equals an integer only non-structurally (log(8)/log(2) = 3) is counted as included."""
from _r import show
import sympy as sp
if __name__ == "__main__":
    print("GT: log(8)/log(2) =", sp.nsimplify(sp.log(8)/sp.log(2)), "; simplify ->", sp.simplify(sp.log(8)/sp.log(2)))
    print("GT: x*log(2) = log(8) <=> x = 3 -> 1 integer;  |x| < 3 -> {-2..2} -> 5 integers")
    ir1 = {"task": {"kind": "count_integers", "params": {"var": "x"}}, "vars": [{"name": "x", "domain": "integer"}], "givens": ["x*log(2) = log(8)"]}
    show("x*log(2)=log(8): claim 0 (wrong)", ir1, {"claimed_answer": {"kind": "count", "payload": 0}, "steps": []}, False)
    show("x*log(2)=log(8): claim 1 (right)", ir1, {"claimed_answer": {"kind": "count", "payload": 1}, "steps": []}, True)
    ir2 = {"task": {"kind": "count_integers", "params": {"var": "x"}}, "vars": [{"name": "x", "domain": "integer"}], "givens": ["Abs(x) < log(8)/log(2)"]}
    show("|x| < log(8)/log(2): claim 7 (wrong)", ir2, {"claimed_answer": {"kind": "count", "payload": 7}, "steps": []}, False)
    show("|x| < log(8)/log(2): claim 5 (right)", ir2, {"claimed_answer": {"kind": "count", "payload": 5}, "steps": []}, True)
