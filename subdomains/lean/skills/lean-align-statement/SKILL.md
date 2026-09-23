---
name: lean-align-statement
description: Use when translating a mathematical assertion into a Lean type or checking a proposed formal statement before proving it.
---

# Align the exact statement

Input: source claim, checked definitions and representation decision.
Output: elaborated Lean signature, binder-to-source mapping and discrepancies.

Read [source mapping](../lean-workflow/references/source-map.md). State the exact
domain, universes, quantifier order, hypotheses, instances and conclusion. Check
definitions, coercions, equality and empty/degenerate cases. Compare the full
elaborated type, not just the displayed theorem line.

Elaborate the signature in a clearly marked scratch skeleton or authorized
incomplete source. A temporary `sorry` makes its status STATED, never proved.
Use `lean-search` for library formulations; compile an application or conversion
when claiming equivalence. Missing definitions go to `lean-define`.

List extra assumptions and missing directions explicitly. If the proposed type
is weaker, conditional or mathematically ambiguous, return the mismatch before
dependent proof work. Keep a corrected theorem distinct from the original claim.
Pass the stable target and source record to `lean-decompose`/`lean-prove`.

Example: `∃ x, P x ∧ Q x` requires the same witness for both properties;
two separate existential theorems do not align with it.
