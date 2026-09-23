---
name: lean-refactor
description: Use when renaming Lean declarations, extracting helpers, splitting modules or restructuring formalization dependencies.
---

# Refactor the formalization API

Input: explicit change scope, dependency/caller map and working baseline.
Output: coherent source changes, updated callers/source map and build evidence.

Identify declarations, imports, attributes, instances, blueprint links and source
labels affected by the change. Plan the smallest dependency-respecting move.
Reuse `lean-decompose` for proof helpers. Preserve shared-witness and mutual-proof
structure; a line-count threshold alone does not justify a new module.

Assign one writer per file. Apply renames and caller changes sequentially where
write scopes overlap; never parallel-edit different declarations in the same
file. Preserve public compatibility or record any intentional API change.
Avoid import cycles and accidental changes of namespace, visibility or instance
scope. Update build roots when adding a module.

Update correspondence to actual qualified names and paths. Build changed
modules and affected consumers; run project validation, then `lean-verify`
and relevant `lean-fidelity`; record current evidence. On failure restore only
owned changes from the captured baseline. Report unresolved downstream uses.

Example: moving a fixed-point definition into `Project.Defs` also updates its
imports, manuscript correspondence and every module that used the old namespace.
