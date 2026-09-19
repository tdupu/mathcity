---
name: referee-report
description: Adversarial line-by-line referee-grade review of OUR OWN manuscript or notes, at prover level, delivered to ai/ — never edits the tex. A green build resolves nothing mathematical (mechanism 5). Use when the user says "referee my section N", "referee-report on the draft", "adversarial review of the manuscript". NOT for handling a RECEIVED referee report (triage-referee-report / manual frontier-fable response per ADR 0005) and NOT for applying fixes (revise, after human adjudication).
---

# referee-report

Read-only toward the tex. This leaf's procedure:

## Produce the report

1. Resolve the repo docs (`subdomains/repo-docs/RESOLUTION.md`); scope
   = the named section(s) of the canonical file (WRITERS.md's Target
   clause defines it).
2. Dispatch the review at prover level per
   `subdomains/proof-assist/PROVERS.md`,
   with the mandate: line-by-line; verify every proof step; attack every
   statement (counterexample hunting per mechanism 6); check every
   citation's plausibility (route suspicious ones to
   track-down-reference); hypothesis/notation drift; the mechanism-5
   rule verbatim — compile success is not mathematical correctness.
3. Report to `ai/<date>-referee-<slug>/report.md`: per-finding
   severity (BLOCKING / MAJOR / MINOR), location, the objection, and
   what evidence would resolve it. Every finding also has a stable ID,
   an explicit disposition, an exact source/report locator, a closure
   test, and a destination: `RESOLVED-IN-REPORT`, `OPEN-TODO`,
   `IMPORTED-OBLIGATION`, `OUT-OF-SCOPE`, or `INVALIDATED`. Claims in
   the report follow the five-way taxonomy; contradictions found route
   through contradiction-check (its report + refusal semantics).
4. Run a report-completeness pass before issuing a verdict. The report
   must contain a coverage table listing every material objection found
   during the review. Every row must use exactly one destination and the
   corresponding evidence fields:
   `RESOLVED-IN-REPORT` gives the exact resolving passage and closure test;
   `OPEN-TODO` gives a named owner, evidence requirement, next source or
   computation, and closure test; `IMPORTED-OBLIGATION` gives the precise
   source, hypotheses, boundary of the import, and an explicit statement
   that the fixed criterion permits it; `OUT-OF-SCOPE` gives the criterion
   and the reason for exclusion; `INVALIDATED` gives the evidence that
   defeats the objection. An objection may not remain only in worker
   scratch, an ancillary calculation, or an unlinked note.
   ACCEPT is forbidden while any material finding is `OPEN-TODO`, or while
   an `IMPORTED-OBLIGATION` row lacks its source, hypotheses, boundary, or
   criterion permission. A material row may support ACCEPT only after its
   stated closure test passes or its permitted import/out-of-scope status is
   explicit.
5. Apply the example admissibility gate. An example used as evidence for
   correctness, a gap, or a verdict must either be a source-native object
   with its exact hypotheses and source interface, or an
   interpretation-compatible object with an explicit typed interpretation
   map preserving the operations under discussion. Do not use the labels
   "toy model", "toy example", or "naive calculation" as mathematical
   evidence. If an illustrative construction has no such interpretation,
   omit it from the proof argument; at most record it as a rejected
   diagnostic in the coverage table, explicitly excluded from the verdict.
6. Return for adjudication under the caller's authorized route.

## Red flags

| Thought | Reality |
|---|---|
| "It compiles and reads well" | thm1p10: green builds, 5 blocking findings. Attack the math. |
| "Fixing it while reviewing saves a round" | Reviewer edits nothing. Adjudication first. |

## Negative results travel with the positive ones (LX11, LX12)

This skill renders previous work into a new artifact, so the negative-result
floor of `../../POLICY.md` applies. Before finishing, enumerate the inputs'
refutations, counterexamples, ill-posed proposals, and failed expectations, and
carry each into the output as a numbered statement (or a labelled question when
unproved), naming the expectation it corrects: "it is natural to expect $X$; in
fact $Y$". Report the count carried and, for anything deliberately left out,
the scope reason. Dropping a refuted claim together with its refutation is a
revise-level violation: the refutation is the surviving result.
