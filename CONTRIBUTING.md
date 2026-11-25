# Contributing

Contributions are welcome, in English or Turkish. The most valuable contribution is a **wrong
verdict**: a wrong solution the verifier approves, or a correct one it rejects. Use the
"Wrong verdict" issue form and include the problem IR and the solution.

## Setup

Python 3.14 with [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock
uv pip install --python .venv/bin/python --no-deps -e .
export PYTHONUTF8=1
```

Lean 4 + Mathlib is optional ([docs/LEAN_SETUP.md](docs/LEAN_SETUP.md)); without it the Lean tests
skip themselves, which `pytest -rs` shows.

## Checks

```bash
.venv/bin/python -m pytest tests -rs          # the test suite
.venv/bin/python scripts/check.py --plan      # which check your change needs
.venv/bin/python scripts/check.py --full      # all 24 gates (needs Lean; slow)
```

CI runs the test suite without Lean on every pull request. A change to code needs one
`scripts/check.py --full` on its final state before it is merged; `--plan` says so.

## Rules of the project

These come from [CLAUDE.md](CLAUDE.md), which is the authoritative list.

1. **No answer that could be wrong is called `CORRECT`.** If a change widens what is accepted, it
   needs a test with wrong answers. When the meaning of a question depends on a convention, or no
   proof is found, the verdict is `UNKNOWN`.
2. **An improvement that was not measured does not count.** Say which test, gate, probe or mutation
   shows the change, with numbers.
3. **Every finding is tied to a test or a permanent gate.**
4. **The answer key never enters the verification path**, and input is never evaluated as code.
5. **Reports are generated, not written by hand** (`reports/*.md`).
6. **Decisions are logged.** A change to a rule or a mathematical convention gets an entry in
   [DECISIONS.md](DECISIONS.md) with its reason and measurement. A statement that turns out wrong is
   corrected with a dated note, not deleted.

## Conventions

- Code, identifiers and comments under `src/` are in English. Project documents, the decision log
  and commit messages are in Turkish; `README.md`, this file and `SECURITY.md` are in English.
  An English pull request is fine; a maintainer will write the Turkish log entry.
- Commit titles have the form `area: summary`; the body says what was measured and how.
- Never commit `.env`, API keys or `reports/*.json`.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately, not in a public issue.

## License

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
