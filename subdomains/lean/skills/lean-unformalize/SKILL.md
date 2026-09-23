---
name: lean-unformalize
description: Use when explaining a Lean declaration in ordinary mathematics or preparing faithful prose from a formal proof.
---

# Explain the encoded mathematics

Input: actual declaration and its definition/dependency context.
Output: precise prose statement, proof sketch and explicit assumptions.

Inspect the full elaborated type, implicit parameters, relevant definitions and
actual proof. Translate objects and hypotheses into standard mathematical
language. Explain the mathematical steps, not a line-by-line tactic transcript.
Inspect dependencies until the explanation is supported; do not claim a complete
closure from a capped name scan.

Retain nonempty, finite, decidable, characteristic and other load-bearing
conditions. Disclose domain axioms, unproved hypotheses and extra compiler trust
using `lean-verify` evidence. When evidence is unavailable, distinguish reading
source from a checked declaration. An axiom-free implication may still be only
a conditional result.

Use the requested output format; otherwise return readable prose in chat.
Requested manuscript write-back delegates to `using-latexpowers` with the same
claim ID and context. Source equivalence needs `lean-fidelity`; fluent prose
alone does not establish it. Blueprint synchronization uses `lean-blueprint`.

Example: `theorem t (h : P) : Q` becomes “assuming P, Q holds,” not simply “Q.”
