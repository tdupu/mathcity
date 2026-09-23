#!/usr/bin/env bash
# staged-deletion-sweep — find rigs whose index is armed to delete their own content.
#
# WHY THIS EXISTS. On 2026-09-19 two rigs (magma_diff_alg, 38 files;
# magma_clifford_algebras, 27) had every tracked file staged for deletion — one
# `git commit -a` from deleting two Magma packages. Every health instrument in
# the city reported both as healthy, because no instrument looks at the index.
# Recorded in gsp-duj6y8 §6, which notes the sweep is ~4 lines and does not exist.
# Carried unbuilt through S72 and S73.
#
# P6.2: a check that could not have failed must not render as a check that
# passed. This prints the repo count it actually scanned, and --self-test proves
# the probe can go red before you trust it going green.
#
# Usage:  staged-deletion-sweep.sh [city-root]      # default ~/gt
#         staged-deletion-sweep.sh --self-test      # positive control, then sweep
# Exit:   0 clean · 1 staged deletions found · 2 scanned nothing (vacuous)

set -uo pipefail

self_test=0
[ "${1:-}" = "--self-test" ] && { self_test=1; shift; }
root="${1:-$HOME/gt}"
cd "$root" || { echo "staged-deletion-sweep: cannot enter $root" >&2; exit 2; }

sweep() {
  local repos=0 hits=0 r n t
  for d in */; do
    r="${d%/}"
    [ -e "$r/.git" ] || continue          # .git may be a FILE (worktree/gc rig), not a dir
    repos=$((repos + 1))
    n=$(git -C "$r" diff --cached --diff-filter=D --name-only 2>/dev/null | wc -l | tr -d ' ')
    [ "${n:-0}" -gt 0 ] || continue
    t=$(git -C "$r" ls-files 2>/dev/null | wc -l | tr -d ' ')
    echo "STAGED-DELETION  $r: $n of $t tracked files staged for deletion"
    hits=$((hits + 1))
  done
  echo "scanned $repos repos under $root; $hits armed to delete tracked content"
  [ "$repos" -eq 0 ] && return 2
  [ "$hits" -gt 0 ] && return 1
  return 0
}

if [ "$self_test" -eq 1 ]; then
  # Positive control: arm a deletion in a throwaway repo and require the sweep to see it.
  ctl="$(mktemp -d)/ctl"
  mkdir -p "$ctl" && git -C "$ctl" init -q 2>/dev/null
  : > "$ctl/canary"
  git -C "$ctl" add canary && git -C "$ctl" -c user.email=t@t -c user.name=t commit -qm x
  git -C "$ctl" rm --cached -q canary
  if git -C "$ctl" diff --cached --diff-filter=D --name-only | grep -q canary; then
    echo "self-test PASS: the probe detects an armed deletion"
  else
    echo "self-test FAIL: the probe cannot go red — a clean sweep proves nothing" >&2
    exit 2
  fi
  rm -rf "$(dirname "$ctl")"
fi

sweep
