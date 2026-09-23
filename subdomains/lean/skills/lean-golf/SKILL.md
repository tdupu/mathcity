---
name: lean-golf
description: Use when simplifying a working Lean proof while preserving its full statement and definition context.
---

# Simplify a proof without changing its claim

Input: verified declaration and scope. Output: a clearer checked proof or a
reason to keep the existing one.

Save the owned baseline and read the full elaborated signature, surrounding
variables, local instances, attributes and definitions. Use `lean-search` for
direct reusable facts. Try one meaningful simplification at a time: replace
redundant intermediates, use a suitable library lemma, or simplify tactic flow.

Compile each candidate, compare the complete signature/context, and inspect
axioms using `lean-verify`. A shorter proof that weakens hypotheses or changes
a definition is not an acceptable golf. Keep useful proof comments. A stable
terminal tactic may be clearer than a long mechanically squeezed replacement.
Retain manuscript-facing wrappers that have a correspondence consumer.

If performance worsens, measure with `lean-profile`. Helper extraction goes
through `lean-decompose`/`lean-refactor`; generality changes use `lean-generalize`
as a separate operation. Discard only this attempt's failing changes, never
other contributors' edits. Return before/after evidence and any remaining issue.

Example: replace an unnecessary chain of equalities with a checked library
application while keeping every binder and the source-facing declaration name.
