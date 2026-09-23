---
name: lean-upgrade
description: Use when a Lean or Mathlib version change is requested or an explicitly requested upgrade causes compatibility failures.
---

# Migrate a pinned Lean environment

Input: requested target revision, current workspace and authorized scope.
Output: new coherent pins, repaired source and before/after verification.

Run `lean-doctor` and record the current toolchain, manifests, dirty files and
build evidence. Resolve the requested revision concretely; “latest” requires a
current lookup and recording the resulting commit. Do not upgrade as an
incidental response to a proof failure.

Preserve an owned baseline. Select the matching Lean version from the target
dependency, update the intended lakefile/lockfile using that project's supported
commands, and fetch available compatible caches. Diagnose API changes from
actual errors and upstream definitions with `lean-diagnose`/`lean-search`.
Repair incrementally without weakening theorem statements or changing source
meaning merely to compile.

Build all selected modules and affected consumers. Run `lean-verify` and fresh
`lean-fidelity` where definitions or semantics changed. Mark prior receipts
stale. If migration fails, report exact blockers and restore only owned edits
when restoration is requested or necessary; never reset unrelated work.

Example: a renamed library lemma needs checked replacement and callers, while
a changed mathematical definition may require a separate correspondence decision.
