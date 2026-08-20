#!/bin/sh
# TDD harness for taking the no-brainer classifier OFF dry-run safely.
#
# Contract under test: `brief-check.sh no-brainer-execute-safety` is the ONE
# component that runs before any no-brainer auto-execution mutates anything.
# It must therefore be a real gate, not an advisory audit:
#
#   1. brief unresolvable            -> REFUSE (cannot prove safety of an unread artifact)
#   2. stop gates (category E etc.)  -> REFUSE, evaluated BEFORE any switch/arm state
#   3. classifier evidence           -> REFUSE unless known_no_brainer + registry
#                                       category + stop_gates_clear + confidence >= 0.85
#   4. N5 kill switch reads `false`  -> REFUSE (city, then rig)
#   5. NOT explicitly armed          -> REFUSE  <-- inverts absent-means-go
#   6. otherwise                     -> PERMIT
#
# Every terminal decision leaves a durable audit line; an unwritable audit
# sink refuses rather than executing unreconstructably.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
RIG_ROOT="$(cd "$HERE/../.." && pwd)"
CHECK="$RIG_ROOT/assets/scripts/checks/brief-check.sh"

PASS_COUNT=0
FAIL_COUNT=0
LAST_ERR=""
LAST_OUT=""
LAST_AUDIT=""

ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() {
  echo "FAIL: $1"
  if [ -n "$LAST_ERR" ] && [ -f "$LAST_ERR" ]; then
    echo "  --- stderr ---"; sed 's/^/  /' "$LAST_ERR"
  fi
  if [ -n "$LAST_AUDIT" ] && [ -f "$LAST_AUDIT" ]; then
    echo "  --- audit ---"; sed 's/^/  /' "$LAST_AUDIT"
  fi
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

GOOD_G9='G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.9 classified_at=2026-08-19T00:00:00Z'

# Build a sandbox: $SANDBOX/city (city root), $SANDBOX/rig (rig root),
# $SANDBOX/rig/.beads/briefs (BRIEF_ROOT), $SANDBOX/rig/.beads/briefs/brief.md
mk_sandbox() {
  body="$1"
  SANDBOX="$(mktemp -d)"
  mkdir -p "$SANDBOX/city/.beads"
  mkdir -p "$SANDBOX/rig/.beads/briefs/decisions"
  BRIEF="$SANDBOX/rig/.beads/briefs/brief.md"
  printf '%s\n' "$body" > "$BRIEF"
  AUDIT="$SANDBOX/rig/.beads/briefs/decisions/no-brainer-execution.jsonl"
  LAST_AUDIT="$AUDIT"
}

arm_city() { printf 'true\n' > "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"; }
arm_rig()  { printf 'true\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"; }
arm_both() { arm_city; arm_rig; }

run_gate() {
  LAST_OUT="$SANDBOX/out"; LAST_ERR="$SANDBOX/err"
  STATUS=0
  (cd "$RIG_ROOT" && \
     GC_CITY="$SANDBOX/city" \
     GC_RIG_ROOT="$SANDBOX/rig" \
     BRIEF_ROOT="$SANDBOX/rig/.beads/briefs" \
     GC_BRIEF_PATH="${FORCE_BRIEF_PATH:-$BRIEF}" \
     "$CHECK" no-brainer-execute-safety) >"$LAST_OUT" 2>"$LAST_ERR" || STATUS=$?
}

cleanup() { rm -rf "$SANDBOX"; FORCE_BRIEF_PATH=""; }
FORCE_BRIEF_PATH=""

audit_field() { # audit_field <key>  -> value of last audit line
  [ -f "$AUDIT" ] || { echo ""; return 0; }
  tail -n 1 "$AUDIT" | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p"
}

echo "=== 1. armed + clean brief + no kill switch -> PERMIT ==="
mk_sandbox "$GOOD_G9"; arm_both; run_gate
if [ "$STATUS" = "0" ] && [ "$(audit_field decision)" = "PERMITTED" ]; then
  ok "armed clean brief permits and audits PERMITTED"
else
  no "armed clean brief permits and audits PERMITTED (exit=$STATUS decision=$(audit_field decision))"
fi
cleanup

echo "=== 2. city kill switch reads false -> REFUSE even when armed ==="
mk_sandbox "$GOOD_G9"; arm_both
printf 'false\n' > "$SANDBOX/city/.beads/auto_merge_enabled"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "kill_switch_engaged" ]; then
  ok "city kill switch false refuses even when armed"
else
  no "city kill switch false refuses even when armed (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 3. rig kill switch reads false -> REFUSE even when armed ==="
mk_sandbox "$GOOD_G9"; arm_both
printf 'false\n' > "$SANDBOX/rig/.beads/auto_merge_enabled"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "kill_switch_engaged" ]; then
  ok "rig kill switch false refuses even when armed"
