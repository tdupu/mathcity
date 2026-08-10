---
name: grill-and-present
description: Produce decision-ready brief(s) on artifact(s) (branch, bead, PR, diff) by gathering all present-it sections, grilling the decision-maker on ambiguity one question at a time, running the artifact's tests (divide-and-conquer in parallel), and FP-converging the brief itself through critical-review BEFORE presenting. When multiple artifacts are queued, prepares ALL briefs as a batch before bringing any to the decision-maker. Self-rejects (refuses to present) any brief lacking test-run evidence (file + command + pass/fail) or that has not passed critical-review. Trigger on "present this for decision", "give me a brief on X", "what's the decision on X", "should we merge/delete/keep X", "grill and present X", or batch phrasing like "brief me on these N items".
---

> **Canonical copy**: `mathcity.grill-and-present` in this mathcity pack. Materialized agent-skills copies are fallback only.

# grill-and-present

> **Status (as-4nu, 2026-07-03): retirement PROPOSED, pending the human adjudicator's adjudication.** The gates here now live in [[create-brief]] (composed by [[brief-prep]]); gate-free terminal presentation is [[present-it]]. This skill remains live until the as-4nu PR is adjudicated; prefer the split skills for new work.

Produce decision-ready brief(s) while interactively resolving ambiguity during gathering, validating tests with evidence, and critical-reviewing each brief to APPROVING before presentation. The decision-maker reads one batch of briefs, asks no follow-up questions, and decides.

This skill is **workflow orchestration**. It composes existing skills — do not re-implement their rules. Resolve via `~/.claude/skills/<name>/SKILL.md` or `<repos-root>/agent-skills/skills/<name>/SKILL.md`.

- **Structure**: the grill-ordered brief (7 sections) from `present-it/SKILL.md`.
- **Interview discipline** when ambiguity surfaces: `grilling/SKILL.md` — one question at a time, recommended answer with each.
- **Terminology sharpening** when fuzzy terms surface: `domain-modeling/SKILL.md` — inline, not batched.
- **Test-quality gate**: `is-good-experiment/SKILL.md` (resolve via `~/.claude/skills/` or `<repos-root>/agent-skills/skills/`) — applied as a special case where the experiment's question is pre-filled as "does X work?" (X = the code under test).
- **Brief FP-finder**: `coordinate-review/SKILL.md` — drives the brief itself to APPROVING.

## Hard gates (non-negotiable, agent self-rejects — does not present)

A brief is **not deliverable** unless all three hold. If a gate fails, the agent refuses to present and reports the failure; this is self-enforcement, not waiting for the decision-maker to reject on receipt.

