"""The final attack after the fourth audit (A+, merged 7892190), lens 4 "parser, steps, fusion" (16 Oct 2026, evening
addendum; the findings in the attack's `tum_bulgular.json`, the decisions of the main session): each test failed on
0e93ed5 unless it is marked as a control. Probe: `denetim/2026-10-01/son/ayristirici/sonda.py`.

* G4YO-1 (realistic, false acceptance): the "no solution" shortcut of a multiple-choice option searched its words
  anywhere in the text, so '{∅}' (the set holding the empty set, a classic distractor), '{0, ∅}' and '∅ değildir' were
  "no solution", and the wrong letter beside the right ∅ was CORRECT. Only a text that IS the empty set or says "no
  solution" as a whole takes the shortcut; one that only names them is read as written.
* G4-RK-5 (realistic, unjust rejection): from premises with no instance every relation follows: '0 = 2' from
  2x + 1 = 2x + 3 and x**2 = -1 (compute) from x**2 + 1 = 0 were refuted, and the right ∅ was INCORRECT. A refutation
  is withdrawn where the problem's own premises are proved to hold nowhere (unknown, never verified); an inconsistent
  linear system is the sibling.
* G4YO-2 (unclear, both directions): '1/2π', '1/2√x', 'x/2π' were read (1/2)·π in plain text and 1/(2π) in LaTeX: a
  convention of the writer. A factor right after a divisor is read neither way (`claim_ambiguous_juxtaposition`), nor
  the dual \\ln 2/2 (latex2sympy read ln(2/2), \\ln{2}/2 too).
* G4YO-3 (unclear, false acceptance): the negation check of the payload cleaner matched whole words only, and Turkish
  suffixes ('5 değildir', '5 yanlıştır', '5 olmayabilir', '5 sanmıyorum', '5 midir') hid the negation or the doubt.
* G4-K-4 (realistic, coverage): a given with one real point (a sum of squares = 0, √ + |·| = 0, squares to complete)
  was solved over ℂ and a wrong step under it was never refuted.
"""
import pytest

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
XP = {"name": "x", "domain": "positive_real"}
Y = {"name": "y", "domain": "real"}


def _ir(kind, params, givens=(), vars_=None, shape="scalar", options=None):
    d = {"task": {"kind": kind, "params": params}, "vars": list(vars_ if vars_ is not None else [X]),
         "givens": list(givens), "answer_shape": shape}
    if options is not None:
        d["options"] = options
    return d


def _sol(payload, kind="value", steps=(), option=None):
    ca = {"kind": kind, "payload": payload}
    if option is not None:
        ca["option"] = option
    return {"claimed_answer": ca, "steps": [{"id": f"s{i + 1}", "kind": k, "claim": c, "from": [], "text": ""}
                                            for i, (k, c) in enumerate(steps)]}


def _statuses(r):
    layer = next((la for la in r.layers if la.layer == "steps.refute"), None)
    return [s.get("status") for s in layer.evidence.get("steps", [])] if layer is not None else []


def _flags(r):
    return {f for la in r.layers for f in (la.flags or [])} | set(r.flags)


def _eqn(e, options=None, vars_=None):
    return _ir("solve_equation", {"var": "x", "equation": e}, vars_=vars_, shape="set", options=options)


def _opts(d):
    return {"A": "{0}", "B": "{-1}", "C": "{1}", "D": d, "E": "{-1, 1}"}


# ---- G4YO-1 -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("d", ["{∅}", "{ ∅ }", "$\\{\\emptyset\\}$", "\\{\\emptyset\\}", "{\\emptyset}", "{0, ∅}",
                               "{∅, 1}", "∅ değildir", "Çözüm yok değil", "{0} ∪ ∅"])
def test_g4yo1_an_option_naming_the_empty_set_in_something_more_is_no_no_solution(d):
    q = _eqn("x**2 + 1 = 0", _opts(d))
    assert verify(q, _sol("∅", "set", option="D")).verdict != "CORRECT", d
    assert verify(q, _sol(None, "set", option="D")).verdict != "CORRECT", d


