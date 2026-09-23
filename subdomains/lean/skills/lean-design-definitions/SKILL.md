---
name: lean-design-definitions
description: Use when choosing Lean representations for mathematical objects, structures, predicates or notation.
---

# Choose the representation

Input: source definitions and expected uses. Output: representation decision,
source correspondence, existing declarations to reuse and new declarations
for `lean-define`. This is design, not implementation.

Invoke `lean-search` for existing structures and equivalent formulations. Read
their actual definitions and instances under the project pin. Compare only
plausible representations: subtype versus set, bundled map versus predicate,
structure versus class, explicit hypothesis versus inferred instance.

Record the chosen carrier, universes, operations, equality, coercions and
instance scope. Check that source constructions and later statements can be
expressed without changing meaning. Avoid duplicate abstractions and ambiguous
instance paths. Identify necessary defining equations and a small meaningful
usage example; do not manufacture an arbitrary quota of API lemmas.

If two interpretations change the mathematics, surface that choice before
dependent work. A routine faithful encoding can proceed within the existing
authorization. Return implementation obligations and unresolved questions to
the same coordinator.

Example: encode “x is fixed by f” as `f x = x`; if the manuscript names its
fixed-point set, decide whether an existing Mathlib definition already provides
that set before introducing a new predicate.
