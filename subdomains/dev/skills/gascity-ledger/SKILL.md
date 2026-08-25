---
name: gascity-ledger
description: Show the gascity issue ledger — exactly two tables, the problems index and the lifecycle command log, covering gc start / gc stop / gc restart failures, supervisor problems (FD leaks, reconcile timeouts, identity), tmux fleet-host absence, claim latency, timeouts, and Dolt data-plane issues. Trigger on "gascity-ledger", "gascity issues", "show the gascity ledger", "what's wrong with gc", "supervisor problems", "lifecycle log".
---

# gascity-ledger

Display the gascity issue ledger. **Two tables. Nothing else.**

Ledger file: `docs/GASCITY-ISSUES.md` (pack-relative).

## Scope — what belongs in this ledger

Problems in the **`gc` layer**, not the mathcity pack:

- lifecycle — `gc start`, `gc stop`, `gc restart`, and every **timeout** they produce
- supervisor — FD leaks, reconcile stalls, RSS growth, build identity, process replacement
- fleet host — missing tmux server, spawn failures, `gc status` blindness
- claim / dispatch — claim latency, claim-window overruns, orphan sweeps, finalize deadlocks
- data plane — Dolt outages, restart churn, port/state-file loss, store health

The dividing line is #98's own wording: *"This is gc source behaviour, not a mathcity pack
change; the fix belongs to whoever owns gc."* MCP tools and skills go to
[surface-ledger](../surface-ledger/SKILL.md) instead.

## Table 1 — Problems index

| Column | Content |
|---|---|
| ID | `A1`, `B2`, `C4`… — area letter + number, stable forever |
| Area | Supervisor · Fleet host · Claim · Dolt |
| Problem | the mechanism in one sentence |
| Status | `OPEN` · `LIVE` · `RECOVERED` · `RECORD` · `WORKING AS DESIGNED` |
| Tracker | issue number, bead id, or **`not filed`** |
| Owner | who holds it, or **`unassigned`** |

**`not filed` and `unassigned` must be rendered literally, never as a blank.** A blank owner
reads as "someone has it". The most consequential fact this ledger has ever carried is that 14
open P0s had zero assignees for an entire session while five agents rediscovered one of them.

## Table 2 — Lifecycle command log

Standing rule (Taylor, 2026-08-23):

> *"For GASCITY issues I want you to record the time and the output of the `gc stop` and
> `gc start` that we run."*

| Column | Content |
|---|---|
| # | `L1`, `L2`, … in order |
| Time (EDT) | wall clock. If not directly observed, a **bound** — never a guess styled as a reading |
| Command | the exact invocation, with the binary path when it is known |
| Outcome | succeeded / failed / in progress, and the resulting city state |
| Verbatim output | the output **unparaphrased** |

Long outputs live in an `### L<n> detail` block below the table with the table cell pointing at
it. **The wording of the output is the evidence** — never summarise it away.

## Procedure

1. **Reconcile first.** Any lifecycle command run, or `gc`-layer problem observed, since the last
   reconcile gets its row now. A ledger displayed without reconciling is displayed as current
   when it is not.
2. **Read `docs/GASCITY-ISSUES.md`.** It is canonical. Do not rebuild either table from memory.
3. **Print the problems index, then the lifecycle log.** Nothing else — not the detail sections,
   not the conventions, not the changelog.
4. Follow with a one-line tally: how many problems are OPEN, how many **not filed**, how many
   **unassigned**.

## Rules that keep this ledger trustworthy

**Never merge same-subsystem symptoms without evidence they share a cause.** Entry `A3` exists
solely to hold three supervisor events apart — a cap self-termination, a tmux death the
supervisor survived, and a stop-reconcile timeout it also survived. S48 lost hours to a
five-way-duplicate P0 cluster assembled exactly by merging on subsystem.

**Tag `[measured]` vs `[inferred]` and never blur them.** A correlation seen once is a
hypothesis. Say which it is in the row.

**`UNKNOWN` is a valid value and is required where a probe could not run.** Never `0`. A probe
that could not run reports `unknown` (P6.2).

## Related

- [add-to-gascity-ledger](../add-to-gascity-ledger/SKILL.md) — record an event or problem, then run this skill
- [surface-ledger](../surface-ledger/SKILL.md) — the sibling ledger for MCP commands and skills
