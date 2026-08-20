---
schema: gc.build.implementation-summary.v1
workflow:
  id: gsp-kwyfx
  formula: do-work
methodology:
  pack: gascity
  name: build-basic
producer:
  formula: do-work
  stage: implement
  attempt: 1
status: approved
trace:
  upstream:
    - path: beads/gsp-gvx21
      hash: bead:gsp-gvx21
      ids:
        - REQ-003
    - path: mathcity/formulas/build-basic-worktree-gated.formula.toml
      hash: sha256:47a55f3a07e62a393bde31e5e9d93d287ec0ef28814853e9715cf4ad8e20bdd7
  coverage:
    - id: REQ-003
      status: covered
---

## Summary

Created `mathcity/formulas/build-basic-worktree-gated.formula.toml`. This formula
extends `build-basic` and overrides only the `implement` drain step to use
`do-work-worktree-gated` instead of `do-work`. All other `build-basic` steps
(requirements, plan, plan-review, decompose, implement-same-session, review,
finalize, publish) are inherited unchanged.

| ID | Status |
| --- | --- |
| REQ-003 | covered |

## Intended Behavior

`build-basic-worktree-gated` is a drop-in variant of `build-basic` that adds
a git pre-commit hook gate on every implementation worker worktree. Workers that
attempt to commit staged paths outside `GC_ITEM_WORKTREE` will be rejected by
the hook, enforcing isolation at the commit layer. The formula differs from
`build-basic` only in the drain formula name on the `implement` step
(`do-work-worktree-gated` vs `do-work`).

## Changed Files

| File | Change |
| --- | --- |
| `mathcity/formulas/build-basic-worktree-gated.formula.toml` | Created (23 lines, commit 3f325e7) |

## Verification

TOML parse (Python `tomllib`): **PASS** — `formula=build-basic-worktree-gated`, `extends=[build-basic]`, `steps[0].drain.formula=do-work-worktree-gated`

SHA256 of committed file: `47a55f3a07e62a393bde31e5e9d93d287ec0ef28814853e9715cf4ad8e20bdd7`

Structural diff from `build-basic` (only `implement` drain formula changed):
```
-formula = "do-work"
+formula = "do-work-worktree-gated"
```
All other fields on the overridden step are identical to `build-basic`.

## Remaining Risks

- `do-work-worktree-gated` formula is committed in a separate worktree (gsp-3rsdk,
  commit 2f0784f); both must land in the same merge before `gc formula validate
  build-basic-worktree-gated` can run end-to-end. The verify step (gsp-suiv8)
  covers this.
