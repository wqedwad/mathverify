"""F5 sweep with NO model calls: deterministic statement + Mathlib tactic ladder + audits.

    python -m harness.run_lean [--limit N] [--timeout 45] [--out reports]

Measures the F5 gate directly: how many items get a formal certificate, and whether any
item whose claimed answer is WRONG is ever proved (must be zero: a false statement is
unprovable, so a proof here would mean the statement does not say what the claim says).
`lean_results.json` also records `lean_available`: whether the Mathlib REPL booted in this run,
so "zero certificates" never reads as a clean result when Lean was simply absent. Because Lean
can also be lost DURING the run (REPL OOM-killed and not respawnable), every record with a
statement carries `lean_reached` (plus prove_statement's `errors`), and `lean_available_end`
re-probes Lean after the junk probe. A reached REPL can still leave a statement unjudged: some
or all tactic attempts timed out, or the audit probes of a proof did. So every such record also
carries `lean_answered` (at least one attempt judged), the attempt counts `n_attempts` /
`n_unanswered`, and `audit_unanswered`: the audit probes of a proved statement Lean did not
answer. A Lean error on every attempt is still an answer, but when the error is about the
statement itself (a template that does not elaborate) Lean never judged the claimed value; so
every statement is also sent once with the body `sorry` and carries `elaborates` (see
elaboration_fields). scripts/check.py fails the FP and junk gates unless every attempt and every
audit probe on each wrong-answer item and each junk statement got a Lean verdict and each of
those statements elaborates.
"""
from __future__ import annotations
import argparse, json, sys, time
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))
from harness.loader import load_items, split_for_verifier  # noqa: E402
# one classification of "Lean gave no verdict" for the ladder, the audit and this sweep: prove's own
from mathverify.formal import prove as _prove  # noqa: E402
from mathverify.formal.lean_client import LeanResult, LeanUnavailable  # noqa: E402
NO_VERDICT, lean_judged = _prove.NO_VERDICT, _prove.lean_judged


def _answer_is_right(it, ir, sol, labels) -> bool:
    """Is the CLAIMED VALUE mathematically right? (The formal layer certifies the value, not
    the reasoning, so this is the reference a Lean proof must be judged against.)

    Cells A, B and D carry a correct answer by construction — including B items whose answer is
    a valid but non-canonical representative (e.g. a different eigenvector), which a literal
    comparison with the gold string would wrongly call wrong. Only C items need the comparison,
    because some of them are wrong solely in the option letter while the value is right.
    """
    import sympy as sp
    from mathverify.normalize.parse import build_namespace, parse_answer
    from mathverify.intake.structured import load_problem_ir
    from mathverify.equiv import answers_equivalent
    if labels["cell"] in ("A", "B", "D"):
        return True
    ca = sol["claimed_answer"]
    gold = it["gold_answer"]
    try:
        ns = build_namespace(load_problem_ir(ir))
        if ca["kind"] == "dne":
            return str(gold).strip().upper() == "DNE"
        a = parse_answer(ca["kind"], ca["payload"], ns)
        shape = "set" if isinstance(a, sp.Set) else ("count" if ca["kind"] == "count" else "scalar")
        b = parse_answer("set" if shape == "set" else ("count" if shape == "count" else "value"), gold, ns)
        ok, _ = answers_equivalent(a, b, shape=shape)
        return bool(ok)
    except Exception:
        return False


# Claims that are FALSE in real mathematics but TRUE about Lean's totalised operations
# (x/0 = 0, sqrt of a negative = 0, log 0 = 0, tan(pi/2) = 0, the integral of a non-integrable
# function = 0). Before the definedness guards in formal/statement.py, five of these received
# clean, audited certificates. Every run re-checks them: a single certificate here is a false
# positive of the formal layer, whatever the evaluation set says.
def _ir(kind, params, vars_=(), givens=(), shape="scalar", dod=None):
    d = {"task": {"kind": kind, "params": params}, "vars": [dict(v) for v in vars_],
         "givens": list(givens), "answer_shape": shape}
    if dod is not None:
        d["domain_of_discourse"] = dod
    return d


