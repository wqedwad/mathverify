import time
from mathverify.verifier import verify

def show(tag, ir, sol):
    t0 = time.perf_counter()
    r = verify(ir, sol)
    print(f"{tag:<28} {r.verdict:<9} conf={r.confidence:.2f} {(time.perf_counter()-t0)*1000:.0f}ms  "
          + "; ".join(f"{l.layer}:{l.verdict}:{l.evidence.get('reason') or ''}" for l in r.layers if l.layer.startswith('certify')))

if __name__ == "__main__":
    # geometry: 3-4-5 triangle hypotenuse
    ir = {"task": {"kind": "synthetic_geometry", "params": {
            "points": ["A", "B", "C"],
            "constraints": ["dist(A,B) = 3", "dist(B,C) = 4", "angle(A,B,C) = 90"],
            "target": "dist(A,C)"}}, "vars": []}
    show("geo hypotenuse 5 (ok)", ir, {"claimed_answer": {"kind": "value", "payload": "5"}})
    show("geo hypotenuse 7 (bad)", ir, {"claimed_answer": {"kind": "value", "payload": "7"}})
    # geometry: angle in isosceles right triangle (scale free)
    ir2 = {"task": {"kind": "synthetic_geometry", "params": {
            "points": ["A", "B", "C"],
            "constraints": ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 90"],
            "target": "angle(A,B,C)"}}, "vars": []}
    show("geo isosceles angle 45", ir2, {"claimed_answer": {"kind": "value", "payload": "45"}})
    # geometry: median length; triangle 6-8-10, median to hypotenuse = 5
    ir3 = {"task": {"kind": "synthetic_geometry", "params": {
            "points": ["A", "B", "C", "M"],
            "constraints": ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90", "midpoint(M, A, C)"],
            "target": "dist(B,M)"}}, "vars": []}
    show("geo median 5", ir3, {"claimed_answer": {"kind": "value", "payload": "5"}})
    # geometry: underdetermined -> unknown
    ir4 = {"task": {"kind": "synthetic_geometry", "params": {
            "points": ["A", "B", "C"], "constraints": ["dist(A,B) = 3"], "target": "dist(A,C)"}}, "vars": []}
    show("geo underdetermined", ir4, {"claimed_answer": {"kind": "value", "payload": "5"}})
    # combinatorics
    ir5 = {"task": {"kind": "probability", "params": {"space": {"structure": "product", "sets": [[1,2,3,4,5,6],[1,2,3,4,5,6]]}, "event": "sum(t) == 7"}}}
    show("prob two dice sum 7 = 1/6", ir5, {"claimed_answer": {"kind": "value", "payload": "1/6"}})
    show("prob two dice sum 7 = 1/5", ir5, {"claimed_answer": {"kind": "value", "payload": "1/5"}})
    ir6 = {"task": {"kind": "count_structures", "params": {"space": {"structure": "permutation", "elements": [0,1,2,3,4], "k": 3}, "predicate": "t[0] != 0"}}, "answer_shape": "count"}
    show("count 3-digit numbers = 48", ir6, {"claimed_answer": {"kind": "count", "payload": 48}})
    # series
    ir7 = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1) + 2*a(n-2)", "initial": {"1": "1", "2": "3"}, "index": 6}}}
    show("recurrence a6", ir7, {"claimed_answer": {"kind": "value", "payload": "43"}})
    ir8 = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = 2*a(n-1)", "initial": {"1": "3"}, "var": "n"}}, "answer_shape": "expression"}
    show("closed form 3*2**(n-1)", ir8, {"claimed_answer": {"kind": "expression", "payload": "3*2**(n-1)"}})
    show("closed form wrong", ir8, {"claimed_answer": {"kind": "expression", "payload": "3*2**n"}})
    ir9 = {"task": {"kind": "series_sum", "params": {"term": "1/2**k", "var": "k", "lo": "1", "hi": "oo"}}, "vars": [{"name": "k", "domain": "positive_integer"}]}
    show("geometric series = 1", ir9, {"claimed_answer": {"kind": "value", "payload": "1"}})
    # linalg
    ir10 = {"task": {"kind": "linalg", "params": {"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}}, "answer_shape": "expression"}
    show("inverse ok", ir10, {"claimed_answer": {"kind": "expression", "payload": "Matrix([[-2, 1],[3/2, -1/2]])"}})
    show("inverse bad", ir10, {"claimed_answer": {"kind": "expression", "payload": "Matrix([[-2, 1],[3/2, 1/2]])"}})
    ir11 = {"task": {"kind": "linalg", "params": {"op": "eigenvector", "matrix": "Matrix([[2,1],[1,2]])", "eigenvalue": "3"}}, "answer_shape": "expression"}
    show("eigenvector (1,1)", ir11, {"claimed_answer": {"kind": "expression", "payload": "(1, 1)"}})
    show("eigenvector (2,2)", ir11, {"claimed_answer": {"kind": "expression", "payload": "(2, 2)"}})
    show("eigenvector (1,-1) bad", ir11, {"claimed_answer": {"kind": "expression", "payload": "(1, -1)"}})
    ir12 = {"task": {"kind": "linalg", "params": {"op": "solve_system", "A": "Matrix([[1,1],[2,4]])", "b": "(30, 88)"}}, "answer_shape": "expression"}
    show("solve system (16,14)", ir12, {"claimed_answer": {"kind": "expression", "payload": "(16, 14)"}})
