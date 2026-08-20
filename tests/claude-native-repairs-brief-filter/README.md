# Smoke test: brief-check.sh

## What is being tested and why

`mathcity/assets/scripts/checks/brief-check.sh` is the shared subcommand
dispatcher behind the brief-pipeline's mechanical gate checks (used by
formulas such as `brief-shuffle.toml`). Per POLICY-formulas.md F6.1, every
new formula or artifact needs a passing smoke test on record before its
deploy brief is filed. This test gives minimal, read-only confidence that
the script is syntactically valid bash/sh and that its dispatch-and-fail
path behaves safely, without standing up real `.beads/briefs` fixtures to
exercise each individual `check_*` function.

## How to run

```bash
bash mathcity/tests/claude-native-repairs-brief-filter/smoke_test.sh
```

No arguments or environment setup required; the script locates the artifact
relative to its own path, so it can be invoked from any working directory.

## What a passing result looks like

Exit code `0` and a single summary line:

```
SMOKE TEST: PASS - brief-check.sh is syntactically valid and its dispatcher fails safely (exit 1, stderr mentions 'unknown check') on an unrecognized command
```

## Known limitations / what is NOT tested

- Does **not** exercise any real `check_*` function (`test-evidence`,
  `mechanical-gates`, `disposition`, `pile-entry`, etc.) — those require a
  populated `.beads/briefs` tree (staging entries, gate-evidence text, stack
  index) that is out of scope for a minimal smoke test.
- Does **not** verify gate-evidence parsing logic, the no-brainer
  classification rules, or the kill-switch checks — only that the script
  parses and that an unrecognized command fails safely with no side effects.
- Does not modify `brief-check.sh` or any repository state; it is read-only
  and creates no files, so there is nothing for it to clean up.