1. **Tests run with evidence in §6.** Test file path + exact command + pass/fail outcome (or exit code). "Tests have not been run" → self-reject. Codified by the decision-maker 2026-06-22.
2. **Tests pass quality rules** per `is-good-experiment` (all six checkpoints must clear; Checkpoint 5's pitfalls — data not loaded, slow route of computation — are the most common source of BLOCKING items in hecke artifacts). A test that functionally passes but yields `NEEDS-REVISION` with BLOCKING items is NOT a passing test for brief purposes.
3. **Brief itself converged to APPROVING** via `coordinate-review` (FP-finder), not just drafted.

## Exception clause for unrunnable tests

A test may be skipped only with a **good reason explicitly declared in §6** of the brief. Acceptable patterns: "the bead IS the test itself" — but even then **the test should still run** if at all possible. The only true skip is impossibility (no Magma reachable, hardware the human adjudicator only has, etc.). **No silent skips.** A blank §6 is auto-reject.

## Workflow

### Step 1: Identify the batch

Enumerate every artifact queued for decision. If one artifact: batch of 1. If many: hold them all. **Do not present until the entire batch is prepared.** Trickling mid-workflow is auto-reject.

### Step 2: Run tests (parallel both within and across artifacts)

For every artifact in the batch, identify the tests that should pass. **Dispatch all test runs in parallel — both within a single artifact (split its test suite across polecats/subagents) and across artifacts in the batch (run tests for A, B, C concurrently).** Do not serialize. For each test set:

1. Dispatch runner(s). Capture file + command + result.
2. If functionally fails → either fix the artifact (out-of-scope work, hand off) or surface the failure as data in §6 of the brief. Do not pretend pass. Re-run after any fix.
3. Once functional-pass, evaluate against `is-good-experiment` (six checkpoints). BLOCKING items → not a pass; fix and re-run.
4. If genuinely unrunnable: declare the reason and the evidence of impossibility (§6), per the exception clause.

Distinguish two failure modes: **(a) functional FAIL** (exit code nonzero, assertion fired) is presentable data — record it in §6 and present the brief; the decision-maker may still decide "delete" or "fix-then-revisit." **(b) `is-good-experiment` BLOCKING** is a gate 2 violation — fix the test design and re-run before presenting; the brief is not deliverable while gate 2 fails.

### Step 3: Gather + grill per artifact

Walk every section of `present-it/SKILL.md` in order. Trigger a grilling round only when ambiguity surfaces:

- **Terminology conflict** — codebase usage vs. bead/branch usage diverge. Invoke domain-modeling: propose the precise term, ask which is meant.
- **Design-tree fork** — the stated goal admits more than one plausible interpretation. Ask which branch.
- **Spec-vs-implementation drift** — bead says X, code does Y. Surface the contradiction; ask which is authoritative.
- **Hidden assumption** — silent dependency (env var, version, calling convention). Name it; ask if intended.

Follow `grilling/SKILL.md`: one question at a time, with your recommended answer.

### Step 4: Draft the brief

Use `present-it/SKILL.md` exactly (7 grill-ordered sections, prose vs. bullets, Required gates summary, Decision options block). After the Decision options block and before asking for the decision, state **your recommendation with a one-line rationale**.

### Step 5: FP-converge each brief

Invoke `coordinate-review` on each drafted brief with a reviewer persona appropriate to the artifact's domain (e.g., "a Magma reviewer paranoid about un-loaded data and slow intrinsics" for hecke artifacts). Iterate until APPROVING. Run `/compact` between iterations N and N+1 so the prior round's reviewer/revisor transcript does not bloat context for the next round. If `coordinate-review` stalls (BLOCKING items persist past its own stop signals), that brief is non-deliverable: **hold the rest of the batch**, do not present any of it, and report the stall to the decision-maker as a separate communication. Do not silently drop the artifact from the batch.

### Step 6: Steps 3–5 per artifact; Step 2 across artifacts

Step 2 (tests) runs in parallel across the whole batch. Steps 3–5 (gather, draft, FP-converge) are per-artifact and may run in parallel across artifacts as well, subject to grilling needing the decision-maker's serial attention. **Only after every brief in the batch reaches APPROVING do you proceed to Step 7.** The unrunnable-test exception (declared in §6) still requires gate 3 — the brief itself must FP-converge to APPROVING.

### Step 7: Present the batch

Bring all briefs together. Within the batch, present in **largest-unblock-count first order**: count the open beads each artifact's decision would unblock (via `bd dep show` or similar) and present highest-count first. Decision-maker may override the order. Present one brief at a time; wait for the decision before the next. (Single-item batches are a degenerate case.)

## Example batching order

Three artifacts queued: A (unblocks 5 beads), B (unblocks 1), C (unblocks 0). Prepare all three (tests + brief + FP-finder) **before** presenting any. Then present: A → wait for decision → B → wait → C.

## Out of scope

- Acting on the decision — this skill produces briefs and questions; the decision-maker (and downstream agents) act on the answers.
- Glossary archaeology — domain-modeling captures terms inline.
- Re-implementing `coordinate-review` or `is-good-experiment` — invoke them.
