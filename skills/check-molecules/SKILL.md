---
name: check-molecules
description: Complete molecule accounting across all rigs, classified by status and in order — [A] BEING WORKED ON (in_progress with a live worker session), [B] STRANDED (in_progress with NO worker, frozen — the reclaim backlog that orphan-sweep/lost-bead should catch), and [C] READY (top-level unblocked dispatchable candidates, priority-ranked with the PRIORITIES.md P0 overlay). Writes the full accounting to <city-root>/molecules and prints a capped per-status summary to the terminal, then asks whether there's anything in particular you'd like to see. Status uses the W/P taxonomy (gsp-5pen4l). Use when the user says "check molecules", "check-molecules", "what's being worked on", "account for the molecules", "molecule status", "what's stranded", "what could push-the-fleet dispatch", "list the molecules", or wants a full inventory of fleet work. Read-only — enumerates and reports; never dispatches (that's push-the-fleet) and never adjudicates.
---

# check-molecules

Read-only inventory of the **push-the-fleet candidate set**: every ready,
unblocked, **top-level** bead across all rigs that `push-the-fleet` could pick
up and dispatch via `build-basic-briefed` (policy `gsp-fhdnu`). It is the
"what COULD run" companion to `push-the-fleet` ("make it run") and
`city-status` ("what IS running").

- **Full ranked list → `<city-root>/molecules`** (a file, overwritten each run).
- **Top 20 → the terminal (TUI).**
- Then **ask the user** whether they want anything in particular.

It never dispatches, never closes beads, never edits `city.toml`.

## Pre-flight (P1.14)

The enumeration script probes its dependencies and fails loud if missing:

- `bd` on PATH — the bead store is the source of truth for ready work.
- Dolt reachable (`gc dolt health`) — bd cannot resolve beads otherwise; the
  script tells you to run `gc dolt start` / `gc start`.

The Dolt probe is **three-valued**, not boolean
(`template-fragments/dolt-preflight.md`): exit 0 is healthy, exit **2** means
the server is reachable but a compaction quarantine is standing — non-fatal, so
the script prints a warning naming the quarantined databases and **proceeds**.
Only exit 1 (or a missing `gc`) aborts, with the standard P1.14 message; fix the
dependency and re-run. (Do NOT trust `gc status` for this — bug `gs-0cy2`.)

## Run it

```bash
bash <city-root>/.claude/skills/mathcity.check-molecules/scripts/enumerate-molecules.sh
```

(Skills install under their pack-namespaced directory, hence the `mathcity.`
prefix — `.claude/skills/check-molecules/` does not exist.)

(or the pack path
`<mathcity-pack-root>/skills/check-molecules/scripts/enumerate-molecules.sh`).

Env overrides: `MOLECULES_FILE` (default `<city-root>/molecules`), `MOLECULES_TOP`
(default `20`), `GC_CITY` (default `<city-root>`).

## What counts as a candidate (matches push-the-fleet's filter)

The script sweeps `bd ready` in **every rig** (each dir under `<city-root>` with a
`.beads/`, plus the HQ store), then **excludes** the molecule-internal and
non-dispatchable shapes so the list is genuine top-level work:

- Skipped titles: `Step spec for …`, `input convoy for …`, `drain unit N for …`,
  `Implement owned work`, `Apply starter review …`, `Generate requirements`,
  `Write …` / `Finalize …` / `Run build …` (build-internal steps),
  `Create task beads`, `do-work`, `[epic]` (scheduling containers), and
  `[brief-record]` / `brief-record` (verdict records, not build work).
- Only `status=open` (already-`in_progress` molecules are running, not
  candidates).

**Ranking:** priority ascending (P0 first), then bead id. If
`<city-root>/PRIORITIES.md` exists, beads whose id is listed under its **P0** section
are marked with `★` and floated to the very top (the same overlay
`push-the-fleet` uses).

## Output columns (dispatch-useful)

`RANK · BEAD · P · RIG · ★ · TITLE`. The file header carries the generation
timestamp, total candidate count, and per-rig counts. These are exactly the
fields you weigh before a dispatch; to actually feed them, hand the top of the
list to `push-the-fleet` (which adds the mandatory per-bead scoped
`artifact_root=<rig-root>/.gc-builds/<bead>` — never the bare rig root, or
concurrent builds clobber each other's stage artifacts, `gsp-1bmxuz`).

## After printing the top 20 — ASK (required)

The full list is on disk; the terminal shows only the top 20. **Always finish
by asking the user** whether there's anything in particular they'd like to see,
e.g.:

> Full list written to `<city-root>/molecules` (N candidates). Top 20 shown above.
> **Anything in particular you'd like to see** — a specific rig only, extra
> columns (age / unlock-count / assignee), a different ranking, or the ones
> matching a keyword?

If they name a refinement, re-run with the relevant filter (grep the file, or
re-run the script scoped to one rig dir) and show that view.

## What this skill does NOT do

- ❌ Dispatch anything — that is `push-the-fleet` / `mathcity.work`.
- ❌ Adjudicate or close beads.
- ❌ Trust `gc status` counts (`gs-0cy2`) — it reads the bead store directly.
- ❌ Include in-progress molecules (those are running, not candidates) —
  use `city-status` / the hourly watch for live molecule progress.
