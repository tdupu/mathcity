#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
CHECK="$ROOT/assets/scripts/checks/brief-check.sh"
TMP=${TMPDIR:-/tmp}/brief-quality-failure-smoke.$$
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP"

grep -Fq 'brief_quality_failure.v1' "$ROOT/formulas/brief-shuffle.toml"
grep -Fq '.brief-quality-failure-pile' "$ROOT/formulas/brief-producer-failure-record.toml"
grep -Fq '.producer-failure-pile' "$ROOT/formulas/brief-producer-failure-record.toml"
grep -Fq 'producer_contract: brief-producer.v1' "$ROOT/formulas/brief-producer-failure-record.toml"
grep -Fq 'brief.quality_failure' "$ROOT/formulas/brief-producer-failure-record.toml"

cat > "$TMP/failure.toml" <<'EOF'
schema = "brief_quality_failure.v1"
brief_id = "brief-123"
brief_kind = "decision"
gate_profile = "decision"
source_bead = "bead-456"
source_surface = "decisions-track"
failed_gate = "G1"
failure_summary = "Test evidence is missing."
failure_fingerprint = "missing-test-evidence"
status = "untriaged"
EOF

GC_BRIEF_PATH="$TMP/failure.toml" "$CHECK" brief-quality-failure-record

sed '/^source_bead = /d' "$TMP/failure.toml" > "$TMP/missing-source-bead.toml"
if GC_BRIEF_PATH="$TMP/missing-source-bead.toml" "$CHECK" brief-quality-failure-record; then
  echo "brief-check accepted fixture missing source_bead" >&2
  exit 1
fi

echo "brief-quality-failure smoke test: PASS"
