# Formula Repair Feedback

This filter closes the loop from rejected briefs back to the formula that
produced the bad brief. It is for repeated producer mistakes: missing gate
evidence, invalid metadata, wrong routing, or other systematic brief-production
failures.

## Purpose

When the shuffler rejects a brief, that may be an isolated bad artifact or it
may be a producer bug. The formula repair feedback path records the rejection
as structured evidence, groups repeated fingerprints, and launches repair
review work only when the pattern is tight enough to justify a fix.

## Inputs

- Rejected brief artifacts under `.beads/briefs/.pile/.rejected/`.
- Rejection records written by the gate/shuffle path.
- Producer metadata from the rejected brief: source formula, source step,
  failed gate, routing path, and failure fingerprint.

## Outputs

- Cache records under `.producer-failure-pile/*.toml` using schema
  `brief-producer-failure.v1`.
- Durable `brief.producer_failure` event beads when the bead store is
  reachable.
- Rollup records in `.producer-failure-rollups/open.jsonl`.
- Batch files for thresholded groups.
- Repair-review work in the `gascity-packs` rig, routed to
  `gascity-packs/gc.run-operator` on `brief-producer-repair`.

## How To Invoke

Usually this is order-driven after gate rejection. For manual investigation:

```sh
gc sling mathcity.brief-operator brief-producer-failure-record --formula \
  --var artifact_root=.beads/briefs
```

Then roll up repeated patterns:

```sh
gc sling mathcity.brief-operator brief-producer-failure-rollup --formula \
  --var artifact_root=.beads/briefs \
  --var threshold=3
```

The rollup formula creates repair work in the target rig store. It must not
create an HQ `gt-*` repair bead and sling it across stores.

## Safety Rules

- Repair briefs self-exclude from producer-failure recording.
- Dedupe uses
  `source_formula + failed_gate + failure_fingerprint + source_bead`.
- Repair review launches only after the distinct-source threshold is met.
- Before slinging repair work, the formula checks required commands and checks
  that the repair bead is not already assigned.
- Failure to write cache or create the event bead must emit a loud failure
  event or exit nonzero.

## Test Status

The regression harness is:

```sh
bash mathcity/tests/producer-failure-rollup-routing/smoke_test.sh
```

In the July 2026 E2E pass, the static/regression path passed. The code path for
recording, grouping, target-rig repair bead creation, and quoted repair
metadata was validated. A live Claude-worker rerun is still needed to prove the
end-to-end worker path without outside-harness fallback.
