---
name: lean-decompose
description: Use when a source proof has multiple steps, a Lean proof needs helper lemmas, or a formalization obligation has unresolved prerequisites.
---

# Decompose without changing the mathematics

Input: aligned target, full source proof and checked library/project results.
Output: ordered obligations with statements, sketches, dependencies, provenance,
and explicit gaps. Reuse the current plan and task tracker.

Read [source mapping](../lean-workflow/references/source-map.md). Mirror the
source argument first; identify implicit bridging steps as your own obligations.
Each leaf records its exact type, source locator or derivation, checked inputs,
proposed discharge and test. Core logic and supplied hypotheses are valid leaves.

Split independently useful conclusions; preserve shared existential witnesses,
iff directions and mutually proved induction bundles. The graph must be acyclic
over jointly proved groups. Avoid both a single opaque giant obligation and
public helpers with no consumer.

Compile proposed application/composition terms where dependencies are claimed
to close a goal. An all-`sorry` signature skeleton does not test composition.
Use `lean-search` for reuse and `lean-align-statement` for signature problems.
Pass one ready obligation to `lean-prove`; return a false statement or research
gap to the coordinator and `using-mathpowers`, with evidence.

Example: idempotence and injectivity yield a pointwise fixed-point statement;
function extensionality then yields equality with identity. Record both steps
without inventing an unrelated cancellation theorem.
