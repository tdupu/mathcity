---
name: immediate-work
description: In-session synchronous dispatch — spawn the right agent NOW in the current session to complete a specific bead or task. No pool, no queue, no sling. Trigger phrases: "immediate work", "do this now", "in-session", "spawn now for X", "right now". Contrast with priority-work (async targeted dispatch to named agent). Model guide: Haiku for mechanical/gate tasks (frontmatter updates, simple patches, config), Sonnet for research/analysis/code, Fable for synthesis/architecture/complex multi-file work.
---

# immediate-work

In-session synchronous dispatch: spawn the right agent in the CURRENT session to complete a specific task right now. No pool, no claim race, no boomerang.

## When to use

- the human adjudicator says "immediate work", "do this now", "spawn now for X", "in-session", "right now"
- A task is urgent enough that it should not wait for a pool claim or sling cycle
- The task is scoped to a single agent session (not multi-day backlog)
- You just created a bead and the human adjudicator says "sling it for immediate work"

**Do NOT use for:**
- **Work that already has an approved decision brief** → that is `mctl work
  dispatch` (step 0 below). Spawning inline discards the provenance record.
- Multi-day backlogs or parallel batches → use priority-work or overnight sling
- Work that requires a separate git worktree context → use a new session
- Work where you need to keep talking to the human adjudicator while it runs → fork the agent

## Protocol

### Step 0 — Is this work brief-backed? (check before spawning anything)

immediate-work exists to skip the pool and the sling. It must **not** skip the
brief gate. If the task already has an approved decision brief behind it, the
canonical dispatch path is `mctl work dispatch` — spawning an inline agent
instead leaves no provenance, no duplicate-dispatch protection, and no record
that the approved brief was ever executed.

```bash
CITY_ROOT="${CITY_ROOT:-$HOME/gt}"

# `bin/mctl` is the ONLY supported entry point for the MathCity control CLI.
# Never invoke assets/scripts/mctl.py directly — the shim owns repo-root
# resolution, and mctl_core/context.py owns city/rig discovery.
PACK_ROOT="${MATHCITY_PACK_ROOT:-$(
  sed -n '/^\[defaults.rig.imports.mathcity\]/,/^\[/p' "$CITY_ROOT/city.toml" \
    | sed -n 's/^source *= *"\(.*\)"/\1/p' | head -1
)}"
MCTL="$PACK_ROOT/bin/mctl"
[ -x "$MCTL" ] || { echo "mctl entry point not found at $MCTL"; exit 1; }

# Is there a brief bead for this work, and is it dispatchable?
"$MCTL" work status "$BRIEF_BEAD" --city "$CITY_ROOT" --rig "$RIG" --json
```

- **`MWRK_BRIEF_NOT_FOUND`** — not brief-backed. This is ordinary immediate
  work; continue to step 1 and spawn in-session.
- **`readiness: ready`** — brief-backed and approved. **Dispatch through mctl**,
  do not spawn inline:

  ```bash
  out=$(MCTL_ENABLE_LIVE_DISPATCH=1 "$MCTL" work dispatch "$BRIEF_BEAD" \
          --city "$CITY_ROOT" --rig "$RIG" --json); rc=$?
  TRACE_ID=$(printf '%s' "$out" \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("trace_id",""))
except Exception: print("")')
  echo "MCTL-TRACE: $TRACE_ID"
  ```

  `MCTL_ENABLE_LIVE_DISPATCH=1` is exported for this one command only; unarmed,
  `work dispatch` returns a dry run and slings nothing.
- **`readiness: blocked`** — read the `blockers`. `MWRK010` (no approving
  verdict) means the brief has not been adjudicated: **immediate-work is not a
  way to get ahead of that.** `MWRK_ALREADY_DISPATCHED` means the work is
  already out. `MWRK001` means the bead already has an assignee.

**`MBRF004`** ("no source dependency") is a **`WARN`** and refuses nothing —
corrected 2026-08-27, this line previously called it an `ERROR` that blocked
dispatch on most of the queue. `briefs.py:1652` emits it at `Severity.WARN`;
`_blocking_diagnostic` (`briefs.py:2124`) selects only `ERROR`/`FATAL`. What
actually gates dispatch is `MBRF011` ("no approving verdict for dispatch"),
which is correct. Report `MBRF004` verbatim; do not branch on it — in either
direction — nor on `MBRF005` or `MBRF021`. See
`template-fragments/mctl-entry-point.md`.

`gt-*` beads live in the city-root HQ store, which is not a registered rig, so
`--rig gt` fails with `MCTL_CONTEXT_UNKNOWN_RIG`. Treat those as not
brief-backed here and spawn in-session.

### Step 1 — Identify the work

If not yet beaded, create the bead first:
```bash
cd <city-root> && bd create -t <type> \
  --title "<title>" \
  --description "<what done looks like>" \
  --priority 1
```

### Step 2 — Select the model

| Work type | Model |
|---|---|
| Mechanical: frontmatter patches, config, scripts, simple fixes | Haiku |
| Research, analysis, code review, implementation | Sonnet |
| Architecture, synthesis, multi-file design, formula authoring | Fable |

### Step 3 — Spawn the agent

Use the Agent tool inline (not background) with:
- Full task context (what bead, what to do, what done looks like)
- The correct model override
- Explicit success criteria / done condition

### Step 4 — Close on completion

When the agent returns, verify and close:
```bash
cd <city-root> && bd close <bead-id> --reason "<what was done>"
```

## Reference example (what defined this skill)

"Spawning a Haiku now to advance the 3 stuck briefs through Phase 5" — briefs
he-1hq, he-0rk2, he-17np had `review_gate: pending`. Haiku spawned in-session,
all 3 promoted to `status: approved` in a single turn. No sling, no queue, no wait.

## Contrast: immediate-work vs. priority-work

| | immediate-work | priority-work |
|---|---|---|
| Execution | Current session (synchronous) | Async (separate agent) |
| Dispatch | Agent tool inline | Background agent / sling to named target |
| the human adjudicator sees | Result in this conversation | Result lands in bead, review later |
| Use when | Urgent + small scope + needs the human adjudicator's eye | High priority but can run unattended |
