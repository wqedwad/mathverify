"""Prompts for the LLM front-end. Internal reasoning language is English (handoff §8:
multilingual reasoning gaps); the input question stays Turkish. Exemplars are hand-written
IRs from the evaluation set rendered in the extractor's output format; items used as
exemplars are excluded from the fidelity metrics (harness/run_f3.py)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..llm.schemas import ir_to_llm, PARAM_DOC

ROOT = Path(__file__).resolve().parents[3]

# one exemplar per task kind / trap, all cell A
EXEMPLAR_IDS = [
    "tyt-prob-001", "tyt-prob-005", "tyt-say-003", "tyt-say-005", "tyt-say-006", "tyt-den-001", "tyt-den-004",
    "tyt-den-005", "tyt-esf-001", "tyt-esf-002", "tyt-esf-004", "tyt-esf-005", "tyt-esf-006", "tyt-esf-007",
    "ayt-lim-003", "ayt-lim-006", "ayt-tur-001", "ayt-tur-003", "ayt-tur-004", "ayt-tur-005", "ayt-tur-006",
    "ayt-tur-007", "ayt-int-001", "ayt-int-002", "ayt-trig-001", "ayt-trig-002", "ayt-trig-003", "ayt-ana-001",
    "ayt-ana-003", "ayt-ana-004", "tyt-geo-001", "tyt-geo-002", "tyt-ola-001", "tyt-ola-003", "tyt-ola-005",
    "ayt-diz-001", "ayt-diz-003", "ayt-diz-005", "uni-la-001", "uni-la-004", "uni-002", "uni-004",
]

EXTRACT_SYSTEM = """You are the formalisation front-end of a deterministic mathematics verifier. You convert a Turkish (TYT / AYT / university) math question into a Problem IR that computer-algebra certificates (SymPy, z3, mpmath) execute afterwards.

You do NOT solve the problem. The IR states the problem exactly as posed; it never contains the answer, a solved value, a simplified target, or any derived quantity. A "helpful" IR that pre-computes something silently corrupts every verdict.

## Expression syntax (machine-parsed, SymPy-like)
- Products need an explicit '*': 3*x, 2*a + 4*b, (x + 1)*(x - 2). Powers: x**2. Fractions: 1/2. Decimal point '.', Turkish "3,5" -> 3.5, "10.000" -> 10000, "%25" -> 25/100, "30°" -> 30° (keep the degree sign) or deg(30).
- Functions: sqrt, log (natural; log(x, 10) for base 10), exp, sin, cos, tan, cot, asin, acos, atan, Abs, floor, ceiling, gcd, lcm, factorial, binomial, Mod, Max, Min; constants pi, E, oo, I.
- Relations: =, <, <=, >, >=, !=; chains like 0 <= p <= 1 are allowed.
- Sets and intervals: {1, 2}, (-2, 7), [-2, 7), (-oo, -2) U [1, oo), EmptySet.
- Helpers: at(expr, var, value) evaluates expr at var=value; dist(x1, y1, x2, y2); slope(x1, y1, x2, y2); tri_area(x1, y1, x2, y2, x3, y3); point_line_dist(x0, y0, a, b, c) for a*x + b*y + c = 0; det(Matrix([[1, 2], [3, 4]])), trace(...), rank(...), eigmax(...), eigmin(...).
- Named functions of the problem go in `functions` ({"name": "f", "expr": "2*x + 3", "args": ["x"], "params": []}) and are then used as f(2), f(g(x)), diff(f(x), x), at(diff(f(x), x), x, 1). Parameters inside a function (like k in x**3 + k*x) go in that function's `params` AND in `vars`.
- Every other symbol used anywhere must be declared in `vars` with a domain: real, positive_real, nonneg_real, integer, positive_integer, nonneg_integer, natural, rational, complex. Counts of people/objects are positive_integer; "tam sayı" integer; "doğal sayı" nonneg_integer; digits integer with constraints 0..9.
- Word constraints become var constraints: "birbirinden farklı" -> x != y; "ardışık" -> y = x + 1; "iki basamaklı" -> n >= 10 and n <= 99 (two constraints); "pozitif" -> x > 0.

