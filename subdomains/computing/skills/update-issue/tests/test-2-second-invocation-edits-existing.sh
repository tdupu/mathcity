#!/bin/bash
# test-2: SECOND invocation — archive comment already exists with marker.
# Expect: gh api PATCH called on the existing comment ID;
# NO new gh issue comment posted; body still replaced.
# Critical: this is the fix for #25 — no comment proliferation.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-2: second invocation edits existing archive (no new comment)"

export MOCK_GH_OLD_BODY="second-pass body content"
export MOCK_GH_EXISTING_ARCHIVE="424242"   # pretend existing archive comment id
export MOCK_GH_EXISTING_BODY="<!-- update-issue-consolidated-archive -->
# Archive — superseded body versions

<details>
<summary>Version as of 2026-06-09 10:00 — initial</summary>

first-pass original body

</details>"

NEW_BODY=$(mktemp)
echo "third canonical body" > "$NEW_BODY"

bash "$SCRIPT" 999 --body-file "$NEW_BODY" --reason "second-pass" --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/999/comments" "searched comments for marker"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/comments/424242" "fetched existing archive body"
assert_log_contains "gh api -X PATCH repos/example-owner/agent-skills/issues/comments/424242" "PATCHed existing archive in place"
assert_log_NOT_contains "gh issue comment 999" "did NOT create a new comment"
assert_log_contains "gh issue edit 999" "replaced body"

rm -f "$NEW_BODY"
test_teardown
