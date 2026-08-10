---
name: switch-city-worker-provider
description: Controlled runbook for temporarily switching selected Gas City worker sessions between Claude-backed and Codex-backed providers and rolling them back. Use when the human adjudicator says "switch workers to Codex", "switch back to Claude", "prove Codex worker spawn", "provider routing for E2E", or asks whether a worker can run under Codex instead of Claude.
---

# switch-city-worker-provider

Temporarily prove or change provider routing for one named Gas City worker,
then roll it back. This is an outside-agent operator runbook for short,
observable tests; it is not a broad fleet migration mechanism.

## Boundaries

- Run from the city root as an outside agent helping the human adjudicator.
- Prefer an existing Codex-pinned worker for smoke tests before changing any
  provider routing.
- Do not stop the city for this skill. Use targeted session inspection and
  targeted session lifecycle commands only.
- Do not select paid or usage-credit options if a provider prompts for them.
- Do not hand-edit city config as a pack fix. If the human adjudicator explicitly authorizes
  a temporary local provider override, label it as a site-local workaround,
  snapshot before changing it, and restore the snapshot after the test window.
- Do not dispatch with `gc sling` until the target bead has no active,
  non-stale assignee.
- Do not use `codex-dispatch` for the smoke if the point is provider spawn
  proof. Its prompt writes result text into bead notes; for this smoke, use a
  raw scratch bead and close-only lifecycle.

## Pre-flight

Before doing anything, run these checks:

```bash
command -v gc >/dev/null || { echo "I'm sorry, I can't do that - gc is not on PATH. Run the Gas City install/update step and retry. (This skill switches Gas City worker provider routing.)"; exit 1; }
command -v bd >/dev/null || { echo "I'm sorry, I can't do that - bd is not on PATH. Run the Beads install/update step and retry. (This skill creates and checks scratch beads.)"; exit 1; }
command -v jq >/dev/null || { echo "I'm sorry, I can't do that - jq is not on PATH. Install jq or use the JSON output manually. (This skill inspects gc and bd JSON safely.)"; exit 1; }
pwd
gc agent list --json >/dev/null
gc session list --json >/dev/null
bd doctor --check-health
```

If `bd doctor --check-health` fails, stop and fix Beads health first. If full
`gc doctor` has unrelated known warnings, record them, but do not treat them as
proof that provider spawn is broken.

## Step 1 - Snapshot Current Provider State

Use a temp evidence directory and keep the raw JSON. This gives rollback and
postmortem data even if the worker never starts.

```bash
CITY_ROOT="${GC_CITY_ROOT:-$(pwd)}"
SWITCH_TS="$(date +%Y%m%d-%H%M%S)"
SWITCH_EVIDENCE="${SWITCH_EVIDENCE:-/private/tmp/gc-provider-switch-$SWITCH_TS}"
mkdir -p "$SWITCH_EVIDENCE"
cd "$CITY_ROOT"
gc agent list --json > "$SWITCH_EVIDENCE/agents-before.json"
gc session list --json > "$SWITCH_EVIDENCE/sessions-before.json"
cp city.toml "$SWITCH_EVIDENCE/city-before.toml"
```

If `city.toml` is absent in the current directory, stop. You are not in the
city root.

## Step 2 - Prove Existing Codex Worker Spawn

Set the rig and worker address explicitly. For the current filter E2E, the
expected rig is the city-side `gascity-packs` checkout and the expected worker
is `mathcity.codex-worker`.

```bash
GC_RIG="${GC_RIG:?set GC_RIG to the target rig name}"
GC_RIG_WORKTREE="${GC_RIG_WORKTREE:?set GC_RIG_WORKTREE to the city-side rig checkout}"
GC_CODEX_WORKER="${GC_CODEX_WORKER:-$GC_RIG/mathcity.codex-worker}"
cd "$CITY_ROOT"
gc agent list --json | jq -e --arg worker "$GC_CODEX_WORKER" '.agents[] | select(.qualified_name==$worker and .provider=="codex")'
cd "$GC_RIG_WORKTREE"
SMOKE_ID="$(bd create "codex provider smoke: close only" \
  --type task \
  --priority 3 \
  --description "Scratch bead for one Codex provider smoke. Do not edit source files and do not update notes; close this bead only after confirming worker startup." \
  --acceptance "A provider=codex Gas City session starts for this bead and the bead closes cleanly or blocks loudly." \
  --silent)"
ASSIGNEE="$(bd show "$SMOKE_ID" --json --readonly | jq -r 'if type=="array" then .[0].assignee // "" else .assignee // "" end')"
if [ -n "$ASSIGNEE" ]; then
  echo "ALREADY DISPATCHED - bead $SMOKE_ID has active assignee: $ASSIGNEE; aborting" >&2
  exit 1
fi
cd "$CITY_ROOT"
gc sling "$GC_CODEX_WORKER" "$SMOKE_ID" --nudge --json
```

