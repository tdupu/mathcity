# Choose mathematical representations

Invoke `using-leanpowers` and take the `lean-design-definitions` route. This is a
DESIGN step: decide, justify, and record. Write no proofs here.

## Search before you define

Take the `lean-search` route first. A definition that duplicates an existing
Mathlib notion is worse than no definition — it forks the ecosystem and orphans
your theorems from every lemma already proved about the standard notion. Report
what you searched for and what you found or ruled out.

## Base-ring gate — check this EARLY

`base_ring_constraint` is **{{base_ring_constraint}}**.

The theory must work over that base. Existing upstream work may assume a field of
characteristic zero, and a representation that quietly assumes QQ where ZZ is
required does not fail loudly — it produces a theory that is true but not the one
asked for, and the error surfaces only after proofs are written.

For each representation, state explicitly whether it holds over
`{{base_ring_constraint}}`. If a target's existing formulation assumes otherwise,
STOP and report it as a design-level obstruction. It may invalidate a roadmap
target, which is a decision for a human, not a thing to route around.

## For each claim in the inventory

- The Lean representation proposed, and the alternatives rejected.
- **Why** this one: which later theorems it makes provable, which it would block.
- Whether it reuses a Mathlib notion or introduces a new one (prefer reuse).
- Typeclass assumptions, stated explicitly.

## Report

The chosen representations with justifications, the base-ring verdict per
representation, and anything you could not decide — say so rather than guessing.
