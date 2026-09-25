"""Definedness is read from the problem's expression AS WRITTEN, not after SymPy simplified it.

SymPy's automatic simplification removes undefined points before any condition can be read:
`x/x` → 1, `sqrt(x)**2` → x, `x**2/x` → x, `log(x) - log(x)` → 0. Measured on 23 Sep 2026, each
wrong answer below was certified CORRECT (0.99–0.995) and each right answer was refuted.
"""
import pytest

from mathverify.verifier import verify


def _verdict(kind, params, claim_kind, claim, givens=(), shape=None):
    ir = {"task": {"kind": kind, "params": params}, "vars": [{"name": "x"}], "givens": list(givens),
          "answer_shape": shape or ("set" if claim_kind in ("set", "interval") else "scalar")}
    sol = {"claimed_answer": {"kind": claim_kind, "payload": claim, "option": None}, "steps": []}
    return verify(ir, sol).verdict


CASES = [
    # (kind, params, claim kind, WRONG claim, RIGHT claim or None, givens, shape)
    ("domain_of", {"expr": "x/x", "var": "x"}, "set", "(-oo, oo)", "(-oo, 0) U (0, oo)", (), "set"),
    ("domain_of", {"expr": "sqrt(x)**2", "var": "x"}, "interval", "(-oo, oo)", "[0, oo)", (), "interval"),
    ("domain_of", {"expr": "(x - 1)/(x - 1)", "var": "x"}, "set", "(-oo, oo)", "(-oo, 1) U (1, oo)", (), "set"),
    ("domain_of", {"expr": "log(x) - log(x)", "var": "x"}, "interval", "(-oo, oo)", "(0, oo)", (), "interval"),
    ("solve_equation", {"equation": "x**2/x = 0", "var": "x"}, "set", "{0}", "{}", (), None),
    ("solve_equation", {"equation": "sqrt(x)**2 = -1", "var": "x"}, "set", "{-1}", "{}", (), None),
    ("solve_inequality", {"inequality": "x/x > 0", "var": "x"}, "set", "(-oo, oo)", "(-oo, 0) U (0, oo)", (), None),
    ("evaluate", {"expr": "x/x"}, "value", "1", None, ("x = 0",), None),
]


@pytest.mark.parametrize("kind,params,ck,wrong,right,givens,shape", CASES,
                         ids=[f"{c[0]}:{list(c[1].values())[0]}" for c in CASES])
def test_a_point_removed_by_simplification_is_still_undefined(kind, params, ck, wrong, right, givens, shape):
    assert _verdict(kind, params, ck, wrong, givens, shape) != "CORRECT"
    if right is not None:
        assert _verdict(kind, params, ck, right, givens, shape) != "INCORRECT"


def _v(kind, params, claim, vars_=None):
    ir = {"task": {"kind": kind, "params": params}, "vars": vars_ or [{"name": "x"}], "givens": [],
          "answer_shape": "scalar"}
    return verify(ir, {"claimed_answer": {"kind": "value", "payload": claim, "option": None},
                       "steps": []}).verdict


def test_kinds_with_their_own_domain_handling_abstain_where_f_as_written_is_undefined():
    """Measured CORRECT before: a derivative at a point f does not reach, a maximum that is never
    attained, a sum with an undefined term. Abstaining is the safe answer (D6)."""
    assert _v("derivative", {"f": "x**2/x", "var": "x", "at": "0"}, "1") != "CORRECT"
    assert _v("extremum", {"f": "x/x - x**2", "var": "x", "interval": "[-1, 1]", "which": "max"}, "1") != "CORRECT"
    assert _v("series_sum", {"term": "k/k", "var": "k", "lo": "-1", "hi": "1"}, "3",
              [{"name": "k", "domain": "integer"}]) != "CORRECT"


def test_a_removable_point_does_not_change_an_integral():
    assert _v("definite_integral", {"integrand": "x/x", "var": "x", "a": "-1", "b": "1"}, "2") == "CORRECT"


def test_a_limit_still_approaches_the_point_where_the_expression_is_undefined():
    """lim x→0 of x/x is 1. Limits are exempt on purpose: their point is usually undefined."""
    v = _verdict("limit", {"expr": "x/x", "var": "x", "to": "0"}, "value", "1")
    assert v != "INCORRECT"


def test_a_simplification_is_still_judged_on_the_expressions_own_domain():
    assert _verdict("simplify_expression", {"expr": "x**2/x"}, "expression", "x", shape="expression") == "CORRECT"


def test_the_written_form_is_used_only_for_definedness():
    from mathverify.normalize.parse import build_namespace, parse_as_written
    ns = build_namespace()
    import sympy as sp
    x = sp.Symbol("x", real=True)
    ns["x"] = x
    e = parse_as_written("x/x = 1", ns)
    assert e is not None and len(e) == 2 and e[0] != 1        # the fraction survives
    # Düzeltme (25 Sep 2026): LaTeX used to return None here, and every undefined point of a
    # LaTeX-written problem was lost; it is now read with evaluation off (test_audit_2026_09_25_core)
    le = parse_as_written(r"\frac{x}{x}", ns)
    assert le is not None and len(le) == 1 and le[0] != 1      # LaTeX: the fraction survives too
    assert parse_as_written("x/zz", ns) is None                # undeclared name: left to the parser
