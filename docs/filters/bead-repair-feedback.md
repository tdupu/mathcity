# Bead Repair Feedback

This filter turns repeated lost-bead observations into upstream repair
proposals. It is the feedback-control half of the bead filter system: when the
same failure fingerprint points back to a dispatch source or formula, the
system files a repair decision brief.

## Purpose

A downstream filter rule helps classify future lost beads. An upstream repair
tries to prevent the failure from recurring. This path groups only records that
carry repair-candidate evidence and enough provenance to identify a plausible
source.

## Inputs

- `lost-bead-classification.v1` records. Each of these becomes a real, linked
  `type=event` bead (created via `bd create`, linked to its source bead with
  `bd dep add ... --type related`) — this is durable, dep-list-verifiable
  evidence.
- `dispatch-provenance.v1` records when available. These are **cache-file
  only** — filesystem TOML records under the classification/provenance cache
  directory, never materialized as a separate bd bead. A decision brief that
  cites provenance is summarizing the cache files, not linking to a
  "provenance event bead" — no such bead type exists.
- A classification/provenance cache directory, defaulting to
  `.beads/lost-bead-classifications`.
- The schemas under `assets/bead-filter/`.

## Outputs

- `upstream-candidates.jsonl` rows with candidate kind
  `upstream_repair_brief`.
- One decision brief per thresholded upstream repair candidate.
- Links from the repair decision brief to contributing classification,
  provenance, and affected source beads.

## How To Invoke

Start with read-only bead diagnoses:

```sh
/bead-check <bead-id>
```

After classification and provenance records have been exported, run:

```sh
gc sling mathcity.brief-operator lost-bead-upstream-repair-rollup --formula \
  --var classification_root=.beads/lost-bead-classifications \
  --var output_path=.beads/lost-bead-classifications/upstream-candidates.jsonl \
  --var threshold=3
```

The formula runs `lost-bead-filter-check.sh` first, then
`lost-bead-filter.py rollup-upstream`.

## Safety Rules

- Records with `root_cause.repair_candidate = false` are ignored.
- Unknown provenance is grouped as `UNKNOWN_PROVENANCE` and must not be blamed
  on a specific formula or skill.
- The formula files decision briefs only. It does not patch skills, formulas,
  gates, policy, or bead lifecycle state.
- The repair proposal must name examples, shared fingerprint, suspected source,
  confidence, alternatives, non-goal, replay command, and expected reduction in
  manual triage.

## Test Status

The same smoke harness covers upstream grouping:

```sh
bash mathcity/tests/lost-bead-filter/smoke_test.sh
```

In the July 2026 E2E pass, static upstream behavior passed: known-source strand
failures route to the verify-assignee gate, unknown provenance remains
unattributed, and unknown provenance does not blame `mathcity.work`. The live
upstream workflow still needs to run after the downstream live workflow
finishes.
