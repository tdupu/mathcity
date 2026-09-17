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

## Red flags

| Thought | Reality |
|---|---|
| "It's just a remark, the gates are overkill" | Remarks ship in the same PDF. Same gates. |
| "Easy to see that X holds — as a remark" | That is a claim in costume. Proposition path. |
