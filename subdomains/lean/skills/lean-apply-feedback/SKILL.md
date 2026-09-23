---
name: lean-apply-feedback
description: Use when applying review comments to Lean code or reconciling requested formalization corrections.
---

# Resolve Lean review feedback

Input: complete comment set, exact source revision and authorized change scope.
Output: checked local fixes, one disposition per comment and unsent draft replies.

Read each comment with its surrounding code and mathematical context. Use stable
comment IDs or supplied item numbers. Classify requests as correctness, fidelity,
API, style, performance or clarification. Verify the reviewer's premise using
`lean-search`, `lean-verify` or `lean-fidelity` where appropriate; do not implement
every suggestion blindly.

Apply justified changes within scope in dependency order with one writer per
file. Route specialized work to the matching leaf. Rebuild affected targets and
refresh evidence. Preserve unrelated edits and record attempted changes that
were reverted after a failing check.

Return a complete disposition map: resolved, already satisfied, declined with
evidence, or blocked with the exact question. If comments were fetched from a
live PR and access is available, recheck for new items before claiming coverage.
Draft concise replies and a change summary. Sending, committing and pushing are
separate coordinator actions requiring their existing authorization.

Example: a requested generalization is accepted only after its new statement,
source specialization and downstream applications are checked.
