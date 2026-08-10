# Brief Document Model: Migration from .beads/ to gc artifact_root

**Bead:** gsp-1pv  
**Date:** 2026-07-08  
**Status:** DRAFT  
**Author:** clerk / planning agent

---

## Problem Statement

The mathcity (mathematics) pack stores research briefs under `.beads/briefs/`
with the following layout:

```
.beads/briefs/
  .staging/<slug>/
    brief.md
    evidence.toml
    breadcrumb.toml
  .pile/
    <slug>.md
    .rejected/<slug>/brief.md
  stack/
    <slug>.md
    manifest.jsonl
  archive/<slug>/
  decisions/<slug>/
    decision.toml
  .shuffle.lock
  ALLOW_NO_BRAINER_AUTO_EXECUTE
```

`.beads/` is Beads' operational store. Placing research documents there
creates four concrete problems:

1. **Backup/sync ambiguity**: `bd backup` and `bd dolt push` are designed for
   issue metadata, not document blobs. Briefs are large, mutable, and
   potentially contain pre-decision sensitive analysis.
2. **Privacy semantics**: DoltHub repos holding `bd` data are private per
   standing policy, but the privacy invariant is tied to *issue data*, not
   document content. Mixing these makes the invariant harder to reason about.
3. **Coupling to internals**: `bd` may restructure `.beads/` in future schema
   versions. Documents living there inherit that fragility.
4. **GC model violation**: GC's artifact model says workflow documents are
   typed artifacts with front matter (schema/workflow/producer/status/trace),
   stored at an `artifact_root` and indexed via bead metadata keys. The
   current layout bypasses this entirely.

---

## Chosen Storage Location and Justification

**Chosen: `~/.gc/mathcity/briefs/<slug>/`** (rig-local, user-home, per-rig)

Three options were considered:

| Option | Path | Verdict |
|--------|------|---------|
| A | `~/.gc/mathcity/briefs/<slug>/` | **CHOSEN** |
| B | `math-work/briefs/<slug>/` (project-local) | Rejected |
| C | `artifact_root` inside a named workspace slug in the repo | Rejected |

**Why A wins:**

- GC's well-established pattern for rig-local operational state is
  `~/.gc/<pack-name>/`. This is outside any git-tracked repo, keeping
  work-in-progress briefs (especially pre-decision staging) out of version
  control entirely. The brief pipeline is a *rig artifact*, not a *repo
  artifact* — it tracks what a specific rig is currently reviewing, not a
  permanent project record.
- Privacy: `~/.gc/` is never synced to DoltHub or pushed to GitHub. The
  boundary is clean.
- Backup: the rig operator can independently snapshot `~/.gc/mathcity/`
  (e.g., `rsync` to a private backup) without entangling it with `bd backup`
  semantics.
- Separation of concerns: the *decision record* (the output) belongs in a
  bead's metadata or in a permanent artifact. The *brief document* (the
  working input) is ephemeral operational state that lives and dies on the
  rig.

**Why B (project-local `math-work/`) is rejected:**

`math-work/briefs/` would land inside a git-tracked workspace. Pre-decision
briefs must not be committed (they can contain sensitive analysis), and
`.gitignore` hygiene is a maintenance burden. Also, `math-work/` is not a
packv2 well-known directory.

**Why C (artifact_root inside a named workspace slug in the repo) is rejected:**

This is appropriate for *completed, shareable* artifacts (e.g., a finished
experiment report that should travel with the repository). Active brief
pipeline state is neither finished nor shareable; forcing it into a repo
artifact_root replicates the coupling problem we are solving.

**Concrete root paths:**

```
artifact_root  = ~/.gc/mathcity/briefs
staging        = ~/.gc/mathcity/briefs/.staging/<slug>/
pile           = ~/.gc/mathcity/briefs/.pile/
rejected       = ~/.gc/mathcity/briefs/.pile/.rejected/
stack          = ~/.gc/mathcity/briefs/stack/
archive        = ~/.gc/mathcity/briefs/archive/
decisions      = ~/.gc/mathcity/briefs/decisions/
```

