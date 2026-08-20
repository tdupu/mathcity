#!/bin/sh
# TDD harness for taking the no-brainer classifier OFF dry-run safely.
#
# Contract under test: `brief-check.sh no-brainer-execute-safety` is the ONE
# component that runs before any no-brainer auto-execution mutates anything.
# It must therefore be a real gate, not an advisory audit:
#
#   1. brief unresolvable            -> REFUSE (cannot prove safety of an unread artifact)
#   2. stop gates (category E etc.)  -> REFUSE, evaluated BEFORE any switch/mode state
#   3. classifier evidence           -> REFUSE unless known_no_brainer + registry
#                                       category + stop_gates_clear + confidence >= 0.85
#   4. N5 kill switch reads `false`  -> REFUSE (city, then rig)
#   5. DRY-RUN is pinned             -> REFUSE (token reads `false`, or unreadable)
#   6. otherwise                     -> PERMIT
#
# ARMED is the DEFAULT (owner ruling, 2026-08-19): an ABSENT token means
# auto-execute. The tokens are brakes, not enablers. DRY-RUN must be pinned.
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

# ARMED is the default, so "arming" is the absence of a pin. These helpers
# exist for the cases that assert the EXPLICIT `true` form behaves identically.
arm_city() { printf 'true\n' > "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"; }
arm_rig()  { printf 'true\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"; }
arm_both() { arm_city; arm_rig; }
pin_city() { printf 'false\n' > "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"; }
pin_rig()  { printf 'false\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"; }

# run_gate_cwd <cwd> — run the gate from an arbitrary working directory.
# run_gate keeps the pack root, which is what every case above wants; the
# cwd-independence cases below pass a directory that is not the pack root.
run_gate_cwd() {
  LAST_OUT="$SANDBOX/out"; LAST_ERR="$SANDBOX/err"
  STATUS=0
  (cd "$1" && \
     GC_CITY="$SANDBOX/city" \
     GC_RIG_ROOT="$SANDBOX/rig" \
     BRIEF_ROOT="$SANDBOX/rig/.beads/briefs" \
     GC_BRIEF_PATH="${FORCE_BRIEF_PATH:-$BRIEF}" \
     "$CHECK" no-brainer-execute-safety) >"$LAST_OUT" 2>"$LAST_ERR" || STATUS=$?
}

run_gate() { run_gate_cwd "$RIG_ROOT"; }

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

echo "=== 4. ABSENT tokens -> PERMIT (ARMED is the default; brakes, not enablers) ==="
mk_sandbox "$GOOD_G9"; run_gate
if [ "$STATUS" = "0" ] && [ "$(audit_field decision)" = "PERMITTED" ] && \
   [ "$(audit_field armed_city)" = "absent" ]; then
  ok "absent tokens permit — an unconfigured rig takes the ARMED default"
else
  no "absent tokens permit (exit=$STATUS decision=$(audit_field decision) city=$(audit_field armed_city))"
fi
cleanup

echo "=== 5. absent tokens + kill switch reads true -> PERMIT ==="
mk_sandbox "$GOOD_G9"
printf 'true\n' > "$SANDBOX/city/.beads/auto_merge_enabled"
run_gate
if [ "$STATUS" = "0" ] && [ "$(audit_field decision)" = "PERMITTED" ]; then
  ok "a released brake and an absent token both mean proceed"
else
  no "a released brake and an absent token both mean proceed (exit=$STATUS decision=$(audit_field decision))"
fi
cleanup

echo "=== 6. explicit true at city, absent at rig -> PERMIT (same as default) ==="
mk_sandbox "$GOOD_G9"; arm_city; run_gate
if [ "$STATUS" = "0" ] && [ "$(audit_field armed_city)" = "armed" ] && \
   [ "$(audit_field armed_rig)" = "absent" ]; then
  ok "explicit true is equivalent to absent, and both permit"
else
  no "explicit true equivalent to absent (exit=$STATUS city=$(audit_field armed_city) rig=$(audit_field armed_rig))"
fi
cleanup

echo "=== 7. pinning EITHER level alone is enough to reach DRY-RUN ==="
mk_sandbox "$GOOD_G9"; arm_city; pin_rig; run_gate
rig_only="$STATUS:$(audit_field reason)"
cleanup
mk_sandbox "$GOOD_G9"; pin_city; arm_rig; run_gate
city_only="$STATUS:$(audit_field reason)"
if [ "$rig_only" = "1:dry_run_pinned" ] && [ "$city_only" = "1:dry_run_pinned" ]; then
  ok "either level alone pins dry-run — rollback is a one-place act"
else
  no "either level alone pins dry-run (rig_only=$rig_only city_only=$city_only)"
fi
cleanup

echo "=== 8. an EXPIRED dry-run pin lapses back to the ARMED default ==="
mk_sandbox "$GOOD_G9"
printf 'false\nexpires=2000-01-01T00:00:00Z\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"
run_gate
if [ "$STATUS" = "0" ] && [ "$(audit_field armed_rig)" = "pin_expired" ]; then
  ok "a temporary dry-run pin auto-resumes ARMED when it expires"
else
  no "expired pin resumes ARMED (exit=$STATUS rig=$(audit_field armed_rig))"
fi
cleanup

echo "=== 9. an UNEXPIRED dry-run pin still holds ==="
mk_sandbox "$GOOD_G9"
printf 'false\nexpires=2999-01-01T00:00:00Z\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "dry_run_pinned" ]; then
  ok "a dry-run pin holds until its deadline"
else
  no "a dry-run pin holds until its deadline (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 9b. an UNREADABLE token holds DRY-RUN (unreadable is not consent) ==="
mk_sandbox "$GOOD_G9"
printf 'maybe?\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "dry_run_token_invalid" ]; then
  ok "a malformed token refuses rather than falling through to the default"
else
  no "malformed token refuses (exit=$STATUS reason=$(audit_field reason))"
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
mk_sandbox "$GOOD_G9"; run_gate
armed_banner=0
grep -q "PRELIMINARY" "$LAST_ERR" && armed_banner=1
armed_decision="$(audit_field decision)"
armed_mode="$(audit_field mode)"
cleanup
mk_sandbox "$GOOD_G9"; pin_rig; run_gate
dry_decision="$(audit_field decision)"
dry_mode="$(audit_field mode)"
if [ "$armed_banner" = "1" ] && [ "$armed_decision" = "PERMITTED" ] && [ "$armed_mode" = "armed" ] && \
   [ "$dry_decision" = "REFUSED" ] && [ "$dry_mode" = "dry-run" ]; then
  ok "armed and dry-run paths are distinguishable (banner + mode + decision)"
else
  no "armed and dry-run paths distinguishable (banner=$armed_banner armed=$armed_decision/$armed_mode dry=$dry_decision/$dry_mode)"
fi
cleanup

# ---------------------------------------------------------------------------
# Dry-run is a RUNTIME MODE that toggles in BOTH directions, not a one-way
# arming. Under an ARMED default the recovery path (armed -> dry-run) is the
# one that has to work under pressure, so it is tested hardest, and every
# toggle happens at runtime with no edit to any skill or formula file.
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

echo "=== 21. mode is observable: an unconfigured city reports ARMED ==="
mk_sandbox "$GOOD_G9"; run_mode
if [ "$MODE_STATUS" = "0" ] && grep -q "mode: ARMED" "$LAST_OUT" && \
   grep -q "ARMED is the DEFAULT" "$LAST_OUT"; then
  ok "an unconfigured city reports ARMED and says so is the default"
else
  no "unconfigured city reports ARMED by default (exit=$MODE_STATUS)"
fi
cleanup

echo "=== 22. mode is observable: a pinned city reports DRY-RUN ==="
mk_sandbox "$GOOD_G9"; pin_rig; run_mode
if [ "$MODE_STATUS" = "0" ] && grep -q "mode: DRY-RUN" "$LAST_OUT"; then
  ok "a pinned city reports DRY-RUN when asked"
else
  no "a pinned city reports DRY-RUN when asked (exit=$MODE_STATUS)"
fi
cleanup

echo "=== 23. mode report names the toggle commands in both directions ==="
mk_sandbox "$GOOD_G9"; run_mode
if grep -q "no-brainer-disarm" "$LAST_OUT" && grep -q "absent = armed default" "$LAST_OUT"; then
  ok "mode report tells the operator how to toggle each way"
else
  no "mode report tells the operator how to toggle each way"
fi
cleanup

echo "=== 24. an engaged kill switch is reported as DRY-RUN, not as ARMED ==="
mk_sandbox "$GOOD_G9"
printf 'false\n' > "$SANDBOX/city/.beads/auto_merge_enabled"
run_mode
if grep -q "mode: DRY-RUN" "$LAST_OUT"; then
  ok "a brake holding the city is not reported as ARMED"
else
  no "a brake holding the city is not reported as ARMED"
fi
cleanup

echo "=== 25. toggle BACK by pinning: default permits, then a false token refuses ==="
mk_sandbox "$GOOD_G9"
run_gate; first_status="$STATUS"
pin_rig
run_gate; second_status="$STATUS"; second_reason="$(audit_field reason)"
if [ "$first_status" = "0" ] && [ "$second_status" = "1" ] && [ "$second_reason" = "dry_run_pinned" ]; then
  ok "armed -> dry-run by writing false takes effect at runtime"
else
  no "armed -> dry-run by writing false (first=$first_status second=$second_status/$second_reason)"
fi
cleanup

echo "=== 26. toggle FORWARD by deletion: removing the pin restores ARMED ==="
mk_sandbox "$GOOD_G9"; pin_rig; pin_city
run_gate; first_status="$STATUS"
rm -f "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed" \
      "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"
run_gate; second_status="$STATUS"; second_decision="$(audit_field decision)"
if [ "$first_status" = "1" ] && [ "$second_status" = "0" ] && [ "$second_decision" = "PERMITTED" ]; then
  ok "deleting the pins returns to the ARMED default"
else
  no "deleting the pins returns to ARMED (first=$first_status second=$second_status/$second_decision)"
fi
cleanup

echo "=== 27. the disarm command is a one-shot recovery path, and it works ==="
mk_sandbox "$GOOD_G9"
run_gate; armed_status="$STATUS"
run_disarm
run_gate; after_status="$STATUS"; after_reason="$(audit_field reason)"
run_mode
if [ "$armed_status" = "0" ] && [ "$DISARM_STATUS" = "0" ] && \
   [ "$after_status" = "1" ] && [ "$after_reason" = "dry_run_pinned" ] && \
   grep -q "mode: DRY-RUN" "$LAST_OUT"; then
  ok "no-brainer-disarm stops an armed-by-default city in one command"
else
  no "no-brainer-disarm stops an armed city (armed=$armed_status disarm=$DISARM_STATUS after=$after_status/$after_reason)"
fi
cleanup

echo "=== 28. round trip: armed -> dry-run -> armed -> dry-run is repeatable ==="
mk_sandbox "$GOOD_G9"
trip=""
run_gate; trip="$trip$STATUS"
run_disarm;                    run_gate; trip="$trip$STATUS"
rm -f "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed" \
      "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"
run_gate; trip="$trip$STATUS"
run_disarm;                    run_gate; trip="$trip$STATUS"
if [ "$trip" = "0101" ]; then
  ok "the mode round-trips (permit, refuse, permit, refuse)"
else
  no "the mode round-trips (got '$trip', expected '0101')"
fi
cleanup

echo "=== 29. a pinned dry-run is distinguishable from an unreadable token ==="
mk_sandbox "$GOOD_G9"; pin_rig
run_gate; pinned_reason="$(audit_field reason)"
run_mode; pinned_report=0
grep -q "explicitly pinned" "$LAST_OUT" && pinned_report=1
cleanup
mk_sandbox "$GOOD_G9"
printf 'yes please\n' > "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed"
run_gate; invalid_reason="$(audit_field reason)"
if [ "$pinned_reason" = "dry_run_pinned" ] && [ "$invalid_reason" = "dry_run_token_invalid" ] && \
   [ "$pinned_report" = "1" ]; then
  ok "pinned and unreadable are distinguishable in audit and report"
else
  no "pinned vs unreadable distinguishable (pinned=$pinned_reason invalid=$invalid_reason report=$pinned_report)"
fi
cleanup

echo "=== 30. stop gates still refuse in ARMED mode after a full round trip ==="
mk_sandbox "---
server_touching: true
---
$GOOD_G9"
run_disarm
rm -f "$SANDBOX/rig/.beads/no_brainer_auto_execute_armed" \
      "$SANDBOX/city/.beads/no_brainer_auto_execute_armed"
run_gate
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "stop_gate_server_touching" ]; then
  ok "category E stays refused across mode toggles, armed by default"
else
  no "category E stays refused across mode toggles (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo "=== 31. the pack never ships a formula pointing at a check it does not provide ==="
# Under an ARMED default the gate script's PRESENCE is load-bearing. Check
# paths are declared in the "../assets/scripts/checks/<name>.sh" form, which gc
# resolves at cook time to the absolute path of the highest-priority formula
# layer that ships the script (see drift-audit D9). Two things are asserted:
# every referenced check really ships, and no formula has regressed to the
# legacy rig-relative ".gc/scripts/checks/..." form, which requires a per-rig
# install that nothing in gascity performs.
missing_checks=""
legacy_refs="$(grep -ho '"\.gc/scripts/checks/[a-z0-9-]*\.sh' "$RIG_ROOT"/formulas/*.toml "$RIG_ROOT"/gates/*.toml 2>/dev/null | sort -u)"
asset_refs="$(grep -ho '\.\./assets/scripts/checks/[a-z0-9-]*\.sh' "$RIG_ROOT"/formulas/*.toml | sort -u)"
for ref in $asset_refs; do
  base="$(basename "$ref")"
  [ -f "$RIG_ROOT/assets/scripts/checks/$base" ] || missing_checks="$missing_checks $base"
done
gate_sh="$RIG_ROOT/assets/scripts/checks/brief-no-brainer-execute-safety.sh"
if [ -z "$missing_checks" ] && [ -n "$asset_refs" ] && [ -z "$legacy_refs" ] && [ -x "$gate_sh" ]; then
  ok "every formula-referenced check ships in the pack, none use the legacy rig-relative form, and the gate is executable"
else
  no "check-path references are wrong (missing from pack:$missing_checks; legacy rig-relative refs:$(printf '%s' "$legacy_refs" | tr '\n' ' '); asset refs found: $(printf '%s' "$asset_refs" | grep -c . || true); gate executable: $([ -x "$gate_sh" ] && echo yes || echo NO))"
fi

echo "=== 32. the guarded-execute step is gated by the EXECUTE check, not the weaker one ==="
# The execute gate must sit on the step that mutates. It was previously on the
# classification step while guarded-execute ran a check that never read the
# switches at all.
formula="$RIG_ROOT/formulas/no-brainer-classify.toml"
guarded_block="$(awk '/^id = "guarded-execute"/,/^\[\[steps\]\]/' "$formula")"
if printf '%s' "$guarded_block" | grep -q 'brief-no-brainer-execute-safety.sh'; then
  ok "guarded-execute is gated by brief-no-brainer-execute-safety.sh"
else
  no "guarded-execute is gated by the execute-safety check"
fi

echo "=== 33. the gate resolves its category registry independently of cwd ==="
# Since cc58a95 the ralph runner resolves this check script from the PACK, but
# it still runs it with the agent work dir as cwd -- never the pack root. A
# cwd-relative registry literal therefore resolves to nothing in production, so
# every candidate refused with reason=classifier_evidence_invalid: the gate
# could not PERMIT at all, and the recorded reason blamed the brief's evidence
# for what was really a missing file. Every case above runs from the pack root,
# so none of them could see it. Same fixture, different cwd, same verdict.
mk_sandbox "$GOOD_G9"; arm_both
run_gate_cwd "$SANDBOX"
if [ "$STATUS" = "0" ] && [ "$(audit_field decision)" = "PERMITTED" ]; then
  ok "gate permits from a cwd that is not the pack root"
else
  no "gate permits from a cwd that is not the pack root (exit=$STATUS decision=$(audit_field decision) reason=$(audit_field reason))"
fi
cleanup

echo "=== 34. a genuinely absent registry still refuses, from any cwd ==="
# The counterpart to 33: resolving the registry from the script's own location
# must not degrade into "assume it is fine when it cannot be found". A pack
# layout that ships the script but no registry must still refuse.
mk_sandbox "$GOOD_G9"; arm_both
FAKE_CHECKS="$SANDBOX/fakepack/assets/scripts/checks"
mkdir -p "$FAKE_CHECKS"
cp "$CHECK" "$FAKE_CHECKS/brief-check.sh"
STATUS=0
(cd "$SANDBOX" && \
   GC_CITY="$SANDBOX/city" \
   GC_RIG_ROOT="$SANDBOX/rig" \
   BRIEF_ROOT="$SANDBOX/rig/.beads/briefs" \
   GC_BRIEF_PATH="$BRIEF" \
   sh "$FAKE_CHECKS/brief-check.sh" no-brainer-execute-safety) \
   >"$SANDBOX/out" 2>"$SANDBOX/err" || STATUS=$?
if [ "$STATUS" = "1" ] && [ "$(audit_field reason)" = "classifier_evidence_invalid" ]; then
  ok "absent category registry still refuses (fail-closed preserved)"
else
  no "absent category registry still refuses (exit=$STATUS reason=$(audit_field reason))"
fi
cleanup

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
