#!/bin/sh
# Regression test for tdupu/mathcity#20.
#
# The missing assertion the issue names: a `.pile/` holding only non-`.md`
# files (e.g. `*.md.bak` residue, or a brief whose `.md` was removed while a
# `.bak` survived) must be DISTINGUISHABLE from a truly-empty pile. Every
# selector in the pipeline globs `*.md`, so before the fix a `.bak`-only pile
# read as empty and `shuffle-result` passed vacuously — hiding two
# pending-review briefs for weeks. This asserts `shuffle-result` now fails
# loud on such a pile, and still passes on a genuinely-empty one.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
RIG_ROOT="$(cd "$HERE/../.." && pwd)"          # the mathcity pack dir
CHECK="$RIG_ROOT/assets/scripts/checks/brief-check.sh"

PASS_COUNT=0
FAIL_COUNT=0

# run_case NAME EXPECTED_STATUS SETUP_FN
run_case() {
  name="$1"; expected="$2"; setup="$3"
  root="$(mktemp -d)"
  mkdir -p "$root/.pile/.rejected" "$root/stack"
  : > "$root/stack/.index.jsonl"               # valid empty manifest
  "$setup" "$root"
  status=0
  (cd "$RIG_ROOT" && BRIEF_ROOT="$root" "$CHECK" shuffle-result) >"$root/out" 2>"$root/err" || status=$?
  if [ "$status" = "$expected" ]; then
    echo "PASS: $name (exit=$status, expected=$expected)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "FAIL: $name (exit=$status, expected=$expected)"
    echo "  --- stderr ---"; sed 's/^/  /' "$root/err"
  fi
  rm -rf "$root"
}

setup_bak_only() {  # residue-only pile: MUST fail (this is the #20 fix)
  printf 'stale snapshot\n' > "$1/.pile/gsp-xztzw.md.bak"
  printf 'stale snapshot\n' > "$1/.pile/gsp-t7pp5.md.bak"
}
setup_truly_empty() {  # nothing anywhere: MUST pass (legit empty-pile no-op)
  :
}
setup_pending_md() {  # a real .md brief, nothing shuffled: MUST fail (pre-existing check)
  printf '# a pending brief\n' > "$1/.pile/gsp-live1.md"
}

echo "=== #20: a .bak-only pile is NOT an empty pile — must fail loud ==="
run_case "bak-only pile fails (was a vacuous pass)" 1 setup_bak_only

echo "=== a truly-empty pile is a legit no-op — must pass ==="
run_case "truly-empty pile passes" 0 setup_truly_empty

echo "=== regression guard: a pending .md with nothing shuffled still fails ==="
run_case "pending .md pile fails" 1 setup_pending_md

echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
