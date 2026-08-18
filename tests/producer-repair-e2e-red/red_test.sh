#!/usr/bin/env bash
# Historical RED test (Track 2: FORMULA repair feedback process).
#
# This used to probe old live `/private/tmp/gc-formula-repair-e2e*` state and
# the current gascity-packs bead store. That made the suite correctly expose
# the missing behavior, but it was not a stable local regression. The source
# repair now has two local obligations:
#
#   1. A genuine rejected-dir fixture creates producer-failure records without
#      hand-running `gc event emit`.
#   2. A thresholded rollup has concrete instructions to create or reuse the
#      repair-review decision bead before dispatch.
#
# Live proof 4 is still runtime acceptance: the next real gate rejection should
# create `.beads/briefs/.producer-failure-pile/<slug>.toml` on its own.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

bash "$ROOT/tests/brief-quality-failure-record-backfill/smoke_test.sh"
bash "$ROOT/tests/producer-failure-rollup-routing/smoke_test.sh"

grep -Fq 'trigger = "condition"' "$ROOT/orders/brief-producer-failure-record-on-rejected-pile.toml"
grep -Fq '.producer-failure-pile' "$ROOT/orders/brief-producer-failure-rollup-on-pile.toml"
grep -Fq 'on = "brief.quality_failure_recorded"' "$ROOT/orders/brief-producer-failure-rollup-on-record.toml"

printf 'producer repair feedback e2e regression: ok\n'
