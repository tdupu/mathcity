#!/bin/sh
# gate-status-tokens — G14 must accept what POLICY mandates (#67).
#
# The bug: GATE_STATUS_DEFAULT was "PASS|N/A", and `\b` after PASS cannot match
# PASSED (S->E is word-to-word, no boundary). So the gate REJECTED both tokens
# T7/G14 mandates and ACCEPTED two it does not.
#
# Case REQUIRED is the one that must keep FAILING. T7 makes G14 a TRI-state and
# the third state is not a pass: "REQUIRED means execution is owed before
# adjudication". Widening the pattern to make more briefs pass would convert an
# owed obligation into a satisfied gate.
set -eu

CHK="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts/checks" && pwd)/brief-check.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

# The pattern under test, read from the script so this cannot drift from it.
# G14's accepted set is the THIRD ARGUMENT at its own require_gate call site --
# POLICY T7 gives G14 its own tri-state, so the gate passes it explicitly. This
# used to read GATE_STATUS_DEFAULT, which was only equivalent while the widening
# was GLOBAL -- and a global widening is the defect (it let `G1: PASSED` satisfy
# the test-evidence gate without the five-field structural check). Reading the
# default made this test assert the bug. Read what it claims to test.
DEFAULT="$(grep -E 'require_gate .*"G14 ' "$CHK" | head -1 | sed -E 's/.*"G14 [^"]*"[[:space:]]*"([^"]*)".*/\1/')"
if [ -z "$DEFAULT" ]; then
  echo "gate-status-tokens: CANNOT VERIFY -- could not read G14's vocabulary from $CHK" >&2
  echo "  (an empty accepted-set would make every case below pass vacuously)" >&2
  exit 2
fi

check() {  # $1 token, $2 want (accept|reject)
  if printf 'G14 Test-execution: %s\n' "$1" | grep -Eq "G14 Test-execution:[[:space:]]*($DEFAULT)\\b"; then
    got=accept
  else
    got=reject
  fi
  if [ "$got" = "$2" ]; then
    pass=$((pass + 1)); echo "  ok   $1 -> $got"
  else
    fail=$((fail + 1)); echo "  FAIL $1 -> $got (want $2)"
  fi
}

echo "gate-status-tokens (GATE_STATUS_DEFAULT=$DEFAULT):"

# POLICY-mandated pass states (subdomains/brief-system/POLICY.md T7 / G14)
check "PASSED"          accept
check "NOT APPLICABLE"  accept

# Legacy spellings still in the live corpus -- 3 of the 12 stack briefs that
# carry a G14 line use these. Failing them would move briefs AWAY from the
# front end, which is the opposite of what #67 requires.
check "PASS"            accept
check "N/A"             accept

# The third tri-state: an OWED obligation, not a pass.
check "REQUIRED"        reject

# Explicit failure states stay failures.
check "FAIL"            reject
check "BLOCKED"         reject

echo "gate-status-tokens: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
