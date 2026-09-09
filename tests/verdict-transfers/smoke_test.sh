#!/bin/sh
# verdict-transfers — does a review verdict survive a rebase? (#201 rule 1)
#
# Case 2 is the control. A tool that only ever answers YES would "save" every
# re-review including the ones that catch real regressions, which is worse than
# no tool. Case 3 is the other control: an unparseable file must be UNDECIDABLE,
# never "identical" -- absence of a readable diff is not absence of a diff.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/verdict-transfers.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

cd "$TMP"
git init -q . && git config user.email t@e && git config user.name t

w() { printf '%s\n' "$1" > mod.py; }

# c1 -> c2: docstrings and comments only. Executable content identical.
w 'def f(x):
    """original."""
    return x + 1'
git add -A && git commit -q -m c1
C1=$(git rev-parse --short HEAD)

w 'def f(x):
    """REWORDED, and a comment added."""
    # this comment is new
    return x + 1'
git add -A && git commit -q -m c2
C2=$(git rev-parse --short HEAD)

# c3: a real behaviour change
w 'def f(x):
    """REWORDED, and a comment added."""
    # this comment is new
    return x + 2'
git add -A && git commit -q -m c3
C3=$(git rev-parse --short HEAD)

# c4: syntactically broken
printf 'def f(x:\n' > mod.py
git add -A && git commit -q -m c4
C4=$(git rev-parse --short HEAD)

run() {  # $1 name, $2 want-exit, $3 old, $4 new
  if out="$(python3 "$SCRIPT" "$3" "$4" mod.py 2>&1)"; then rc=0; else rc=$?; fi
  if [ "$rc" = "$2" ]; then
    pass=$((pass + 1)); echo "  ok   $1 (exit=$rc)"
  else
    fail=$((fail + 1)); echo "  FAIL $1: exit=$rc want=$2"; printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

echo "verdict-transfers:"

# 1. docstring + comment churn only -> the verdict TRANSFERS
run "docstring/comment-only change transfers" 0 "$C1" "$C2"

# 2. CONTROL: a real behaviour change must NOT transfer
run "behaviour change does NOT transfer"      1 "$C2" "$C3"

# 3. CONTROL: unparseable is UNDECIDABLE, never "identical"
run "unparseable file is undecidable, not ok" 2 "$C3" "$C4"

# 4. a path absent at one ref is undecidable too
if out="$(python3 "$SCRIPT" "$C1" "$C1" nosuch.py 2>&1)"; then rc=0; else rc=$?; fi
if [ "$rc" = 2 ]; then pass=$((pass+1)); echo "  ok   missing path is undecidable (exit=2)"
else fail=$((fail+1)); echo "  FAIL missing path gave exit=$rc want=2"; fi

echo "verdict-transfers: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
