#!/usr/bin/env bash
# Reap orphaned prepare-item-worktree directories left behind by the
# do-work / implementation-base formula pair (gascity-packs/gascity, upstream
# read-only). prepare-worktree.md creates `git worktree add $WORKTREE
# --detach HEAD`; close-source-anchor.md closes the bead but never removes
# the worktree. Filed as gsp-qsw4qh (root cause + upstream fix direction).
#
# This order is the stopgap: sweep every rig for <bead-id>-prepare-item-worktree
# directories, and for any whose bead is CLOSED, remove the worktree and
# prune the parent repo's git worktree admin metadata. OPEN/IN_PROGRESS beads
# are left untouched — the work may still be using the checkout.
set -euo pipefail

CITY_ROOT="${GC_CITY:-$HOME/gt}"
removed=0
kept=0

while IFS= read -r -d '' dir; do
  base="$(basename "$dir")"
  bead_id="${base%-prepare-item-worktree}"
  rig_dir="$(dirname "$dir")"

  status_line="$(bd -C "$rig_dir" show "$bead_id" 2>/dev/null | head -1 || true)"
  if [[ -z "$status_line" ]]; then
    echo "skip $bead_id: bead not found (leave for manual review)"
    kept=$((kept + 1))
    continue
  fi

  if echo "$status_line" | grep -q "CLOSED"; then
    echo "reap $bead_id: $dir"
    rm -rf "$dir"
    # Clean up git's own worktree admin entry so `git worktree list` in the
    # parent repo doesn't keep pointing at a missing path.
    git -C "$rig_dir" worktree prune 2>/dev/null || true
    removed=$((removed + 1))
  else
    kept=$((kept + 1))
  fi
done < <(find "$CITY_ROOT" -mindepth 2 -maxdepth 2 -type d -iname "*-prepare-item-worktree" -print0 2>/dev/null)

echo "reap-prepare-item-worktrees: removed=$removed kept=$kept"
