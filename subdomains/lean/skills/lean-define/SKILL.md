---
name: lean-define
description: Use when an agreed mathematical representation requires new Lean definitions, structures, classes or instances.
---

# Implement a mathematical definition

Input: representation decision and source meaning. Output: actual checked
definitions, behavior checks and any separate API proof obligations.

Read the selected definition context and baseline. Implement only the needed
representation in its declared source module. Name it by mathematical content;
place it before its uses. Keep instances local unless the agreed API needs a
global instance. Never encode an unproved theorem as a structure field or axiom
merely to bypass its proof obligation.

Compile the definition and a meaningful use or defining-equation check. Inspect
coercions, inferred instances and universes. Reuse definitions found by
`lean-search` rather than creating aliases without a consumer. Explicitly record
noncomputability and choice when they affect the intended construction.

Update the [source record](../lean-workflow/references/evidence.md) with the actual
declaration and its meaning. Route properties needing proof to `lean-align-statement`
and `lean-prove`; a definition existing is not proof of its advertised properties.
Changing an existing definition invalidates dependent fidelity evidence.

Example: after defining `FixedBy f x := f x = x`, compile a reflexive unfolding
example. The theorem that every point is fixed under additional assumptions is
a separate obligation.
