## What changes

<!-- One or two sentences. Link the issue if there is one. -->

## How it was measured

<!-- This project's rule: an improvement that was not measured does not count.
     Say which test, gate, probe or mutation shows the change, with numbers. -->

## Checklist

- [ ] `python -m pytest tests -rs` passes (say whether Lean was available)
- [ ] `python scripts/check.py --plan` was run and its verdict followed
- [ ] The change cannot turn a wrong answer into `CORRECT`; if it widens what is accepted, a test with wrong answers covers it
- [ ] New behaviour is tied to a test or a gate
- [ ] `DECISIONS.md` has an entry if a rule or a convention changed