The `paths.toml` `[paths] root` key changes from `.beads/briefs` to
`~/.gc/mathcity/briefs` (expanded at runtime via `$HOME/.gc/mathcity/briefs`
or resolved by the formula engine's HOME expansion).

---

## Brief Front Matter Fields

Every brief file (`brief.md`) gains a YAML front matter block. Required fields:

```yaml
---
schema: mathcity.brief/1
workflow: brief-pipeline
producer: <bead-id or formula-run-id>
status: staging | pile | stack | archive | decided | rejected
trace:
  source: <artifact: bead-id, branch, PR, GH-issue>
  brief_type: standard | test-execution | experiment | no-brainer | decision
  slug: <slug>
  created_at: <ISO 8601>
  updated_at: <ISO 8601>
---
```

Field semantics:

- `schema`: namespaced schema identifier; `mathcity.brief/1` is version 1.
  The formula engine can use this to validate the document shape before
  processing.
- `workflow`: always `brief-pipeline` for pipeline-managed briefs. Enables
  generic tooling to identify these documents.
- `producer`: the formula run or bead that created the brief. Traceability
  for audit.
- `status`: single source of truth for the document's pipeline stage.
  Replaces the directory position as the status signal.
- `trace.*`: provenance block. `source` is the artifact the brief is about;
  `brief_type` drives gate profile selection; `slug` is stable across moves;
  timestamps enable manifest reconstruction.

---

## Mapping Pipeline States to Bead Metadata

Each brief-in-flight is indexed by a bead metadata key on the *source bead*
(the bead the brief is about). This eliminates the need for `manifest.jsonl`
as the primary index — the bead store is the index.

### Bead Metadata Keys

| Key | Value | Set when |
|-----|-------|----------|
| `mathcity.brief.slug` | `<slug>` | Brief enters staging |
| `mathcity.brief.path` | `~/.gc/mathcity/briefs/stack/<slug>.md` | Brief promoted to stack |
| `mathcity.brief.stage` | `staging` / `pile` / `stack` / `archive` / `decided` / `rejected` | Updated at each transition |
| `mathcity.brief.type` | `standard` / `test-execution` / `experiment` / `no-brainer` / `decision` | Set at brief creation |
| `mathcity.brief.gate_profile` | Gate profile name from `gates.toml` | Set at gate-keep |
| `mathcity.brief.decision_at` | ISO 8601 timestamp | Set when decision is recorded |
| `mathcity.brief.decision_outcome` | `approved` / `rejected` / `deferred` | Set when decision is recorded |

The shuffler and archiver write these keys via `bd update <source-bead-id>
--meta mathcity.brief.stage=stack` (or equivalent `bd` metadata API) at each
state transition.

### Replacing manifest.jsonl

`stack/manifest.jsonl` was the shuffler's append-only record of promoted
briefs. In the new model:

- The canonical index is bead metadata (`mathcity.brief.stage=stack` query
  replaces a manifest scan).
- A lightweight `~/.gc/mathcity/briefs/stack/.index.jsonl` can be maintained
  as a local cache for tooling that needs fast listing without `bd` queries,
  but it is *derived* — reconstructible from bead metadata at any time.
- `brief-drain-manifest.sh` is replaced by a `bd list --meta
  mathcity.brief.stage=stack` query piped through the same output formatter.

---

## Shuffle Lock Mechanism in the New Model

The `.shuffle.lock` file was a filesystem mutex preventing concurrent
shuffler runs. In the new model:

**Keep the filesystem lock, move the path:**

```
~/.gc/mathcity/briefs/.shuffle.lock
```

Rationale: the lock is a *rig-local runtime coordination device*. It does not
belong in `.beads/` (issue store), nor in a repo. `~/.gc/mathcity/briefs/`
is the natural home since the lock guards operations on that same directory
tree.

**No change to lock semantics:** the shuffler still acquires the lock before
touching `.pile`, `stack`, or the index; stale-lock detection logic is
unchanged; the lock file contains the same pid/timestamp content.

**ALLOW_NO_BRAINER_AUTO_EXECUTE kill-switch:**

Move to `~/.gc/mathcity/ALLOW_NO_BRAINER_AUTO_EXECUTE`. This is a rig
operator toggle, not a brief-document — it belongs one level above the briefs
tree so it survives a `rm -rf ~/.gc/mathcity/briefs/` cleanup without being
accidentally deleted.

---

## Migration Path from Current Structure

### Prerequisites

- `~/.gc/mathcity/briefs/` does not yet exist (clean slate on most rigs).
- The current `.beads/briefs/` tree may have live content on the human adjudicator's rig.

### Step 1 — Create new root

```bash
mkdir -p ~/.gc/mathcity/briefs/{.staging,.pile/.rejected,stack,archive,decisions}
```

### Step 2 — Migrate existing briefs with front matter injection

For each brief found under `.beads/briefs/`:

1. Determine its current stage from its directory position (staging, pile,
   stack, archive, decisions).
2. Inject front matter if absent (slug from filename or directory name;
   status from directory; created_at from file mtime; brief_type from
   content scan for "Brief type:" line).
3. Copy to the corresponding path under `~/.gc/mathcity/briefs/`.
4. Update the source bead's metadata:
   ```bash
   bd update <source-bead-id> \
     --meta mathcity.brief.slug=<slug> \
     --meta mathcity.brief.stage=<stage> \
     --meta mathcity.brief.path=~/.gc/mathcity/briefs/stack/<slug>.md
   ```
   (Skip `mathcity.brief.path` for non-stack stages.)

A migration script outline:

```bash
#!/usr/bin/env bash
# migrate-briefs.sh — one-shot migration from .beads/briefs to ~/.gc/mathcity/briefs
set -euo pipefail
OLD_ROOT="${BEADS_ROOT:-.beads}/briefs"
NEW_ROOT="$HOME/.gc/mathcity/briefs"
# ... iterate OLD_ROOT subdirs, inject front matter, copy, update beads
```

A full implementation is out of scope for this plan; a bead (child of
gsp-1pv) should be filed to write and run the migration script.

### Step 3 — Update paths.toml

Change `root` and all derived paths in
`mathematics/assets/brief-pipeline/paths.toml`:

```toml
[paths]
root = "~/.gc/mathcity/briefs"
pile = "~/.gc/mathcity/briefs/.pile"
rejected = "~/.gc/mathcity/briefs/.pile/.rejected"
stack = "~/.gc/mathcity/briefs/stack"
archive = "~/.gc/mathcity/briefs/archive"
decisions = "~/.gc/mathcity/briefs/decisions"
manifest = "~/.gc/mathcity/briefs/stack/.index.jsonl"
staging = "~/.gc/mathcity/briefs/.staging"
lock = "~/.gc/mathcity/briefs/.shuffle.lock"
kill_switch = "~/.gc/mathcity/ALLOW_NO_BRAINER_AUTO_EXECUTE"
```

### Step 4 — Update formula default vars

In every formula that has `[vars.artifact_root]`, change the default:

```toml
[vars.artifact_root]
description = "Brief pipeline artifact root."
default = "~/.gc/mathcity/briefs"
```

Affected formulas: `brief-prep.toml`, `brief-shuffle.toml`,
`brief-archive-sweep.toml`, `brief-present-next.toml`,
`brief-decision-dispatch.toml`, `brief-gate-keep.toml`,
`brief-review-patrol.toml`, `brief-watchdog-refill.toml`,
`brief-record-decision.toml`.

### Step 5 — Update orders

All orders referencing `.beads/briefs/.pile` in their `check` trigger
condition must be updated:

```toml
# brief-shuffle-pile.toml — before
check = "find .beads/briefs/.pile -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null | grep -q ."

# after
check = "find $HOME/.gc/mathcity/briefs/.pile -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null | grep -q ."
```

Orders to audit:
- `brief-shuffle-pile.toml`
- `brief-review-patrol.toml`
- `brief-archive-sweep.toml`
- `brief-watchdog-refill.toml`
- `brief-present-next.toml`
- `brief-decision-dispatch.toml`
- `brief-archive-on-request.toml`

### Step 6 — Update check scripts

Scripts under `mathematics/assets/scripts/checks/` that reference
`.beads/briefs` paths need the same substitution. Also remove any hard-coded
`<home>/` prefixes (per standing constraint in Phase 1 plan).

### Step 7 — Verify and cut over

1. Run `gc lint mathematics/` — must pass.
2. Run `pytest tests/` — must pass.
3. Smoke-test: trigger `brief-shuffle-pile` order on a test brief in the new
   location; confirm manifest entry and bead metadata update.
4. Delete `.beads/briefs/` after confirming all live briefs are migrated and
   indexed.

---

## Changes to orders/ Dispatch Scripts

Beyond the path-update mechanical changes (Step 5 above), two semantic
changes are needed in orders:

### 1. Scope correction

`brief-shuffle-pile.toml` has `scope = "rig"` for correct path resolution
relative to each rig root. This was necessary because `.beads/briefs/.pile`
resolved relative to the rig root. With `~/.gc/mathcity/briefs/` (absolute
home-relative path), the scope can switch to `city` — the path resolves
identically regardless of which directory the order runs from. Recommend
changing `scope = "rig"` to `scope = "city"` for all brief-pipeline orders
after the migration.

### 2. Manifest drain → bead metadata query

`brief-drain-manifest.sh` polls `stack/manifest.jsonl` to find briefs
awaiting presentation. Replace the shell script poll with:

```bash
bd list -C <pack-root> \
  --meta-key mathcity.brief.stage \
  --meta-value stack \
  --json | jq '.[].id'
```

This makes `brief-present-next` order's condition a `bd list` check rather
than a `find`/`grep` on a JSONL file, eliminating the script entirely or
reducing it to a thin wrapper.

---

## Open Questions / Child Beads to File

1. **Migration script**: implement and run `migrate-briefs.sh` (child of
   gsp-1pv, priority P2).
2. **bd metadata API for mathcity.brief.***: confirm `bd update --meta` syntax
   supports namespaced keys like `mathcity.brief.stage`; if not, choose an
   alternative encoding (child of gsp-1pv).
3. **HOME expansion in formula vars**: confirm the formula engine expands `~`
   in `[vars.artifact_root].default`; if not, use `${HOME}` or require an
   env-var override (child of gsp-1pv).
4. **Scope city vs rig post-migration**: after cutover, audit all brief-pipeline
   orders for scope correctness (child of gsp-1pv, can be batched with Step 7).
5. **brief-prep skill SKILL.md**: the canonical copy references
   `<city-root>/hecke/.beads/briefs/` — now uses `~/` prefix; further migration to
   artifact_root variable is a follow-up (child of gsp-1pv).
