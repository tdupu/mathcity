# Formalization evidence

One record per source claim; several Lean declarations may implement one claim.
Use the repository's existing ledger/schema when available, adding equivalent
fields rather than creating a competing task tracker. Otherwise keep a compact
source map with the run's evidence under its declared scratch root.

| Required field | Meaning |
|---|---|
| claim ID, scope | Stable manuscript label or explicit supplied-proof ID; requested versus supporting result |
| source | Path/locator, exact assertion, relevant definitions and hypotheses; identify synthetic fixtures |
| Lean | Workspace, module, fully qualified declaration names and full elaborated types |
| representation | How source objects, equality, quantifiers, witnesses and conventions map to Lean |
| dependencies | Claim/definition IDs, library declarations, open obligations; label a manually reconstructed graph |
| snapshot | Hashes of relevant source and Lean files, local definitions/imports, toolchain, lakefile and manifest; dependency revisions and dirty content |
| compiler | Actual commands, working directory, versions, exit status and complete output paths |
| trust | Actual `#print axioms` output per target and its classification |
| fidelity | Reviewer, compared snapshot, matches/mismatches, extra assumptions, exclusions |
| status | The narrowest supported status below, with remaining obligations |

Conservatively invalidate the whole run when any relevant project source,
definition, dependency, pin or toolchain changes. Hash all project `.lean` files
and the selected manuscript/definition sources if a precise dependency closure
is unavailable. A clean revision alone is not a snapshot when files are dirty.
Dependency pins require a clean checkout or a digest of its dirty changes.
Fresh builds update compiler evidence; changed meanings also require fresh
fidelity review. Never reuse an old review merely because a theorem name survived.

## Status and trust

- **UNSTARTED / STATED:** missing proof; an elaborating skeleton is only STATED.
- **LEAN-PROVED:** the encoded statement passes the selected compiler/trust gates;
  source correspondence is still a separate question.
- **FORMALIZED:** current compiler evidence and current source fidelity both pass
  for the requested claim and its necessary definitions/dependencies.
- **CONDITIONAL:** checked only under additional unproved hypotheses or domain
  axioms; name them. Never describe the original unconditional claim as proved.
- **REFUTED:** retain a checked counterexample and the exact refuted statement.
- **BLOCKED:** identify missing source, tool, mathematical step or environment.
- **STALE:** evidence belongs to a different relevant snapshot.

Classify every reported axiom:

| Class | Examples | Treatment |
|---|---|---|
| Placeholder | `sorryAx` | Incomplete; reject completion even if transitive or generated from `admit` |
| Standard logic | `propext`, `Classical.choice`, `Quot.sound` | Record; normally accepted under Lean/Mathlib's usual trust policy |
| Domain/custom | An assumed theorem or project `axiom` | Disclose as conditional; never hide it among library axioms |
| Compiler/native evaluation | `Lean.ofReduceBool`, other implementation-specific trust axioms | Separate trust extension; do not call it ordinary kernel-only verification |
| Unclassified | Unfamiliar name | Inspect before accepting; do not infer safety from its namespace |

Use an existing repository trust policy. Without one, use the standard logical
set as the completion default and report other classes without silently approving
them. Theorem parameters are not axioms: `theorem t (h : P) : P := h` has no
axioms but proves only `P → P`. Inspect full types and custom definitions too.

Scope matters: an unused `sorry` does not contaminate an independent theorem's
axiom set, but does block a requested whole-file/manuscript completeness claim.
Enumerate every requested target; a green default build can omit entire modules.
Logs, hashes and reviews are reproducibility evidence, not cryptographic proof
that natural-language meaning was captured.
