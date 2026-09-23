---
name: lean-review
description: Use when reviewing Lean changes, a formalization handoff, mathematical representation choices or a candidate Mathlib contribution.
---

# Review the formalization

Input: exact changed files, source map, target scope and current build evidence.
Output: read-only findings with severity, location, evidence and suggested remedy.

Read the full changed declarations and load-bearing context. Verify findings
before reporting them; explain the existing design's plausible rationale.
Review representation necessity, typeclass/generalization choices, mathematical
statement shape, source fidelity, dependency reuse, proof clarity, imports,
automation stability and performance evidence where relevant.

Use `lean-search` to test alleged library duplication. Use `lean-verify` and
`lean-fidelity` evidence rather than equating a successful build with a correct
translation. Missing evidence is a finding, not an invented passing check.
Do not demand maximum generality for a source-specific theorem without benefit.

Where an independent reviewer is available, pass the target and evidence in a
bounded brief without the author's preferred verdict. Otherwise disclose the
self-review limitation. Return verified findings to the coordinator; proposed
fixes receive reasoned dispositions and checks rather than automatic acceptance.
Do not edit files or send review comments from this leaf.

Example: a short wrapper tying a manuscript label to a library theorem may be
a useful stable interface; evaluate its consumer before recommending deletion.
