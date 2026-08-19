---
name: strand-sweep
description: >-
  Find beads and molecules that have been slung but will never execute —
  immediate strands (empty assignee), dead formula run_target addresses,
  prose-only-blocked beads bd ready can't see, and deadlocked molecules
  whose step count is flat. Use when the user says "strand-sweep", "find dead
  molecules", "find stranded beads", "DOA molecules", "find slung-but-never-run",
  "check molecule health", "are any molecules stuck", or when a bead was slung
  but no progress is visible after several minutes. Read-only: reports strands
  but never mutates bead state, files, or config.
---

# strand-sweep

Find beads and molecules that have been slung but will **never** execute.
Read-only — reports findings, never mutates.

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
  *) echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot query bead state)."
     echo "Run 'gc dolt status' / 'gc dolt start' and retry."
     exit 1 ;;
esac
tmux -L gt ls >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — no tmux fleet server (liveness check impossible)."
  echo "Run 'gc restart' to give the supervisor a fresh tmux server, then retry."
  exit 1
}
```

## Detection ladder

Run all rungs. Report findings per-rung. A bead may appear in multiple rungs.

---

### Rung A — Immediate strands (empty assignee after dispatch)

Beads that were slung but no session ever claimed them.

```bash
# Open beads with dispatch metadata but no assignee (check he-*, gsp-*, gt-* rigs)
for RIG in <city-root>/hecke <city-root>/gascity-packs <city-root>; do
  [ -d "$RIG/.beads" ] || continue
  echo "=== $(basename $RIG) ==="
  cd "$RIG"
  bd list --status open --limit 50 2>/dev/null | while read id rest; do
    body=$(bd show "$id" 2>/dev/null)
    assignee=$(echo "$body" | grep -m1 "^Assignee:" | awk '{print $2}')
    dispatched=$(echo "$body" | grep -im1 "dispatched\|slung\|build-basic-briefed\|gc sling")
    if [ -n "$dispatched" ] && [ -z "$assignee" -o "$assignee" = "-" ]; then
      title=$(echo "$body" | grep -m1 "^Title:" | cut -d: -f2-)
      echo "STRAND-A: $id —$title"
    fi
  done
done
```

**Signal:** open bead, has dispatch evidence in body/comments, no assignee. These are the verify-assignee gate failures (doctrine: he-uz9fg).

---

### Rung B — Dead formula run_target (formula compiler)

Formula TOMLs that name a `gc.run_target` that no longer resolves to a live session pool. This is the pre-sling hygiene check the supervisor does NOT perform automatically.

```bash
# Get live session addresses
LIVE_POOLS=$(gc agent list 2>/dev/null | grep -E "^\s*(name|pool|session):" | grep -v "^$" || echo "")
TMUX_SESSIONS=$(tmux -L gt ls 2>/dev/null | awk -F: '{print $1}' || echo "")

