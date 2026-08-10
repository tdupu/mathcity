---
name: gc-recycle-bead
description: >-
  Handle graceful lifecycle transitions for research beads — beads that contain
  mathematical decisions, session notes, or research context rather than purely
  actionable task steps. Supports three transitions: ABSORB (merge unique
  content into a canonical bead, close the source with absorbed_by metadata),
  ARCHIVE (mark as a permanent non-actionable research record with
  archived-research label, defer to prevent dispatch), and MATERIALIZE (write
  key content from the bead to a versioned file for long-term access outside the
  bead store). Trigger phrases: "recycle this bead", "absorb this into X",
  "archive this as research", "materialize this bead to a file",
  "this bead has unique items — absorb before closing", "superseded but has
  unique content", "research journal bead", "lifecycle transition".
---

# gc-recycle-bead

Beads accumulate three kinds of content that don't fit the normal close/done
lifecycle: **unique findings** that belong in a canonical bead, **research
context** that is historically valuable but not a task, and **detailed notes**
that are too long to live in a bead but must survive session death.

This skill provides a consistent protocol for each transition so nothing is
silently dropped when a bead is superseded or retired.

## Decision tree

1. **Does this bead contain unique items that belong in another bead?**
   → **ABSORB** — merge them into the target, close with `absorbed_by` metadata.

2. **Is this bead historical context / a research journal with no open task
   remaining?**
   → **ARCHIVE** — add `archived-research` label, defer to prevent future
   dispatch, leave content readable.

3. **Does this bead contain key findings that should be accessible outside the
   bead store (as a file in a repo)?**
   → **MATERIALIZE** — write to a versioned file, set `materialized_to`
   metadata, optionally archive after.

Multiple modes can apply to the same bead — e.g., ABSORB unique items first,
then ARCHIVE the remainder.

---

## ABSORB

*Transfer unique content from a source bead to an absorbing (canonical) bead,
then close the source.*

### When to use

- A bead is superseded but contains 1+ items (findings, decisions, references)
  not present in the canonical bead.
- A duplicate bead was created; unique items must not be lost.
- A session produced research in the wrong bead; results need consolidation.

### Steps

**Step 1 — Identify unique items.** Read source and target. List items in the
source that do not appear in the target.

```bash
SOURCE=<source-bead-id>
TARGET=<absorbing-bead-id>
bd show "$SOURCE"   # note unique items
bd show "$TARGET"   # confirm they are absent
```

**Step 2 — Append unique items to the absorbing bead.** Use
`--append-notes` (non-destructive) so the target's existing notes are preserved.

```bash
bd update "$TARGET" --append-notes "$(cat <<'EOF'
## Absorbed from $SOURCE — $(date +%Y-%m-%d)

<unique items, verbatim or lightly structured>
EOF
)"
```

If the items belong in the description body rather than notes, use
`--description` with the merged content (requires reading the current
description first to avoid overwriting).

**Step 3 — Record the absorption on the source bead.**

```bash
bd update "$SOURCE" \
  --set-metadata "absorbed_by=$TARGET" \
  --add-label absorbed
```

**Step 4 — Close the source bead.**

```bash
bd close "$SOURCE" --reason "Absorbed into $TARGET — unique items transferred"
```

### Verify

```bash
bd show "$TARGET" | grep -A 20 "Absorbed from"   # items are present
bd show "$SOURCE" | grep absorbed_by              # metadata set
```

---

## ARCHIVE

*Mark a bead as a permanent non-actionable research record. Keeps content
readable and searchable, but removes it from `bd ready` and prevents dispatch.*

### When to use

- A research journal bead captures session history or mathematical context but
  has no remaining open tasks.
- A bead was created to hold notes or findings for reference; it should never
  appear as work.
- A decision bead or brief record should persist indefinitely without being
  re-dispatched.

### Steps

**Step 1 — Add the `archived-research` label.**

```bash
BEAD=<bead-id>
bd update "$BEAD" --add-label archived-research
```

**Step 2 — Set lifecycle metadata.**

```bash
bd update "$BEAD" \
  --set-metadata "gc.lifecycle=archived" \
  --set-metadata "gc.archive_date=$(date -u +%Y-%m-%d)" \
  --set-metadata "gc.archive_reason=<one-line reason>"
```

