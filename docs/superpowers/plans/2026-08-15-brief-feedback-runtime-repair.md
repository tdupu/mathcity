# Brief Feedback Runtime Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the unified brief queue practical at runtime: adjudicated briefs stop reappearing, decision briefs carry the gates they claim, direct decision producers stop inheriting the unsatisfiable `standard` profile, and rejected briefs create feedback records without relying on a skipped prompt bullet.

**Architecture:** Keep the unified `.beads/briefs/.pile -> stack` design. Add small deterministic scripts/checks where the current system relies on LLM prompt compliance, and keep formula/order TOML as orchestration. Do not rewrite `stack/.index.jsonl` as part of presentation filtering; selectors read it and fall back to brief frontmatter.

**Tech Stack:** POSIX shell, Python 3 standard library, TOML formula/order files, existing `brief-check.sh` gate checks.

## Global Constraints

- Work on the deployed/source-owned side: `<repos-root>/mathcity`.
- Do not mutate live `.beads` data during local tests; fixture tests use temporary directories.
- Do not hand-run `gc event emit` as proof for proof 4. Acceptance is a rejected brief directory producing `.producer-failure-pile/<slug>.toml` from durable filesystem state.
- Preserve the existing event orders for compatibility, but add condition-triggered backstops over durable state.
- Preserve `.index.jsonl` formatting by reading and filtering only; no whole-file reserialization for presentation.
- A producer-repair brief must be self-excluded with `producer_contract: brief-producer-repair.v1`.
- No git commit, push, PR, or live GitHub issue write without explicit authorization.
- QUIMBY positive control, 2026-08-15 23:08/23:51: brief #16 passed after hand-written decision Gate Evidence. Treat that as proof that `gt-rcav8b` is the decisions-to-briefs defect, not as proof that proof 4 is green. Proof 4 still requires the next genuine gate rejection to create a failure record without a synthetic event.
- Runtime acceptance choice, 2026-08-16 grilling: proof 4 does not block source landing. After landing, run a controlled live canary by depositing a dedicated test-only producer-origin `standard` brief with obvious provenance (`source_formula: proof-4-runtime-canary`) that predictably fails G4. Do not hand-run `gc event emit`, do not manually backfill, and do not mutate real queued briefs. Keep the rejected canary directory and producer-failure record as durable evidence, clearly marked as runtime canary artifacts; archive later only through the normal brief archive path if needed.
- Execution context: outside agent in the human adjudicator's local session, conservative git policy. Source changes land only through explicit git authorization; live runtime canary runs only after the source patch is landed/deployed.

## Hygiene and Impact

**Root-cause invariants.**

- Rejected-brief feedback is derived from durable `.pile/.rejected/<slug>/` state, not from a prompt bullet or synthetic event.
- Decision-shaped producers stamp their intended `gate_profile` explicitly, so `brief-shuffle` cannot silently default them to `standard`.
- Decision Gate Evidence uses literal gate tokens and files the one-bead `type=decision` brief record before deposit.

**Wheel-check / alternatives.**

- Feedback trigger alternatives: event-only rejected path (ruled out; workers skipped the prompt bullet), synthetic `gc event emit` proof (ruled out; reproves only the old event order), durable rejected-dir condition trigger (adopted).
- Producer profile alternatives: reuse `decision` (adopted; current direct producers are human disposition briefs), create `producer_decision` (ruled out until there is a policy distinction), keep inherited `standard` (ruled out; confirmed `mc-uvg` failure mode).
- Proof-4 runtime alternatives: wait for a natural rejection (ruled out as nondeterministic), mutate a real queued brief (ruled out as unsafe/noisy), create a dedicated canary brief after landing (adopted).

**Impact review.**

- Upstream impact: source edits remain inside the owned mathcity pack. No direct edits to gascity core, beads, vendor trees, or upstream-owned packs are planned.
- Downstream impact: `present-briefs`, `brief-shuffle` feedback records, direct decision producers, and producer-repair rollups consume the new contracts. Existing event orders are preserved for compatibility, while condition orders add the durable backstop.
- Runtime state impact: the proof-4 canary intentionally creates one clearly labeled rejected brief and one failure record in the live city brief queue after landing. These are test evidence, not source artifacts, and must be archived only through the normal brief archive path if they later become noise.

