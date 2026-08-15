---
name: create-brief
description: Produce the durable, gated `.md` brief artifact for the brief stack from a code artifact (branch, bead-id, PR, diff, GH-issue-N). The file-artifact sibling of present-it — same grill-ordered section structure, but written to disk and REQUIRED to clear the pipeline gates (test-evidence + good-test review + critical-review) before it is stack-eligible. Delivers via the clerk channel (brief stack / mail / file-inbox), NEVER by presenting in the Mayor's terminal. Trigger phrases "create a brief for X", "write a brief file for X", "draft a brief artifact on X", "make a .md brief for X", "file a brief on X", "add a brief to the stack for X". Also use when a blocked or dispatch-failed worker must file a durable escalation and has no code artifact at all — "escalate this", "file an escalation brief", "I cannot claim my bead", "my bead store is unreachable", "the claim protocol is stuck", "no live mayor session to escalate to". NOT for in-conversation context dumps — use present-it for "present X / give me context on X". NOT for recording a disposition or policy choice when nothing is blocking you — use decisions-to-briefs. For the end-to-end pipeline with classification, external review, and bookkeeping, use brief-prep (which composes this skill).
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

## Two input lanes — classify FIRST, before anything else

Answer one question: **can you open and inspect the artifact?**

| What you have | Lane |
|---|---|
| A branch, PR, diff, or bead you can actually read | **code-artifact** — the artifact gates (registry **G1, G2, G4**) apply in full |
| No such artifact, **because a defect is blocking you from reaching one** — store unreachable, claim protocol failing, dispatch misrouted, identity mismatch, lease expiring | **escalation** — the blocker IS the artifact; gates E1–E3 apply instead |
| No artifact and nothing is blocking you — you are recording a disposition or policy choice | Neither lane. Use [[decisions-to-briefs]]. |

Record the answer in frontmatter as `lane: code-artifact | escalation`. **The lane is a fact about your input, not a preference.** A worker who can read its artifact is in the code-artifact lane no matter how inconvenient the tests are.

**This resolves a standing conflict with [[catch-no-brainer]].** That skill classifies this shape as `capability-blocker` and says emit to stdout, do not deposit, and let the Mayor consume the signal. **When no live Mayor session exists, that route is a dangling channel and stdout dies with the session** — the escalation vanishes. In this lane, `capability-blocker` means **deposit here in full form**; the stdout signal is an addition to the file, never a substitute for it.

## Artifact format

**Path:** `<city-root>/.beads/briefs/<artifact-safe-name>-brief.md` — the canonical HQ stack (S6 2026-07-15: cross-rig consolidation completed; ALL rigs deposit briefs here for uniform landing, per the human adjudicator — supersedes the old per-rig `<city-root>/hecke/.beads/briefs/` hardcode). One canonical file per artifact; revisions in place with a `.bak` before any FP-revision; no `-vN-` suffixes.

**Frontmatter (required, per the stack schema + safety overrides):**

```yaml
---
artifact: <branch | bead-id | PR-number | gh-issue-N | blocked:<what-you-could-not-reach>>
lane: code-artifact | escalation          # REQUIRED — see "Two input lanes" above
status: pending-review | in-review-iter-N | review-failed | escalation-unreviewed | approved | pulled | presented | adjudicated | archived
deposited_at: <ISO 8601>
deposited_by: <polecat session ID or worker name>
review_gate: pending | iter-N | approved | review-failed | escalation-self-checked   # lowercase — the patrol/shuffle vocabulary (brief-review-patrol.toml)
unlock_count: <int> | UNKNOWN-NOT-COMPUTED
priority: P0 | P1 | P2 | P3 | P4
server_touching: <bool>                  # he-lele cat-E mechanical test — see [[brief-prep]] §"Safety overrides"
user_skill_touching_override: <bool>     # as-wjv mechanical test — see [[brief-prep]] §"Safety overrides"
---
```

