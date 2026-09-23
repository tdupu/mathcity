# Split the statement into proof obligations

Invoke `using-leanpowers` and take the `lean-decompose` route. This is planning:
decide the obligations and their order. Prove nothing here.

## What to produce

An ordered list of obligations. Each carries:

- **id** and the Lean statement of the obligation.
- **needs** — obligations it rests on.
- **prerequisite** — an existing Mathlib or project result it depends on. Take the
  `lean-search` route to confirm the prerequisite EXISTS before relying on it.

## The judgment that matters

A decomposition whose leaves are each as hard as the original has achieved nothing.
For each leaf, say why it is genuinely easier — a known Mathlib lemma applies, it is
a special case, it is a direct computation. If you cannot say that for a leaf, mark
it as the real obstruction and say so plainly rather than decomposing it further.

## Report

The obligation graph, the confirmed prerequisites with their Mathlib names, and any
leaf you believe is the genuine hard core of the problem.
