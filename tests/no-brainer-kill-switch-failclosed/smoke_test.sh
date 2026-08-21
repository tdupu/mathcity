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

# GC_CITY is PINNED to a fixture. It was previously left to inherit, so
# NB_CITY_ROOT fell back to $HOME/gt -- the LIVE city -- and when that city was
# pinned to dry-run the gate short-circuited at `dry_run_pinned` BEFORE ever
# reaching the kill-switch branch. The suite then passed against unfixed code
# (sally, reviewing). A unit test must not read production configuration, and a
# verdict that depends on live operator state is not a verdict.
mkdir -p "$TMP/city/.beads"
run_gate() {  # $1 = "resolvable" | "unresolvable"; sets OUT, returns the gate rc
  local out rc
  if [ "$1" = "resolvable" ]; then
    out="$(cd "$TMP" && env -u GC_RIG_ROOT GC_CITY="$TMP/city" \
           BRIEF_ROOT="$TMP/rig/.beads/briefs" GC_BRIEF_PATH="$BRIEF" \
           bash "$CHECK" no-brainer-execute-safety 2>&1)" && rc=0 || rc=$?
  else
    out="$(cd "$TMP" && env -u BRIEF_ROOT -u GC_RIG_ROOT GC_CITY="$TMP/city" \
           GC_BRIEF_PATH="$BRIEF" \
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
  # The rc alone is NOT enough. Any refusal satisfies a bare exit-code check --
  # including `dry_run_pinned`, which is what let this suite pass against
  # unfixed code. The refusal must name the unreadable brake specifically.
  case "$OUT" in
    *kill_switch_unreadable*|*"kill switch was NOT read"*)
      ok "engaged kill switch refuses with the unreadable-brake reason" ;;
    *dry_run_pinned*|*"pinned to DRY-RUN"*)
      no "refused, but at dry_run_pinned -- the gate never reached the kill-switch branch, so this proves nothing: $OUT" ;;
    *)
      no "refused for an unrelated reason, which does not pin this defect: $OUT" ;;
  esac
fi

# --- C. The reason must not assert a read that did not happen ---------------
case "$OUT" in
  *armed_and_gates_clear*|*"is ARMED"*)
    no "the gate reported ARMED / armed_and_gates_clear while an engaged switch went unread" ;;
  *) ok "the gate does not claim the switch was read and clear" ;;
esac

# --- D. Sibling (#94): disarm must not aim the rig token at filesystem root ---
# Requirement 4 asked whether one fix covers both. It does -- both read
# NB_RIG_ROOT from nb_resolve_mode.
#
# MY FIRST TWO ASSERTIONS HERE WERE VACUOUS and I caught them re-probing against
# unfixed code: I asserted "no rig token appears under the cwd", but unfixed
# disarm does not write to the cwd -- NB_RIG_ROOT resolves EMPTY, so the path
# composes to `/.beads/no_brainer_auto_execute_armed` and it dies with
# "cannot create /.beads to pin dry-run". The assertion checked a location that
# could never hold a token either way, so it passed on broken code.
#
# What actually discriminates: unfixed ABORTS on `/.beads` (and would have
# written there if root were writable); fixed SUCCEEDS, writes the city token
# only, and says the rig token was withheld.
DIS="$TMP/disarm"; mkdir -p "$DIS"
DIS_OUT="$(cd "$DIS" && env -u BRIEF_ROOT -u GC_RIG_ROOT GC_CITY="$TMP/city" \
           bash "$CHECK" no-brainer-disarm 2>&1)" && DIS_RC=0 || DIS_RC=$?

if [ "$DIS_RC" -eq 0 ]; then
  ok "#94: disarm succeeds outside a rig instead of aiming at filesystem root"
else
  no "#94: disarm failed outside a rig (rc=$DIS_RC): $DIS_OUT"
fi

# Matched on the DISTINCT messages, not on a "/.beads" substring: the legitimate
# city token path is `<tmp>/city/.beads/...`, which contains "/.beads" too. My
# first version of this case matched it and reported the fixed code as broken --
# an unanchored match, the same defect class this suite exists to catch, written
# into the suite itself.
case "$DIS_OUT" in
  *"rig token NOT written"*)
    ok "#94: disarm says plainly that the rig token was withheld" ;;
  *"cannot create /.beads"*)
    no "#94: disarm still aims the rig token at filesystem root: $DIS_OUT" ;;
  *"both tokens"*)
    no "#94: disarm claims BOTH tokens written when there is no rig to pin" ;;
  *)
    no "#94: disarm gave an unrecognised disposition: $DIS_OUT" ;;
esac

# The city token IS still written -- the safe direction stays easy.
if [ -f "$TMP/city/.beads/no_brainer_auto_execute_armed" ]; then
  ok "#94: the city token is still written, so dry-run can still be pinned"
else
  no "#94: disarm wrote no city token; the safe direction is no longer available"
fi

echo "no-brainer-kill-switch-failclosed: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
