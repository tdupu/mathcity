#!/bin/sh
# brief-review-patrol-record-required.sh — verify the patrol wrote a record.
#
# Passes when a patrol record exists under $BRIEF_ROOT/patrol/ that was
# modified within the last 2 hours (i.e., plausibly by the current run).
# Standalone by design; does not route through brief-check.sh.
set -eu

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
ROOT="${BRIEF_ROOT:-.beads/briefs}"

if [ ! -d "$ROOT/patrol" ]; then
  echo "brief-review-patrol: no patrol directory at $ROOT/patrol" >&2
  exit 1
fi

recent=$(find "$ROOT/patrol" -name 'patrol-*.md' -type f -mmin -120 2>/dev/null | head -n 1)
if [ -z "$recent" ]; then
  echo "brief-review-patrol: no patrol record written in the last 2h under $ROOT/patrol" >&2
  exit 1
fi

exit 0
