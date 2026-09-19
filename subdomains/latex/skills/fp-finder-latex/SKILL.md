---
name: fp-finder-latex
description: Run a bounded simulated journal referee and independent revision cycle for one or more LaTeX manuscripts. Use when asked to repeat brutal mathematical review and revision until referees are satisfied, including a manuscript package. Preserves exact versions, findings, scope and usage; reports unresolved outcomes honestly. Not actual journal review or guaranteed acceptance.
---

# fp-finder-latex

Parent: [LaTeX workflows](../../README.md).

You are the coordinator. Use separate native agents as referees and revisors;
sequential dispatch is sufficient. Judge arguments, not author reputation.
The result is a simulated review with stated coverage, never human approval
or formal verification. Keep a scientifically useful **WORKING** revision
even when further findings remain; only independent review can make an exact
submission **ACCEPTED** under its declared criterion.

## Preflight and contract

Read the nearest project instructions and canonical-file contracts. Load
[using-latexpowers](../using-latexpowers/SKILL.md),
[using-mathpowers](../../../proof-assist/skills/using-mathpowers/SKILL.md),
[referee-report](../referee-report/SKILL.md) and the relevant shared
[writer mechanics](../../WRITERS.md). Use their scoped proof/source/writing
leaves in workers, without restarting the whole intake in every worker.
Keep mathematical claim states in the existing
[LEDGER contract](../../../repo-docs/LEDGER.md); this skill owns review
history, not a competing proof-status system.

Before expensive work, verify accessible manuscript inputs and primary
sources, the project's TeX/PDF tools, distinct-agent dispatch and any
required proof backend. Record actual capability and model provenance.
If a required dependency is absent, say what is missing, the concrete setup
action and which work it blocks; continue only independent work. Do not
invent a backend or call inline self-review independent. An explicitly
authorized inline mode must retain that limitation and cannot satisfy the
independent-review acceptance condition.

Create one run root in the project's permitted scratch area. Record:

- User goal, canonical manuscripts, active-document boundaries, local input
  closures and cross-paper dependencies; preserve existing work and archives.
- Revision authorization and limits. Existing autonomous authorization uses
  the manual referee-response route with writer mechanics and an item-to-tag
  map. Use [revise](../revise/SKILL.md) only for its actual accepted-item-list
  contract. A review-only request permits reports, not manuscript mutation;
  obtain missing authorization at that boundary, without asking again for
  authorization already granted. Real received reports retain their chosen
  adjudication route.
- A fixed criterion and track ID: genre, contribution bar, reader background,
  correctness/source standards, required coverage and package objective.
  Do not infer a research-only venue from “high quality.” State necessary
  assumptions; clarify a consequential unresolved choice. A later narrower
  genre/claim is a separate track, never retroactive closure of the original.
- Referee/revisor identities and relevant prior authorship. A referee never
  writes the manuscript revision it judges. Disclose same-task/model limits.
- A positive round budget, default **8**, checked before every new dispatch.
  Record any user-specified time/token limit. A limit is not a verdict.

For multiple papers, first assess their division and dependency graph.
Combining or splitting is allowed within authorization, with a claim and
finding relocation map, stable aliases and review of affected interfaces.
Do not improve apparent acceptance by hiding a difficult claim elsewhere.

## One round

1. **Freeze.** Snapshot sources, bibliography/figures/preambles and available
   PDFs, with hashes and build/tool evidence. Never overwrite a reviewed
   snapshot. An initial failed build or absent PDF is recorded explicitly;
   useful source review may proceed, but final PDF checking is still owed.

