# Extract and enumerate source claims

Invoke `using-leanpowers` and take the `lean-extract-claims` route.

## Scope is bounded and stated

Formalize only `scope_box`. If it is empty, STOP and report that the scope was
never stated — do not infer it from the whole document. An unbounded scope is how
a 7,681-line manuscript becomes an unbounded task.

## What to do

For the bounded section of `source_document`, produce a numbered inventory. Each
entry carries:

- **id** — stable, referenceable (e.g. `C1`, `C2`).
- **statement** — the claim in precise prose.
- **kind** — definition / lemma / theorem / corollary / remark / construction.
- **depends-on** — ids of other claims, or named external results.
- **gap** — anything the source ASSUMES but does not state. Name it explicitly.

## The gaps are the point

A manuscript written for humans leaves steps implicit that Lean will not. Record
every one as a gap entry. Do not silently repair a gap by inventing a hypothesis —
record it, so stage 6 can hold the formalization to the source and so a human can
rule on whether the repair is faithful.

## Report

The inventory, plus a count: N claims, M gaps. State which the source proves and
which it cites externally.
