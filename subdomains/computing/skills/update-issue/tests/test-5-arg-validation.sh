#!/bin/bash
# test-5: usage errors caught before any gh call.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-5: arg validation errors"

# no issue
bash "$SCRIPT" --body-file /tmp/never </dev/null >/tmp/scenario1.out 2>&1
assert_exit 1 "$?" "no issue number → exit 1"
assert_log_NOT_contains "gh " "no gh calls made on missing issue"

# both body-file and body-stdin
NB=$(mktemp); echo x > "$NB"
bash "$SCRIPT" 99 --body-file "$NB" --body-stdin <<<"y" >/tmp/scenario2.out 2>&1
assert_exit 1 "$?" "mutually exclusive flags → exit 1"

# body-file missing on disk
bash "$SCRIPT" 99 --body-file /nonexistent/path >/tmp/scenario3.out 2>&1
assert_exit 1 "$?" "missing --body-file → exit 1"

# unknown option
bash "$SCRIPT" 99 --body-file "$NB" --bogus >/tmp/scenario4.out 2>&1
assert_exit 1 "$?" "unknown option → exit 1"

rm -f "$NB" /tmp/scenario*.out
test_teardown
