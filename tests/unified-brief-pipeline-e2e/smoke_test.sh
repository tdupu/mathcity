#!/usr/bin/env bash
# Source-local end-to-end fixture for the unified brief pipeline.
#
# CT7.4 launch provenance:
# - launch surface: direct shell fixture, source-local only
# - expected result label: PASS, PARTIAL, BLOCKED-SUBSTRATE, INVALID-SPEC, or FAIL
# - proves: legacy decisions-track inventory, typed profile checks, stack-first
#   presentation selection, legacy duplicate suppression, defer filtering, and
#   shared brief_quality_failure.v1 feedback validation compose coherently
# - non-goals: does not mutate live .beads, does not run gc orders, does not
#   prove BART live runtime path resolution, does not run bulk migration
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INVENTORY="$ROOT/assets/scripts/brief-decisions-track-inventory.py"
CHECK="$ROOT/assets/scripts/checks/brief-check.sh"
PRESENT="$ROOT/skills/present-briefs/SKILL.md"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/unified-brief-pipeline-e2e.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

result() {
  local label="$1"
  local message="$2"
  printf '%s: %s\n' "$label" "$message"
}

require() {
  local message="$1"
  shift
  if ! "$@"; then
    result FAIL "$message"
    exit 1
  fi
}

STACK_SELECTOR="$TMP/stack-selector.py"
LEGACY_SELECTOR="$TMP/legacy-selector.py"
awk '/^### Method 1 — stack index/{section=1; next} section && /python3 - "\$STACK_DIR" <<'"'"'PY'"'"'/{found=1; next} found && /^PY$/{exit} found {print}' "$PRESENT" >"$STACK_SELECTOR"
awk '/^### Method 2 — decisions-track legacy fallback/{section=1; next} section && /python3 - "\$DECISIONS_DIR" <<'"'"'PY'"'"'/{found=1; next} found && /^PY$/{exit} found {print}' "$PRESENT" >"$LEGACY_SELECTOR"
require "INVALID-SPEC missing stack selector in present-briefs" test -s "$STACK_SELECTOR"
require "INVALID-SPEC missing legacy selector in present-briefs" test -s "$LEGACY_SELECTOR"

RIG="$TMP/rig"
BRIEFS="$RIG/.beads/briefs"
PILE="$BRIEFS/.pile"
STACK="$BRIEFS/stack"
DECISIONS="$RIG/.beads/decisions-track"
MIGRATIONS="$BRIEFS/migrations"
mkdir -p "$PILE" "$STACK" "$DECISIONS" "$MIGRATIONS"

cat >"$DECISIONS/manifest.jsonl" <<'JSONL'
{"n":1,"slug":"approve-unified-pipeline","status":"ready","unlock_count":9}
{"n":2,"slug":"future-deferred","status":"ready","defer_until":"2999-01-01","unlock_count":8}
{"n":3,"slug":"already-adjudicated","status":"adjudicated","unlock_count":7}
JSONL

cat >"$DECISIONS/01-approve-unified-pipeline-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Approve Unified Pipeline
MD
cat >"$DECISIONS/02-future-deferred-brief.md" <<'MD'
---
status: ready-for-adjudication
defer_until: 2999-01-01
---
# Future Deferred
MD
cat >"$DECISIONS/03-already-adjudicated-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Already Adjudicated
MD
cat >"$DECISIONS/99-orphan-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Orphan
MD

INVENTORY_OUT="$MIGRATIONS/2026-08-15-decisions-track-inventory.jsonl"
python3 "$INVENTORY" inventory --rig-root "$RIG" --output "$INVENTORY_OUT"
python3 - "$INVENTORY_OUT" <<'PY'
import json, sys
rows=[json.loads(line) for line in open(sys.argv[1]) if line.strip()]
actions={(row.get("legacy_n"), row.get("legacy_slug")): row["migration_action"] for row in rows}
assert actions[(1,"approve-unified-pipeline")] == "copy_to_pile"
assert actions[(2,"future-deferred")] == "copy_to_pile_deferred"
assert actions[(3,"already-adjudicated")] == "preserve_terminal"
assert actions[(99,"orphan")] == "preserve_file_without_manifest"
PY

DECISION_BRIEF="$PILE/01-approve-unified-pipeline-brief.md"
cat >"$DECISION_BRIEF" <<'MD'
---
brief_kind: decision
gate_profile: decision
legacy_source: decisions-track/01-approve-unified-pipeline-brief.md
feedback_sink: brief_quality_failure
---
action_block:
  on_approve: []
  on_reject: []
  on_defer: [{type: snooze, interval: 7d}]

Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=e2e-decision classified_at=2026-08-15T00:00:00Z
MD
GC_BRIEF_PATH="$DECISION_BRIEF" sh "$CHECK" decision-profile

