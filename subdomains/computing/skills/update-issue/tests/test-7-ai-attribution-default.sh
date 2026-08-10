#!/bin/bash
# test-7: default behavior auto-injects AI footer and applies ai-assisted label.
# Expect: body sent to `gh issue edit --body-file` ends with the footer marker;
# `gh label list` is called (lookup); `gh issue edit --add-label ai-assisted`
# is called.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-7: default behavior injects AI footer + applies label"

export MOCK_GH_OLD_BODY="old body"
unset MOCK_GH_EXISTING_ARCHIVE
unset MOCK_GH_LABEL_EXISTS

NEW_BODY=$(mktemp)
echo "user-authored canonical body" > "$NEW_BODY"

bash "$SCRIPT" 555 --body-file "$NEW_BODY" --reason "default attribution" --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"

# Footer must be injected into the body file passed to `gh issue edit`.
BODIES_LOG="${MOCK_GH_LOG}.bodies"
if [ -f "$BODIES_LOG" ] && grep -q "<!-- ai-assisted-footer -->" "$BODIES_LOG"; then
  echo "PASS: AI footer marker present in body sent to gh issue edit"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: AI footer marker NOT found in $BODIES_LOG"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi
if [ -f "$BODIES_LOG" ] && grep -q "AI-assisted" "$BODIES_LOG"; then
  echo "PASS: AI-assisted attribution prose present in body"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: AI-assisted attribution prose missing from body"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi
if [ -f "$BODIES_LOG" ] && grep -q "claude-opus-4-7" "$BODIES_LOG"; then
  echo "PASS: default model name present in footer"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: default model name missing from footer"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi
if [ -f "$BODIES_LOG" ] && grep -q "on behalf of @example-owner" "$BODIES_LOG"; then
  echo "PASS: default on-behalf-of handle present in footer"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: default on-behalf-of handle missing from footer"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Label flow: list, create (since MOCK_GH_LABEL_EXISTS unset), edit --add-label.
assert_log_contains "gh label list --repo example-owner/agent-skills --search ai-assisted" "looked up label existence"
assert_log_contains "gh label create ai-assisted --repo example-owner/agent-skills" "created missing label"
assert_log_contains "gh issue edit 555 --repo example-owner/agent-skills --add-label ai-assisted" "added label to issue"

rm -f "$NEW_BODY"
test_teardown