2. **Referee.** Dispatch a read-only reviewer using referee-report at proof
   level. Read the source before weighing the author response. Inventory
   active claims/proofs and catalogue entries; mark checked, imported and
   unchecked coverage precisely. Test hypotheses, edge cases, counterexamples,
   source editions and actual source-to-manuscript maps. Separate correctness,
   contribution, presentation and the stronger package objective. A citation,
   compilation or statement count is not proof. Imported theorems can be
   legitimate journal inputs without making a package self-contained.

   Each report gives ACCEPT, MINOR_REVISION, MAJOR_REVISION or REJECT under
   the fixed criterion. Every finding has a stable ID, original objection
   and locator, severity/type, evidence, concrete closure requirement and
   reviewing authority. New objections get new IDs. Preserve counterexamples
   and source evidence. Reviewers must not manufacture objections for tone,
   or approve from fatigue, pressure or iteration count.

   Before issuing a verdict, the reviewer runs a report-completeness audit.
   Every material objection discovered in the source, a prior report, a
   source comparison, or an adversarial check appears in the current finding
   table with a stable ID, exact locator, closure test, and one destination:
   `RESOLVED-IN-REPORT`, `OPEN-TODO`, `IMPORTED-OBLIGATION`,
   `OUT-OF-SCOPE`, or `INVALIDATED`. Findings may not
   remain only in worker scratch or an ancillary calculation. The report
   links each TODO to the manuscript response map. `RESOLVED-IN-REPORT`
   requires the exact resolving passage and closure test; `OPEN-TODO`
   requires an owner, evidence requirement, next source or computation, and
   closure test; `IMPORTED-OBLIGATION` requires the precise source,
   hypotheses, import boundary, and explicit permission under the fixed
   criterion; `OUT-OF-SCOPE` requires the criterion and exclusion reason;
   `INVALIDATED` requires the defeating evidence. ACCEPT is forbidden while
   any material finding is `OPEN-TODO`, or while an imported row lacks those
   source, hypothesis, boundary and criterion-permission fields.

   Apply an example admissibility gate to every calculation used as evidence.
   It must be source-native with exact hypotheses and source interfaces, or
   interpretation-compatible with an explicit typed map into the interpretation
   catalogue that preserves the relevant operations. The workflow does not use
   the labels "toy model", "toy example", or "naive calculation". An
   illustrative construction that fails the gate is excluded from the verdict
   and recorded only as a rejected diagnostic, never as a counterexample to
   the manuscript's source-level theorem.

3. **Adjudicate and revise.** Check findings against evidence; a referee is
   not automatically correct. Keep disputed/conflicting items open with
   reasons until resolved by mathematical evidence or an independent focused
   adjudicator; seek the user only for a genuinely missing choice. Within
   existing authorization, a different agent makes tagged, bounded revisions
   and maps every finding to an edit/evidence locator or an explicit unresolved
   response. The revisor proposes closure, never awards it. Preserve human
   comments and dormant material under project rules. Prove new claims or
   mark their unresolved status; don't insert a plausible argument as proved.
   The response map must cover the referee's complete finding table and every
   linked investigation TODO. An imported obligation may remain open only
   when the fixed criterion expressly permits that import and the report gives
   its precise source, hypotheses, and boundary.

4. **Validate a working candidate.** Check the coherent diff and complete
   item accounting. Build changed roots with isolated auxiliaries, inspect
   logs, references/citations and the actual compiled prose/formulas. TeX
   comments can swallow text without a build error. Keep required AI/software
   statements accurate and at the project's specified introduction location.
   Record regressions; repair/revert them or leave them explicitly unresolved.
   A supported partial revision may be retained as WORKING, with unchecked
   claims visible. It is not an accepted article. Freeze its next submission.

5. **Return to the referee.** Give the original referee the exact new snapshot,
   complete response map and earlier reports. Verify each item as CLOSED,
   PARTIALLY_ADDRESSED, OPEN or RETRACTED, with reasons and revised locators.
   A retraction retains the original finding and evidence. Check all changed
   arguments and affected dependencies, including new mistakes. Retain limits
   for unchanged material; do not claim a fresh complete proof audit from a
   diff check. A changed hash creates an unreviewed version and invalidates
   affected dependent claims, without erasing historical acceptance of the
   old version. No acceptance silently transfers between versions or tracks.

   The returned report repeats the completeness table, including findings
   discovered during revision. A clean build or polished exposition cannot
   close a mathematical item whose closure test was not met. If an example
   used in the prior round fails the admissibility gate, remove it from the
   evidentiary chain and preserve the correction in the response history.