**Documentation pass.**

- Before landing, run or explicitly record the `improve-documentation` pass for the changed user-facing brief workflow surfaces. At minimum, keep `docs/testing-guide.md` and the permanent plan artifact current with the new local runner, producer-profile regression, and runtime proof-4 acceptance boundary.

---

### Task 1: Harden Local Test Runner

**Files:**
- Modify: `scripts/run-local-tests.sh`
- Modify: `tests/test-runner/test_runner_failure_propagation.sh`

**Interfaces:**
- Consumes: discovered shell test paths from `scripts/run-local-tests.sh`.
- Produces: runner behavior where child tests cannot consume the discovery file through stdin.

- [ ] **Step 1: Add failing fixture coverage**

Extend `tests/test-runner/test_runner_failure_propagation.sh` with a discovered shell test that reads stdin and a later shell test that must still run. Before the runner fix, the stdin reader can consume remaining discovery lines.

- [ ] **Step 2: Close child-test stdin**

Change the runner loop from `bash "$script"` to `bash "$script" </dev/null`.

- [ ] **Step 3: Verify**

Run:

```bash
bash tests/test-runner/test_runner_failure_propagation.sh
```

Expected: PASS, with the failure summary still preserving the intentionally failing fixture.

### Task 2: Stop Re-presenting Adjudicated Stack Rows

**Files:**
- Modify: `skills/present-briefs/SKILL.md`
- Modify: `tests/present-briefs-unified-source/smoke_test.sh`

**Interfaces:**
- Consumes: `stack/.index.jsonl` rows and pointed markdown frontmatter.
- Produces: Method 1 selector output containing only ready/non-terminal briefs.

- [ ] **Step 1: Add fixture rows**

Extend the selector test with:

- a row with `manifest_status: "adjudicated"`,
- a native row lacking `manifest_status` whose brief frontmatter says `status: adjudicated`,
- a native row with no terminal status that should still print.

- [ ] **Step 2: Implement selector filter**

In Method 1, skip entries whose index status or frontmatter status is terminal/resolved. Treat missing status as presentable, and keep malformed/missing files fail-open so the selector does not hide unknown work.

Terminal statuses include `adjudicated`, `decided`, `archived`, `closed`, `rejected`, `superseded`, `moot`, `rescinded`, `changes_required`, `deferred`, `draft`, plus `adjudicated:*`, `needs-revision*`, `approved-slung`, `brief-prep-dispatched`, and `present-it-pending`. Treat `manifest_status=approved` as terminal for migrated legacy rows, but do not treat frontmatter `status: approved` as terminal; native artifact briefs use it as a ready state after brief-prep approval.

BART review note, 2026-08-15 23:54: `briefed` and `present-it-pending` are safe in the terminal set only while deposit paths use `ready` for newly presentable briefs. Add a selector comment or regression guard before landing so a future deposit path cannot silently hide a live brief by writing `status: briefed` or `status: present-it-pending` as a ready state.

- [ ] **Step 3: Verify**

Run:

```bash
bash tests/present-briefs-unified-source/smoke_test.sh
```

Expected: future-deferred and adjudicated/resolved rows are absent; ready rows remain.

### Task 3: Require Gate Evidence in Decision Briefs

**Files:**
- Modify: `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`
- Modify: `formulas/brief-gate-keep.toml`
- Create: `tests/decisions-to-briefs-gate-evidence/smoke_test.sh`
- Modify: `tests/unified-brief-gate-profiles/smoke_test.sh`

**Interfaces:**
- Consumes: the `decision` profile from `assets/brief-pipeline/gates.toml`.
- Produces: decision-brief authoring instructions that include `## Gate Evidence` with the decision profile's gates.

- [ ] **Step 1: Add static regression**

Create a shell test that verifies the skill explicitly requires `## Gate Evidence` and the decision-profile gate lines `G5`, `G5b`, `G8`, `G9`, `G11`, `G12`, and `G13`.

