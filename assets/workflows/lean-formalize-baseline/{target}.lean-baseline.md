# Establish toolchain and build baseline

Invoke `using-leanpowers` and take the `lean-doctor` route.

## Critical constraint — never trigger a cold Mathlib build

`allow_cold_build` defaults to **false**. A cold Mathlib build is a multi-hour
operation. If establishing the baseline would require one:

1. Do NOT start it.
2. File a blocker: `bd create -t task --labels blocker,kolchin-monitor`.
3. Report the stage as BLOCKED and stop.

Only proceed with a cold build if `allow_cold_build` is explicitly `true`.

## What to do

1. Run `lean-doctor` in the workspace to report toolchain, Mathlib revision and
   cache state.
2. Establish that the project elaborates. Prefer the cheapest sufficient probe —
   e.g. `lake env lean` on a file importing Mathlib — over a full `lake build`.
3. Read the exit code DIRECTLY. Do not pipe the command into `head`/`tail`: a pipe
   reports the exit status of the LAST command, so a failing build reads as rc=0.
   Redirect to a file, then read `$?`.

## Report

Toolchain version, Mathlib revision, cache warm/cold, the exact probe command you
ran, its exit code, and PASS or FAIL. Evidence, not assertion.
