#!/bin/bash
# test-10: --ai-model, --on-behalf-of, --ai-label "" customize attribution.
# Empty --ai-label "" suppresses just the label while keeping the footer.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-10: ai-model, on-behalf-of, ai-label customization"

export MOCK_GH_OLD_BODY="old body"
unset MOCK_GH_EXISTING_ARCHIVE
export MOCK_GH_LABEL_EXISTS=1

NEW_BODY=$(mktemp)
echo "customized invocation body" > "$NEW_BODY"

bash "$SCRIPT" 888 --body-file "$NEW_BODY" \
  --ai-model "claude-sonnet-4-6" \
  --on-behalf-of "alogan" \
  --ai-label "" \
  --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"

BODIES_LOG="${MOCK_GH_LOG}.bodies"
if [ -f "$BODIES_LOG" ] && grep -q "claude-sonnet-4-6" "$BODIES_LOG"; then
  echo "PASS: custom model name in footer"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: custom model name missing from footer"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi
if [ -f "$BODIES_LOG" ] && grep -q "on behalf of @alogan" "$BODIES_LOG"; then
  echo "PASS: custom on-behalf-of handle in footer"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: custom on-behalf-of handle missing from footer"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Footer marker still present (only the label was suppressed, not the footer).
if [ -f "$BODIES_LOG" ] && grep -q "<!-- ai-assisted-footer -->" "$BODIES_LOG"; then
  echo "PASS: footer marker still injected (only label suppressed)"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: footer marker missing despite --ai-label \"\" (footer should still fire)"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

# No label flow should fire.
assert_log_NOT_contains "gh label list" "did NOT look up label (empty --ai-label)"
assert_log_NOT_contains "add-label" "did NOT add a label to issue"

rm -f "$NEW_BODY"
test_teardown
