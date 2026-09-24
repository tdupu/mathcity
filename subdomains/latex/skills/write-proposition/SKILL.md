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

## The environment holds the statement and nothing else

A theorem-class environment contains hypotheses and conclusion. Unpacking
("Explicitly, for every $y$ there is ..."), explication of what the
statement means, worked notation, and secondary conclusions drawn from a
cited source all go *after* `\end{...}`, each introduced by its own
connective sentence rather than run on inside the environment. This is
the Definition layout rule of `using-latexpowers` applied to every
theorem-class environment, not only to `definition`.

Test: if a reader who trusts the statement could skip a sentence without
losing the statement, that sentence is outside the environment.

## Enumerate only the parts that are consumed

Enumerate a statement when more than one of its parts is cited somewhere.
If exactly one part is used, state one thing and do not enumerate. Before
enumerating, list the citing site for each intended part; a part with no
citing site is deleted or demoted to a sentence in the proof, never
shipped as an unused item.

A statement's parts are an **interface**. Once enumerated and labelled,
they are consumed by other statements, by later proofs, and by any
formalization of the document. Therefore:

- Cite a part by `\eqref{item:...}`, never as a literal "(1)", "(2)".
  A hardcoded ordinal survives the deletion of the part it names and
  LaTeX reports nothing; an `\eqref` breaks the build, which is the
  point.
- De-enumerating or reordering a statement re-points every citation of
  its parts, in the same edit. Repair such a break by giving each
  consumed part its own labelled statement — not by restoring an
  enumerate whose shape the author has already rejected.

## When the environment type is unclear, ask how it would be formalized

A useful discriminator, and the one that matches how these documents are
actually consumed downstream:

| The fact, in a proof assistant | The environment here |
|---|---|
| a `def` — it names an object or fixes notation | definition (write-definition) |
| a `theorem`/`lemma` — it has a proof and is applied elsewhere | proposition |
| a `have` inside one proof, used nowhere else | prose inside that proof; do not promote |
| several separately named theorems | several statements, not one with parts |
| nothing — it has no formal counterpart | remark, and see write-remark's limits on it |

Corollaries: a fact cited more than once earns a number and a label; a
fact cited zero times is prose, or is deleted; a statement whose parts
would be separate theorems is written as separate statements. The test
is silent on motivation, intuition, and worked examples, which have no
formal counterpart and are governed by exposition, not by this table.

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