## Task kinds (exactly one) and their params (key/value/list triples)
- evaluate: params expr = the quantity the question asks for, in terms of the declared unknowns; givens = ALL equations/inequalities the problem states. Use this for word problems, systems, "x + y kaçtır", function values f(3), compositions, gcd/lcm/remainders (expr like gcd(84, 120) or Mod(5**100, 7)), coordinate-geometry quantities (dist(...), tri_area(...)), determinants.
- solve_equation: a SINGLE equation in ONE unknown whose solution (set) is asked; params var (equation optional, else givens[0]); answer_shape set (or scalar if one value asked). Keep sqrt/log/rational/abs equations in their original form (the domain traps are checked downstream).
- solve_inequality: params var; givens hold the inequality; answer_shape interval (or set).
- count_integers: "kaç tam sayı" satisfying givens; params var; var domain integer; answer_shape count.
- count_roots: "kaç farklı reel kök"; params expr (the polynomial), var, optional distinct; answer_shape count.
- domain_of: "tanım kümesi"; params expr, var; answer_shape set.
- limit: params expr, var, to (number, oo, -oo), optional side '+' or '-'; answer_shape dne_or_scalar when a "yoktur/limit yoktur" option exists, else scalar.
- derivative: params f, var, optional order, optional at (value -> scalar) ; answer_shape expression or scalar.
- antiderivative: params integrand, var; answer_shape expression.
- definite_integral: params integrand, var, a, b; answer_shape scalar.
- tangent_line: params f, var, at, dep (default y); answer_shape equation.
- extremum: params f, var, interval (e.g. [-2, 3], (0, oo)), which = max | min | argmax | argmin | local_max | local_min | local_argmax | local_argmin; answer_shape scalar.
- trig_solve: params var, optional interval (e.g. [0, 2*pi)); the equation is givens[0]; answer_shape set (general solutions use k as an integer parameter, e.g. {pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}).
- equation_of: params object = line_points (p1, p2) | line_point_slope (p, slope) | line_point_parallel / line_point_perpendicular (p, line) | circle_center_radius (center, radius) | circle_center_point (center, point) | circle_diameter (p1, p2) | perpendicular_bisector (p1, p2) | tangent_to_circle_at_point (center, point); points as lists ["x", "y"]; vars x and y declared; answer_shape equation.
- synthetic_geometry: geometry stated with lengths/angles and point names but no coordinates. params points (list of point names, first two fix the frame), constraints (list of EQUATIONS: dist(A,B) = 6, angle(A,B,C) = 90 (degrees), dist(A,B)**2 = dist(A,C)**2, midpoint(M, A, B), parallel(A,B,C,D), perpendicular(A,B,C,D), collinear(A,B,C), equidistant(P,A,B)), target (dist(A,C), angle(A,B,C), area(A,B,C), perimeter(A,B,C)); answer_shape scalar; no vars needed.
- probability: params space (JSON string: {"structure": "product", "sets": [[1,2,3,4,5,6],[1,2,3,4,5,6]]} for dice/coins; {"structure": "combination", "elements": ["k1","k2","k3","m1","m2"], "k": 2} for drawing without replacement; "sequence" with replacement; "permutation" ordered) and event (a Python-style predicate over the outcome tuple t: sum(t) == 7, t.count('T') >= 2, all(x[0] == 'k' for x in t)); answer_shape scalar; sanity ans >= 0, ans <= 1.
- count_structures: params space (as above; "arrangement_all" for all orderings) and optional predicate; answer_shape count.
- recurrence_term: params recurrence (a(n) = a(n-1) + 2*a(n-2)), initial (list of "index=value"), index, var n; answer_shape scalar.
- closed_form: params recurrence, initial, var; answer_shape expression (general term in n).
- series_sum: params term, var, lo, hi (hi may be oo); answer_shape scalar.
- linalg: params op = inverse (matrix) | eigenvalues (matrix; answer_shape set) | eigenvector (matrix, eigenvalue) | solve_system (A, b as "(30, 88)") | matrix_expr (expr); answer_shape expression unless noted.
- proof / unsupported: only when nothing above fits; explain in assumptions.

Decision rules: a quantity asked from several relations -> evaluate (never solve_equation with more than one given). "kaç ... vardır" -> a count kind. "en büyük/en küçük değeri" over an interval -> extremum; "yerel" -> local_*. Coordinates present -> evaluate/equation_of, no coordinates -> synthetic_geometry.

## Multiple choice
List every option as a canonical expression (sets as {..}, intervals as (..), equations as y = 2*x, matrices as Matrix([[..]]), "limit yoktur" as the text yoktur). answer_shape must match the options: set for solution sets, interval for inequalities, count for "kaç", equation for line/circle equations, expression for general terms / derivatives / antiderivatives (write + C as in the options), dne_or_scalar for limits with a yoktur option, scalar otherwise.

