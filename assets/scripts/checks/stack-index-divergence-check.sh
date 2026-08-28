#!/usr/bin/env bash
# Reproducible measurement of brief-stack index/disk divergence.
#
# Read-only. Wraps `brief-stack-index.py check`, which matches rows to files on
# BASENAME because the live index spells the same file three ways
# (".beads/briefs/stack/x.md", absolute, and bare "stack/x.md"). Resolving those
# against a single base is what once turned a 1-file gap into a reported
# "40 phantom rows / 41 orphan files / ~44% divergence".
#
# Exit: 0 clean · 1 divergence · 2 malformed index or missing stack dir.
set -euo pipefail

BRIEF_ROOT="${1:-${BRIEF_ROOT:-$HOME/gt/.beads/briefs}}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$HERE/../brief-stack-index.py" check --brief-root "$BRIEF_ROOT"
