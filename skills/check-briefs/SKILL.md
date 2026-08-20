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

### 3. Resolve live bead status — ONE cross-rig `bin/mctl` call

For each candidate file, read the frontmatter fields the rest of this skill
needs (`artifact`, `unlock_count`, `deposited_at`, `brief_bead`, `epic`); the
target bead is `${brief_bead:-$artifact}`.

Canonical brief state (adjudicated / deferred / pending) is `mctl`'s job, not
this skill's. Read the whole city in **one** call. `--all-rigs` resolves every
registered rig concurrently in `mctl_core/city.py` and tags each row with the
`rig_id` of the store it came from:

```bash
# DO NOT wrap this call in `set -e` or `set -o pipefail`. A nonzero exit here
# is an EXPECTED, non-fatal outcome — it means "a rig could not be read", not
# "the command failed". Under `set -e` every partial city-wide read becomes a
# hard abort and the degraded-rig branch below becomes unreachable.
ALL_RIGS_OUT="$(mktemp)"; ALL_RIGS_ERR="$(mktemp)"; STATE_TSV="$(mktemp)"
"$MCTL" briefs list --all-rigs --json --city "$CITY_ROOT" \
  >"$ALL_RIGS_OUT" 2>"$ALL_RIGS_ERR"
MCTL_RC=$?   # 0 = every rig read; 1 = a rig failed OR the call itself failed
```

Do **not** loop this per rig. The shell loop this replaced was a second
implementation of city-wide assembly — the reason `--all-rigs` was built into
the core — and it was serial: ~3.9s across the live 16 rigs versus ~1.3s here.
The `set -e` warning is inline in the block above deliberately: it belongs
next to the call, because a later editor adding `set -euo pipefail` to the top
of the block is exactly how the partial-read path gets silently removed.

#### The exit-code contract — nonzero means "a rig could not be read"

`MCTL_RC` is **not** a simple pass/fail. `mctl` exits 1 when any rig was
unreadable precisely so a caller cannot mistake a partial answer for a
complete one; it still prints the full payload. Two different failures share
that exit code, and only the payload tells them apart:

| `MCTL_RC` | stdout | Meaning | Action |
|-----------|--------|---------|--------|
| `0` | JSON | Every registered rig answered. | Proceed; complete answer. |
| `1` | valid JSON | **Partial** — ≥1 rig degraded, the rest reported. | Proceed, and name the degraded rigs (below). |
| `1` | not JSON (empty) | The **call** failed before any rig was read (e.g. `MCTL_CONTEXT_CITY_NOT_FOUND`). | Abort; print `$ALL_RIGS_ERR`. |

So branch on the payload, never on the exit code alone:

```bash
python3 - "$ALL_RIGS_OUT" <<'PY' > "$STATE_TSV" || SKILL_ABORT=1
import json, sys
try:
    payload = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)          # no payload -> the call itself failed, not a rig
for entry in payload.get("rigs") or ():
    if not entry.get("ok"):
        print("DEGRADED\t%s\t%s" % (entry.get("rig_id"), entry.get("reason")))
for brief in payload.get("briefs") or ():
    print("STATE\t%s\t%s\t%s"
          % (brief.get("brief_id"), brief.get("decision_state"), brief.get("rig_id")))
PY

if [ "${SKILL_ABORT:-0}" = 1 ]; then
  echo "I'm sorry, I can't do that — the city-wide brief read failed outright."
  cat "$ALL_RIGS_ERR"
  exit 1
fi
```

`STATE` rows give `brief_id -> decision_state` for every decision bead in the
city; `DEGRADED` rows give the rigs that could not be read, each with the
reason `mctl` recorded. Both come out of the same single call.

Then, per candidate, using that target bead:

- **Skip** it if its `decision_state` is `adjudicated`, `deferred`, or
  `malformed` (a closed bead with no recorded verdict). Together these are the
  old "CLOSED or DEFERRED" filter.
- **Keep** it if the state is `pending`, or if the id is absent from the STATE
  rows. Unknown is common and benign: `mctl briefs list` enumerates **decision
  beads only**, while the target is usually the `artifact:` *work* bead (most
  stack files carry no `brief_bead:`). Keeping unknown ids matches the old
  behavior, where an unresolvable probe left the brief visible.

#### What a degraded rig actually costs you

A degraded rig contributes no STATE rows, so every candidate belonging to it
falls into the "unknown → keep" branch above. The consequence is therefore an
**over**-report, not an under-report: a brief already adjudicated in the
degraded rig can still appear in the table. The count never silently shrinks,
because the candidate set comes from the filesystem scan in step 2, not from
the merged `briefs` array.

That is still a wrong answer presented as a right one, which is why the
degraded rigs are named in the output rather than absorbed. Never report the
table without the banner when `DEGRADED` rows exist.

**`gt-*` / HQ IS in the `--all-rigs` roster (changed 2026-08-19).** The
city-root HQ store has no `[[rigs]]` entry in `city.toml`, but
`mctl_core/context.py::city_rig_entries` **synthesises** a reserved `hq` entry
for it whenever `<city-root>/.beads/config.yaml` exists and no configured rig
claims the name (commit `effa679`). So HQ is enumerated, it is read like any
other rig, and **it can appear in `DEGRADED` rows**:

```
DEGRADED  hq  ->  Rig 'hq' did not answer within 25s and is reported as degraded.
```

Treat that as a real degraded rig, not as noise — and **treat it as a signal
about city health, not a property of HQ**. HQ is not inherently slow: measured
directly it answers in ~2.5s, comparable to the other rigs. The one observed
`hq` timeout (2026-08-19) coincided with a supervisor file-descriptor
exhaustion incident that swung `gc status` latency from 3s to 92s
(`tdupu/mathcity#70`). So `DEGRADED hq` most likely means the data plane is
sick, which is worth escalating rather than absorbing.

Do NOT assume an id is missing from the roster just because its rig is absent
from `city.toml`; `city_rig_entries` is the authority, not the config file.

`gt-*` ids are therefore covered by the STATE rows like any other rig when HQ
answers. The direct probe below remains the fallback for when HQ is degraded,
and for any id whose prefix is in no registered rig at all:

```bash
bead_status=$(cd "$CITY_ROOT" && bd show "$TARGET" 2>/dev/null \
  | grep -m1 "^Status:" | awk '{print $2}')
```

> **Known-dead probe (verified 2026-08-18, bd 1.1.0).** `bd show` no longer
> emits a `^Status:` line — status is rendered inline in the header
> (`○ gsp-nq3ut1 · … [● P2 · OPEN]`). This grep has therefore been returning
> empty for every brief, making this fallback a silent no-op. Routing decision
> beads through `mctl` fixes the registered rigs; `gt-*` stays unfiltered until
> the parse is repaired. Do not "fix" it by guessing the format — confirm
> against the installed `bd` first.

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
- **Rig** — the `rig_id` mctl returned for the target bead when it knew it;
  otherwise derived from the artifact prefix (`he-*` → `hecke`, `gsp-*` →
  `gascity-packs`, `gt-*` → `gt`). This map is now **display only** — it no
  longer selects which store to query, so a prefix missing from it costs a
  label, never a skipped rig.
- **Artifact** — the `artifact:` frontmatter value
- **unlock_count** — from frontmatter `unlock_count:` (0 if absent)
- **Age** — time since `deposited_at:` in `Xd Yh` / `Xh` / `Xm` format
- **Epic / linked** — `epic: <id>` if `epic:` frontmatter field is present; parent bead ID if the brief has a linked parent; `—` if standalone

Sort: `unlock_count` descending (highest unblocking value first).

If N = 0: `"Brief stack is empty — 0 briefs ready. Run /brief-prep on pending artifacts to populate it."`

#### Degraded-rig banner (required whenever `DEGRADED` rows exist)

Print it directly under the header, **before** the table, naming every rig:

```
Brief stack — 7 ready · 2026-08-19 14:02

⚠ 2 of 16 rigs could not be read — this list is not authoritative for them:
    hecke          Rig 'hecke' did not answer within 25s and is reported as degraded.
    lmfdb          The explicit MCTL_BEADS_FIXTURE path is not a file.
  Briefs from these rigs are UNFILTERED below: an already-adjudicated brief can
  still appear. Re-run once `mctl briefs list --rig <name>` reads them again.
```

Never collapse this to a count ("2 rigs unavailable"). The operator's next
action is to go and read one specific store, and that is unanswerable without
the name.

## What mctl does NOT yet serve

Steps 2, 4, and 5 stay hand-rolled because `mctl` has no command that produces
their data. Do **not** invent an mctl subcommand to close these:

- **`unlock_count`, `deposited_at`, `epic`** — brief-file frontmatter. `mctl
  briefs list` exposes only `brief_id` / `title` / `status` / `decision_state` /
  `labels` / `created_at` / `updated_at` (plus `rig_id` under `--all-rigs`); the
  ranking key this skill sorts on is not modelled anywhere in `mctl_core`.
- **`status: approved` frontmatter** — the brief-quality gate flag. `mctl`
  models the adjudication verdict, not the gate flag.
- **Stack residency** — `mctl` reports it (`redundant_artifacts[kind=
  stack_index]`), but `mctl_core/redundant_state.py` resolves the stack
  **rig-root-relative** (`<rig_root>/.beads/briefs/stack`), while the live stack
  is city-root-level and cross-rig (`<city-root>/.beads/briefs/stack`). Every
  artifact therefore reports `missing` in the live deployment, so step 2 keeps
  scanning `$STACK_DIR` directly.
- ~~**The `gt-*` HQ store**~~ — no longer a gap. `city_rig_entries`
  synthesises a reserved `hq` rig for the city-root store, so `--all-rigs`
  covers it. See step 3.

Cross-rig *assembly* is no longer on this list: `--all-rigs` owns it. Do not
reintroduce a per-rig loop here.

## What this skill does NOT do

- ❌ Present any brief (that is `/present-briefs`)
- ❌ Adjudicate any brief (that is `/adjudicate-brief`)
- ❌ Mutate any bead or file
- ❌ Count or report pile (awaiting gate-keep promotion) contents