- [ ] **Step 2: Patch the skill template**

Add a required section to the draft procedure and pile conventions. Decision-shaped briefs must record explicit `PASS` or `N/A` evidence for every decision-profile gate. G9 must carry `classifier_state`, `reason` or category fields, and `classified_at=<UTC ISO timestamp>`.

QUIMBY positive-control detail to preserve in the template: tokens must be literal `PASS` or `N/A` (not `PASSED`, not placeholder `PASS|N/A`), and G8 must cite a `type=decision` brief bead filed BEFORE deposit.

- [ ] **Step 3: Patch latent gate-keep enum**

Add `decision`, `lost_bead_filter`, and `producer_repair` to `brief-gate-keep.toml`'s `gate_profile` enum so the shipped profiles will not fail if the formula is wired later.

- [ ] **Step 4: Verify**

Run:

```bash
bash tests/decisions-to-briefs-gate-evidence/smoke_test.sh
bash tests/unified-brief-gate-profiles/smoke_test.sh
```

Expected: the skill instruction and gate-profile checker agree.

### Task 3b: Pin Direct Decision Producers To The Decision Profile

**Files:**
- Modify: `formulas/pr-pipeline-briefed.formula.toml`
- Modify: `formulas/create-issue-briefed.formula.toml`
- Modify: `formulas/planning-briefed.formula.toml`
- Modify: `formulas/commission-work-briefed.toml`
- Modify: `formulas/formula-creator-math.toml`
- Modify: `formulas/smoke-test-briefed.toml`
- Modify: `formulas/no-brainer-candidate-curate.toml`
- Modify: `formulas/brief-producer-repair.toml`
- Create: `tests/producer-decision-gate-profiles/smoke_test.sh`

**Interfaces:**
- Consumes: direct producer formulas that file already-reviewed human decision briefs without running the full `brief-prep` critical-review loop.
- Produces: deposited decision briefs with explicit `brief_kind`, `gate_profile`, and `feedback_sink`, so `brief-shuffle` does not silently default them to `standard`.

- [ ] **Step 1: Add static regression**

Add a test that scans the direct producer formulas above for:

- `brief_kind: decision`, `gate_profile: decision`, and `feedback_sink: brief_quality_failure` on direct human decision briefs,
- `brief_kind: producer_repair`, `gate_profile: producer_repair`, and `feedback_sink: brief_quality_failure` on producer-repair briefs.

- [ ] **Step 2: Patch direct producer templates**

For direct producer formulas that ask the human adjudicator to approve a PR body, issue body, plan, commission graph, formula draft, test-evidence brief, or no-brainer category curation, require `gate_profile: decision` in the deposited brief frontmatter and say the `## Gate Evidence` section is for the `decision` profile.

Do not change `brief-prep`-based artifact formulas to `decision`; those workflows actually run the full review path and should keep their artifact profile.

- [ ] **Step 3: Patch producer-repair template**

Require `brief_kind: producer_repair`, `gate_profile: producer_repair`, `feedback_sink: brief_quality_failure`, and producer-repair Gate Evidence so repair briefs use their own profile and self-exclude from producer-failure rollups.

- [ ] **Step 4: Verify**

Run:

```bash
bash tests/producer-decision-gate-profiles/smoke_test.sh
```

Expected: `mc-uvg` class is covered source-side. Direct decision producer briefs no longer inherit `standard`, so they no longer deterministically fail G4 merely because no critical review was dispatched.

### Task 4: Make Rejected Brief Feedback Durable

**Files:**
- Create: `assets/scripts/brief-quality-failure-record.py`
- Create: `assets/scripts/checks/brief-quality-failure-record-backfill.sh`
- Modify: `formulas/brief-producer-failure-record.toml`
- Create: `orders/brief-producer-failure-record-on-rejected-pile.toml`
- Modify: `orders/brief-producer-failure-rollup-on-record.toml`
- Create: `orders/brief-producer-failure-rollup-on-pile.toml`
- Modify: `tests/brief-quality-failure/smoke_test.sh`
- Create: `tests/brief-quality-failure-record-backfill/smoke_test.sh`

