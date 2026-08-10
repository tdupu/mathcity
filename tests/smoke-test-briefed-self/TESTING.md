# Testing Record: smoke-test-briefed formula

## 1. Artifact under test

- **Path**: `mathcity/formulas/smoke-test-briefed.toml`
- **Type**: formula
- **Tested at git SHA**: to be filled in after commit (run `git rev-parse HEAD`)
- **Test date**: 2026-07-23
- **Tester**: Mayor session Q27 (smoke-test-briefed self-test, pre-commit)

## 2. Test summary

**Outcome: CONDITIONAL** — 5/6 checks pass; 1 check (gc formula registration)
fails because repo-side landing agent has not yet pulled the commit that adds this formula. The
structural checks (file exists, TOML valid, catalog fields, terminal step,
companion skill) all pass.

The single failure is a known pre-sync state, not a formula defect. Expected
to become full PASS after repo-side landing agent pulls the adding commit.

## 3. How to reproduce

**Requirements:**
- macOS/Linux, Python ≥ 3.11 (for `tomllib`)
- Run from the `<city-root>/gascity-packs` rig root
- `gc` on PATH (optional — check 5 only)

**Commands:**
```bash
cd <city-root>/gascity-packs
bash mathcity/tests/smoke-test-briefed-self/smoke_test.sh
```

**Expected passing output (after repo-side landing agent pulls):**
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

**Actual output at time of writing (pre-repo-side landing agent-sync):**
```
smoke-test-briefed self-test results:
  PASS: formula file exists
  PASS: TOML parses without error
  PASS: catalog fields present (name, description, formula, version)
  PASS: terminal step is a brief step
  FAIL: gc formula show smoke-test-briefed succeeds — gc formula show returned non-zero (formula may not be loaded yet)
  PASS: testing-work SKILL.md exists

FAIL — 1/6 checks failed
```

## 4. What this test does NOT cover

- Mathematical correctness (n/a — this is a formula, not a math computation)
- That the formula actually runs end-to-end through the fleet (that requires a live gc sling)
- F-rule compliance of the formula (use `check-formula-hygiene` for that)
- The quality of the test scripts the formula generates for other artifacts

## 5. Recommended next tests

1. **End-to-end fleet test**: sling `smoke-test-briefed` against a real formula
   and confirm the brief lands on the stack. This is the full integration test.
2. **Artifact-type coverage tests**: write one minimal smoke test per artifact
   type (skill, magma-function, python, script) to exercise the classify-artifact
   strategy table.
