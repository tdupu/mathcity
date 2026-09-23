# Translate the claim into a Lean statement

Invoke `using-leanpowers` and take the `lean-align-statement` route. Write the
STATEMENT only. Use `sorry` for the proof body.

## The target

Claim `{{claim_id}}` from the stage-2 inventory. Its prose statement and its
recorded gaps are your input.

## What to do

1. Take the `lean-search` route first — the theorem may already exist in Mathlib,
   in which case say so and stop. Proving it again is waste.
2. Write the full Lean type: every hypothesis, every quantifier, every typeclass.
3. For each gap recorded in stage 2, state how you handled it — as an explicit
   hypothesis, as a typeclass assumption, or not at all. A gap that silently
   became a hypothesis makes the theorem weaker than the source claimed.

## The failure this step exists to prevent

A statement that elaborates is not a statement that is right. `∀ n, P n → Q n` is
vacuously provable when `P` is never satisfiable, and Lean will happily accept it.
State any hypothesis that could be vacuous, and say why it is not.

## Report

The Lean statement with `sorry`, the claim it formalizes, how each gap was handled,
and an explicit note on any hypothesis that could be vacuously satisfied.
