---
name: hourly-check
description: Start a 12-hour city health watchdog that fires every hour — shows fleet, molecule step table, brief stack, and Dolt health; outputs a prominent reminder to the invoking session to check on the city if stalls or usage limits are detected. Use when the user says "start hourly check", "set up watchdog", "monitor city overnight", "keep an eye on the city", or "hourly-check". Also handles recurring wakeup firings (argument form: /hourly-check N where N is the firing number 1–12). Recommended model: Sonnet.
---

# hourly-check

Periodic city health watchdog. One invocation starts the full 12-hour cycle;
each subsequent hourly wakeup re-runs this skill with the next firing number.

## State file

State is stored at `<city-root>/mathcity-mayor/hourly-check-state.json`:

```json
{
  "start_utc": "<ISO timestamp>",
  "firing": 1,
  "max_firings": 12,
  "interval_seconds": 3600
}
```

On first invocation (no argument or argument `1`): create/overwrite state file.
On wakeup invocations: read state, increment firing counter, update file.

## Procedure

### Step 1 — Determine firing number

Read the invocation argument (if any). If the skill is called as
`/hourly-check` with no number, this is firing #1. If called as
`/hourly-check 3`, this is firing #3.

```bash
FIRING=${1:-1}
STATE_FILE=<city-root>/mathcity-mayor/hourly-check-state.json
MAX=12

if [ "$FIRING" -eq 1 ]; then
  echo '{"firing":1,"max_firings":12,"interval_seconds":3600}' > "$STATE_FILE"
fi
```

### Step 2 — Run the health snapshot

Collect all data in parallel. Report the local time (HST = UTC-10) and UTC:

```bash
TZ=Pacific/Honolulu date "+%I:%M %p HST (%H:%M UTC)"
```

**Fleet:**
```bash
TMUX_COUNT=$(tmux -L gt ls 2>/dev/null | wc -l | tr -d ' ')
SESSION_COUNT=$(gc session list --state active 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')
DISPATCHERS=$(gc session list --state active 2>/dev/null | grep "control-dispatcher" | wc -l | tr -d ' ')
BRIEF_OPS=$(gc session list --state active 2>/dev/null | grep "brief-operator" | wc -l | tr -d ' ')
RUN_OPS=$(gc session list --state active 2>/dev/null | grep "gc\.run-operator" | wc -l | tr -d ' ')
IMPL=$(gc session list --state active 2>/dev/null | grep "gc\.implementation-worker" | wc -l | tr -d ' ')
```

**Dolt:**
```bash
LATENCY=$(gc dolt health 2>/dev/null | grep -oE '[0-9]+ms' | head -1)
```

**Molecules** — for each active run-operator or implementation-worker session,
extract the bead ID from the worktdir and query step counts via
`cd <city-root>/.beads/dolt/<db> && dolt sql` (steps use `dependencies.type='tracks'`,
not a `parent_id` column — see city-status §3 for the exact query). Build the
markdown table inline. impl-worker beads have no tracked steps; show `n/a`.

**Stale sessions** — flag any session with `LAST ACTIVE` > 2h:
```bash
gc session list --state active 2>&1 | awk '$NF ~ /^[0-9]+h/ && $NF+0 >= 2 {print $0}'
```

**Brief stack:**
```bash
PILE=$(ls <city-root>/.beads/briefs/.pile/*.md 2>/dev/null | wc -l | tr -d ' ')
STACK=$(ls <city-root>/.beads/briefs/stack/*.md 2>/dev/null | wc -l | tr -d ' ')
```

### Step 3 — Assess nudge need

Raise a prominent inline alert (output to this session — whoever invoked the watchdog)
if ANY of these are true. Do NOT send mail to the mayor; the invoking session IS the
right place to surface this so the human can act directly.

