# Smoke test: smoke-test-briefed formula (self-test)

Tests that the `smoke-test-briefed.toml` formula is well-formed and registered
in the gc catalog. This is the F6.1 baseline test for the testing formula itself.

## How to run

```bash
cd <mathcity-checkout>
bash tests/smoke-test-briefed-self/smoke_test.sh
```

## Expected output (passing)

```
smoke-test-briefed self-test results:
  PASS: formula file exists
  PASS: TOML parses without error
  PASS: catalog fields present (name, description, formula, version)
  PASS: terminal step is a brief step
  PASS: gc formula show smoke-test-briefed succeeds
  PASS: testing-work SKILL.md exists

PASS — 6/6 checks passed
```

## Known limitation

Check 5 (`gc formula show`) requires the active city import to resolve to a
checkout or release that contains this formula. Until the city import is
updated, check 5 returns FAIL (non-zero exit from `gc`).
Checks 1–4 and 6 pass regardless of repo-side landing agent sync state. The overall test exits 1
when check 5 fails; re-run after repo-side landing agent pulls to get full PASS.