**Interfaces:**
- Consumes: rejected brief directories at `.beads/briefs/.pile/.rejected/<slug>/` containing `brief.md` and either `rejection.md` or `rejection-record.md`.
- Produces: `.brief-quality-failure-pile/<slug>.toml` for all non-repair rejects and compatibility `.producer-failure-pile/<slug>.toml` for every non-repair reject so all lanes feed the repair rollup.

- [ ] **Step 1: Add failing fixture**

Create a temp brief root with producer-origin and decision/lane rejected briefs and no record files. The test expects the backfill script to create both the shared quality record and the compatibility producer-failure record for each non-repair reject.

- [ ] **Step 2: Implement deterministic recorder**

Implement a Python standard-library script that parses simple frontmatter, extracts the first failed gate from the rejection record, writes TOML cache files idempotently, skips `brief-producer-repair.v1`, and never requires `gc`, `bd`, or network access for cache creation.

- [ ] **Step 3: Wire the recorder into formula checks**

Add a check to `brief-producer-failure-record.toml` so even if the LLM step does nothing, the deterministic check writes missing records.

- [ ] **Step 4: Add durable-state orders**

Add a city-scoped condition order that fires when a rejected dir lacks its quality/producer record. Add a rollup condition order that fires when producer-failure records are newer than `open.jsonl`. Change the existing rollup event order to the event name the record formula emits: `brief.quality_failure_recorded`.

- [ ] **Step 5: Verify**

Run:

```bash
bash tests/brief-quality-failure/smoke_test.sh
bash tests/brief-quality-failure-record-backfill/smoke_test.sh
```

Expected: a genuine rejected-dir fixture creates record files without `gc event emit`.

### Task 5: Repair Producer-Repair Launch Instructions

**Files:**
- Modify: `formulas/brief-producer-failure-rollup.toml`
- Modify: `tests/producer-failure-rollup-routing/smoke_test.sh`
- Modify: `tests/producer-repair-e2e-red/red_test.sh`

**Interfaces:**
- Consumes: `.producer-failure-pile/*.toml` and threshold groups in `.producer-failure-rollups/open.jsonl`.
- Produces: clear instructions to create or reuse one `type=decision` repair-review bead in the `gascity-packs` rig before `gc sling`.

- [ ] **Step 1: Pin the missing behavior**

The current formula references `$repair_bead` without defining it. Add a test assertion for `bd -C "$repair_rig_dir" search` / `bd -C "$repair_rig_dir" create` before the assignee guard.

- [ ] **Step 2: Patch the formula**

Define `repair_bead` by searching the target rig for an existing repair-review bead with the fingerprint. If none exists, create one with `bd -C "$repair_rig_dir" create --type=decision`, include the batch path and producer fingerprint in its description, then run the existing assignee guard and sling.

- [ ] **Step 3: Convert the RED test into a local E2E regression**

Keep the historical context in comments, but make the test fixture prove the source-level repaired path: backfill produces producer records, rollup routing has a defined repair bead, and producer-repair self-exclusion remains enforced.

- [ ] **Step 4: Verify**

Run:

```bash
bash tests/producer-failure-rollup-routing/smoke_test.sh
bash tests/producer-repair-e2e-red/red_test.sh
```

Expected: both pass locally. Live proof 4 remains a runtime acceptance check: the next real gate rejection should create `.producer-failure-pile/<slug>.toml` without a synthetic event.

BART review note, 2026-08-15 23:54: the producer-repair bead-creation assertion is structural source coverage, not a live thresholded `rollup -> create bead -> sling` E2E. Do not describe it as full live E2E until a live rig acceptance run proves the thresholded path executes. The remaining runtime tracker is `gt-hpho6h`.

### Task 5b: Runtime Proof-4 Canary After Landing

**Files:**
- Live runtime state only: `<city-root>/.beads/briefs/.pile/`, `.pile/.rejected/`, `.producer-failure-pile/`.
- No source files beyond Tasks 1-5.

