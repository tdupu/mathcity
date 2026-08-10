---
name: is-good-experiment
description: Critical-review variant specialized for experiment proposals. Decides whether a proposed experiment is well-designed BEFORE any compute is spent running it. Trigger on "is this a good experiment?", "review this experiment proposal", "critique my experiment design", "is-good-experiment X", or whenever the user wants a pre-flight check on a computation, test script, or research probe. Used by `run-experiment` as a gate; specialization of `critical-review` (same verdict format, narrower scope).
---

> **Canonical copy**: `mathcity.is-good-experiment` in this mathcity pack. Materialized agent-skills copies are fallback only.

# is-good-experiment

Specialization of `critical-review` for one artifact type: an **experiment proposal**. Your job is to decide whether the experiment is worth running. An experiment that produces an uninterpretable result is wasted compute; an experiment that can only support one conclusion is a confirmation, not a probe.

Per the human adjudicator: **each experiment needs a question it is trying to answer.** No question, no experiment.

## When to use

The artifact is a proposal to compute something in order to learn something. Examples:

- A Magma test script header docstring (e.g. `test-snfs-up-to-scaling-02.mag` — "scaling test, output TSV, fit complexity model").
- A brief like "let's compute `snfs_up_to` on order O for `n <= 50` to see if cost grows linearly in `coprime_pairs(n)`".
- A section of a research bead proposing a probe.
- A `run-experiment` invocation about to fire.

If the artifact is a finished test result, this is the wrong skill — use `critical-review` on the report instead.

## Inputs

A proposed experiment, pasted into the turn or given as a file path. If absent or ambiguous, ask once; do not guess.

Optional context: prior failed runs of similar experiments, the bead the experiment serves, the hypothesis being tested.

## Procedure

Step through the **six checkpoints** in order. Each produces a pass/fail/flag. The verdict is determined by the rules in Output (see below): one hard rule (Checkpoint 1 → REJECT on fail), one threshold rule (any BLOCKING → NEEDS-REVISION), and otherwise APPROVING.

### 1. Question — REQUIRED

Does the proposal state **one falsifiable question**? Not a goal ("explore X"), not a wish ("understand Y"), but a question with possible answers. "Does `Gamma0_fp` cost scale linearly in `coprime_pairs(n)`?" passes. "Profile `Gamma0_fp`" fails.

If absent: **fail this checkpoint, mark verdict REJECT, stop.** Without a question, none of the other checkpoints have anything to evaluate against.

### 2. Outcomes mapped — REQUIRED

For the question's possible answers (typically YES and NO, sometimes a spectrum), is the **interpretation of each outcome** spelled out? What does the human adjudicator learn if the answer is YES? What does the human adjudicator learn if the answer is NO? An experiment where only the YES interpretation is written down is a confirmation trap — the NO outcome will be hand-waved away.

If only one outcome is interpreted: **fail this checkpoint → BLOCKING action item → verdict NEEDS-REVISION.**

### 3. Coverage

Apply the human adjudicator's coverage doctrine: **just enough to support an inferential leap about general behavior.** Two failure modes:

- **Over-narrow**: a single anecdote with no plan for what the one data point would let you conclude. "Run on order O at level 11" with no second order or second level is rarely enough.
- **Over-broad**: exhaustive sweeps where a representative sample would do. "Run on every level up to 1000" when the question is about scaling, not boundary cases.

Flag the violation and propose what the right coverage looks like. This checkpoint can pass with notes; it rarely blocks alone.

### 4. Cost classification

Is this short-term (under ~30 minutes wall) or long-term? Is there a resource estimate (wall time, RAM, disk for outputs)? An experiment with no cost estimate that turns out to take 6 hours is a planning failure.

Flag missing estimates. A long-term experiment without an estimate is a MAJOR issue; a short-term one is MINOR.

### 5. Pitfalls planned for

Look for the **recurring failure modes** from past Magma / hecke experiments. Two are nearly universal and the human adjudicator wants them surfaced explicitly every time:

