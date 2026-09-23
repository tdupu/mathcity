#!/usr/bin/env bash
set -uo pipefail

# Smoke test for the lean-formalize gate scripts (POLICY-formulas F6.1).
#
# What this asserts, per P6.2: each gate must be FALSIFIABLE -- there must exist a
# state in which it reports failure -- AND it must be able to PASS. A gate that
# only ever fails is as useless as one that only ever passes.
#
# The cases that matter most are the "cannot look" ones. A scan whose operand does
# not resolve must FAIL, never report zero violations. That reading -- an empty
# result as an all-clear -- is the defect that let a wrong root cause stand in this
# repo for eight days (ma-af9 / decision ma-sux).
#
# Runs offline. No Lean toolchain, no city, no dispatch required.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
CHECKS="$REPO/assets/scripts/checks"

NO_SORRY="$CHECKS/lean-no-sorry.sh"
GAP_ACCT="$CHECKS/lean-gap-accounting.sh"
BASELINE="$CHECKS/lean-baseline-green.sh"

for f in "$NO_SORRY" "$GAP_ACCT" "$BASELINE"; do
  [ -f "$f" ] || { echo "FATAL: missing gate script $f" >&2; exit 2; }
  bash -n "$f" || { echo "FATAL: syntax error in $f" >&2; exit 2; }
done

FIX=$(mktemp -d) || exit 2
trap 'rm -rf "$FIX"' EXIT
mkdir -p "$FIX/clean" "$FIX/dirty" "$FIX/empty"
printf 'theorem t : 2 + 2 = 4 := by norm_num\n'                       > "$FIX/clean/A.lean"
printf 'theorem u : True := by\n  sorry\ntheorem v : True := by admit\n' > "$FIX/dirty/B.lean"
printf '%%%% LEAN-GAP: G1 -- a named gap\n%%%% LEAN-GAP: G2 -- another\n' > "$FIX/gaps.tex"
printf 'no gap markers here\n'                                         > "$FIX/nogaps.tex"

PASSED=0; FAILED=0
check() { # <label> <expect PASS|FAIL> <script> <env...>
  local label="$1" expect="$2" script="$3"; shift 3
  local out rc got
  out=$(env "$@" bash "$script" 2>&1); rc=$?
  if [ "$rc" -eq 0 ]; then got=PASS; else got=FAIL; fi
  if [ "$got" = "$expect" ]; then
    PASSED=$((PASSED+1)); printf '  ok   %-44s (%s)\n' "$label" "$got"
  else
    FAILED=$((FAILED+1)); printf '  FAIL %-44s expected %s got %s\n' "$label" "$expect" "$got"
    printf '       %s\n' "$(printf '%s' "$out" | head -2)"
  fi
}

echo "lean-no-sorry.sh"
check "no project dir -- cannot look"    FAIL "$NO_SORRY" GC_LEAN_PROJECT_DIR=
check "project dir absent"               FAIL "$NO_SORRY" GC_LEAN_PROJECT_DIR="$FIX/nope"
check "no .lean files -- cannot look"    FAIL "$NO_SORRY" GC_LEAN_PROJECT_DIR="$FIX/empty"
check "sorry and admit present"          FAIL "$NO_SORRY" GC_LEAN_PROJECT_DIR="$FIX/dirty"
check "clean project"                    PASS "$NO_SORRY" GC_LEAN_PROJECT_DIR="$FIX/clean"

echo "lean-gap-accounting.sh"
check "no gap document set"              FAIL "$GAP_ACCT" GC_LEAN_PROJECT_DIR="$FIX/clean" GC_LEAN_GAP_DOCUMENT=
check "gap document absent"              FAIL "$GAP_ACCT" GC_LEAN_PROJECT_DIR="$FIX/clean" GC_LEAN_GAP_DOCUMENT="$FIX/absent.tex"
check "no .lean files -- cannot look"    FAIL "$GAP_ACCT" GC_LEAN_PROJECT_DIR="$FIX/empty" GC_LEAN_GAP_DOCUMENT="$FIX/nogaps.tex"
check "2 sorries vs 0 gap entries"       FAIL "$GAP_ACCT" GC_LEAN_PROJECT_DIR="$FIX/dirty" GC_LEAN_GAP_DOCUMENT="$FIX/nogaps.tex"
check "2 sorries, 2 gaps, 0 beads"       FAIL "$GAP_ACCT" GC_LEAN_PROJECT_DIR="$FIX/dirty" GC_LEAN_GAP_DOCUMENT="$FIX/gaps.tex"
check "0/0/0 all equal"                  PASS "$GAP_ACCT" GC_LEAN_PROJECT_DIR="$FIX/clean" GC_LEAN_GAP_DOCUMENT="$FIX/nogaps.tex"

echo "lean-baseline-green.sh"
check "no project dir -- cannot look"    FAIL "$BASELINE" GC_LEAN_PROJECT_DIR=
check "project dir absent"               FAIL "$BASELINE" GC_LEAN_PROJECT_DIR="$FIX/nope"
check "not a Lean workspace"             FAIL "$BASELINE" GC_LEAN_PROJECT_DIR="$FIX/clean"

echo
echo "passed=$PASSED failed=$FAILED"
[ "$FAILED" -eq 0 ] || exit 1
echo "lean-formalize gate smoke test: ALL PASS"
