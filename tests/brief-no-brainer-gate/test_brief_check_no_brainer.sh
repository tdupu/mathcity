#!/bin/sh
# RED-phase TDD harness for Track 1 (BRIEF no-brainer/gate system) of the
# 2026-07-28 four-filter-E2E-tracks directive. Exercises brief-check.sh's
# actual no-brainer subcommand logic (no-brainer-classification-evidence,
# no-brainer-safety, no-brainer-execute-safety) against real fixture briefs
# -- the exact coverage gap TESTING.md in tests/claude-native-repairs-brief-filter
# names ("does not cover actual subcommand logic, gate parsing, no-brainer
# rules, kill switches, or live formula behavior").
#
# Each case asserts an EXPECTED exit status (0 = pass/gate-clear,
# 1 = fail/gate-blocked) against a synthetic brief.md fixture. A case whose
# actual exit status does not match its expected status is reported as a
# FAILURE of this harness (RED) -- meaning brief-check.sh's real behavior
# diverges from what the no-brainer/gate contract requires.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
# "Rig root" for brief-check.sh's relative-path resolution is the mathcity
# pack dir itself (has assets/brief-pipeline/... directly under it) --
# matches a real brief-operator worker's rig cwd, NOT the gascity-packs
# monorepo root (which has assets/ under mathcity/, one level deeper).
RIG_ROOT="$(cd "$HERE/../.." && pwd)"
CHECK="$RIG_ROOT/assets/scripts/checks/brief-check.sh"

PASS_COUNT=0
FAIL_COUNT=0

run_case() {
  name="$1"
  expected_status="$2"
  brief_content="$3"
  subcommand="$4"

  tmp="$(mktemp -d)"
  brief_path="$tmp/brief.md"
  printf '%s\n' "$brief_content" > "$brief_path"

  status=0
  # brief-check.sh resolves the no-brainer category registry as a path
  # RELATIVE TO CWD ("assets/brief-pipeline/..."), matching its documented
  # convention that step checks run with the rig root (gascity-packs) as
  # cwd -- must cd there before invoking, or every known_no_brainer case
  # false-fails on "missing registry" regardless of the actual property
  # under test (caught by this harness's own first run).
  (cd "$RIG_ROOT" && GC_BRIEF_PATH="$brief_path" "$CHECK" "$subcommand") >"$tmp/out" 2>"$tmp/err" || status=$?

  if [ "$status" = "$expected_status" ]; then
    echo "PASS: $name (exit=$status, expected=$expected_status)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL: $name (exit=$status, expected=$expected_status)"
    echo "  --- stderr ---"
    sed 's/^/  /' "$tmp/err"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
  rm -rf "$tmp"
}

echo "=== G9 classifier evidence: known_no_brainer, valid ==="
run_case "valid known_no_brainer passes" 0 \
  'G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.9 classified_at=2026-07-28T00:00:00Z' \
  no-brainer-classification-evidence

echo "=== G9 classifier evidence: missing G9 line entirely ==="
run_case "missing G9 evidence fails" 1 \
  '# some brief with no G9 line at all' \
  no-brainer-classification-evidence

echo "=== G9 classifier evidence: category not in registry ==="
run_case "unregistered category fails" 1 \
  'G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=totally-made-up-category stop_gates_clear=true confidence=0.9 classified_at=2026-07-28T00:00:00Z' \
  no-brainer-classification-evidence

echo "=== G9 classifier evidence: confidence below 0.85 threshold ==="
run_case "low confidence fails" 1 \
  'G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.5 classified_at=2026-07-28T00:00:00Z' \
  no-brainer-classification-evidence

echo "=== G9 classifier evidence: stop_gates_clear=false for known_no_brainer ==="
run_case "stop_gates_clear=false fails" 1 \
  'G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=false confidence=0.9 classified_at=2026-07-28T00:00:00Z' \
  no-brainer-classification-evidence

echo "=== no-brainer-safety: G5 Server-touching FAIL blocks ==="
run_case "G5 FAIL blocks no-brainer-safety" 1 \
  'G5 Server-touching: FAIL
G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.9 classified_at=2026-07-28T00:00:00Z' \
  no-brainer-safety

echo "=== no-brainer-safety: clean gates pass ==="
run_case "clean gates pass no-brainer-safety" 0 \
  'G5 Server-touching: PASS
G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.9 classified_at=2026-07-28T00:00:00Z' \
  no-brainer-safety

# The two execute-safety cases below set BRIEF_ROOT into a sandbox: the gate
# now appends a durable audit line under $BRIEF_ROOT/decisions/, and without
# the override that record would be written into the pack checkout itself.
# Full arming/stop-gate/audit coverage lives in
# tests/brief-no-brainer-arming/test_no_brainer_arming.sh.

echo "=== no-brainer-execute-safety: kill switch ENGAGED (flag=false) blocks execution ==="
KS_CITY="$(mktemp -d)"
mkdir -p "$KS_CITY/.beads"
printf 'false\n' > "$KS_CITY/.beads/auto_merge_enabled"
tmp="$(mktemp -d)"
mkdir -p "$tmp/rig/.beads/briefs"
brief_path="$tmp/brief.md"
printf '%s\n' 'G5 Server-touching: PASS
G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.9 classified_at=2026-07-28T00:00:00Z' > "$brief_path"
status=0
(cd "$RIG_ROOT" && GC_CITY="$KS_CITY" GC_RIG_ROOT="$tmp/rig" BRIEF_ROOT="$tmp/rig/.beads/briefs" GC_BRIEF_PATH="$brief_path" "$CHECK" no-brainer-execute-safety) >"$tmp/out" 2>"$tmp/err" || status=$?
if [ "$status" = "1" ]; then
  echo "PASS: kill switch engaged blocks execute-safety (exit=$status, expected=1)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "FAIL: kill switch engaged blocks execute-safety (exit=$status, expected=1)"
  echo "  --- stderr ---"; sed 's/^/  /' "$tmp/err"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
rm -rf "$tmp" "$KS_CITY"

echo "=== no-brainer-execute-safety: kill switch flag ABSENT no longer allows execution (arming required) ==="
# Was: "absent kill switch allows execute-safety (expected=0)".  Absent-means-go
# put the brake in the go position by default; auto-execution now requires a
# positive arming token at both the city and rig level, so an absent brake and
# an absent arm token both mean DO NOT EXECUTE.
KS_CITY2="$(mktemp -d)"
mkdir -p "$KS_CITY2/.beads"
tmp="$(mktemp -d)"
mkdir -p "$tmp/rig/.beads/briefs"
brief_path="$tmp/brief.md"
printf '%s\n' 'G5 Server-touching: PASS
G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.9 classified_at=2026-07-28T00:00:00Z' > "$brief_path"
status=0
(cd "$RIG_ROOT" && GC_CITY="$KS_CITY2" GC_RIG_ROOT="$tmp/rig" BRIEF_ROOT="$tmp/rig/.beads/briefs" GC_BRIEF_PATH="$brief_path" "$CHECK" no-brainer-execute-safety) >"$tmp/out" 2>"$tmp/err" || status=$?
if [ "$status" = "1" ] && grep -q '"reason":"not_armed"' "$tmp/rig/.beads/briefs/decisions/no-brainer-execution.jsonl"; then
  echo "PASS: absent kill switch alone does not arm execute-safety (exit=$status, expected=1, reason=not_armed)"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "FAIL: absent kill switch alone does not arm execute-safety (exit=$status, expected=1)"
  echo "  --- stderr ---"; sed 's/^/  /' "$tmp/err"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
rm -rf "$tmp" "$KS_CITY2"

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