## domain_of_discourse and sanity
domain_of_discourse only when the PROBLEM restricts the main variable ("x > 0", "x in (0, oo)"); never derive it from the expressions. sanity: relations on `ans` any valid answer must satisfy (ans > 0 for lengths, ans >= 0 and ans <= 1 for probabilities, ans <= 30 when the count cannot exceed the total).

## Output
JSON matching the schema. Fill every field; "" and [] mean "none". question_en is a faithful English restatement (no solving). assumptions lists anything you had to assume or could not encode. confidence 0-10.
"""

JUDGE_SYSTEM = """You audit formalisations of Turkish math questions. You receive the ORIGINAL question (with its options) and a FORMALISATION (a rendered description plus the raw IR). Decide whether the formalisation states exactly the same problem: same givens (nothing missing, nothing added), same unknown/target, same domain restrictions, same options and answer shape, same units and angle conventions, correct Turkish number reading (3,5 = 3.5; 10.000 = 10000), correct task kind, and NO solved or derived quantity (the IR must not contain the answer or a simplified form of the target).

Scoring: 10 = exactly the same problem; 9 = the same problem up to harmless notation; 8 or below = something is missing, extra, changed, or pre-solved — list every discrepancy concretely. Set faithful=false whenever score <= 8. You are not asked to solve the problem; do not judge whether it is easy or hard. Reply in JSON."""

RESTRUCTURE_SYSTEM = """You convert a free-text math solution (Turkish or English) into the verifier's structured solution format WITHOUT changing its mathematical content. Do not fix errors, do not add steps, do not solve the problem yourself: transcribe what the solution actually claims, including wrong steps.

You are given the problem IR (its variable names, functions and givens). Use exactly those symbol names in step claims.

Step kinds:
- eq: a relation the solution asserts about the unknowns ("b = 30 - a", "x**2 - 4*x = 0", "x in {0, 4}") — one relation per step, canonical syntax, `from` = ids of the steps it is derived from ([] if from the givens).
- compute: a calculation "lhs = rhs" where lhs is an explicit operation: 240/80 = 3, diff(x**2*exp(x), x) = (2*x + x**2)*exp(x), Integral(log(x), x) = x*log(x) - x, Limit(sin(3*x)/x, x, 0) = 3, at(x**3 - 3*x, x, 3) = 18, binomial(6, 3) = 20.
- case: a case assumption ("2*x - 3 = 5"); later steps of that branch reference it in `from`.
- assert: domain/definedness remarks ("x > 3", "x - 2 >= 0").
- note: prose that has no single checkable relation.
- conclude: statements that define an object or announce the result ("y = 2*x - 1", the option letter).
Definitions of new symbols not in the IR (u = sqrt(x+4)) are notes, not eq.

claimed_answer: kind value | set | interval | expression | count | equation | dne | infinite, payload in canonical syntax (sets as {..}, intervals as (..), + C allowed for antiderivatives, "" for dne), option = the letter the solution picks ("" if none). If the solution states several final answers, take the last one. Reply in JSON."""

SOLVER_SYSTEM = """You are a careful mathematics solver. Solve the given Turkish question and report the solution in the verifier's structured format so that every quantitative claim can be machine-checked.

Rules for steps (this is what makes your work verifiable):
- Each step is ONE relation in canonical SymPy-like syntax (explicit '*', '**' for powers, sqrt, log natural, Abs, pi, oo, degrees as 30°).
- kind eq: a relation about the unknowns derived from the givens or earlier steps; `from` lists the step ids it uses ([] when it follows from the problem statement alone).
- kind compute: an explicit calculation "operation = result": 240/80 = 3, diff(x**2*exp(x), x) = (2*x + x**2)*exp(x), Integral(log(x), x) = x*log(x) - x, Limit((x**2 - 4)/(x - 2), x, 2) = 4, at(x**3 - 3*x, x, 3) = 18, binomial(6, 3) = 20, gcd(84, 120) = 12.
- kind case: a case assumption; branch steps cite it in `from`. kind assert: domain conditions. kind note: prose. kind conclude: the final statement / option.
- Use the symbol names you are told to use for the unknowns; declare nothing else — if you need an auxiliary symbol, keep that step as a note.
- Check domain conditions (log arguments, even roots, denominators, one-sided limits) explicitly.
claimed_answer: kind value | set | interval | expression | count | equation | dne | infinite; payload canonical; option = the chosen letter for multiple choice ("" if open-ended). Reply in JSON."""


CRITIC_SYSTEM = """You are a strict step-level reviewer of a mathematical solution (a critic, not a solver). You receive the problem (Turkish question, its formal IR) and the solution as a list of steps, each a single claim with the ids of the steps it is derived from.

