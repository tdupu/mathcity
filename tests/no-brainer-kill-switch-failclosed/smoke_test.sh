#!/usr/bin/env bash
# An ENGAGED kill switch must hold whether or not the rig root resolves.
#
# sally's finding, with sally's control: identical fixture, identical engaged
# rig kill switch, only the environment differs.
#
#   A. rig root resolvable   -> rc=1  kill_switch_engaged      (the brake works)
#   B. rig root unresolvable -> rc=0  reason=armed_and_gates_clear
#
# (B) is the worst instance of the day's pattern. The other seven were checks
# that passed without looking; this is a control an operator DELIBERATELY
# ENGAGED, reporting that it was checked and found disengaged.
#
# Root cause: nb_resolve_mode falls back to `cd "$ROOT/../.." || true`. When
# that cannot resolve a rig, NB_RIG_ROOT is left degenerate, the kill-switch
# path composes against it, the file is absent, absent != "false", and the
# brake is silently skipped.
#
# Requirement 1 is fail-closed; requirement 2 is that the REASON must not
# assert a read that did not happen. Both are asserted here: a run that
# refuses for the wrong stated reason still fails this test.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$ROOT_DIR/assets/scripts/checks/brief-check.sh"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/rig/.beads/briefs/.pile"
printf 'false\n' > "$TMP/rig/.beads/auto_merge_enabled"      # ENGAGED
BRIEF="$TMP/rig/.beads/briefs/.pile/x-brief.md"
printf -- '---\nbrief_slug: x\n---\n## Gate Evidence\nG9 No-brainer-filter: PASS classifier_state=known_no_brainer category=stale-branch confidence=0.95 stop_gates_clear=true classified_at=2026-08-20T00:00:00Z\n' > "$BRIEF"

run_gate() {  # $1 = "resolvable" | "unresolvable"; prints rc, sets OUT
  local out rc
  if [ "$1" = "resolvable" ]; then
    out="$(cd "$TMP" && BRIEF_ROOT="$TMP/rig/.beads/briefs" GC_BRIEF_PATH="$BRIEF" \
           bash "$CHECK" no-brainer-execute-safety 2>&1)" && rc=0 || rc=$?
  else
    out="$(cd "$TMP" && env -u BRIEF_ROOT -u GC_RIG_ROOT GC_BRIEF_PATH="$BRIEF" \
           bash "$CHECK" no-brainer-execute-safety 2>&1)" && rc=0 || rc=$?
  fi
  OUT="$out"; return "$rc"
}

# --- A. CONTROL: the brake works when the rig root resolves ------------------
# If this fails the fixture is wrong, not the code -- and every verdict below
# would be meaningless. It is the single-variable control.
if run_gate resolvable; then
  no "CONTROL: engaged kill switch PERMITTED with a resolvable rig root; fixture is not exercising the brake"
else
  case "$OUT" in
    *"kill switch ENGAGED"*) ok "CONTROL: engaged kill switch refuses when the rig root resolves" ;;
    *) no "CONTROL: refused, but not for the kill switch: $OUT" ;;
  esac
fi

# --- B. The defect: same engaged switch, unresolvable rig root ---------------
if run_gate unresolvable; then
  no "engaged kill switch PERMITTED when the rig root cannot be resolved (fails permissive)"
  echo "    $OUT" | head -2
else
  ok "engaged kill switch still refuses when the rig root cannot be resolved"
fi

# --- C. The reason must not assert a read that did not happen ---------------
case "$OUT" in
  *armed_and_gates_clear*|*"is ARMED"*)
    no "the gate reported ARMED / armed_and_gates_clear while an engaged switch went unread" ;;
  *) ok "the gate does not claim the switch was read and clear" ;;
esac

# --- D. Sibling (#94): disarm must not write a rig token outside a rig -------
# Requirement 4 asked whether one fix covers both. It does: both read
# NB_RIG_ROOT from nb_resolve_mode. A token written to a non-rig directory is
# a phantom brake -- worse than none, because it reads as one.
DIS="$TMP/disarm"; mkdir -p "$DIS"
DIS_OUT="$(cd "$DIS" && env -u BRIEF_ROOT -u GC_RIG_ROOT GC_CITY="$TMP/city"            bash "$CHECK" no-brainer-disarm 2>&1 || true)"
if [ -f "$DIS/.beads/no_brainer_auto_execute_armed" ]; then
  no "#94: disarm wrote a rig token into a non-rig directory ($DIS/.beads/)"
else
  ok "#94: disarm writes no rig token when the rig root does not resolve"
fi
case "$DIS_OUT" in
  *"both tokens"*) no "#94: disarm claims BOTH tokens written when the rig one was not" ;;
  *) ok "#94: disarm does not claim a rig token it did not write" ;;
esac

echo "no-brainer-kill-switch-failclosed: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
