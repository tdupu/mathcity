# Testing

Run from the `gascity-packs` repository root:

```bash
bash mathcity/tests/lost-bead-filter/smoke_test.sh
```

The harness compiles the validator, checks valid and invalid fixtures, runs the
downstream and upstream rollups, parses the formula and order TOML files, and
greps the relevant skills for their output contracts.

## What This Covers

- `lost-bead-classification.v1` validation.
- `dispatch-provenance.v1` validation.
- Downstream filter-rule rollup at threshold 3.
- No downstream candidate below threshold.
- Upstream repair grouping for known dispatch provenance.
- Unknown provenance routed to provenance recording instead of formula blame.
- Formula and order TOML parse checks for the two rollup formulas.
- Skill documentation contract checks.
- Linked Beads contract checks for `type=event` observations and `type=decision` rollup briefs.

## What This Does Not Cover

- Live `bd` writes; those run only in formula or skill execution with authorized Beads access.
- Live `gc sling` execution.
- Actual brief filing into `.beads/briefs/.pile`; the smoke test checks the contract, not the live pile.
- Formula controller execution in a running city.

Those are intentionally outside the smoke test because the filter is
read-only/additive until a repair brief is adjudicated.

If the default `python3` on a machine is unusable, set `PYTHON` to a Python
3.11 or newer executable:

```bash
PYTHON=/path/to/python3 bash mathcity/tests/lost-bead-filter/smoke_test.sh
```

Expected result:

```text
PASS - 19 checks passed
```
