#!/bin/bash
# run-all.sh — L1 mocked test driver for update-issue.
# Runs anywhere safely; mocks gh via PATH redirect. No real GitHub API calls.

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
total_pass=0
total_fail=0
script_pass=0
script_fail=0

for f in "$TESTS_DIR"/test-*.sh; do
  echo ""
  if bash "$f"; then
    script_pass=$((script_pass+1))
  else
    script_fail=$((script_fail+1))
  fi
done

echo ""
echo "================================================================"
echo "update-issue L1 test summary: $script_pass pass / $script_fail fail (of $((script_pass+script_fail)) test scripts)"
echo "================================================================"

if [ "$script_fail" -gt 0 ]; then exit 1; fi
