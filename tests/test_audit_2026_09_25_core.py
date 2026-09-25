"""Findings of the systematic audit of 25 Sep 2026 in the core pipeline (parsing, intake, fusion,
written definedness). Each case below was measured wrong before its fix: a wrong claim certified
CORRECT, a right claim refuted, a crash, or code executed from a claim.
"""
import pytest
import sympy as sp

from mathverify.equiv import exact_integer
from mathverify.normalize.parse import _SAFE_NAMES, ParseError, parse_as_written, parse_expr_str
from mathverify.solution import MalformedSolution, Solution
from mathverify.verifier import verify


def _run(ir, claim_kind, payload, option=None, steps=(), **ca_extra):
    ca = {"kind": claim_kind, "payload": payload, "option": option, **ca_extra}
    return verify(ir, {"claimed_answer": ca, "steps": list(steps)})


def _ir(kind, params, givens=(), shape="scalar", **extra):
    return {"task": {"kind": kind, "params": params}, "vars": [{"name": "x"}], "givens": list(givens),
            "answer_shape": shape, **extra}


# --- code execution from a claim --------------------------------------------------------------

# `exact_integer` read a string claim with `sympify`, which evaluates with Python's builtins in
# reach: `__import__('os').getpid()*0+3` returned 3 after calling getpid. `and`/`or`/`not` passed
# through `parse_expr` as Python operators, so `0 or (7/2)` read as 7/2 and was certified.
INJECTIONS = ["__import__('os').getpid()*0+3", "(lambda: 3)()", "[3][0]", "3 if True else 4",
              "getattr(3, 'real')", "().__class__", "exec('x=1')", "open('/etc/passwd')",
              "0 or 3", "3 and 3", "not 0"]


@pytest.mark.parametrize("src", INJECTIONS)
def test_exact_integer_never_evaluates_python(src):
    assert exact_integer(src) is None


@pytest.mark.parametrize("src", INJECTIONS)
def test_the_parser_rejects_python_that_is_not_mathematics(src):
    with pytest.raises((ParseError, sp.SympifyError, TypeError, ValueError, SyntaxError)):
        parse_expr_str(src)


def test_the_guard_does_not_run_the_code_it_rejects(tmp_path):
    marker = tmp_path / "ran"
    src = f"__import__('pathlib').Path({str(marker)!r}).touch() or 3"
    assert exact_integer(src) is None
    with pytest.raises(Exception):
        parse_expr_str(src)
    assert not marker.exists()


def test_exact_integer_keeps_honest_readings():
    assert exact_integer("3") == 3
    assert exact_integer("3.0") == 3
    assert exact_integer("ceiling(5/2)") == 3
    assert exact_integer(3) == 3
    assert exact_integer("7/2") is None
    assert exact_integer(True) is None


def test_the_guard_still_reads_ordinary_mathematics():
    x, n = sp.symbols("x n")
    ns = dict(_SAFE_NAMES, x=x, n=n, a=sp.IndexedBase("a"))
    assert parse_expr_str("sqrt(x)**2 + Rational(1, 2)", ns) == sp.sqrt(x) ** 2 + sp.Rational(1, 2)
    assert parse_expr_str("a[n] + 1", ns) == sp.IndexedBase("a")[n] + 1
    assert parse_expr_str("2*x + 1", ns) == 2 * x + 1
    assert parse_as_written("x >= 3", ns) == sp.Tuple(x, 3)
    # a one-sided limit names its side with a string: that literal is a sign, not code
    assert parse_expr_str("Limit(Abs(x)/x, x, 0, '+')", ns) == sp.Limit(sp.Abs(x) / x, x, 0, "+")
    assert parse_expr_str("Limit(1/x, x, 0, '-')", ns) == sp.Limit(1 / x, x, 0, "-")
    with pytest.raises(ParseError):
        parse_expr_str("Limit(1/x, x, 0, '__import__')", ns)


EVAL = _ir("evaluate", {"expr": "x"}, ["2*x = 7"])