LOST_BRIEF="$PILE/02-lost-bead-filter-brief.md"
cat >"$LOST_BRIEF" <<'MD'
---
brief_kind: lost_bead_filter
gate_profile: lost_bead_filter
feedback_sink: brief_quality_failure
source_bead: gsp-source-1
fingerprint: empty_assignee_after_verified_sling
threshold_count: 3
distinct_bead_count: 3
replay_command: bd show gsp-source-1
false_positive_risk: medium
---
Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=e2e-lost-bead classified_at=2026-08-15T00:00:00Z
MD
GC_BRIEF_PATH="$LOST_BRIEF" sh "$CHECK" lost-bead-filter-profile

REPAIR_BRIEF="$PILE/03-producer-repair-brief.md"
cat >"$REPAIR_BRIEF" <<'MD'
---
brief_kind: producer_repair
gate_profile: producer_repair
feedback_sink: brief_quality_failure
producer_contract: brief-producer-repair.v1
repair_source_formula: brief-producer-failure-rollup
repair_failed_gate: G9
repair_failure_fingerprint: synthetic-missing-provenance
replay_command: bash tests/producer-failure-rollup-routing/smoke_test.sh
---
Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=e2e-repair classified_at=2026-08-15T00:00:00Z
MD
GC_BRIEF_PATH="$REPAIR_BRIEF" sh "$CHECK" producer-repair-profile

cp "$DECISION_BRIEF" "$STACK/01-approve-unified-pipeline-brief.md"
cp "$LOST_BRIEF" "$STACK/02-lost-bead-filter-brief.md"
cat >"$STACK/.index.jsonl" <<JSONL
{"slug":"approve-unified-pipeline","path":"$STACK/01-approve-unified-pipeline-brief.md","unlock_count":9,"brief_kind":"decision","gate_profile":"decision","legacy_source":"decisions-track/01-approve-unified-pipeline-brief.md"}
{"slug":"lost-bead-filter","path":"$STACK/02-lost-bead-filter-brief.md","unlock_count":5,"brief_kind":"lost_bead_filter","gate_profile":"lost_bead_filter"}
{"slug":"future-stack","path":"$STACK/future-stack.md","unlock_count":99,"brief_kind":"decision","gate_profile":"decision","defer_until":"2999-01-01"}
JSONL

stack_out="$(python3 "$STACK_SELECTOR" "$STACK")"
grep -Fq "$STACK/01-approve-unified-pipeline-brief.md" <<<"$stack_out"
grep -Fq "$STACK/02-lost-bead-filter-brief.md" <<<"$stack_out"
if grep -Fq "$STACK/future-stack.md" <<<"$stack_out"; then
  result FAIL "future-deferred stack brief was presented"
  exit 1
fi

legacy_out="$(STACK_INDEX="$STACK/.index.jsonl" MIGRATION_MARKER="$INVENTORY_OUT" INCLUDE_LEGACY_DECISIONS=1 python3 "$LEGACY_SELECTOR" "$DECISIONS")"
if grep -Fq "$DECISIONS/01-approve-unified-pipeline-brief.md" <<<"$legacy_out"; then
  result FAIL "legacy duplicate was presented despite stack legacy_source mapping"
  exit 1
fi
if grep -Fq "$DECISIONS/02-future-deferred-brief.md" <<<"$legacy_out"; then
  result FAIL "future-deferred legacy brief was presented"
  exit 1
fi
if grep -Fq "$DECISIONS/03-already-adjudicated-brief.md" <<<"$legacy_out"; then
  result FAIL "adjudicated legacy brief was presented"
  exit 1
fi

FAILURE="$BRIEFS/.brief-quality-failure-pile/01-approve-unified-pipeline.toml"
mkdir -p "$(dirname "$FAILURE")"
cat >"$FAILURE" <<'TOML'
schema = "brief_quality_failure.v1"
brief_id = "01-approve-unified-pipeline"
brief_kind = "decision"
gate_profile = "decision"
source_bead = "unknown"
source_surface = "decisions-to-briefs"
failed_gate = "G9"
failure_summary = "synthetic E2E rejection feedback"
failure_fingerprint = "synthetic-e2e-feedback"
status = "untriaged"
TOML
GC_BRIEF_PATH="$FAILURE" sh "$CHECK" brief-quality-failure-record

result PASS "source-local unified brief pipeline E2E fixture passed"
