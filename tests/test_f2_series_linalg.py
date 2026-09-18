"""F2 — recurrences/series and linear algebra certificates."""

from mathverify.verifier import verify


def _sol(kind, payload):
    return {"claimed_answer": {"kind": kind, "payload": payload}}


# ---------------------------------------------------------------- series
def test_recurrence_term_exact_iteration():
    ir = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1) + 2*a(n-2)",
                                                         "initial": {"1": "1", "2": "3"}, "index": 6}}}
    assert verify(ir, _sol("value", "43")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "21")).verdict == "INCORRECT"


def test_closed_form_symbolic_and_term_checks():
    ir = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = 2*a(n-1)", "initial": {"1": "3"}, "var": "n"}},
          "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "3*2**(n-1)")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "3*2**n")).verdict == "INCORRECT"
    assert verify(ir, _sol("expression", "6*2**n/4")).verdict == "CORRECT"       # equivalent form
    # Binet for Fibonacci: symbolic proof may fail, exact 20-term check decides
    ir = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = a(n-1) + a(n-2)",
                                                     "initial": {"1": "1", "2": "1"}, "var": "n"}},
          "answer_shape": "expression"}
    binet = "(((1+sqrt(5))/2)**n - ((1-sqrt(5))/2)**n)/sqrt(5)"
    r = verify(ir, _sol("expression", binet))
    assert r.verdict == "CORRECT", r.decision_trace
    assert verify(ir, _sol("expression", "(((1+sqrt(5))/2)**n + ((1-sqrt(5))/2)**n)/sqrt(5)")).verdict == "INCORRECT"


def test_series_sums():
    ir = {"task": {"kind": "series_sum", "params": {"term": "k**2", "var": "k", "lo": "1", "hi": "10"}},
          "vars": [{"name": "k", "domain": "positive_integer"}]}
    assert verify(ir, _sol("value", "385")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "330")).verdict == "INCORRECT"
    ir = {"task": {"kind": "series_sum", "params": {"term": "1/(k*(k+1))", "var": "k", "lo": "1", "hi": "oo"}},
          "vars": [{"name": "k", "domain": "positive_integer"}]}
    assert verify(ir, _sol("value", "1")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "1/2")).verdict == "INCORRECT"
    ir = {"task": {"kind": "series_sum", "params": {"term": "1/k**2", "var": "k", "lo": "1", "hi": "oo"}},
          "vars": [{"name": "k", "domain": "positive_integer"}]}
    assert verify(ir, _sol("value", "pi**2/6")).verdict == "CORRECT"


# ---------------------------------------------------------------- linalg
def test_inverse_is_checked_by_multiplication():
    ir = {"task": {"kind": "linalg", "params": {"op": "inverse", "matrix": "Matrix([[1,2],[3,4]])"}}, "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "Matrix([[-2, 1],[3/2, -1/2]])")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "Matrix([[4, -2],[-3, 1]])")).verdict == "INCORRECT"     # adjugate only
    assert verify(ir, _sol("expression", "Matrix([[-2, 1],[1.5, -0.5]])")).verdict == "CORRECT"


def test_eigenvalues_set_and_multiset():
    ir = {"task": {"kind": "linalg", "params": {"op": "eigenvalues", "matrix": "Matrix([[2,1],[1,2]])"}}, "answer_shape": "set"}
    assert verify(ir, _sol("set", "{1, 3}")).verdict == "CORRECT"
    assert verify(ir, _sol("set", "{1, 2}")).verdict == "INCORRECT"
    ir = {"task": {"kind": "linalg", "params": {"op": "eigenvalues", "matrix": "Matrix([[2,0],[0,2]])"}}, "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "(2, 2)")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "(2, 2, 2)")).verdict == "INCORRECT"


def test_eigenvector_any_nonzero_multiple_accepted():
    ir = {"task": {"kind": "linalg", "params": {"op": "eigenvector", "matrix": "Matrix([[2,1],[1,2]])", "eigenvalue": "3"}},
          "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "(1, 1)")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "(-7, -7)")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "(1, -1)")).verdict == "INCORRECT"
    assert verify(ir, _sol("expression", "(0, 0)")).verdict == "INCORRECT"


def test_solve_system_and_uniqueness():
    ir = {"task": {"kind": "linalg", "params": {"op": "solve_system", "A": "Matrix([[1,1],[2,4]])", "b": "(30, 88)"}},
          "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "(16, 14)")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "(14, 16)")).verdict == "INCORRECT"
    # singular system: a particular solution satisfies A x = b but uniqueness fails -> UNKNOWN
    ir = {"task": {"kind": "linalg", "params": {"op": "solve_system", "A": "Matrix([[1,1],[2,2]])", "b": "(2, 4)"}},
          "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "(1, 1)")).verdict == "UNKNOWN"


def test_matrix_expression():
    ir = {"task": {"kind": "linalg", "params": {"op": "matrix_expr", "expr": "Matrix([[1,1],[0,1]])**3"}}, "answer_shape": "expression"}
    assert verify(ir, _sol("expression", "Matrix([[1,3],[0,1]])")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "Matrix([[1,2],[0,1]])")).verdict == "INCORRECT"