@pytest.mark.parametrize("payload", ["0 or 7/2", "7/2 or 0", "__import__('os').getpid()*0 + 7/2"])
def test_a_python_wrapped_value_is_not_certified(payload):
    assert _run(EVAL, "value", payload).verdict != "CORRECT"


def test_an_honest_value_is_still_certified():
    assert _run(EVAL, "value", "7/2").verdict == "CORRECT"


# --- malformed solutions ----------------------------------------------------------------------

@pytest.mark.parametrize("step", [
    {"id": "s1", "claim": 7},
    {"id": "", "claim": "2*x = 7"},
    {"id": True, "claim": "2*x = 7"},
    {"id": "s1", "claim": "2*x = 7", "from_ids": {"s0": 1}},
    {"id": "s1", "claim": "2*x = 7", "from_ids": [["s0"]]},
    {"id": "s1", "claim": "2*x = 7", "kind": 3},
])
def test_a_malformed_step_is_reported_not_raised(step):
    with pytest.raises(MalformedSolution):
        Solution.from_dict({"claimed_answer": {"kind": "value", "payload": "7/2"}, "steps": [step]})
    r = verify(EVAL, {"claimed_answer": {"kind": "value", "payload": "7/2"}, "steps": [step]})
    assert r.verdict == "UNKNOWN" and "malformed_solution" in r.flags


def test_step_ids_are_labels():
    """Integer ids and a single `from` are read as the labels they are: `"from": 5` crashed the
    step layer, and the crash hid the refutation of the wrong step (INCORRECT became CORRECT)."""
    sol = Solution.from_dict({"claimed_answer": {"kind": "value", "payload": "7/2"},
                              "steps": [{"id": 1, "claim": "2*x = 7"},
                                        {"id": 2, "claim": "x = 7/2", "from": 1},
                                        {"id": "s3", "claim": "x = 7/2", "from_ids": [1, "2"]}]})
    assert [st.id for st in sol.steps] == ["1", "2", "s3"]
    assert sol.steps[1].from_ids == ["1"] and sol.steps[2].from_ids == ["1", "2"]


def test_a_wrong_step_is_still_refuted_whatever_its_from_says():
    for frm in (5, "s9", [7], None):
        steps = [{"id": "s1", "kind": "eq", "claim": "2*x = 7"},
                 {"id": "s2", "kind": "eq", "claim": "x = 3", "from": frm}]
        r = verify(EVAL, {"claimed_answer": {"kind": "value", "payload": "7/2"}, "steps": steps})
        assert r.verdict == "INCORRECT", (frm, r.verdict, r.flags)


def test_null_fields_of_a_step_are_read_as_absent():
    sol = Solution.from_dict({"claimed_answer": {"kind": "value", "payload": "7/2"},
                              "steps": [{"id": "s1", "claim": None, "text": None, "from_ids": None}]})
    assert sol.steps[0].claim == "" and sol.steps[0].from_ids == []


@pytest.mark.parametrize("steps", ["s1", [["s1"]], {"id": "s1"}])
def test_steps_must_be_a_list_of_objects(steps):
    r = verify(EVAL, {"claimed_answer": {"kind": "value", "payload": "7/2"}, "steps": steps})
    assert r.verdict == "UNKNOWN" and "malformed_solution" in r.flags


# --- claims that are not values ---------------------------------------------------------------

SOLVE = _ir("solve_equation", {"var": "x"}, ["x**2 - 5*x + 6 = 0"], shape="set")


@pytest.mark.parametrize("payload", ["{x}", "x"])
def test_the_unknown_itself_is_not_an_answer(payload):
    r = _run(SOLVE, "set", payload)
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in r.flags


@pytest.mark.parametrize("payload,kind", [("3,5", "value"), ("2,3", "set")])
def test_a_decimal_comma_is_not_guessed(payload, kind):
    ir = SOLVE if kind == "set" else _ir("evaluate", {"expr": "7/2"})
    r = _run(ir, kind, payload)
    assert r.verdict == "UNKNOWN" and "decimal_comma_ambiguous" in r.flags


