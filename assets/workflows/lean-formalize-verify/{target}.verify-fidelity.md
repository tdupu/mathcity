# Check the formalization against the source

Invoke `using-leanpowers` and take the `lean-fidelity` route.

## A green build is not fidelity

This step exists because a project can build cleanly and still formalize something
the source never claimed. The build answers "is this valid Lean"; only this step
answers "is this the manuscript's mathematics."

## For each claim in the stage-2 inventory

- Which Lean declaration corresponds to it?
- Does the declaration's statement mean the claim? Compare TEXT to TYPE, not
  declaration name to claim name — a name proves nothing.
- Is it stronger, weaker, or equal? Weaker is the common and quiet failure.
- If no declaration corresponds, is the claim recorded as a gap?

## Verdict

**APPROVING** or **NEEDS-REVISION**, per claim. Do not approve on the strength of
the build. Do not approve a correspondence you established from names alone.
