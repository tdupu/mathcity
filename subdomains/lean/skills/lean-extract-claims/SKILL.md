---
name: lean-extract-claims
description: Use when a natural-language proof, manuscript or selected theorem needs a formalization inventory.
---

# Extract the mathematical obligations

Input: selected source and scope. Output: source/claim/dependency records under
the [evidence contract](../lean-workflow/references/evidence.md).

Read [source mapping](../lean-workflow/references/source-map.md), then the actual
statements, definitions and full proofs. Preserve source labels; supply explicit
IDs for unlabeled user arguments. Record objects, hypotheses, quantifiers,
conclusions, conventions, references and dependencies. Include negative results
and counterexamples. Distinguish requested claims from supporting obligations.

Expand “clearly”, “by compactness” and similar skipped steps into explicit
obligations. Mark missing sources and ambiguous interpretations. Do not assume
the conclusion to make the map complete, invent citations, or silently correct
the manuscript. Route mathematical gaps to `using-mathpowers` under the same
claim IDs; continue independent claims where possible.

Return coverage: every selected source assertion has a record, including those
not yet formalized. Definitions feed `lean-design-definitions`; claims then
feed `lean-align-statement` and `lean-decompose`.

Example: “cancel n” in `n / n = 1` over natural numbers exposes the missing
nonzero condition and the zero counterexample; it does not authorize adding a
hypothesis while retaining a completed status for the original claim.
