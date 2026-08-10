---
name: priority-work
description: Async targeted dispatch — bump a bead to P0 and dispatch it explicitly to a NAMED agent (polecat or codex target) immediately, bypassing queue order. No pool claim race: the target is named, the work starts now, the result lands in the bead for later review. Trigger phrases: "priority work", "bump this to the front", "dispatch this to <agent> now", "jump the queue", "priority dispatch X". Contrast with immediate-work (in-session synchronous — result comes back in THIS conversation). The "queue" is the set of open beads ordered by priority; priority-work reorders it AND staffs the front explicitly.
---

# priority-work

Async targeted dispatch: bump a bead to the front of the priority queue and dispatch it to a named agent immediately. The work runs unattended in a separate session; the result lands in the bead.

The "queue" in Gas City is not a literal FIFO — it is the set of open beads ordered by priority, drained by whoever claims next. Priority-work does two things at once:

1. **Reorder**: set the bead to P0 so every queue view puts it first.
2. **Staff**: dispatch it explicitly to a NAMED target (a dedicated agent, not a pool), so it does not wait for a claim cycle at all.

No pool, no claim race, no boomerang class.

## When to use

- the human adjudicator says "priority work", "bump this to the front", "jump the queue", "dispatch this to <agent> now"
- Work is high priority but can run unattended — the human adjudicator does not need to watch it happen
- The work deserves a dedicated session (separate context, possibly separate worktree)
- You know which agent should do it (or can pick one from the model guide below)

**Do NOT use for:**
- Urgent + small + needs the human adjudicator's eye on the result → use immediate-work (in-session)
- Routine backlog that can wait for normal queue order → just set priority and leave it
- Cross-model review / creative second opinion → pour `codex-dispatch` (that is its own explicit path)

## Protocol

### Step 1 — Ensure the bead exists and is complete

Priority-work runs unattended, so the bead IS the spec. It must contain everything a fresh agent needs: what to do, where, and what done looks like.

```bash
cd <city-root> && bd create -t <type> \
  --title "<title>" \
  --description "<full spec: context, files, done condition>" \
  --priority 0
```

If the bead already exists, verify the description is self-sufficient (a fresh agent with no conversation context must be able to execute it), then bump:

```bash
cd <city-root> && bd update <bead-id> --priority 0
```

### Step 2 — Pick the named target

| Work type | Target |
|---|---|
| Mechanical: frontmatter patches, config, scripts | dedicated Haiku agent |
| Research, analysis, implementation, code review | dedicated Sonnet agent |
| Architecture, synthesis, formula authoring, multi-file design | dedicated Fable agent |
| Cross-model review (explicit, sparse) | `codex:codex-worker` via codex-dispatch |

"Dedicated" means an on-demand agent spawned for THIS bead — never a pool claim. Name the target in the bead metadata so the dispatch is auditable:

```bash
cd <city-root> && bd update <bead-id> --set-metadata dispatch_target=<target> --set-metadata dispatched_by=priority-work
```

### Step 3 — Dispatch

Spawn the agent in the background (Agent tool with `run_in_background` semantics, or `gc sling <bead-id> <named-target>` when a standing named session exists). The dispatch prompt must include:

- The bead ID and full task context (do not assume the agent will find it)
- The model-appropriate framing (see table above)
- Explicit done condition: update the bead's notes with results, set `status=in_review` (or reassign per the bead's flow), NEVER `bd close` unless the bead's flow says workers close their own
- Escalation path: if blocked, file an escalation via `<mathcity-pack-root>/assets/scripts/escalate.sh` and stop — do not guess

Record the dispatch as a linked `dispatch-provenance.v1` event bead. The event
is canonical for downstream lost-bead filters; metadata fields on the source
bead are convenience hints only.

```toml
schema = "dispatch-provenance.v1"
source_bead = "<bead-id>"
dispatch_command = "<Agent background run or gc sling command>"
formula = "priority-work"
verified_assignee = true
assignee_state = "dispatched_to_named_target"
classification_hint = "healthy"
fingerprint = "priority_named_target_dispatch"
observed_at = "YYYY-MM-DDTHH:MM:SSZ"
```

If a named target fails to claim or acknowledge the work after the agreed
verification window, create the same event with `verified_assignee=false`,
`assignee_state="empty_after_60s"`,
`classification_hint="immediate_strand"`, and
`fingerprint="empty_assignee_after_verified_sling"`, then escalate instead of
waiting silently.

### Step 4 — Record and release

You are done at dispatch. Record in the current conversation:

```
PRIORITY-DISPATCHED: <bead-id> → <target>
DONE-CONDITION: <one line>
REVIEW: result lands in bead notes; check with `bd show <bead-id>`
```

Do NOT wait for the result — that is the whole point. If the human adjudicator wants to watch it happen, that was an immediate-work call, not a priority-work call.

### Step 5 — Later: verify and close

When the result lands (next session, next patrol, or when the human adjudicator asks):

```bash
cd <city-root> && bd show <bead-id>   # read notes/results
cd <city-root> && bd close <bead-id> --reason "<verified outcome>"
```

## Contrast: immediate-work vs. priority-work

| | immediate-work | priority-work |
|---|---|---|
| Execution | Current session (synchronous) | Async (separate dedicated agent) |
| Dispatch | Agent tool inline | Background agent / sling to named target |
| Queue effect | None (bypasses it entirely) | Bumps bead to P0 + staffs the front |
| the human adjudicator sees | Result in this conversation | Result lands in bead, review later |
| Use when | Urgent + small scope + needs the human adjudicator's eye | High priority but can run unattended |
| Pool involvement | None | None — named target only, no claim race |
