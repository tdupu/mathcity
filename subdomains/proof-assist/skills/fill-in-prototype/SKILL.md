---
name: fill-in-prototype
description: Complete a coherent presentation from a prototype and selected research evidence, composing writers for supported material and targeted prove/refute attempts for genuine gaps. Use for "fill in the prototype", "complete this exposition", or narrowly "work these conjectures". Requires doubt before promotion and returns actual artifacts and unresolved obligations to the synthesis coordinator; a fill request authorizes execution, not just recommendations.
---

# fill-in-prototype

The [synthesis contract](../../../../skills/math-workflow/references/synthesis.md)
owns the end-to-end stages, reviews and integration. This leaf executes the
requested fill, then returns to that coordinator. A direct request to work
named conjectures stays confined to those items; a request to fill the
presentation includes its definitions, proofs, examples and explanatory prose.

## Fill from evidence, then resolve gaps

1. Read the prototype, spec, selected originals and relevant live text;
   reconcile touched rows under [LEDGER.md](../../../repo-docs/LEDGER.md).
   Resolve audience, depth and target through
   [RESOLUTION.md](../../../repo-docs/RESOLUTION.md). Inventory missing content
   and genuine research obligations separately, with source locators and
   dependencies; report their counts. If the spec or structure is missing,
   compose `create-exposition` or `rapid-prototype` and the applicable outline
   review within the fill scope.
2. Fill supported material in dependency order from the actual arguments,
   not the dump's status labels. Complete the topic introduction, definitions,
   statements, required proofs, worked examples and connective explanation
   to the audience's declared level. Preserve hypotheses, computational range,
   qualifications and counterexamples. Verify imported results through
   `track-down-reference`; a source citation does not replace a required
   self-contained proof.
3. For unresolved claims, dispatch focused attempts through
   [PROVERS.md](../../PROVERS.md), giving the exact statement, prerequisites,
   selected evidence and requested proof **and** counterexample search.
   Harvest by the backend contract into the permitted dated run directory;
   retain packages, partial proofs, reductions and failed expectations.
   Update the existing spec/ledger evidence and dependency links without
   silently expanding source selection. Missing tools/evidence leave a named
   obligation open; continue independent supported work.
4. Route refutations and conflicts through `contradiction-check` before any
   dependent promotion; never silently replace an earlier claim. Run `doubt`
   on claims to be promoted, continue independent work while it runs, and
   collect its recorded verdict before integration promotes a claim. Only SOUND
   on the actual statement/argument/dependencies satisfies the gate; changed
   evidence needs renewed scrutiny. WEAK, SUSPECT or absent verdicts block
   the affected promotion, including computational or negative claims.
5. Compose `write-definition`, `write-proposition`, `write-example` and
   `write-remark` for their respective content; use `explain-experiment` for
   computational exposition when needed. Supply each writer its evidence,
   prerequisites and concrete planned location. Produce the complete content,
   not a list of recommended writer calls. Scratch workers apply the writers'
   content disciplines and return candidate text/evidence only: no canonical
   mutation or canonical postamble during drafting. Reasonable reordering and
   insertion within the selected target are authorized unless a repository
   rule reserves them; retain relocations and recheck dependencies. Claims
   inside explanatory prose still require the proposition gates.
6. Keep pre-integration candidates in permitted scratch Markdown, including
   LaTeX excerpts where useful; do not invent an undeclared `.tex` target.
   At requested integration the coordinator invokes
   [WRITERS.md](../../../latex/WRITERS.md) and the composed leaves in full at
   the declared canonical/aspirational destination. Preserve human markers
   and tagged history; keep statuses in the ledger.
   Drafting an introduction to the topic does not invoke or bypass
   `write-introduction`'s finished-paper/abstract gates.
7. Assemble the returns into one readable presentation, checking notation,
   transitions, labels and dependency coverage. Carry negative findings as
   substantive results with the expectation they correct (LX11/LX12); count
   those carried and exclusions with authorized reasons. Missing proofs stay
   explicit questions/conjectures, never theorem/proof placeholders presented
   as completed mathematics. Identify any unmet presentation requirement.

## Return and continue

Return the exact candidate/edited regions, source and relocation map, evidence
and doubt records, writer checks, and unresolved obligations with their blocked
dependents. The coordinator consumes these artifacts and continues the shared
presentation review/integration sequence; a writer's return is not a reason
to end the synthesis. For direct fill requests, the invoking agent carries out
the applicable review and requested delivery from that contract. Report actual
completion or incompleteness. Source-candidate acceptance is not final manuscript
acceptance: the coordinator must obtain the shared contract's final independent
review of the integrated diff, its interfaces/dependency closure and compiled
PDF. Neither outline acceptance nor a successful compile establishes a proof.
