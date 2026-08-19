---
name: testing-work
description: >
  Dispatch a smoke-test run for a mathcity artifact (formula TOML, skill
  SKILL.md, Magma intrinsic, Magma function, Python script, or shell script)
  through the fleet via the `smoke-test-briefed` formula. Satisfies F6.1
  (POLICY-formulas.md): every new formula needs a passing smoke test before
  its deploy brief. Use when the user says "test this formula", "smoke test",
  "run a smoke test", "testing-work", "dispatch testing", "create a test for",
  "write a test for", "test this skill", "test this script", "test-work",
  "check if this works", "F6.1 gate", or "run the testing formula". Companion
  to formula-work (which creates formulas) and skill-creator-math (which
  creates skills). NOT for authorizing high-risk test execution (use
  test-execution-request). NOT for running tests inline without a brief gate.
---

# testing-work — dispatch a smoke-test brief through the fleet

Companion dispatch skill for [`smoke-test-briefed`](../../../../formulas/smoke-test-briefed.toml).
While the formula spec describes HOW to run the smoke test, this skill tells
you how to **dispatch** that work through the fleet so the test is run,
results are recorded, and a decision brief lands on the stack asynchronously.

Think of it as: **`formula-work` is to `formula-creator-math`** as
**`testing-work` is to `smoke-test-briefed`**.

## When to use

- You created a new formula and must satisfy **F6.1** before filing the
  deploy brief.
- A brief comes back with "no test evidence" — dispatch `testing-work` first.
- You want a repeatable, fleet-executed smoke test record for a Magma
  function, skill, or Python script.
- The formula-work pipeline requests a test via its F6.1 hook.

## Artifact types supported

| Type | What the test checks |
|------|---------------------|
| `formula` | TOML parses, catalog fields present, terminal step valid, `gc formula show` succeeds |
| `skill` | `name:` + `description:` frontmatter, referenced scripts exist |
| `magma-intrinsic` | `IsIntrinsic("<name>")` returns true |
| `magma-function` | `load "<path>"` exits 0 in Magma |
| `python` | `py_compile` + import/help invocation succeeds |
| `script` | `bash -n` syntax check + `--help` invocation |

## Pre-flight

```bash
tmux -L gt ls >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — no tmux fleet server."
  echo "Run 'gc restart' then retry."
  exit 1
}
# `gc dolt health` is THREE-valued: 0 healthy, 2 reachable-but-quarantined
# (non-fatal), 1/other unreachable. See template-fragments/dolt-preflight.md.
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;
  2) ;;   # reachable; auto-GC blocked by a standing compaction quarantine.
          # NON-FATAL and NOT this skill's business: bd resolves beads normally.
          # Proceed SILENTLY — the reporting skills surface it (Variant B).
  *) echo "I'm sorry, I can't do that — Dolt is unreachable."
     echo "Run 'gc dolt start' then retry."
     exit 1 ;;
esac
```

## Dispatch command

```bash
gc sling <rig>/gc.run-operator <bead> --on smoke-test-briefed \
  --var artifact_path=<path-to-artifact> \
  --var artifact_type=<formula|skill|magma-intrinsic|magma-function|python|script> \
  --var test_slug=<short-slug> \
  --var brief_slug=<test_slug>-smoke-test \
  --var source_bead=<bead>
```

Run from the rig root. For `gsp-*` beads: `<city-root>/gascity-packs`. For `he-*`: `<city-root>/hecke`.

### Required vars

| Var | What to put |
|-----|-------------|
| `artifact_path` | Path to the file under test (relative to rig root or absolute) |
| `artifact_type` | One of: `formula`, `skill`, `magma-intrinsic`, `magma-function`, `python`, `script` |
| `test_slug` | Lowercase hyphenated slug; becomes `mathcity/tests/<slug>/` directory name |

### Optional vars

| Var | Default | Notes |
|-----|---------|-------|
| `brief_slug` | `<test_slug>-smoke-test` | Filename stem for the brief artifact |
| `source_bead` | (empty) | If provided, results are recorded as bead notes |
| `operator_target` | `gc.run-operator` | Fleet address for generate/run/classify steps — never a model name |
| `review_target` | `gc.review-synthesizer` | Fleet address for result-review and brief-filing |
| `test_root` | `mathcity/tests` | Where test scripts and results land |

## MANDATORY — verify-assignee gate

Within ~60s of slinging:

```bash
bd show <bead> | grep -i assignee   # must be NON-EMPTY
```

## What you get back

The formula produces:
- `mathcity/tests/<test_slug>/smoke_test.sh` — runnable smoke test
- `mathcity/tests/<test_slug>/results.txt` — captured stdout/stderr + exit code
- `mathcity/tests/<test_slug>/README.md` — what is tested and how to run it
- `mathcity/tests/<test_slug>/TESTING.md` — full reproducibility guide
- A brief on the stack: `<artifact_root>/stack/<brief_slug>.md`

The brief contains the full `TESTING.md` inline and a recommended verdict
(A=pass, C=conditional, R=fail). adjudication happens. The brief serves as
the test-evidence artifact referenced by F6.1.

## Example — smoke-test a new formula

```bash
cd <city-root>/gascity-packs
gc sling gascity-packs/gc.run-operator gsp-8f1o4 --on smoke-test-briefed \
  --var artifact_path=mathcity/formulas/upf-experiment-dispatch.toml \
  --var artifact_type=formula \
  --var test_slug=upf-experiment-dispatch-smoke \
  --var source_bead=gsp-8f1o4
```

## Example — smoke-test a Python script

```bash
cd <city-root>/hecke
gc sling hecke/gc.run-operator he-abc123 --on smoke-test-briefed \
  --var artifact_path=scripts/compute_hecke_eigenvalues.py \
  --var artifact_type=python \
  --var test_slug=hecke-eigenvalues-smoke \
  --var source_bead=he-abc123
```

## Provenance

- Formula: `smoke-test-briefed` (`gc formula show smoke-test-briefed`)
- Policy gate: `mathcity/POLICY-formulas.md` rule F6.1
- Testing guide: `mathcity/docs/testing-guide.md`
- Companion dispatch skill (formula creation): `formula-work` (`mathcity-dev.formula-work`)
- Companion dispatch skill (skill creation): `skill-creator-math` (`mathcity-dev.skill-creator-math`)
