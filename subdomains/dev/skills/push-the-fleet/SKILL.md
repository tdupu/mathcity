---
name: push-the-fleet
description: >
  Saturate the city fleet with ready, unblocked work. Use when the human adjudicator says
  "push the fleet", "fire more things", "get N things running", "dispatch
  everything ready", or "I want 10 things being worked on at a time". Finds
  all ready beads across rigs and dispatches them via build-basic-briefed
  (mathcity.work pattern, policy gsp-fhdnu) until the active worker count
  reaches TARGET. Never slows down to ask for confirmation — it dispatches
  and reports.
---

# push-the-fleet

Saturate the fleet. Dispatch every ready, unblocked bead via
`build-basic-briefed` until active workers ≥ TARGET (default: 10).

This skill is the batch version of `mathcity.work`: same formula, same
vars, same verify-assignee doctrine — but it sweeps the whole queue instead
of one bead.

## Step 0 — Load research priorities

Locate `PRIORITIES.md` at the city root:

```bash
CITY_ROOT=$(gc root 2>/dev/null || echo "$HOME/gt")
PRIORITIES_FILE="$CITY_ROOT/PRIORITIES.md"
```

**If the file exists:** read it now. It contains ranked research areas and
keywords. Use it as a scoring overlay in Step 3 — candidates matching
PRIORITIES.md P0 keywords dispatch before equal-priority candidates that
don't match; P1 keywords fill next, and so on. Announce the active priorities
at the top of the Step 6 report.

**If the file does not exist:** before dispatching, examine evidence of current
research direction:

1. Run `bd ready` across all rigs to see what is queued (read titles).
2. Run `gc dolt sql -q "SELECT id, title FROM gascity_packs.issues WHERE status='closed' ORDER BY closed_at DESC LIMIT 15"` to see what completed recently.
3. From those signals, draft a starter file and write it to `$CITY_ROOT/PRIORITIES.md`. Announce to the human adjudicator that you created it and what you inferred.

**PRIORITIES.md format (write this when creating from scratch):**

```markdown
# Research Priorities

Last updated: <YYYY-MM-DD>

## P0 — Critical / Blocking
<!-- Specific bead IDs or keyword phrases that always dispatch first -->

## P1 — High Priority Research Areas
<!-- Name research themes, e.g. "hecke algebra correctness", "brief pipeline" -->
- <area>

## P2 — Active but not urgent
- <area>

## Skip / Defer
<!-- Keywords or bead IDs to never auto-dispatch -->
```

## Pre-flight (same as mathcity.work)

```bash
tmux -L gt ls >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — no tmux fleet server (city can't spawn agents)."
  exit 1
}
gc dolt health >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
  exit 1
}
```

## Step 1 — Read target and current count

```bash
TARGET=${1:-10}
```

Count active workers via `gc session list` (NOT `gc status` — bug gs-0cy2):

```bash
ACTIVE=$(gc session list --state active 2>/dev/null \
  | grep -c "run-operator\|impl-worker" || echo 0)
echo "Active workers: $ACTIVE / target $TARGET"
```

If `ACTIVE >= TARGET`: report fleet is at target and stop. Do not re-dispatch
already-running beads.

## Step 2 — Enumerate ready beads per rig

For each rig, run `bd ready` from the rig's working directory to get its
unblocked queue. Only dispatch from rigs where work actually exists.

**Rig → working dir → artifact_root mapping:**

**⚠️ artifact_root MUST be scoped per bead, never passed as the bare rig
root.** Concurrent `build-basic-briefed` runs on the same rig that share an
artifact_root silently overwrite each other's `implementation-plan.md` /
`requirements.md` / `decomposition.md` (confirmed data loss, gsp-1bmxuz —
gsp-ewlwh's plan was overwritten by gsp-4qe2a's design-author because both
resolved to the same unsuffixed path). Always append `/.gc-builds/<bead-id>`
to the rig root below before passing `--var artifact_root=...`.

| Rig prefix | Working dir | Rig root |
|---|---|---|
| `gsp-` | `<city-root>/gascity-packs` | `<city-root>/gascity-packs` |
| `he-` | `<city-root>/hecke` | `<city-root>/hecke` |
| `hom-` | `<city-root>/homog` | `<city-root>/homog` |
| `jac-` | `<city-root>/jacobi` | `<city-root>/jacobi` |
| `lm-` | `<city-root>/lmfdb` | `<city-root>/lmfdb` |
| `mca-` | `<city-root>/magma_clifford_algebras` | `<city-root>/magma_clifford_algebras` |

