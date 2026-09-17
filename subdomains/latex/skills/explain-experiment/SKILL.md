---
name: explain-experiment
description: Turn a scratch dump report into notes-tier exposition a hostile reader can FOLLOW — what was computed, why, how, with a re-runnable pointer and provenance. Use when the user says "write up the experiment", "move this report into the notes", "explain the computation in notes.tex". Only proved or verified-computational content becomes statements; conjectural claims stay agent-side or enter as marked conjectures. NOT for literature background (create-exposition).
---

# explain-experiment

Runs [../../WRITERS.md](../../WRITERS.md) preamble and postamble in full. This leaf's middle:

## From report to exposition

- Read the dump (report.md + ai-usage.md): extract the question, the
  method, the result, the verification status per claim (the five-way
  taxonomy — it stays in the ledger).
- The hostile-reader bar (mechanism 10's receipt: "reader can repeat
  the conclusion but cannot follow the stated mechanism" — FAIL):
  the exposition must let a reader RERUN the reasoning — state the
  setup, the mechanism, and what would have falsified it.
- Computation traceability: name the script/notebook path and its
  inputs in a tex comment (ephemeral cache, deletable — D4) and in the
  ledger row (durable).
- Statements: `proved`/verified-`computational` claims may enter per
  write-proposition's rules (composed, its gates); `conjectural` →
  conjecture env or omitted. Prose reporting observations ("for all
  computed cases…") states the computed range exactly.

## Red flags

| Thought | Reality |
|---|---|
| "The report says proved, so it's proved" | Reports are drafts. Ledger + doubt gate decide promotability. |
| "Skip the boring method paragraph" | The mechanism IS the exposition (mechanism 10). |
