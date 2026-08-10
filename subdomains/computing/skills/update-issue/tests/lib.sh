# lib.sh — shared test helpers for update-issue L1 tests.

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SKILL_DIR/scripts/update-issue.sh"
MOCKS_DIR="$SKILL_DIR/tests/mocks"

# Use the mocked gh for the run.
export PATH="$MOCKS_DIR:$PATH"

# Each test gets its own log + tmpdir.
test_setup() {
  TEST_NAME="${1:?test name required}"
  TMPDIR=$(mktemp -d)
  export MOCK_GH_LOG="$TMPDIR/gh-calls.log"
  : > "$MOCK_GH_LOG"
  PASS_COUNT=0
  FAIL_COUNT=0
  echo "===== $TEST_NAME ====="
}

test_teardown() {
  rm -rf "$TMPDIR"
  echo "===== $PASS_COUNT pass / $FAIL_COUNT fail ====="
  if [ "$FAIL_COUNT" -gt 0 ]; then exit 1; fi
}

assert_log_contains() {
  local needle="$1" label="$2"
  if grep -qF "$needle" "$MOCK_GH_LOG"; then
    echo "PASS: $label  (log contains '$needle')"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo "FAIL: $label  (log does NOT contain '$needle')"
    echo "  log contents:"
    sed 's/^/    /' "$MOCK_GH_LOG"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
}

assert_log_NOT_contains() {
  local needle="$1" label="$2"
  if ! grep -qF "$needle" "$MOCK_GH_LOG"; then
    echo "PASS: $label  (log correctly does NOT contain '$needle')"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo "FAIL: $label  (log contains '$needle' but should not)"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
}

assert_exit() {
  local expected="$1" actual="$2" label="$3"
  if [ "$expected" -eq "$actual" ]; then
    echo "PASS: $label  (exit=$expected)"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo "FAIL: $label  (expected=$expected, actual=$actual)"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
}
