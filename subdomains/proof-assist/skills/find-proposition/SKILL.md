---
name: find-proposition
description: Hunt plausible propositions on a topic at prover level: candidate statements with why-plausible rationales and attack lines, delivered to a scratch dump with conjectural ledger rows — never touches tex. Use when the user says "find propositions about X", "what could we prove here", "generate candidate statements". Candidates are adversary-bait until a doubt run and a proof exist (mechanism 6). NOT for proving (prove-it / fill-in-prototype) or writing (write-proposition).
---

# find-proposition

## Procedure

1. Scope from the human: the topic, the ambient objects, what counts
   as interesting (or inherit from the repo's notes context).
2. Dispatch the hunt per [../../PROVERS.md](../../PROVERS.md) (fable pipeline on Claude
   harnesses, astra-dump otherwise): candidates must each carry the
   statement (explicit hypotheses), why-plausible (evidence class:
   analogy, computed cases, special case of a known result), a first
   attack line, and a falsification attempt sketch.
3. Deliver to `scratch/<date>-find-proposition-<slug>/` (dump triple);
   ledger rows per candidate, status `conjectural`, provenance = the
   dump.
4. Recommended next steps per candidate: fill-in-prototype /
   prove-it / doubt — dispatch none of them yourself.

## Red flags

| Thought | Reality |
|---|---|
| "This one is surely true, mark it proved" | Mechanism 6 is one-line counterexamples killing sure things. |
| "Drop the weak candidates silently" | Report all with their evidence class; the human prunes. |
