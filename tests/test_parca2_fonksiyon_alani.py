"""N5 of the third audit (tur3_e6712f5.json, critic; DECISIONS §75): an IR function's declared domain
that was not one relation was dropped silently. f(x) = x**2 + 1, f(x) = 5: with the domain written
"(0, oo)", "x in (0, oo)", "x > 0 and x < 3", "R+", "[0, oo)" or "x > 0, x < 3" the wrong {-2, 2}
was CORRECT and the right {2} INCORRECT (12/12 wrong on aa67b20); "x > 0, x < 3" read as
x > (0, x) and (0, x) < 3 and killed five sandbox workers (TypeError unpickling it); "x > a" with
the given a = 0 was read on two variables and dropped. The declared constraints of a variable
(`vars[].constraints`) and the written conditions on two variables had the same silent drop.
Every case below was measured wrong before the fix (denetim/2026-09-30/n19/sonda_n19.py N5).
"""
import pytest
import sympy as sp

from mathverify.certify.base import make_ctx
from mathverify.extract.ir_extract import validate_ir
from mathverify.ir import ProblemIR
from mathverify.normalize.parse import ParseError, parse_relation, read_domain_condition, _SAFE_NAMES
from mathverify.sandbox import Sandbox, SandboxError, get_sandbox
from mathverify.verifier import verify

XR = [{"name": "x", "domain": "real"}]
XA = XR + [{"name": "a", "domain": "real"}]
X = sp.Symbol("x", real=True)


def _ir(params, vars_=XR, givens=(), functions=None, kind="solve_equation", shape="set"):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_), "givens": list(givens),
         "answer_shape": shape}
    if functions:
        d["functions"] = functions
    return d


def _f(domain, expr="x**2 + 1"):
    return [{"name": "f", "expr": expr, "args": ["x"], "domain": domain}]


def _run(ir, payload, kind="set"):
    return verify(ir, {"claimed_answer": {"kind": kind, "payload": payload}, "steps": []})


EQ = {"equation": "f(x) = 5", "var": "x"}


# --- the audit's inputs ---------------------------------------------------------------------------

@pytest.mark.parametrize("domain", ["x > 0", "(0, oo)", "x in (0, oo)", "x > 0 and x < 3", "[0, oo)",
                                    "x > 0, x < 3"])
def test_a_declared_domain_in_any_written_form_restricts_the_roots(domain):
    """Only "x > 0" was applied before: the other five forms certified {-2, 2} and refuted {2}."""
    ir = _ir(EQ, functions=_f(domain))
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT"
    assert _run(ir, "{2}").verdict == "CORRECT"


def test_a_domain_that_cannot_be_read_is_not_dropped_the_problem_is_not_verified():
    """"R+" is no notation the parser reads (positive or nonnegative?): it was ignored, {-2, 2}
    CORRECT. Now the namespace refuses it and the verifier abstains on both claims."""
    ir = _ir(EQ, functions=_f("R+"))
    for claim in ("{-2, 2}", "{2}"):
        r = _run(ir, claim)
        assert r.verdict == "UNKNOWN" and "parse_error" in r.flags
        assert "ir_namespace_error" in str(r.layers[0].evidence)


def test_a_symbol_fixed_by_a_given_is_read_with_its_value():
    """f on x > a with the given a = 0: the condition had two symbols and was dropped."""
    ir = _ir(EQ, XA, ["a = 0"], _f("x > a"))
    assert _run(ir, "{2}").verdict == "CORRECT"
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT"
    ir = _ir(EQ, XA, ["0 = a"], _f("x > a"))
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT"
    ir = _ir(EQ, XA, ["a = -3"], _f("x > a"))                  # both roots are in the domain
    assert _run(ir, "{-2, 2}").verdict == "CORRECT"
    assert _run(ir, "{2}").verdict == "INCORRECT"
    # a call outside the domain has no value (f(-1) was INCORRECT for 2, read on a free a)
    ir = _ir({"expr": "f(-1)"}, XA, ["a = 0"], _f("x > a"), kind="evaluate", shape="scalar")
    assert _run(ir, "2", "value").verdict == "UNKNOWN"
    ir = _ir({"expr": "f(1)"}, XA, ["a = 0"], _f("x > a"), kind="evaluate", shape="scalar")
    assert _run(ir, "2", "value").verdict == "CORRECT"


