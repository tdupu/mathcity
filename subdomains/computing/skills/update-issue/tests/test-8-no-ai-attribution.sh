#!/bin/bash
# test-8: --no-ai-attribution suppresses BOTH footer injection AND label add.
# Useful when shepherding a human-authored rewrite through the skill.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-8: --no-ai-attribution suppresses footer + label"

export MOCK_GH_OLD_BODY="old body"
unset MOCK_GH_EXISTING_ARCHIVE

NEW_BODY=$(mktemp)
echo "human-authored canonical body" > "$NEW_BODY"

bash "$SCRIPT" 666 --body-file "$NEW_BODY" --no-ai-attribution \
  --reason "human edit" --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"

# Footer marker must NOT appear in the body sent to gh.
BODIES_LOG="${MOCK_GH_LOG}.bodies"
if [ -f "$BODIES_LOG" ] && grep -q "<!-- ai-assisted-footer -->" "$BODIES_LOG"; then
  echo "FAIL: AI footer marker present in body even though --no-ai-attribution was set"
  FAIL_COUNT=$((FAIL_COUNT+1))
else
  echo "PASS: AI footer marker absent from body (suppressed)"
  PASS_COUNT=$((PASS_COUNT+1))
fi

# No label flow should fire.
assert_log_NOT_contains "gh label list" "did NOT look up label"
assert_log_NOT_contains "gh label create" "did NOT create label"
assert_log_NOT_contains "add-label ai-assisted" "did NOT add label to issue"

# Body still replaced.
assert_log_contains "gh issue edit 666 --repo example-owner/agent-skills --body-file" "still replaced body"

rm -f "$NEW_BODY"
test_teardown
