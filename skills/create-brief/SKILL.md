---
name: create-brief
description: Produce the durable, gated `.md` brief artifact for the brief stack from a code artifact (branch, bead-id, PR, diff, GH-issue-N). The file-artifact sibling of present-it — same grill-ordered section structure, but written to disk and REQUIRED to clear the pipeline gates (test-evidence + good-test review + critical-review) before it is stack-eligible. Delivers via the clerk channel (brief stack / mail / file-inbox), NEVER by presenting in the Mayor's terminal. Trigger phrases "create a brief for X", "write a brief file for X", "draft a brief artifact on X", "make a .md brief for X", "file a brief on X", "add a brief to the stack for X". NOT for in-conversation context dumps — use present-it for "present X / give me context on X". For the end-to-end pipeline with classification, external review, and bookkeeping, use brief-prep (which composes this skill).
---

# create-brief

Produce the **durable `.md` brief artifact** that the brief pipeline runs on: a decision-ready brief file, gated before it becomes stack-eligible, delivered through the clerk channel for the human adjudicator's adjudication.

This is the file-artifact half of the two-skill split codified under as-4nu:

| | [[present-it]] | **create-brief** |
|---|---|---|
| Output | terminal text in the current conversation | `.md` file in the brief stack |
| Gates | none (reports evidence, never self-rejects) | test-evidence + good-test + critical-review (HARD) |
| Batch | never | batch preparation applies |
| Audience | the decision-maker in this conversation | the human adjudicator, asynchronously, via the clerk channel |

This skill is **composition by reference**: the section structure comes from [[present-it]], the gate policies from the Mayor memories `feedback_brief_test_evidence_required.md` and `project_brief_pipeline_workflow.md`, the stack schema from `project_brief_stack_workflow.md`. Do not re-implement their rules; consult them.

## Artifact format

**Path:** `<city-root>/.beads/briefs/<artifact-safe-name>-brief.md` — the canonical HQ stack (S6 2026-07-15: cross-rig consolidation completed; ALL rigs deposit briefs here for uniform landing, per the human adjudicator — supersedes the old per-rig `<city-root>/hecke/.beads/briefs/` hardcode). One canonical file per artifact; revisions in place with a `.bak` before any FP-revision; no `-vN-` suffixes.

**Frontmatter (required, per the stack schema + safety overrides):**

```yaml
---
artifact: <branch | bead-id | PR-number | gh-issue-N>
status: pending-review | in-review-iter-N | review-failed | approved | pulled | presented | adjudicated | archived
deposited_at: <ISO 8601>
deposited_by: <polecat session ID or worker name>
review_gate: pending | iter-N | approved | review-failed   # lowercase — the patrol/shuffle vocabulary (brief-review-patrol.toml)
unlock_count: <int>
priority: P0 | P1 | P2 | P3 | P4
server_touching: <bool>                  # he-lele cat-E mechanical test — see [[brief-prep]] §"Safety overrides"
user_skill_touching_override: <bool>     # as-wjv mechanical test — see [[brief-prep]] §"Safety overrides"
---
```

**Body:** the Decision-at-Top INVARIANT and the section structure are [[present-it]]'s, written to file instead of spoken:

- **Full-form (default):** the 7 grill-ordered sections per [[present-it]] §"Full-form template" — §1 what is being decided, §2 recommended answer, §3 assumptions, §4 alternatives, §5 risks, §6 evidence (test evidence lives here), §7 plan membership + required gates.
- **Compact form:** `DECISION` / `CONTEXT` / `RECOMMEND` / `CONFIRM y/n/grill-me-further` per [[present-it]] §"Compact form" — ONLY when [[catch-no-brainer]] emitted `compact_eligible: true` AND both safety-override booleans are `false` AND the shape is not `capability-blocker`.

The FIRST content after the frontmatter MUST be "What is being decided." A brief file violating the Decision-at-Top INVARIANT is malformed: rewrite before depositing; [[brief-prep]] Phase 4 auto-rejects it.