**Interfaces:**
- Consumes: live `brief-shuffle` and condition-triggered producer-failure orders after the source patch is landed/deployed.
- Produces: durable runtime evidence that a genuine gate rejection creates `.producer-failure-pile/<slug>.toml` without a synthetic event or manual backfill.

- [ ] **Step 1: Create a dedicated canary brief**

After landing, deposit one clearly labeled test-only brief into the live pile. It must:

- use a unique slug, e.g. `proof-4-runtime-canary-<timestamp>`,
- be producer-origin with `producer_contract: brief-producer.v1`,
- use `source_formula: proof-4-runtime-canary`,
- use `source_step: file-brief`,
- use `brief_kind: standard` and `gate_profile: standard`,
- be obviously marked as a runtime canary artifact in the title/body/frontmatter,
- include an explicit `G4 Critical-review: FAIL` line in `## Gate Evidence`,
- fail `G4 Critical-review` predictably while still carrying enough provenance for the feedback recorder.

Do not use or mutate one of the real queued briefs. Do not trigger the canary by
omitting a failure line; failures must be recorded explicitly.

- [ ] **Step 2: Let the live pipeline reject it**

Allow `brief-shuffle` to claim and reject the canary. Do not run `gc event emit`. Do not run the backfill script by hand as the proof.

- [ ] **Step 3: Verify durable feedback appeared**

Check that `.producer-failure-pile/<canary-slug>.toml` appears on its own and records the canary provenance and failed gate. Also check the shared `.brief-quality-failure-pile/<canary-slug>.toml` if present.

- [ ] **Step 4: Preserve evidence**

Keep the rejected canary directory and producer-failure record as durable evidence, clearly marked as runtime canary artifacts. If they later become operational noise, archive them through the normal brief archive path rather than manual deletion.

- [ ] **Step 5: Update tracker**

Append the outcome to `gt-hpho6h`. If the canary fails to produce the record, keep `gt-hpho6h` open with the exact missing artifact and runtime timestamps.

### Task 6: Full Verification And Coordination

**Files:**
- No new source files beyond Tasks 1-5.

**Interfaces:**
- Consumes: all local tests discovered by `scripts/run-local-tests.sh`.
- Produces: current evidence for BART, QUIMBY, and the human adjudicator.

- [ ] **Step 1: Run targeted tests**

Run all tests named in Tasks 1-5, plus:

```bash
bash tests/producer-decision-gate-profiles/smoke_test.sh
```

- [ ] **Step 2: Run full local suite**

Run:

```bash
bash scripts/run-local-tests.sh
```

Expected: all local shell and pytest tests pass. If a live-runtime test cannot be proven locally, report the exact remaining runtime proof instead of marking it green.

- [ ] **Step 3: Documentation pass**

Run or explicitly record the `improve-documentation` pass for these user-facing workflow changes. The pass should either update the relevant README/testing surfaces or record a precise N/A reason for any surface left unchanged.

- [ ] **Step 4: Coordinate**

Message QUIMBY that proof 4 is being handled by a durable rejected-dir backstop and ask him not to double-file unless he wants a tracking bead. Message BART that the source-side fixes are in `<repos-root>/mathcity` and request review after tests.

- [ ] **Step 5: Split Landing**

BART cleared the source review but flagged bundling. When landing, split into reviewable commits or PRs:

1. runner #36 hardening and test-runner coverage,
2. presentation/decision-gate work (`present-briefs`, `decisions-to-briefs`, `brief-gate-keep` enum),
3. proof-4 durable feedback and producer-repair rollup work.

Do not push any split without Taylor's explicit git authorization.

## Self-Review

- Spec coverage: covers BART's runner review, Clark's present-briefs correction, QUIMBY's Gate Evidence positive control, QUIMBY's `mc-uvg` two-arm profile contrast, proof 4 durable-state repair, event-name mismatch, and the undefined `repair_bead` path behind the producer-repair E2E failure.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: `brief_quality_failure.v1`, `brief-producer-failure.v1`, `brief-producer-repair.v1`, `manifest_status`, `gate_profile`, and `classifier_state` match the existing source vocabulary.
