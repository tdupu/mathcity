---
name: create-exposition
description: Gather selected frontier-dump packages or related research files into a source-aware Markdown exposition spec, preserving exact provenance, dependencies, uncertainty and negative findings. Use for "create an exposition spec", "gather the background on X", or the gathering phase of research synthesis. File-based; no browser prerequisite. Does not itself draft the presentation or solve open questions.
---

# create-exposition

The [synthesis contract](../../../../skills/math-workflow/references/synthesis.md)
owns the end-to-end stages and reviews. This leaf gathers the spec; a direct
invocation ends there. Under synthesis, return it to the coordinator for the
outline/prototype phase. Read files directly, without browser automation or
a live conversation prerequisite.

## Gather the selected evidence

1. Resolve repository contracts through
   [RESOLUTION.md](../../../repo-docs/RESOLUTION.md). Record topic, audience,
   assumed background, depth, intended output and the exact selected
   paths/sections in the existing run spec. A selection may be a subset or the
   whole corpus; use the coordinator's selection, or infer and name one from
   the request. Clarify only ambiguity that changes the presentation's scope.
2. Read selected originals, corrections, proof/source attachments and relevant
   existing text. Record coverage and unavailable inputs; partition large
   inputs without treating summaries as fully read evidence. Dependencies
   outside the selection remain named gaps until their inclusion is
   authorized; neighboring files are not implicitly selected.
3. Build `spec.md` in the repository-permitted run/scratch directory, retaining
   earlier versions. Use linked entries for definitions, exact claims with
   all hypotheses, proof arguments, examples and explanatory connections.
   Each entry maps back to an exact path plus section/line/page/result locator
   and source version where available; link the evidence and prerequisite
   entries. Keep conflicting formulations and distinguish source assertions
   from checked arguments. Never strengthen a claim while normalizing it.
4. Enumerate refutations, counterexamples, ill-posed proposals and failed
   expectations first (LX11/LX12). Preserve the expectation corrected, the
   actual finding, its hypotheses and supporting evidence. Record each
   omission with its authorized scope reason; dropping both a false claim
   and its refutation loses a result. Missing proof remains an open question,
   not an established negative result.
5. Separate research provenance from mathematical citation: a dump identifies
   where an idea came from, not a verified primary reference. Carry opened-
   source pinpoint verification from `track-down-reference`, or use its
   opening and hypothesis-match procedure on supplied local sources. Missing
   sources leave an import-verification gap for the coordinator; this
   gathering phase does not browse or launch fresh research.
   Route conflicts through `contradiction-check` before dependent promotion.
   Reconcile any claim rows read or updated under
   [LEDGER.md](../../../repo-docs/LEDGER.md); reuse that ledger, not a new status
   database. Unsupported source labels do not establish ledger status.

## Return

Return the spec path, selected-source coverage, dependency/verification gaps,
conflicts, and counts of negative findings carried or excluded with reasons.
The spec is the review surface for `rapid-prototype`; it does not authorize
TeX edits or certify any claim as proved. Return candidate text/evidence only;
canonical writer mutations belong to the coordinator's integration stage.
The coordinator resumes the shared synthesis sequence with these artifacts.
