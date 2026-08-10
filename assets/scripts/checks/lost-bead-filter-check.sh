#!/bin/sh
set -eu

CHECK_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$CHECK_DIR/../../.." && pwd)"
ROOT="${1:-$PACK_ROOT/tests/lost-bead-filter/fixtures}"
SCRIPT="$PACK_ROOT/assets/scripts/lost-bead-filter.py"
PYTHON_BIN="${PYTHON:-python3}"
PROBE_DIR="${TMPDIR:-/tmp}/lost-bead-filter-check-$$"

cleanup() {
  rm -rf "$PROBE_DIR"
}
trap cleanup EXIT
mkdir -p "$PROBE_DIR"

STATUS_FILE="$PROBE_DIR/python.status"
(
  "$PYTHON_BIN" -c 'import sys, tomllib; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
  printf '%s\n' "$?" >"$STATUS_FILE"
) &
PY_PID=$!
WAITED=0
while kill -0 "$PY_PID" 2>/dev/null; do
  sleep 1
  WAITED=$((WAITED + 1))
  if [ "$WAITED" -ge 5 ]; then
    kill "$PY_PID" 2>/dev/null || true
    wait "$PY_PID" 2>/dev/null || true
    echo "I'm sorry, I can't do that - $PYTHON_BIN did not respond to the Python 3.11+ preflight." >&2
    echo "Set PYTHON to a working Python 3.11+ executable and retry from the repository root." >&2
    echo "(The lost-bead filter validator uses Python tomllib to parse schema fixtures.)" >&2
    exit 1
  fi
done
wait "$PY_PID" 2>/dev/null || true

if [ ! -f "$STATUS_FILE" ] || [ "$(cat "$STATUS_FILE")" != "0" ]; then
  echo "I'm sorry, I can't do that - $PYTHON_BIN is missing or older than Python 3.11." >&2
  echo "Install Python 3.11 or newer, or set PYTHON to a working interpreter, then retry from the repository root." >&2
  echo "(Python 3.11 provides the tomllib parser used by this check.)" >&2
  exit 1
fi

if [ ! -f "$SCRIPT" ]; then
  echo "I'm sorry, I can't do that - missing $SCRIPT." >&2
  echo "Run Task 2 of the lost-bead filter plan to add the validator script." >&2
  echo "(The wrapper delegates schema validation to the shared validator.)" >&2
  exit 1
fi

"$PYTHON_BIN" "$SCRIPT" validate "$ROOT"
