---
name: roadmap-draft
description: Use when a mathematical corpus (manuscript, notes, or Lean development) needs a dependency roadmap of formalization or research targets that other agents will be dispatched against, and no roadmap exists for it yet. Also use when an existing roadmap's targets must be checked for dispatchability before handing them out.
---

# Draft a roadmap

Decompose into tiers, order by dependency, find the critical path,
conditionalize bottlenecks — do all that as you normally would. This skill is
for the one thing that reliably goes wrong anyway.

## The rule that earns this skill

**Every library name you write is a claim requiring evidence, at the same
standard as a mathematical one.** Check each against the *pinned* version before
grading anything, and record the pin in the roadmap.

Four measured failures, both directions:

| Direction | What happened | Cost |
|---|---|---|
| Believed absent | `Differential` hand-specified as new work; Mathlib has `Derivation/DifferentialRing.lean` with exactly that ℤ-linear shape | strongest agent sent to rebuild the library |
| Believed absent | scheme normalization taken as missing; it is in `AlgebraicGeometry/Normalization.lean` | two targets blocked on a false premise |
| Believed present | `MonomialOrder.lex` cited, and a proof declared **unnecessary** because of it; the pin ships only `degLex`, which is not lex | a deleted obligation |
| Believed present | `Tropical` used as the foundation type; it is `@[deprecated MinTropical]` | foundation of a 40-item roadmap |

Both directions are cheap to prevent. A false *present*-claim attached to "this
work is unnecessary" is the most expensive of the four — check those twice.

**A zero-hit grep is evidence about a string, not about the mathematics.** Before
recording anything absent: search the leaf name without its namespace (Mathlib
writes `theorem IsPWO.union` inside `namespace Set`, so the qualified name never
appears literally), check for an anonymous `instance`, and look one directory over.
Two of the four failures were a correct grep with a wrong conclusion.

## Inputs must be literal

An `inputs` or `outputs` entry is a name that greps, a tag that fetches, or a path
that exists — never a description of what belongs there. If a validator cannot
resolve it, it is a lead, not an input. One committed roadmap's input was a literal
ellipsis, past two human readings, because prose scans as intent.

Give every target an acceptance check written before the work, and confirm it is
reachable **by the declared method**. A well-defined criterion the target's own
content cannot reach is the subtlest defect in the catalogue.

## Stop rather than guess

When a source statement is imprecise, self-contradictory, or unsupported by its
citation, record a finding with an owning target and **do not write a target that
papers over it**. A returned blocking report is a success — it costs one agent
instead of one review round.

Never record a claim as proved because a manuscript asserts it or because it
compiles. Those are evidence about two different propositions.

## Then

`references/process.md` — the eight phases and the defect each prevents.
`references/schema.md` — record format, status axes, evidence gate, typed edges,
and the iff test for an interface equivalent to its own conclusion.
`references/failure-modes.md` — 29 incidents with checks.

When the draft validates clean, **dispatch one target.** Thirteen review passes
over two clean roadmaps measured nothing; one execution measures it.
