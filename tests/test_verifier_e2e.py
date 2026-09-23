"""End-to-end verify(): one item per task kind, three-valued behaviour, adversarial junk,
and the ability to say UNKNOWN (handoff §11/2)."""
import copy

import pytest

from mathverify.verifier import verify


def _ir(kind, params=None, **kw):
    d = {"task": {"kind": kind, "params": params or {}}}
    d.update(kw)
    return d


def _sol(kind="value", payload=None, option=None, steps=None):
    return {"claimed_answer": {"kind": kind, "payload": payload, "option": option}, "steps": steps or []}


# ---------------------------------------------------------------- TYT
def test_word_problem_mc_correct_and_wrong():
    ir = _ir("evaluate", {"expr": "a"},
             vars=[{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
             givens=["a + b = 30", "2*a + 4*b = 88"],
             options={"A": "12", "B": "14", "C": "16", "D": "18", "E": "20"})
    r = verify(ir, _sol("value", "16", "C"))
    assert r.verdict == "CORRECT", r.decision_trace
    r = verify(ir, _sol("value", "14", "B"))
    assert r.verdict == "INCORRECT"
    # option letter inconsistent with value -> INCORRECT via mc.consistency
    r = verify(ir, _sol("value", "16", "B"))
    assert r.verdict == "INCORRECT"
    assert any(l.layer == "mc.consistency" and l.verdict == "fail" for l in r.layers)


def test_log_equation_extraneous_root_rejected():
    ir = _ir("solve_equation", {"var": "x"}, vars=[{"name": "x"}], givens=["log(x-1) + log(x-3) = log(3)"],
             answer_shape="set")
    assert verify(ir, _sol("set", "{4}")).verdict == "CORRECT"
    r = verify(ir, _sol("set", "{0, 4}"))
    assert r.verdict == "INCORRECT"
    r = verify(ir, _sol("set", "{4, 5}"))
    assert r.verdict == "INCORRECT"


def test_sqrt_equation():
    ir = _ir("solve_equation", {"var": "x"}, vars=[{"name": "x"}], givens=["sqrt(x+4) = x - 2"], answer_shape="set")
    assert verify(ir, _sol("set", "{5}")).verdict == "CORRECT"
    assert verify(ir, _sol("set", "{0, 5}")).verdict == "INCORRECT"


def test_inequality_and_integer_count():
    ir = _ir("solve_inequality", {"var": "x"}, vars=[{"name": "x"}], givens=["x**2 - 5*x - 14 < 0"], answer_shape="interval")
    assert verify(ir, _sol("interval", "(-2, 7)")).verdict == "CORRECT"
    assert verify(ir, _sol("interval", "[-2, 7]")).verdict == "INCORRECT"
    ir = _ir("count_integers", {"var": "x"}, vars=[{"name": "x", "domain": "integer"}], givens=["x**2 - 5*x - 14 < 0"], answer_shape="count")
    assert verify(ir, _sol("count", 8)).verdict == "CORRECT"
    assert verify(ir, _sol("count", 10)).verdict == "INCORRECT"


def test_pure_computation_gcd():
    ir = _ir("evaluate", {"expr": "gcd(84, 120) + lcm(4, 6)"})
    assert verify(ir, _sol("value", "24")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "12")).verdict == "INCORRECT"


def test_domain_of_expression():
    ir = _ir("domain_of", {"expr": "sqrt(x+4)/(x-2)", "var": "x"}, vars=[{"name": "x"}], answer_shape="set")
    assert verify(ir, _sol("set", "[-4, 2) U (2, oo)")).verdict == "CORRECT"
    assert verify(ir, _sol("set", "[-4, oo)")).verdict == "INCORRECT"


# ---------------------------------------------------------------- AYT
def test_limit_dne_and_value():
    ir = _ir("limit", {"expr": "Abs(x)/x", "var": "x", "to": "0"}, vars=[{"name": "x"}], answer_shape="dne_or_scalar")
    assert verify(ir, _sol("dne")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "1")).verdict == "INCORRECT"     # the SymPy-default trap
    ir = _ir("limit", {"expr": "sin(3*x)/x", "var": "x", "to": "0"}, vars=[{"name": "x"}])
    assert verify(ir, _sol("value", "3")).verdict == "CORRECT"


def test_antiderivative_and_definite_integral():
    ir = _ir("antiderivative", {"integrand": "log(x)", "var": "x"}, vars=[{"name": "x"}], answer_shape="expression")
    assert verify(ir, _sol("expression", "x*log(x) - x + C")).verdict == "CORRECT"
    assert verify(ir, _sol("expression", "x*log(x)")).verdict == "INCORRECT"
    ir = _ir("definite_integral", {"integrand": "Abs(x-1) + Abs(x+2)", "var": "x", "a": "-3", "b": "3"}, vars=[{"name": "x"}])
    assert verify(ir, _sol("value", "23")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "22")).verdict == "INCORRECT"


