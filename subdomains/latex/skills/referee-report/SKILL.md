---
name: referee-report
description: Adversarial line-by-line referee-grade review of OUR OWN manuscript or notes, at prover level, delivered to scratch — never edits the tex. A green build resolves nothing mathematical (mechanism 5). Use when the user says "referee my section N", "referee-report on the draft", "adversarial review of the manuscript". NOT for handling a RECEIVED referee report (triage-referee-report / manual astra-fable response per ADR 0005) and NOT for applying fixes (revise, after human adjudication).
---

# referee-report

Read-only toward the tex. This leaf's procedure:

## Produce the report

1. Resolve the repo docs (`subdomains/repo-docs/RESOLUTION.md`); scope
   = the named section(s) of the canonical file.
2. Dispatch the review at prover level per
   [../../../proof-assist/PROVERS.md](../../../proof-assist/PROVERS.md)
   (fable pipeline on Claude harnesses; astra-dump otherwise), with the
   mandate: line-by-line; verify every proof step; attack every
   statement (counterexample hunting per mechanism 6); check every
   citation's plausibility (route suspicious ones to
   track-down-reference); hypothesis/notation drift; the mechanism-5
   rule verbatim — compile success is not mathematical correctness.
3. Report to `scratch/<date>-referee-<slug>/report.md`: per-finding
   severity (BLOCKING / MAJOR / MINOR), location, the objection, and
   what evidence would resolve it. Claims in the report follow the
   five-way taxonomy; contradictions found route through
   contradiction-check (its report + refusal semantics).
4. Hand to the human for adjudication; accepted items feed `revise`.

## Red flags

| Thought | Reality |
|---|---|
| "It compiles and reads well" | thm1p10: green builds, 5 blocking findings. Attack the math. |
| "Fixing it while reviewing saves a round" | Reviewer edits nothing. Adjudication first. |
