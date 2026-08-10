# Bead Repair No-Brainer And Gates

This filter turns repeated lost-bead observations into proposed downstream
filter rules. It does not repair beads directly; it files decision briefs that
ask whether a repeated manual classification should become a rule.

## Purpose

Some stranded or lost beads have the same shape every time: a verified sling
left no assignee, a hidden blocker prevented dispatch, or another repeatable
condition made a bead look ready while no worker could use it. The downstream
filter path groups those repeated labels so future sweeps can classify the
shape consistently.

## Inputs

- `lost-bead-classification.v1` TOML records, usually emitted by `/bead-check`
  and exported from linked event beads.
- A classification cache directory, defaulting to
  `.beads/lost-bead-classifications`.
- The schema at `assets/bead-filter/lost-bead-schema.toml`.

## Outputs

- `downstream-candidates.jsonl` rows with candidate kind
  `downstream_filter_rule`.
- One decision brief per thresholded candidate, written into the brief pile.
- Links from the decision brief bead to contributing classification event beads
  and affected source beads.

## How To Invoke

Classify individual beads first:

```sh
/bead-check <bead-id>
```

After enough classification records have been exported, run the rollup:

```sh
gc sling mathcity.brief-operator lost-bead-classification-rollup --formula \
  --var classification_root=.beads/lost-bead-classifications \
  --var output_path=.beads/lost-bead-classifications/downstream-candidates.jsonl \
  --var threshold=3
```

The rollup runs `lost-bead-filter-check.sh` first, then
`lost-bead-filter.py rollup-downstream`.

## Safety Rules

- `/bead-check` is read-only and only proposes a disposition.
- The rollup formula never mutates source beads directly.
- The file-brief step must not run `bd close`, `bd update`, `bd defer`,
  `bd supersede`, or `gc sling`.
- New rules are proposed through decision briefs; they are not silently added
  to policy or gates.

## Test Status

The smoke harness is:

```sh
bash mathcity/tests/lost-bead-filter/smoke_test.sh
```

The lower-level check is:

```sh
sh mathcity/assets/scripts/checks/lost-bead-filter-check.sh \
  mathcity/tests/lost-bead-filter/fixtures
```

In the July 2026 E2E pass, the static downstream filter behavior passed. The
live city workflow was launched, but execution was blocked by a stale shuffler
lock before the Claude-backed brief operator could complete the live output.
