---
name: lean-doctor
description: Use before Lean proof edits, maintenance or upgrades, or when the project's build baseline is unknown.
---

# Establish the baseline

Input: workspace and selected modules. Output: actual versions, dependency
state, target coverage, build receipts and blockers. This leaf inspects and
runs checks; installation and repairs return to their owners.

Read [tool recipes](../lean-workflow/references/tools.md). Record the toolchain,
lakefile and manifest, dependency revisions and dirty state. Check available
Lean/Lake and optional LSP/search capabilities; missing optional tools do not
invalidate a working CLI path.

Run the configured project validation and explicitly build selected modules.
Verify that the default target actually covers the intended source files.
Capture working directory, command, exit code and output. A cached success is
not fresh evidence after changes.

On failure, classify toolchain/dependency availability, existing source errors,
or a missing target. Hand the concrete failure to `lean-diagnose`; preserve the
baseline distinction so later edits are not blamed for old breakage. Independent
source analysis may continue. Never report a clean baseline from style checks,
editor diagnostics alone, or a command that did not run.

Example: `lake build` succeeds but `Project.Appendix` is not a default target;
build that selected module explicitly before accepting the baseline.