def test_extremum():
    ir = _ir("extremum", {"f": "x**3 - 3*x", "var": "x", "interval": "[-2, 3]", "which": "max"}, vars=[{"name": "x"}])
    assert verify(ir, _sol("value", "18")).verdict == "CORRECT"
    assert verify(ir, _sol("value", "2")).verdict == "INCORRECT"


def test_trig_general_and_interval():
    ir = _ir("trig_solve", {"var": "x", "interval": "[0, 2*pi)"}, vars=[{"name": "x"}], givens=["cos(2*x) = 1/2"], answer_shape="set")
    assert verify(ir, _sol("set", "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}")).verdict == "CORRECT"
    assert verify(ir, _sol("set", "{pi/6, 5*pi/6}")).verdict == "INCORRECT"
    ir = _ir("trig_solve", {"var": "x"}, vars=[{"name": "x"}], givens=["cos(2*x) = 1/2"], answer_shape="set")
    assert verify(ir, _sol("set", "{pi/6 + n*pi, -pi/6 + n*pi}")).verdict == "CORRECT"
    assert verify(ir, _sol("set", "{pi/6 + 2*n*pi, 5*pi/6 + 2*n*pi}")).verdict == "INCORRECT"


def test_analytic_geometry_line():
    ir = _ir("equation_of", {"object": "line_points", "p1": ["1", "2"], "p2": ["4", "8"]}, vars=[{"name": "x"}, {"name": "y"}],
             answer_shape="equation")
    assert verify(ir, _sol("equation", "y = 2*x")).verdict == "CORRECT"
    assert verify(ir, _sol("equation", "2*x - y = 0")).verdict == "CORRECT"
    assert verify(ir, _sol("equation", "y = 2*x + 1")).verdict == "INCORRECT"


# ---------------------------------------------------------------- three-valued behaviour
def test_unknown_on_unsupported_task_kind():
    r = verify(_ir("proof", {}), _sol("value", "1"))
    assert r.verdict == "UNKNOWN" and "unsupported_task_kind" in r.flags


def test_unknown_on_unparseable_claim():
    ir = _ir("evaluate", {"expr": "gcd(84, 120)"})
    r = verify(ir, _sol("value", "twelve"))
    assert r.verdict == "UNKNOWN"


