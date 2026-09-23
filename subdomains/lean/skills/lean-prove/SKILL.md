---
name: lean-prove
description: Use when implementing a Lean proof for one aligned theorem or a ready formalization obligation.
---

# Prove one exact obligation

Input: full target type, source sketch, checked prerequisites and workspace.
Output: actual proof with compiler receipts, or the precise remaining goal.

Read the source argument and current Lean context. Reuse the baseline from
`lean-doctor` only for the same snapshot. Keep the target's full signature and
definition context fixed. Search before reinventing facts with `lean-search`.

Implement a small step, inspect the resulting goals/diagnostics, and compile.
Use available LSP tools or the [CLI recipes](../lean-workflow/references/tools.md).
Try tactics appropriate to the actual goal; inspect suggested terms. A different
tactic needs no new plan. A mathematical detour needs a checked dependency
argument and an update to the existing plan, not a silent target change.

On failure use `lean-diagnose`. Missing prerequisites go to `lean-decompose`;
false claims or research gaps return to mathpowers through the coordinator.
Continue independent obligations. Do not hide a gap in a parameter, new axiom,
`sorry`, an altered definition, or unreported trust extension.

After the proof closes, invoke `lean-verify` for the declaration and affected
modules. Return Lean evidence to `lean-fidelity`; do not mark the manuscript
FORMALIZED yourself. Preserve a compact useful mathematical comment, not a
transcript of tactic attempts.

Example: for injective `f` and `h : f (f x) = f x`, use injectivity on `h` to
obtain `f x = x`; compile the application under the actual binder types.