@pytest.mark.parametrize("d", ["{∅}", "{ ∅ }", "\\{\\emptyset\\}", "$\\{\\emptyset\\}$", "{0, ∅}"])
def test_g4yo1_the_letter_of_a_set_holding_the_empty_set_is_refuted(d):
    assert verify(_eqn("x**2 + 1 = 0", _opts(d)), _sol(None, "set", option="D")).verdict == "INCORRECT", d


@pytest.mark.parametrize("d", ["∅", "{}", "Ø", "$\\emptyset$", "$\\varnothing$", "Çözüm yok", "Çözüm kümesi boştur",
                               "Gerçel kök yoktur", "Gerçel çözümü yoktur", "Hiçbir çözüm yok", "No real solution",
                               "Ç = ∅", "Ç = {}", "x ∈ ∅", "∅ (boş küme)", "Denklemin reel kökü yoktur."])
def test_g4yo1_the_empty_set_itself_takes_the_shortcut(d):
    """Controls (most) and coverage (Ø, \\varnothing, 'Ç = {}', 'Gerçel çözümü yoktur' were not read, or refuted)."""
    q = _eqn("x**2 + 1 = 0", _opts(d))
    assert verify(q, _sol("∅", "set", option="D")).verdict == "CORRECT", d
    assert verify(q, _sol(None, "set", option="D")).verdict == "CORRECT", d
    assert verify(_eqn("x - 1 = 0", _opts(d)), _sol("{1}", "set", option="D")).verdict == "INCORRECT", d


def test_g4yo1_a_union_with_the_empty_set_is_read_as_written():
    for d in ("∅ ∪ {1}", "{1} ∪ ∅"):
        assert verify(_eqn("x - 1 = 0", _opts(d)), _sol("{1}", "set", option="D")).verdict == "CORRECT", d
        assert verify(_eqn("x**2 + 1 = 0", _opts(d)), _sol("∅", "set", option="D")).verdict == "INCORRECT", d


def test_g4yo1_prose_that_only_names_no_solution_is_not_refuted():
    """'Reel sayılarda çözüm yok' is read by nobody: undecided, never the DNE word test's refutation."""
    q = _eqn("x**2 + 1 = 0", _opts("Reel sayılarda çözüm yok"))
    assert verify(q, _sol("∅", "set", option="D")).verdict == "UNKNOWN"


# ---- G4-RK-5 ------------------------------------------------------------------------------------------------------
_SYS = _ir("solve_equation", {"var": "x"}, ["x + y = 1", "2*x + 2*y = 3"], [X, Y], "set")


@pytest.mark.parametrize("q,steps", [
    (_eqn("2*x + 1 = 2*x + 3"), [("eq", "1 = 3")]),
    (_eqn("2*x + 1 = 2*x + 3"), [("eq", "0 = 2")]),
    (_eqn("2*x + 1 = 2*x + 3"), [("eq", "2*x - 2*x = 3 - 1")]),
    (_eqn("x**2 + 1 = 0"), [("compute", "x**2 = -1")]),
    (_eqn("Abs(x) + 1 = 0"), [("compute", "Abs(x) = -1")]),
    (_ir("solve_inequality", {"var": "x", "inequality": "x**2 + 2 < 2*x"}, shape="set"), [("eq", "1 < 0")]),
    (_eqn("x + 1 = 0", vars_=[XP]), [("eq", "1 = 0")]),
    (_SYS, [("eq", "2 = 3")]),
    (_SYS, [("compute", "2*(x + y) = 2")]),
])
def test_g4rk5_a_step_from_premises_with_no_instance_is_not_refuted(q, steps):
    """The system's ∅ has no certificate of its own (UNKNOWN at the answer level): its step is what changed."""
    r = verify(q, _sol("{}", "set", steps))
    want = {"CORRECT", "UNKNOWN"} if q is _SYS else {"CORRECT"}
    assert r.verdict in want and "refuted" not in _statuses(r) and "verified" not in _statuses(r), \
        (r.verdict, _statuses(r))