For bead `<bead-id>` on rig root `<rig-root>`, the scoped value is:
`<rig-root>/.gc-builds/<bead-id>`

Detect rig from the bead ID prefix (first 2–4 chars before the first `-`).

## Step 3 — Priority filter before dispatching

**Skip these automatically — they need special handling or the human adjudicator input:**

- `[epic]` — epics are scheduling containers, not direct work items
- `human-gated` / `human-ok-required` in the title — requires the human adjudicator's explicit OK before dispatch
- `[reconcile D]` or repo-side landing agent-coordinated deploy beads — route to repo-side landing agent
- `brief-record` type — recording a verdict, not building; dispatching via build-basic-briefed is wrong for these
- `input convoy for <other>` — convoys feed context to another bead; dispatch the parent bead instead
- `Step spec for` — step specs are auto-managed by the formula machinery
- Status already `in_progress` or `closed` — skip

**Prefer in this order:**
1. P0 bugs and incidents
2. P1 bugs (especially infra and brief-system)
3. P1 implementation and design beads
4. P1 policy/skill beads
5. P2+ (fill remaining slots)

## Step 4 — Dispatch via `mathcity.work` (do NOT hand-sling)

**Feed the ranked candidates to the `mathcity.work` skill — never call
`gc sling` directly here.** A raw `gc sling` loop is exactly the
hand-sling anti-pattern `mathcity.work` exists to replace; it re-implements
(and drifts from) the canonical dispatch path. `mathcity.work` owns the
feed-don't-hand-sling doctrine: formula selection (`build-basic-briefed`
default per `gsp-fhdnu`; `planning-briefed` / `simple-work-briefed` /
`smoke-test-briefed` when the bead shape calls for it), the standard vars,
the **mandatory per-bead scoped `artifact_root=<rig-root>/.gc-builds/<bead-id>`**
guardrail (`gsp-1bmxuz`), and the verify-assignee + slow-build-≠-strand gates.

`push-the-fleet` is the **batch layer over `mathcity.work`**: it ranks (Steps
0–3) and hands the ranked candidate set to `mathcity.work`, which does the
actual dispatch correctly.

- Invoke the **`mathcity.work`** skill with the ranked candidate beads from
  Step 3 (it accepts a single bead or a set of ready beads). It selects the
  right formula per bead and slings each with the correct vars + scoped
  `artifact_root`.
- Feed in parallel batches — the dispatcher queues what it can't run
  immediately; do not serialize.
- Stop feeding when DISPATCHED_COUNT + ACTIVE >= TARGET.

This keeps a single canonical dispatch implementation: fix a dispatch bug once
in `mathcity.work` and `push-the-fleet` inherits it.

## Step 5 — Verify assignees (mandatory gate)

After each batch, wait ~30–60s then spot-check a sample of the freshly
created molecule beads:

```bash
bd show <molecule-bead> | grep -i assignee   # must be NON-EMPTY
```

If a molecule still has no assignee after 60s, the slot may be full. Report
it — do not silently assume success. An open root bead is NOT a strand (see
gs-0cy2 and `mathcity.work` slow-build doctrine); wait before escalating.

## Step 6 — Report

Emit one concise table:

```
Fleet loaded — <N> dispatched, <ACTIVE> workers active.

| Bead | Title | Rig | Molecule |
|------|-------|-----|----------|
| he-2zv | conductor bug | hecke | he-xxxx |
| gsp-ws6hx | reaper order | gascity-packs | gsp-xxxx |
...

Target: <TARGET> | Active (post-dispatch): <ACTIVE> | Queue remaining: <N>
```

If the queue was exhausted before reaching TARGET, say so explicitly — that
is a "no more unblocked work" state, not a failure.

## Guardrails

- Never dispatch the same bead twice — check for an existing `in_progress`
  molecule before slinging.
- Do not dispatch beads that are blocked (dependencies open).
- Do not touch <repos-root>/ — all git operations use the repo-side landing lane.
- Do not hand-edit city.toml to raise worker caps — use `adjust-workers` if
  the worker ceiling itself is the bottleneck.
- If the bottleneck is worker *slots* (too few run-operators in the pool),
  use `/adjust-workers` AFTER this skill to raise the cap.

## Composes with

- `mathcity.work` — single-bead dispatch (this skill is the batch form)
- `adjust-workers` — raise worker cap when slot count limits throughput
- `hourly-check` — periodic fleet health that surfaces when queue depth > 0
  but active workers = 0

## Source policy

Dispatch formula: `gsp-fhdnu` (build-basic-briefed preferred).
Slow-build ≠ strand: `gs-0cy2`, `he-uz9fg`.
