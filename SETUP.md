# Setup

Parent: [README.md](./README.md)

This document explains setup from first principles. It distinguishes the code
checkout, the Gas City runtime, the bead data backup, and operator tools.

## Support Matrix

| Environment | Status | Notes |
| --- | --- | --- |
| MacOS | Supported target | Requires `git`, `gc`, `bd`, Dolt, and `tmux`. Optional math tools depend on subdomain use. |
| Linux | Supported target | Same conceptual setup as MacOS. Package-manager commands differ by distribution. |
| Windows | Not directly documented yet | Use WSL2 for the same Linux-style setup. Native Windows operation needs a documented validation pass before it is advertised as supported. |
| Codex | Supported operator | Codex can edit the pack checkout, run local tests, and work through documented skills. |
| Claude Code | Supported operator | Claude Code can use materialized skills and operate as an outside clerk or pack-development agent. |
| Gas City agents | Supported runtime | City-managed agents execute formulas and orders after the pack is imported into a city. |

## Concepts

Mathcity has three planes:

| Plane | What lives there |
| --- | --- |
| Code | The `mathcity` Git checkout: skills, formulas, policies, docs, tests, orders, and agents. |
| Runtime | A Gas City city with rigs, sessions, imports, formulas, orders, and brief queues. |
| Bead data | `bd` state backed by Dolt. This is operational data and should use a private backup remote. |

## Required Tools

Install these before using mathcity in a city:

| Tool | Purpose |
| --- | --- |
| `git` | Clone and update code repositories. |
| `gc` | Gas City CLI and supervisor. |
| `bd` | Beads issue/work tracker. |
| Dolt | Storage backend for bead data. |
| `tmux` | Session substrate for Gas City workers. |

Optional tools depend on subdomains: Magma, SageMath, Lean/Mathlib search,
LMFDB access, or other project-specific tools.

## Install Into A City

1. Create or choose a Gas City city.
2. Import the Gas City base packs that provide shared formulas and roles.
3. Import mathcity into the city root and into rig defaults.
4. Run import checks.
5. Add rigs for repositories you want the city to manage.
6. Configure private bead backup using [README-dolt.md](./README-dolt.md).

The older [docs/INSTALL.md](./docs/INSTALL.md) contains command-level examples.
Use placeholders such as `<city-root>`, `<repo-root>`, `<github-owner>`, and
`<repo>` when adapting commands.

## Operator Setup

### Codex

Open the mathcity checkout in Codex. Codex can run local documentation checks,
unit tests, smoke tests, and source edits. Codex should not start the Mayor or
city runtime unless the user explicitly asks.

### Claude Code

Use materialized skills when operating from Claude Code. For documentation work,
the relevant skills are:

- `mathcity-dev.improve-documentation`
- `mathcity-dev.check-documentation-policy`
- `mathcity-dev.new-documentation-policy`

### Gas City Runtime

Once imported, Gas City agents can run mathcity formulas such as
`work-briefed`, `build-basic-briefed`, `brief-shuffle`, and
`smoke-test-briefed`. Mayor and clerk operation are separate:

- [README-mayor.md](./README-mayor.md)
- [README-clerk.md](./README-clerk.md)

## Verify

Cheap local verification:

```sh
bash scripts/run-local-tests.sh
```

Runtime verification requires a configured city:

```sh
gc import check
gc formula list
gc order list
gc doctor
```

## Unsupported Or Unknown

If an environment has not been validated, document it as unknown rather than
assuming it works. Planned support should link to an issue in the mathcity issue
tracker.
