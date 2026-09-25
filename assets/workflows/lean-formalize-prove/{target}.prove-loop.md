# Prove the obligations

This node owns the bounded prove/diagnose loop. Its children do the work:

- `prove` — prove one obligation
- `diagnose` — classify and address a failing or stalled goal

## Your job at this node

1. Walk the obligations from `decompose` in dependency order. An obligation whose
   prerequisites are unproved is not ready; do not start it.
2. Run `prove`, then `diagnose` on failure, and repeat — within the bound.
3. The gate on this node is `lean-no-sorry.sh`: it fails while any unrecorded
   `sorry` or `admit` remains in the project.

## The bound is the point

`max_proof_attempts` is a bound, not a suggestion. When it is exhausted, STOP.

The honest output of a hard obstruction is a **recorded obstruction**, not another
tactic. On exhaustion, invoke `lean-frontier-dump` on the stuck goal, which
produces the dump, the named gap entry and the open bead together. All three, or
none — `lean-formalize-verify` reconciles their counts and a `sorry` without its
pair is exactly what that gate catches.

## What must not happen here

- **Do not weaken a statement to close a goal.** Adding a hypothesis changes the
  theorem and invalidates the stage-4 review that approved it. Report the conflict.
- **Do not leave a silent `sorry`.** An unrecorded hole behind a green build is the
  most misleading state a formalization can reach.
- **Do not retry a misclassified failure.** A statement problem or a genuine
  obstruction will not yield to another tactic; retrying one is the most common way
  this loop burns its whole bound for nothing.

## Report

Per obligation: proved / recorded-gap / blocked, with the build command and its
exit code. Then the loop's totals, and whether the bound was reached.