@pytest.mark.parametrize("q,answer,steps", [
    (_eqn("2*x + 1 = 5"), "{2}", [("eq", "2 = 3")]),
    (_eqn("2*x + 1 = 5"), "{2}", [("compute", "5 - 1 = 3")]),
    (_eqn("x**2 = 4"), "{-2, 2}", [("compute", "x**2 = -4")]),
    (_eqn("x**2 + 1 = 0"), "{}", [("compute", "0 - 4 = 4")]),          # a closed computation, premises or not
    (_ir("solve_equation", {"var": "x"}, ["x + y = 1", "x - y = 3"], [X, Y], "set"), "{2}", [("eq", "2 = 3")]),
    (_ir("evaluate", {"expr": "x + y"}, ["x**2 - y**2 + 1 = 0"], [X, Y]), "1", [("eq", "1 = 2")]),
    (_ir("evaluate", {"expr": "x + y"}, ["x + y + 1 = 0"], [X, Y]), "-1", [("eq", "1 = 2")]),
    (_ir("trig_solve", {"equation": "cos(x) = -1", "var": "x", "interval": "[0, pi)"}, shape="set"), "{}",
     [("eq", "cos(x) = -1"), ("eq", "x = 0")]),
])
def test_g4rk5_control_a_wrong_step_where_the_premises_have_instances_is_refuted(q, answer, steps):
    r = verify(q, _sol(answer, "set" if answer.startswith("{") else "value", steps))
    assert r.verdict == "INCORRECT" and _statuses(r)[-1] == "refuted", (r.verdict, _statuses(r))


def test_g4rk5_premises_hold_nowhere_reads_only_the_problem():
    """The steps are no premise of the emptiness proof: an unknown wrong step cannot make the premises empty and
    withdraw a later refutation (x**2 = 4: 'x**2 = -1' then '0 = 1')."""
    r = verify(_eqn("x**2 = 4"), _sol("{-2, 2}", "set", [("eq", "x**2 = -1"), ("eq", "0 = 1")]))
    assert r.verdict == "INCORRECT" and _statuses(r)[-1] == "refuted", _statuses(r)


# ---- G4YO-2 -------------------------------------------------------------------------------------------------------
def _der(f, v=XP):
    return _ir("derivative", {"f": f, "var": "x"}, vars_=[v], shape="expression")


def _ev(e):
    return _ir("evaluate", {"expr": e}, vars_=[])


@pytest.mark.parametrize("q,claim", [
    (_der("x*sqrt(x)/3"), "1/2√x"), (_der("sqrt(x)"), "1/2√x"), (_der("pi*x**2/4", X), "x/2π"),
    (_der("x**2/(4*pi)", X), "x/2π"), (_ev("asin(1)"), "1/2π"), (_ev("asin(1)/pi**2"), "1/2π"), (_ev("sin(pi/3)"), "1/2√3"),
    (_ev("sin(pi/3)/3"), "1/2√3"), (_ev("asin(1)/4"), "1/2^3π"), (_ev("asin(1)"), "$1/2\\pi$"), (_ev("asin(1)/pi**2"), "$1/2\\pi$"),
    (_ev("3*sin(pi/4)/2"), "3/4\\sqrt{2}"), (_ev("log(sqrt(2))"), "$\\ln 2/2$"), (_ev("log(sqrt(2))"), "\\ln{2}/2"),
    (_ev("sin(pi)"), "\\ln{2}/2"),
])
def test_g4yo2_a_factor_right_after_a_divisor_is_not_read(q, claim):
    r = verify(q, _sol(claim, "expression" if q["answer_shape"] == "expression" else "value"))
    assert r.verdict == "UNKNOWN" and "claim_ambiguous_juxtaposition" in _flags(r), (claim, r.verdict, _flags(r))