@pytest.mark.parametrize("payload", ["3 or 4", "len('abc')"])
def test_an_unreadable_count_abstains(payload):
    ir = _ir("count_roots", {"expr": "x**3 - x", "var": "x"}, shape="count")
    r = _run(ir, "count", payload)
    assert r.verdict == "UNKNOWN" and "claim_unreadable" in r.flags


# --- notation of sets, intervals and conditions ------------------------------------------------

@pytest.mark.parametrize("payload", ["{2, 3}", "2, 3", "x ∈ {2, 3}"])
def test_set_notations_of_the_right_answer_are_certified(payload):
    assert _run(SOLVE, "set", payload).verdict == "CORRECT"


DOMAIN = _ir("domain_of", {"expr": "sqrt(x - 3)", "var": "x"}, shape="interval")


@pytest.mark.parametrize("kind,payload,expected", [
    ("interval", "[3, oo)", "CORRECT"), ("interval", "x >= 3", "CORRECT"),
    ("condition", "x >= 3", "CORRECT"), ("interval", "x >= 4", "INCORRECT")])
def test_a_condition_is_read_as_the_set_it_describes(kind, payload, expected):
    assert _run(DOMAIN, kind, payload).verdict == expected


# --- multiple choice ----------------------------------------------------------------------------

MC = dict(EVAL, options={"A": "3", "B": "7/2", "C": "4", "D": "2", "E": "1"})


@pytest.mark.parametrize("opt", ["B", "(B)", "B)", "b", "B şıkkı", "B."])
def test_spellings_of_an_option_letter_are_read(opt):
    assert _run(MC, "value", "7/2", option=opt).verdict == "CORRECT"


def test_several_letters_are_not_a_choice():
    r = _run(MC, "value", "7/2", option="B, C")
    assert r.verdict == "UNKNOWN" and "option_unreadable" in r.flags


NO_SOL = {**_ir("solve_equation", {"var": "x"}, ["x/(x - 3) = 3/(x - 3) + 2"], shape="set"),
          "options": {"A": "{1}", "B": "{2}", "C": "{1, 2}", "D": "{3}", "E": "Çözüm yok"}}


def test_an_empty_answer_matches_the_no_solution_option():
    """"Çözüm yok" matched the generic "yok" test for DNE and refuted the right empty set."""
    assert _run(NO_SOL, "set", "{}", option="E").verdict == "CORRECT"
    assert _run(NO_SOL, "none", None, option="E").verdict == "CORRECT"


def test_a_solution_under_the_no_solution_option_is_refuted():
    assert _run(NO_SOL, "set", "{3}", option="E").verdict == "INCORRECT"
    assert _run(NO_SOL, "set", "{3}", option="D").verdict == "INCORRECT"


# --- negated or hedged answers ------------------------------------------------------------------

@pytest.mark.parametrize("payload", ["5 değil", "5 olamaz", "5 yanlış", "5, not 7", "5?", "belki 5",
                                     "5 sanırım"])
def test_a_negated_or_hedged_answer_is_not_certified(payload):
    assert _run(_ir("evaluate", {"expr": "2 + 3"}), "value", payload).verdict != "CORRECT"


def test_a_plain_answer_with_prose_is_still_read():
    assert _run(_ir("evaluate", {"expr": "2 + 3"}), "value", "5 bu çözüm doğrudur").verdict == "CORRECT"


# --- a payload recovered from prose is advisory ---------------------------------------------------

def test_a_recovered_payload_may_abstain_but_never_refute():
    r = _run(SOLVE, "set", "{2}", payload_source="recovered_text")
    assert r.verdict == "UNKNOWN" and "recovered_answer_refuted" in r.flags
    assert _run(SOLVE, "set", "{2, 3}", payload_source="recovered_text").verdict == "CORRECT"
    assert _run(SOLVE, "set", "{2}").verdict == "INCORRECT"


