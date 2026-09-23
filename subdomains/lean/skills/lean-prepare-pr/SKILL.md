---
name: lean-prepare-pr
description: Use when preparing a Lean or Mathlib contribution for review, submission readiness or a local PR package.
---

# Prepare a reviewable Lean contribution

Input: selected diff, intended destination and source/build evidence.
Output: a local submission package and remaining readiness findings.

Read the target repository's current contribution rules and PR template.
Summarize the concrete mathematical result and why the API belongs there.
Use `lean-mathlib-fit` when Mathlib inclusion is intended. Confirm source/license
attribution, useful documentation, imports, statement shape and compatible pins.

Run `lean-style`, `lean-review`, `lean-verify` and `lean-fidelity` as applicable
to the current snapshot. Account for every finding; keep scope bounded and
separate conditional claims. Describe relevant validation and known limitations
in a concise draft PR body with dependency information.

Return the exact files/diff, draft title/body, command receipts and unresolved
items. Follow the active repository's identity and git rules. This leaf does
not itself commit, push, post comments or create a PR; an explicitly authorized
submission is a subsequent coordinator action on this reviewable package.

Example: a passing local build with a remaining source mismatch is a readiness
finding, not a reason to describe the patch as a completed formalization.
