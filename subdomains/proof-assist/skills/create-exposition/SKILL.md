---
name: create-exposition
description: Gather the definitions and theorems of a topic into a LINKED markdown spec in scratch — per item: statement, verified source, dependency links — the staging artifact the writers then move into notes.tex. Use when the user says "create an exposition spec", "gather the background on X", "build the linked spec" (the hecke hyperbolic-space pattern). NOT for writing the tex (write-* / explain-experiment) or open-question research (research-SOH / astra-dump).
---

# create-exposition

## Procedure

1. Scope: the topic and target audience (the repo's STYLE variables).
2. Collect the item graph: definitions, theorems, examples the
   exposition needs, each as a spec entry: statement (verbatim or
   faithfully normalized), source — verified via track-down-reference
   for every imported item (opened source, pinpoint) — and
   [[wiki-style]] dependency links between entries (mechanism 10's
   antidote: the reader can walk the graph).
3. Heavy gathering may dispatch per [../../PROVERS.md](../../PROVERS.md); output lands in the
   spec regardless of backend.
4. Deliver `scratch/<date>-exposition-<slug>/spec.md` (+ dump triple);
   ledger rows for imported claims (status `imported`, evidence = the
   verification).
5. Hand off: the spec feeds write-definition / write-proposition /
   write-remark per item, each through its own gates.

## Red flags

| Thought | Reality |
|---|---|
| "I know this theorem, no need to open the source" | Unopened sources are mechanism 7. Verify each import. |
| "Write it straight into notes.tex, skip the spec" | The spec IS the review surface. Writers come second. |