- **Not loading data.** Many `test-*.mag` failures come from forgetting `AttachSpec`, `SetLMFDBRootFolder`, or a `load_*` call before referencing data. The proposal should name the data it depends on and how it loads it.
- **Slow route of computation.** Computing the right answer via the wrong intrinsic — recomputing instead of caching, calling a quadratic helper inside an outer loop, choosing a generic intrinsic when a specialized one exists. The proposal should state which intrinsics it calls and why those are the right ones.

Other pitfalls to scan for: Magma API drift (intrinsic renamed/removed since the proposal was drafted), ambiguous outputs that cannot be machine-checked (printing a matrix that the operator has to eyeball is a smell), output not written to a stable path.

Flag each pitfall not planned for. Two or more is a MAJOR issue.

### 6. Failure-to-run plan — reviewer-side alertness check

Unlike Checkpoints 1-5 (which check what the proposal contains), this checkpoint asks **you, the reviewer**, to estimate whether the experiment will actually run as written. If it's at serious risk of failing for environmental reasons — missing data, missing intrinsic, missing dependency, environment mismatch — flag that risk so the operator goes in with eyes open. Policy: **if unrunnable, the experimenter should report unrunnable + obtain a `critical-review` verdict supporting that conclusion** before declaring the experiment dead.

The proposal does not need to pre-write a runnability plan, but the reviewer's flag here saves the operator wall time.

## Output

End with a verdict block. Use the parser-friendly fences exactly so downstream tooling (`coordinate-review`, `run-experiment`) can parse:

    ---REVIEW-VERDICT---
    verdict: APPROVING | NEEDS-REVISION | REJECT
    blocking_count: N
    major_count: N
    minor_count: N
    ---ACTION-ITEMS---
    [BLOCKING] ...
    [MAJOR] ...
    [MINOR] ...
    ---END-REVIEW---

Verdict labels are aligned with `critical-review`'s parent vocabulary plus one specialization: `REJECT`. **Important**: when this skill is invoked as the reviewer inside `coordinate-review`'s FP-loop, the loop terminates only on `verdict: APPROVING`. A `REJECT` will be treated as a (terminal-style) NEEDS-REVISION because the proposal is unsalvageable without restating the question — surface that fact in action items.

Verdict rules:

- **REJECT**: Checkpoint 1 (Question) failed. Nothing else matters; the experiment is not yet a proposal. Surfaces as a `NEEDS-REVISION` to `coordinate-review`; the experimenter must restate the question before re-submitting.
- **NEEDS-REVISION**: Any BLOCKING action item present. Always the case when Checkpoint 2 (Outcomes) failed, or two-plus pitfalls (Checkpoint 5) are unplanned-for.
- **APPROVING**: Zero BLOCKING items. MAJOR and MINOR items can coexist with APPROVING; they are improvements, not gates.

Above the verdict block, write the checkpoint-by-checkpoint results in prose (one short paragraph per checkpoint), citing exact lines / sentences of the proposal you are flagging.

## Cross-references

- **`critical-review`** — parent skill. This skill inherits its tone, severity tiers, and verdict format. If the artifact is not actually an experiment proposal, defer to `critical-review`.
- **`run-experiment`** — sibling, primary consumer. `run-experiment` should call this skill as a pre-flight gate; a REJECT or NEEDS-REVISION verdict means do not spend compute yet.
- **`coordinate-review`** — if the proposal fails and needs iteration, hand it to `coordinate-review` with this skill as the reviewer persona to drive it to APPROVING.

## What this skill does NOT do

- **Does not run the experiment.** It only evaluates the proposal.
- **Does not write the experiment.** If the proposal is salvageable, return action items; do not draft the fix.
- **Does not second-guess the hypothesis.** Whether the question is *interesting* is the human adjudicator's call; whether the experiment can *answer* the question is yours.

## Versioning

- **v1.1 — FP-finder pass 1** (2026-06-23): aligned verdict labels with `critical-review` (APPROVING in place of GOOD), clarified Checkpoint 6 as reviewer-side, tightened Checkpoint 2 wording, made the procedure→output rules explicit. The six checkpoints remain the floor; real-world experiment reviews may surface further refinements.
