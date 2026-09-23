---
name: lean-blueprint
description: Use when creating or synchronizing a formalization blueprint, Lean declaration links or a proof dependency presentation.
---

# Synchronize blueprint evidence

Input: current claim graph, source map and declared blueprint destination.
Output: checked declaration/dependency links and scope-accurate status updates.

Inspect the existing format and build. Preserve LaTeX leanblueprint, Verso or
other declared conventions; do not impose a new renderer or publishing service.
For a new blueprint use the requested format, resolving a material format choice
with the coordinator before adding infrastructure.

Map each selected claim to actual qualified Lean declarations. Check every
dependency edge and distinguish manually described structure from verified
formal dependencies. Derive completion marks from current `lean-verify` and
`lean-fidelity` evidence, never from declaration existence or a `sorry` skeleton.
Invalidate marks affected by changed statements or definitions.

This leaf owns synchronization data. LaTeX mathematical prose and statement
edits route to `using-latexpowers` and its writer under the same plan, claim IDs
and authorization. Pure link/status metadata may be edited here when local
contracts permit it. Build with the repository's actual command and inspect
unresolved links. Report partial scope; do not deploy the rendered site.

Example: an existing theorem label keeps its identity while its Lean link
changes after an authorized module rename; its proof status is rechecked.
