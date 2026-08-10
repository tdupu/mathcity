---
name: present-it
description: Dump decision-ready context into the CURRENT conversation for ONE specific question about a code artifact (branch, bead, PR, diff, GH-issue), so the decision-maker can decide with no prior knowledge. Terminal/in-conversation output only — produces NO file artifact, enforces NO pipeline gates, never batches. Enforces the Decision-at-Top INVARIANT — "What is being decided" MUST be the FIRST content after the header, before origin, math, timeline, or gates. Two output shapes — full-form (default, 7 grill-ordered sections) and compact form (decision + one-line context + recommended action + y/n confirm) when the caller passes `--compact` or upstream catch-no-brainer flagged compact-eligible. Trigger phrases "present X", "give me context on X", "what is X", "show me everything about X", "context dump on X", "walk me through X". NOT for the brief stack — to produce a gated .md brief artifact use create-brief; for the end-to-end pipeline with bookkeeping use brief-prep.
---

> **Canonical copy**: `mathcity.present-it` in this mathcity pack. Materialized agent-skills copies are fallback only.

# present-it

Present a code artifact **in the current conversation** so the decision-maker can evaluate it with no prior knowledge. The presenter does all the research; the decision-maker only reads the brief. The output is terminal text for ONE specific decision the reader is being asked to make right now — nothing is written to disk, nothing is queued.

The brief follows a **grill-with-docs** shape: decision at the top; supporting evidence organized so a challenger can attack it head-on — assumptions surfaced, alternatives named, risks foregrounded.

## When to use

Use present-it when a decision-maker in THIS conversation needs full context on one artifact to answer one question, now. Typical seat: the clerk presenting a promoted brief to the human adjudicator; any agent asked "what is X / present X / give me context on X" in-session.

**Out of scope (route elsewhere):**

- **File artifacts.** present-it never writes a `.md` brief. To produce the durable, gated brief artifact for the stack, use [[create-brief]].
- **The brief stack / pipeline.** Depositing, gating, bookkeeping, unlock-count ranking — that is [[brief-prep]] (which composes [[create-brief]]).
- **Batches.** present-it presents one artifact per invocation and carries no "prepare all before presenting any" semantics. Batch preparation is a property of the artifact pipeline — [[create-brief]] and the dispatch layer that queues its runs — not of this skill.
- **Gate enforcement.** present-it runs no test-evidence, good-test, or critical-review gates and never self-rejects on their absence. Those gates bind the `.md`-artifact pipeline. Here, missing evidence is *reported*, not *enforced* (see §6).

## Decision-at-Top INVARIANT (hard rule)

**The FIRST content after the artifact header MUST be "What is being decided."**

Not origin. Not mathematics. Not timeline. Not required gates. The decision.

This is an **invariant**, not a convention. It binds both this skill and the `.md`-artifact pipeline: [[create-brief]] and [[brief-prep]] auto-reject any brief file violating it before deposit. In conversation there is no rejector — if your draft does not open with the decision, rewrite it before presenting.

Rationale: a brief is a decision aid. If the reader can't spot the question in the first ~5 lines, the brief has failed. Every downstream section is **evidence** for the decision at the top — not context to wade through before finding it.

Violation examples (rewrite before presenting; auto-reject in the pipeline):
- Opening with "This branch was created on 2026-04-01 by …" (origin before decision)
- Opening with "The mathematics behind this change is …" (math before decision)
- Opening with a diff summary or file list
- Opening with a required-gates checklist
- Anything that requires the reader to infer the question from context

The invariant applies to BOTH output shapes below.

## Output shapes

The skill has TWO output shapes. Pick based on classification.

### Full-form (default)

Use for anything requiring judgment: unclear merge/delete/keep decisions, mathematical claims to verify, tradeoffs to weigh, risks to assess, safety-override triggers (server-touching, user-skill-touching), architecture-class artifacts.

Structure: §1 decision → §2 recommended answer → §3 assumptions → §4 alternatives → §5 risks → §6 evidence → §7 gates. See "Full-form template" below.

### Compact form

Use ONLY when ALL of the following hold:

1. Upstream [[catch-no-brainer]] flagged the brief as no-brainer-eligible (category cat-A / cat-B / cat-C / cat-D) with `compact_eligible: true` in its output.
2. Safety overrides all passed (no `server_touching`, no `user_skill_touching_override` per [[brief-prep]] §"Safety overrides").
3. Caller did not explicitly request full-form (`--full`).

