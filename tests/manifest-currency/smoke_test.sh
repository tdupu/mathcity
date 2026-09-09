#!/bin/sh
# manifest-currency — the `manifest-current` gate must detect a STALE index,
# not merely a malformed one (#102).
#
# The three fixtures are the ones the issue measured, kept verbatim so this
# test and the report stay comparable:
#
#   A  index ABSENT over an empty stack   -> PASS  (legitimate fresh city)
#   B  index MALFORMED                    -> FAIL  (control: the gate CAN fail)
#   C  index VALID but STALE, 3 briefs /  -> FAIL  (the defect: was exit 0)
#      1 indexed
#
# Fixture B is a CONTROL and must stay. Before the fix the gate returned
# non-zero on B and zero on C, which is what made it look like coverage: it
# was a working check of the wrong property. A version of this test without B
# could not tell "detects staleness" from "fails on everything".
set -eu

CHK="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts/checks" && pwd)/brief-check.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

mkdir -p "$TMP/A/stack"

mkdir -p "$TMP/B/stack"
echo 'brief' > "$TMP/B/stack/a.md"
printf '%s\n' '{"slug":"a"' > "$TMP/B/stack/.index.jsonl"

mkdir -p "$TMP/C/stack"
for n in a b c; do echo 'brief' > "$TMP/C/stack/$n.md"; done
printf '%s\n' '{"slug":"a","path":"stack/a.md","source":"x","unlock_count":0,"created_at":"2026-01-01","gate_profile":"decision"}' \
  > "$TMP/C/stack/.index.jsonl"

check() {
  name="$1"; root="$2"; want="$3"; wantmsg="${4:-}"
  # `if` rather than `out=$(...); rc=$?` -- under `set -eu` the assignment form
  # terminates the script at the assignment when the command exits non-zero,
  # which is the same trap this test's subject was fixed for.
  if out="$(BRIEF_ROOT="$root" sh "$CHK" manifest-current 2>&1)"; then rc=0; else rc=$?; fi
  ok=1
  [ "$rc" = "$want" ] || ok=0
  if [ -n "$wantmsg" ]; then
    printf '%s' "$out" | grep -qi "$wantmsg" || ok=0
  fi
  if [ "$ok" = 1 ]; then
    pass=$((pass + 1)); echo "  ok   $name (exit=$rc)"
  else
    fail=$((fail + 1))
    echo "  FAIL $name: exit=$rc want=$want msg-want='$wantmsg'"
    printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

echo "manifest-currency:"
check "A absent index over empty stack passes (bootstrap)" "$TMP/A" 0
check "B malformed index fails (control)"                  "$TMP/B" 1 "invalid JSONL"
check "C valid-but-stale index fails"                      "$TMP/C" 1 "STALE"

echo "manifest-currency: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
