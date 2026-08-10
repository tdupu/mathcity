---
name: check-work
description: Decide whether the fleet is ACTUALLY doing work — the signal-trust hierarchy and anti-patterns for reading fleet state, plus routing to the right per-purpose checker. Use when the user asks "how is work going", "is the fleet working", "is anything actually getting done", "are the workers stuck or just slow", "check on work", "is it progressing", or when you need to judge working-vs-hung-vs-stalled before acting. Encodes which signals to trust IN ORDER and which ones LIE (peek beats step-counts; gc status is buggy; step-count=0 is not a stall). Read-only. Routes to check-on-agent (one worker), city-status (fleet snapshot), check-molecules (accounting). Recommended model: Sonnet.
---

# check-work

**The one question:** is the fleet *actually working*, or does it just look
that way (or look broken when it's fine)? This skill is the **signal-trust
hierarchy** — which signals to believe, in what order — plus the anti-patterns
that burned real sessions. It does not replace the per-purpose checkers; it
tells you which signal is truth and routes you to the right one.

> Provenance: distilled from QUIMBY 36 (2026-08-05), an all-night fleet-throughput
> incident where lagging/misleading signals caused repeated mis-calls (restart
> "failed" that hadn't; fleet "stalled" that was mid-planning). The lesson: **peek
> the worker before concluding anything.**

## Signal-trust hierarchy (most trustworthy → most misleading)

| # | Signal | Command | Trust | What it tells you |
|---|---|---|---|---|
| 1 | **Worker peek** | `gc session peek <id>` | GROUND TRUTH | What the agent is doing *this second* — live tokens, the running command, the spinner. The ONLY signal that separates working / hung / idle. |
| 2 | **Event stream** | `gc events` | high | *Why* the fleet behaves as it does — spawns, drains, config-drift, cap rejections, wake-budget exhaustion. |
| 3 | **tmux counts** | `tmux -L gt ls \| grep -c run-operator` | high | Real live session counts. |
| 4 | **supervisor.log** | `tail ~/.gc/supervisor.log` | high | Mechanism view — `poolDesired`, `scaleCheck`, drift, spawn budgets. |
| 5 | **session STATE** | `gc session list` | medium | `active` / `draining` / `asleep` (reason: config-drift, weekly-limit). |
| 6 | **bd step-closure** | `bd show <root>` step counts | ⚠️ LAGGING | Confirms *completed* work only. Zero closed ≠ stalled. |

## Anti-patterns (signals that LIE — burned real sessions)

- **`step-count = 0` is NOT a stall.** Molecules spend their early phase in
  planning/decompose; steps close *late*. Concluding "stalled" from step-count
  alone mis-called both a restart and fleet-health in one session. **Peek (signal
  1) before ever saying stalled.**
- **`gc status` "0/N running" is a probe-timeout artifact** (bug `gs-0cy2`), not
  an idle fleet. Trust tmux + peek, never `gc status` counts.
- **Molecule ROOT has no assignee — that's normal, not stranded.** Run-ops work
  the *step* beads; the root is an assignee-less container. `check-molecules`
  keys STRANDED off in-progress step children for exactly this reason.
- **A slow build is not a strand** (`bd recall great-regression-misdiagnosis-s14`).
  Give a live-but-slow worker minutes before escalating; peek to confirm it's
  actually producing tokens, not hung.
- **`poolDesired` ≠ live run-ops.** Desired can read 12 while actual sits at 6 —
  a *spawn-rate* throttle (`max_wakes_per_tick`), not a stall. Check `gc events`
  for `create budget exhausted`.
- **Dolt "unreachable" while `bd` resolves beads = probe stress, not an outage.**
  `gc dolt health` pings the 58506 SQL server (can time out under load); `bd`
  uses a separate path. If `bd show <id>` works, the store is fine.

## Procedure

1. **Peek first (signal 1).** For each active worker: `gc session peek <id>`.
   Live token generation / a running command = working. Idle prompt with no
   progress across two peeks = investigate. This alone answers most "is it
   working?" questions.
2. **If a worker looks stopped, ask WHY (signal 2):** `gc events` — look for
   `session.draining` (config-drift), `create budget exhausted` (spawn throttle),
   idle-timeout, weekly-limit.
3. **Confirm counts (signal 3):** `tmux -L gt ls | grep -c run-operator` vs
   `poolDesired` in supervisor.log — a gap is usually spawn-rate, not death.
4. **Only then** consult step-counts (signal 6) for *completed* throughput — and
   never conclude stalled from it alone.

## Route to the right checker (don't reinvent)

| Need | Skill |
|---|---|
| ONE worker: what is it doing / did its artifact land / is it hung? | `check-on-agent` |
| Fleet snapshot: liveness, sessions, molecule step tables, briefs, Dolt | `city-status` |
| Full molecule accounting: being-worked / stranded / ready, ranked | `check-molecules` |
| Revive a genuinely stalled fleet (diagnose + fix + verify) | `wake-city` |
| Saturate a healthy fleet with ready work | `push-the-fleet` |

This skill is the *judgment layer* over those — it tells you which signal is
truth so you pick the right checker and don't mis-call the result.

## What this skill does NOT do

- ❌ Dispatch, nudge, or modify anything (read-only judgment + routing).
- ❌ Replace check-on-agent / city-status / check-molecules — it routes to them.
- ❌ Revive a stalled fleet (that is `wake-city`).
