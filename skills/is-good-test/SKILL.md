---
name: is-good-test
description: Thin wrapper around is-good-experiment specialized for test files. A test is an experiment whose question is fixed as "does X work?" where X is the intrinsic / function / pipeline under test. Trigger on "is-good-test X", "review this test design", "is this a good test?", "does this test answer 'does X work?'", "review my Magma test", or any request to evaluate a test file's design (not its results). Sibling of is-good-experiment (parent), critical-review (grandparent). Out of scope for finished test results — use critical-review on the report instead.
---

> **Canonical copy**: `mathcity.is-good-test` in this mathcity pack. Materialized agent-skills copies are fallback only.

# is-good-test

A test is a special case of an experiment whose **question is fixed**: "does X work?" where X is the artifact under test (an intrinsic, function, pipeline, script, or workflow).

This skill is a thin wrapper: it (a) extracts X from the test file, (b) frames the experiment question as "does X work?", (c) invokes `is-good-experiment`, (d) returns that verdict.

The six-checkpoint logic lives in the parent skill (`is-good-experiment`). Do not restate it.

## When to use

The artifact is a **test file** (or a directory of test files) that exercises code: `test-*.mag`, `*_test.py`, `tests/test_*.py`, a shell-test harness, etc. The skill checks the **test's design**, not its results.

If the artifact is a passing/failing test report, use `critical-review` instead.

## Inputs

A test file path or directory path, pasted into the turn. Multiple files are reviewed file-by-file; emit one verdict per file.

## Procedure

For each test file:

1. **Read the file.** Identify X — the named thing under test — from one of: the file header docstring, the test name, the primary `assert`/`require`/`expect` target, or an explicit `intrinsic_under_test`/`function_under_test` annotation.
2. **If X cannot be identified**: this is a Checkpoint 1 (Question) failure for the parent skill. The test has no falsifiable question. Verdict: **REJECT**. Action item: "Test file does not state what it is testing; add a header docstring naming the intrinsic / function / pipeline under test."
3. **Frame the experiment.** Construct the question as "does `X` work?" — meaning: does X produce correct outputs across the inputs the test exercises, and does the test's pass/fail signal correctly distinguish working from broken X?
4. **Invoke `is-good-experiment`** with the test file as the proposal and the question pre-filled as "does X work?". The parent's six checkpoints apply directly; do not restate them here. Two test-specific framings the parent's reviewer should know about:
   - **Outcomes (Checkpoint 2)**: a test must interpret both PASS and FAIL. A test where only PASS is meaningful (FAIL just means "something went wrong") is a confirmation trap.
   - **Pitfalls (Checkpoint 5)**: in addition to not-loading-data + slow-route, watch for **assert-by-accident** (e.g., `nil eq nil` always true) and **single-input tests** (one input passing does not show X works in general).
5. **Return the parent's verdict block verbatim.** Do not re-emit; do not re-format.

## Output

The verdict block emitted by `is-good-experiment` (`APPROVING | NEEDS-REVISION | REJECT`). When multiple test files are reviewed, emit one verdict block per file, each prefixed by `## <file-path>`.

## Cross-references

- **`is-good-experiment`** — parent skill (the six-checkpoint engine). All logic lives there.
- **`critical-review`** — grandparent. For finished test results / test reports, use this instead.
- **`coordinate-review`** — to drive a failing test design to APPROVING through iteration.

## What this skill does NOT do

- **Does not run the test.** It only reviews the test's design.
- **Does not rewrite the test.** Return action items to the parent skill.
- **Does not duplicate the parent's six checkpoints.** Re-read `is-good-experiment` if you need them.
