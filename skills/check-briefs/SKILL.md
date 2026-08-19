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
# `gc dolt health` is THREE-valued: 0 healthy, 2 reachable-but-quarantined
# (non-fatal), 1/other unreachable. See template-fragments/dolt-preflight.md.
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;
  2) ;;   # reachable; auto-GC blocked by a standing compaction quarantine.
          # NON-FATAL and NOT this skill's business: bd resolves beads normally.
          # Proceed SILENTLY — the reporting skills surface it (Variant B).
  *) echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
     echo "Run 'gc dolt status' / 'gc dolt start' and retry."
     echo "(check-briefs reads bead status from the live store to filter already-closed briefs.)"
     exit 1 ;;
esac
```

## Execution

### 1. Discover stack directory and the mctl entry point

```bash
CITY_ROOT="${CITY_ROOT:-$HOME/gt}"
STACK_DIR="${BRIEF_QUEUE_PATH:-$CITY_ROOT/.beads/briefs/stack}"

# `bin/mctl` is the ONLY supported entry point for the MathCity control CLI.
# Never invoke assets/scripts/mctl.py directly — the shim owns repo-root
# resolution, and mctl_core/context.py owns city/rig discovery.
PACK_ROOT="${MATHCITY_PACK_ROOT:-$(
  sed -n '/^\[defaults.rig.imports.mathcity\]/,/^\[/p' "$CITY_ROOT/city.toml" \
    | sed -n 's/^source *= *"\(.*\)"/\1/p' | head -1
)}"
MCTL="$PACK_ROOT/bin/mctl"
[ -x "$MCTL" ] || { echo "mctl entry point not found at $MCTL"; exit 1; }
```

### 2. Collect candidate briefs

Scan all `.md` files in the stack with `status: approved` in frontmatter:

```bash
find "$STACK_DIR" -maxdepth 1 -name "*.md" \
  | xargs grep -l "^status: approved" 2>/dev/null
```

### 3. Resolve live bead status via `bin/mctl`

For each file, read frontmatter fields (`artifact`, `unlock_count`,
`deposited_at`, `brief_bead`, `epic`); the target bead is
`${brief_bead:-$artifact}`.

Canonical brief state (adjudicated / deferred / pending) is `mctl`'s job, not
this skill's. Call it **once per distinct rig** in the candidate set — this
replaces the old per-brief `bd show` loop (N `bd` invocations become one
`bd list` per rig):

```bash
rig_for_prefix() {   # bead prefix -> rig NAME registered in city.toml
  case "$1" in
    he-*)  echo hecke ;;
    gsp-*) echo gascity-packs ;;
    gs-*)  echo gascity ;;
    as-*)  echo agent_skills ;;
    mc-*)  echo mathcity ;;
    tgi-*) echo tdupu_github_io ;;
    lm-*)  echo lmfdb ;;
    ho-*)  echo homog ;;
    ja-*)  echo jacobi ;;
    dv-*)  echo differential_valuations ;;
    mca-*) echo magma_clifford_algebras ;;
    mda-*) echo magma_diff_alg ;;
    *)     echo "" ;;   # unmapped — see the gt-* fallback below
  esac
}

# brief_id -> decision_state, for every decision bead in one rig
"$MCTL" briefs list --json --city "$CITY_ROOT" --rig "$RIG" \
  | python3 -c 'import json,sys
for b in json.load(sys.stdin)["briefs"]:
    print(b["brief_id"], b["decision_state"])'
```

Then, per candidate:

- **Skip** it if mctl reports `decision_state` of `adjudicated`, `deferred`, or
  `malformed` (a closed bead with no recorded verdict). Together these are the
  old "CLOSED or DEFERRED" filter.
- **Keep** it if mctl reports `pending`, or if mctl does not know the id at all.
  Unknown is common and benign: `mctl briefs list` enumerates **decision beads
  only**, while `TARGET` is usually the `artifact:` *work* bead (most stack
  files carry no `brief_bead:`). Keeping unknown ids matches the old behavior,
  where an unresolvable probe left the brief visible rather than dropping it.

**`gt-*` fallback (mctl gap, not a choice).** `gt-*` beads live in the
city-root HQ store, which is **not a registered rig** in `city.toml`, so
`mctl --rig` cannot address it (`MCTL_CONTEXT_UNKNOWN_RIG`). For `gt-*` and any
other unmapped prefix, keep the direct probe:

```bash
bead_status=$(cd "$CITY_ROOT" && bd show "$TARGET" 2>/dev/null \
  | grep -m1 "^Status:" | awk '{print $2}')
```

> **Known-dead probe (verified 2026-08-18, bd 1.1.0).** `bd show` no longer
> emits a `^Status:` line — status is rendered inline in the header
> (`○ gsp-nq3ut1 · … [● P2 · OPEN]`). This grep has therefore been returning
> empty for every brief, making the whole pre-mctl step-3 filter a silent
> no-op. Routing decision beads through `mctl` fixes them; this fallback branch
> stays broken until the parse is repaired. Do not "fix" it by guessing the
> format — confirm against the installed `bd` first.

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

## What mctl does NOT yet serve

Steps 2, 4, and 5 stay hand-rolled because `mctl` has no command that produces
their data. Do **not** invent an mctl subcommand to close these:

- **`unlock_count`, `deposited_at`, `epic`** — brief-file frontmatter. `mctl
  briefs list` exposes only `brief_id` / `title` / `status` / `decision_state` /
  `labels` / `created_at` / `updated_at`; the ranking key this skill sorts on is
  not modelled anywhere in `mctl_core`.
- **`status: approved` frontmatter** — the brief-quality gate flag. `mctl`
  models the adjudication verdict, not the gate flag.
- **Stack residency** — `mctl` reports it (`redundant_artifacts[kind=
  stack_index]`), but `mctl_core/redundant_state.py` resolves the stack
  **rig-root-relative** (`<rig_root>/.beads/briefs/stack`), while the live stack
  is city-root-level and cross-rig (`<city-root>/.beads/briefs/stack`). Every
  artifact therefore reports `missing` in the live deployment, so step 2 keeps
  scanning `$STACK_DIR` directly.

## What this skill does NOT do

- ❌ Present any brief (that is `/present-briefs`)
- ❌ Adjudicate any brief (that is `/adjudicate-brief`)
- ❌ Mutate any bead or file
- ❌ Count or report pile (awaiting gate-keep promotion) contents