else
  no "rig kill switch false refuses even when armed (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 4. ABSENT arm files -> REFUSE (absent-means-go is inverted) ==="
mk_sandbox "$GOOD_G9"; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "not_armed" ]; then
  ok "absent arm files refuse (explicit arming required)"
else
  no "absent arm files refuse (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 5. absent arm files + kill switch reads true -> still REFUSE ==="
mk_sandbox "$GOOD_G9"
printf 'true\n' > "$SANDBOX/city/.beads/auto_merge_enabled"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "not_armed" ]; then
  ok "a released brake is not an arming signal"
else
  no "a released brake is not an arming signal (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 6. city armed but rig not armed -> REFUSE (both levels required) ==="
mk_sandbox "$GOOD_G9"; arm_city; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "not_armed" ]; then
  ok "city-only arming refuses; arming is per-rig"
else
  no "city-only arming refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 7. rig armed but city not armed -> REFUSE ==="
mk_sandbox "$GOOD_G9"; arm_rig; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "not_armed" ]; then
  ok "rig-only arming refuses"
else
  no "rig-only arming refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 8. expired arm token -> REFUSE (arming decays) ==="
mk_sandbox "$GOOD_G9"; arm_rig
printf 'true\nexpires=2000-01-01T00:00:00Z\n' > "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "arming_expired" ]; then
  ok "expired arm token refuses"
else
  no "expired arm token refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 9. unexpired arm token -> PERMIT ==="
mk_sandbox "$GOOD_G9"; arm_rig
printf 'true\nexpires=2999-01-01T00:00:00Z\n' > "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"
run_gate
if [ "$STATUS" = "0" ] && [ "$(audit_field decision)" = "PERMITTED" ]; then
  ok "unexpired arm token permits"
else
  no "unexpired arm token permits (exit=$STATUS decision=$(audit_field decision))"
fi
cleanup

echo "=== 10. category E via frontmatter server_touching -> REFUSE regardless of switch state ==="
mk_sandbox "---
server_touching: true
---
$GOOD_G9"
arm_both
printf 'true\n' > "$SANDBOX/city/.beads/auto_merge_enabled"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "stop_gate_server_touching" ]; then
  ok "server_touching frontmatter refuses regardless of switch state"
else
  no "server_touching frontmatter refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 11. category E via G5 FAIL token -> REFUSE while fully armed ==="
mk_sandbox "G5 Server-touching: FAIL
$GOOD_G9"
arm_both; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "stop_gate_server_touching" ]; then
  ok "G5 FAIL refuses while fully armed"
else
  no "G5 FAIL refuses while fully armed (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 12. G5b user-skill-touching -> REFUSE while fully armed ==="
mk_sandbox "G5b User-skill-touching: FAIL
$GOOD_G9"
arm_both; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "stop_gate_user_skill_touching" ]; then
  ok "G5b FAIL refuses while fully armed"
else
  no "G5b FAIL refuses while fully armed (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 13. stop gate is evaluated BEFORE arming (unarmed + server-touching names the stop gate) ==="
mk_sandbox "---
server_touching: true
---
$GOOD_G9"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "stop_gate_server_touching" ]; then
  ok "stop gate outranks arming state in the audit reason"
else
  no "stop gate outranks arming state (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 14. unresolvable brief -> REFUSE (no silent pass) ==="
mk_sandbox "$GOOD_G9"; arm_both
FORCE_BRIEF_PATH="$SANDBOX/rig/.beads/briefs/does-not-exist.md"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "brief_unresolvable" ]; then
  ok "unresolvable brief refuses instead of passing"
else
  no "unresolvable brief refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 15. missing classifier evidence -> REFUSE while fully armed ==="
mk_sandbox "# a brief with no G9 line at all"
arm_both; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "classifier_evidence_invalid" ]; then
  ok "missing G9 evidence refuses while fully armed"
else
  no "missing G9 evidence refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 16. confidence below threshold -> REFUSE while fully armed ==="
mk_sandbox 'G9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch stop_gates_clear=true confidence=0.5 classified_at=2026-08-19T00:00:00Z'
arm_both; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "classifier_evidence_invalid" ]; then
  ok "confidence < 0.85 refuses while fully armed"
else
  no "confidence < 0.85 refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 17. classifier_state=candidate -> REFUSE while fully armed ==="
mk_sandbox 'G9 No-brainer-filter: PASS classifier_state=candidate proposed_registry_extension=some-new-shape classified_at=2026-08-19T00:00:00Z'
arm_both; run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "classifier_not_no_brainer" ]; then
  ok "candidate classification refuses while fully armed"