# --- written definedness: the problem's functions and LaTeX -------------------------------------

def _fn(expr):
    return [{"name": "f", "expr": expr, "args": ["x"], "params": []}]


FN_CASES = [
    # (kind, params, givens, body, claim kind, WRONG claim, RIGHT claim or None, shape)
    ("solve_equation", {"var": "x"}, ["f(x) = 0"], "x**2/x", "set", "{0}", "{}", "set"),
    ("solve_equation", {"var": "x"}, ["f(x) = -1"], "sqrt(x)**2", "set", "{-1}", None, "set"),
    ("solve_equation", {"var": "x"}, ["f(x) = -1"], "log(x) - log(x) + x", "set", "{-1}", None, "set"),
    ("solve_inequality", {"var": "x"}, ["f(x) > 0"], "x/x", "interval", "(-oo, oo)", None, "interval"),
    ("solve_inequality", {"var": "x"}, ["f(x) < 1"], "sqrt(x)**2", "interval", "(-oo, 1)", "[0, 1)",
     "interval"),
    ("domain_of", {"expr": "f(x)", "var": "x"}, [], "x**2/x", "interval", "(-oo, oo)",
     "(-oo, 0) U (0, oo)", "interval"),
    ("domain_of", {"expr": "f(x)", "var": "x"}, [], "sqrt(x)**2", "interval", "(-oo, oo)", "[0, oo)",
     "interval"),
    ("evaluate", {"expr": "f(-1)"}, [], "log(x) - log(x) + x", "value", "-1", None, "scalar"),
    ("evaluate", {"expr": "f(0)"}, [], "x**2/x", "value", "0", None, "scalar"),
]


@pytest.mark.parametrize("kind,params,givens,body,ck,wrong,right,shape", FN_CASES,
                         ids=[f"{c[0]}:{c[3]}" for c in FN_CASES])
def test_a_function_body_keeps_its_undefined_points(kind, params, givens, body, ck, wrong, right, shape):
    ir = _ir(kind, params, givens, shape=shape, functions=_fn(body))
    assert _run(ir, ck, wrong).verdict != "CORRECT"
    if right is not None:
        assert _run(ir, ck, right).verdict != "INCORRECT"


def test_a_function_at_a_point_where_it_is_defined_is_still_certified():
    ir = _ir("evaluate", {"expr": "f(2)"}, functions=_fn("log(x) - log(x) + x"))
    assert _run(ir, "value", "2").verdict == "CORRECT"
    ir = _ir("evaluate", {"expr": "f(f(1))"}, functions=_fn("x**2 + 1"))
    assert _run(ir, "value", "5").verdict == "CORRECT"
    ir = _ir("domain_of", {"expr": "f(x)", "var": "x"}, shape="interval", functions=_fn("(2*x + 3)/(x - 1)"))
    assert _run(ir, "interval", "(-oo, 1) U (1, oo)").verdict == "CORRECT"


LATEX_CASES = [
    ("domain_of", {"expr": r"\frac{x}{x}", "var": "x"}, [], "interval", "(-oo, oo)", "(-oo, 0) U (0, oo)",
     "interval"),
    ("domain_of", {"expr": r"\left(\sqrt{x}\right)^{2}", "var": "x"}, [], "interval", "(-oo, oo)", "[0, oo)",
     "interval"),
    ("solve_equation", {"var": "x"}, [r"\frac{x^{2}}{x} = 0"], "set", "{0}", "{}", "set"),
    ("solve_equation", {"var": "x"}, [r"\left(\sqrt{x}\right)^{2} = -1"], "set", "{-1}", None, "set"),
    ("solve_inequality", {"var": "x"}, [r"\frac{x}{x} > 0"], "interval", "(-oo, oo)", None, "interval"),
    ("evaluate", {"expr": r"\frac{x}{x}"}, ["x = 0"], "value", "1", None, "scalar"),
]


