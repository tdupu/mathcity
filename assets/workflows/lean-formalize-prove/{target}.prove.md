# Prove one obligation

Invoke `using-leanpowers` and take the `lean-prove` route.

## Rules

1. **One obligation at a time**, in dependency order.
2. **`sorry` is a recorded gap, never a silent one.** If you leave one, it must
   have a named entry in the gap document and an open bead. The three counts —
   `sorry`s in the project, gap entries, open beads — must match exactly.
3. **Never weaken the statement to make it provable.** Adding a hypothesis to close
   a goal changes the theorem. If the statement cannot be proved as aligned, that is
   a finding to report, not an edit to make.
4. Take the `lean-search` route before writing a proof by hand; the lemma likely
   exists.

## Evidence

Read the build exit code DIRECTLY — never through a pipe into `head`/`tail`, which
reports the pipe's status and turns a failure into rc=0. Never trigger a cold
Mathlib build.

## Report

Per obligation: proved / `sorry` / blocked, the exact build command, its exit code,
and for any `sorry` the matching gap entry and bead id.