else
  no "candidate classification refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 18. audit line carries the reconstruction fields ==="
mk_sandbox "$GOOD_G9"; arm_both; run_gate
missing=""
for key in decision reason brief_path classifier_state category confidence armed_city armed_rig kill_switch_city kill_switch_rig classifier_version classified_at recorded_at; do
  if ! tail -n 1 "$AUDIT" 2>/dev/null | grep -q "\"$key\""; then
    missing="$missing $key"
  fi
done
if [ "$STATUS" = "0" ] && [ -z "$missing" ]; then
  ok "audit line carries every reconstruction field"
else
  no "audit line carries every reconstruction field (exit=$STATUS missing:$missing)"
fi
cleanup

echo "=== 19. unwritable audit sink -> REFUSE (never execute unreconstructably) ==="
mk_sandbox "$GOOD_G9"; arm_both
rm -rf "$SANDBOX/rig/.beads/briefs/decisions"
: > "$SANDBOX/rig/.beads/briefs/decisions"   # a FILE where the directory must be
run_gate
if [ "$STATUS" = "1" ]; then
  ok "unwritable audit sink refuses"
else
  no "unwritable audit sink refuses (exit=$STATUS)"
fi
cleanup

echo "=== 20. armed run is distinguishable from the dry-run path in output ==="
mk_sandbox "$GOOD_G9"; arm_both; run_gate
armed_banner=0
grep -q "PRELIMINARY" "$LAST_ERR" && armed_banner=1
armed_decision="$(audit_field decision)"
cleanup
mk_sandbox "$GOOD_G9"; run_gate
dry_decision="$(audit_field decision)"
dry_mode="$(audit_field mode)"
if [ "$armed_banner" = "1" ] && [ "$armed_decision" = "PERMITTED" ] && \
   [ "$dry_decision" = "REFUSED" ] && [ "$dry_mode" = "dry-run" ]; then
  ok "armed and dry-run paths are distinguishable (banner + mode + decision)"
else
  no "armed and dry-run paths distinguishable (banner=$armed_banner armed=$armed_decision dry=$dry_decision mode=$dry_mode)"
fi
cleanup

# ---------------------------------------------------------------------------
# Dry-run is a RUNTIME MODE that toggles in BOTH directions, not a one-way
# arming. The recovery path (armed -> dry-run) is the one that has to work
# under pressure, so it is tested at least as hard as the forward path, and
# every toggle happens at runtime with no edit to any skill or formula file.
# ---------------------------------------------------------------------------

run_mode() {
  LAST_OUT="$SANDBOX/mode-out"; LAST_ERR="$SANDBOX/mode-err"
  MODE_STATUS=0
  (cd "$RIG_ROOT" && \
     GC_CITY="$SANDBOX/city" \
     GC_RIG_ROOT="$SANDBOX/rig" \
     BRIEF_ROOT="$SANDBOX/rig/.beads/briefs" \
     "$CHECK" no-brainer-mode) >"$LAST_OUT" 2>"$LAST_ERR" || MODE_STATUS=$?
}

run_disarm() {
  DISARM_STATUS=0
  (cd "$RIG_ROOT" && \
     GC_CITY="$SANDBOX/city" \
     GC_RIG_ROOT="$SANDBOX/rig" \
     BRIEF_ROOT="$SANDBOX/rig/.beads/briefs" \
     "$CHECK" no-brainer-disarm) >"$SANDBOX/disarm-out" 2>"$SANDBOX/disarm-err" || DISARM_STATUS=$?
}

echo "=== 21. mode is observable: unarmed reports DRY-RUN ==="
mk_sandbox "$GOOD_G9"; run_mode
if [ "$MODE_STATUS" = "0" ] && grep -q "DRY-RUN" "$LAST_OUT" && ! grep -q "mode: ARMED" "$LAST_OUT"; then
  ok "unarmed city reports DRY-RUN when asked"
else
  no "unarmed city reports DRY-RUN when asked (exit=$MODE_STATUS)"
fi
cleanup

echo "=== 22. mode is observable: armed reports ARMED ==="
mk_sandbox "$GOOD_G9"; arm_both; run_mode
if [ "$MODE_STATUS" = "0" ] && grep -q "ARMED" "$LAST_OUT"; then
  ok "armed city reports ARMED when asked"
else
  no "armed city reports ARMED when asked (exit=$MODE_STATUS)"
fi
cleanup

echo "=== 23. mode report names the toggle commands in both directions ==="
mk_sandbox "$GOOD_G9"; run_mode
if grep -q "no_brainer_auto_execute_armed" "$LAST_OUT" && grep -q "no-brainer-disarm" "$LAST_OUT"; then
  ok "mode report tells the operator how to toggle each way"
