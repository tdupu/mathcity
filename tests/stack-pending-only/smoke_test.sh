#!/bin/sh
# stack-pending-only — the PENDING stack must contain only pending briefs (#95).
#
# Case 1 is the control and must PASS. Without a fixture that passes, the suite
# cannot distinguish "detects decided briefs on the stack" from "fails on any
# stack at all" — and #95 is precisely a report about a check that was never
# there, so shipping a check that always fires would repeat the mistake in the
# opposite direction.
set -eu

CHK="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts/checks" && pwd)/brief-check.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

mkbrief() { mkdir -p "$(dirname "$1")"; printf -- '---\nstatus: %s\n---\n\nbody\n' "$2" > "$1"; }

run() {  # $1 name, $2 root, $3 want-exit, $4 want-substring (optional)
  if out="$(BRIEF_ROOT="$2" sh "$CHK" stack-pending-only 2>&1)"; then rc=0; else rc=$?; fi
  ok=1
  [ "$rc" = "$3" ] || ok=0
  if [ -n "${4:-}" ]; then printf '%s' "$out" | grep -q "$4" || ok=0; fi
  if [ "$ok" = 1 ]; then
    pass=$((pass + 1)); echo "  ok   $1 (exit=$rc)"
  else
    fail=$((fail + 1)); echo "  FAIL $1: exit=$rc want=$3 want-msg='${4:-}'"
    printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

echo "stack-pending-only:"

# 1. CONTROL — a genuinely pending stack passes
mkbrief "$TMP/a/stack/1.md" pending
run "a pending-only stack passes"              "$TMP/a" 0

# 2. a decided brief still on the pending stack
mkbrief "$TMP/b/stack/1.md" adjudicated
run "adjudicated brief on the stack is caught" "$TMP/b" 1 "TERMINAL status"

# 3. every terminal spelling counts, not just 'adjudicated'
for st in approved rejected deferred; do
  rm -rf "$TMP/c"; mkbrief "$TMP/c/stack/1.md" "$st"
  run "terminal status '$st' is caught"        "$TMP/c" 1 "TERMINAL status"
done

# 4. same slug in stack AND .adjudicated-archive — two authoritative locations
rm -rf "$TMP/d"
mkbrief "$TMP/d/stack/1.md" pending
mkbrief "$TMP/d/.adjudicated-archive/1.md" adjudicated
run "slug in both locations is caught"         "$TMP/d" 1 "BOTH"

# 5. an archive entry NOT also on the stack is normal, not a finding
rm -rf "$TMP/e"
mkbrief "$TMP/e/stack/1.md" pending
mkbrief "$TMP/e/.adjudicated-archive/2.md" adjudicated
run "archived brief with no stack twin passes" "$TMP/e" 0

# 6. no stack dir at all -> not an error (bootstrap), same as manifest-current
rm -rf "$TMP/f"; mkdir -p "$TMP/f"
run "absent stack dir does not fail"           "$TMP/f" 0

echo "stack-pending-only: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
