#!/bin/bash
# Smoke test for assets/scripts/checks/brief-check.sh.
# Read-only: does not modify the artifact under test and creates no files
# of its own, so there is nothing to clean up (F2.1 satisfied by construction).

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACT="$REPO_ROOT/assets/scripts/checks/brief-check.sh"

FAILURES=""

fail_check() {
  FAILURES="${FAILURES}${1}; "
}

if [ ! -r "$ARTIFACT" ]; then
  echo "SMOKE TEST: FAIL - artifact not found or not readable: $ARTIFACT"
  exit 1
fi

# 1. Syntax check.
syntax_out="$(bash -n "$ARTIFACT" 2>&1)"
syntax_rc=$?
if [ "$syntax_rc" -ne 0 ]; then
  fail_check "syntax check failed (exit $syntax_rc): $syntax_out"
fi

# 2. Safe invocation probe. The dispatcher has no --help subcommand, so an
# unrecognized command name is expected to fail SAFELY via its own fail()
# helper: stderr message, exit 1, no file writes. This confirms the script
# runs under bash and the dispatch/fail path is intact, without requiring
# real .beads/briefs fixtures to exercise the individual check_* functions.
help_out="$(bash "$ARTIFACT" --help 2>&1)"
help_rc=$?
if [ "$help_rc" -ne 1 ]; then
  fail_check "expected --help probe to exit 1 (unrecognized command), got exit $help_rc: $help_out"
fi
case "$help_out" in
  *"unknown check"*) ;;
  *) fail_check "expected --help probe stderr to mention 'unknown check', got: $help_out" ;;
esac

if [ -n "$FAILURES" ]; then
  echo "SMOKE TEST: FAIL - $FAILURES"
  exit 1
fi

echo "SMOKE TEST: PASS - brief-check.sh is syntactically valid and its dispatcher fails safely (exit 1, stderr mentions 'unknown check') on an unrecognized command"
exit 0
