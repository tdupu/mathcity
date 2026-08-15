# Unified Brief Pipeline With Typed Gate Profiles

Date: 2026-08-15
Status: design artifact for review
Owner: mathcity brief-system

## Summary

Adopt one user-facing brief pipeline:

```text
brief source
  -> .beads/briefs/.pile
  -> brief-shuffle
  -> .beads/briefs/stack
  -> present-briefs
  -> adjudicate-brief
  -> verdict dispatch / archive / feedback
```

All adjudicable briefs should pass through the same pile, shuffle, stack, and
presentation lifecycle. Different sources still need different checks, so the
system should use typed gate profiles inside `brief-shuffle` rather than
separate presentation lanes.

The target design is **unified pile plus typed gate profiles**:

- `artifact` briefs use the existing standard artifact profile.
- `decision` briefs use a decision-only profile.
- `lost_bead_filter` briefs use provenance, threshold, replay, and false-positive
  gates.
- `producer_repair` briefs use repair-loop safety gates.
- no-brainer classification is an overlay that every profile records.
- feedback is a shared lifecycle feature, not only a producer-failure side lane.

## Problem

The policy and the implementation disagree.

The brief-system policy already says there is one fixed pile and that canonical
brief state lives in beads. The live-facing `present-briefs` skill still treats
briefs as a union of two independent sources:

1. artifact briefs from `.beads/briefs/stack`
2. file-only decision briefs from `.beads/decisions-track`

That split is the reason filters feel disconnected in practice. Artifact briefs
hit the pile, shuffle, gate registry, no-brainer gate, stack, and producer-failure
feedback path. Decision-track briefs are selected directly by a separate
manifest scan. They can record defer state, but they do not naturally pass
through the same shuffle gates, no-brainer classifier, stack index, or rejection
feedback loop.

The lost-bead filter side is closer to the desired model because its rollups
file decision briefs into `.beads/briefs/.pile`. But if those generated briefs
fail quality gates, the existing repair path still records the problem as a
producer failure rather than as a general brief-quality failure.

## Goals

1. `present-briefs` presents all promoted briefs from one stack.
2. Every adjudicable brief starts as an open `type=decision` brief bead.
3. Every brief has source metadata, source links, defer state when applicable,
   a gate profile, no-brainer classifier state, and a feedback sink.
4. Decision-only briefs no longer bypass `.pile -> brief-shuffle -> stack`.
5. Lost-bead and producer-repair briefs keep their specialized evidence, but
   they use the same lifecycle.
6. Bad briefs from any source create durable repair signals.
7. The migration preserves all old decisions-track content and proves by count
   that no ready, deferred, adjudicated, rescinded, or auto-dispatched item was
   lost.
8. Deployment through BART is explicit about whether the live city reads
   `~/repos/mathcity` directly or an installed/built copy.

## Non-Goals

- Do not delete the old `.beads/decisions-track` files during the initial
  migration.
- Do not invent a second presentation UI.
- Do not replace the bead store as canonical state.
- Do not auto-execute irreversible actions.
- Do not make all profiles run all gates. Shared lifecycle does not mean one
  universal gate set.

## Terminology

Use **brief source** or **brief kind** instead of "track" for new code and
docs. A source describes where the brief came from; it does not create a
separate queue.

Recommended `brief_kind` values:

- `artifact`
- `decision`
- `branch_disposition`
- `lost_bead_filter`
- `producer_repair`
- `capability_blocker`
- `policy`
- `hygiene`

Recommended `gate_profile` values:

- `standard`
- `decision`
- `lost_bead_filter`
- `producer_repair`
- `no_brainer`

`no_brainer` remains a classifier outcome/profile overlay, not a user-facing
lane.

## Required Metadata Contract

Every new brief bead and printout should carry enough metadata for shuffle,
presentation, migration, and repair:

```yaml
brief_kind: decision
gate_profile: decision
source_bead: gt-example
source_surface: decisions-to-briefs
legacy_source: decisions-track/42-example-brief.md
classifier_state: known_non_no_brainer
classifier_category: null
classifier_confidence: 1.0
feedback_sink: brief_quality_failure
defer_until: null
unlock_count: 0
```

The bead store is canonical. Markdown frontmatter and manifest/index rows are
cache/rendering state derived from bead metadata where possible.

## Gate Profiles

### `standard`

Current artifact-producing brief profile. Keep the existing G1-G16 plus G5b
behavior.

Used by:

- `brief-prep`
- `create-brief` for artifact work
- branch-disposition briefs that evaluate real branches or runnable artifacts

### `decision`

Decision-only briefs do not have a runnable artifact, so they should not be
forced through fake test evidence. They still need shape and lifecycle checks.

