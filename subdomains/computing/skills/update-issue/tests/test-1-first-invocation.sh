#!/bin/bash
# test-1: first invocation against an issue (no existing archive comment)
# Expect: gh issue comment called (creates new consolidated archive);
# gh api PATCH NOT called; gh issue edit called (replaces body).

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-1: first invocation creates consolidated archive comment"

# No existing archive comment in the mock universe.
export MOCK_GH_OLD_BODY="some old body content"
unset MOCK_GH_EXISTING_ARCHIVE

NEW_BODY=$(mktemp)
echo "new canonical body for issue 999" > "$NEW_BODY"

bash "$SCRIPT" 999 --body-file "$NEW_BODY" --reason "first run test" --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"
assert_log_contains "gh issue view 999" "fetched current body"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/999/comments" "searched comments for marker"
assert_log_contains "gh issue comment 999" "created new consolidated archive comment"
assert_log_NOT_contains "gh api -X PATCH" "did NOT patch (no existing archive)"
assert_log_contains "gh issue edit 999" "replaced body"

rm -f "$NEW_BODY"
test_teardown