**`unlock_count` when you cannot reach the store: write `UNKNOWN-NOT-COMPUTED`. NEVER write `0`.** `0` is a *measurement* claiming this blocks nothing, and it sorts a live blocker to the bottom of an `unlock_count`-ranked stack. The field being typed `<int>` is not a reason to supply one. A visible non-integer beats an invisible false zero, and the same rule governs every other field you cannot measure: mark it `UNKNOWN`, never a plausible placeholder.

**`escalation-unreviewed` and `escalation-self-checked` exist so the escalation lane does not have to borrow `review-failed`.** Borrowing it says the review ran and failed; in this lane no external review was ever obtainable, which is a different fact.

### Escalation-lane field rules — the exact values, so you do not have to invent them

These fields have no measurable answer while blocked. **Every one has a required value below. Do not derive your own.**

| Field | Write exactly | Why |
|---|---|---|
| `status` | `escalation-unreviewed` | reports the *external-review* fact: none was obtainable |
| `review_gate` | `escalation-self-checked` | reports the *E3* fact: one self-pass was done. **These two co-occur and do not conflict** — they describe different checks |
| `unlock_count` | `UNKNOWN-NOT-COMPUTED` | never `0` — see above |
| `priority` | `P1`, unless the blocker halts a whole rig or the fleet → `P0` | the enum has no `UNKNOWN` member, so a rule is required rather than a guess |
| `server_touching` | `true` | **the `UNKNOWN` rule does NOT apply to booleans feeding fail-closed stop gates.** A parser may coerce a non-bool to falsy — the invisible-false failure the `unlock_count` rule exists to prevent. `true` forbids auto-approval, which is the safe direction and asserts nothing about a surface you did not check. Annotate inline: `# fail-closed, NOT measured` |
| `user_skill_touching_override` | `true`, same rule and same inline annotation | as above |
| `artifact` | `blocked:<what you could not reach>` | e.g. `blocked:mc-hs3` |

**An escalation-lane brief is NEVER auto-approvable**, regardless of kill-switch state or classifier output. Do not rely on that falling out of the two booleans above — it is a rule in its own right.

**When you hold the failure but not its transcript** — you were dispatched after the fact, or a constraint forbids re-running the command — write `UNKNOWN-NOT-CAPTURED` and say whose report you are relaying. **Never reconstruct a plausible error string.** A declared second-hand account is evidence; an invented verbatim is fabrication, and this is the field where that temptation is strongest.

**Known open items, stated rather than hidden.** These are real gaps between this lane and the machinery around it. Declare them in the brief; do not paper over them.

- The stack sorts by `unlock_count`, and how consumers order a non-integer is unspecified. `UNKNOWN-NOT-COMPUTED` protects the record's honesty; **it does not guarantee visibility.** This is why `priority` carries the ranking here, and why delivery must signal a human rather than trusting the sort.
- **`escalation-unreviewed`, `escalation-self-checked`, and `.escalation-drop/` are new vocabulary that no consumer yet parses.** `formulas/brief-review-patrol.toml` only advances briefs at `review_gate: pending`, so a brief marked `escalation-self-checked` is invisible to the patrol. That is deliberate — it is better than borrowing `review-failed`, which asserts a review ran — but it means **an escalation brief will not move through the pipeline on its own.** Say so in the delivery line.
- **The deposit path is contested.** This skill says `<city-root>/.beads/briefs/<name>-brief.md`; `assets/brief-pipeline/paths.toml` is rig-relative with a distinct `stack`/`.pile` layout; [[brief-prep]] deposits flat to `.beads/briefs/.pile/<slug>.md`. **Write to the path [[brief-prep]] uses if you can reach it, and record which path you chose** — a brief in the wrong directory is read by nobody.

**Body:** the Decision-at-Top INVARIANT and the section structure are [[present-it]]'s, written to file instead of spoken:

- **Full-form (default):** the 7 grill-ordered sections per [[present-it]] §"Full-form template" — §1 what is being decided, §2 recommended answer, §3 assumptions, §4 alternatives, §5 risks, §6 evidence (test evidence lives here), §7 plan membership + required gates.
- **Compact form:** `DECISION` / `CONTEXT` / `RECOMMEND` / `CONFIRM y/n/grill-me-further` per [[present-it]] §"Compact form" — ONLY when [[catch-no-brainer]] emitted `compact_eligible: true` AND both safety-override booleans are `false` AND the shape is not `capability-blocker`.