| Condition | Alert reason |
|---|---|
| `TMUX_COUNT` == 0 | City is DOWN — no tmux sessions |
| `LATENCY` >= 3000ms (or Dolt unreachable) | Dolt critical — city may stall |
| Any session last-active > 2h AND it holds a shuffler lock | Shuffler stall |
| Any molecule with +1h == 0 AND running for > 3h | Molecule stalled |
| `PILE` > 0 AND no active brief-operators | Shuffler dead with pile backlog |
| `gc status` returns partial banner OR reported running count < `TMUX_COUNT` × 0.5 | gc status probe timeout (gs-0cy2) — trust tmux, not gc status |

If a condition is met, emit prominently in the report output (Step 4):
```
⚠️ CITY NEEDS ATTENTION — <reason>
Please check on the city. Suggested action: <stall diagnosis hint>
```

### Step 4 — Output the report

Emit a single copy-pastable block:

```
• City Health Check — <time> HST (<UTC>) — check <N>/12

---
1. Fleet: <N> tmux sessions (ground truth) — <stable/STALLED>. <N> dispatchers, <N> brief-operators <active/idle>, <N> run-operators, <N> impl-workers. [Use `gc session list` counts, NOT `gc status` running count — see gs-0cy2]

2. Dolt: ✅ <N>ms — healthy. / ⚠️ <N>ms — WARN latency. / ❌ DOWN.

3. Molecules:
| Molecule           | Steps    | +1h | Status       | Started    | Completed   |
|--------------------|----------|-----|--------------|------------|-------------|
| <id> (<label>)     | N/M ✓    | +N  | ✅ complete  | <time>     | <time>      |
| <id> (<label>)     | N/M      | +0  | ⏳ running   | <time>     | —           |

4. Brief stack: <PILE> in pile, <STACK> on stack.

5. Stale sessions: None — all sessions LAST ACTIVE < 2h. / ⚠️ <session-id> stale <N>h.

---
[If alert condition met]: ⚠️ CITY NEEDS ATTENTION — <reason>. Please check on the city. <suggested action>
[If firing < 12]: Next check at <time+1h> HST. (check <N+1>/12)
[If firing == 12]: Final check — watchdog complete (12/12). Have a good morning, the human adjudicator.
```

### Step 5 — Schedule next wakeup (if firing < 12)

If `FIRING < MAX`, schedule the next wakeup using ScheduleWakeup:

- `delaySeconds`: 3600
- `prompt`: `/hourly-check $((FIRING + 1))`
- `reason`: `hourly city watchdog — check $((FIRING + 1))/12`

If `FIRING == MAX`: do NOT schedule. Report watchdog complete.

## First-invocation checklist

On `FIRING == 1` only:
1. Write state file
2. Run the check immediately (don't wait an hour for the first report)
3. Tell the human adjudicator: "Watchdog started — 12 checks scheduled, every hour. Next at <time+1h>."

## Stall diagnosis hints

- **No tmux sessions**: city crashed. Run `/prime-outsider` then restart sequence.
- **Dolt DOWN**: run `gc dolt status`; if stopped, `gc dolt start`.
- **Shuffler lock stale**: check `gc session list` for brief-operator sessions; if none, `rm <city-root>/.beads/briefs/.shuffle.lock`.
- **Molecule +1h == 0 for > 3h**: `gc session peek <session-id>` to confirm. If stuck, report to the human adjudicator.
- **Usage limit hit**: city agents pause on API rate limits. Alert text: "usage limit suspected — agents may be paused. Run /city-status to confirm, then wait or re-nudge sessions."
- **gc status partial or count mismatch**: bug gs-0cy2 — `gc status` probe timed out; reported counts are wrong. Use `tmux -L gt ls` and `gc session list` as ground truth. No action needed unless tmux count is also anomalous.

## What this skill does NOT do

- Does not restart the city (reports only; alerts the invoking session inline)
- Does not close or force-release beads
- Does not delete the shuffler lock without confirming no brief-operator holds it
- Does not push git or run Dolt migrations
