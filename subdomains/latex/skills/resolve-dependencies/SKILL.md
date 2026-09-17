---
name: resolve-dependencies
description: Recursive include-what-you-use for a statement's proof: enumerate every definition and result the proof uses, verify each is present in-document or properly imported, list the gaps, and update ledger depends-on edges. Placement of missing items is a HUMAN question. Use when the user says "resolve dependencies", "what does this proof use", "include-what-you-use", or as pre-promotion hygiene. NOT for writing the missing pieces (composes write-definition per item, human-gated) or hunting sources (track-down-reference).
---

# resolve-dependencies

Runs [../../WRITERS.md](../../WRITERS.md) preamble step 1 (resolution + style variables) only;
write gates apply via the composed writers. This leaf's middle:

## The walk

1. Parse the proof of the target statement: every term, symbol, and
   invoked result. Recurse: dependencies of dependencies, to closure.
2. For each: PRESENT (defined/stated earlier — record label), IMPORTED
   (cited per LX2; at notes tier ST6 wants the proof included — flag
   if bare), or MISSING.
3. Report counts — the instruments-must-fail principle (RESOLUTION.md
   §5), applied to the walk counts: "walked N nodes, P present, I
   imported (J bare at notes tier), M missing".
4. Ledger: write/refresh depends-on edges for every walked claim
   (LEDGER.md format; ledger cache, tex truth).
5. Gaps: recommend WHAT each missing item needs; WHERE it goes is the
   human's call (D5) — on approval, compose write-definition /
   track-down-reference per item.

## Red flags

| Thought | Reality |
|---|---|
| "Everyone knows what a Groebner fan is" | The declared audience decides (STYLE variables), not you. |
| "I'll just insert the missing definition where it fits" | Placement is the human's call. Gap report first. |