The FIRST content after the frontmatter MUST be "What is being decided." A brief file violating the Decision-at-Top INVARIANT is malformed: rewrite before depositing; [[brief-prep]] Phase 4 auto-rejects it.

**`## Gate Evidence` section (required in both shapes):** one explicit entry per gate of the active `assets/brief-pipeline/gates.toml` profile, keyed by `evidence_key`, each `PASS`/`FAIL`/`BLOCKED`/`N/A` with every `N/A` citing its surface check; G14 uses the literal tri-state `PASSED`/`NOT APPLICABLE`/`REQUIRED`. G9 evidence must use the `classifier_state=...` syntax required by `brief-prep`; free-form "no-brainer considered" prose is malformed and the shuffle must fail closed. The shuffle's `process-item` step is fail-closed — a brief without this section is structurally guaranteed rejection (see [[brief-prep]] Phase 3 for the full spec).

## Code-artifact lane — the artifact gates (HARD; a brief that fails any is not stack-eligible)

**Gate IDs here are the registry's, not a local 1-2-3.** The three below are `gates.toml`'s **G1 (test-evidence), G2 (good-test), and G4 (critical-review)** — note the jump: **registry `G3` is `shell-scripts-testable`, a different gate entirely.** Never write "G1–G3" for this trio; a `## Gate Evidence` section built on that misreading declares the wrong gate and silently omits G4, which is a guaranteed fail-closed rejection.

Unlike [[present-it]], this skill **self-rejects**: do not deposit a brief that fails a gate; fix it or surface the failure. The gates, per `feedback_brief_test_evidence_required.md` (the human adjudicator 2026-06-22) and `project_brief_pipeline_workflow.md` §3:

1. **Test-evidence gate.** Run the artifact's tests before drafting. §6 must cite, per test: file path + exact command + exit code + pass/fail + wall time. No silent skips — an unrunnable test must be declared with its impossibility reason ("no Magma reachable", "requires hardware the human adjudicator only has"). "Tests exist but haven't been run" → not stack-eligible. Functional FAIL is presentable *data* (record it; the verdict may become "fix-then-revisit"); missing evidence is not.
2. **Good-test gate.** Each test is evaluated against [[is-good-experiment]] / [[is-good-test]] (six checkpoints; watch the classic pitfalls: data not loaded, slow route of computation). A test that functionally passes but carries BLOCKING items is NOT a passing test for brief purposes — fix the test design and re-run.
3. **Critical-review gate.** The brief itself FP-converges to APPROVING via [[coordinate-review]] (cap 4 rounds per `project_brief_stack_workflow.md`; on non-convergence mark `review-failed`, file a follow-up bead, surface to Mayor — never deposit-and-pretend).

Divide-and-conquer is encouraged: dispatch test runs in parallel within and across artifacts.

## Escalation lane — gates E1–E3 (HARD, and satisfiable *while blocked*)

A blocked worker cannot run tests, cannot judge test quality, and cannot survive a capped multi-round review loop. **In this lane the artifact gates — registry `G1`, `G2`, and `G4` — are `N/A by construction`**: declare each with that exact phrase plus its surface check. (The convention comes from [[decisions-to-briefs]], which declares `gates: test-evidence N/A` the same way; that skill is user-scope and may not be reachable from a pack agent, so the phrase is specified here rather than by reference.) **Declaring N/A is not a gate failure. Fabricating evidence to satisfy G1 is.**

These three replace them. Each is satisfiable from what a blocked worker already holds:

1. **E1 — Blocker evidence.** The exact command you ran, its output or error **verbatim**, and what you expected instead. One command is enough. You already have this: it is the thing that blocked you. Paraphrase is not evidence.
2. **E2 — Reproduction.** Whether it recurred, and how many attempts you made. **One attempt is acceptable.** *"Did not retry — lease expiring"* is a complete answer. An unstated attempt count is not.
3. **E3 — Single-pass self-check.** Read your own draft once: is §1 the decision, is E1 verbatim rather than summarised, is every unmeasured field marked `UNKNOWN` rather than guessed? Set `review_gate: escalation-self-checked`. **Do NOT run [[coordinate-review]] in this lane** — its capped FP loop cannot finish before a lease expires and it spawns subagents a blocked worker may not have.

