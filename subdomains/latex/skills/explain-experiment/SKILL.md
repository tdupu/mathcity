---
name: explain-experiment
description: Turn a scratch dump report into notes-tier exposition a hostile reader can FOLLOW — what was computed, why, how, with a re-runnable pointer and provenance. Use when the user says "write up the experiment", "move this report into the notes", "explain the computation in notes.tex". Only proved claims — or computational claims whose ledger row carries a SOUND doubt run — become statements; conjectural claims stay agent-side or enter as marked conjectures. NOT for literature background (create-exposition).
---

# explain-experiment

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full. This leaf's middle:

## From report to exposition

- Read the dump (report.md + ai-usage.md): extract question, method,
  result, and per-claim verification status (the taxonomy stays in
  the ledger).
- The hostile-reader bar (mechanism 10's receipt: conclusion
  repeatable, mechanism unfollowable = FAIL): the exposition must let
  a reader RERUN the reasoning — setup, mechanism, and what would
  have falsified it.
- Traceability: name the script/notebook path and its
  inputs in a tex comment (ephemeral cache, deletable — D4) and in the
  ledger row (durable).
- Statements: `proved` claims — and computational claims whose ledger
  row carries a SOUND doubt run — enter per write-proposition
  (composed, its gates); `conjectural` → conjecture env or omitted.
  Observation prose ("for all computed cases…") states the computed
  range exactly.

- Concrete cases use `write-example`; figures use `generate-graphics` and
  `add-figure` when they explain the result. Carry graph/axis semantics and
  exact versus numerical scope through the caption; link the example and
  figure instead of repeating the derivation.

## Red flags

| Thought | Reality |
|---|---|
| "The report says proved, so it's proved" | Reports are drafts. Ledger + doubt gate decide promotability. |
| "Skip the boring method paragraph" | The mechanism IS the exposition (mechanism 10). |
