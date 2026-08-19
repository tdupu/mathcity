#!/bin/sh
# mathcity/tests/mctl-shim-callsite/smoke_test.sh
#
# Guards the mctl entry-point contract:
#
#   1. bin/mctl exists, is executable, and execs assets/scripts/mctl.py.
#   2. bin/mctl has at least one real caller — check-briefs. An MCP server is
#      being built on this CLI; a CLI with zero callers is the top project risk,
#      so the one wired call site must not silently regress.
#   3. No skill bypasses the shim by invoking assets/scripts/mctl.py directly.
#
# Static only, in the style of tests/dolt-preflight-exit-codes/smoke_test.sh
# part A: needs no live gc, bd, Dolt server, or city.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="$(cd "$HERE/../.." && pwd)"
SHIM="$PACK/bin/mctl"
CALLER="$PACK/skills/check-briefs/SKILL.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "=== 1. the shim itself ==="

[ -f "$SHIM" ] || fail "missing entry point: bin/mctl"
[ -x "$SHIM" ] || fail "bin/mctl is not executable (chmod +x, and commit the mode bit)"
grep -q 'assets/scripts/mctl.py' "$SHIM" \
  || fail "bin/mctl does not hand off to assets/scripts/mctl.py"
grep -q '^exec ' "$SHIM" \
  || fail "bin/mctl must exec, so stdin and the exit code pass through unchanged"
echo "ok: bin/mctl is an executable exec-shim over assets/scripts/mctl.py"

echo "=== 2. check-briefs routes through the shim ==="

[ -f "$CALLER" ] || fail "missing call site: skills/check-briefs/SKILL.md"

grep -q 'bin/mctl' "$CALLER" \
  || fail "check-briefs no longer names bin/mctl — mctl is back to zero callers"
grep -q '"\$MCTL" briefs list' "$CALLER" \
  || fail "check-briefs no longer invokes 'mctl briefs list'; the stack-reading
step has regressed to hand-rolled shell"
grep -q 'decision_state' "$CALLER" \
  || fail "check-briefs invokes mctl but never consumes decision_state"

# The output contract: still a table sorted by unlock_count descending.
grep -q 'unlock_count' "$CALLER" \
  || fail "check-briefs no longer reports unlock_count"
grep -q 'unlock_count. descending\|unlock_count` descending' "$CALLER" \
  || fail "check-briefs no longer states the unlock_count-descending sort"
echo "ok: check-briefs calls bin/mctl briefs list and keeps the output contract"

echo "=== 3. nobody bypasses the shim ==="

SEARCH_DIRS="$PACK/skills"
for d in "$PACK"/subdomains/*/skills; do
  [ -d "$d" ] || continue
  SEARCH_DIRS="$SEARCH_DIRS $d"
done

# Match invocation shape only — prose and comments may name the file as the
# thing NOT to call (as check-briefs does when it explains the contract).
hits=$(grep -rnE '(^|[^[:alnum:]_])(python3?|exec|bash|sh)[[:space:]][^#]*assets/scripts/mctl\.py' \
         $SEARCH_DIRS | grep -v ':[[:space:]]*#' || true)
[ -z "$hits" ] || fail "skill invokes mctl.py directly instead of bin/mctl:
$hits"
echo "ok: no skill bypasses bin/mctl"

echo "ALL MCTL SHIM CALL-SITE CHECKS PASSED"
