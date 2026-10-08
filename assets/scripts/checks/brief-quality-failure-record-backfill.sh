#!/bin/sh
set -eu

ROOT="${BRIEF_ROOT:-.beads/briefs}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

# mc-ntfzh / mc-gokfn: forward "$@". Without it the wrapper silently dropped
# every caller flag, so a --dry-run preview ran as a real mutating pass.
exec python3 "$SCRIPT_DIR/brief-quality-failure-record.py" --brief-root "$ROOT" "$@"
