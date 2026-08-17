# Development Guide

Parent: [README.md](./README.md)

This guide explains how mathcity development is governed by policies, specs,
briefs, and tests.

## Source Of Truth

| Surface | Purpose |
| --- | --- |
| [POLICY-POLICY.md](./POLICY-POLICY.md) | How policy domains, rule IDs, check skills, and amendment skills work. |
| [POLICY-formulas.md](./POLICY-formulas.md) | Rules for formula TOMLs and formula creation. |
| [POLICY-beads.md](./POLICY-beads.md) | Bead types, labels, research-bead lifecycle, and stale-bead handling. |
| [subdomains/dev/POLICY.md](./subdomains/dev/POLICY.md) | Pack portability, ownership boundaries, upstream changes, and development hygiene. |
| [subdomains/dev/POLICY-city.md](./subdomains/dev/POLICY-city.md) | Runtime city operations. |
| [subdomains/dev/POLICY-documentation.md](./subdomains/dev/POLICY-documentation.md) | Documentation quality, examples, setup, and navigation. |

Specs should explain behavior by citing current formulas, skills, orders, and
policy. If a spec contradicts source, source wins and the spec is fixed.

## Front Door

All ordinary work should enter through `mathcity.work`. It routes by shape to
briefed formulas such as `work-briefed`, `simple-work-briefed`,
`build-basic-briefed`, `planning-briefed`, and `smoke-test-briefed`.

Formula creation currently uses `formula-work` as a dispatch skill for
`formula-creator-math`. That is a known planned improvement: formula creation
should begin with a formula plan, then produce docs, tests, and the formula
brief as one lifecycle. Track that rework in #3.

## Issue And PR Handoffs

Upstream issue and PR text is prepared by mathcity formulas, then adjudicated
before anything is published:

| Surface | Purpose |
| --- | --- |
| `create-issue-briefed` | Drafts a template-complete issue body and files it as a decision brief. |
| `pr-pipeline-briefed` | Drafts a template-complete PR body and files it as a decision brief. |

Original upstream repositories:

- [Gas City](https://github.com/gastownhall/gascity)
- [Gas City packs](https://github.com/gastownhall/gascity-packs)
- [Beads](https://gastownhall.github.io/beads/)

## Tests

Current cheap tests:

```sh
bash scripts/run-local-tests.sh
```

### Mctl Context

Resolve an explicit local fixture context with:

```sh
python3 assets/scripts/mctl.py context --city tests/mctl/fixtures/city_root --rig mathcity --json
```

`mctl` reads `rigs.imports.mathcity.source` (or the matching default import)
from `city.toml`. It uses an explicit rig `db` value when present; otherwise,
the resolved rig ID is the database name.

Use `testing-work` and `smoke-test-briefed` for lightweight generated smoke
tests. Use `test-execution-request` before risky, slow, or costly test
execution.

## Documentation Workflow

Run `improve-documentation` for feature, formula, skill, policy, setup, or
workflow changes. Then run `check-documentation-policy` and compare the result
against the requested documentation changes.

New features need examples and tests. Existing gaps can be tracked as backlog,
but they should not be presented as complete.

## Planned Development Surfaces

| Surface | Tracker | Current status |
| --- | --- | --- |
| `mathcity doctor` | #1 | Planned tiered health/test/documentation report. |
| `create-test-briefed` | #2 | Planned test-design workflow for example-driven certification. |
| `formula-work` lifecycle rework | #3 | Planned upgrade from dispatch wrapper to plan -> formula -> docs -> tests -> brief lifecycle. |
