---
name: check-briefs
description: >-
  Report the current brief stack — how many briefs are ready to adjudicate,
  displayed as a compact table sorted by unlock_count descending. Use when you
  want a quick at-a-glance view of what's waiting for a verdict. Trigger
  phrases: "check briefs", "check-briefs", "what's on the stack",
  "how many briefs are ready", "what briefs are waiting", "stack status",
  "how many briefs are pending adjudication", "brief queue status".
---

# check-briefs

One command, one table, zero side effects. Reports all actionable briefs
(stack-resident, approved, not yet adjudicated) sorted by unlock_count descending.

## Pre-flight (P1.14)

```bash
gc dolt health >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
  echo "Run 'gc dolt status' / 'gc dolt start' and retry."
  echo "(check-briefs reads bead status from the live store to filter already-closed briefs.)"
  exit 1
}
```

## Execution

### 1. Discover stack directory

```bash
STACK_DIR="${BRIEF_QUEUE_PATH:-$HOME/gt/.beads/briefs/stack}"
```

### 2. Collect candidate briefs

Scan all `.md` files in the stack with `status: approved` in frontmatter:

```bash
find "$STACK_DIR" -maxdepth 1 -name "*.md" \
  | xargs grep -l "^status: approved" 2>/dev/null
```

### 3. For each candidate — resolve live bead status

For each file, read frontmatter fields (`artifact`, `unlock_count`,
`deposited_at`, `brief_bead`, `epic`). Then check whether the bead is
already CLOSED in the live store:

```bash
# preferred: check brief_bead if populated; fall back to artifact
TARGET="${brief_bead:-$artifact}"
RIG_DIR=$(rig_for_prefix "$TARGET")
bead_status=$(cd "$RIG_DIR" && bd show "$TARGET" 2>/dev/null | grep -m1 "^Status:" | awk '{print $2}')
```

`rig_for_prefix` mapping:
- `he-*` → `<city-root>/hecke`
- `gsp-*` → `<city-root>/gascity-packs`
- `gt-*` → `<city-root>`
- unknown → `<city-root>` (fallback)

Skip any brief whose bead is CLOSED or DEFERRED.

### 4. Compute age

From `deposited_at:` frontmatter (ISO 8601) to now. Format as `Xd Yh` if ≥ 1 day,
else `Xh` if ≥ 1 hour, else `Xm`. Examples: `2d 3h`, `4h`, `45m`.

### 5. Render output

```
Brief stack — <N> ready · <YYYY-MM-DD HH:MM>

| Rig           | Artifact   | unlock_count | Age    | Epic / linked |
|---------------|------------|-------------|--------|---------------|
| gascity-packs | gsp-xyz    | 4           | 2d 3h  | epic: gsp-abc |
| hecke         | he-p4x5    | 2           | 1d     | —             |
| gt            | gt-q5nah   | 1           | 45m    | —             |

<N> brief(s) ready to adjudicate. Run /present-briefs to start.
```

Columns:
- **Rig** — derived from artifact prefix (`he-*` → `hecke`, `gsp-*` → `gascity-packs`, `gt-*` → `gt`)
- **Artifact** — the `artifact:` frontmatter value
- **unlock_count** — from frontmatter `unlock_count:` (0 if absent)
- **Age** — time since `deposited_at:` in `Xd Yh` / `Xh` / `Xm` format
- **Epic / linked** — `epic: <id>` if `epic:` frontmatter field is present; parent bead ID if the brief has a linked parent; `—` if standalone

Sort: `unlock_count` descending (highest unblocking value first).

If N = 0: `"Brief stack is empty — 0 briefs ready. Run /brief-prep on pending artifacts to populate it."`

## What this skill does NOT do

- ❌ Present any brief (that is `/present-briefs`)
- ❌ Adjudicate any brief (that is `/adjudicate-brief`)
- ❌ Mutate any bead or file
- ❌ Count or report pile (awaiting gate-keep promotion) contents
