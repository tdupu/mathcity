# Diagnose a failing or stalled goal

Invoke `using-leanpowers` and take the `lean-diagnose` route.

## Distinguish the three causes — they have different remedies

1. **A proof-engineering problem** — right statement, wrong tactic. Fix and retry.
2. **A statement problem** — the goal is unprovable as stated, or vacuous. Return
   to stage 4. Do NOT patch it here; a statement edit must be re-reviewed.
3. **A genuine mathematical obstruction** — the result needs theory the project and
   Mathlib do not have. This is not a retry candidate.

Naming which of the three you are looking at IS the work of this step. Retrying a
type-2 or type-3 failure with a different tactic is the most common way sessions
are wasted here.

## Bound

`max_proof_attempts` is **{{max_proof_attempts}}**. On exhaustion, stop and invoke
`lean-frontier-dump` on the stuck goal. An honest recorded obstruction is a better
outcome than an unbounded retry, and it is what lets a human decide.

## Report

Which of the three causes, the evidence for that classification, and either the fix
applied or the frontier dump produced.