Poll for both the provider session and the bead lifecycle:

```bash
cd "$CITY_ROOT"
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  gc session list --json | jq -e --arg worker "$GC_CODEX_WORKER" '[.sessions[] | select((.template==$worker) or (.provider=="codex"))] | length > 0' && break
  sleep 10
done
gc session list --json | jq --arg worker "$GC_CODEX_WORKER" '[.sessions[] | select((.template==$worker) or (.provider=="codex")) | {id,name,template,provider,state}]'
cd "$GC_RIG_WORKTREE"
bd show "$SMOKE_ID" --json --readonly | jq 'if type=="array" then .[0] else . end | {id,status,assignee}'
```

If no Codex provider session appears, stop. Do not switch any other worker.

## Step 3 - Decide Whether A Provider Override Is Needed

Only consider a provider override after the Codex smoke passes. The usual
reason is a temporary E2E window where Claude-backed warm sessions are blocked
by a provider token prompt and the human adjudicator wants one deterministic machine worker
to run under Codex.

The invariant for the temporary workaround is:

1. One target worker address is named.
2. The prior city config and sessions are snapshotted.
3. Existing sessions for that worker are observed before restart/close.
4. The change is rolled back to the prior provider after the E2E window.

If the root cause is "Claude provider prompt blocks machine-worker E2E", file
or reference a follow-up bead for a pack-owned provider-routing fix. Do not
pretend the local override is that fix.

## Step 4 - Apply A Narrow Temporary Override

Use this step only with explicit current-session authorization from the human adjudicator.
Set:

```bash
TARGET_AGENT="${TARGET_AGENT:?set TARGET_AGENT, for example mathcity.brief-operator}"
TARGET_PROVIDER="${TARGET_PROVIDER:?set TARGET_PROVIDER, usually codex or claude}"
```

Edit only the existing city-local override for the target agent. If no override
exists, stop and propose the exact single-agent override block before writing
anything. Keep the snapshot from Step 1.

After the edit, reload and inspect:

```bash
cd "$CITY_ROOT"
gc reload
gc agent list --json | jq --arg agent "$TARGET_AGENT" --arg provider "$TARGET_PROVIDER" '.agents[] | select((.qualified_name==$agent or .name==$agent) and .provider==$provider)'
gc session list --json | jq --arg agent "$TARGET_AGENT" '[.sessions[] | select((.template==$agent) or (.name|contains($agent))) | {id,name,template,provider,state}]'
```

If active sessions still use the old provider, close or reset only the named
sessions for that target, then let the supervisor respawn them. Do not close
unrelated worker sessions.

## Step 5 - Roll Back To Claude

Rollback is mandatory unless the human adjudicator explicitly extends the test window.

```bash
CITY_ROOT="${GC_CITY_ROOT:-$(pwd)}"
SWITCH_EVIDENCE="${SWITCH_EVIDENCE:?set SWITCH_EVIDENCE to the snapshot directory from Step 1}"
cd "$CITY_ROOT"
cp "$SWITCH_EVIDENCE/city-before.toml" city.toml
gc reload
gc agent list --json > "$SWITCH_EVIDENCE/agents-after-rollback.json"
gc session list --json > "$SWITCH_EVIDENCE/sessions-after-rollback.json"
```

Then verify the target agent is back on the expected provider:

```bash
EXPECTED_PROVIDER="${EXPECTED_PROVIDER:-claude}"
gc agent list --json | jq --arg agent "$TARGET_AGENT" --arg provider "$EXPECTED_PROVIDER" '.agents[] | select(($agent == .qualified_name or $agent == .name) and .provider==$provider)'
```

If rollback verification fails, stop and escalate to the human adjudicator before running more
city work.

## Completion Report

Report these facts:

- Smoke bead ID and final status.
- Codex session ID, provider, and state observed.
- Whether a provider override was applied.
- Snapshot directory path.
- Rollback verification result.
- Any blocked Beads or Dolt sync state that prevents collaborator proof.