def test_the_comma_domain_no_longer_kills_sandbox_workers():
    """"x > 0, x < 3" was built as the unevaluated x > (0, x): each sandbox call that carried it
    died unpickling it (five restarts per verification). The verification returns and no worker
    is restarted."""
    sb = get_sandbox()
    sb.call("mathverify.sandbox.ops:simplify_diff", 1, 1)
    before = sb.restarts
    ir = _ir(EQ, functions=_f("x > 0, x < 3"))
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT"
    assert sb.restarts == before


def test_an_order_between_non_expressions_is_not_a_relation():
    """The root of the crash: parse_relation built x > (0, x) unevaluated. It is refused now."""
    ns = dict(_SAFE_NAMES, x=X)
    for text in ["x > 0, x < 3", "x < 3, 1", "x >= (0, 1)"]:
        with pytest.raises(ParseError):
            parse_relation(text, ns)
    assert parse_relation("0 < x < 3", ns) == sp.And(sp.Lt(0, X), sp.Lt(X, 3))     # a chain still reads
    assert parse_relation("x != 1", ns) == sp.Ne(X, 1)


def test_a_request_the_worker_cannot_rebuild_is_an_error_not_the_workers_end():
    """Whatever reaches the sandbox, an object that fails to unpickle is that call's error: the
    worker process stays (it died before, and every later call paid a restart)."""
    s = Sandbox(mem_mb=512, mode="process")
    try:
        assert s.call("mathverify.sandbox.ops:simplify_diff", 1, 1) == 0
        pid = s._proc.pid
        bad = sp.Gt(X, sp.Tuple(0, X), evaluate=False)
        with pytest.raises(SandboxError, match="request not readable"):
            s.call("mathverify.sandbox.ops:simplify_diff", bad, 0)
        assert s.restarts == 0 and s._proc.pid == pid
        assert s.call("mathverify.sandbox.ops:simplify_diff", 2, 2) == 0
    finally:
        s.close()


# --- abstentions ----------------------------------------------------------------------------------

def test_a_domain_symbol_no_given_fixes_makes_the_verifier_abstain():
    """f on x > a with a free: every claim depends on a. {-2, 2} was CORRECT."""
    for givens in ([], ["a = integrate(0*x, (x, 0, 1))"], ["a = 0", "a = 1"]):
        ir = _ir(EQ, XA, givens, _f("x > a"))
        for claim in ("{-2, 2}", "{2}"):
            r = _run(ir, claim)
            assert r.verdict == "UNKNOWN" and "function_domain_not_applied" in r.flags, (givens, claim)
    ir = _ir({"expr": "f(1)"}, XA, [], _f("x > a"), kind="evaluate", shape="scalar")
    assert _run(ir, "2", "value").verdict == "UNKNOWN"


@pytest.mark.parametrize("domain", ["x < 3, 1", "x > 0 && x < 3", "(-oo, 0) U (0, oo)", "y > 0",
                                    "t in (0, oo)", "Naturals"])
def test_domains_that_are_not_read_abstain(domain):
    """A set that is not an interval, a stray element, a condition on no argument: not guessed."""
    vs = XR + [{"name": "y", "domain": "real"}, {"name": "t", "domain": "real"}]
    ir = _ir(EQ, vs, functions=_f(domain))
    assert _run(ir, "{-2, 2}").verdict == "UNKNOWN"
    assert _run(ir, "{2}").verdict == "UNKNOWN"


def test_an_empty_domain_after_the_given_abstains():
    ir = _ir(EQ, XA, ["a = 0"], _f("x**2 < a"))
    assert _run(ir, "{}").verdict == "UNKNOWN"


