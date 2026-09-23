---
name: lean-generalize
description: Use when explicitly investigating weaker Lean theorem assumptions, broader types or a more reusable mathematical formulation.
---

# Test a genuine generalization

Input: current declaration, source claim and intended API scope.
Output: tested candidate, per-hypothesis reasoning and source specialization.

Record the original full type and callers. Classify each hypothesis and instance;
inspect explicit and inferred uses. Search existing broader formulations with
`lean-search`; route substantive literature questions to mathpowers.

Test one weakening at a time in scratch: drop an unused assumption, use a
verified parent structure, localize a global premise or broaden the carrier.
Compile the candidate and its applications. Merely replacing a definition with
an easier one is not generalization; confirm the candidate entails the source
claim via an actual checked specialization.

Apply changes within the requested scope. A choice that changes the intended
mathematics or exceeds that scope returns to the coordinator for resolution.
Keep the source correspondence interface where useful. Recheck callers,
`lean-verify` and `lean-fidelity`; invalidate old evidence after changed meanings.
Return failed trials as evidence, not claims of maximal possible generality.

Example: a proof using only multiplication and identity may work for a monoid;
verify the weaker instance assumptions and the original ring specialization.
