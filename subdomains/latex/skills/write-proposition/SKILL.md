---
name: write-proposition
description: Draft ONE proposition — statement plus proof per LX4/ST6 — into the repo's canonical tex file, from an evidenced claim (ledger row, harvested proof package, or opened-source verification). Use when the user says "write this up as a proposition", "add a proposition for X", or when a proved claim is promoted from scratch into notes.tex. NOT for unproved ideas (rapid-prototype / find-proposition), definitions (write-definition), or whole-experiment write-ups (explain-experiment). Refuses without evidence, a passing contradiction-check, and (for notes promotion) a recorded doubt run.
---

# write-proposition

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full — resolution,
canonical target, contradiction and doubt gates, ST5 tagging, ledger
update, check-latex/check-style verification, human acceptance. This
leaf's middle:

## Definition separation

Before the statement, extract each new term, construction, or notation
into a preceding definition or notation paragraph (LX10). Keep the
hypotheses in the result, referring to the definition as needed. The
statement may assert that a previously specified construction is
well-defined; it must not introduce that construction while asserting it.

## Inputs

The claim, verbatim, and its EVIDENCE: a ledger row with proof-package
or computation paths, or a track-down-reference verification for an
imported result. No evidence → loud refusal naming what is missing
(mechanism 6: plausible statements without evidence are how false
lemmas enter manuscripts).

## Drafting

- Environment per the repo's STYLE.md (ST1: proposition, never lemma or
  corollary). Explicit hypotheses in the opening sentence (ST2).
- Proof per LX4: own proof written out; imported result at notes tier →
  proof + pinpoint (ST6); manuscript tier → pinpoint citation allowed.
- Placement: the section the human named, or — if ambiguous — ask;
  never guess a location (D5). Labels per the repo's existing scheme
  (check-labels-and-refs compatible).
- The statement asserts exactly what the evidence supports: no
  strengthening, no "for all" from a checked family.

## Red flags

| Thought | Reality |
|---|---|
| "The proof is obvious, skip the evidence check" | Obvious is how mechanism 6 ships. Evidence or refuse. |
| "I'll tidy the surrounding text while here" | One proposition, one tagged region. Nothing else. |
