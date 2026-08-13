---
name: wake-city
description: >
  Actually WAKE a stalled Gas City — diagnose WHY the fleet is dead, then apply
  the correct revival per cause and VERIFY work resumes. Unlike nudge-city
  (which only nudges and silently fails on weekly-limit-dead zombies),
  wake-city triages every stall cause — dead tmux server, Dolt down, suspended
  rig, dead control-dispatcher, session-limit vs weekly-limit zombies — and
  fixes each the right way, then confirms the city is processing work again.
  Use when the city looks dead or frozen: "wake the city", "wake-city", "the
  fleet is stuck / not picking up work", "nudge-city didn't wake them", "revive
  the city", "no workers are active", "0 workers but ready beads", "bring the
  city back to life". NOT for saturating an already-live fleet (push-the-fleet)
  or scheduling a future alarm (wake-up-call).
---

# wake-city

Bring a stalled city back to life. `nudge-city` **nudges** stalled sessions —
but a nudge only works when the session's agent process is alive-but-idle with
quota to resume into. It is **blind** to the other ways a city dies:

- a session that hit the **weekly** limit (resets days out) has **no quota to
  wake into** — a nudge has nothing to revive (observed live 2026-07-31: three
  hecke run-operators nudged into a wall, `weekly limit · resets Aug 4`);
