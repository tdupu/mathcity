#!/bin/sh
# mathcity/tests/stuck-bead-watch/smoke_test.sh
# Self-contained smoke test: exercises the detector's pure-Python logic
# (find_stuck_candidates, grace_window_seconds, cache roundtrip,
# classify_and_escalate) without requiring a live gc/bd fleet.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_DIR="$(cd "$HERE/../../assets/scripts" && pwd)"

echo "=== running unit tests ==="
cd "$HERE/../.."
python3 -m pytest tests/stuck-bead-watch/test_stuck_bead_watch.py -v

echo "=== verifying script is syntactically valid and --help works ==="
python3 "$SCRIPT_DIR/stuck-bead-watch.py" --help > /dev/null

echo "ALL STUCK-BEAD-WATCH SMOKE CHECKS PASSED"