Proposed required checks:

- source link exists or a legacy source pointer exists
- decision is the first body content
- recommended verdict exists
- alternatives are explicit when more than yes/no is possible
- action block exists and is reversible-only unless explicitly marked external
- defer handling is valid when present
- no-brainer classifier state is recorded
- no-resurface state is respected
- stale status/frontmatter/manifest disagreements fail closed
- feedback sink is declared

### `lost_bead_filter`

Used for downstream filter-rule proposals and upstream repair proposals emitted
by the lost-bead filter rollups.

Proposed required checks:

- contributing classification event beads are linked
- affected source beads are linked where known
- fingerprint and root-cause class are present
- threshold count and distinct bead count are present
- replay command is present
- false-positive risk is present
- non-goal is explicit
- unknown provenance is labeled as `UNKNOWN_PROVENANCE`, not guessed
- no-brainer classifier state is recorded
- feedback sink is declared

### `producer_repair`

Used for briefs proposing repairs to brief producers, gates, routes, or terminal
steps.

Proposed required checks:

- failed gate and failure fingerprint are present
- source formula/source step/routing path are present when known
- repair briefs self-exclude from recursive producer-failure rollups
- proposed repair target is explicit
- replay/retest command is present
- no-brainer classifier state is recorded
- feedback sink is declared

## No-Brainer Contract

Every profile records a no-brainer result before the brief can be promoted.
The classifier may return:

- `known_no_brainer`
- `known_non_no_brainer`
- `candidate`
- `capability_blocker`
- `safety_blocked`

For decision-only briefs, the initial likely categories are:

- ratify existing defer/held state
- close done with cited commit or existing closure proof
- execution confirmation with cryptographic or command-output proof
- pure metadata correction with no live side effect

If a no-brainer reaches the human and the human says it was obvious, the
verdict path records a durable `no_brainer_leak` event. That event feeds the
classifier/gate registry improvement loop.

## Feedback Contract

Replace the mental model "producer failures only" with a broader
`brief_quality_failure.v1` event. Keep compatibility with the existing
producer-failure cache and rollups by mapping producer-origin failures into the
new event shape.

Minimum event payload:

```toml
schema = "brief_quality_failure.v1"
brief_id = "<slug-or-brief-bead>"
brief_kind = "<brief kind>"
gate_profile = "<profile>"
source_bead = "<source bead or unknown>"
source_surface = "<producer formula/skill/migration source>"
failed_gate = "<gate id or profile-check name>"
failure_summary = "<one sentence>"
failure_fingerprint = "<dedupe fingerprint>"
observed_at = "<RFC3339 UTC>"
status = "untriaged"
legacy_event = "<producer_failure id when applicable>"
```

Feedback behavior:

- any shuffle rejection emits `brief_quality_failure`
- producer-origin failures also populate `.producer-failure-pile` for existing
  rollups
- decision-origin failures file a decision-brief repair item
- lost-bead-filter-origin failures file filter/provenance repair items
- no-brainer leaks emit `no_brainer_leak` and link back to classifier state

## Migration Plan

### Phase 0: Preflight Inventory

Run a read-only inventory before changing behavior.

Inventory sources:

- `.beads/decisions-track/manifest.jsonl`
- `.beads/decisions-track/*-brief.md`
- `.beads/briefs/.pile/*.md`
- `.beads/briefs/.pile/.rejected/**`
- `.beads/briefs/.pile/.no-brainer/**`
- `.beads/briefs/stack/*.md`
- `.beads/briefs/stack/.index.jsonl`
- `.beads/briefs/archive/**`

Classify every decisions-track row by status:

- `ready`
- `ready` with future `defer_until`
- `adjudicated`
- `rescinded`
- `auto-dispatched`
- malformed JSON
- missing file
- file with no manifest row

The inventory output should be JSONL, for example:

```text
.beads/briefs/migrations/2026-08-15-decisions-track-inventory.jsonl
```

Each row should include:

- legacy manifest number
- legacy slug
- legacy file path
- manifest status
- file frontmatter status
- defer state
- unlock count
- whether a matching decision bead exists
- migration action

### Phase 1: Copy-First Migration

Do not move or delete decisions-track files in the first migration.

For each live, unadjudicated decisions-track item:

1. Create or locate the canonical `type=decision` brief bead.
2. Link it to a source bead when one is known.
3. If no source bead exists, record `legacy_source` and mark the source-link
   exception explicitly for migration audit.
4. Write a normalized markdown printout into `.beads/briefs/.pile/`.
5. Add metadata:
   - `brief_kind=decision`
   - `gate_profile=decision`
   - `legacy_source=<decisions-track path>`
   - `migration_batch=<batch id>`