JUNK_PROBES = [
    ("tan(pi/2) = 0", _ir("evaluate", {"expr": "tan(pi/2)"}), {"kind": "value", "payload": "0"}),
    ("sqrt(2-5) = 0", _ir("evaluate", {"expr": "sqrt(2 - 5)"}), {"kind": "value", "payload": "0"}),
    ("0/0 = 0", _ir("evaluate", {"expr": "(2**2 - 4)/(2 - 2)"}), {"kind": "value", "payload": "0"}),
    ("log 0 = 0", _ir("evaluate", {"expr": "log(0)"}), {"kind": "value", "payload": "0"}),
    ("sin 0 = sqrt(-4)", _ir("evaluate", {"expr": "sin(0)"}), {"kind": "value", "payload": "sqrt(-4)"}),
    ("int_{-1}^{1} dx/x = 0", _ir("definite_integral", {"integrand": "1/x", "var": "x", "a": "-1", "b": "1"},
                                  [{"name": "x"}]), {"kind": "value", "payload": "0"}),
    ("sqrt'(-1) = 0", _ir("derivative", {"f": "sqrt(x)", "var": "x", "at": "-1"}, [{"name": "x"}]),
     {"kind": "value", "payload": "0"}),
    ("log'(-1) = -1", _ir("derivative", {"f": "log(x)", "var": "x", "at": "-1"}, [{"name": "x"}]),
     {"kind": "value", "payload": "-1"}),
    ("max -1/x^2 on [-1,1] = 0", _ir("extremum", {"f": "-1/x**2", "var": "x", "interval": "[-1, 1]", "which": "max"},
                                     [{"name": "x"}]), {"kind": "value", "payload": "0"}),
    ("sum_{k=-1}^{1} 1/k = 0", _ir("series_sum", {"term": "1/k", "var": "k", "lo": "-1", "hi": "1"},
                                   [{"name": "k", "domain": "integer"}]), {"kind": "value", "payload": "0"}),
    ("x = 2 from 1/(x-2) = 0", _ir("evaluate", {"expr": "x"}, [{"name": "x"}], ["1/(x - 2) = 0"]),
     {"kind": "value", "payload": "2"}),
    ("(sqrt(-x^2-1))' = 0", _ir("derivative", {"f": "sqrt(-x**2 - 1)", "var": "x"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "0"}),
    # templates added 23 Sep (domain_of, simplify_expression, count_solutions)
    ("sqrt(-x^2-1) simplifies to 0", _ir("simplify_expression", {"expr": "sqrt(-x**2 - 1)"}, [{"name": "x"}],
                                        shape="expression"), {"kind": "expression", "payload": "0"}),
    ("1/(x-x) simplifies to 0", _ir("simplify_expression", {"expr": "1/(x - x)"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "0"}),
    ("x simplifies to x^2/x", _ir("simplify_expression", {"expr": "x"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "x**2/x"}),
    ("domain of 1/(x-2) is R", _ir("domain_of", {"expr": "1/(x - 2)", "var": "x"}, [{"name": "x"}], shape="set"),
     {"kind": "set", "payload": "(-oo, oo)"}),
    ("#{x/y = 0 in [0,2]^2} = 6 (Z division)",
     _ir("count_solutions", {"bounds": {"x": ["0", "2"], "y": ["0", "2"]}},
         [{"name": "x", "domain": "nonneg_integer"}, {"name": "y", "domain": "nonneg_integer"}], ["x/y = 0"],
         shape="count"), {"kind": "count", "payload": 6}),
    # families found by the formal-layer audit of 25 Sep 2026: 53 of 98 wrong claims were certified
    # (tests/test_lean_audit_2026_09_25.py has them all). One or more of each, so the junk gate
    # fails if any family ever certifies again.
    # closed goals elaborated in ℕ, where 7 / 2 = 3 and 1 / 2 = 0
    ("7/2 = 3 (ℕ division in a closed goal)", _ir("evaluate", {"expr": "7/2"}), {"kind": "value", "payload": "3"}),
    ("2^(-1) = 0 (ℕ division in a closed goal)", _ir("evaluate", {"expr": "2**(-1)"}),
     {"kind": "value", "payload": "0"}),
    # Mod beyond "integer mod a positive literal": Lean's ℤ % is Euclidean, x % 0 = x, ℝ % is 0
    ("7 mod -2 = 1 (negative divisor)", _ir("evaluate", {"expr": "Mod(7, -2)"}), {"kind": "value", "payload": "1"}),
    ("7 mod 0 = 7 (zero divisor)", _ir("evaluate", {"expr": "Mod(7, 0)"}), {"kind": "value", "payload": "7"}),
    ("x mod n = 1 (symbolic divisor)", _ir("evaluate", {"expr": "Mod(x, n)"},
                                           [{"name": "x", "domain": "integer"}, {"name": "n", "domain": "integer"}],
                                           ["x = 7", "n = 2"]), {"kind": "value", "payload": "1"}),
    ("x mod 2 simplifies to 0 (real x)", _ir("simplify_expression", {"expr": "Mod(x, 2)"}, [{"name": "x"}],
                                             shape="expression"), {"kind": "expression", "payload": "0"}),
    # ℕ subtraction in a recurrence: a(1 - 2) is a(0) in Lean, undefined in the problem
    ("a(3) = 5 from a(n) = a(n-1) + a(n-2), a(0) = 1 only (ℕ subtraction)",
     _ir("recurrence_term", {"name": "a", "var": "n", "recurrence": "a(n) = a(n-1) + a(n-2)", "initial": {"0": "1"},
                             "index": 3}, [{"name": "n", "domain": "integer"}]), {"kind": "value", "payload": "5"}),
    # a dropped restriction: the answer to a different question
    ("root 2 of 2x = 4 over x > 5 (domain_of_discourse dropped)",
     _ir("solve_equation", {"equation": "2*x = 4", "var": "x"}, [{"name": "x"}], shape="set", dod="x > 5"),
     {"kind": "set", "payload": "{2}"}),
    ("root 2 of 2x = 4 with constraint x > 5 (var constraint dropped)",
     _ir("solve_equation", {"equation": "2*x = 4", "var": "x"}, [{"name": "x", "constraints": ["x > 5"]}], shape="set"),
     {"kind": "set", "payload": "{2}"}),
    ("root 2 of 2x = 4, x > 5 (second given dropped)",
     _ir("solve_equation", {"var": "x"}, [{"name": "x"}], ["2*x = 4", "x > 5"], shape="set"),
     {"kind": "set", "payload": "{2}"}),
    ("x^2 < 4 with x > 0 is (-2, 2) (given dropped)",
     _ir("solve_inequality", {"inequality": "x**2 < 4", "var": "x"}, [{"name": "x"}], ["x > 0"], shape="interval"),
     {"kind": "interval", "payload": "(-2, 2)"}),
    ("x^2 = -1 over C has no root (complex read as R)",
     _ir("solve_equation", {"equation": "x**2 = -1", "var": "x"}, [{"name": "x", "domain": "complex"}], shape="set"),
     {"kind": "set", "payload": "EmptySet"}),
    # contradictory givens the vacuity probe could not see (no satisfiability witness either)
    ("a + b = 42 from a^2 + b^2 < 2ab (contradictory givens)",
     _ir("evaluate", {"expr": "a + b"}, [{"name": "a"}, {"name": "b"}], ["a**2 + b**2 < 2*a*b"]),
     {"kind": "value", "payload": "42"}),
    # the simplifying parse: undefined points of the problem's text disappear
    ("root 0 of x^2/x = 0 (x/x folded)", _ir("solve_equation", {"equation": "x**2/x = 0", "var": "x"}, [{"name": "x"}],
                                             shape="set"), {"kind": "set", "payload": "{0}"}),
    ("int_{-2}^{-1} exp(log x) dx = -3/2 (exp(log x) folded)",
     _ir("definite_integral", {"integrand": "exp(log(x))", "var": "x", "a": "-2", "b": "-1"}, [{"name": "x"}]),
     {"kind": "value", "payload": "-3/2"}),
    # the claim's junk region: Real.log x = log|x|
    ("int dx/x = log x + C (log of a negative)",
     _ir("antiderivative", {"integrand": "1/x", "var": "x"}, [{"name": "x"}], shape="expression"),
     {"kind": "expression", "payload": "log(x) + C"}),
]


LEAN_UNAVAILABLE = "lean_unavailable"


def lean_reached(r: dict) -> bool:
    """Did every Lean call this statement needed get through to a running REPL?

    When the REPL is gone and cannot be respawned (e.g. OOM-killed), prove_statement stops with
    an error starting `lean_unavailable` and returns proved=False. Without this flag such a
    record reads exactly like "Lean could not prove it": a sweep that lost Lean after its first
    item still passed all four Lean gates, junk probe included, although no junk statement had
    reached Lean. A statement Lean did answer (even with a timeout or a crash it recovered from)
    counts as reached.
    """
    return not any(str(e).startswith(LEAN_UNAVAILABLE) for e in r.get("errors") or [])


def attempt_answered(a: dict) -> bool:
    """Did Lean itself judge this attempt? prove.lean_judged on the attempt as prove_statement
    recorded it (`ok` is the result's `clean`): a compiled proof did; a failed one only when it
    carries at least one Lean error that is not a transport failure (prove.NO_VERDICT: timeout,
    dead REPL, broken pipe, bad JSON). A failure with no error at all (e.g. a REPL-level `message`;
    none among the 869 attempts of the 24 Sep full sweep) counts as unanswered: fail closed."""
    return lean_judged(LeanResult(ok=bool(a.get("ok")), errors=list(a.get("errors") or [])))


def lean_answered(r: dict) -> bool:
    """Did at least one attempt on this statement get a real answer from Lean?

    lean_reached only says the REPL was there. When every tactic of the ladder hits the timeout,
    the REPL is killed and respawned each time, prove_statement records no `lean_unavailable`
    error and the statement counts as reached, although Lean never judged it: a junk probe made
    only of such statements reported "0/17 certified" with no junk statement evaluated. This flag
    alone is not what scripts/check.py gates on: one cheap tactic answered and every heavy one
    timed out still makes it True, so the gate also needs `n_unanswered` == 0 and an empty
    `audit_unanswered` (see statement_silent).
    """
    return any(attempt_answered(a) for a in r.get("attempts") or [])


# prove._axioms_of's placeholder when `#print axioms` gave no parseable verdict (timeout, dead REPL)
AXIOMS_UNKNOWN = "<unknown>"


def audit_unanswered(r: dict) -> list[str]:
    """The audit probes of a PROVED statement that Lean did not answer: prove._audit's own
    `unanswered` list ("vacuity", "no_hyp") plus "axioms" when `#print axioms` gave no verdict
    (AXIOMS_UNKNOWN). An unproved statement is never audited: []. A proved one whose audit is
    missing or malformed gives ["audit"]: fail closed.

    Every probe that times out makes the audit unclean, so the proof gets no certificate; but that
    refusal is silence, not Lean's verdict. The junk statement `x = 2 from 1/(x-2) = 0` compiles
    in the real sweep and only the answered vacuity probe (its hypotheses contradict each other)
    keeps it from a certificate; with both probes timed out the junk gate still read "0/17"
    (reviewer's junk_audit_silence_probe.py), and so would a wrong-answer item for "Lean FP 0".
    """
    if not r.get("proved"):
        return []
    audit = r.get("audit")
    if not isinstance(audit, dict) or not isinstance(audit.get("unanswered"), list):
        return ["audit"]
    out = [str(p) for p in audit["unanswered"]]
    axioms = audit.get("axioms")
    if not isinstance(axioms, list) or AXIOMS_UNKNOWN in axioms:
        out.append("axioms")
    return out


def lean_fields(r: dict) -> dict:
    """What run_lean stores per statement about how far Lean got with it."""
    attempts = r.get("attempts") or []
    return {"lean_reached": lean_reached(r), "lean_answered": lean_answered(r), "n_attempts": len(attempts),
            "n_unanswered": sum(1 for a in attempts if not attempt_answered(a)),
            "audit_unanswered": audit_unanswered(r), "errors": list(r.get("errors") or [])}


def statement_silent(rec: dict) -> bool:
    """Did Lean leave anything on this stored statement unjudged: an attempt or an audit probe?
    For a junk statement or a wrong-answer item this fails its gate in scripts/check.py; a
    right-answer item only loses its certificate."""
    return (not rec["lean_answered"]) or rec["n_unanswered"] > 0 or bool(rec["audit_unanswered"])


# The elaboration check: the statement once with the body `sorry`, autoImplicit off. An attempt
# that fails because the STATEMENT does not elaborate (unknown identifier from a broken template,
# a type error) carries a real Lean error, so it counts as answered, and a wrong-answer item or a
# junk statement made only of such attempts passed "Lean FP 0" / junk "0/17" although Lean never
# judged the claimed value (reviewer's unelaborated_probe.py). autoImplicit is off because with
# Lean's default an unknown ATOMIC name (`x = brokenc`) is silently bound as an implicit variable
# and elaborates; off, it is an error. Measured on 24 Sep (live Lean, r6 sorry_shape_probe*.py):
# all 175 sweep statements (122 right-answer items, 50 wrong-answer items, 3 junk) come back with no
# error, exactly one sorry and no REPL `message`, with autoImplicit on and off alike, 2.2-2.5 s for
# all 175 (slowest 42 ms); an unknown dotted name, an unknown atomic name (off only), a type error
# and a parse error each give a Lean error. The check itself is measurement-only (no verifier call
# makes it), but since 24 Sep the verifier compiles with the same option: LeanStatement.theorem and
# both audit probes start with statement.AUTOIMPLICIT_OFF, so st.theorem() already carries it.
from mathverify.formal.statement import AUTOIMPLICIT_OFF as ELAB_PREFIX  # noqa: E402


def elaboration_code(st) -> str:
    code = st.theorem("  sorry")          # opens with ELAB_PREFIX (statement.AUTOIMPLICIT_OFF)
    # the check must not depend on that: should theorem() ever drop the option, add it here
    return code if code.startswith(ELAB_PREFIX) else ELAB_PREFIX + code


def elaboration_verdict(r: LeanResult) -> bool | None:
    """Does Lean's reply show that the statement elaborates? True: Lean answered with no
    error-severity message (the `sorry` warning is expected), no REPL `message`, and the `sorry` of
    the body reported (the statement was read up to its proof). False: Lean answered with an error,
    or without reaching the body. None: no verdict (timeout, dead REPL, broken pipe, bad JSON, a
    REPL-level `message` such as an unknown environment): fail closed in scripts/check.py."""
    if r.timed_out or not isinstance(r.raw, dict) or "message" in r.raw:
        return None
    if r.errors:
        return False
    return bool(r.ok and r.sorries)


def elaboration_fields(st, timeout: float) -> dict:
    """`elaborates` (elaboration_verdict) and `elab_errors` (the first Lean errors, or the REPL
    message) of one elaboration check. It runs on prove's client (`prove.get_lean`, the thread-local
    REPL prove_statement uses). Lean gone for good gives None plus a `lean_unavailable` error, which
    add_elaboration also records as the statement not having reached Lean."""
    try:
        r = _prove.get_lean().run(elaboration_code(st), timeout=timeout)
    except LeanUnavailable as e:
        return {"elaborates": None, "elab_errors": [f"{LEAN_UNAVAILABLE}: {e}"]}
    errs = [str(e)[:300] for e in r.errors[:2]]
    if not errs and isinstance(r.raw, dict) and "message" in r.raw:
        errs = [f"REPL message: {str(r.raw['message'])[:300]}"]
    return {"elaborates": elaboration_verdict(r), "elab_errors": errs}


ELAB_NOT_SENT = "not sent: Lean unavailable for this statement"


def add_elaboration(rec: dict, st, timeout: float) -> dict:
    """Store the elaboration check on a statement's record (after lean_fields). A check that found
    Lean gone makes the statement unreached, like a lost ladder or audit call. A statement that is
    already unreached gets no check (None): every Lean gate fails on it anyway, and a second
    respawn attempt can cost up to the REPL's boot timeout (300 s) per statement."""
    if rec.get("lean_reached") is False:
        rec.update({"elaborates": None, "elab_errors": [ELAB_NOT_SENT]})
        return rec
    fields = elaboration_fields(st, timeout)
    rec.update(fields)
    lost = [e for e in fields["elab_errors"] if e.startswith(LEAN_UNAVAILABLE)]
    if lost:
        rec["lean_reached"] = False
        rec["errors"] = list(rec.get("errors") or []) + lost
    return rec


def statement_unelaborated(rec: dict) -> bool:
    """Is this stored statement not shown to elaborate? For a junk statement or a wrong-answer item
    this fails its gate in scripts/check.py; a right-answer item fails no gate."""
    return rec.get("elaborates") is not True


def junk_probe(timeout: float) -> list[dict]:
    from mathverify.formal import build_statement, prove_statement
    out = []
    for label, ir, ca in JUNK_PROBES:
        st = build_statement(ir, ca)
        rec = {"label": label, "statement": bool(st), "certified": False}
        if st is not None:
            r = prove_statement(st, use_model=False, tactic_timeout=timeout)
            rec["certified"] = bool(r["proved"] and (r.get("audit") or {}).get("clean"))
            rec["proved"] = r["proved"]
            rec["audit"] = r.get("audit")
            rec.update(lean_fields(r))
            add_elaboration(rec, st, timeout)
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    # 45 s is what scripts/check.py and every report use; measured on 23 Sep, 60 s certifies the
    # same 107 items, so the standalone default now matches the gate
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--out", default=str(ROOT / "reports"))
    args = ap.parse_args(argv)
    from mathverify.formal import build_statement, prove_statement, lean_available
    items = load_items(ROOT / "evalset" / "items")
    if args.limit:
        items = items[:args.limit]
    t0 = time.time()
    # "Lean was available in this run" = this probe, before the sweep, came back clean. It goes
    # through the same thread-local client the sweep uses (get_lean), so the REPL it boots is the
    # one that proves the items, never a second one. Clean requires all of: the REPL process
    # started, `import Mathlib` returned an environment, LeanClient._spawn's Mathlib probe
    # ((2 : ℝ) + 2 = 4 by norm_num) compiled, and a first check on that environment compiled with
    # no error and no sorry. Without this flag a machine with no Lean at all wrote 0 certificates
    # with exit 0, and check.py's Lean gates passed vacuously on it. The sweep itself is not
    # changed: when the probe fails, every item is still attempted, exactly as before.
    lean_ok = lean_available()
    print(f"lean_available={lean_ok}", flush=True)
    recs, kinds = [], Counter()
    for i, it in enumerate(items, 1):
        ir, sol, labels = split_for_verifier(it)
        st = build_statement(ir, sol["claimed_answer"])
        rec = {"id": it["id"], "cell": labels["cell"], "topic": labels["topic"],
               # the formal layer certifies the claimed VALUE, so the reference is the value
               # itself: a C item whose only defect is the option letter has a right value
               "answer_right": _answer_is_right(it, ir, sol, labels), "task": ir["task"]["kind"],
               "statement": bool(st), "kind": st.kind if st else None, "proved": False, "clean": None}
        if st is not None:
            kinds[st.kind] += 1
            r = prove_statement(st, use_model=False, tactic_timeout=args.timeout)
            rec.update({"proved": r["proved"], "clean": (r.get("audit") or {}).get("clean"),
                        "proof": r.get("proof"), "audit": r.get("audit"), "ms": round(r["ms"]),
                        "stmt_text": r.get("statement"), **lean_fields(r)})
            # every item, right-answer ones too (they fail no gate on it; 2.5 s for all 175)
            add_elaboration(rec, st, args.timeout)
        recs.append(rec)
        if i % 20 == 0 or rec["proved"]:
            print(f"[{i}/{len(items)}] {rec['id']:<16} stmt={rec['statement']} proved={rec['proved']} clean={rec['clean']}", flush=True)
    n = len(recs)
    with_stmt = [r for r in recs if r["statement"]]
    proved = [r for r in recs if r["proved"]]
    certified = [r for r in proved if r["clean"]]
    fp = [r for r in certified if not r["answer_right"]]
    out = Path(args.out); out.mkdir(exist_ok=True)
    junk = junk_probe(args.timeout)
    # The probe above only says Lean was there when the sweep STARTED. Re-probe once the junk
    # probe is done (same thread-local client): Lean lost after the last statement shows here,
    # Lean lost before it shows as records with lean_reached False.
    lean_end = lean_available()
    unreached = [r.get("id") or r.get("label") for r in recs + junk if r["statement"] and not r["lean_reached"]]
    # Lean left an attempt or an audit probe unjudged (timeout, dead REPL). check.py fails the junk
    # gate on any such junk statement and the FP gate on any such wrong-answer item; a right-answer
    # item only loses its certificate
    stmts = [r for r in recs + junk if r["statement"]]
    n_att = sum(r["n_attempts"] for r in stmts)
    n_un = sum(r["n_unanswered"] for r in stmts)
    proved_stmts = [r for r in stmts if r.get("proved")]
    audit_silent = [r for r in proved_stmts if r["audit_unanswered"]]
    silent_items = [r for r in recs if r["statement"] and statement_silent(r)]
    silent_wrong = [r["id"] for r in silent_items if not r["answer_right"]]
    silent_junk = [j["label"] for j in junk if j["statement"] and statement_silent(j)]
    # the elaboration check, per group: (elaborates, statements, the ones that do not)
    groups = {"right": [r for r in recs if r["statement"] and r["answer_right"]],
              "wrong": [r for r in recs if r["statement"] and not r["answer_right"]],
              "junk": [j for j in junk if j["statement"]]}
    elab = {g: (sum(1 for r in rows if not statement_unelaborated(r)), len(rows),
                [r.get("id") or r.get("label") for r in rows if statement_unelaborated(r)])
            for g, rows in groups.items()}
    elab_txt = " ".join(f"{g}={a}/{n}{' ' + str(bad[:10]) if bad else ''}" for g, (a, n, bad) in elab.items())
    print(f"lean_available_end={lean_end} lean_unreached={len(unreached)} "
          f"lean_unanswered_attempts={n_un}/{n_att} lean_audit_unanswered={len(audit_silent)}/{len(proved_stmts)} "
          f"lean_silent_items={len(silent_items)} "
          f"(wrong answer: {len(silent_wrong)}{' ' + str(silent_wrong) if silent_wrong else ''}) "
          f"lean_silent_junk={len(silent_junk)}{' ' + str(silent_junk) if silent_junk else ''} "
          f"elaborates: {elab_txt}", flush=True)
    (out / "lean_results.json").write_text(json.dumps({"lean_available": lean_ok, "lean_available_end": lean_end,
                                                       "records": recs, "junk_probe": junk},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    md = "# F5 (Lean) taraması — modelsiz, deterministik ifade + Mathlib taktik merdiveni\n\n"
    md += f"- Lean REPL (Mathlib) bu koşuda açıldı: **{'evet' if lean_ok else 'hayır'}**"
    md += f" · taramanın sonunda erişilebilir: **{'evet' if lean_end else 'hayır'}**"
    md += f" · Lean'e ulaşamayan ifade: **{len(unreached)}**{' ✗ ' + str(unreached[:10]) if unreached else ''}\n"
    md += (f"- Lean'in cevap vermediği taktik denemesi (zaman aşımı ya da REPL çökmesi): **{n_un}/{n_att}**"
           f" · denetim sondası (aksiyom/vakum/hipotezsiz) cevapsız kalan kanıt: **{len(audit_silent)}/{len(proved_stmts)}**"
           f"{' ' + str([r.get('id') or r.get('label') for r in audit_silent[:10]]) if audit_silent else ''}\n")
    md += (f"- En az bir denemesi ya da denetim sondası cevapsız kalan ifade: öğe **{len(silent_items)}**"
           f"{' ' + str([r['id'] for r in silent_items[:10]]) if silent_items else ''}"
           f" · bunlardan cevabı yanlış (FP kapısı düşer): **{len(silent_wrong)}**"
           f"{' ✗ ' + str(silent_wrong) if silent_wrong else ''}"
           f" · junk sondası (junk kapısı düşer): **{len(silent_junk)}**{' ✗ ' + str(silent_junk) if silent_junk else ''}\n")
    a_r, n_r, _ = elab["right"]
    a_w, n_w, bad_w = elab["wrong"]
    a_j, n_j, bad_j = elab["junk"]
    md += (f"- Lean'de derlenen ifade (`sorry` gövdesiyle, autoImplicit kapalı): cevabı doğru öğe **{a_r}/{n_r}**"
           f" · cevabı yanlış öğe (FP kapısı) **{a_w}/{n_w}**{' ✗ ' + str(bad_w[:10]) if bad_w else ''}"
           f" · junk sondası (junk kapısı) **{a_j}/{n_j}**{' ✗ ' + str(bad_j) if bad_j else ''}\n")
    md += f"- Öğe: **{n}** · Lean ifadesi üretilebilen: **{len(with_stmt)}** ({len(with_stmt)/n:.1%})\n"
    md += f"- Kanıtlanan: **{len(proved)}** · denetimden geçen (sorry/aksiyom/vakum/kullanılmayan hipotez): **{len(certified)}**\n"
    md += f"- **Yanlış cevaplı öğelerde kanıt (FP): {len(fp)}** {'✓ hedef 0' if not fp else '✗ ' + str([r['id'] for r in fp])}\n"
    md += f"- Kapsama (tüm sette formal sertifika): {len(certified)/n:.1%} · ifadesi olanlar içinde: {len(certified)/max(1,len(with_stmt)):.1%}\n"
    md += f"- Şablon türleri: {dict(kinds)}\n"
    md += f"- Süre: {time.time()-t0:.0f} s (ortalama {(time.time()-t0)/n*1000:.0f} ms/öğe)\n\n"
    bad_junk = [j["label"] for j in junk if j["certified"]]
    md += (f"- **Junk-value sondası:** {len(junk)} gerçekte yanlış iddia (Lean'in x/0 = 0, √(−1) = 0, "
           f"log 0 = 0 gibi tamamlamalarında doğru) · ifade üretilen: {sum(j['statement'] for j in junk)} · "
           f"**sertifika alan: {len(bad_junk)}** (hedef 0){' ✗ ' + str(bad_junk) if bad_junk else ' ✓'}\n\n")
    byc = Counter(r["cell"] for r in certified)
    md += f"- Sertifikalı öğelerin hücre dağılımı: {dict(byc)} (D hücresi = cevabı doğru, adımı bozuk: formal katman cevabı onaylar, adımı değil)\n"
    used = Counter(r["proof"] for r in certified)
    md += f"- Kullanılan taktikler: {dict(used)}\n"
    unproved = [r for r in with_stmt if not r["proved"]]
    md += f"\n## İfadesi üretilip kanıtlanamayanlar ({len(unproved)})\n\n"
    for r in unproved[:40]:
        md += f"- {r['id']} [{r['kind']}] {('cevap doğru' if r['answer_right'] else 'cevap YANLIŞ (kanıtlanamaması beklenir)')}: `{(r.get('stmt_text') or '')[:150]}`\n"
    (out / "lean_report.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
