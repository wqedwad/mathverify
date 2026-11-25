# mathverify

**A verifier that asks for proof before it calls an AI's math solution correct.**

[Türkçe README](README.md)

Given a math question in Turkish and a solution written by an AI, mathverify returns one of three
verdicts: `CORRECT`, `INCORRECT` or `UNKNOWN`. It does not recompute the answer and compare. It
**proves or refutes the claim**, with symbolic certificates, concrete counterexamples and Lean 4 +
Mathlib proofs. When it cannot prove either way, it does not guess; it answers `UNKNOWN`.

The repository's documents, decision log and commit messages are in Turkish; code, identifiers and
source comments are in English.

| Measure | Result |
|---|---|
| Wrong answers approved | **0** (467 generated wrong answers, 21,139 adversarial attacks, 278 solutions from a real model) |
| Equivalent rewrites and valid step transformations rejected | **0** (224 equivalent answers, 184 step transformations) |
| Audited formal certificates in Lean | 121 of 280 items; proofs on wrong-answer items: **0** |
| Tests | 6045 passed, 5 skipped; 24 of 24 quality gates passed |

The numbers come from the full check run of 3 November 2026 and are read from the generated reports
in [reports/](reports/). The evaluation set is synthetic; see [Limits](#limits).

## Why

Language models grade math in both wrong directions: they approve a confident wrong solution and
reject an unusual correct one. Comparing against an answer key is not enough either: `1/2` and `0.5`
are the same answer, and `x/x = 1` is not true at `x = 0`.

The design has one rule: **no answer that could be wrong is called `CORRECT`.** The price is
coverage. If the meaning of the question depends on a convention, or no proof is found, the verdict
is `UNKNOWN`.

## Three verdicts

These are real outputs of the code in this repository (layer lines shortened).

**Right answer, wrong path → `INCORRECT`.** Distance between A(1, 2) and B(4, 6). The solution says
"4 − 1 = 4, 6 − 2 = 3, √(4² + 3²) = 5". The final answer is right, the first step is wrong:

```console
$ python scripts/verify_cli.py --item evalset/items/ayt-ana-017.json
VERDICT: INCORRECT   confidence=0.970   first_bad_step=1
flags: step_refuted
```

**Two independent proofs → `CORRECT`.** f′(0) for f(x) = x²·eˣ. The symbolic certificate passes and
the same claim is then proved in Lean 4:

```console
$ python scripts/verify_cli.py --item evalset/items/ayt-tur-002.json --lean
VERDICT: CORRECT   confidence=0.995   first_bad_step=None
flags: lean_proved
```

**Meaning depends on a convention → `UNKNOWN`.** "The derivative of xˣ is xˣ(ln x + 1)" depends on
what is meant for x ≤ 0. With no constraint there is no verdict; if the question says `x > 0`, the
same answer is `CORRECT`.

## How it works

| Layer | What it does | Authority |
|---|---|---|
| `certify/` | Tests the claimed answer: algebra, calculus, limits, extrema, trigonometry, geometry, combinatorics, series, linear algebra, word problems | May return `CORRECT` and `INCORRECT` |
| `steps/` | Tries each step of the solution | Rejects only on a counterexample; a step it cannot prove is not penalised |
| `formal/` | Builds the Lean statement from the problem IR by template and proves it with Mathlib tactics | Positive proof only |
| `resolve/`, `meta/`, `critic/` | Signals from another model family | May block `CORRECT`; cannot overturn a certificate |
| `fuse/` | Combines the signals | One hard rejection is enough |

Some of the principles (all of them are in [CLAUDE.md](CLAUDE.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)):

- **The answer key never enters the verification path.** A key-like field in the input stops the
  pipeline with `LeakageError`, and this has its own test.
- **Numerical closeness is not proof.** Exact numbers are compared exactly; a claim is not rounded
  or rewritten before comparison.
- **Definedness is read from the expression as written.** SymPy simplifies `x/x` to 1 and erases
  the undefined point; the verifier reads definedness from the unsimplified form.
- **The model does not write the Lean statement.** It is generated from the IR; every proof is
  audited for `sorry`, axioms, vacuity and unused hypotheses.
- **Lean's junk values cannot produce a certificate.** In Lean `x/0 = 0`, `Real.sqrt (−3) = 0` and
  `Real.log 0 = 0`. Statements that touch these definitions get no formal certificate.
- **Input is not code.** Claims are read only with a guarded parser; malformed input becomes
  `UNKNOWN`, not an exception.

## Measured results

280 items at Turkish university-entrance (TYT, AYT) and university level; 16 topics, 23 task kinds.
Four cells: correct solution (A), correct but unusual solution (B), wrong answer (C), right answer
with a broken step (D).

| Measure | Value | Target | Report |
|---|---|---|---|
| Positive / negative precision (answer level) | 1.000 / 1.000 | ≥ 0.98 | [eval](reports/eval_report.md) |
| Coverage (items with a verdict) | 1.000 | ≥ 0.85 | [eval](reports/eval_report.md) |
| Rejection of unusual correct solutions (B) | 0.000 | < 0.10 | [eval](reports/eval_report.md) |
| Broken step detected (D) | 41 of 42 | reported | [eval](reports/eval_report.md) |
| Generated wrong answers approved | 0 of 467 | 0 | [soundness](reports/soundness_report.md) |
| Equivalent rewrites rejected | 0 of 224 | 0 | [soundness](reports/soundness_report.md) |
| Valid step transformations rejected | 0 of 184 | 0 | [soundness](reports/soundness_report.md) |
| Adversarial attack success (3 surfaces, 21,139 attacks) | 0% | < 2% | [adversarial](reports/adversarial_report.md) |
| Lean certificates; proofs on wrong answers; junk probe | 121 of 280; 0; 0 of 33 | —; 0; 0 | [lean](reports/lean_report.md) |
| Wrong approvals on 278 solutions from a real model | 0 | 0 | [solver](reports/solver_meta_report.md) |

## How the results are kept honest

The project's rule is that an improvement that was not measured does not count.

- **24 gates in one command.** `scripts/check.py --full` runs the tests, static checks, the
  evaluation set, the Lean sweep and the adversarial and metamorphic sweeps; any failure exits 1.
- **The verifier itself is tested.** The metamorphic sweep generates provably wrong and provably
  equivalent answers with SymPy. On its first run 27 of 448 wrong answers were approved; those
  classes were closed and the sweep became a permanent gate.
- **Mutation testing.** The code is broken on purpose to see that fixes are protected; in the last
  measurement all 357 mutations in six lists were caught by a test.
- **Four independent audit rounds.** Every finding was found by measurement, confirmed by
  measurement and tied to a test or a gate. Records are under [denetim/](denetim/).
- **Decision log.** More than 90 decisions with reasons and measurements in
  [DECISIONS.md](DECISIONS.md). A statement that turns out wrong is corrected with a dated note,
  not deleted.

## Limits

- **The evaluation set is synthetic.** The project wrote the items and their solutions; precision
  1.000 is specific to this set. In the real-model measurement the solver answered all 278 questions
  correctly, so that run did not test resistance to wrong approvals. The verifier approved 274 of
  those solutions and wrongly rejected 4.
- **One known wrong approval.** `tyt-prob-018`: a solution with the right answer and a step that is
  true but unjustified gets `CORRECT` at solution level. The step rejecter refutes only with a
  counterexample and cannot refute a true statement.
- **Without steps, `CORRECT` is about the answer only.** The output says so with the
  `answer_level_only` flag.
- **The LLM layers are not fully measured.** Automatic IR extraction and the critic layers have code
  and offline tests; their full measurement has not run yet.
- **The formal layer does not cover everything.** No Lean statement is generated for limits,
  probability, synthetic geometry or improper integrals.

The full list of open items is in [HANDOFF.md](HANDOFF.md) §4.

## Setup

Python 3.14 with [uv](https://docs.astral.sh/uv/) (Linux; on Windows the interpreter is
`.venv/Scripts/python.exe`):

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock
uv pip install --python .venv/bin/python --no-deps -e .
export PYTHONUTF8=1
.venv/bin/python scripts/verify_cli.py --item evalset/items/ayt-ana-017.json
.venv/bin/python -m pytest tests -rs
```

The Lean layer is optional and needs a local Lean 4 + Mathlib install
([docs/LEAN_SETUP.md](docs/LEAN_SETUP.md)); without it the Lean tests are skipped. The
deterministic pipeline needs no API key.

## How it was built

The project was developed between 18 September and 3 November 2026 with Claude Code: agent sessions
did the work under human direction and approval. Standing rules are in [CLAUDE.md](CLAUDE.md), the
hand-off between sessions in [HANDOFF.md](HANDOFF.md), and the reason for every decision in
[DECISIONS.md](DECISIONS.md). The repository history was rewritten before publication (credentials
and personal identifiers were removed), so the short commit ids quoted in the documents do not match
the ids in this repository. Details and the id map: [docs/BASVURU.md](docs/BASVURU.md).
