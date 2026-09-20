---
name: rapid-prototype
description: Combine make-outline and rapid-prototype into an audience-aware introduction to a topic and the whole presentation structure, from a selected research spec or discussion. Use for "outline this", "prototype this", or "rough in the presentation". Supports theorem-first planning with prerequisite backfill; preserves evidence, negative results and explicit proof obligations. Outline-only requests stop at the outline; filling belongs to fill-in-prototype.
---

# rapid-prototype

Use the [synthesis contract](../../../../skills/math-workflow/references/synthesis.md)
for stage ordering, the outline review and later presentation review. This is
the combined outline/prototype leaf, not a separate outline framework.

## Scope and target

Read the selected spec/evidence and resolve the repository's audience, style
and destinations through [RESOLUTION.md](../../../repo-docs/RESOLUTION.md).
Use a permitted scratch Markdown prototype for pre-integration work; never
create an undeclared sibling `.tex`. Scratch workers return candidate text
and evidence, without canonical writer mutations or a canonical postamble.
At requested integration the coordinator runs [WRITERS.md](../../WRITERS.md)
in full against the declared canonical/aspirational target. For a direct
request to insert a prototype, the invoking agent owns that integration.
Reconcile affected rows under [LEDGER.md](../../../repo-docs/LEDGER.md).

## Build the presentation structure

1. Record the audience's assumed knowledge, intended depth and purpose.
   Draft an introduction **to the topic**: the motivating question, why the
   objects arise, a guiding example and the route through the presentation.
   This does not invoke `write-introduction`'s finished-paper/abstract workflow
   or bypass that leaf's explicit-request and evidence gates.
2. Outline the whole presentation: definitions and notation, examples, exact
   statements, proofs or named proof obligations, connections, negative
   findings and remaining questions. Link each item to its spec/source
   locator and prerequisites; give every section a purpose. State audience
   assumptions explicitly rather than silently dropping needed background.
3. For a desired result, put its full target statement first in the planning
   artifact, including all hypotheses, then backfill every prerequisite.
   Mark an unproved target as an obligation. Choose final reading order by
   dependencies and explanatory purpose: definitions precede use, and proof
   dependencies are available or explicitly identified as gaps. Cyclic or
   missing dependencies require resolution, not a reordered assertion.
4. Reorder and plan insertion within the selected target as authorized by the
   synthesis request; retain the item/source relocation map. Give composed
   writers concrete section/label locations. Ask only where scope or a
   repository-reserved decision is unresolved, not for routine ordering
   already authorized. Do not mechanically preserve conversation order.
5. Preserve counterexamples and corrected expectations as planned content
   (LX11/LX12), with evidence and hypotheses. Report their carried/excluded
   counts and authorized exclusion reasons. Unsupported claims stay questions
   or proof obligations in Markdown; TeX claim stubs use attributed conjectures
   or explicitly marked new conjectures per LX4, never fake propositions or
   proofs. A known refutation must not become a fresh conjecture.
6. Use `write-definition`'s content discipline for definition candidates;
   canonical writer calls wait for integration and run their full gates.
   Do not assign a blanket `conjectural` ledger status to supported claims.
   At integration, directly authored TeX stubs use ST5 tags and composed
   writers tag their own regions. Keep workflow statuses agent-side. Cite a
   prototyping method only with opened-source verification.

## Return

Return the prototype path/version, planned locations, source/dependency map,
open obligations and actual checks to the coordinator for the shared outline
review. On a direct invocation, complete that applicable review and end at the
requested outline/prototype; do not begin filling merely because gaps exist.
Within an authorized synthesis, the coordinator consumes this return and
continues to `fill-in-prototype` after the outline review. Outline or source
acceptance does not establish final manuscript acceptance; the shared contract
requires independent review of the integrated result.
