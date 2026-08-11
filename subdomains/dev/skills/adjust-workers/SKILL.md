---
name: adjust-workers
description: Scale up (or down) the number of concurrent workers on a Gas City rig. Use when the human adjudicator says "more workers on <rig>", "scale up <rig>", "I need more capacity for hecke", or when gc session list shows a rig has fewer active run-operators than open work items. Reads current session counts, proposes a max_active_sessions patch, and guides the briefed pack-change path (city-toml-via-packs-not-hand policy).
---

# adjust-workers

Scale the number of concurrent run-operators (or any named agent template) on a
Gas City rig. Reads the live session state, computes the gap, proposes a
`max_active_sessions` patch, and routes it through the briefed pack-change path
(per `city-toml-via-packs-not-hand` policy — never hand-edit city.toml).

**Scope:** outside-agent only (the human adjudicator's Claude Code session). Does NOT dispatch
city agents; proposes a config change for repo-side landing agent to commit.

## Pre-flight

```bash
gc version || { echo "I'm sorry, I can't do that — gc CLI not found."; exit 1; }
```

## Step 1 — Identify the target rig

If the human adjudicator named a rig (e.g. "hecke", "gascity-packs"), use it directly.
Otherwise run:

```bash
gc session list
```

Look for rigs where the number of active `run-operator` sessions is fewer than
the number of open `in_progress` work beads. That rig is the bottleneck.

For a quick per-rig count:

```bash
gc session list | awk '{print $2}' | grep "run-operator" | sed 's|/gc\.run-operator.*||' | sort | uniq -c | sort -rn
```

## Step 2 — Read current limits

```bash
# How many run-operators are active RIGHT NOW for the target rig?
gc session list | grep "<rig>/gc.run-operator"

# What is the configured max_active_sessions for that agent?
gc agent show <rig>/gc.run-operator 2>/dev/null || echo "(no explicit cap — system default applies)"
```

If `gc agent show` is unavailable, grep city.toml for the relevant patches block:

```bash
grep -A 4 'name = "gc.run-operator"' <city-root>/city.toml
```

Note the current `max_active_sessions` value (absent = system default, usually 1
for on_demand named sessions unless the agent's [[agent]] block sets it).

## Step 3 — Compute proposed values

Default raise: **+2** on the current cap (or absolute min=2/max=4 if no cap set).

| Current max_active_sessions | Proposed new value |
|-----------------------------|--------------------|
| absent / 1                  | 3                  |
| 2                           | 4                  |
| 3                           | 5                  |
| N                           | N + 2              |

the human adjudicator may override with an explicit number. Accept and use it.

`min_active_sessions` keeps sessions warm even when the queue is empty.
Default: set to 1 (keep one worker warm) if raising max to ≥ 3.

## Step 4 — Propose the patch block

Present the proposed TOML block to the human adjudicator before any action:

```
Proposed [[patches.agent]] for <city-root>/city.toml (via pack PR):

  [[patches.agent]]
  dir = "<rig-prefix>"   # e.g. "hecke", "gascity-packs"
  name = "gc.run-operator"
  max_active_sessions = <N>
  min_active_sessions = 1

This will allow up to <N> concurrent run-operators for the <rig> rig,
and keep 1 warm session alive between work items.

Policy: city-toml-via-packs-not-hand → this goes via pack PR (repo-side landing lane),
not a hand-edit. See Step 5.
```

Wait for the human adjudicator to confirm or adjust the numbers before proceeding.

## Step 5 — Route via pack PR (structural fix)

Per `city-toml-via-packs-not-hand` policy, the patch must come from a pack
update, not a direct hand-edit.

**Option A — File a bead and route through briefed GitHub handoffs (canonical):**

```bash
bd create -t feature -p 1 \
  --title "[infra] Raise gc.run-operator max_active_sessions to <N> on <rig>" \
  --description "Add [[patches.agent]] block to mathcity pack (or gascity/roles pack) for <rig>/gc.run-operator with max_active_sessions=<N>, min_active_sessions=1. Bottleneck: <current-count> workers for <open-count> in_progress beads." \
  --rig <owning-rig>
# Record the resulting bead ID.

gc sling <rig>/gc.run-operator create-issue-briefed --formula \
  --var source_bead=<bead-id> --var brief_slug=<bead-id>-issue

# After the issue body is approved and filed, draft the PR body brief:
gc sling <rig>/gc.run-operator pr-pipeline-briefed --formula \
  --var source_bead=<bead-id> --var issue_number=<N> \
  --var brief_slug=<bead-id>-pr-body
```

**Option B — Lever A immediate workaround (no config change, per gc-increase-capacity):**

If the work is urgent and can't wait for the PR cycle, use Lever A:

```bash
# Re-sling a stalled item with explicit pool bypass
gc sling <rig>/gc.run-operator <convoy-id> --on build-basic \
  --var implementation_target=gc.implementation-worker
```

After Lever A, Option A is still required as the structural fix. File the bead.

**Option C — Named-session duplication (alternative structural fix):**

For rigs where adding a new `[[named_session]]` entry is cleaner than patching
max_active_sessions, add a second named entry to the roles pack:

```toml
[[named_session]]
name = "gc.run-operator-2"
template = "run-operator"
scope = "rig"
mode = "on_demand"
```

This is the Lever B pattern from `gc-increase-capacity`. Route via the same
briefed GitHub handoff flow.

## Step 6 — Gate on authorize-git-operation

If the human adjudicator approves the patch and Mayor session is about to push anything:

```
I need to push to <github-owner>/gascity-packs.
Run /authorize-git-operation to proceed.
```

Note: Mayor session (outside agent) cannot commit to <repos-root> — this is the repo-side landing lane.
Hand the proposed patch block to repo-side landing agent with the bead ID and proposed TOML text.

## What this skill does NOT do

- Does not hand-edit `<city-root>/city.toml` directly (violates city-toml-via-packs-not-hand)
- Does not commit or push to any repo (Mayor session is in conservative profile; repo-side landing agent executes)
- Does not affect brief-operator pool (that uses `pool = {max = N}` via its own [[patches.agent]])
- Does not adjust rig-level `max_active_sessions` (the per-rig cap under `[[rigs]]`) — that is a different lever

## Composes with

- `gc-increase-capacity` — canonical runbook this skill operationalizes
- `gc-check-capacity` — run-first diagnostic (what needs scaling)
- `authorize-git-operation` — gate before any push
- `create-issue-briefed` — issue body brief
- `pr-pipeline-briefed` — PR body brief

## See also

Source truth: `max_active_sessions` on `AgentOverride` (config.go:784) and on
`Agent` (config.go:3100). `min_active_sessions` on `AgentOverride` (config.go:786)
and `Agent` (config.go:3102). Pool is the legacy field; `max_active_sessions`
supersedes `pool.max`.
