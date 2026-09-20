# Research files to a coherent presentation

Parent: [math-workflow](../SKILL.md). Both powers routers use this sequence
when the user wants selected research assembled into an exposition. Resume
at the requested stage; an outline-only request stops at the reviewed outline.
One coordinator owns selection, dependencies, reviews and final integration.
[execution.md](execution.md) owns backend/path preflight, delegation, shared
limits, conflict investigation/adoption and partial-stub delivery. No browser
conversation is required.

## Select and gather

Use [create-exposition](../../../subdomains/proof-assist/skills/create-exposition/SKILL.md)
to gather context from the chosen frontier dumps or related files. Record the
topic, audience, assumed background, intended depth, requested output and exact
selected paths/sections in the existing run plan or spec. The selection may be
the whole corpus. Infer a reasonable selection from an explicit topic and name
it; clarify only ambiguity that changes the intended presentation. Unselected
material does not become evidence merely because it is nearby.

Read selected originals, including corrections, refutations and source/proof
attachments needed by their claims. If the corpus is too large, partition the
reading and retain source locators and coverage; never label an unread summary
as full context. An excluded dependency is a gap to resolve, not permission to
silently expand scope. Record any newly authorized selection explicitly.

Keep a compact source-to-item map in `spec.md`: exact statements/hypotheses,
definitions, evidence and source locators, dependency links, conflicting versions,
negative findings, and omissions with reasons. Retain originals and earlier
specs; consolidation must not erase a counterexample, qualification or failed
expectation. Summaries guide retrieval; verify load-bearing passages from the
original evidence. A dump is research provenance, not a primary mathematical
citation. Use `track-down-reference` for imported results and
`contradiction-check` for conflicts before any dependent promotion.

## Prototype and review

Use [rapid-prototype](../../../subdomains/latex/skills/rapid-prototype/SKILL.md)
for the combined outline/prototype stage. Plan an introduction to the topic and
a self-contained presentation relative to the recorded audience: motivation,
definitions, examples, exact statements, proofs or explicit proof obligations,
connections and negative results. Choose the order by dependencies and narrative
purpose; do not mechanically preserve the order questions were asked.

For a single desired result, write its exact full target first in the planning
artifact, then work backwards through every prerequisite. This is a planning
order: in the final exposition definitions and notation still precede use.
Preserve uncertainty and hypotheses; a desired theorem is not an established
result. This introductory prototype does not invoke `write-introduction`'s
finished-paper/abstract workflow, whose gates remain in force when requested.

Review the exact prototype with `fp-finder-latex` under an **outline** criterion:
audience fit, dependency closure or explicit gaps, accurate claim states,
source coverage, negative-result retention and a coherent narrative. It may
accept clearly identified research obligations; it cannot certify those as
proved. Use its bounded review cycle and retain findings, responses and exact
versions. Apply `fp-finder-skill` only to changes to these skill instructions,
never its strict-shrink rule to the mathematical presentation.

Resolve undetermined mathematics through `using-mathpowers` under the
[shared gate](execution.md#undetermined-mathematics-is-work-not-a-disposition),
including actual attempts, finite allowance, deadline outcomes and loud errors.
Preserve new evidence packages, record authorized selection, update spec and
dependencies, and repeat affected reviews within those limits. Bounded
gather/outline-only requests stop at their stage and claim no math resolution.

## Fill, review and integrate

Use [fill-in-prototype](../../../subdomains/proof-assist/skills/fill-in-prototype/SKILL.md)
to fill from selected evidence. Assign scratch-only drafting of definitions,
statements/proofs, examples and connective prose using writers' content disciplines,
without invoking canonical writer execution or its postamble. Return candidate
text, sources, dependencies, evidence/doubt records and open obligations,
without canonical edits or promotion. Route new proving/refutation to math
leaves. The coordinator consumes returns and continues. Retain an item/source
relocation map and recheck dependencies when reordering. Check arguments
regardless of dump status.

Run `fp-finder-latex` on the filled presentation under a **presentation**
criterion: declared self-containedness, supported statements, complete required
proofs, verified imports, retained counterexamples/qualifications, coherent notation
and readable exposition. Record assumed prerequisites. Outline acceptance does not
transfer. Review changed statements, proofs, source selection or order across
affected dependencies under the shared limits; reviews never renew the resolution
allowance. Never force acceptance or call partial work complete.

Default to `notes.tex`; honor user or repository-declared targets. Resolve
missing/conflicting declarations through contract adoption; never create an
undeclared sibling manuscript. Prefer a permitted scratch Markdown prototype
and complete Markdown/LaTeX-excerpt candidate for review.
A declared working `.tex` is usable if permitted. Record source-only review
honestly; final acceptance requires actual build/PDF checks.

Integrate eligible reviewed content under [manuscript return](execution.md#manuscript-return)
at the planned location using the relevant writers and full
[WRITERS.md](../../../subdomains/latex/WRITERS.md) preamble and
postamble; human acceptance remains separate. Workflow authorization covers
routine ordering/insertion within the agreed
topic/target unless repository rules reserve that decision. Preserve human
markers and tagged history, check duplicates, update labels/citations and ledger
locations, and never append after `\end{document}`. Reruns update the identified
region without duplication. Run source/style/layout/reference checks. Require
independent `fp-finder-latex` **integrated manuscript** acceptance on the exact
integrated version; until then retain pending-review status. A bounded integration
diff, affected-interface and build/PDF check may
reuse unchanged proof audits with recorded limits; meaning/dependency changes
require renewed review of their affected closure. Report reviewed and integrated
versions separately.

Use the existing AI-accounting delegates and repository contracts throughout.
Keep originals, reviews, exclusions and unresolved findings as evidence. Retiring
a workflow does not authorize deleting source dumps, human annotations or legacy
project data. A research question remains visibly open when its proof is missing;
formatting or a successful build cannot promote it.

## Legacy input

For an existing `chunk-NAME.tex` or `.claude-outline` directory, inventory DRAFT,
GENERATED, prompt histories, dependencies and provenance before migration. DRAFT
is existing authored text; GENERATED is a candidate with no implicit acceptance.
Reconcile both with the live manuscript and keep their original files. Map useful
material into the spec and existing ledger; list omitted or superseded items
with evidence/reasons. Never auto-promote GENERATED, discard it during stripping,
or install a second ATOM/status database. The active pipeline uses research
files and the existing writer/ledger contracts.
