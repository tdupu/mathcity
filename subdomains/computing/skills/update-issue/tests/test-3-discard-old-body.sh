#!/bin/bash
# test-3: --discard-old-body skips the archive entirely.
# Expect: NO gh api PATCH, NO gh issue comment, just gh issue edit.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-3: --discard-old-body skips archive"

export MOCK_GH_OLD_BODY="old body, will be discarded"
export MOCK_GH_EXISTING_ARCHIVE="999"
export MOCK_GH_EXISTING_BODY="<!-- marker -->stale content"

NEW_BODY=$(mktemp)
echo "fresh content" > "$NEW_BODY"

bash "$SCRIPT" 999 --body-file "$NEW_BODY" --discard-old-body --reason "trivial" --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"
assert_log_NOT_contains "gh issue comment 999" "did NOT post a new comment"
assert_log_NOT_contains "gh api -X PATCH" "did NOT patch any comment"
assert_log_NOT_contains "gh api repos/example-owner/agent-skills/issues/999/comments" "did NOT even search for marker"
assert_log_contains "gh issue edit 999" "replaced body"

rm -f "$NEW_BODY"
test_teardown
