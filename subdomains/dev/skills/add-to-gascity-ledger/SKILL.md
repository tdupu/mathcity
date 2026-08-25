---
name: add-to-gascity-ledger
description: Record a gc-layer problem or lifecycle event into the gascity issue ledger — a gc start / gc stop / gc restart invocation with its time and verbatim output, a supervisor problem (FD leak, reconcile timeout, RSS growth, build identity), a tmux fleet-host failure, a claim or dispatch timeout, or a Dolt data-plane issue — then immediately display the ledger by running gascity-ledger. Trigger on "add to gascity ledger", "record this gc issue", "log this timeout", "record the gc start output", "that's a gascity bug", or whenever a lifecycle command is run.
---

# add-to-gascity-ledger

Record the event or problem, then **immediately run
[gascity-ledger](../gascity-ledger/SKILL.md)**.

Ledger file: `docs/GASCITY-ISSUES.md` (pack-relative).

## When this fires

Standing rule (Taylor, 2026-08-23):

> *"For GASCITY issues I want you to record the time and the output of the `gc stop` and
> `gc start` that we run."*

So: **every** lifecycle invocation, without being asked — and any newly observed `gc`-layer
problem. Timeouts especially. A timeout is a measurement, not a non-event.

If the finding is about an `mcp__mctl__*` command or a skill, it does **not** belong here —
use [add-to-surface-ledger](../add-to-surface-ledger/SKILL.md).

## Which table

| The thing is… | Goes in |
|---|---|
| a `gc start` / `gc stop` / `gc restart` invocation | **Lifecycle command log** (Table 2) as `L<n>` |
| a problem/defect in the `gc` layer | **Problems index** (Table 1) as `<Area><n>` |

Many lifecycle runs produce both: the log entry records *what happened*, and any new defect it
reveals is **promoted** into its own indexed problem. Precedent: L2 (`gc start`) produced
entries A4, A5 and A6. **Promote rather than leave a bug buried in a log entry** — a defect
recorded only inside a command transcript is not findable later.

## Procedure — lifecycle event

1. **Wall-clock time.** If not directly observed (e.g. output was pasted after the fact), record
   a **bound** — `"after 12:44:49, before 12:55"` — and say it was not directly observed.
   **Never present a guess as a reading.**
2. **The exact command**, with the binary path when known. Two `gc` install paths have been live
   simultaneously (A4), so `~/.local/bin/gc` and `~/go/bin/gc` are different facts.
3. **Outcome** — succeeded / failed / in progress, and the resulting city state.
4. **Verbatim output. Do not paraphrase.** The wording is the evidence: `exe=(unreadable)`,
   `start is already in progress`, and `no readiness deadline set` were each load-bearing and
   each would have been lost to a summary. Long outputs go in an `### L<n> detail` block with
   the table cell pointing to it.
5. **Surrounding measurements**, so a restart's effect is measurable rather than asserted:
   supervisor pid, uptime, FD count vs `kern.maxfilesperproc`, RSS, tmux `-L gt` state, Dolt
   listener, last city event seq/time. Take these **before** the command when you can — a
   restart erases the evidence for the thing that caused it.

## Procedure — problem entry

1. **Assign a stable ID**: area letter + next number (`A`=Supervisor, `B`=Fleet host,
   `C`=Claim/dispatch, `D`=Dolt). **IDs are permanent.** Never renumber; other entries and
   sessions cite them.
2. **Status**: `OPEN` · `LIVE` · `RECOVERED` · `RECORD` · `WORKING AS DESIGNED`.
3. **Tracker**: issue number or bead — or the literal **`not filed`**. Never blank.
4. **Owner**: who holds it, or the literal **`unassigned`**. Never blank. A blank owner reads as
   "someone has it"; 14 open P0s sat unassigned for a whole session behind exactly that.
5. **Body**: the mechanism, the measurements that establish it, and a drafted
   **candidate-issue sentence** so it can be filed later without re-deriving the analysis.
6. Add the row to the Problems Index **and** the detail section. Both.

## Rules that keep this ledger trustworthy

**Tag `[measured]` vs `[inferred]`. Never blur them.** A correlation observed once is a
hypothesis and must say so.

**Never merge same-subsystem symptoms without evidence of a shared cause.** Entry A3 exists only
to hold three supervisor events apart. S48 lost hours to a five-way-duplicate P0 cluster built by
merging on subsystem alone. If you believe two entries share a cause, **say what measurement
would show it** rather than combining them.

**`UNKNOWN` where a probe could not run — never `0`.** A diagnostic that cannot pass is as bad as
a check that cannot fail (P6.2).

**Record retractions in place.** If new evidence overturns an earlier entry, correct it visibly
and say what was wrong. Precedent: A1 carries the withdrawal of the ~232/min FD rate, with the
reasoning; C3 carries the withdrawal of "`he-8d6gsg` never claimed".

## Then run gascity-ledger

Invoke [gascity-ledger](../gascity-ledger/SKILL.md). Always, immediately, even for a small
change — the operator should see the current ledger every time it moves.

## Hard stops

- Do not paraphrase command output.
- Do not leave Tracker or Owner blank — use `not filed` / `unassigned`.
- Do not renumber existing IDs.
- Do not record MCP or skill defects here.
- Do not run a lifecycle command yourself. Lifecycle is out of the Mayor's lane; this skill
  **records** what the operator ran.
