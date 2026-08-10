#!/bin/sh
# gate-test-execution-declaration.sh
#
# Gate G-test-execution, step 1: verify the brief carries a non-silent
# test-execution tri-state declaration.
#
# Exit 0 = PASS (declaration present and parseable)
# Exit 1 = FAIL (silent, absent, or unparseable)
#
# Source spec: he-8akk (G-test-execution gate)
#
set -eu

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
ROOT="${BRIEF_ROOT:-.beads/briefs}"

fail() {
  echo "gate-test-execution-declaration: $*" >&2
  exit 1
}

# Resolve brief path from environment, gc metadata, or staging fallback.
metadata_value() {
  key="$1"
  if [ -z "${GC_BEAD_ID:-}" ] || ! command -v gc >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    return 0
  fi
  gc bd show "$GC_BEAD_ID" --json 2>/dev/null |
    jq -r --arg key "$key" '.[0].metadata[$key] // empty' 2>/dev/null || true
}

brief_path() {
  if [ -n "${GC_BRIEF_PATH:-}" ]; then
    printf '%s\n' "$GC_BRIEF_PATH"
    return 0
  fi
  value="$(metadata_value "gc.brief.path")"
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
    return 0
  fi
  # staging fallback
  find . -path "./$ROOT/.staging/*/brief.md" -type f 2>/dev/null | sort | head -n 1
}

BRIEF="$(brief_path)"
[ -n "$BRIEF" ] || fail "gate_blocked_reason: test-execution-unstated — could not resolve brief path"
[ -f "$BRIEF" ] || fail "gate_blocked_reason: test-execution-unstated — brief file not found: $BRIEF"

# Accepted patterns (from he-8akk tri-state spec):
#   test-execution: PASSED — ...
#   test-execution: NOT APPLICABLE — ...
#   test-execution: REQUIRED — ...
#
# Silent or absent → FAIL.
if grep -Eq '^test-execution:[[:space:]]+(PASSED|NOT APPLICABLE|REQUIRED)[[:space:]]+[-—]' "$BRIEF"; then
  # Valid tri-state found.
  STATE="$(grep -E '^test-execution:[[:space:]]+(PASSED|NOT APPLICABLE|REQUIRED)[[:space:]]+[-—]' "$BRIEF" | head -n 1)"
  echo "gate-test-execution-declaration: PASS — $STATE"
  exit 0
fi

# Also accept bare REQUIRED without reason text (explicit gate-block form).
if grep -Eq '^test-execution:[[:space:]]*REQUIRED' "$BRIEF"; then
  echo "gate-test-execution-declaration: PASS — REQUIRED (gate-block declared)"
  exit 0
fi

# Also accept legacy gate_status.G14_test_execution_silent format (briefs produced
# before the tri-state field was codified, 2026-07-12 backwards-compat window).
if grep -Eq '^[[:space:]]+G14_test_execution_silent:[[:space:]]*PASS' "$BRIEF"; then
  STATE="$(grep -E '^[[:space:]]+G14_test_execution_silent:' "$BRIEF" | head -n 1)"
  echo "gate-test-execution-declaration: PASS (legacy gate_status format) — $STATE"
  exit 0
fi
if grep -Eq '^[[:space:]]+G14_test_execution_silent:[[:space:]]' "$BRIEF"; then
  FOUND="$(grep -E '^[[:space:]]+G14_test_execution_silent:' "$BRIEF" | head -n 1)"
  fail "gate_blocked_reason: test-execution-unstated — legacy G14 gate_status not PASS: $FOUND"
fi

# Not found or malformed.
if grep -Eq '^test-execution:' "$BRIEF"; then
  FOUND="$(grep -E '^test-execution:' "$BRIEF" | head -n 1)"
  fail "gate_blocked_reason: test-execution-unstated — unrecognized declaration: $FOUND"
fi

fail "gate_blocked_reason: test-execution-unstated — brief is silent on test-execution; add tri-state declaration"
