#!/bin/bash
# test-6: marker search uses the REST API (per-issue comments endpoint),
# not the gh-issue-view graphql-style call. Verifies the fix to the
# graphql-id-vs-rest-id bug noted in the script.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-6: marker search uses REST repos/.../issues/N/comments"

export MOCK_GH_OLD_BODY="content"
unset MOCK_GH_EXISTING_ARCHIVE

NEW_BODY=$(mktemp); echo "x" > "$NEW_BODY"

bash "$SCRIPT" 77 --body-file "$NEW_BODY" --reason "rest path" --repo example-owner/agent-skills >/dev/null
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"
assert_log_contains "gh api repos/example-owner/agent-skills/issues/77/comments" "uses REST per-issue comments endpoint"
# The graphql .comments[].id query (used by old design) would look like:
#   gh issue view 77 --repo example-owner/agent-skills --json comments --jq .comments[]...
# We should NOT see a `--json comments` view used for marker search.
# (We DO see one --json comments for final count; check the format excludes 'select' there.)
calls_with_select=$(grep -c "select(.body" "$MOCK_GH_LOG" || true)
if [ "$calls_with_select" -eq 1 ]; then
  echo "PASS: marker-search jq filter present exactly once (in REST call)  (got $calls_with_select)"
  PASS_COUNT=$((PASS_COUNT+1))
else
  echo "FAIL: expected 1 select(.body) jq filter, got $calls_with_select"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

rm -f "$NEW_BODY"
test_teardown
