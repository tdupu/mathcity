#!/bin/sh
# silent-pass-scan.sh -- find cwd-relative directory scans inside check scripts
# whose failure mode is a PASS.
#
# THE CLASS (#71, fourth site of the family fixed in d3ec6d7 / 310b15a):
# a check script runs `find formulas ...` or `grep -r ... gates`, accumulates
# matches, and decides pass/fail on whether the accumulator is empty. The ralph
# runner's cwd is an agent work dir, never the pack root, so the operand does not
# exist, the scan matches nothing, the accumulator stays empty -- and the check
# reports PASS. It cannot fail, and a check that cannot fail looks exactly like a
# check that passed.
#
# This is strictly worse than the three sites already fixed. Those resolved a
# cwd-relative FILE and were guarded by `[ -f ... ] || fail`, so they failed
# CLOSED. A directory scan has no such guard: emptiness is indistinguishable from
# "nothing to report".
#
# WHY A SEPARATE RULE. test 36 matches `="assets/` -- an assignment-shaped
# literal. A bare `find formulas` has neither an `assets/` prefix nor an `=`, so
# no existing guard can see it. Verified by injection: adding `find gates -type f`
# to brief-check.sh leaves the suite at 38 passed / 0 failed.
#
# SAFE FORMS (not flagged): an operand anchored on anything that is not the cwd --
# $ROOT, $RIG_ROOT, $CITY, an absolute path, a $(pack_asset ...) capture, or any
# variable. Those resolve independently of where the runner happens to stand.
#
# Usage: silent-pass-scan.sh [pack-root]   (default: resolved from this script)
# Exit:  0 = clean, 1 = at least one silent-pass scan found.

set -eu

if [ "$#" -ge 1 ]; then
  PACK="$1"
else
  PACK="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." 2>/dev/null && pwd)"
fi

[ -d "$PACK/assets/scripts" ] || {
  echo "silent-pass-scan: not a pack root: $PACK" >&2
  exit 2
}

# Repo top-level directories that only exist when cwd IS the pack root.
DIRS='formulas|gates|orders|skills|assets|subdomains|tests|agents|template-fragments'

found=0
tmp="${TMPDIR:-/tmp}/silent-pass-scan.$$"
: > "$tmp"

for f in $(find "$PACK/assets/scripts" -name '*.sh' -type f | sort); do
  # Strip comments before matching so the explanatory prose in this family of
  # scripts is not itself reported.
  sed 's/[[:space:]]*#.*$//' "$f" |
  grep -nE "(^|[;&|[:space:]])(find|ls)[[:space:]]+($DIRS)([[:space:]]|/|\$)|grep[^|;]*-[a-zA-Z]*r[a-zA-Z]*[[:space:]]+[^|;]*[[:space:]]($DIRS)([[:space:]]|/|\$)" |
  while IFS= read -r hit; do
    printf '%s:%s\n' "${f#"$PACK"/}" "$hit" >> "$tmp"
  done
done

if [ -s "$tmp" ]; then
  echo "silent-pass scans (cwd-relative directory operand in a check script):" >&2
  cat "$tmp" >&2
  found=$(grep -c . "$tmp")
  rm -f "$tmp"
  echo "" >&2
  echo "Each of these reports PASS when run off the pack root, because the scan" >&2
  echo "matches nothing and emptiness is read as 'no violations'. Anchor the" >&2
  echo "operand on \$ROOT / \$RIG_ROOT / an absolute path, or resolve it the way" >&2
  echo "pack_asset() does, so a resolution failure is visible instead of silent." >&2
  echo "found: $found" >&2
  exit 1
fi

rm -f "$tmp"
echo "silent-pass-scan: clean (no cwd-relative directory scans in check scripts)"
exit 0