@pytest.mark.parametrize("kind,params,givens,ck,wrong,right,shape", LATEX_CASES,
                         ids=[f"{c[0]}:{c[1].get('expr') or c[2][0]}" for c in LATEX_CASES])
def test_latex_keeps_its_undefined_points(kind, params, givens, ck, wrong, right, shape):
    ir = _ir(kind, params, givens, shape=shape)
    assert _run(ir, ck, wrong).verdict != "CORRECT"
    if right is not None:
        assert _run(ir, ck, right).verdict != "INCORRECT"


def test_latex_is_read_as_written():
    x = sp.Symbol("x")
    e = parse_as_written(r"\frac{x}{x}", {"x": x})
    assert e is not None and e != sp.Tuple(1)
    rel = parse_as_written(r"\sqrt{x+4} = x - 2", {"x": x})
    assert rel is not None and len(rel) == 2


@pytest.mark.parametrize("expr", ["log(-1) - log(-1) - 1", "sqrt(-4)**2", r"\frac{3-3}{3-3}"])
def test_a_problem_undefined_at_a_constant_point_abstains(expr):
    r = _run(_ir("evaluate", {"expr": expr}), "value", "-1")
    assert r.verdict == "UNKNOWN" and "problem_undefined_as_written" in r.flags


def test_complex_problems_are_not_held_to_real_definedness():
    ir = dict(_ir("evaluate", {"expr": "sqrt(-4)**2"}, domain_of_discourse="complex"), vars=[])
    assert _run(ir, "value", "-4").verdict == "CORRECT"


@pytest.mark.parametrize("expr,claim", [("2 + 3", "5"), ("1/2 + 1/3", "5/6"), (r"\frac{6}{3}", "2")])
def test_ordinary_constants_are_still_certified(expr, claim):
    assert _run(_ir("evaluate", {"expr": expr}), "value", claim).verdict == "CORRECT"


def test_a_step_with_the_unknown_itself_does_not_crash():
    steps = [{"id": "s1", "kind": "eq", "claim": "2*x = 7"}, {"id": "s2", "kind": "eq", "claim": "x = 7/2",
                                                              "from_ids": ["s1"]}]
    assert _run(EVAL, "value", "7/2", steps=steps).verdict == "CORRECT"


# --- decimals inside LaTeX ------------------------------------------------------------------------

@pytest.mark.parametrize("kind,params,payload", [
    ("limit", {"expr": "x/3", "var": "x", "to": "1"}, r"0.3333333333333 \cdot 1"),
    ("derivative", {"f": "x**3/3", "var": "x", "at": "1"}, r"0.9999999999999\cdot 1"),
    ("definite_integral", {"integrand": "x**2", "var": "x", "a": "0", "b": "1"}, r"\frac{0.9999999999999}{3}"),
])
def test_a_latex_decimal_is_the_exact_number_written(kind, params, payload):
    """latex2sympy kept the decimal as a Float, compared at ~1e-12: each was certified CORRECT."""
    assert _run(_ir(kind, params), "value", payload).verdict != "CORRECT"


@pytest.mark.parametrize("kind,params,payload", [
    ("limit", {"expr": "x/2", "var": "x", "to": "1"}, r"0.5 \cdot 1"),
    ("definite_integral", {"integrand": "x", "var": "x", "a": "0", "b": "3"}, r"\frac{9.0}{2}"),
    ("evaluate", {"expr": "7/4"}, r"1.75"),
])
def test_a_right_latex_decimal_is_still_certified(kind, params, payload):
    assert _run(_ir(kind, params), "value", payload).verdict == "CORRECT"


def test_a_free_parameter_may_appear_in_a_right_answer():
    """Only the task's unknown makes a claim "not a value"; `k` in "solve x² = k" is a parameter."""
    ir = {"task": {"kind": "solve_equation", "params": {"var": "x"}},
          "vars": [{"name": "x"}, {"name": "k", "domain": "positive_real"}], "givens": ["x**2 = k"],
          "answer_shape": "set"}
    assert _run(ir, "set", "{-sqrt(k), sqrt(k)}").verdict == "CORRECT"
    assert _run(ir, "set", "{sqrt(k)}").verdict == "INCORRECT"
    r = _run(ir, "set", "{x}")
    assert r.verdict == "UNKNOWN" and "claim_is_not_a_value" in r.flags