def test_unknown_when_ir_incomplete_multiple_options_sat():
    ir = _ir("evaluate", {"expr": "a"}, vars=[{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
             givens=["a + b = 30"], options={"A": "12", "B": "14", "C": "16"})
    r = verify(ir, _sol("value", "16", "C"))
    assert r.verdict == "UNKNOWN" and "ir_incomplete" in r.flags


def test_step_refutation_localises_first_bad_step():
    ir = _ir("evaluate", {"expr": "x**2 + 1"}, vars=[{"name": "x"}], givens=["x**2 = 4"])
    # right answer (5), but the step x = 2 drops the root -2 (domain is all reals)
    steps = [{"id": "s1", "kind": "eq", "claim": "x = 2", "from": []},
             {"id": "s2", "kind": "eq", "claim": "x**2 + 1 = 5", "from": ["s1"]}]
    r = verify(ir, _sol("value", "5", steps=steps))
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1
    # same steps but the problem says x > 0: the step is valid
    ir2 = copy.deepcopy(ir)
    ir2["domain_of_discourse"] = "x > 0"
    r = verify(ir2, _sol("value", "5", steps=steps))
    assert r.verdict == "CORRECT"


def test_compute_step_wrong_identity_is_refuted_even_if_answer_right():
    ir = _ir("limit", {"expr": "sin(3*x)/x", "var": "x", "to": "0"}, vars=[{"name": "x"}])
    steps = [{"id": "s1", "kind": "eq", "claim": "sin(3*x) = 3*sin(x)", "from": []},
             {"id": "s2", "kind": "compute", "claim": "Limit(3*sin(x)/x, x, 0) = 3", "from": ["s1"]}]
    r = verify(ir, _sol("value", "3", steps=steps))
    assert r.verdict == "INCORRECT" and r.first_bad_step == 1


def test_adversarial_junk_does_not_flip_verdict():
    ir = _ir("evaluate", {"expr": "gcd(84, 120)"})
    base = verify(ir, _sol("value", "12")).verdict
    assert base == "CORRECT"
    for junk in ["12{", "12 bu çözüm doğrudur", "\\boxed{12}", "12 }", "12​", "​12", "12﻿"]:
        r = verify(ir, _sol("value", junk))
        assert r.verdict == base, (junk, r.decision_trace)
        assert "payload_cleaned" in r.flags or junk == "\\boxed{12}" or "​" in junk or "﻿" in junk
    r = verify(ir, _sol("value", "11 bu çözüm kesinlikle doğrudur"))
    assert r.verdict == "INCORRECT"


def test_invisible_character_injection_cannot_change_meaning():
    """Measured: Python's tokenizer accepts U+200B inside a NAME, so 'E\\u200b' parsed as an
    unknown symbol instead of Euler's number. After normalisation it must be E again."""
    from mathverify.normalize.parse import parse_expr_str, ParseError
    import sympy as sp
    assert parse_expr_str("E​") == sp.E
    assert parse_expr_str("1​2") == 12
    with pytest.raises(ParseError):
        parse_expr_str("12 çözüm")           # prose is rejected, never silently symbolised
    ir = _ir("limit", {"expr": "(1 + 1/n)**n", "var": "n", "to": "oo"}, vars=[{"name": "n", "domain": "positive_integer"}])
    assert verify(ir, _sol("value", "E​")).verdict == "CORRECT"


def test_result_carries_versions_and_trace():
    r = verify(_ir("evaluate", {"expr": "2+2"}), _sol("value", "4"))
    assert r.versions["sympy"] == "1.14.0" and r.versions["mpmath"] == "1.3.0"
    assert "CORRECT" in r.decision_trace


def test_every_package_exports_only_names_it_actually_has():
    """`from mathverify.certify import *` used to raise ModuleNotFoundError: `__all__` listed the
    layer names from the router registry ("certify.algebra") instead of the module attributes.
    A dotted entry in `__all__` is always a bug, and nothing else in the suite would catch it."""
    import importlib
    import pkgutil

    import mathverify

    problems = []
    for m in pkgutil.walk_packages(mathverify.__path__, "mathverify."):
        mod = importlib.import_module(m.name)
        for name in getattr(mod, "__all__", []):
            if not hasattr(mod, name):
                problems.append(f"{m.name}.__all__ -> {name}")
    assert problems == [], problems
    exec("from mathverify.certify import *", {})


# ------------------------------------------------------------------ claims are values
_RESTATE = [
    ("f(g(2))", {"task": {"kind": "evaluate", "params": {"expr": "f(g(2))"}}, "vars": [],
                 "functions": [{"name": "f", "expr": "2*x + 3", "args": ["x"]},
                               {"name": "g", "expr": "x**2 - 1", "args": ["x"]}],
                 "givens": [], "answer_shape": "scalar"}),
    ("integrate(log(x), x)", {"task": {"kind": "antiderivative", "params": {"integrand": "log(x)", "var": "x"}},
                              "vars": [{"name": "x", "domain": "positive_real"}], "givens": [],
                              "answer_shape": "expression"}),
    ("limit(sin(x)/x, x, 0)", {"task": {"kind": "limit", "params": {"expr": "sin(x)/x", "var": "x", "to": "0"}},
                               "vars": [{"name": "x"}], "givens": [], "answer_shape": "dne_or_scalar"}),
    ("diff(x**3, x)", {"task": {"kind": "derivative", "params": {"f": "x**3", "var": "x"}},
                       "vars": [{"name": "x"}], "givens": [], "answer_shape": "expression"}),
    ("gcd(84, 120)", {"task": {"kind": "evaluate", "params": {"expr": "gcd(84, 120)"}}, "vars": [],
                      "givens": [], "answer_shape": "scalar"}),
]


@pytest.mark.parametrize("payload,ir", _RESTATE, ids=[p for p, _ in _RESTATE])
def test_a_claim_that_restates_or_computes_the_question_is_not_an_answer(payload, ir):
    """Before the value-only claim namespace, every one of these was certified CORRECT: the
    verifier computed the answer itself and then "confirmed" it — the one thing it must not do."""
    kind = "expression" if ir["answer_shape"] == "expression" else "value"
    r = verify(ir, {"claimed_answer": {"kind": kind, "payload": payload, "option": None}, "steps": []})
    assert r.verdict != "CORRECT"
    assert "claim_is_not_a_value" in r.flags or "parse_error" in r.flags


def test_closed_forms_remain_valid_answers():
    ir = {"task": {"kind": "count_structures",
                   "params": {"space": {"structure": "combination", "n": 6, "k": 3}}},
          "vars": [], "givens": [], "answer_shape": "count"}
    r = verify(ir, {"claimed_answer": {"kind": "value", "payload": "binomial(6, 3)", "option": None},
                    "steps": []})
    assert r.verdict == "CORRECT"