@pytest.mark.parametrize("q,claim,want", [
    (_der("sqrt(x)"), "1/(2√x)", "CORRECT"), (_der("sqrt(x)"), "√x/2", "INCORRECT"), (_ev("asin(1)"), "(1/2)π", "CORRECT"),
    (_ev("asin(1)"), "1/2·π", "CORRECT"), (_ev("asin(1)/pi**2"), "1/(2π)", "CORRECT"), (_ev("acos(-1/2)"), "2π/3", "CORRECT"),
    (_ev("2*tan(pi/3)/3"), "2√3/3", "CORRECT"), (_ev("asin(1)"), "\\frac{1}{2}\\pi", "CORRECT"),
    (_ev("asin(1)/pi**2"), "\\frac{1}{2\\pi}", "CORRECT"), (_ev("asin(1)"), "$1/2 \\cdot \\pi$", "CORRECT"),
    (_ev("log(sqrt(2))"), "\\ln(2)/2", "CORRECT"), (_ev("csc(1)"), "1/\\sin 1", "CORRECT"), (_ev("asin(1)"), "1/(2π)", "INCORRECT"),
])
def test_g4yo2_control_explicit_operators_and_brackets_are_read(q, claim, want):
    r = verify(q, _sol(claim, "expression" if q["answer_shape"] == "expression" else "value"))
    assert r.verdict == want, (claim, r.verdict)


def test_g4yo2_an_ambiguous_option_or_step_decides_nothing():
    mc = _der("sqrt(x)")
    mc["options"] = {"A": "1/2√x", "B": "2√x", "C": "√x/2", "D": "1/x", "E": "x"}
    assert verify(mc, _sol("1/(2*sqrt(x))", "expression", option="A")).verdict == "UNKNOWN"
    assert verify(mc, _sol(None, "expression", option="A")).verdict == "UNKNOWN"
    r = verify(_der("sqrt(x)"), _sol("1/(2*sqrt(x))", "expression", [("compute", "Derivative(sqrt(x), x) = 1/2√x")]))
    assert r.verdict != "INCORRECT" and _statuses(r) != ["refuted"], (r.verdict, _statuses(r))


def test_g4yo2_the_parser_reads_neither_way():
    import sympy as sp
    from mathverify.normalize.parse import ParseError, ambiguous_juxtaposition, parse_expr_str
    for t in ("1/2π", "1/2 π", "x/2π", "1/2√3", "1/(2)π", "1/-2π", "1/2**3π", "$1/2\\pi$", "\\pi/2x", "1/2\\,\\pi",
              "\\ln 2/2", "\\sin x/2", "1/2\\left(x+1\\right)", "1/2%", "3/4 %", "180/2°", "1/(30)°", "1/2 derece"):
        assert ambiguous_juxtaposition(t), t
        with pytest.raises(ParseError):
            parse_expr_str(t, {"x": sp.Symbol("x"), "pi": sp.pi, "sqrt": sp.sqrt, "sin": sp.sin, "log": sp.log})
    for t in ("π/2", "2π/3", "(1/2)π", "1/2·π", "1/(2π)", "√2π", "\\frac{1}{2}\\pi", "\\pi/2 + k\\pi", "1/\\sin x",
              "\\sin(x)/2", "e^{x/2}", "x \\in [\\pi/2, \\pi)", "\\{\\pi/6, 5\\pi/6\\}", "2/3\\cdot x", "\\pi/2 \\le x",
              "50%", "%50", "30°/2", "(1/2)·%50"):
        assert not ambiguous_juxtaposition(t), t


# ---- G4YO-3 -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("p", ["5 değildir", "5 değildir.", "5 yanlıştır", "5 olmayabilir", "5 sanmıyorum", "5 midir",
                               "5 hariçtir", "5 çıkmaz", "5 olmuyor", "5 olabilir", "5 herhalde", "5 mıdır",
                               "5 olmamalı", "5 is incorrect", "5 DEĞİLDİR"])
def test_g4yo3_a_negation_or_a_doubt_with_its_suffix_is_not_cleaned_away(p):
    r = verify(_ev("2 + 3"), _sol(p))
    assert r.verdict == "UNKNOWN" and "payload_negated" in _flags(r), (p, r.verdict)


