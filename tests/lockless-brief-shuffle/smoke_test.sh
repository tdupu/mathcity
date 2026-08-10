#!/bin/sh
# Static regression test for gsp-89yli: proves the lockless brief-shuffle
# formula shape is correct and the old lock-based design is fully gone.
# Does not require a live city — pure TOML/shell-source fixture check.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA="$PACK_ROOT/formulas/brief-shuffle.toml"
CHECK_SH="$PACK_ROOT/assets/scripts/checks/brief-check.sh"
STAGING_CLEAR_SH="$PACK_ROOT/assets/scripts/checks/brief-staging-clear.sh"

fail() {
  echo "I'm sorry, I can't do that - $1" >&2
  exit 1
}

[ -f "$FORMULA" ] || fail "missing $FORMULA"
[ -f "$CHECK_SH" ] || fail "missing $CHECK_SH"
[ -x "$STAGING_CLEAR_SH" ] || fail "missing or non-executable $STAGING_CLEAR_SH"

CHECKS=0
PASS=0

check() {
  CHECKS=$((CHECKS + 1))
  if eval "$2"; then
    PASS=$((PASS + 1))
    echo "  PASS: $1"
  else
    echo "  FAIL: $1"
  fi
}

# 1. Old lock-based step ids are fully gone.
check "no acquire-lock step remains" '! grep -q "^id = \"acquire-lock\"" "$FORMULA"'
check "no release-lock step remains" '! grep -q "^id = \"release-lock\"" "$FORMULA"'
check "only 2 legitimate .shuffle.lock documentation references (lines 8, 146)" '[ $(grep -c "\.shuffle\.lock" "$FORMULA") -eq 2 ]'

# 2. New 3-step shape is present with the correct needs graph.
check "claim-item step present" 'grep -q "^id = \"claim-item\"" "$FORMULA"'
check "process-item step present, needs claim-item" 'grep -A2 "^id = \"process-item\"" "$FORMULA" | grep -q "needs = \[\"claim-item\"\]"'
check "finalize step present, needs process-item" 'grep -A2 "^id = \"finalize\"" "$FORMULA" | grep -q "needs = \[\"process-item\"\]"'

# 3. Atomic mv claim and rescue-sweep language present (the actual fix, not just renamed steps).
check "claim-item uses atomic mv into .staging" 'grep -q "mv -f {{artifact_root}}/.pile/<slug>.md" "$FORMULA"'
check "claim-item documents the rescue sweep" 'grep -qi "RESCUE SWEEP" "$FORMULA"'
check "claim-item documents the 30-minute bound" 'grep -q "30 minutes" "$FORMULA"'

# 4. Manifest append still uses a short, bounded flock (not the old whole-run lock).
check "process-item uses flock only around the manifest append" 'grep -q "flock 9;" "$FORMULA"'

# 5. staging-clear check wired end to end.
check "brief-check.sh defines check_staging_clear" 'grep -q "^check_staging_clear()" "$CHECK_SH"'
check "brief-check.sh dispatches staging-clear" 'grep -q "staging-clear) check_staging_clear ;;" "$CHECK_SH"'
check "finalize step references the staging-clear check path" 'grep -q "brief-staging-clear.sh" "$FORMULA"'

# 6. Formula version bumped.
check "formula version bumped to 3" 'grep -q "^version = 3" "$FORMULA"'

echo ""
if [ "$PASS" -eq "$CHECKS" ]; then
  echo "PASS $PASS/$CHECKS - lockless brief-shuffle static regression test"
  exit 0
else
  echo "FAIL $PASS/$CHECKS - lockless brief-shuffle static regression test"
  exit 1
fi