6. **Account and decide.** Update the per-round records by delegating:
   [[update-ai-usage]] for provenance (call/agent IDs, requested versus
   observed models and harness, tool and source use, failed and discarded
   attempts, source-check limits) and [[update-tokens]] for the priced
   counters. Both consolidate upward into the repository's master
   `ai-usage.md` and `tokens.md`; root summaries reference those records.
   Their contract — never invent totals or costs, never treat unavailable as
   zero, label every estimate — is `AI-POLICY.md` (AI15, AI16) and is not
   restated here. Round-local duties that remain this skill's: do not
   double-count mirrors and do not add overlapping intervals.

   Accept only when all in-scope papers and affected package interfaces meet
   the fixed criterion and required coverage on the exact current tuple, with
   no mandatory unresolved items or unchecked load-bearing proofs, and final
   build/PDF checks complete. Record permitted imported prerequisites. A larger
   self-containedness goal needs its own dependency closure; article approval
   does not imply it. Further substantive repairs start another round within
   budget, not a repeat of the same report to solicit a nicer verdict.

## Non-success and completion

After two successive rounds with the same substantive open obligations and
no new resolving evidence, reassess strategy. Continue only with a recorded
materially different approach within the remaining budget. A blocker needing
new research or unavailable evidence can stop its track while independent
work finishes. On exhaustion, unresolved disagreement or inability to progress,
report **NOT CONVERGED** with exact blockers and the best working snapshot;
never manufacture an acceptance or weaken the criterion silently.

Return manuscript paths, exact reviewed versions, per-track verdicts, closed
and remaining findings, package dependencies and accounting links. Preserve
all reports and rejected candidates. Clean up only task-created worktrees,
branches and disposable files after preserving evidence; no implicit commit,
push, submission or publication. Simulated acceptance means only that the
recorded reviewers found no remaining mandatory objection under that scope.

This is a thin manuscript adapter, not the generic META-FP formula running
unchanged. That formula already permits LaTeX growth; its APPROVING quality
floor differs from retaining a partial WORKING revision. To stabilize this
skill's own text, use [fp-finder-skill](../../../../skills/fp-finder-skill/SKILL.md);
its per-file shrink rule does not govern manuscripts.

## Example and validation

Example prompt: “Use fp-finder-latex on these two canonical papers as
specialist exposition. Revise autonomously for at most four rounds; preserve
the separate goal of a self-contained package.” Paths come from the caller.

[Behavioral fixtures](assets/scenarios.json) are portable inputs for bounded
agent dry runs. For the final skill hash, give a separate agent each input,
request its decision and next actions under this skill, and save the prompt,
response and independent comparison with the expected observable outcome.
The inputs are fictional tests, not real manuscript states. Distinguish
executed cases from supplied-only cases. Hash/accounting checks certify only
those mechanics; semantic trials do not certify general mathematical judgment.
After any promoted change, rerun affected cases on the final tuple.

## Negative results travel with the positive ones (LX11, LX12)

This skill renders previous work into a new artifact, so the negative-result
floor of `../../POLICY.md` applies. Before finishing, enumerate the inputs'
refutations, counterexamples, ill-posed proposals, and failed expectations, and
carry each into the output as a numbered statement (or a labelled question when
unproved), naming the expectation it corrects: "it is natural to expect $X$; in
fact $Y$". Report the count carried and, for anything deliberately left out,
the scope reason. Dropping a refuted claim together with its refutation is a
revise-level violation: the refutation is the surviving result.