def test_the_extractor_is_told_the_domain_does_not_read():
    ir = _ir(EQ, functions=_f("R+"))
    errs = validate_ir(ir)
    assert any(e.startswith("namespace: ParseError") for e in errs), errs
    assert validate_ir(_ir(EQ, functions=_f("(0, oo)"))) == []


# --- the reader -----------------------------------------------------------------------------------

@pytest.mark.parametrize("domain,expected", [
    ("x > 0", sp.Gt(X, 0)),
    ("(0, oo)", sp.Gt(X, 0)),
    ("x in (0, oo)", sp.Gt(X, 0)),
    ("x ∈ (0, ∞)", sp.Gt(X, 0)),
    ("Interval.open(0, oo)", sp.Gt(X, 0)),
    ("[0, 3)", sp.And(sp.Ge(X, 0), sp.Lt(X, 3))),
    ("(-oo, 3]", sp.Le(X, 3)),
    ("x > 0 and x < 3", sp.And(sp.Gt(X, 0), sp.Lt(X, 3))),
    ("x > 0, x < 3", sp.And(sp.Gt(X, 0), sp.Lt(X, 3))),
    ("x > 0 & x < 3", sp.And(sp.Gt(X, 0), sp.Lt(X, 3))),
    ("x > 0 ∧ x != 1", sp.And(sp.Gt(X, 0), sp.Ne(X, 1))),
    ("0 < x < 3", sp.And(sp.Lt(0, X), sp.Lt(X, 3))),
    ("x in [0, 3), x != 1", sp.And(sp.Ge(X, 0), sp.Lt(X, 3), sp.Ne(X, 1))),
    ("Reals", None),
    ("(-oo, oo)", None),
])
def test_read_domain_condition(domain, expected):
    ns = dict(_SAFE_NAMES, x=X)
    assert read_domain_condition(domain, [X], ns) == expected


def test_read_domain_condition_refuses_what_it_does_not_read():
    y = sp.Symbol("y", real=True)
    ns = dict(_SAFE_NAMES, x=X, y=y)
    for bad in ["R+", "x < 3, 1", "{1, 2}", "(-oo, 0) U (0, oo)", "y > 0", "y in (0, oo)", "x > 0,",
                "x > 0 && x < 3", "Integers", "positive"]:
        with pytest.raises(ParseError):
            read_domain_condition(bad, [X], ns)
    with pytest.raises(ParseError):                        # a bare set for two arguments names neither
        read_domain_condition("(0, oo)", [X, y], ns)
    assert read_domain_condition("x > 0, y > 0", [X, y], ns) == sp.And(sp.Gt(X, 0), sp.Gt(y, 0))
    assert read_domain_condition("y in (0, oo)", [X, y], ns) == sp.Gt(y, 0)


def test_two_argument_domains_apply_to_each_argument():
    f2 = [{"name": "g", "expr": "x + y", "args": ["x", "y"], "domain": "x > 0, y > 0"}]
    vs = XR + [{"name": "y", "domain": "real"}]
    assert _run(_ir({"expr": "g(-1, 2)"}, vs, [], f2, "evaluate", "scalar"), "1", "value").verdict == "UNKNOWN"
    assert _run(_ir({"expr": "g(1, 2)"}, vs, [], f2, "evaluate", "scalar"), "3", "value").verdict == "CORRECT"


# --- controls: what already worked keeps working --------------------------------------------------

def test_controls_single_relation_chain_and_dataset_domain():
    ir = _ir(EQ, functions=_f("0 < x < 3"))
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT" and _run(ir, "{2}").verdict == "CORRECT"
    ir = _ir(EQ, functions=_f("x >= 0"))
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT" and _run(ir, "{2}").verdict == "CORRECT"
    for dom in ("Reals", "x != 1", "x**2 >= 0"):              # no root is excluded
        ir = _ir(EQ, functions=_f(dom))
        assert _run(ir, "{-2, 2}").verdict == "CORRECT" and _run(ir, "{2}").verdict == "INCORRECT"
    # tyt-esf-005: f(x) = (2x + 3)/(x - 1) on x != 1, f(x) = 5
    ir = _ir(EQ, [{"name": "x"}], ["f(x) = 5"], _f("x != 1", "(2*x + 3)/(x - 1)"), shape="scalar")
    assert _run(ir, "8/3", "value").verdict == "CORRECT"
    assert _run(ir, "3", "value").verdict == "INCORRECT"