else
  no "mode report tells the operator how to toggle each way"
fi
cleanup

echo "=== 24. toggle FORWARD at runtime: dry-run refuses, then armed permits ==="
mk_sandbox "$GOOD_G9"
run_gate; first_status="$STATUS"; first_reason="$(audit_field reason)"
arm_both
run_gate; second_status="$STATUS"; second_decision="$(audit_field decision)"
if [ "$first_status" = "1" ] && [ "$first_reason" = "not_armed" ] && \
   [ "$second_status" = "0" ] && [ "$second_decision" = "PERMITTED" ]; then
  ok "dry-run -> armed takes effect at runtime"
else
  no "dry-run -> armed takes effect at runtime (first=$first_status/$first_reason second=$second_status/$second_decision)"
fi
cleanup

echo '=== 25. toggle BACK by pinning: armed permits, then a false token refuses ==='
mk_sandbox "$GOOD_G9"; arm_both
run_gate; first_status="$STATUS"
printf 'false\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"
run_gate; second_status="$STATUS"; second_reason="$(audit_field reason)"
if [ "$first_status" = "0" ] && [ "$second_status" = "1" ] && [ "$second_reason" = "dry_run_pinned" ]; then
  ok "armed -> dry-run by writing false takes effect at runtime"
else
  no "armed -> dry-run by writing false (first=$first_status second=$second_status/$second_reason)"
fi
cleanup

echo "=== 26. toggle BACK by deletion: removing one token is enough ==="
mk_sandbox "$GOOD_G9"; arm_both
run_gate; first_status="$STATUS"
rm -f "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"
run_gate; second_status="$STATUS"; second_reason="$(audit_field reason)"
if [ "$first_status" = "0" ] && [ "$second_status" = "1" ] && [ "$second_reason" = "not_armed" ]; then
  ok "deleting either token returns to dry-run"
else
  no "deleting either token returns to dry-run (first=$first_status second=$second_status/$second_reason)"
fi
cleanup

echo "=== 27. the disarm command is a one-shot recovery path, and it works ==="
mk_sandbox "$GOOD_G9"; arm_both
run_gate; armed_status="$STATUS"
run_disarm
run_gate; after_status="$STATUS"; after_reason="$(audit_field reason)"
run_mode
if [ "$armed_status" = "0" ] && [ "$DISARM_STATUS" = "0" ] && \
   [ "$after_status" = "1" ] && [ "$after_reason" = "dry_run_pinned" ] && \
   grep -q "DRY-RUN" "$LAST_OUT"; then
  ok "no-brainer-disarm returns the city to dry-run in one command"
else
  no "no-brainer-disarm returns to dry-run (armed=$armed_status disarm=$DISARM_STATUS after=$after_status/$after_reason)"
fi
cleanup

echo "=== 28. round trip: dry-run -> armed -> dry-run -> armed is repeatable ==="
mk_sandbox "$GOOD_G9"
trip=""
run_gate; trip="$trip$STATUS"
arm_both;                      run_gate; trip="$trip$STATUS"
run_disarm;                    run_gate; trip="$trip$STATUS"
arm_both;                      run_gate; trip="$trip$STATUS"
if [ "$trip" = "1010" ]; then
  ok "the mode round-trips (refuse, permit, refuse, permit)"
else
  no "the mode round-trips (got '$trip', expected '1010')"
fi
cleanup

echo "=== 29. an explicitly pinned dry-run is distinguishable from never-armed ==="
mk_sandbox "$GOOD_G9"; arm_city
printf 'false\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"
run_gate; pinned_reason="$(audit_field reason)"
run_mode; pinned_report=0
grep -q "pinned" "$LAST_OUT" && pinned_report=1
cleanup
mk_sandbox "$GOOD_G9"; run_gate; never_reason="$(audit_field reason)"
if [ "$pinned_reason" = "dry_run_pinned" ] && [ "$never_reason" = "not_armed" ] && [ "$pinned_report" = "1" ]; then
  ok "pinned dry-run and never-armed are distinguishable in audit and report"
else
  no "pinned vs never-armed distinguishable (pinned=$pinned_reason never=$never_reason report=$pinned_report)"
fi
cleanup

echo "=== 30. stop gates still refuse in ARMED mode after a full round trip ==="
mk_sandbox "---
server_touching: true
---
$GOOD_G9"
arm_both; run_disarm; arm_both
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "stop_gate_server_touching" ]; then
  ok "category E stays refused across mode toggles"
else
  no "category E stays refused across mode toggles (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