**`## Gate Evidence` section (required in both shapes):** one explicit entry per gate of the active `assets/brief-pipeline/gates.toml` profile, keyed by `evidence_key`, each `PASS`/`FAIL`/`BLOCKED`/`N/A` with every `N/A` citing its surface check; G14 uses the literal tri-state `PASSED`/`NOT APPLICABLE`/`REQUIRED`. G9 evidence must use the `classifier_state=...` syntax required by `brief-prep`; free-form "no-brainer considered" prose is malformed and the shuffle must fail closed. The shuffle's `process-item` step is fail-closed — a brief without this section is structurally guaranteed rejection (see [[brief-prep]] Phase 3 for the full spec).

## Gates (HARD — a brief file that fails any of these is not stack-eligible)

Unlike [[present-it]], this skill **self-rejects**: do not deposit a brief that fails a gate; fix it or surface the failure. The gates, per `feedback_brief_test_evidence_required.md` (the human adjudicator 2026-06-22) and `project_brief_pipeline_workflow.md` §3:

1. **Test-evidence gate.** Run the artifact's tests before drafting. §6 must cite, per test: file path + exact command + exit code + pass/fail + wall time. No silent skips — an unrunnable test must be declared with its impossibility reason ("no Magma reachable", "requires hardware the human adjudicator only has"). "Tests exist but haven't been run" → not stack-eligible. Functional FAIL is presentable *data* (record it; the verdict may become "fix-then-revisit"); missing evidence is not.
2. **Good-test gate.** Each test is evaluated against [[is-good-experiment]] / [[is-good-test]] (six checkpoints; watch the classic pitfalls: data not loaded, slow route of computation). A test that functionally passes but carries BLOCKING items is NOT a passing test for brief purposes — fix the test design and re-run.
3. **Critical-review gate.** The brief itself FP-converges to APPROVING via [[coordinate-review]] (cap 4 rounds per `project_brief_stack_workflow.md`; on non-convergence mark `review-failed`, file a follow-up bead, surface to Mayor — never deposit-and-pretend).

Divide-and-conquer is encouraged: dispatch test runs in parallel within and across artifacts.

## Batch preparation

Batch semantics live HERE, not in [[present-it]] (batching across artifacts happens at the dispatch layer that queues multiple create-brief / [[brief-prep]] runs): when N briefs are queued for adjudication, prepare ALL of them — tests + draft + review — before ANY is surfaced. Don't trickle partial batches into the stack while siblings are mid-pipeline; adjudication happens batches efficiently, trickles interrupt.

## Pre-authorized conditions (stub — policy-driven)

Some dispositions are pre-authorized to skip human adjudication. This skill does not decide that; it declares the inputs and defers to policy:

- **Classification** comes from [[catch-no-brainer]] (he-lele 5-criterion, cats A–D; cat-E and user-skill-touching are negative classifiers).
- **Safety overrides** (`server_touching`, `user_skill_touching_override`) are computed mechanically per [[brief-prep]] §"Safety overrides" and recorded in frontmatter. Either being `true` forbids auto-approval regardless of category.
- **Auto-approval** additionally requires the N5 kill-switch hierarchy to be clear: `<city-root>/.beads/auto_merge_enabled` first, then `<rig_root>/.beads/auto_merge_enabled`. Auto-execute is the default; a switch file that exists and reads `false` halts automation. Absent or `true` proceeds, provided the known-category, confidence, and stop-gate checks pass.
- Everything else → **stack-insert** ranked by `unlock_count` for human adjudication.

The mechanical policy itself lives in the gate registry and the gate-keep architecture (`project_gate_keep_architecture.md`: X-policy + X-gate + improve-X trinities). As gate-keep lands, this section delegates to it; until then, treat "pre-authorized" as: known no-brainer category match, confidence at or above threshold, both overrides false, and no engaged kill switch — otherwise the human adjudicator decides.

