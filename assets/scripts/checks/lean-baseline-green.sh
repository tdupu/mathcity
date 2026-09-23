#!/usr/bin/env bash
set -euo pipefail

# Lean baseline gate: the project must ELABORATE.
#
# P6.2 note. The failure this gate is built to avoid is its own: a build check
# whose operand does not resolve, returning "no errors" because it never looked.
# Every unresolved operand below is an explicit FAIL, never a pass. It also never
# starts a cold Mathlib build -- that is a multi-hour operation and a human
# decision, so an absent cache is reported, not resolved.

fail() { echo "lean-baseline-green: $*" >&2; exit 1; }

PROJ="${GC_LEAN_PROJECT_DIR:-${LEAN_PROJECT_DIR:-}}"
[ -n "$PROJ" ] || fail "no Lean project dir (set GC_LEAN_PROJECT_DIR); refusing to pass a check that cannot look"
[ -d "$PROJ" ] || fail "Lean project dir does not exist: $PROJ"

# A Lean workspace needs both a lakefile and a pinned toolchain.
if [ ! -f "$PROJ/lakefile.lean" ] && [ ! -f "$PROJ/lakefile.toml" ]; then
  fail "no lakefile.lean or lakefile.toml under $PROJ -- not a Lean workspace"
fi
[ -f "$PROJ/lean-toolchain" ] || fail "no lean-toolchain under $PROJ -- toolchain is unpinned"

command -v lake >/dev/null 2>&1 || fail "lake is not on PATH"

# Refuse to trigger a cold Mathlib build.
ALLOW_COLD="${GC_LEAN_ALLOW_COLD_BUILD:-false}"
CACHE_DIR="$PROJ/.lake/packages/mathlib/.lake/build/lib"
if [ "$ALLOW_COLD" != "true" ] && [ -d "$PROJ/.lake/packages/mathlib" ] && [ ! -d "$CACHE_DIR" ]; then
  fail "Mathlib present but its build cache is absent -- this would start a COLD build. Set GC_LEAN_ALLOW_COLD_BUILD=true only as a deliberate human decision."
fi

# Redirect and read $? directly. Piping into head/tail reports the PIPE's status
# and turns a failing build into rc=0 -- the exact defect this repo has hit before.
OUT=$(mktemp); trap 'rm -f "$OUT"' EXIT
set +e
( cd "$PROJ" && lake build ) >"$OUT" 2>&1
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  echo "lean-baseline-green: build FAILED (rc=$RC) in $PROJ" >&2
  tail -40 "$OUT" >&2
  exit 1
fi

echo "lean-baseline-green: PASS (lake build rc=0 in $PROJ)"