OR when the caller passes `--compact` as an explicit override (the human adjudicator may force compact if they know the artifact already). The NEVER rules below trump `--compact`: a safety override, an architecture-class artifact, or a capability-blocker shape forces full-form even when compact was explicitly requested.

Compact template:

```
DECISION:  <one sentence — what is being decided>
CONTEXT:   <one sentence — why this exists / what triggered it>
RECOMMEND: <verb + object — e.g., "DELETE branch polecat/foo (superseded by bar merged 2026-06-24 in PR #217)">
CONFIRM:   y / n / grill-me-further
```

Rules:
- `DECISION` and `CONTEXT` are each ONE sentence. If either needs more, escalate to full-form.
- `RECOMMEND` names both the action and the one-line reason (why the action is safe).
- `CONFIRM y` = execute the recommended action; `n` = do not; `grill-me-further` = escalate to full-form and re-present.
- NEVER present compact when a safety override fires — those ALWAYS route to full-form + human adjudication.
- NEVER present compact for architecture-class or judgment-heavy briefs — those bypass catch-no-brainer classification and go straight to Mayor / the human adjudicator per [[catch-no-brainer]].
- NEVER present compact when catch-no-brainer flagged the shape as `capability-blocker`. In conversation, still present — full-form, reporting the blocker in §5/§6; the "resolve the blocker, then re-classify" routing belongs to the pipeline per [[catch-no-brainer]] §"Capability-blocker shape".

## Full-form template

Gather all sections before writing. Every section must have content; if genuinely N/A, say so explicitly with a one-line reason. Density beats brevity.

The section order is **grill order**: decision anchors the top; each subsequent section answers a specific challenge a reviewer would raise.

### §1 — What is being decided (INVARIANT — first content)

State the artifact name, type, and the specific question being put to the decision-maker. One or two sentences.

Example: "Should `feat/290-phase1-inline-ranks-pp` be merged to `master`, deleted as superseded, or deferred pending the sibling refactor on `feat/291`?"

This is §1. This is FIRST. See "Decision-at-Top INVARIANT" above.

### §2 — Recommended answer + one-line rationale

State YOUR recommended verdict (MERGE / DELETE / DEFER / INVESTIGATE / CLOSE-CONFIRMED / …) and a single-line reason.

The decision-maker may override, but must see your read of the situation immediately after the question. This is the reviewer's target for grilling.

### §3 — Assumptions surfaced (grill-target)

Every non-obvious assumption the recommended disposition rests on. Bulleted; each bullet is a claim a challenger could attack, followed by the evidence that supports it.

Examples:
- "Assumes PR #217 covers the same intrinsic — verified by grep of the merged diff for `MyIntrinsic`."
- "Assumes no downstream bead cites this branch by name — checked via `bd list --status=blocked | grep polecat/foo`."
- "Assumes `magma/test/foo.mag` is the only test exercising this path — bounded scan of `magma/test/`; not exhaustive."

If genuinely no assumptions, write "None surfaced" with a one-line reason for why not. Never omit §3.

### §4 — Alternatives named (grill-target)

Every plausible alternative to the recommended verdict, with a one-line implication each.

Format:
- A — MERGE (recommended): unblocks 5 beads, no known regressions.
- B — DELETE: prior work lost but supersession complete per §3.
- C — DEFER: leaves 5 beads blocked; requires re-review in N weeks.
- D — INVESTIGATE further: name the specific question that would be investigated.
- E — <anything else the reader may propose>.

The decision-maker may pick any of A/B/C/D or propose E. Never omit §4.

### §5 — Risks foregrounded (grill-target)

Two flavors, both surfaced HERE (not buried at the bottom):

**Currently-working paths this could break.**
- Currently-passing tests that touch the same code paths (list them).
- Additive change (new files only) vs. modifies existing behavior?
- If it modifies existing behavior: expected behavioral delta?

**Downstream commitments this creates.**
- Technical debt or commitment to a specific design path?
- Open questions that should be resolved before merging?
- Interface changes that other code depends on?
- Alternatives foreclosed by approving?

If both flavors surface no risks, write "None surfaced" per flavor with a one-line reason. Never omit §5.

### §6 — Supporting evidence

The rest of the evidence, in whatever order best supports the decision at the top:

**Why it was created.** Originating issue or bead (ID + title). Who created it and when (from `git log` or bead metadata). Stated goal at creation time (from issue body or earliest commit message). Problem it was solving.

**Lines of code modified.** `git diff --stat origin/master...origin/<branch>` for branches, equivalent for other artifact types. For each file: one sentence on what changed and why. Show key lines for substantive diffs.

**Test evidence (report, don't gate).** For every test that exercises the artifact, report what is known:
- Test file path
- Exact command run
- Exit code + pass/fail outcome
- Wall time
- If unrunnable, state the reason explicitly ("no Magma reachable", "requires missing DATA").

If the tests have NOT been run, say so explicitly ("tests exist at <path>; not run in this session"). For a terminal context dump, missing test evidence is *information the decision-maker weighs* — it is NOT grounds to refuse to present, and this skill has no auto-reject. The test-evidence HARD gate binds the `.md`-artifact pipeline instead: [[create-brief]] and [[brief-prep]] self-reject brief files lacking it (per the brief-test-evidence-required policy).

**Mathematics (research repos only).** For `hecke`, `differential-valuations`, `magma-diff-alg`, `magma-clifford-algebras`:
- What mathematical claim or construction does this implement?
- Is the claim known-correct? Cite reference / verified test / prior proof.
- Known edge cases, unverified assumptions, or open questions?
- Conjecture vs. theorem — state explicitly if the implementation embodies a conjecture.

For non-research artifacts: "N/A — pure engineering change."

**Timeline.** First commit, last commit, age (days since last commit), number of commits.

### §7 — Plan membership, blocking, and required gates

**Plan / epic.** Name it and link to bead or design document. Sequence: what comes before / after this artifact.

**Blocking.** Beads this artifact blocks (list them). Blockers on this artifact (list them).

**Required gates before merge.**

*improve-README (Magma/Sage repos — `hecke`, `magma-diff-alg`, `magma-clifford-algebras`).* Two triggers.

- *Required (hard gate):* branch adds/changes a package intrinsic, a new type, a data-generation script, or a database pipeline step. Do not recommend merging until improve-README has run and `magma/test/README-tests/` artifacts exist and pass.
- *Coverage opportunity (recommend):* branch exercises a code path, edge case, or mathematical case not currently covered in `magma/test/README-tests/`. Scan `README-tests/` for coverage of the same intrinsic + inputs. Examples that warrant improve-README even without a new intrinsic: non-rational Hecke eigenvectors when only the rational case is in README-tests; a new field extension type; a new conductor or order that exercises a different branch. State explicitly whether a coverage gap exists and name the missing case if so.
- *Not required:* only development test files (`magma/test/test-*.mag` not in `README-tests/`), or modifies data files only, and all affected cases already covered.

*LaTeX hard gate (`differential-valuations`, `hecke` notes.tex, `homog`, `jacobi`).* Any edit to `notes.tex` on `main` requires the human adjudicator's explicit approval of the specific diff before push.

*agent-skills.* PR-only to `main` (ADR 0001). No direct push to `main`.

## Output format (full-form)

Write structured prose. Prose for §1, §2, §4 alternatives text, §5 risks, §6 evidence subsections. Bullets for lists (files, commits, test names, bead IDs, assumptions in §3).

End with a **Required gates summary** one-liner (e.g., "improve-README: not required" or "improve-README: REQUIRED — not yet run"). The Decision options block from §4 is repeated verbatim at the end for the reader's convenience.

Ask for the decision at the end.

## Cross-references

- [[create-brief]] — the file-artifact sibling: same section structure, written to a `.md` in the brief stack, gated (test-evidence + good-test + critical-review). Use it whenever the brief must outlive the conversation.
- [[brief-prep]] — the end-to-end pipeline orchestrator (classification, external review, deposit, bookkeeping); composes [[create-brief]]; enforces the Decision-at-Top INVARIANT in its Phase 4 self-review.
- [[catch-no-brainer]] — upstream classifier that signals `compact_eligible` and identifies `capability-blocker` shapes that MUST NOT go compact.
- [[grill-and-present]] — legacy orchestrator (brief + grilling + gates in one skill); retirement proposed under as-4nu in favor of [[create-brief]] + [[brief-prep]].
- [[grilling]] / [[grill-with-docs]] — the interrogation style this template is shaped by.