## Delivery — clerk channel, NOT the Mayor's terminal

Constraint (the human adjudicator 2026-06-24, per `feedback_mayor_no_direct_grilling.md` + `feedback_clerk_is_intermediary_only.md`): the Mayor does not grill the human adjudicator directly; the clerk owns the human adjudicator-facing dialogue, the Mayor owns dispatch. A finished brief therefore reaches the human adjudicator only through the clerk channel:

- **Primary: the brief stack.** Deposit the file; the clerk pulls promoted briefs and runs [[present-it]] on them toward the human adjudicator.
- **Signal paths:** `gc mail send` to the clerk / "human" inbox channel, or the file-inbox (see [[communicate-with-clerk]]) — to announce stack state, never to carry the brief body as terminal dialogue.
- **Forbidden:** presenting the brief in the Mayor's terminal, or expecting the Mayor to relay brief dialogue to the human adjudicator in-conversation.

## Procedure

1. **Locate the artifact** (branch / bead / PR / GH-issue / diff). Ambiguous or nonexistent → STOP, return UNABLE-TO-RUN with the reason.
2. **Run the gates**, in order: tests (gate 1), good-test evaluation (gate 2).
3. **Draft the brief** — frontmatter + Decision-at-Top + full-form or compact body per "Artifact format" above. Compute `unlock_count` (bd queries per `project_brief_stack_workflow.md`; record the transcript in §7).
4. **Self-check** the Decision-at-Top INVARIANT and section completeness ("None surfaced" + reason is acceptable; blank is not).
5. **Critical-review** (gate 3) to APPROVING; update `status` / `review_gate` per iteration.
6. **Write the file** to the stack path; deliver per "Delivery" above.
7. **Return** the brief path + verdict + gate outcomes to the caller. When invoked from [[brief-prep]], the orchestrator's Phase 2/4/5 executions ARE gates 1–3 (do not run tests or coordinate-review a second time) and it owns deposit bookkeeping (brief-record bead, follow-up beads, epic links) — don't duplicate either; when invoked standalone, say explicitly in the return that bookkeeping has NOT been filed.

## Hard rules

- **NO presenting to the human adjudicator** — clerk channel only (above).
- **NO `bd close` on adjudication-class beads.** the human adjudicator decides; agents propose.
- **NO commits or pushes.** Brief deposits are local-only artifact writes.
- **NO `gh issue close`, NO branch deletes.** The brief recommends; the human adjudicator (via decisions.jsonl) executes.
- **Credential discipline** per [[never-echo-credentials]].

## Cross-references

- [[present-it]] — the terminal sibling: defines the section structure and both output shapes; no file, no gates.
- [[brief-prep]] — the end-to-end pipeline worker: classification, safety overrides, external review gate, deposit bookkeeping; produces its artifact per THIS skill.
- [[catch-no-brainer]] — no-brainer / capability-blocker classifier; source of `compact_eligible`.
- [[coordinate-review]] — the FP-loop used by gate 3.
- [[is-good-experiment]] / [[is-good-test]] — the test-quality rules behind gate 2.
- Mayor memories: `feedback_brief_test_evidence_required.md` (gate policy), `project_brief_pipeline_workflow.md` (pipeline state machine), `project_brief_stack_workflow.md` (stack infra + schema), `project_gate_keep_architecture.md` (gate trinity; pre-authorization future home), `feedback_two_skill_split.md` (the split this skill implements).

## Versioning

- **v1.0 — two-skill split** (2026-07-03, per as-4nu): created as the gated file-artifact counterpart of [[present-it]], which simultaneously dropped its gates, batch semantics, and one-at-a-time constraint. Encodes: stack path + frontmatter schema from `project_brief_stack_workflow.md`; the three HARD gates from `feedback_brief_test_evidence_required.md`; batch preparation; pre-authorized-conditions stub referencing the gate-keep architecture; clerk-channel delivery per the human adjudicator 2026-06-24.
