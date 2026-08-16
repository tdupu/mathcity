#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$ROOT/assets/scripts/checks/brief-check.sh"
BACKFILL="$ROOT/assets/scripts/checks/brief-quality-failure-record-backfill.sh"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/brief-quality-failure-backfill.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

BRIEFS="$TMP_DIR/.beads/briefs"
REJECTED="$BRIEFS/.pile/.rejected"
mkdir -p "$REJECTED/producer-one" "$REJECTED/decision-one" "$REJECTED/repair-one"

cat >"$REJECTED/producer-one/brief.md" <<'EOF'
---
artifact: gsp-source1
brief_slug: producer-one
brief_kind: artifact
gate_profile: standard
track: artifact
producer_contract: brief-producer.v1
source_formula: simple-work-briefed
source_step: file-brief
routing_path: "simple-work-briefed"
---

# Producer brief
EOF

cat >"$REJECTED/producer-one/rejection.md" <<'EOF'
---
artifact: gsp-source1
slug: producer-one
rejected_at: 2026-08-15T23:00:00Z
gate_profile: standard
---

# Rejection Record

### G4 Critical-review (required, kind=review) - FAIL

Critical review was missing at deposit.
EOF

cat >"$REJECTED/decision-one/brief.md" <<'EOF'
---
artifact: none
brief_slug: decision-one
brief_kind: decision
gate_profile: decision
track: policy-disposition
legacy_source: decisions-track/01-decision-one-brief.md
feedback_sink: brief_quality_failure
---

# Decision brief
EOF

cat >"$REJECTED/decision-one/rejection-record.md" <<'EOF'
---
slug: decision-one
rejected_at: 2026-08-15T23:01:00Z
gate_profile: decision
---

# Rejection Record

### G9 No-brainer-filter (required, kind=judgment) - FAIL

Classifier state was absent.
EOF

cat >"$REJECTED/repair-one/brief.md" <<'EOF'
---
artifact: gsp-repair
brief_slug: repair-one
brief_kind: producer_repair
gate_profile: producer_repair
producer_contract: brief-producer-repair.v1
source_formula: brief-producer-failure-rollup
source_step: launch-repair-review
---

# Repair brief
EOF

cat >"$REJECTED/repair-one/rejection.md" <<'EOF'
# Rejection Record

### G9 No-brainer-filter - FAIL

Repair classifier missing.
EOF

python3 "$ROOT/assets/scripts/brief-quality-failure-record.py" \
  --brief-root "$BRIEFS" \
  --slug producer-one \
  --dry-run >/dev/null
test ! -e "$BRIEFS/.brief-quality-failure-pile"
test ! -e "$BRIEFS/.producer-failure-pile"

BRIEF_ROOT="$BRIEFS" sh "$BACKFILL" >/dev/null
BRIEF_ROOT="$BRIEFS" sh "$BACKFILL" >/dev/null

QUALITY_PRODUCER="$BRIEFS/.brief-quality-failure-pile/producer-one.toml"
QUALITY_DECISION="$BRIEFS/.brief-quality-failure-pile/decision-one.toml"
PRODUCER_RECORD="$BRIEFS/.producer-failure-pile/producer-one.toml"
DECISION_PRODUCER_RECORD="$BRIEFS/.producer-failure-pile/decision-one.toml"

test -f "$QUALITY_PRODUCER"
test -f "$QUALITY_DECISION"
test -f "$PRODUCER_RECORD"
test -f "$DECISION_PRODUCER_RECORD"
test ! -f "$BRIEFS/.brief-quality-failure-pile/repair-one.toml"
test ! -f "$BRIEFS/.producer-failure-pile/repair-one.toml"

GC_BRIEF_PATH="$QUALITY_PRODUCER" sh "$CHECK" brief-quality-failure-record
GC_BRIEF_PATH="$QUALITY_DECISION" sh "$CHECK" brief-quality-failure-record

grep -Fq 'schema = "brief-producer-failure.v1"' "$PRODUCER_RECORD"
grep -Fq 'source_formula = "simple-work-briefed"' "$PRODUCER_RECORD"
grep -Fq 'failed_gate = "G4"' "$PRODUCER_RECORD"
grep -Fq 'failed_gate_name = "Critical-review"' "$PRODUCER_RECORD"
grep -Fq 'source_formula = "policy-disposition"' "$DECISION_PRODUCER_RECORD"
grep -Fq 'failed_gate = "G9"' "$DECISION_PRODUCER_RECORD"
grep -Fq 'failed_gate_name = "No-brainer-filter"' "$DECISION_PRODUCER_RECORD"

producer_count="$(find "$BRIEFS/.producer-failure-pile" -type f -name '*.toml' | wc -l | tr -d ' ')"
quality_count="$(find "$BRIEFS/.brief-quality-failure-pile" -type f -name '*.toml' | wc -l | tr -d ' ')"
test "$producer_count" = "2"
test "$quality_count" = "2"

printf 'brief-quality-failure backfill check: ok\n'
