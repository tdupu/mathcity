# Locate or create the Lean workspace

Invoke `using-leanpowers` and take the `lean-project` route.

## What to do

1. If `lean_project_dir` is set, verify it is a Lean workspace: a `lakefile.lean`
   or `lakefile.toml` AND a `lean-toolchain` must both be present.
2. If it is not set, locate the workspace from the bead's repository context.
3. If no workspace exists and the task requires one, create it with `lean-project`.

## Report

State the absolute workspace path, the `lean-toolchain` contents, and whether the
workspace was found or created. If you created it, say what template you used.

## Stop conditions

- More than one candidate workspace and no way to choose: STOP and report both.
  Do not guess; a wrong workspace silently formalizes into the wrong project.
- The path exists but is not a Lean workspace: STOP and say what is missing.