- the **tmux fleet server** is gone (nothing can spawn);
- **Dolt** is down (bd can't resolve beads, so no worker can claim);
- the **rig is suspended** (the reconciler is skipping its agents on purpose);
- the **control-dispatcher** is dead (nothing respawns workers).

`wake-city` diagnoses which of these holds **per rig/session**, applies the
matching fix, and — the part nudge-city never does — **verifies the city is
actually processing work again**, failing loud when a cause it cannot fix
(e.g. a weekly-limit block) is the real problem.

Companions: `nudge-city` (the nudge fan-out — wake-city calls the same nudge for
the one cause a nudge fixes), `wake-up-call` (schedules the alarm for a reset
moment), `push-the-fleet` (saturate an *already-live* fleet), `adjust-workers`
(raise the worker cap when slots are the bottleneck).

## Pre-flight

`gc` on PATH (`command -v gc`). gc is slow under server-mode load — bound every
loop and expect each call to take seconds.

## Step 1 — Diagnose the stall cause (do NOT act yet)

Collect evidence BEFORE any restart — a blind restart destroys the evidence and
can mask the real cause. Work the causes top-down (a lower cause is moot if a
higher one is true):

```bash
# A. Is the tmux fleet server alive at all? (nothing spawns without it)
tmux -L gt ls >/dev/null 2>&1 && echo "tmux: UP" || echo "tmux: DOWN"

# B. Is Dolt reachable? (bd can't resolve beads otherwise — use gc dolt, NOT gc status)
#    THREE-valued: 0 = UP, 2 = UP but compaction-quarantined (NOT a stall cause),
#    1/other = genuinely DOWN. See template-fragments/dolt-preflight.md.
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) echo "dolt: UP" ;;
  2) echo "dolt: UP (compaction quarantined — auto-GC blocked, NOT a stall cause)"
     printf '%s\n' "$_dolt_out" | sed -n '/^Compaction quarantine:/,$p' | sed 's/^/  /'
     echo "  Reclaim with 'gc dolt compact' once an operator clears the marker." ;;
  *) echo "dolt: DOWN" ;;
esac

# C. Per-rig: is the rig suspended? (reconciler intentionally skips its agents)
gc rig list 2>/dev/null

# D. Is each rig's control-dispatcher alive? (it is what respawns workers)
tmux -L gt ls 2>/dev/null | grep -i "control-dispatcher"

# E. The stalled sessions + WHY each stalled (the crux nudge-city gets wrong)
gc session list 2>/dev/null            # STATE, LAST ACTIVE, workdir
gc session logs <id> 2>/dev/null | tail -3   # the last line names the cause
```

**Classify each stalled worker by its log tail (this decides the fix):**

| Log tail signal | Cause | Fix (Step 2) |
| --- | --- | --- |
| `hit your session limit · resets <hours>` | session-limit zombie | **nudge** (resumes when quota returns) |
| `hit your weekly limit · resets <days>` | **weekly**-limit zombie | **close** + surface the capacity block (nudge canNOT fix this) |
| no progress since spawn, process idle | idle-but-alive | **nudge** |
| recent tool calls / real work | LIVE | **skip** — never nudge live work |

## Step 2 — Apply the fix that matches the cause (top-down)

Fix the highest true cause first, then re-diagnose before descending — often one
fix (e.g. `gc dolt start`) revives everything below it.

1. **tmux DOWN** → the supervisor lost its server; give it a fresh one:
   ```bash
   gc restart          # respawns supervisor + tmux fleet server
   ```
   Re-run Step 1 after; most sessions come back on their own.

2. **Dolt DOWN** → workers can't claim beads until it's up:
   ```bash
   gc dolt status; gc dolt start
   ```
   NEVER `rm -rf ~/.dolt-data`, never touch `.dolt/` internals, never signal the
   Dolt PID (see nudge-city / mayor Dolt doctrine).

3. **Rig SUSPENDED** → resume it so the reconciler stops skipping its agents:
   ```bash
   gc rig resume <rig>
   ```

4. **control-dispatcher DEAD** (rig not suspended, but no dispatcher in tmux) →
   it is the thing that respawns workers; without it a resumed rig still does
   nothing. Restart it (supervisor respawns dispatchers on its tick; if it does
   not, `gc restart`). Re-diagnose after.

5. **session-limit zombie** → nudge (this is the one case a nudge fixes; defer
   to `nudge-city` for the fan-out, or inline):
   ```bash
   gc session nudge <id> "Your usage limit has reset. Please resume: finish your task, close your wake-up bead, send the drain-ack, and exit so your run-operator slot frees. If nothing to record, close with a no-op reason."
   ```

6. **weekly-limit zombie** → a nudge does NOTHING (no quota to wake into). The
   correct move is to **free the slot** so the *live* control-dispatcher can
   respawn a fresh worker — but that fresh worker can only DO work if account
   quota exists (a switched provider/account, or after the weekly reset):
   ```bash
   gc session close <id>      # frees the run-operator slot the zombie was holding
   ```
   Then **fail loud** (P6.1): the fleet cannot truly wake on this account until
   the weekly limit resets or the worker provider is switched. State the reset
   time and the option explicitly — do not report "city woken" while a weekly
   block stands. If provider-switching is wanted, point at `switch-city-worker-provider`.

## Step 3 — VERIFY the city actually woke (the step nudge-city skips)

"Sessions exist" is not "city is working." Confirm real throughput resumed:

```bash
# Live worker sessions present (ground truth — not gc status, bug gs-0cy2):
tmux -L gt ls 2>/dev/null | grep -c "run-operator"

# Ready work exists AND is now being claimed (assignee becomes non-empty):
bd ready 2>/dev/null | head
bd show <a-ready-bead> 2>/dev/null | grep -i assignee   # should populate within ~60s

# For an in-flight molecule, its closed-step count should CLIMB (run twice, minutes apart):
bd show <molecule-root> 2>/dev/null | grep -c "✓ "
```

- Workers live + a ready bead picks up an assignee + step counts climb → **awake.**
- Ready beads but 0 workers claiming after a full pass → **still dead**; report
  the unresolved cause (do not declare success). A slow build is NOT a strand
  (`bd recall great-regression-misdiagnosis-s14`) — give it minutes before
  escalating, but never silently assume it worked.

## Guardrails

- **Diagnose before you restart** — a blind `gc restart` erases the evidence of
  the real cause. Step 1 first, always.
- **Never blanket-nudge.** Skip genuinely live sessions and long-running
  implementation workers (a nudge interrupts real work). Nudge only the
  session-limit / idle class from the Step 1 table.
- **A weekly-limit block is not something a nudge or close can fix** — closing
  frees the slot, but real work waits on the weekly reset or a provider switch.
  Say so loudly; a city reported "awake" while weekly-blocked is a false pass.
- **Never touch Dolt internals** — no `rm -rf ~/.dolt-data`, no `.dolt/` edits,
  no signals to the Dolt PID.
- **Not a substitute for diagnosing a wedged supervisor.** If the supervisor
  itself is not dispatching at all (dispatchers alive, rigs resumed, Dolt up,
  yet nothing pulls), that is a supervisor bug — diagnose it, do not loop-nudge.
- Bound every loop; gc is slow under the server-mode fallback.

## Provenance

- Companion (nudge-only fan-out): `nudge-city`; root-cause bead `gt-0x2sz`.
- `gc status` "0/N" is a probe-timeout artifact, NOT an idle fleet — ground
  truth is `tmux -L gt ls` + climbing step counts (bug `gs-0cy2`).
- Weekly-vs-session distinction observed live 2026-07-31 (hecke run-operators
  nudged into `weekly limit · resets Aug 4`; nudge could not wake them, close
  freed the slots for the live dispatcher).
- Wheel-check (P1.20): BUILD — nudge-city (nudge), wake-up-call (alarm),
  push-the-fleet (saturate live), adjust-workers (cap) surveyed; none diagnoses
  cause + revives + verifies. wake-city fills that gap.
