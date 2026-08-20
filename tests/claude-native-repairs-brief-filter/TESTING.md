# Testing Record: brief-check.sh

## 1. Artifact under test

- **Path**: `mathcity/assets/scripts/checks/brief-check.sh`
- **Type**: shell script (bash subcommand dispatcher)
- **Tested at git SHA**: `4e7dd1229bde210508b5c87bb03ccbf97779f374` (repo HEAD at
  test time; the artifact's content was last changed in
  `d7e3255eb7fc1f3d73a0fd15a966d9648ffef534`, "fix(mathcity): check_staging_clear
  cross-step metadata lookup (gsp-89yli)" — no commits between the two touched
  this file)
- **Test date**: 2026-07-28
- **Tester**: `gc.run-operator` session `gt-a8z42`, `smoke-test-briefed` formula
  run, step `run-test` (bead `gsp-wr5yl3`)

## 2. Test summary

**Outcome: PASS** — both smoke-test checks passed. `brief-check.sh` is
syntactically valid bash, and its dispatcher fails safely (exit 1, stderr
mentions `unknown check`) when given an unrecognized subcommand. Nothing
failed.

## 3. How to reproduce

**Requirements:**
- bash (tested under GNU bash 3.2.57(1)-release, macOS arm64-apple-darwin25).
  No other dependencies — no Magma, no Python, no populated `.beads/briefs`
  fixtures.
- No fixed working directory required — the smoke test resolves the artifact
  path relative to its own script location
  (`$SCRIPT_DIR/../../../mathcity/assets/scripts/checks/brief-check.sh`).

**Commands:**
```bash
cd ~/gt/gascity-packs   # or wherever this rig is checked out
bash mathcity/tests/claude-native-repairs-brief-filter/smoke_test.sh
```

To reproduce `results.txt` exactly (stdout+stderr captured, exit code
appended), as the formula's `run-test` step does:
```bash
bash "mathcity/tests/claude-native-repairs-brief-filter/smoke_test.sh" 2>&1 \
  | tee "mathcity/tests/claude-native-repairs-brief-filter/results.txt"
echo "exit_code: ${PIPESTATUS[0]}" >> "mathcity/tests/claude-native-repairs-brief-filter/results.txt"
```

**Expected passing output** (verbatim from `results.txt`):
```
SMOKE TEST: PASS - brief-check.sh is syntactically valid and its dispatcher fails safely (exit 1, stderr mentions 'unknown check') on an unrecognized command
exit_code: 0
```

## 4. What this test does NOT cover

- Mathematical correctness — N/A, this is a shell script, not a math
  computation.
- Any individual `check_*` subcommand's actual gate logic. The dispatcher
  exposes roughly twenty subcommands (`test-evidence`, `mechanical-gates`,
  `disposition`, `pile-entry`, `staging-clear`,
  `no-brainer-classification-evidence`, `decision-record`, and more) and none
  of them are exercised here — that requires a populated `.beads/briefs` tree
  (staging entries, gate-evidence text, stack index) that is out of scope for
  a minimal smoke test.
- Gate-evidence parsing correctness, the no-brainer classification rules, or
  the kill-switch checks (`no-brainer-execute-safety`,
  `server-touching-safety`).
- Behavior when invoked from a live formula (e.g. `brief-shuffle.toml`) as
  part of the real brief pipeline — this test only exercises the script as a
  standalone invocation.
- Performance or resource limits — not measured; the script is a small, fast
  dispatcher with no known resource sensitivity.

## 5. Recommended next tests

1. **Fixture-backed functional tests**: stand up a minimal `.beads/briefs`
   tree (staging entries, gate-evidence text, stack index) and exercise each
   `check_*` subcommand individually against known-good and known-bad
   fixtures, asserting both the exit code and the stdout/stderr message.
2. **Integration test through `brief-shuffle.toml`**: run the formula that
   actually invokes `brief-check.sh`'s dispatcher end-to-end and confirm gate
   outcomes correctly drive brief disposition (this is the "tests grow over
   time" hook — F6.1).
