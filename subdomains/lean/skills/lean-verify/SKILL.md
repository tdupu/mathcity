---
name: lean-verify
description: Use before reporting a Lean proof, file, project or manuscript formalization as checked, or after Lean changes that may invalidate evidence.
---

# Verify the selected formal artifacts

Input: explicit target names/modules and current workspace snapshot.
Output: compiler and trust evidence under the
[evidence contract](../lean-workflow/references/evidence.md), never a fidelity claim.

1. Enumerate all requested declarations and modules from the source map. Include
   supporting definitions and scope exclusions. Inspect whether project defaults
   actually build those modules; an empty/default success is insufficient.
2. Run the configured project validation and explicit selected module builds.
   Capture actual commands, cwd, versions, exit status and complete output.
   Use [tool recipes](../lean-workflow/references/tools.md); LSP success alone is
   not a replacement for the build used by the project.
3. Compile probes printing each selected declaration's full type and axioms.
   Inspect relevant definitions and implicit assumptions. Classify placeholders,
   standard logic, domain axioms and native/compiler trust separately. A scan
   for `sorry` is only triage; check transitive `sorryAx` too.
4. Record current source/definition/dependency hashes and pins. Mark older
   evidence stale when context changed. An unrelated unused admission blocks
   whole-scope completeness without falsely contaminating independent theorems.
5. Return LEAN-PROVED only for targets passing all applicable checks. Name
   conditional assumptions, failed targets and unclassified trust. Route the
   current evidence to `lean-fidelity` before claiming source formalization.

Example: an axiom-free `theorem main (h : P) : P := h` is conditional, not a
proof of the manuscript's unconditional `P`.
