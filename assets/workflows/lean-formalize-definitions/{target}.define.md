# Implement the agreed definitions

Invoke `using-leanpowers` and take the `lean-define` route.

## Implement what was agreed

Implement the representations from the design step — the ones that were chosen and
justified. If, while implementing, you find a chosen representation does not work,
do NOT silently substitute another: report the conflict and stop. A substituted
representation invalidates the design review that approved it.

## What to produce

Definitions, structures and instances for the agreed representations. No proofs of
the source's theorems here beyond what an instance genuinely requires.

## Evidence required

The project must still elaborate when you are done.

- Run the build and read the exit code DIRECTLY — never through a pipe into
  `head`/`tail`, which reports the pipe's status and turns a failure into rc=0.
- Never trigger a cold Mathlib build. If one appears unavoidable, stop and file a
  blocker.

## Report

Each definition added with its file and line, the exact build command, its exit
code, and PASS or FAIL. A claim that it builds is not evidence that it builds.