echo "=== Rung B: Formula run_target validation ==="
# Scan for static (non-template) run_target values
grep -rh '"gc\.run_target"\s*=\s*"[^{]' \
  <mathcity-pack-root>/formulas/*.toml 2>/dev/null \
  | grep -oE '"gc\.run_target"\s*=\s*"[^"]+"' \
  | grep -oE '"[^"]+"$' | tr -d '"' | sort -u \
  | while read target; do
      if ! echo "$LIVE_POOLS $TMUX_SESSIONS" | grep -qF "$target"; then
        echo "DEAD-TARGET: $target (formula uses this address but it is not in gc agent list)"
      else
        echo "OK: $target"
      fi
    done
```

**Signal:** a static `gc.run_target` value that does not appear in `gc agent list`. Template targets (`{{run_target}}`, `{{prep_target}}`) are runtime-resolved and skipped.

---

### Rung C — Prose-blocked with no clearing event

Beads that `bd ready` reports as ready but carry prose-only blocking that will never clear automatically.

```bash
echo "=== Rung C: Prose-only blocking ==="
for RIG in <city-root>/hecke <city-root>/gascity-packs <city-root>; do
  [ -d "$RIG/.beads" ] || continue
  cd "$RIG"
  bd ready --limit 30 2>/dev/null | while read id rest; do
    body=$(bd show "$id" 2>/dev/null)
    if echo "$body" | grep -qiE "needs human|needs-decision|waiting for verdict|HOLD|deferred-post-city|blocked by [hg][est]-[a-z0-9]+.*prose"; then
      title=$(echo "$body" | grep -m1 "^Title:" | cut -d: -f2-)
      echo "PROSE-BLOCKED: $id ($(basename $RIG)) —$title"
    fi
  done
done
```

**Signal:** bead is `bd ready` but body contains human-only clearing conditions. The machine will never auto-claim it.

---

### Rung D — Fleet liveness (orphaned wisps)

Molecule roots whose target pool has no live worker to claim them.

```bash
echo "=== Rung D: Fleet liveness ==="
echo "--- tmux sessions (ground truth) ---"
tmux -L gt ls 2>/dev/null || echo "(no sessions)"
echo "--- gc agent list ---"
gc agent list 2>/dev/null || echo "(unavailable)"
echo "--- in-progress roots (check assignee pool is alive above) ---"
for RIG in <city-root>/hecke <city-root>/gascity-packs <city-root>; do
  [ -d "$RIG/.beads" ] || continue
  cd "$RIG"
  bd list --status in_progress --limit 20 2>/dev/null | while read id rest; do
    body=$(bd show "$id" 2>/dev/null)
    assignee=$(echo "$body" | grep -m1 "^Assignee:" | awk '{print $2}')
    [ -z "$assignee" -o "$assignee" = "-" ] && continue
    if ! echo "$TMUX_SESSIONS" | grep -qF "${assignee%%/*}"; then
      title=$(echo "$body" | grep -m1 "^Title:" | cut -d: -f2-)
      echo "ORPHANED-WISP: $id assigned to $assignee but pool not in tmux — $(basename $RIG) —$title"
    fi
  done
done
```

**Signal:** in-progress bead whose assignee pool is absent from `tmux -L gt ls`. The worker is dead; the wisp will never complete.

---

### Rung E — Deadlocked molecules (flat step count)

Build-basic-briefed roots open for > 30 min with no step-count change.

```bash
echo "=== Rung E: Deadlocked molecules (requires two readings 5min apart) ==="
for RIG in <city-root>/hecke <city-root>/gascity-packs <city-root>; do
  [ -d "$RIG/.beads" ] || continue
  cd "$RIG"
  bd list --status in_progress --limit 20 2>/dev/null | while read id rest; do
    body=$(bd show "$id" 2>/dev/null)
    steps=$(echo "$body" | grep -c "✓ ")
    title=$(echo "$body" | grep -m1 "^Title:" | cut -d: -f2-)
    echo "MOLECULE $id ($(basename $RIG)) steps_done=$steps —$title"
  done
done
echo "(Run again in 5–10 minutes. Flat step_done count = genuine deadlock.)"
echo "(Rising count = healthy slow-build — do NOT classify as a strand. gs-0cy2)"
```

**Signal:** step count flat across two readings separated by ≥ 5 minutes. Distinguish from healthy slow builds — molecule roots stay OPEN by design until all terminal steps finish (gs-0cy2, he-uz9fg).

---

## Classification Contract

For each reported candidate, include `lost_class`,
`recommended_disposition`, `root_cause`, and `fingerprint` from
`assets/bead-filter/lost-bead-schema.toml`. Persisted classification events
use `schema = "lost-bead-classification.v1"`.

Default mappings:
- Rung A empty assignee: `lost_class=immediate_strand`, `recommended_disposition=resling`, `root_cause=no_worker_claimed`, `fingerprint=empty_assignee_after_verified_sling`.
- Rung B dead target: `lost_class=dead_target`, `recommended_disposition=repair_source`, `root_cause=dead_or_deprecated_target`, `fingerprint=dead_static_run_target`.
- Rung C prose blocker: `lost_class=hidden_blocker`, `recommended_disposition=encode_dependency`, `root_cause=hidden_human_decision_dependency`, `fingerprint=ready_but_prose_blocked`.
- Rung D orphaned wisp: `lost_class=orphaned_wisp`, `recommended_disposition=recycle`, `root_cause=no_live_target`, `fingerprint=assigned_pool_absent_from_tmux`.
- Rung E flat step count: `lost_class=deadlock`, `recommended_disposition=repair_source`, `root_cause=formula_deadlock`, `fingerprint=flat_step_count_after_observation_window`.

The sweep remains read-only; executor skills run only after adjudication. To
persist a row, create one linked `type=event` bead per classified source bead
and treat any table/file export as cache.

## Output table

After all rungs, produce a summary:

```
Strand-sweep complete — YYYY-MM-DD HH:MM

| Rung | ID       | Rig           | Type          | Evidence                             |
|------|----------|---------------|---------------|--------------------------------------|
| A    | he-jrr9t | hecke         | empty-assignee| dispatch metadata in body, no assignee|
| B    | —        | formula level | dead-target   | mathcity.dispatcher not in gc agent list|
| D    | gsp-xyz  | gascity-packs | orphaned-wisp | assignee=gc.run-operator, pool absent |

N strand(s) found. Recommended actions: [list per rung]
```

If no strands found: `"Strand-sweep clean — 0 strands found across N rungs."`

## Compose with

- **`/mathcity.work`** — re-dispatch a Rung A strand (re-sling with verify-assignee gate)
- **`/city-status`** — get a broader fleet snapshot before acting on Rung D findings
- **`/check-formula-hygiene`** — deep-audit a specific formula after a Rung B finding
- **`formula-compiler` bead (gsp-nihd4)** — tracks the substrate fix for Rung B (adding creation-time validation to formula-creator-math)

## What this skill does NOT do

- Does not close, defer, or reassign any bead
- Does not distinguish healthy slow-builds from true deadlocks on a single pass (Rung E needs two readings)
- Does not scan ephemeral wisps directly (`bd list` is blind to them — use `gc bd query 'ephemeral=true AND status=open'` for that)
- Does not report `bd blocked` deps — those are handled by the normal `bd ready` + `bd dep tree` workflow
