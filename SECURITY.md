# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on
this repository ([direct link](https://github.com/wqedwad/mathverify/security/advisories/new)).
Do not open a public issue for a vulnerability. Reports are welcome in English or Turkish.

Useful reports include the input that triggers the problem (problem IR, solution or claim text),
the command you ran, and the commit (`git rev-parse --short HEAD`). Only the `master` branch is
supported; there are no released versions yet.

A *wrong verdict* (the verifier approving a wrong solution) is a correctness bug, not a
vulnerability, unless it can be triggered by text that is not mathematics (for example a prompt
injection in the solution). Report it with the "Wrong verdict" issue form.

## What the verifier defends against

The verifier's input is untrusted: it is text written by a language model.

- **Input is not code.** Claims and problem IR text are read only with a guarded parser
  (`guarded_parse_expr`). Raw text and containers are never passed to `sympy.sympify`, which
  evaluates text with Python's builtins reachable. Malformed input becomes `UNKNOWN`; it must not
  surface as an exception or run code. This class was found by an audit on 25 September 2026
  (a counting claim of the form `__import__('os')…` ran inside the verifier) and is covered by
  tests since.
- **The answer key never enters the verification path.** A key-like field in the input stops the
  pipeline with `LeakageError`.
- **Prompt injection cannot produce an approval.** A language-model signal can block `CORRECT`
  but cannot overturn a certificate. The adversarial sweep injects instructions into answers, option
  letters and step claims; none of 21,139 attacks succeeded in the last full run.
- **Lean proofs are audited.** Every proof is checked for `sorry`, axioms, vacuity and unused
  hypotheses, and statements that touch Lean's junk values (`x/0 = 0`) get no certificate.

## What it does not defend against

- **The sandbox is process isolation, not a security boundary.** It exists to bound time and
  memory of symbolic computation. Do not use it to run code written by a model; that needs a real
  sandbox (gVisor, Firecracker or similar).
- **Resource exhaustion.** Budgets are cooperative in some paths; a hostile expression can make a
  single verification slow.
- **Secrets.** API keys for the optional LLM layers are read from an untracked `.env` file or the
  environment and are never written to output, reports or logs. No key belongs in the repository.

Design details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (in Turkish) and the standing rules in
[CLAUDE.md](CLAUDE.md).
