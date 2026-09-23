---
name: lean-mathlib-fit
description: Use when assessing whether a Lean declaration is suitable for Mathlib or whether existing library material already supplies it.
---

# Assess library fit

Input: verified declaration, mathematical context and target Mathlib revision.
Output: a supported fit verdict and concrete evidence; this leaf is read-only.

Understand the statement and its consumers. Use `lean-search` on the actual and
plausibly general forms; compile candidate replacements. Check whether an
existing definition, instance-derived fact or short composition already supplies
the mathematical content. Route literature and substantive formulation questions
through mathpowers with focused scope.

Assess useful generality, naming, normal forms, representation duplication,
instance/coercion diamonds, API stability and proof strategy. A manuscript-facing
wrapper may be useful locally without being an upstream candidate. Expense does
not itself make useful mathematics unsuitable.

Return one verdict with evidence: **existing result**, **composition sufficient**,
**candidate as stated**, **candidate after specified generalization**, or
**uncertain**. Name verified declarations and the proposed library gap. Give a
checked weakening for a generalization verdict; do not infer novelty from failed
searches or promise acceptance by maintainers.

A submission request continues to `lean-prepare-pr`. External discussion or PR
creation requires its own authorization; this assessment sends nothing.
