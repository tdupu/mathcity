#!/bin/sh
# Static regression test: work-briefed must resolve child dispatch targets from
# the Gas City rig registry, support the commissioning path, and preserve the
# known simple/full continuation paths.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FORMULA="$ROOT/formulas/work-briefed.toml"

fail() {
  echo "I'm sorry, I can't do that - $1" >&2
  exit 1
}

[ -f "$FORMULA" ] || fail "missing $FORMULA"

grep -q '\[vars.child_run_target\]' "$FORMULA" \
  || fail "missing child_run_target var"
grep -q 'default = "auto"' "$FORMULA" \
  || fail "child_run_target does not default to auto"
grep -q 'gc rig list --json' "$FORMULA" \
  || fail "formula does not consult the rig registry"
grep -q 'startswith($p + "-")' "$FORMULA" \
  || fail "formula does not use bead-prefix matching"
grep -q 'gc sling "$CHILD_RUN_TARGET" {{source_bead}} --on simple-work-briefed' "$FORMULA" \
  || fail "simple child dispatch does not use resolved target"
grep -q 'gc sling "$CHILD_RUN_TARGET" {{source_bead}} --on build-basic-briefed' "$FORMULA" \
  || fail "full child dispatch does not use resolved target"
grep -q 'gc sling "$CHILD_RUN_TARGET" {{source_bead}} --on commission-work-briefed' "$FORMULA" \
  || fail "commission child dispatch does not use resolved target"
grep -q 'COMMISSION' "$FORMULA" \
  || fail "formula does not define a commissioning route"
grep -q 'SIMPLE_CONTINUE' "$FORMULA" \
  || fail "formula does not define simple continue route"
grep -q 'FULL_CONTINUE' "$FORMULA" \
  || fail "formula does not define full continue route"
grep -q 'EXPLICIT_CONTINUE' "$FORMULA" \
  || fail "formula does not define explicit continue route"

if grep -q 'basename $(git rev-parse --show-toplevel' "$FORMULA"; then
  fail "formula still derives the target rig from git checkout basename"
fi

echo "PASS work-briefed routing target regression"
