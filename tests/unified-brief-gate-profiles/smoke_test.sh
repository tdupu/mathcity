#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$ROOT/assets/scripts/checks/brief-check.sh"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/unified-brief-gate-profiles.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

valid_decision="$TMP_DIR/valid-decision.md"
missing_g9="$TMP_DIR/missing-g9.md"
valid_lost="$TMP_DIR/valid-lost.md"
missing_provenance="$TMP_DIR/missing-provenance.md"
lost_body_fields="$TMP_DIR/lost-body-fields.md"
valid_repair="$TMP_DIR/valid-repair.md"
repair_body_fields="$TMP_DIR/repair-body-fields.md"
missing_decision_provenance="$TMP_DIR/missing-decision-provenance.md"
decision_body_provenance="$TMP_DIR/decision-body-provenance.md"
decision_late_frontmatter="$TMP_DIR/decision-late-frontmatter.md"
missing_repair_contract="$TMP_DIR/missing-repair-contract.md"

cat >"$valid_decision" <<'EOF'
---
brief_kind: decision
gate_profile: decision
legacy_source: decisions-track/42-valid-decision-brief.md
feedback_sink: brief_quality_failure
---
action_block:
  on_approve: []
  on_reject: []
  on_defer: [{type: snooze, interval: 7d}]

Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=decision-profile-fixture classified_at=2026-08-15T00:00:00Z
EOF

sed '/^G9 No-brainer-filter:/d' "$valid_decision" >"$missing_g9"

cat >"$valid_lost" <<'EOF'
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
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=lost-filter-fixture classified_at=2026-08-15T00:00:00Z
EOF

sed '/^source_bead:/d' "$valid_lost" >"$missing_provenance"
cat >"$lost_body_fields" <<'EOF'
---
brief_kind: lost_bead_filter
gate_profile: lost_bead_filter
feedback_sink: brief_quality_failure
---
source_bead: gsp-source-1
fingerprint: empty_assignee_after_verified_sling
threshold_count: 3
distinct_bead_count: 3
replay_command: bd show gsp-source-1
false_positive_risk: medium
Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=lost-filter-body-fixture classified_at=2026-08-15T00:00:00Z
EOF

sed '/^legacy_source:/d' "$valid_decision" >"$missing_decision_provenance"
sed '/^legacy_source:/d' "$valid_decision" >"$decision_body_provenance"
printf '%s\n' 'legacy_source: decisions-track/42-valid-decision-brief.md' >>"$decision_body_provenance"
cat >"$decision_late_frontmatter" <<'EOF'
Decision text before a delimiter.
---
brief_kind: decision
gate_profile: decision
legacy_source: decisions-track/42-valid-decision-brief.md
feedback_sink: brief_quality_failure
---
action_block:
  on_approve: []
  on_reject: []
  on_defer: [{type: snooze, interval: 7d}]
Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=late-frontmatter-fixture classified_at=2026-08-15T00:00:00Z
EOF

cat >"$valid_repair" <<'EOF'
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
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=repair-profile-fixture classified_at=2026-08-15T00:00:00Z
EOF

sed '/^producer_contract:/d' "$valid_repair" >"$missing_repair_contract"

cat >"$repair_body_fields" <<'EOF'
---
brief_kind: producer_repair
gate_profile: producer_repair
feedback_sink: brief_quality_failure
producer_contract: brief-producer-repair.v1
---
repair_source_formula: brief-producer-failure-rollup
repair_failed_gate: G9
repair_failure_fingerprint: synthetic-missing-provenance
replay_command: bash tests/producer-failure-rollup-routing/smoke_test.sh
Gate Evidence
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=repair-body-fixture classified_at=2026-08-15T00:00:00Z
EOF

GC_BRIEF_PATH="$valid_decision" sh "$CHECK" decision-profile
if GC_BRIEF_PATH="$missing_g9" sh "$CHECK" decision-profile 2>/dev/null; then
  echo "expected decision profile without G9 evidence to fail" >&2
  exit 1
fi
GC_BRIEF_PATH="$valid_lost" sh "$CHECK" lost-bead-filter-profile
if GC_BRIEF_PATH="$missing_provenance" sh "$CHECK" lost-bead-filter-profile 2>/dev/null; then
  echo "expected lost-bead profile without provenance to fail" >&2
  exit 1
fi
if GC_BRIEF_PATH="$lost_body_fields" sh "$CHECK" lost-bead-filter-profile 2>/dev/null; then
  echo "expected lost-bead body-only metadata to fail" >&2
  exit 1
fi
GC_BRIEF_PATH="$valid_repair" sh "$CHECK" producer-repair-profile
if GC_BRIEF_PATH="$repair_body_fields" sh "$CHECK" producer-repair-profile 2>/dev/null; then
  echo "expected producer-repair body-only metadata to fail" >&2
  exit 1
fi
if GC_BRIEF_PATH="$missing_repair_contract" sh "$CHECK" producer-repair-profile 2>/dev/null; then
  echo "expected producer-repair profile without producer_contract to fail" >&2
  exit 1
fi
for key in repair_source_formula repair_failed_gate repair_failure_fingerprint replay_command; do
  missing_repair_field="$TMP_DIR/missing-$key.md"
  sed "/^${key}:/d" "$valid_repair" >"$missing_repair_field"
  if GC_BRIEF_PATH="$missing_repair_field" sh "$CHECK" producer-repair-profile 2>/dev/null; then
    echo "expected producer-repair profile without $key to fail" >&2
    exit 1
  fi
done
missing_decision_metadata="$TMP_DIR/missing-decision-metadata.md"
sed '/^feedback_sink:/d' "$valid_decision" >"$missing_decision_metadata"
printf '%s\n' 'feedback_sink: brief_quality_failure' >>"$missing_decision_metadata"
if GC_BRIEF_PATH="$missing_decision_metadata" sh "$CHECK" decision-profile 2>/dev/null; then
  echo "expected decision profile with body-only feedback_sink to fail" >&2
  exit 1
fi
if GC_BRIEF_PATH="$missing_decision_provenance" sh "$CHECK" decision-profile 2>/dev/null; then
  echo "expected decision profile without provenance to fail" >&2
  exit 1
fi
if GC_BRIEF_PATH="$decision_body_provenance" sh "$CHECK" decision-profile 2>/dev/null; then
  echo "expected decision profile with body-only provenance to fail" >&2
  exit 1
fi
if GC_BRIEF_PATH="$decision_late_frontmatter" sh "$CHECK" decision-profile 2>/dev/null; then
  echo "expected late delimiter section to fail as frontmatter" >&2
  exit 1
fi
missing_decision_action="$TMP_DIR/missing-decision-action.md"
sed '/^action_block:/,/^$/d' "$valid_decision" >"$missing_decision_action"
if GC_BRIEF_PATH="$missing_decision_action" sh "$CHECK" decision-profile 2>/dev/null; then
  echo "expected decision profile without action_block to fail" >&2
  exit 1
fi
grep -Fq '[profiles.decision]' "$ROOT/assets/brief-pipeline/gates.toml"
grep -Fq '[profiles.lost_bead_filter]' "$ROOT/assets/brief-pipeline/gates.toml"
grep -Fq '[profiles.producer_repair]' "$ROOT/assets/brief-pipeline/gates.toml"
grep -Fq 'enum = ["standard", "no_brainer", "test_execution", "experiment", "decision", "lost_bead_filter", "producer_repair"]' "$ROOT/formulas/brief-gate-keep.toml"

echo "PASS - unified brief gate profile checks"