**Where E1 and E2 go in the body.** The 7-section [[present-it]] structure still governs, but §6's code-artifact prompts (diff --stat, lines changed, mathematics, timeline) have no escalation meaning. Map it: **E1 and E2 are §6** — they *are* the evidence section, replacing the test-evidence content wholesale. **§7 carries the `unlock_count` non-transcript** (the queries you would have run, and that you ran none) plus the delivery-status line. §3 assumptions, §4 alternatives and §5 risks keep their ordinary meaning. Do not leave §6 code-artifact prompts unanswered — replace them.

**`## Gate Evidence` still requires one entry per gate of the active profile** (17 in the `standard` profile, not 3 — read `assets/brief-pipeline/gates.toml`, do not work from this file's prose). **Token rule — this is mechanical, and getting it wrong fails the brief closed.** `assets/scripts/checks/brief-check.sh` applies `require_gate` to **G1, G3, G5, G5b, G7, G8, G10, G11, G12, G13, G14, G15, G16**. `require_gate` **rejects `FAIL` and `BLOCKED` outright** and demands a match on `(PASS|N/A)`. So:

- For any gate in that list, write **`N/A` followed by a surface check that names the blocker in prose** — e.g. `G13 Stale-claim: N/A — no claim exists to be fresh or stale; THIS GATE IS THE DEFECT LOCUS (claim never registers, see E1)`. **The prose carries the finding; the token gets it past the checker.** Naming which gate the defect sits on is still the most useful line in the brief — put it in the prose, not the token.
- Reserve `BLOCKED` for gates `require_gate` does *not* check.
- **Never write `PASS` on a gate you did not satisfy** just to clear the checker. `N/A` + honest prose is the sanctioned route; `PASS` is fabrication and it is the one that silently promotes.

**Two known pipeline defects you will hit here — declare them, do not work around them silently:**

1. **`G14 Test-execution-silent` cannot pass the checker as specified.** This skill and [[brief-prep]] mandate the literal tri-state `PASSED` / `NOT APPLICABLE` / `REQUIRED`; `require_gate` matches `(PASS|N/A)\b`, and **`PASSED` fails the word boundary while `NOT APPLICABLE` matches neither token.** This is lane-independent — it affects every brief, not just escalations. Write the mandated tri-state, and note the conflict in the entry.
2. **`server_touching: true` makes `check-server-touching-safety` exit non-zero by design** — its message is *"brief requires explicit … adjudication; auto-dispatch and auto-approval are forbidden."* That is the routing mechanism doing its job, not a rejection of your brief. **Do not "fix" it by writing `false`.**

**You ARE authorized to self-classify G9 in this lane.** [[catch-no-brainer]] is normally the source, but a blocked worker often cannot invoke it, and G9 is mandatory and fail-closed — so without this permission there is no compliant path. Write the `classifier_state=capability_blocker` line yourself, and state in the entry that you applied the rule table by hand rather than running the classifier.

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

### Escalation lane — delivery when the store and the mail channel are BOTH down

The common case, not the edge case: **the same defect that blocked you also took out `bd`, the follow-up-bead remedy, and `gc mail`.** Every remedy above routes through what just failed, so the escalation path shares a failure domain with the most common thing worth escalating.

Escalation-lane delivery therefore uses a **plain filesystem write**, which needs neither:

1. **Write the file to the stack path directly.** This is an ordinary file write, not `bd` — it works with the store down and with no Mayor session alive.
2. If the stack path is unwritable, write to `<city-root>/.beads/briefs/.escalation-drop/` — **create the directory if it does not exist; it is not present by default** — and say in the brief that you took the fallback. A fallback that fails at the worst moment is not a fallback.
3. **State delivery status in one line in the brief**: either a human has been signalled, or this file is **an unread letter**. Never let *"the file exists"* stand in for *"someone knows."*
4. Emit the [[catch-no-brainer]] stdout signal too if you can — as an addition to the file, never instead of it.

## Procedure

1. **Classify the lane** (see "Two input lanes"), then **locate the artifact** (branch / bead / PR / GH-issue / diff).
   - **Code-artifact lane:** ambiguous or nonexistent artifact → STOP, return UNABLE-TO-RUN with the reason.
   - **Escalation lane: being unable to reach the artifact IS the finding, not a stop condition.** Proceed. Record precisely what you could not reach and the command that proved it. **This STOP does not apply to you** — you do not need to reinterpret it, and you should not have to.
2. **Run the gates** for your lane, in order: code-artifact → tests (G1), good-test evaluation (G2). Escalation → blocker evidence (E1), reproduction (E2).
3. **Draft the brief** — frontmatter + Decision-at-Top + full-form or compact body per "Artifact format" above. **Code-artifact lane:** compute `unlock_count` (bd queries per `project_brief_stack_workflow.md`; record the transcript in §7). **Escalation lane: do NOT run store queries — the store is what failed.** Write `UNKNOWN-NOT-COMPUTED` and record in §7 which queries you would have run and that none were run. Use the escalation-lane field-rules table for every other unmeasurable field.
4. **Self-check** the Decision-at-Top INVARIANT and section completeness ("None surfaced" + reason is acceptable; blank is not).
5. **Code-artifact lane: critical-review** (registry **G4**, not G3 — see the gate-ID warning above) to APPROVING; update `status` / `review_gate` per iteration. **Escalation lane: single-pass self-check** (E3) and set `review_gate: escalation-self-checked`. Do not run the FP loop.
6. **Write the file** to the stack path; deliver per "Delivery" above.
7. **Return** the brief path + verdict + gate outcomes to the caller. When invoked from [[brief-prep]], the orchestrator's Phase 2/4/5 executions ARE gates 1–3 (do not run tests or coordinate-review a second time) and it owns deposit bookkeeping (brief-record bead, follow-up beads, epic links) — don't duplicate either; when invoked standalone, say explicitly in the return that bookkeeping has NOT been filed.

## Hard rules

- **NO presenting to the human adjudicator** — clerk channel only (above).
- **NO `bd close` on adjudication-class beads.** the human adjudicator decides; agents propose.
- **NO commits or pushes.** Brief deposits are local-only artifact writes.
- **NO `gh issue close`, NO branch deletes.** The brief recommends; the human adjudicator (via decisions.jsonl) executes.
- **Credential discipline** per [[never-echo-credentials]].

## Red flags — you are in the wrong lane, or about to fabricate

- **You CAN read the artifact, but the tests are slow, awkward, or failing.** → code-artifact lane. **Inconvenience is not blockage.** The escalation lane is not a gate-skip.
- **You are writing `N/A by construction` for G1 on work you actually performed.** → wrong lane. That phrase is for input that has no runnable artifact, not for work you chose not to test.
- **You are about to write `unlock_count: 0` because the field is typed `<int>`.** → write `UNKNOWN-NOT-COMPUTED`. "It satisfies the type and nobody would notice" is the whole problem.
- **You are inventing a wall time, an exit code, or a test result you did not observe.** → stop. **A declared N/A always beats a fabricated PASS**, and the fabricated PASS is the one that silently promotes.
- **You are marking a gate `PASS` to keep the Gate Evidence section looking clean.** → the gate the defect sits on is the most useful line in the brief. Name it `BLOCKED`.
- **You are reinterpreting step 1's STOP to let yourself proceed.** → you are in the escalation lane. Declare `lane: escalation` and use E1–E3. **You do not need a clever reading; you need the other lane.**
- **You are borrowing `review-failed` to mean "could not review."** → use `escalation-unreviewed`. A review that never ran is not a review that failed.
- **You are about to write `server_touching: false` because your brief's disposition modifies no files.** → **write `true`.** The disposition triggers an investigation that may land anywhere; `false` asserts you checked a surface you did not check. This is the `unlock_count: 0` trap one field over, and it is the one agents actually fall into.
- **You are about to write `UNKNOWN` into a field typed `<bool>`.** → use the field-rules table. `UNKNOWN` is right for free-form fields and wrong for booleans feeding fail-closed stop gates, where a parser may coerce it to falsy — producing the exact invisible-false the rule exists to prevent.
- **You are reconstructing an error string from a description because the verbatim would read better.** → `UNKNOWN-NOT-CAPTURED`, and name whose report you are relaying.

## Cross-references

- [[present-it]] — the terminal sibling: defines the section structure and both output shapes; no file, no gates.
- [[brief-prep]] — the end-to-end pipeline worker: classification, safety overrides, external review gate, deposit bookkeeping; produces its artifact per THIS skill.
- [[catch-no-brainer]] — no-brainer / capability-blocker classifier; source of `compact_eligible`. See "Two input lanes" for how its `capability-blocker` do-not-deposit rule is resolved here.
- [[decisions-to-briefs]] — the sibling for disposition/policy decisions with no artifact and no blocker; source of the `N/A by construction` gate-declaration convention this skill's escalation lane borrows.
- [[coordinate-review]] — the FP-loop used by gate 3.
- [[is-good-experiment]] / [[is-good-test]] — the test-quality rules behind gate 2.
- Mayor memories: `feedback_brief_test_evidence_required.md` (gate policy), `project_brief_pipeline_workflow.md` (pipeline state machine), `project_brief_stack_workflow.md` (stack infra + schema), `project_gate_keep_architecture.md` (gate trinity; pre-authorization future home), `feedback_two_skill_split.md` (the split this skill implements).

## Versioning

- **v1.1 — escalation lane** (2026-08-14): added the two-lane input classification, gates E1–E3, the `lane:` frontmatter field, the `UNKNOWN-NOT-COMPUTED` rule for `unlock_count`, `escalation-unreviewed` / `escalation-self-checked` status values, filesystem-write delivery for when the store and mail are both down, the [[catch-no-brainer]] `capability-blocker` conflict resolution, and the red-flags list. **Baseline-driven:** two agents were run against v1.0 with real blocked-worker scenarios (store unreachable; claim-protocol identity mismatch). Both departed from step 1's `STOP` by reinterpretation and both said so unprompted; they then **diverged** on `unlock_count` — one refused `0` as an unfounded claim, the other wrote it, noting *"it satisfies the type and nobody would notice."* That divergence is why the rules above are stated as binding defaults rather than guidance. Fixes the structural defect that the gates presupposed a code artifact the skill's own description named as its input, so a blocked worker could satisfy them only by fabricating evidence or by reasoning around the procedure.

  **Then re-tested (GREEN), and the second round found more than the first.** Both agents classified the lane in seconds, neither reinterpreted the STOP, and neither wrote `unlock_count: 0`. But they **diverged again one field over** — one wrote `server_touching: UNKNOWN` into a `<bool>`, the other `true` — which produced the field-rules table, the fail-closed boolean rule, and the matching red flag. They also caught a defect introduced by this very revision: the prose numbered the artifact gates **G1–G3**, while the registry says `G3` is `shell-scripts-testable` and `G4` is `critical-review` — a misnumbering that would declare the wrong gate `N/A` and silently omit `G4`, guaranteeing fail-closed rejection. Also from that round: the E1/E2 → §6 section mapping, `UNKNOWN-NOT-CAPTURED` for second-hand evidence, the step-3 store-query carve-out, explicit G9 self-classification authority, the never-auto-approvable rule, and creating `.escalation-drop/` rather than assuming it exists.
- **v1.0 — two-skill split** (2026-07-03, per as-4nu): created as the gated file-artifact counterpart of [[present-it]], which simultaneously dropped its gates, batch semantics, and one-at-a-time constraint. Encodes: stack path + frontmatter schema from `project_brief_stack_workflow.md`; the three HARD gates from `feedback_brief_test_evidence_required.md`; batch preparation; pre-authorized-conditions stub referencing the gate-keep architecture; clerk-channel delivery per the human adjudicator 2026-06-24.