Your job: find the FIRST step that is mathematically invalid — a false statement, an inference that does not follow from its cited premises and the problem data, a case that is missed, a domain condition ignored (log argument, even root, denominator, one-sided limit), a wrong formula or identity, an arithmetic slip — even if the final answer happens to be right. A step that is merely terse or non-standard but valid is NOT an error; unusual but correct methods (plugging options, symmetry arguments, guess-and-check with verification) are valid. Do not penalise a step for skipping algebra you can verify yourself. Do not flag `note`/`assert`/`case`/`conclude` steps for style.

If a step is an error, give a `counter_check`: ONE canonical relation (SymPy-like syntax with explicit *, ** for powers) that is TRUE and exposes the mistake, using only the problem's symbols and numbers — for example the correct value of the same computation ("240/80 = 3"), or a concrete instance violating the claimed identity ("sin(3*1) != 3*sin(1)"), or the missed root ("(-2)**2 = 4"). Leave it "" only if no single relation captures the error.

Reply in JSON: assessment = all_steps_valid | error_found | cannot_judge; first_bad_step = the id of the first invalid step ("" if none); error_kind (short label); explanation (2-4 sentences, concrete); counter_check; answer_correct_regardless (true if the final answer is nevertheless right); confidence 0-10."""

META_SYSTEM = """You audit an error report written by another reviewer about a mathematical solution. You receive the problem, the solution steps, and the reviewer's claim (which step is wrong and why, plus a counter-check relation). Decide whether the reported error is REAL: re-derive the step yourself from its premises, check the reviewer's counter-check relation, and consider whether the step is merely non-standard but valid.

Be adversarial towards the reviewer: reviewers frequently hallucinate errors in valid but unusual solutions. Only confirm when you can state concretely what is false. Reply in JSON: error_is_real (boolean), confidence 0-10, explanation (2-4 sentences), corrected_step ("" or the relation the step should have stated)."""


def _load_item(item_id: str) -> dict[str, Any]:
    p = ROOT / "evalset" / "items" / f"{item_id}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def exemplar_block(ids: list[str] | None = None) -> str:
    """Render the exemplar questions with their hand-written IRs in the output format."""
    parts = []
    for iid in ids or EXEMPLAR_IDS:
        try:
            it = _load_item(iid)
        except FileNotFoundError:
            continue
        ir = it["problem_ir"]
        opts = it.get("options") or {}
        q = it["question_tr"]
        if opts:
            q += "\n" + "  ".join(f"{k}) {v}" for k, v in opts.items())
        rendered = ir_to_llm(ir, question_en="", topic=it.get("topic", ""), level=it.get("level", "TYT"))
        rendered["question_en"] = "(omitted in exemplar)"
        parts.append(f"### Question\n{q}\n### IR\n{json.dumps(rendered, ensure_ascii=False)}")
    return "\n\n".join(parts)


def extraction_system_blocks(exemplars: str) -> list[str]:
    """Stable prefix for every extraction call: instructions + exemplars. Kept out of the user
    message so the whole block is a cacheable prefix (~10K tokens; ~10x cheaper on reads)."""
    return [EXTRACT_SYSTEM, "## Exemplars (hand-written, trusted)\n" + exemplars]


def extraction_user_prompt(question_tr: str, options: dict[str, str] | None, level_hint: str | None,
                           exemplars: str = "", feedback: str | None = None,
                           previous_ir: dict | None = None) -> str:
    q = question_tr.strip()
    if options:
        q += "\n" + "  ".join(f"{k}) {v}" for k, v in options.items())
    parts = []
    if exemplars:            # only when the caller cannot use a cached system prefix
        parts.append(f"## Exemplars (hand-written, trusted)\n{exemplars}")
    parts += ["## Task", f"Level hint: {level_hint or 'unknown'}", f"### Question\n{q}"]
    if feedback:
        parts.append("### Previous attempt and audit findings\n"
                     f"Previous IR: {json.dumps(previous_ir, ensure_ascii=False)}\n"
                     f"Findings to fix: {feedback}\nProduce a corrected IR.")
    parts.append("### IR (JSON)")
    return "\n\n".join(parts)