@pytest.mark.parametrize("p,want", [("5 bulunur", "CORRECT"), ("5 olur", "CORRECT"), ("5 olarak bulunur", "CORRECT"),
                                    ("5 olmalıdır", "CORRECT"), ("5 elde edilir", "CORRECT"), ("5 cm", "CORRECT"),
                                    ("5 eşittir", "CORRECT"), ("5 doğrudur", "CORRECT"), ("5 tane", "CORRECT"),
                                    ("5 sonucuna ulaşılır", "CORRECT"), ("6 bulunur", "INCORRECT")])
def test_g4yo3_control_plain_prose_after_the_value_is_cleaned(p, want):
    assert verify(_ev("2 + 3"), _sol(p)).verdict == want, p


# ---- G4-K-4 -------------------------------------------------------------------------------------------------------
_G1 = ["x**2 + y**2 + 2*x - 4*y + 5 = 0"]          # (x + 1)^2 + (y - 2)^2 = 0
_G2 = ["sqrt(x - 2) + Abs(y + 3) = 0"]
_G4 = ["x**2 + 4*y**2 - 2*x + 8*y + 5 = 0"]         # (x - 1)^2 + 4(y + 1)^2 = 0


@pytest.mark.parametrize("g,answer,step", [
    (_G1, "1", ("eq", "x = 1")), (_G1, "1", ("eq", "x + y = 3")), (_G1, "1", ("compute", "x*y = 2")),
    (_G1, "1", ("eq", "(x - 1)**2 + (y + 2)**2 = 0")), (_G2, "-1", ("eq", "x = -2")), (_G2, "-1", ("compute", "x*y = 6")),
    (_G4, "0", ("eq", "y = 1")), (["x**2 + y**2 = 0"], "0", ("eq", "x = 1")),
])
def test_g4k4_a_wrong_step_under_a_one_point_given_is_refuted(g, answer, step):
    r = verify(_ir("evaluate", {"expr": "x + y"}, g, [X, Y]), _sol(answer, steps=[step]))
    assert r.verdict == "INCORRECT" and _statuses(r) == ["refuted"], (r.verdict, _statuses(r))


@pytest.mark.parametrize("g,answer,step", [
    (_G1, "1", ("eq", "x = -1")), (_G1, "1", ("eq", "(x + 1)**2 + (y - 2)**2 = 0")), (_G1, "1", ("compute", "x*y = -2")),
    (_G2, "-1", ("eq", "x = 2")), (_G2, "-1", ("compute", "x*y = -6")), (_G4, "0", ("eq", "y = -1")),
    (["x**2 + y**2 = 1"], "1", ("eq", "x**2 = 1 - y**2")),
])
def test_g4k4_control_a_right_step_is_not_refuted(g, answer, step):
    expr = "x**2 + y**2" if g == ["x**2 + y**2 = 1"] else "x + y"
    r = verify(_ir("evaluate", {"expr": expr}, g, [X, Y]), _sol(answer, steps=[step]))
    assert r.verdict == "CORRECT" and _statuses(r) != ["refuted"], (r.verdict, _statuses(r))


def test_g4k4_completed_squares():
    import sympy as sp
    from mathverify.steps.deterministic import _completed_squares
    x, y = sp.symbols("x y", real=True)
    assert _completed_squares(x**2 + y**2 + 2*x - 4*y + 5, {x, y}) == [sp.Eq(x + 1, 0), sp.Eq(y - 2, 0)]
    assert _completed_squares(x**2 + y**2 + 2*x + 2, {x, y}) == [sp.false]          # (x + 1)^2 + y^2 + 1
    assert _completed_squares(x**2 + y**2 - 1, {x, y}) is None                      # a circle
    assert _completed_squares(x**2 - y**2 + 1, {x, y}) is None                      # a hyperbola
    assert _completed_squares(x**2 + 2*x*y + 2*y**2, {x, y}) is None                # a cross term
    assert _completed_squares(x + y + 1, {x, y}) is None
