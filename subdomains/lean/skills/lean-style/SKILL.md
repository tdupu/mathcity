---
name: lean-style
description: Use when auditing Lean formatting, naming, documentation, imports or mechanical style issues.
---

# Audit and repair mechanical style

Input: working files, local conventions and audit-versus-fix scope.
Output: located findings and, when requested, checked mechanical edits.

Establish a `lean-doctor` baseline. Read neighboring maintained modules and the
project's actual lint/build configuration. Audit module documentation, import
organization, mathematical names, whitespace, notation and temporary debug
scaffolding. Use available project linters, recording their command and output.

Keep mathematical signposts and source attribution. Treat lexical findings as
candidates: comments containing `sorry` are not proof holes, and terminal `simp`
is not automatically inferior to `simp only`. Avoid universal proof/file-length
limits copied from another project. Do not rename APIs, change hypotheses,
generalize definitions or golf proofs as incidental formatting.

For authorized repairs, edit one owned file at a time, preserve the complete
statement/definition context and build affected targets. Route substantive
changes to `lean-refactor`, `lean-generalize` or `lean-golf`. Return unresolved
findings explicitly and refresh `lean-verify` evidence after edits.

Example: remove trailing whitespace without altering a multiline binder;
changing a theorem's name requires a caller-aware refactoring instead.