6. Preserve `defer_until`; deferred briefs are represented canonically on the
   bead and are not promoted until ripe.
7. Record one migration mapping row.

For terminal decisions-track items:

- do not re-enter them into pile or stack
- preserve their legacy files
- record them in the migration mapping as terminal/preserved
- ensure any canonical decision bead carries terminal verdict state if it
  already exists

### Phase 2: Dual-Read Safety Window

During the transition, `present-briefs` should prefer the unified stack and
use decisions-track only as a legacy safety net when explicitly enabled or when
the migration marker is absent.

Recommended behavior:

- default queue source: `.beads/briefs/stack`
- legacy fallback: decisions-track scan only when `--include-legacy-decisions`
  is passed or when no migration marker exists
- duplicate guard: if a decisions-track item has a `legacy_source` mapping to
  a pile/stack brief, never present the legacy copy

### Phase 3: Cutover

After migration counts match and BART has run live validation:

1. Disable automatic decisions-track presentation.
2. Keep old decisions-track files as preserved legacy records.
3. Update docs to describe decisions-track as a legacy intake/migration source,
   not an active presentation lane.
4. Make `check-brief-policy` flag any new presentable decisions-track file as
   a policy violation unless it is explicitly legacy-marked.

### Phase 4: Cleanup

Cleanup is intentionally delayed.

Only after several successful live presentation/adjudication cycles:

- archive migrated decisions-track files or leave them read-only
- remove fallback presentation scan
- require all new decision-only briefs to use `.beads/briefs/.pile`

No cleanup phase should delete legacy files without a separate human-approved
brief.

## Deployment Plan For BART

### Source Of Truth

Implement in `~/repos/mathcity`, not `~/gt/mathcity`, unless BART proves the
live runtime is resolving a different checkout. The current assumption is that
live Gas City runs from `~/repos/mathcity`, but deployment must verify that
assumption mechanically.

### Does `git pull` Suffice?

Do not assume. Use this rule:

- If the live `gc` runtime resolves skills, formulas, assets, and tests
  directly from `~/repos/mathcity`, then `git pull --ff-only` is sufficient.
- If the live runtime resolves an installed copy under `~/gt`, `~/.gc/cache`,
  or another materialized pack location, then BART must run the existing pack
  import/build/install step after pulling.

BART should verify with a content marker:

1. Pull or check out the expected commit in `~/repos/mathcity`.
2. Inspect the live-resolved `present-briefs`, `decisions-to-briefs`,
   `gates.toml`, and `check-brief-policy` paths.
3. Confirm those live-resolved files contain the new unified-pile wording or
   match the source commit hash/content.

The deployment is not complete until the live-resolved files match the source
repo revision being tested.

### Branch And PR Sequence

Use a separate branch in `~/repos/mathcity`.

Recommended branch name:

```text
feat/unified-brief-pipeline-gate-profiles
```

Recommended flow:

1. Create branch from current `main`.
2. Implement source changes and migration tooling.
3. Run pre-merge tests locally in `~/repos/mathcity`.
4. Open PR.
5. Have BART review/merge.
6. BART pulls or deploys the merged commit into the live runtime.
7. Run post-deploy live tests.
8. Only then run the live migration.

Do not develop this in `~/gt/mathcity` unless that directory is confirmed to
be the active source checkout. `~/gt` should not become the hidden source of
truth for repo-specific changes.

## Testing Plan

### Pre-Merge Tests

These can run before BART merges because they are source-local and should not
mutate live city state:

```bash
bash tests/lost-bead-filter/smoke_test.sh
bash skills/catch-no-brainer/fixtures/run.sh
bash tests/brief-no-brainer-gate/test_brief_check_no_brainer.sh
bash tests/present-briefs-defer-filter/test_defer_filter.sh
bash tests/lockless-brief-shuffle/smoke_test.sh
bash tests/producer-failure-rollup-routing/smoke_test.sh
python3 -m pytest tests/stuck-bead-watch tests/tail-end-detector
```

New pre-merge tests to add:

- decision-profile gate test: a decision-only brief can pass the decision
  profile without fake artifact gates
- decision-profile no-brainer test: classifier state is required on a
  decision-profile brief
- present-briefs unified-source test: queue discovery uses stack as the
  primary source and does not present decisions-track entries that have mapped
  unified-pile replacements
- migration dry-run fixture: all legacy statuses are counted and mapped
- feedback event fixture: a rejected `decision` or `lost_bead_filter` brief
  emits `brief_quality_failure.v1`

### Pre-Deploy Checks

After merge but before touching live data:

