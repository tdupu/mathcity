# Verify build, coverage and axioms

Invoke `using-leanpowers` and take the `lean-verify` route.

## What to establish

1. **The project builds.** Run it, redirect output to a file, read `$?` directly.
   A pipe into `head`/`tail` reports the PIPE's status and turns a failing build
   into rc=0. Never trigger a cold Mathlib build.
2. **Axioms.** For each target theorem, print the axiom dependencies. `sorryAx`
   anywhere means the theorem is NOT proved, whatever the build says. Report any
   axiom beyond the standard three (propext, Classical.choice, Quot.sound).
3. **Coverage.** Which inventory claims have a corresponding proved declaration.

## Report

Exact build command, exit code, per-theorem axiom list, and the coverage table.
Evidence, not assertion: quote the command and its output.
