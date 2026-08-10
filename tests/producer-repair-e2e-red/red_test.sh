#!/usr/bin/env bash
# RED test (Track 2: FORMULA repair feedback process, Codex TDD directive 2026-07-28).
# Proves the full classification -> threshold rollup -> repair-review decision-brief
# chain has never completed end-to-end, despite the first stage (record-signals)
# having genuinely fired for real gate-rejected briefs.
set -euo pipefail

FAIL=0

echo "=== Stage 1: record-signals produced real signal artifacts? ==="
SIGNAL_COUNT=0
for f in /private/tmp/gc-formula-repair-e2e-claude.IFBdT6/.producer-failure-pile/*.toml \
         /private/tmp/gc-formula-repair-e2e/.producer-failure-pile/*.toml; do
  [ -f "$f" ] || continue
  SIGNAL_COUNT=$((SIGNAL_COUNT + 1))
  echo "  found: $f"
done
if [ "$SIGNAL_COUNT" -ge 1 ]; then
  echo "  PASS (stage 1 has real evidence: $SIGNAL_COUNT signal file(s))"
else
  echo "  FAIL stage 1: no producer-failure-pile signal artifacts found anywhere"
  FAIL=1
fi

echo "=== Stage 2: rollup batch (threshold reached, repair review launched)? ==="
# NOTE (corrected 2026-07-28 per Codex review): stage 2 firing is REAL, EXPECTED
# evidence, not surprising -- it required a manual --threshold override (the
# organic default threshold=3 has never been reached by real production
# signals; the live pile has zero accumulated signals as of this test). This
# stage is not itself the RED condition; it's supporting evidence that the
# rollup/batch-write logic works when triggered. Stage 3 is the true RED.
BATCH_COUNT=0
for root in /private/tmp/gc-formula-repair-e2e-claude.IFBdT6 /private/tmp/gc-formula-repair-e2e <city-root>/.beads/briefs; do
  d="$root/.producer-failure-rollups/batches"
  if [ -d "$d" ]; then
    BATCH_COUNT=$((BATCH_COUNT + $(find "$d" -name '*.md' 2>/dev/null | wc -l)))
  fi
done
if [ "$BATCH_COUNT" -ge 1 ]; then
  echo "  REAL EVIDENCE (expected, with manual threshold override): $BATCH_COUNT rollup batch file(s) exist -- rollup logic fires correctly when triggered"
else
  echo "  FAIL stage 2: no rollup batch file exists anywhere (rollup logic itself untested)"
  FAIL=1
fi

echo "=== Stage 3: repair-review decision brief bead exists (gascity-packs rig store)? ==="
# This is the true RED condition: the launch-repair-review step (which reads
# open.jsonl groups at the ORGANIC default threshold and is meant to sling
# gascity-packs/gc.run-operator on brief-producer-repair) has never fired --
# zero repair-review decision beads exist anywhere in the rig store.
REPAIR_BEAD_COUNT=$(bd -C <city-root>/gascity-packs search "producer_contract: brief-producer-repair.v1" 2>/dev/null | grep -c '^gsp-' || true)
if [ "$REPAIR_BEAD_COUNT" -ge 1 ]; then
  echo "  GREEN: $REPAIR_BEAD_COUNT repair-review decision bead(s) found"
else
  echo "  RED (this IS the missing behavior): no repair-review decision brief exists"
  FAIL=1
fi

echo
if [ "$FAIL" -eq 1 ]; then
  echo "RED CONFIRMED: the classification->rollup->repair-review chain has NOT completed end-to-end."
  echo "Stages 1-2 (record-signals, rollup-batch-write) have genuine real evidence when triggered;"
  echo "the missing behavior is specifically: thresholded batch -> repair-review decision/work bead."
  exit 1
else
  echo "GREEN: full chain confirmed -- record-signals, rollup, and repair-review decision brief all present."
  exit 0
fi