- verify BART has the merged commit in `~/repos/mathcity`
- verify live-resolved files match that commit or run the required
  build/import step
- run the pre-merge test set again in the exact runtime path BART will use
- run migration inventory in read-only mode against live `.beads`
- compare counts:
  - manifest rows
  - files on disk
  - ready rows
  - deferred rows
  - terminal rows
  - malformed/missing rows

### Post-Deploy Live Tests

Run after BART deploys the merged behavior, before bulk migration:

1. Create a synthetic decision-only brief in a test fixture or temporary rig
   area.
2. Confirm it enters `.beads/briefs/.pile`.
3. Confirm `brief-shuffle` applies `gate_profile=decision`.
4. Confirm it promotes to `.beads/briefs/stack`.
5. Confirm `present-briefs` sees it from the stack.
6. Confirm defer does not resurface before `defer_until`.
7. Confirm a forced bad decision-profile brief rejects and records
   `brief_quality_failure`.
8. Run a lost-bead filter fixture through the same lifecycle.

After the migration:

- rerun inventory and confirm every legacy item is either migrated,
  terminal-preserved, or explicitly malformed/preserved
- run `check-brief-policy`
- run `check-city-policy`
- run `present-briefs` queue discovery and confirm all ripe migrated briefs
  appear through stack, not direct decisions-track scan

## Documentation Plan

Update these docs and skills together:

- `subdomains/brief-system/POLICY.md`
  - strengthen one-pile rule
  - define source/profile contract
  - require no-brainer classification for all profiles
  - require feedback sink for all rejects
- `subdomains/dev/POLICY-city.md`
  - add city-facing invariant that `present-briefs` is the single doorway
  - define hygienic issue for substrate/lifecycle blockers
- `subdomains/brief-system/README.md`
  - update walkthrough from two-source presentation to unified pile/stack
  - describe decisions-track as legacy/migration input
- `skills/present-briefs/SKILL.md`
  - remove normal Method 3 behavior
  - document legacy fallback only
- `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`
  - file decision-only briefs into `.beads/briefs/.pile`
  - write canonical decision bead metadata
- `skills/adjudicate-brief/SKILL.md`
  - keep decisions-track sync only as legacy compatibility
- `subdomains/brief-system/skills/check-brief-policy/SKILL.md`
  - audit for side-presentation lanes
  - audit required profile/no-brainer/feedback metadata
- `README-clerk.md` and `skills/prime-clerk/SKILL.md`
  - update clerk mental model to one stack
- `docs/testing-guide.md`
  - add pre-merge, pre-deploy, and post-deploy test commands

## Rollback Plan

Rollback must preserve both old and new records.

If live deployment fails before migration:

- revert the source branch or deployment
- keep decisions-track untouched
- continue using old presentation behavior

If live deployment fails during migration:

- stop migration immediately
- keep all generated `.beads/briefs/.pile` files
- keep decisions-track originals
- use the migration mapping JSONL to identify generated files
- disable unified-only presentation and re-enable legacy fallback
- file a hygienic issue with the failure, counts, and failed command

If live deployment fails after cutover:

- restore legacy fallback in `present-briefs`
- do not delete migrated brief beads
- prevent duplicates by honoring `legacy_source` mappings
- file a repair brief before any destructive cleanup

## Implementation Phases

1. Write migration inventory tool and fixture tests.
2. Add typed gate profiles and profile checks.
3. Update `decisions-to-briefs` to file into `.beads/briefs/.pile`.
4. Update `present-briefs` queue discovery to use stack as primary and
   decisions-track as legacy fallback only.
5. Add `brief_quality_failure.v1` recording while preserving existing
   producer-failure rollup compatibility.
6. Update policy and docs.
7. Run pre-merge tests.
8. Open PR.
9. BART merges and verifies live-resolved source path.
10. Run pre-deploy checks.
11. Run live canary tests.
12. Run copy-first migration.
13. Run post-migration policy checks.
14. Remove legacy fallback in a later, separate change after successful live
    operation.

## Acceptance Criteria

- `present-briefs` presents every ripe promoted brief from one stack.
- New decision-only briefs do not live as file-only active decisions-track
  entries.
- All new briefs carry `brief_kind`, `gate_profile`, no-brainer classifier
  state, and feedback sink metadata.
- Bad briefs from every source can generate a durable feedback event.
- No legacy decisions-track file is deleted by the first migration.
- Migration reports prove counts before and after.
- BART deployment verifies whether pull-only is sufficient or build/import is
  required.
- Pre-merge, pre-deploy, and post-deploy tests are documented and runnable.
- Updated docs describe the same lifecycle as the code.

