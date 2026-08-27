#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FORMULA="$ROOT/formulas/brief-producer-failure-rollup.toml"

require_text() {
  local pattern="$1"
  local message="$2"
  if ! rg -q -- "$pattern" "$FORMULA"; then
    printf 'producer-failure-rollup routing check failed: %s\n' "$message" >&2
    exit 1
  fi
}

require_text 'repair_rig_dir="\$\(gc rig list --json' 'repair bead must be created/found in the target rig store'
require_text 'repair_title="\[brief-producer-repair\]' 'repair review bead must use a stable repair title'
require_text 'repair_bead="\$\(bd -C "\$repair_rig_dir" search "\$failure_fingerprint"' 'repair bead must be searched in the target rig store before creation'
require_text 'bd -C "\$repair_rig_dir" create "\$repair_title"' 'repair bead must be created in the target rig store when missing'
require_text '--type=decision' 'repair bead must be a decision bead'
require_text '--description "\$repair_description"' 'repair bead description must carry the failure batch context'
require_text 'bd -C "\$repair_rig_dir" show "\$repair_bead"' 'assignee guard must inspect the target rig store'
require_text '--var operator_target="gascity-packs/gc.run-operator"' 'repair workflow must keep child steps in the target rig store'
require_text 'repair_workflow="\$\(printf' 'dispatch verification must check the returned workflow root'
require_text 'bd -C "\$repair_rig_dir" show "\$repair_workflow"' 'workflow verification must inspect the target rig store'

# --- close path: rollup groups never leave the open set ---
# open.jsonl is named for a state the formula never assigns: every group is
# written status="open" and nothing ever transitions one. Closure must be read
# from the repair bead in the target rig store (B2.8), not from a status field
# that the next full rewrite of open.jsonl would clobber.
require_text 'group_repair_status\(\)' \
  'build-rollups must resolve the repair-bead status of each group before writing open.jsonl'
require_text 'Omit any group whose repair bead is .closed.' \
  'build-rollups must exclude closed groups from open.jsonl'
require_text 'closure state UNKNOWN' \
  'an unresolvable repair rig must report UNKNOWN loudly, never silently as open (P6.2)'

# --- assignee guard must skip the group, not fail the whole step ---
# An already-dispatched group is the expected steady state once repair work is
# actually running; aborting the step on it latches the entire rollup molecule.
require_text 'skipping this group' \
  'assignee guard must skip an already-dispatched group'
if rg -q -- 'aborting producer repair sling' "$FORMULA"; then
  printf 'producer-failure-rollup routing check failed: %s\n' \
    'assignee guard must not abort the step - that latches the whole molecule' >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/producer-repair-routing.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
REPAIR_BRIEF="$TMP_DIR/quoted-repair-brief.md"
cat >"$REPAIR_BRIEF" <<'EOF'
---
producer_contract: brief-producer-repair.v1
repair_source_formula: "simple-work-briefed"
repair_failed_gate: "G9"
repair_failure_fingerprint: "synthetic-e2e-missing-target-file"
---

# Quoted Repair Brief
EOF

GC_BRIEF_PATH="$REPAIR_BRIEF" sh "$ROOT/assets/scripts/checks/brief-check.sh" producer-repair-self-exclusion

printf 'producer-failure-rollup routing check: ok\n'
