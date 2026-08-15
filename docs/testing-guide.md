# Mathcity Testing Guide

Parent: [../README-development.md](../README-development.md)

> Policy: `mathcity/POLICY-formulas.md` rule **F6.1** — every new formula (and
> by extension every mathcity artifact) must have a passing smoke test before
> its deploy brief is filed. This document explains what testing looks like,
> how to dispatch it, and how results are recorded.

## What counts as a test

Mathcity tests are **artifact-type specific**. A smoke test is not a proof of
correctness — it is the minimal bar that confirms the artifact is loadable,
invocable, and structured correctly. Tests grow over time; the smoke test is
the non-negotiable minimum (F6.1).

| Artifact type | Smoke test content |
|---|---|
| **formula** | TOML parses; catalog fields present; terminal step is `file-brief`/`brief-finalize`/`workflow-finalize`; `gc formula show <name>` succeeds |
| **skill** | `name:` + `description:` frontmatter present; any referenced scripts exist |
| **magma-intrinsic** | `IsIntrinsic("<name>")` returns `true` in Magma |
| **magma-function** | `load "<path>"` exits 0 in Magma without error |
| **python** | `python3 -m py_compile <file>` passes; import or `--help` invocation succeeds |
| **script** | `bash -n <file>` passes; `--help` invocation exits cleanly |

## Where tests live

All test artifacts go under `mathcity/tests/<slug>/`:

```
mathcity/tests/
  <slug>/
    smoke_test.sh    — self-contained, idempotent, exits 0 on pass
    results.txt      — captured stdout/stderr from last run + exit code
    README.md        — what is tested, how to run, expected output
    TESTING.md       — full reproducibility guide (the canonical test record)
```

`TESTING.md` is the artifact referenced in briefs as test evidence.

## How to dispatch a smoke test

Use the `testing-work` skill (`/testing-work`):

```bash
gc sling <rig>/gc.run-operator <bead> --on smoke-test-briefed \
  --var artifact_path=<path> \
  --var artifact_type=<formula|skill|magma-intrinsic|magma-function|python|script> \
  --var test_slug=<slug> \
  --var source_bead=<bead>
```

The fleet agent will:
1. Classify the artifact and select the correct smoke-test strategy
2. Write `mathcity/tests/<slug>/smoke_test.sh`
3. Run it and record output to `results.txt`
4. Write `TESTING.md` (reproducibility guide)
5. File a brief with the test evidence for the human adjudicator adjudication

## How to run a test manually

Any smoke test can be run standalone:

```bash
cd <rig-root>   # e.g. <city-root>/gascity-packs
bash mathcity/tests/<slug>/smoke_test.sh
```

Exit 0 = PASS, non-zero = FAIL. Output is human-readable.

## How to reproduce a test run

The `TESTING.md` in each test directory is the canonical reproducibility guide.
It contains:
- The exact commands to re-run the test
- Environment requirements (Magma version, Python version, etc.)
- Expected output (copy of passing stdout)
- What is NOT tested and what to test next

## Integration with the brief pipeline

A brief that arrives on the stack without test evidence will be flagged for
rejection under F6.1. The standard pattern is:

```
new artifact created
  → /testing-work dispatched
  → smoke-test-briefed runs
  → TESTING.md written
  → brief filed with test evidence in .beads/briefs/.pile
  → brief-shuffle applies the brief's gate_profile
  → stack
  -> adjudication
  → A verdict → commit + push
```

The `formula-work` skill references `testing-work` explicitly; formula authors
should dispatch both in parallel where possible.

Every brief source uses the same promotion contract: the relevant typed
profile, no-brainer classifier evidence, and a declared
`brief_quality_failure.v1` feedback sink. Artifact briefs still carry the
standard artifact evidence gates; decision-only, lost-bead-filter, and
producer-repair briefs prove their own profile-specific evidence instead of
inventing fake artifact-style test evidence.

## Brief Pipeline Regression Tests

The unified brief pipeline has focused smoke tests that can run before BART
touches live city state:

```bash
bash tests/unified-brief-pipeline-e2e/smoke_test.sh
bash tests/brief-stack-index-reconcile/smoke_test.sh
bash tests/decisions-track-migration/smoke_test.sh
bash tests/unified-brief-gate-profiles/smoke_test.sh
bash tests/present-briefs-unified-source/smoke_test.sh
bash tests/present-briefs-defer-filter/test_defer_filter.sh
bash tests/brief-quality-failure/smoke_test.sh
```

Run the older filter/gate regressions with them when changing the brief
pipeline:

```bash
bash tests/lost-bead-filter/smoke_test.sh
bash skills/catch-no-brainer/fixtures/run.sh
bash tests/brief-no-brainer-gate/test_brief_check_no_brainer.sh
bash tests/lockless-brief-shuffle/smoke_test.sh
bash tests/producer-failure-rollup-routing/smoke_test.sh
python3 -m pytest tests/stuck-bead-watch tests/tail-end-detector
```

For BART deployment, rerun the same commands in the exact runtime path that
`gc` resolves. Pull-only deployment is enough only if live-resolved
`present-briefs`, `decisions-to-briefs`, `assets/brief-pipeline/gates.toml`,
and `check-brief-policy` match `/Users/tdupuy/repos/mathcity` at the merged
commit. If those files resolve from `/Users/tdupuy/gt`, `~/.gc/cache`, or
another installed pack location, run the existing pack import/build/install
step first, then rerun the tests there before live migration.

## Tests that grow over time

A smoke test is the floor, not the ceiling. After the initial smoke test passes:

1. **Correctness tests** — for Magma functions and Python scripts, add a
   `correctness_test.sh` that computes a known example and compares the result.
2. **Regression tests** — when a bug is fixed, add a test case that would have
   caught the bug.
3. **Edge case tests** — add a `edge_cases.sh` that exercises boundary conditions.

These additional tests go in the same `mathcity/tests/<slug>/` directory and
can be dispatched via `test-execution-request` (for high-risk) or run directly
(for low-risk).

## Existing test infrastructure

- `mathcity/formulas/test-execution-request.toml` — formal authorization
  workflow for high-risk test execution
- `mathcity/formulas/smoke-test-briefed.toml` — the testing formula (dispatch
  via `testing-work`)
- `mathcity/subdomains/dev/skills/testing-work/SKILL.md` — dispatch skill
- `mathcity/tests/smoke-test-briefed-self/` — self-test for the testing formula
  (dogfood example)
