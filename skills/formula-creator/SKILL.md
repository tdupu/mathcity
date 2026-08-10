---
name: formula-creator
description: Create a new Gas City formula TOML in a pack checkout and validate the gc/bd command surface before committing. Use whenever the user says "create a formula", "add a formula to <pack>", "new formula for <workflow>", "formula-creator", or asks to codify a multi-step agent workflow as a reusable gc formula. For mathcity formulas that must end in a decision brief, use formula-creator-math.
---

# formula-creator

Create a **formula TOML** in a Gas City pack and run basic shape, command
surface, and safety checks before committing. This is the generic creator; the
mathcity-specific `formula-creator-math` skill adds the required briefed
terminal-step policy.

## Inputs

Before writing anything, identify:

- `<pack-root>`: the checkout or imported pack root that contains `pack.toml`.
- `<formula-name>`: lowercase, hyphenated, and stable.
- `<formula-path>`: normally `<pack-root>/formulas/<formula-name>.toml`.
- The intended runner pool for each step.
- Whether the formula is deterministic shell work, agent work, or mixed.

If the target is a mathcity formula, switch to `formula-creator-math` unless the
user explicitly asks for the generic creator.

## TOML Skeleton

```toml
description = """
One-paragraph description of what this formula does.
Include: purpose, input assumptions, exit criteria, and what it does NOT do.
"""
formula = "<formula-name>"
version = 1

[requires]
formula_compiler = ">=2.0.0"

[catalog]
name = "<formula-name>"
description = "One-line catalog entry shown by gc formula list."

[vars]
[vars.source_bead]
description = "Source bead or artifact identifier."
required = true
```

Add a `[[steps]]` block for each workflow step:

```toml
[[steps]]
id = "step-id"
title = "Human-readable title"
needs = ["previous-step-id"]
metadata = { "gc.run_target" = "{{run_target}}" }
description = """
What the agent does in this step.

Exit criteria: what must be true before the step is complete.
"""
```

Rules:

- `formula` must match the filename stem.
- Step ids are stable kebab-case identifiers.
- Every non-root step declares `needs`.
- Use `metadata."gc.run_target"` for pool routing; do not put model names such
  as `haiku`, `sonnet`, or `opus` in `gc.run_target`.
- Prefer variables for deployment-specific pool names.
- Put reusable check scripts under `<pack-root>/assets/scripts/checks/`.

## Optional Check Block

Attach a deterministic shell check when the step has mechanical completion
criteria:

```toml
[steps.check]
max_attempts = 3

[steps.check.check]
mode = "exec"
path = "<pack-root>/assets/scripts/checks/<check-script>.sh"
timeout = "2m"
```

Use a pack-root-relative path only if the current Gas City version resolves it
for this field; otherwise use a generated absolute path in the consuming city
or add a setup step that installs the script. Never rely on `../` traversal.

## Pool Routing

Choose targets by role, not by one concrete session instance:

| Step character | Typical `gc.run_target` |
|---|---|
| Deterministic bookkeeping | `gc.run-operator` |
| Implementation work | `gc.implementation-worker` |
| Requirements or design | `gc.requirements-planner` or `gc.design-author` |
| Review or synthesis | `gc.review-synthesizer` |
| Pack-local operations | `<pack>.<agent>` |

If the right target varies by install, expose it as `[vars.<name>]` and use
`"{{<name>}}"` in metadata.

## Validation

Run these before committing:

```bash
cd <pack-root>

# TOML parse check
python3 -c "import tomllib; tomllib.load(open('formulas/<formula-name>.toml','rb'))"

# Formula appears in the catalog once the active city imports this checkout
gc formula show <formula-name>

# Secret scan for the changed formula
gitleaks detect --no-git --source formulas/<formula-name>.toml
```

If the formula text includes `gc` or `bd` commands, verify every command against
the current CLI help. Do not invent subcommands.

## Commit Discipline

Show the diff before committing. Commit the formula, any check scripts, and any
index documentation together:

```bash
cd <pack-root>
git add formulas/<formula-name>.toml
git diff --cached
git commit -m "feat: add <formula-name> formula"
```

Push only to a remote and branch the repository owner has authorized.

## What This Skill Does Not Do

- It does not create `SKILL.md` skills; use `skill-creator-math` for mathcity
  skills.
- It does not bypass human authorization for pushes, PRs, merges, or releases.
- It does not assume a particular local checkout path or GitHub fork.
- It does not touch another pack's formulas unless the user explicitly names
  that pack and authorizes the target repository.