# --- the same drop elsewhere: written conditions on two variables, declared constraints -----------

def test_a_written_condition_on_a_bound_symbol_restricts_the_domain():
    """log(x - a) with the given a = 0 is defined on x > 0; read on two variables it was dropped
    and {-2, 2} was CORRECT, {2} INCORRECT. (The word-problem layer still reads a as free, N7, so
    the claims abstain for now; the domain itself is exact.)"""
    for eq in ["x**2 + 1 + 0*log(x - a) = 5", "x**2 + 1 + 0*sqrt(x - a) = 5"]:
        ir = _ir({"equation": eq, "var": "x"}, XA, ["a = 0"])
        ctx = make_ctx(ProblemIR.from_dict(ir))
        want = sp.Interval.open(0, sp.oo) if "log" in eq else sp.Interval(0, sp.oo)
        assert ctx.domain_for(ctx.sym("x")) == want
        assert _run(ir, "{-2, 2}").verdict != "CORRECT"
        assert _run(ir, "{2}").verdict != "INCORRECT"
    fn = [{"name": "f", "expr": "x**2 + 1 + 0*log(x - a)", "args": ["x"]}]
    ir = _ir(EQ, XA, ["a = 0"], fn)
    assert _run(ir, "{-2, 2}").verdict != "CORRECT"
    # control: with a free the parametric answer is still read (the condition stays on x and a)
    ir = _ir({"equation": "sqrt(x - a) = 2", "var": "x"}, XA)
    assert _run(ir, "{a + 4}").verdict == "CORRECT"


@pytest.mark.parametrize("constraint", ["(0, oo)", "x in (0, oo)", "x > 0 and x < 3", "R+", "[0, oo)",
                                        "x > 0, x < 3", "x > 0 & x < 3"])
def test_a_constraint_that_does_not_read_as_relations_abstains(constraint):
    """`(0, oo)` read as a tuple and was dropped from the domain: {-2, 2} CORRECT. The others did
    not parse; the domain dropped them and the right {2} was INCORRECT."""
    ir = _ir({"equation": "x**2 + 1 = 5", "var": "x"}, [{"name": "x", "domain": "real", "constraints": [constraint]}])
    for claim in ("{-2, 2}", "{2}"):
        r = _run(ir, claim)
        assert r.verdict == "UNKNOWN" and "constraint_unreadable" in r.flags, claim


def test_constraints_chain_and_bound_symbol():
    """A chain 0 < x < 3 is an And, which solveset did not read: dropped from the domain (UNKNOWN
    both ways). A constraint x > a with the given a = 0 was dropped as one on two variables."""
    ir = _ir({"equation": "x**2 + 1 = 5", "var": "x"}, [{"name": "x", "domain": "real", "constraints": ["0 < x < 3"]}])
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT" and _run(ir, "{2}").verdict == "CORRECT"
    ir = _ir({"equation": "x**2 + 1 = 5", "var": "x"},
             [{"name": "x", "domain": "real", "constraints": ["x > a"]}, {"name": "a", "domain": "real"}], ["a = 0"])
    ctx = make_ctx(ProblemIR.from_dict(ir))
    assert ctx.domain_for(ctx.sym("x")) == sp.Interval.open(0, sp.oo)
    assert _run(ir, "{-2, 2}").verdict != "CORRECT"
    ir = _ir({"equation": "x**2 + 1 = 5", "var": "x"}, [{"name": "x", "domain": "real", "constraints": ["x > 0"]}])
    assert _run(ir, "{-2, 2}").verdict == "INCORRECT" and _run(ir, "{2}").verdict == "CORRECT"
