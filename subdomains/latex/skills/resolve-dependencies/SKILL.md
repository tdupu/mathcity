---
name: resolve-dependencies
description: Recursive include-what-you-use for a statement's proof: enumerate every definition and result the proof uses, verify each is present in-document or properly imported, list the gaps, and update ledger depends-on edges. Placement of missing items is a HUMAN question. Use when the user says "resolve dependencies", "what does this proof use", "include-what-you-use", or as pre-promotion hygiene. NOT for writing the missing pieces (composes write-definition per item, human-gated) or hunting sources (track-down-reference).
---

# resolve-dependencies

Runs [../../WRITERS.md](../../WRITERS.md) preamble (read-only leaf: the postamble's write steps
apply only when composition inserts something). This leaf's middle:

## The walk

1. Parse the proof of the target statement: every term, symbol, and
   invoked result. Recurse: dependencies of dependencies, to closure.
2. For each: PRESENT (defined/stated earlier in the document — record
   label), IMPORTED (cited per LX2; at notes tier ST6 wants the proof
   included — flag if bare), or MISSING (a gap).
3. Report counts (RESOLUTION.md §5 in `subdomains/repo-docs/`): "walked
   N nodes, P present, I imported (J bare at notes tier), M missing".
4. Ledger: write/refresh depends-on edges for every walked claim
   (LEDGER.md format; ledger is cache, tex is truth).
5. Gaps: for each missing item, recommend WHAT is needed; WHERE it goes
   is presented to the human (D5) — on approval, compose
   write-definition / track-down-reference per item.

## Red flags

| Thought | Reality |
|---|---|
| "Everyone knows what a Groebner fan is" | The declared audience decides (STYLE variables), not you. |
| "I'll just insert the missing definition where it fits" | Placement is the human's call. Gap report first. |
