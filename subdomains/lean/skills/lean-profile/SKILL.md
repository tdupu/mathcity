---
name: lean-profile
description: Use when Lean elaboration is slow, resource limits are reached or proof performance is explicitly requested.
---

# Measure and repair elaboration cost

Input: working targets and observed performance problem.
Output: comparable before/after measurements, diagnosis and checked changes.

Read [profiling recipes](../lean-workflow/references/tools.md). Record the actual
toolchain, machine and cache state. Profile the selected files; map expensive
commands to declarations. Recheck borderline measurements before claiming a gain.

Diagnose the dominant cost: instance search, simplification, definitional
equality, broad automation, metavariable/coercion churn, duplicated terms or
kernel replay. Inspect relevant traces or available LSP profiling. Try a focused
fix such as a type annotation, explicit lemma or smaller simplifier input.
Check the same cause against other slow declarations before inventing new ones.

Keep full statement/definition context fixed and run `lean-verify`. Do not
silently raise heartbeats, recursion limits or trust assumptions to report a
speedup. A needed configuration change is a separate explicit decision. Remove
temporary profiling wrappers/options from delivered source. Helper extraction
routes through decomposition/refactoring; speculative global instances do not
belong in a local performance edit.

Report measured gains, failed attempts and remaining cost. A longer but faster
proof can be the right result; there is no universal one-second requirement.