def test_a_bare_list_is_a_set_only_where_a_set_is_asked():
    ir = _ir("solve_inequality", {"var": "x"}, ["x**2 < 1"], shape="interval")
    assert _run(ir, "interval", "-1, 1").verdict != "CORRECT"
    assert _run(ir, "interval", "(-1, 1)").verdict == "CORRECT"


# --- fusion: every new abstention flag blocks a positive verdict -------------------------------

@pytest.mark.parametrize("flag", ["layer_exception", "malformed_solution", "option_unreadable",
                                  "decimal_comma_ambiguous", "recovered_answer_refuted", "payload_negated",
                                  "problem_undefined_as_written"])
def test_a_new_abstention_flag_blocks_correct(flag):
    """Each flag means the certificate may be about a claim nobody could read, or a problem with
    no answer; a primary pass next to it must not become CORRECT."""
    from mathverify.fuse import fuse
    from mathverify.types import LayerResult
    ok = LayerResult(layer="certify.algebra", verdict="pass", confidence=0.99, hard=True, evidence={},
                     latency_ms=1.0, primary=True)
    note = LayerResult(layer="intake", verdict="unknown", confidence=0.0, hard=False, evidence={},
                       latency_ms=1.0, flags=[flag])
    assert fuse([ok, note])["verdict"] == "UNKNOWN"
    assert fuse([ok])["verdict"] == "CORRECT"


# --- the certificates reason over the reals -------------------------------------------------------

@pytest.mark.parametrize("ir,claim", [
    ({"task": {"kind": "solve_equation", "params": {"equation": "x**2 = -1", "var": "x"}},
      "vars": [{"name": "x", "domain": "complex"}], "givens": [], "answer_shape": "set"},
     {"kind": "set", "payload": "EmptySet"}),
    ({"task": {"kind": "evaluate", "params": {"expr": "x**2 + 1"}},
      "vars": [{"name": "x", "domain": "complex"}], "givens": ["x**4 = 1"], "answer_shape": "scalar"},
     {"kind": "value", "payload": "2"}),
    ({"task": {"kind": "solve_equation", "params": {"equation": "x**2 = 2", "var": "x"}},
      "vars": [{"name": "x", "domain": "rational"}], "givens": [], "answer_shape": "set"},
     {"kind": "set", "payload": "{-sqrt(2), sqrt(2)}"}),
    ({"task": {"kind": "solve_equation", "params": {"equation": "x**2 = -1", "var": "x"}},
      "vars": [{"name": "x"}], "givens": [], "answer_shape": "set", "domain_of_discourse": "complex"},
     {"kind": "set", "payload": "EmptySet"}),
])
def test_a_complex_or_rational_variable_is_not_read_as_real(ir, claim):
    """Each wrong claim was certified over ℝ (audit of 25 Sep 2026); there is no sound verdict."""
    r = verify(ir, {"claimed_answer": claim, "steps": []})
    assert r.verdict == "UNKNOWN" and "var_domain_unsupported" in r.flags


@pytest.mark.parametrize("givens,wrong", [(["x**2 = 4", "x > 0"], "{-2, 2}"), (["2*x = 4", "x > 5"], "{2}")])
def test_a_given_inequality_restricts_the_solutions(givens, wrong):
    ir = _ir("solve_equation", {"var": "x"}, givens, shape="set")
    assert _run(ir, "set", wrong).verdict != "CORRECT"


def test_a_given_inequality_on_an_inequality_restricts_it():
    ir = _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, ["x > 0"], shape="interval")
    assert _run(ir, "interval", "(-2, 2)").verdict == "INCORRECT"
    assert _run(ir, "interval", "(0, 2)").verdict == "CORRECT"
