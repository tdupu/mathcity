#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

decision_files=(
  "$ROOT/formulas/pr-pipeline-briefed.formula.toml"
  "$ROOT/formulas/create-issue-briefed.formula.toml"
  "$ROOT/formulas/planning-briefed.formula.toml"
  "$ROOT/formulas/commission-work-briefed.toml"
  "$ROOT/formulas/formula-creator-math.toml"
  "$ROOT/formulas/smoke-test-briefed.toml"
  "$ROOT/formulas/no-brainer-candidate-curate.toml"
)

for file in "${decision_files[@]}"; do
  rg -q '`brief_kind: decision`|brief_kind: decision' "$file" ||
    { echo "missing decision brief_kind in $file" >&2; exit 1; }
  rg -q '`gate_profile: decision`|gate_profile: decision' "$file" ||
    { echo "missing decision gate_profile in $file" >&2; exit 1; }
  rg -q '`feedback_sink: brief_quality_failure`|feedback_sink: brief_quality_failure' "$file" ||
    { echo "missing brief-quality feedback sink in $file" >&2; exit 1; }
  rg -q 'decision` gate profile|`decision` gate profile|gate_profile: decision' "$file" ||
    { echo "missing explicit decision profile wording in $file" >&2; exit 1; }
done

repair="$ROOT/formulas/brief-producer-repair.toml"
rg -q 'brief_kind: producer_repair' "$repair"
rg -q 'gate_profile: producer_repair' "$repair"
rg -q 'feedback_sink: brief_quality_failure' "$repair"
rg -q 'producer_repair` gate profile' "$repair"

printf 'producer decision gate-profile check: ok\n'
