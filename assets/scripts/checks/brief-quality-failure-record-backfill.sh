#!/bin/sh
set -eu

ROOT="${BRIEF_ROOT:-.beads/briefs}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

exec python3 "$SCRIPT_DIR/brief-quality-failure-record.py" --brief-root "$ROOT"
