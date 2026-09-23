---
name: lean-search
description: Use before proving or defining Lean material, or when a proof needs a reusable library lemma, instance or equivalent formulation.
---

# Find and check reusable mathematics

Input: mathematical requirement, typed goal and pinned workspace.
Output: candidates with actual types/imports, compiled applications and search
coverage; or a bounded unresolved API gap.

Search local project and dependency sources by concept, type shape, naming
variants and neighboring declarations. Inspect more general formulations and
automatically generated or typeclass-derived facts. Follow
[search tools](../lean-workflow/references/search-tools.md): discover actual
MCP schemas, use LeanSearch for natural-language queries and Loogle for names
or types. Installed `search-mathlib` can supply hosted lookup; pass already
searched/unavailable channels so fallback cannot recurse. Missing services or
LSP version incompatibility leave the pinned local CLI usable.

## Source routing

LeanSearch is a Mathlib retrieval channel, not a general registry search API.
For requests about prior formalization or reusable declarations, search the
target project and Mathlib first, then fan out to the bounded sources below
when they are relevant:

| Source | Use it for | Required receipt |
|---|---|---|
| Palomar Registry | Registered Lean-verified results and named declarations from independent projects | Permanent `PALOMAR-*` id, integer version, entry URL, source repository and pinned commit |
| Tau Ceti | Existing declarations, local API patterns, roadmap targets and repository precedents | Repository name, exact commit, file/module path, and whether the result came from code, roadmap, generated docs or review material |

Do not send Palomar or Tau Ceti prose to `lean_leansearch` as though the
hosted Mathlib corpus had been extended. Query those sources through the
machine-readable or pinned-repository routes in the search-tools reference,
then use LeanSearch/Loogle or a local Lean project for the actual reusable
declaration search.

For a Palomar hit, treat the registry as discovery and provenance evidence.
Fetch the versioned record, inspect its theorem names and source commit, then
check out or otherwise inspect that exact source snapshot before claiming that
an import or declaration applies to the target project. A registered result is
not automatically a Mathlib theorem, a novelty claim, or a proof of the
current target.

For Tau Ceti, search the pinned `TauCetiProject/TauCeti` checkout for code and
the separate `TauCetiRoadmap` checkout for human-owned targets. Generated API
docs are useful navigation only; use the published `docs/SOURCE_SHA` or the
repository commit when freshness matters. A roadmap statement or review
verdict is source/process evidence, not a Lean certificate.

For a Stacks source or missing informal prerequisite, use installed
`search-stacks` or the documented direct fallback. Fetch the actual tagged
statement/proof and preserve hypotheses and source location. A Stacks proof is
informal evidence; align it and discharge its Lean prerequisites separately.

Follow [tool recipes](../lean-workflow/references/tools.md): `#check @name` under
the actual project pin, then compile a small application at the desired goal.
An online hit or source substring alone does not establish applicability.
Where supported, probe `exact?`/`apply?` and instance inference; inspect suggested
proof terms before adopting them.

Record queries, sources searched, unavailable channels, verified names, imports
and hypothesis differences. Neither failed search nor failed automation proves
absence or novelty. Return reusable results to the caller; a genuine remaining
mathematical obligation goes through `lean-decompose` or mathpowers.

For federated searches, also record each source's snapshot, the exact external
locator, and the verification state: `candidate`, `locally checked`,
`stale/unavailable`, or `not applicable`. Keep external candidates separate
from declarations checked under the target project's Lean and Mathlib pins.

Example: a theorem about a concrete ring may already follow from a general
monoid lemma. Verify the specialization instead of duplicating the theorem.
