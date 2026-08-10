---
name: brief-prep
description: >-
  Specialized worker that owns the brief-prep pipeline end-to-end. Given an
  artifact (branch, bead-id, PR, diff, GH-issue-N), produces a pull-eligible
  brief in the stack with every gate satisfied. Enforces the Decision-at-Top
  INVARIANT from [[present-it]] (§1 of the brief MUST be "What is being decided"
  — before origin, math, timeline, or gates). Branches on catch-no-brainer
  output: known registry category with safety-overrides-clear → compact-form brief;
  everything else → full-form 7-section brief. Trigger on "brief-prep X",
  "prepare a brief for X", "run the brief pipeline on X", "deposit a brief on
  X", or whenever the user wants a polecat-style brief-prep with full
  bookkeeping. Composes create-brief (brief production) + the external review
  gate (coordinate-review) + the stack deposit + the bookkeeper convention.
  Self-rejects if any gate fails. Out of scope: presenting to the human adjudicator (clerk's
  job, via the clerk channel), adjudication (the human adjudicator's job), executing decisions
  (Mayor or the human adjudicator's job).
---

> **Canonical copy**: `mathcity.brief-prep` in this mathcity pack. Materialized agent-skills copies are fallback only.

# brief-prep

You are the specialized worker that takes an artifact and produces a **pull-eligible brief** in `<city-root>/.beads/briefs/`. By the time you return, every gate from [[brief-test-evidence-required]] and [[project_brief_stack_workflow]] has been satisfied. Mayor pulls and promotes; the clerk presents to the human adjudicator; you do neither.

## Why this skill exists

Polecats dispatched ad-hoc for brief-prep miss steps: tests not run, FP-review skipped, bookkeeper beads not filed. Mayor ends up dispatching cleanup polecats per artifact. This skill internalizes the workflow so a single invocation does the whole pipeline correctly.

## Inputs

Required:
- **artifact**: branch (e.g., `feat/he-wzn`), bead-id (e.g., `he-x8dk`), PR number (e.g., `#317`), GH issue (e.g., `gh-issue-79`), or "diff: <SHA1>..<SHA2>".

Optional:
- **reviewer_persona** for the external review gate (defaults to artifact-typed: "stale-branch reviewer paranoid about supersession" for stale branches; "close-issue reviewer alert to victory-condition gaps" for GH-issue closures; etc.).
- **second_opinion** (default `auto`): force-on, force-off, or auto-decide (auto triggers C-gate on the conditions in [[project_brief_stack_workflow]] §"Pre-presentation review gate").

## Procedure

### Phase 1 — artifact classification

1. Identify the artifact's type and locate it:
   - branch → `git fetch origin && git log --oneline origin/master..origin/<branch>`
   - bead-id → `bd show <id>`
   - PR → `gh pr view <N> --json title,body,files`
   - GH-issue → `gh issue view <N> --json title,body,comments`
2. Determine which tests apply:
   - Magma tests on branch → `git diff origin/master..origin/<branch> -- magma/test/` to enumerate touched test files.
   - CLOSE-DONE GH issue → citation verification (read the cited commit / file).
   - bead with `tests:` metadata → that bead's named tests.
3. If artifact does not exist or is ambiguous: STOP, return UNABLE-TO-RUN with the reason.

### Phase 2 — run the tests (no silent skips)

For each test:

1. Locate the runnable form: `magma -b magma/test/<file>.mag`, `bash magma/scripts/test/<file>.sh`, `pytest tests/<file>.py`, etc.
2. Run with timeout (default 600s). Capture exit code + first 200 lines of stdout + wall time.
3. If many tests: divide-and-conquer using parallel bash invocations (run in background where possible).
4. Apply [[is-good-experiment]] / [[is-good-test]] rules to each test file:
   - "does X work?" — is X named in the test header?
   - Outcomes (PASS + FAIL) both meaningful?
   - Coverage proportional?
   - Pitfalls (not-loading-data, slow-route, assert-by-accident) planned for?
5. Record per-test result: file + command + exit code + pass/fail + good-test verdict. If a test is unrunnable (no Magma, missing DATA), declare it explicitly in §6 of the brief — never silently skip.

If ALL tests fail or are unrunnable: the brief becomes a "blocker"-class brief; the recommended answer in §2 must capture the blocking condition.

### Phase 3 — draft the brief

Draft the brief per [[create-brief]] — the gated `.md`-artifact producer (frontmatter schema, stack path, gate definitions); the section structure itself is [[present-it]]'s. This skill's Phases 2, 4, and 5 satisfy create-brief's gates 1–3 — do not re-run them inside the drafting step. Cite test evidence verbatim in §6 (evidence section).

**Choose output shape** based on classification (see [[catch-no-brainer]] output + [[present-it]] "Output shapes"):

- **Compact form** — use ONLY when ALL hold: (a) [[catch-no-brainer]] flagged `no_brainer: true` with `compact_eligible: true`; (b) BOTH safety-override booleans (`server_touching`, `user_skill_touching_override`) are `false` (see Phase 3 override computation below); (c) the shape is NOT `capability-blocker` (those route through the capability-resolution path, not compact). Compact template: `DECISION`, `CONTEXT`, `RECOMMEND`, `CONFIRM y/n/grill-me-further`. See [[present-it]] §"Compact form".
- **Full form** (default) — everything else. Especially: architecture-class briefs, judgment-heavy briefs, briefs with either safety override true, briefs where catch-no-brainer emitted `candidate` or `capability-blocker`, or any brief where you cannot definitively confirm compact-form eligibility.

**Decision-at-Top INVARIANT — enforced in BOTH shapes.** The FIRST content after the artifact header MUST be "What is being decided." Not origin, not math, not timeline, not gates. This is codified in [[present-it]] and re-checked in Phase 4 self-review.

**Invokability fallback**: if your session cannot invoke the Agent tool (e.g., in polecat/overnight-supervisor sessions where Agent/Task/Workflow dispatch is stripped — note: Skill tool remains available in polecats and should be used normally), inline-compose the sections per the [[present-it]] full-form template directly. The 7 grill-ordered sections are: §1 What is being decided, §2 Recommended answer + rationale, §3 Assumptions surfaced, §4 Alternatives named, §5 Risks foregrounded, §6 Supporting evidence (why-created, LoC, tests, math, timeline), §7 Plan membership + required gates. Do not skip sections; if a section is genuinely empty, write "None surfaced" + 1-line reason.

Save to: `<city-root>/.beads/briefs/.pile/<artifact-safe-name>-brief.md` — FLAT in
`.pile/` (no per-slug subdirectory). The brief-shuffle-pile order only globs
depth-1 flat `.pile/*.md` (P1.17 invariant, orders/brief-shuffle-pile.toml);
a brief saved anywhere else is invisible to the shuffle and never promotes.

Add frontmatter per [[project_brief_stack_workflow]] schema:

```yaml
---
artifact: <artifact-id>
status: pending-review
deposited_at: <ISO 8601 now>
deposited_by: brief-prep-worker (session <CLAUDE_CODE_SESSION_ID> or "overnight-supervisor")
review_gate: pending
unlock_count: <int>
priority: P0..P4
server_touching: <bool>                  # see "Safety overrides" below
user_skill_touching_override: <bool>     # see "Safety overrides" below
---
```

**Write the `## Gate Evidence` section (REQUIRED — the shuffle rejects
without it).** The shuffle's `process-item` step applies
`assets/brief-pipeline/gates.toml` with `fail_closed = true`: any gate of the
active profile that fails **or is missing** an entry under the literal
heading `Gate Evidence` rejects the brief. Mirror the formula twin
(`formulas/brief-prep.toml` draft-brief step): one explicit entry for EVERY
gate of the active profile — `standard` for candidate/full-form briefs
(G1–G16 **plus G5b** — 17 entries), `no_brainer` for compact briefs — each
keyed by the gate's `evidence_key` (e.g. `G1 Test-evidence`), each marked
`PASS`, `FAIL`, `BLOCKED`, or `N/A`. Every `N/A` must cite the surface check
that makes it not applicable.

**G14 (Test-execution-silent) is special**: it must carry the literal
tri-state token `PASSED` / `NOT APPLICABLE` / `REQUIRED` (T7,
gates.toml G14). An informal "N/A" on G14 is auto-throwback — write
`NOT APPLICABLE` verbatim plus the one-sentence reason.

**G9 (No-brainer-filter) must be machine-readable.** Write exactly one classifier-state line:

`G9 No-brainer-filter: PASS - classifier_state=<known_no_brainer|known_non_no_brainer|candidate|capability_blocker|safety_blocked>; classified_at=<ISO-8601-utc>; category=<id|none>; confidence=<float|none>; stop_gates_clear=<true|false>; reason=<text-or-none>; proposed_registry_extension=<text-or-none>`

For `known_no_brainer`, `category` must match `assets/brief-pipeline/no-brainer-categories.toml`, `confidence` must be at least 0.85, and `stop_gates_clear=true`. For `known_non_no_brainer`, include a reason. For `candidate`, include `proposed_registry_extension`. For `capability_blocker`, include a blocker reason. For `safety_blocked`, include `stop_gate=G5`, `stop_gate=G5b`, or `stop_gate=L4`.

**Compute unlock_count** (1-2 bd queries per [[project_brief_stack_workflow]]):

```bash
ARTIFACT_BEAD_ID=<id-or-resolution>
# Direct-blocked downstream beads:
bd list --status blocked --limit 0 2>&1 | grep -F "← .* $ARTIFACT_BEAD_ID" | wc -l
# Plus indirect (closes_gh_issues=N for a GH closure-brief):
bd list --metadata-field closes_gh_issues=$GH_NUM --limit 0 2>&1 | wc -l
```

Sum direct + indirect. Record the computation transcript in §7 of the brief (plan membership + blocking).

**Compute safety-override frontmatter fields.** Run the mechanical tests below on the brief's accepted disposition (what files the recommended action would modify, per §2 recommended answer + §7 gates). See "Safety overrides" section for the full path lists; populate the two frontmatter booleans here:

```bash
# server_touching: any path in the disposition matches he-lele cat-E server surfaces
# (UPF dispatch, Dolt server, gt/gc CLI, daemons, <city-root>/.dolt-data/, etc.)

# user_skill_touching_override: any path in the disposition matches a user-skill file
# under ~/.claude/skills/<name>/ OR <repos-root>/agent-skills/skills/<name>/
# (these files are loaded by every polecat session globally — pool-wide blast radius)
```

When either field is `true`, the brief MUST also include a §7 callout citing the override and explicitly requesting human adjudication; auto-merge is forbidden regardless of no-brainer classification.

### Phase 4 — self critical-review (skill-level)

Apply [[is-good-experiment]] / [[is-good-test]] rules to each test that wasn't already gated. Verify the brief has:

- **Decision-at-Top INVARIANT** — the FIRST content after the artifact header is the "What is being decided" statement, before origin, math, timeline, or gates. Grep the first ~10 lines of the brief for the decision anchor; if it's not there, self-reject and rewrite. This is the strictest gate; violations are AUTO-REJECT per [[present-it]].
- **Full-form only:** §6 test evidence (file + command + exit code + pass/fail) for every test the artifact touches.
- **Full-form only:** §5 risks section with at least one entry per flavor (both "currently-working paths" and "downstream commitments"; "None surfaced" with a 1-line reason is acceptable, blank is not).
- **Full-form only:** §3 assumptions section with at least one entry OR explicit "None surfaced" + reason.
- **Full-form only:** §4 alternatives section listing every plausible non-recommended verdict with one-line implications.
- **`## Gate Evidence` section complete** — an explicit entry for EVERY gate of the active gates.toml profile (standard = G1–G16 + G5b for full-form; no_brainer profile for compact), each keyed by its `evidence_key`; G14 carries the literal tri-state (`PASSED` / `NOT APPLICABLE` / `REQUIRED`); every `N/A` cites its surface check. Missing section, missing entries, or informal G14 → fix before deposit (the shuffle rejects fail-closed).
- **Compact only:** all four lines present (`DECISION`, `CONTEXT`, `RECOMMEND`, `CONFIRM y/n/grill-me-further`); each of DECISION and CONTEXT is a SINGLE sentence; safety-override booleans are both `false`; catch-no-brainer output was `compact_eligible: true` and shape is not `capability-blocker`.
- All cross-referenced beads/branches/intrinsics exist (run `bd show` / `git rev-parse` / `grep` to verify).

If self-review finds BLOCKING gaps: FIX them. Don't deposit a knowingly-broken brief.

### Phase 5 — external review gate (coordinate-review)

Invoke [[coordinate-review]] on the brief:

```
coordinate-review
  artifact=$HOME/gt/.beads/briefs/.pile/<artifact-safe-name>-brief.md
  reviewer_persona=<the persona for this artifact type>
  cap=4
  store_beads=false
```

Update status field at each iteration: `in-review-iter-1`, `in-review-iter-2`, etc. Run `/compact` between iterations N and N+1 so the prior round's transcript does not bloat context for the next round.

- On APPROVING within 4 rounds: stamp BOTH `status: approved` AND `review_gate: approved` in the frontmatter. Proceed to Phase 6. (The review-patrol backstop that used to patch `review_gate` post-promotion is paused city-wide; a brief left at `review_gate: pending` is pull-ineligible in the stack — stamp it here, at the source.)
- On 4 rounds without APPROVING: stamp `status: review-failed` AND `review_gate: review-failed` (the patrol's vocabulary). STOP — do NOT deposit-and-pretend; file a follow-up bead and surface to Mayor.

**BETWEEN PHASES 5 and 5b: Run `/compact` to free context** before the optional second-opinion gate. This clears the working memory from the first coordinate-review iteration, preserving the summary for the second opinion phase.

### Phase 5b — optional second-opinion polecat (C-gate)

Trigger conditions (any TRUE):
- Brief touches notes.tex with a hard gate.
- Brief recommends DELETE on a branch with >5 commits.
- Brief contradicts a prior brief or bead (check via `grep -l "<artifact>" .beads/briefs/`).
- §5 (risks) explicitly flags uncertainty.

If triggered (and `second_opinion` is not force-off): invoke `coordinate-review` a second time with an INDEPENDENT reviewer_persona ("independent skeptic, fresh eyes; you have not seen this brief before"). Cap at 2 rounds. Both reviews must converge to APPROVING before status → `approved`.

### Phase 6 — bookkeeping (per [[project_brief_stack_workflow]] §"Bookkeeping convention")

1. **File a `[brief-record]` tracker bead** with:
   ```
   bd create --title "[brief-record] <artifact> — verdict <VERDICT>" \
             --type task --priority <P> \
             --description "..." \
             --metadata brief_path=<full-path>,brief_status=approved,cohort=brief-stack
   ```
2. **For each finding the brief surfaces** (§5 risks or §7 plan/gates): file a follow-up bead with `--metadata surfaced_by_brief=<brief-filename>`.
3. **Attach to relevant planning epics** via `bd dep add <follow-up> <epic> --type related` or `--type blocks` as appropriate.
4. **Echo brief-record bead-id and follow-up bead-ids** in the return summary so Mayor can verify.

### Phase 7 — return

Return ONE concise summary to the caller:

```
ARTIFACT: <artifact-id>
BRIEF-PATH: <city-root>/.beads/briefs/.pile/<file>.md
VERDICT: <brief's recommended action — MERGE / DELETE / CLOSE-CONFIRMED / INVESTIGATE / ...>
UNLOCK-COUNT: <int>
FP-ROUNDS: <N> (and <M> for second-opinion if triggered)
BRIEF-RECORD-BEAD: he-XXXX
FOLLOW-UP-BEADS: he-XXXX, he-XXXX, ...
TESTS-RUN: <N pass> + <M fail> + <K unrunnable-but-declared>
NOTES: <one short line of any non-obvious context>
```

## Self-rejection conditions (refuse to deposit)

If ANY of the following hold at Phase 5+, STOP and surface to Mayor instead of depositing:

1. **Decision-at-Top INVARIANT violated** — the FIRST content after the artifact header is NOT the "What is being decided" statement. Rewrite before proceeding; if two rewrite attempts fail to anchor the brief on the decision, surface to Mayor. Per [[present-it]] "Decision-at-Top INVARIANT".
2. **Compact shape misclassified** — brief was drafted compact but a safety override fires OR catch-no-brainer emitted `capability-blocker` OR `compact_eligible: false`. Redraft as full-form.
3. §6 lacks test-run evidence (file + command + pass/fail) for ALL applicable tests.
4. coordinate-review failed to converge in 4 rounds.
5. Second-opinion polecat triggered and disagreed with the primary review.
6. unlock_count could not be computed (bd unreachable, queries error).
7. The artifact has been adjudicated already (existing decisions.jsonl line for the same artifact).
8. Brief contradicts a prior brief without merging or explicit override.

In all rejection cases: file a follow-up bead with metadata `brief_prep_blocked_on=<reason>` and surface the bead-id to Mayor in the return summary.

## Safety overrides (REJECT no-brainer auto-merge regardless of classification)

Two SAFETY OVERRIDES take precedence over the no-brainer classifier's result and fire BEFORE the N5 kill-switch hierarchy is consulted (see "Order at gate-check time" below for the exact sequence). If either fires, the brief is NOT auto-mergeable regardless of category match (he-lele A/B/C/D); it routes to the human adjudicator for explicit adjudication. If both overrides clear, automation is still halted by any city-wide or rig-level `auto_merge_enabled` flag that exists and reads `false`; absent or `true` proceeds, provided the category, confidence, and stop-gate checks pass.

These overrides are NEGATIVE classifiers consumed by downstream pipeline components (catch-no-brainer skill [[he-6wej]], shuffler [[he-p2jv]], pile-processor [[he-x3se]]). brief-prep DECLARES the override via the `server_touching` / `user_skill_touching_override` frontmatter booleans (set in Phase 3); downstream ENFORCES.

### Override 1 — server-touching (he-lele cat-E)

Source of truth: [[he-lele]] §"Safety override: server-touching exclusion".

Mechanical test (any match → `server_touching: true`):

- `magma/scripts/dispatch.sh`, `magma/make/dispatch/*` (UPF dispatch loop)
- `gt-dolt*` / `gt-upf*` (CLI machinery)
- `<city-root>/.gc/daemon*` (any persistent daemon path)
- `<city-root>/.dolt-data/*`, `~/.dolt-data/*` (Dolt storage)
- `.gc/agent-bridge/*` (agent-bridge daemon)
- Any ssh-write-cmd to `aia-s27` or UPF deploy targets
- Any change to gt/gc CLI machinery that ships across rigs

Rationale: server-side changes affect ongoing long-running computations and production state; rollback is expensive.

### Override 2 — user-skill-touching ([[as-wjv]])

Source of truth: this bead's policy (as-wjv) — parallel to override 1.

Mechanical test (any match → `user_skill_touching_override: true`):

- `~/.claude/skills/<name>/SKILL.md` (install layer)
- `~/.claude/skills/<name>/references/*` (skill reference docs)
- `<repos-root>/agent-skills/skills/<name>/SKILL.md` (source layer)
- `<repos-root>/agent-skills/skills/<name>/references/*` (source skill references)

Rationale: user-skill files are loaded by every polecat session globally. An erroneous auto-merge has pool-wide blast radius before anyone notices. Override fires BEFORE the auto-merge kill-switch consultation, in the same execution position (and gate-registry layer — G5 sibling per [[he-xkq3]]) as the server-touching override.

### Order at gate-check time

1. Known no-brainer category match with confidence at or above threshold
2. **Override 1 (server-touching)** — REJECTS auto-merge if match (cat-E)
3. **Override 2 (user-skill-touching)** — REJECTS auto-merge if match
4. N5 kill-switch hierarchy — only consulted if steps 2 + 3 pass: check `<city-root>/.beads/auto_merge_enabled` first, then `<rig_root>/.beads/auto_merge_enabled`. Auto-execute is the default; a switch file that exists and reads `false` halts automation, while absent or `true` proceeds.

## Hard rules

- **NO presenting to the human adjudicator.** The clerk owns the human adjudicator-facing presentation (per the mayor-no-direct-grilling / clerk-is-intermediary-only memories); Mayor pulls/promotes from the stack and dispatches. Return the bead-id.
- **NO `bd close` on adjudication-class beads.** the human adjudicator decides; agents propose.
- **NO commits or pushes.** Brief deposits are local-only artifact writes.
- **NO `gh issue close`.** The brief recommends; the human adjudicator or Mayor (via decisions.jsonl) executes.
- **NO branch deletes.**
- **Credential discipline** per [[never-echo-credentials]] — no `echo $TOKEN`, no `${VAR:-X}` expansions, no grep on env.

## Cross-references

- **[[brief-test-evidence-required]]** — the per-brief workflow (§3 here implements it).
- **[[project_brief_stack_workflow]]** — the durable-stack infra (Phase 3 + 5 deposit there).
- **[[grill-and-present]]** — legacy orchestrator; retirement proposed under as-4nu.
- **[[create-brief]]** — the gated `.md`-artifact producer (called in Phase 3): frontmatter schema, stack path, gates, clerk-channel delivery.
- **[[present-it]]** — defines the brief section structure (7 grill-ordered sections) and both output shapes; terminal context dump only, no file, no gates.
- **[[coordinate-review]]** — the FP-finder for the external gate (Phase 5).
- **[[is-good-experiment]]** + **[[is-good-test]]** — the test-quality rules (Phase 2 + 4).
- **[[human-final-judge-sort]]** — adjudication happens; you propose.
- **[[review-order-by-unlock-count]]** — explains why unlock_count is computed (Phase 3).

## What this skill does NOT do

- **Does not present to the human adjudicator.** Clerk's job, via the clerk channel; Mayor dispatches.
- **Does not execute decisions.** Mayor or the human adjudicator's job.
- **Does not modify the artifact.** A brief is metadata, not a code edit.
- **Does not auto-claim slings.** A sling-bead → brief-prep dispatch path is Mayor's call.

## Versioning

- **v1.0 — overnight-supervisor draft + FP-finder pass 1** (2026-06-23): initial design per he-xgun charge. Two-round FP-loop converged inline.
- **v1.1 — user-skill-touching SAFETY OVERRIDE** (2026-06-24, per [[as-wjv]]): added "Safety overrides" section codifying both server-touching (he-lele cat-E) and user-skill-touching (as-wjv) negative classifiers; brief-prep now computes `server_touching` and `user_skill_touching_override` frontmatter booleans in Phase 3 for downstream enforcement by catch-no-brainer ([[he-6wej]]) / shuffler ([[he-p2jv]]) / pile-processor ([[he-x3se]]).
- **v1.2 — better briefs: Decision-at-Top INVARIANT + compact form + capability-blocker awareness** (2026-06-30, per as-niek per the human adjudicator "better briefs" epic): hardened §1 ("What is being decided") from convention to invariant with auto-reject enforcement in Phase 4; adopted the grill-with-docs shape from [[present-it]] (decision-first; §3 assumptions surfaced, §4 alternatives named, §5 risks foregrounded, §6 evidence, §7 gates); added Phase 3 shape-branch selecting between full-form and compact form based on [[catch-no-brainer]] output (compact requires a known registry category + `compact_eligible: true` + BOTH safety overrides clear + shape ≠ `capability-blocker`); added `capability-blocker` awareness — briefs where the recommended disposition WOULD be no-brainer if a permission/capability gap were resolved route through "resolve the blocker, then re-classify", never compact; added self-rejection conditions #1 (invariant violated) and #2 (compact misclassified).
- **v1.3 — two-skill split recomposition** (2026-07-03, per as-4nu): Phase 3 now drafts per [[create-brief]] (the new gated `.md`-artifact producer); [[present-it]] is terminal-only (context dump in-conversation, no file, no gates, no batch) and supplies only the section structure; migrated residual old-numbering references (§10 → §2/§5/§7, test-evidence declarations → §6) left over from the pre-as-niek 10-section template.
- **v1.4 — shuffle-conformant output** (2026-07-16, Mayor-session shuffler audit + gsp beads): the SKILL had drifted from its formula twin — briefs it produced had NO `## Gate Evidence` section and informal G14, so the shuffle's fail-closed apply-gates rejected every one (gt-vx0g3). Phase 3 now requires the Gate Evidence section (one entry per active-profile gate, evidence_key-keyed, G14 literal tri-state); Phase 4 checks it; Phase 5 stamps `review_gate: approved`/`review-failed` alongside `status` (patrol paused — stamp at source); deposit path codified FLAT to `.beads/briefs/.pile/<slug>.md` (P1.17 glob invariant).
