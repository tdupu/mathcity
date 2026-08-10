#!/bin/bash
# test-4: --delete-comments now ARCHIVES each comment body before deleting,
# folding them into the consolidated archive. Verifies the pattern dogfooded
# on hecke#275.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-4: --delete-comments archives bodies into folds before deleting"

export MOCK_GH_OLD_BODY="canonical body about to be replaced"
# Return this body whenever the script fetches any comment by ID.
export MOCK_GH_EXISTING_BODY="STAGED-DELETED-COMMENT-BODY-MARKER"
unset MOCK_GH_EXISTING_ARCHIVE   # no existing archive marker — first time

NEW_BODY=$(mktemp)
echo "new canonical body" > "$NEW_BODY"

bash "$SCRIPT" 999 --body-file "$NEW_BODY" --delete-comments "111,222,333" \
  --reason "cleanup with archival" --repo example-owner/agent-skills
EXIT=$?

# Call-log assertions
assert_exit 0 "$EXIT" "script exits 0"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/comments/111 --jq .body" "fetched body of comment 111 BEFORE deleting"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/comments/222 --jq .body" "fetched body of comment 222 BEFORE deleting"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/comments/333 --jq .body" "fetched body of comment 333 BEFORE deleting"
assert_log_contains "gh api -X DELETE repos/example-owner/agent-skills/issues/comments/111" "deleted 111"
assert_log_contains "gh api -X DELETE repos/example-owner/agent-skills/issues/comments/222" "deleted 222"
assert_log_contains "gh api -X DELETE repos/example-owner/agent-skills/issues/comments/333" "deleted 333"
assert_log_contains "gh issue comment 999" "posted consolidated archive comment"
assert_log_contains "gh issue edit 999" "replaced body"

# Body-content assertions: the archive comment posted via --body-file must
# contain the deleted-comment body content.
BODIES_LOG="${MOCK_GH_LOG}.bodies"
if [ -f "$BODIES_LOG" ]; then
  STAGED_COUNT=$(grep -c "STAGED-DELETED-COMMENT-BODY-MARKER" "$BODIES_LOG" 2>/dev/null || echo 0)
  if [ "$STAGED_COUNT" -ge 3 ]; then
    echo "PASS: archive body contains all 3 deleted-comment bodies  (count=$STAGED_COUNT, expected >=3)"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo "FAIL: archive body should contain 3 deleted-comment markers but found $STAGED_COUNT"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
  if grep -q "canonical body about to be replaced" "$BODIES_LOG"; then
    echo "PASS: archive body also contains the old body content"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo "FAIL: archive body missing the old body content"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
else
  echo "FAIL: no body-file sidecar log produced at $BODIES_LOG"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Order assertion: GET fires BEFORE DELETE for at least one comment.
GET_LINE=$(grep -n "comments/111 --jq .body" "$MOCK_GH_LOG" | head -1 | cut -d: -f1)
DEL_LINE=$(grep -n "DELETE repos/example-owner/agent-skills/issues/comments/111" "$MOCK_GH_LOG" | head -1 | cut -d: -f1)
if [ -n "$GET_LINE" ] && [ -n "$DEL_LINE" ] && [ "$GET_LINE" -lt "$DEL_LINE" ]; then
  echo "PASS: fetched 111's body (log line $GET_LINE) before deleting it (log line $DEL_LINE)"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: GET/DELETE order check failed (get=$GET_LINE, del=$DEL_LINE)"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

rm -f "$NEW_BODY"
test_teardown
