---
name: nudge-city
description: Revive city workers that are stalled/asleep after a usage-limit reset by nudging each one to resume, finish its task, and free its run-operator slot. Use when slung work won't start, sessions show "active" but idle for a long time, or right after a weekly/session usage limit resets. Trigger phrases "nudge the city", "nudge-city", "wake the workers", "revive stalled workers", "workers asleep after usage reset", "sessions stuck after limit reset", "why won't new work start / slots are full of zombies". NOT for a clean city (no stalled sessions) and NOT a restart — this is a targeted nudge, never a supervisor bounce.
---

# nudge-city

Fan-out revive for managed gc sessions that stalled at a usage/session
limit and did **not** auto-resume after the limit reset.

## Why this exists (failure mode, observed live 2026-07-13)

When a managed gc session's agent turn hits a usage/session limit, the
turn dies but the **session stays registered as `active`**, still holding
its rig's *singleton* `run-operator` slot. After the limit resets the
session does **not** auto-resume — it becomes a zombie that starves any
newly-slung work (e.g. the brief-pipeline dispatch waits forever for a
free slot). The fix is not a restart; it is a **nudge** to each stalled
session so it finishes, drains, and frees its slot. Root-cause tracking:
bead **gt-0x2sz**. Companion: **wake-up-call** schedules the alarm for the
reset moment; `nudge-city` is the fan-out that actually revives the fleet.

## Pre-flight

`gc` must be on PATH (`command -v gc` — every city session has it). No
conf file, no server, no Dolt-internal access. gc calls are **slow under
server-mode load**, so bound the loop and expect each call to take seconds.

## Procedure

1. **Enumerate** sessions:
   ```bash
   gc session list
   ```
   Columns of interest: session id (`gt-wisp-…`), template
   (`<rig>/gc.run-operator`), STATE, LAST ACTIVE, LAST NUDGE, workdir.

2. **Identify STALE candidates** — a session is a revive candidate when
   ALL hold:
   - STATE is `active` (not `asleep`/`draining`/`drained`), and
   - LAST ACTIVE is long ago (rule of thumb **> 15m**), and
   - it is not visibly doing work right now.
   Wake-up-class sessions (`on-merge-brief-record`, other
   `*-brief-record` / patrol wake-ups) are the usual offenders.

3. **Confirm the stall cause** before nudging (don't nudge healthy work):
   ```bash
   gc session logs <id> | tail -5
   ```
   A revive target's log ends with a line like
   `You've hit your (session|weekly) limit · resets <time>`, or shows no
   progress since spawn. If the tail shows recent tool calls / real work,
   it is LIVE — skip it.

4. **NUDGE each stale session** to resume and free its slot:
   ```bash
   gc session nudge <id> "Your usage limit has reset. Please resume: finish your current task, close your wake-up bead, send the drain-ack, and exit so your rig's run-operator slot frees. If there is nothing to record, close with a no-op reason."
   ```
   Loop over the candidates. Because gc is slow, cap the batch (e.g. skip
   after N per invocation) and re-run rather than letting one call block
   the whole loop.

5. **SKIP (never nudge):**
   - Genuinely LIVE sessions (recent activity, running tools) — a nudge
     interrupts real work.
   - Long-running **implementation workers** (`gc.implementation-worker`,
     build/do-work sessions) — check the log first; they can be legitimately
     busy for hours.
   - `core.control-dispatcher` and other infrastructure singletons.

6. **Report** which sessions were nudged and, on a follow-up
   `gc session list`, which slots freed (state moved to
   `draining`/`asleep`, or LAST ACTIVE became recent). Note any that did
   NOT respond.

## Fallback — close, only if a nudge doesn't take

A nudge revives a session whose agent process is alive-but-idle. If a
nudged session shows no activity after a reasonable wait (its process is
truly dead), close it to free the slot:
```bash
gc session close <id>     # single zombie
gc session prune          # sweep old dormant sessions (skips live ones)
```
Prefer **nudge first**; `close`/`prune` is the fallback, and `prune` only
touches dormant sessions so it will not kill live work.

## Guardrails

- Nudge before you close — closing loses any in-flight session state.
- NEVER touch Dolt internals, `.dolt/` files, or signal Dolt PIDs.
- This is NOT a supervisor restart. If the supervisor itself is wedged
  (not dispatching at all), that is a different problem — diagnose the
  supervisor, do not blanket-nudge.
- Bound the loop; gc is slow under the v53/v54 server-mode fallback.
