---
name: lean-fidelity
description: Use when checking that Lean declarations represent a manuscript or natural-language claim, especially before formalization completion or after definition changes.
---

# Review source correspondence

Input: source map, current source/Lean snapshot and compiler evidence.
Output: per-claim MATCH, MISMATCH, UNRESOLVED or STALE, with reasons.
This is a read-only semantic review.

Read [source mapping](../lean-workflow/references/source-map.md) and the full
current source statement/definitions. Inspect the entire elaborated Lean type,
implicit binders, instances, coercions and custom definition bodies. Explain the
Lean assertion in ordinary mathematics before comparing it with the source.

Check quantifier order, domains, missing directions, shared witnesses, boundary
cases, extra finiteness/nonzero/nonempty assumptions and circular hypotheses.
A weaker specialization does not certify a stronger manuscript theorem.
Conversely, a checked generalization may certify the source via a checked
specialization. Follow dependencies where their meaning is load-bearing.

Verify the evidence snapshot is current. Distinguish a manually reconstructed
dependency graph from compiler-derived evidence. A rebuild cannot renew a
semantic review after relevant definitions change. Report ambiguity or missing
source explicitly; do not edit the manuscript to make a mismatch disappear.

Return discrepancies to the coordinator: `lean-align-statement` for encoding,
mathpowers for mathematical gaps, latexpowers for authorized manuscript changes.
Only a current MATCH plus passing `lean-verify` permits FORMALIZED status under
the [evidence contract](../lean-workflow/references/evidence.md).