**Step 3 — Defer to prevent future dispatch.**

Use a far-future date so the bead never surfaces in `bd ready` or dispatch
cycles while remaining open and readable.

```bash
bd update "$BEAD" --defer 2099-01-01
```

**Step 4 — Add an archive note to the description (optional but recommended).**

Prepend a short header so the archive status is visible to anyone reading the
bead without querying metadata.

```bash
bd update "$BEAD" --append-notes "$(cat <<'EOF'
---
ARCHIVED $(date -u +%Y-%m-%d): non-actionable research record.
Reason: <same as gc.archive_reason above>
This bead is intentionally deferred to 2099; it will not appear in bd ready.
---
EOF
)"
```

### Verify

```bash
bd show "$BEAD" | grep -E "archived-research|deferred|gc.lifecycle"
bd ready | grep "$BEAD" && echo "STILL IN READY — check defer" || echo "OK: not in ready"
```

---

## MATERIALIZE

*Write key content from a bead to a versioned file so it is accessible outside
the bead store (e.g., as a research note in the project repo).*

### When to use

- A bead contains detailed mathematical findings (proofs, data, session
  journals) that are too long to maintain only in the bead.
- The content should be diffable in git and accessible without `bd`.
- A research journal entry needs to graduate into a persistent notes file.

### Steps

**Step 1 — Choose a target file path.**

```bash
BEAD=<bead-id>
REPO=<repos-root>/<project>           # e.g. <repos-root>/hecke
TARGET_FILE="$REPO/research/$(date +%Y-%m-%d)-<slug>.md"
# or: notes/, docs/research/, session-logs/, etc.
```

**Step 2 — Write the file.** Construct the file from the bead's content.
Include the bead ID as a header so the file's origin is traceable.

```bash
cat > "$TARGET_FILE" <<EOF
# <Title from bead>

> Source bead: $BEAD — materialized $(date -u +%Y-%m-%dT%H:%M:%SZ)

$(bd show "$BEAD" --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('description', ''))
if d.get('notes'):
    print()
    print('## Notes')
    print(d.get('notes', ''))
")
EOF
```

**Step 3 — Commit the file.**

```bash
cd "$REPO"
git add "$TARGET_FILE"
git commit -m "research: materialize bead $BEAD to $(basename $TARGET_FILE)"
```

**Step 4 — Record the materialization on the bead.**

```bash
RELATIVE_PATH="${TARGET_FILE#$REPO/}"   # strip repo root for portability
bd update "$BEAD" \
  --set-metadata "materialized_to=$RELATIVE_PATH" \
  --set-metadata "gc.lifecycle=materialized" \
  --set-metadata "gc.materialize_date=$(date -u +%Y-%m-%d)"
```

**Step 5 (optional) — Archive the bead after materializing.**

If the bead no longer needs to be tracked as open work, follow the ARCHIVE
steps above. The file is the durable record; the bead becomes a pointer.

### Verify

```bash
bd show "$BEAD" | grep materialized_to     # path set
cat "$TARGET_FILE" | head -5              # file exists and starts with header
git -C "$REPO" log --oneline -1           # commit is present
```

---

## Notes on dispatch prevention

The `archived-research` label prevents dispatch **only when the routing formula
explicitly excludes it**. If you are operating a rig whose formula does NOT
filter on labels, the defer-to-2099 step (ARCHIVE Step 3) is the sole
mechanical blocker. Always apply both.

A bead with `archived-research` + `defer 2099-01-01` will:
- Appear in `bd list --status deferred`
- Not appear in `bd ready`
- Not appear in `gc hook --claim` result sets (deferred beads are not routed)
- Remain readable via `bd show <id>`

## Combining transitions

| Situation | Protocol |
|---|---|
| Superseded bead with unique items | ABSORB (transfer items) → ARCHIVE remainder |
| Research journal, all tasks complete | ARCHIVE |
| Bead with long findings, still active | MATERIALIZE (file) → keep bead open |
| Bead with long findings, retiring | MATERIALIZE → ARCHIVE |
| Superseded bead with both unique items AND long findings | ABSORB (merge short items) → MATERIALIZE (write long content to file) → ARCHIVE |
