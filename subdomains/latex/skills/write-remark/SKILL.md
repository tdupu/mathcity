---
name: write-remark
description: Draft ONE remark — expository connective tissue — into the repo's canonical tex file. Use when the user says "add a remark", or when explain-experiment needs a bridging observation. A remark that asserts a checkable mathematical claim is NOT a remark: route to write-proposition. Inherits all writer gates.
---

# write-remark

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full. This leaf's middle:

## Drafting

- Remark environment per STYLE.md. Content: motivation, connection,
  caveat, or attribution — prose a hostile reader can follow
  (mechanism 10's bar), at the declared terseness.
- The claim test: if any sentence has a truth value a referee could
  demand a proof for, it is not remark material — stop and route to
  write-proposition (with evidence) or rapid-prototype (as conjecture).
- Attributions inside remarks still cite per LX2 through
  track-down-reference.

## Process is not mathematics

A remark records mathematics, never the project's history. Never write
"an earlier draft asserted", "in a previous version", "this was
originally stated without", "we initially believed", or any sentence
whose subject is the manuscript rather than its objects. The reader is
owed the result, not the route.

This is the environment where such prose accumulates, because it is the
only theorem-class environment with no counterpart in a proof assistant:
a definition is a `def`, a proposition is a `theorem`, and a remark is
nothing — so nothing constrains it. Treat that as a warning, not a
licence.

LX11/ST11 are discharged by the mathematics, not by the narration. When
prior work refuted a claim, state the refutation as a labelled result
and name the corrected expectation in mathematical terms — "it is
natural to expect $X$; in fact $Y$, by Example~\ref{...}". That names
the expectation without narrating the draft that held it. If the claim
failed because it conflated several inequivalent notions, the repair is
not a remark at all: define the notions and state the theorem saying
when they agree (write-definition, then write-proposition).

Where process genuinely must be recorded — what was tried, what a model
produced, what an earlier run got wrong — it belongs to the repository's
AI-assistance/disclosure section and the `ai/` work records, never to
the mathematical body.

## Red flags

| Thought | Reality |
|---|---|
| "It's just a remark, the gates are overkill" | Remarks ship in the same PDF. Same gates. |
| "Easy to see that X holds — as a remark" | That is a claim in costume. Proposition path. |
| "ST11 says carry the refutation forward, so I'll record what the old version claimed" | ST11 wants the refutation as mathematics. The old version is not mathematics. |
| "A short note on how we got here orients the reader" | It orients the author. AI-assistance section. |
