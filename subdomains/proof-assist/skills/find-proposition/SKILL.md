---
name: find-proposition
description: >-
  Hunt plausible propositions on a topic at prover level: candidates with plausibility rationales and attack lines, in a dated ai/ dump with ledger rows — never touches tex. Use for "find propositions about X", "what could we prove here", "generate candidate statements". Candidates are adversary-bait until a doubt run and a proof exist (mechanism 6). NOT for proving (a PROVERS.md backend dispatch — fill-in-prototype for gap-working) or writing (write-proposition).
---

# find-proposition

## Procedure

1. Scope from the human: topic, ambient objects, what counts as
   interesting (or inherit from the repo's notes context).
2. Dispatch the hunt per `subdomains/proof-assist/PROVERS.md`: each
   candidate carries the statement (explicit hypotheses),
   why-plausible (evidence class: analogy, computed cases, special
   case of a known result), a first attack line, and a falsification
   attempt sketch.
3. Deliver to `ai/<date>-find-proposition-<slug>/` (dump triple);
   ledger rows per candidate: `refuted` for counterexamples, else `conjectural`;
   where/evidence = dump path, retaining counterexample evidence.
4. Recommended next steps per candidate: fill-in-prototype
   (gap-working) / doubt — dispatch neither yourself.

## Red flags

| Thought | Reality |
|---|---|
| "This one is surely true, mark it proved" | Mechanism 6: one-line counterexamples kill sure things. |
| "Drop the weak candidates silently" | Report all with their evidence class; the human prunes. |
