---
name: lean-diagnose
description: Use when Lean reports an error, a tactic stalls, a build regresses or a formal proof attempt exposes an unexpected goal.
---

# Diagnose the failing obligation

Input: exact command, full error/goal, baseline and current source.
Output: reproduced cause, minimal checked repair or a concrete blocker.

Apply Superpowers' `systematic-debugging` method within the active Lean task.
Reproduce the smallest relevant failure without erasing evidence. Classify it:
toolchain/cache/build setup; missing import or changed API; elaboration,
coercion/universe/instance mismatch; tactic choice; or mathematical falsehood.

Inspect full types and available instances before adding hypotheses. Search
actual declarations with `lean-search`. In a scratch probe, vary one suspected
cause and compile the result. For a suspected false claim, test boundary cases
and return the counterexample to the coordinator; do not patch the theorem's
meaning to satisfy the compiler.

Keep only a repair that passes the relevant original command and affected
targets. Revert only this attempt's edits when it fails, preserving concurrent
work. Repeated identical attempts are not new evidence. If blocked, return the
goal, attempted hypotheses, outputs and next discriminating experiment.

Example: a module-system file rejected by raw `lake env lean` may need Lake's
module-aware driver; that setup failure is not evidence that its theorem is false.
