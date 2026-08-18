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

Context resolution also probes the rig's Gas City data plane and reports
`city_active` / `city_endpoint`. A rig configured for Dolt server mode
(`.beads/dolt-server.port`) whose endpoint refuses a connection is reported as
`city_active: false`, and every `briefs`/`work` command then fails immediately
with `MCTL_CITY_NOT_ACTIVE` instead of blocking on a `bd` timeout. A rig with
no server port uses embedded Dolt; it reports `city_active: null` and is never
gated. `mctl context` always answers, so it stays usable for diagnosing a
down city.

### Mctl Brief Inspection

Read canonical brief beads and their redundant filesystem cache without
repairing any drift:

```sh
python3 assets/scripts/mctl.py briefs list --status open --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs show mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs options mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs doctor --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs doctor --brief mc-abc --city <city-root> --rig mathcity --json
```

From the MathCity source checkout, brief commands require both `--city` and
`--rig`. The bead store is canonical; pile, stack, decision TOML, and legacy
decisions-track files are reported as redundant artifacts and are never
rewritten by these read-only commands.

If a command inspects a matching legacy decisions-track row, or if that legacy
manifest cannot be parsed, the JSON `diagnostics` envelope includes
`MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED`. That blocker remains until the #38
decisions-track migration proof/canary has passed and the result is explicitly
authorized; historical migration marker files alone are not trusted proof.

### Mctl Brief Mutations

Decision mutations are dry-run first and bead-first. The canonical bead update
is applied before redundant decision TOML, stack index, event, or trace writes:

```sh
python3 assets/scripts/mctl.py briefs adjudicate mc-abc --verdict approve --reason "ready" --dry-run --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs adjudicate mc-abc --verdict approve --reason "ready" --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --dry-run --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --city <city-root> --rig mathcity --json
```

Mutation commands refuse to run without a reason, refuse to run when `briefs
doctor` reports `ERROR` or `FATAL`, and preserve the legacy
`MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED` guard from read-only inspection.

### Mctl Work Controls

Inspect brief-backed work and dispatch provenance from the same explicit city
context:

```sh
python3 assets/scripts/mctl.py work ready --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py work status mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py work provenance mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py work dispatch mc-abc --dry-run --city <city-root> --rig mathcity --json
```

`work ready` is derived from canonical decision beads and excludes blocked,
non-approving, already-dispatched, or invalid-provenance items. Dispatch uses
the same effect-plan model as brief mutation commands. Fixture-backed dispatch
writes dispatch provenance plus MCTL event/trace rows; live dispatch remains
fail-closed until a dedicated runtime canary enables the actual `gc sling`
handoff.

Every bead read is a full `bd list` subprocess, so core functions that already
hold a bead snapshot pass it down (`doctor_briefs(ctx, brief_id, beads)`)
rather than re-reading per brief. `work ready` reads beads once for the whole
rig; re-introducing a per-brief read makes the command scale with rig size and
is caught by `tests/mctl/test_bd_invocation_count.py`.

### Mctl Bead-Backed Tests

Most `tests/mctl` files inject `MCTL_BEADS_FIXTURE`, which bypasses the `bd`
adapter and reads static JSONL. Two suites deliberately do not:

- `tests/mctl/test_real_bead_store.py` builds an isolated embedded-Dolt store
  with `bd init` and drives mctl against real beads, including the canonical
  `bd update` write path. It never touches a production rig, and skips when
  `bd` is not installed.
- `tests/mctl/test_bd_invocation_count.py` puts a counting `bd` shim on `PATH`
  to bound how many times a command shells out.

`bd` and `gc` are external contracts mctl does not own.
`tests/mctl/test_external_command_contracts.py` pins the argv mctl builds
and checks every long flag in it against the flags the installed `bd` and
`gc` actually advertise, so a rename upstream fails the suite instead of
silently producing a broken command.

`bd` subprocess timeout defaults to 30s and is overridable with
`MCTL_BD_TIMEOUT_SECONDS`. It must stay clear of the ~1-5s a full read of a
large rig costs, since reads are slowest exactly when the data plane is
degraded and these commands are most needed.

When adding bead fixtures, prefer `related` dependencies between a brief and
its source bead — that is what live rigs use, and real `bd` refuses to close a
brief that a `blocks` dependency still blocks.

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
