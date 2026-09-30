---
name: check-mayor-objectives
description: >-
  Analyse the Mayor session catalog's accumulated `objectives_eval` corpus and
  report how objectives have ACTUALLY gone — completion rates, the
  position-in-the-charge effect, objective-count effects (flagged as
  era-confounded), objectives carried across sessions, and schema defects in
  the corpus itself — then recommend how to size and ORDER the next charge.
  Read-only; never writes the catalog. Use at handoff time when filling
  `objectives_short` / `charge_for_next`, or whenever someone asks "how many
  objectives should I charge", "is three the right number", "why does this
  objective keep getting skipped", "how are we doing on objectives", "check
  mayor objectives", "check-mayor-objectives", "were the objectives
  well-sized". NOT a dispatcher and NOT an adjudicator — it reports and
  recommends only.
---

# check-mayor-objectives

Every Mayor handoff records an `objectives_eval` table: what the previous
session was charged with, whether it landed, and a note on how to improve.
After enough sessions that corpus can answer a question no single seat can —
**what actually predicts an objective getting done.**

Run it:

```bash
CITY_ROOT=<city-root> python3 \
  <mathcity-pack-root>/skills/check-mayor-objectives/scripts/analyze-objectives.py
```

It resolves the catalog from `MAYOR_STATE_DIR`, else `$CITY_ROOT/mathcity-mayor/`,
else `~/HQ/mathcity-mayor/`. Pass a path as `$1` to override. Pure stdlib, no
deps, read-only.

## What it measures, and why the distinction matters

**The POSITION effect is the finding.** It is measured *within* a session —
which slot of the same charge got done — so it is not confounded by era, seat
quality, or how hard that session's work happened to be. On the corpus at the
time of writing (66 rows, 13 sessions, K1–K42) work objectives went

    position 1  69%   position 4  45%
    position 2  50%   position 5  30%
    position 3  64%   position 6   0%

and first-listed vs last-listed was **75% vs 25%**.

**The COUNT effect is reported but must not be quoted bare.** It compares
*different* sessions, so a block of consecutive sessions that shared an
objective count also shared an era and a backlog. The script prints which
sessions sit behind each row precisely so you can check for that before
believing it.

## Separate standing chores from work objectives — this is not cosmetic

A **standing chore** — write the handoff, the run-log shard, the catalog entry —
recurs every session by construction. It is small and mandatory and gets done
wherever it sits. In this corpus chores completed **5/7 regardless of position**.

Leaving them mixed in *hides the thing you are looking for*: the entire
position-6 anomaly in the combined view (67%) was one chore completing 4/4 in
the last slot, while work objectives at position 6 completed **0/2**. Excluding
chores moved the first-vs-last gap from +23 points to **+50**.

The script prints work-only, chore-only, and combined, in that order. **Read the
work-only table.** The combined one is there to show you what the mixed view
would have told you.

## What this is evidence FOR, and what it is not

It supports: *an objective you actually want done goes in position 1.* An
objective that has survived several charges unattempted is not thereby
"unimportant", and is not necessarily "too large" — **it may simply never have
been placed where a seat reaches it.** Move it to position 1 for exactly one
session as a test, or strike it. Carrying a dead objective costs every future
seat the read and teaches the chain that the charge is partly decorative.

It does **not** establish a correct objective count. The chain has carried a
standing "three is the right number" rule; on this corpus the charged-3 evidence
is **two sessions, both at 33%**, while charged-6 sessions average higher and are
mostly one contiguous era. That is not a refutation either — it is a between-
session comparison with a visible confound. **The honest statement is that the
count rule is unsupported by the corpus in both directions**, and the script says
so rather than substituting a new number.

Nothing here is causal. Position may be correlated with how hard or how vague an
objective is, if charges tend to put the clear work first. The corpus cannot
separate those, and the script does not pretend to.

## Corpus schema defects it also reports

The catalog is hand-written each session and has drifted:

- rows using `improvement` where the handoff spec says `improve` — both are
  normalised, and the drift is reported so it can be fixed at the source;
- entries whose `objectives_eval` is a bare string rather than a list — these
  **cannot be read at all** and are excluded from every denominator. The script
  names their sessions so the exclusion is visible rather than a quiet gap.

Recurrence detection matches on the first six words of the objective text, so a
rephrasing between sessions hides a recurrence. **A low recurrence count is weak
evidence of no carrying, not evidence of none** — the script says this inline.

## Re-run it after every handoff

The corpus grows by one session each time, and a rule that held at n=13 may not
hold at n=20. This is cheap; run it while filling `objectives_short`, and put
what it says into the charge rather than into a comment nobody re-reads.
