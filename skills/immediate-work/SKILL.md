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
- Multi-day backlogs or parallel batches → use priority-work or overnight sling
- Work that requires a separate git worktree context → use a new session
- Work where you need to keep talking to the human adjudicator while it runs → fork the agent

## Protocol

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
