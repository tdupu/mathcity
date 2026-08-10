#!/bin/sh
# Static regression test: proves the six build-basic-briefed dispatch docs
# (push-the-fleet, mathcity.work, mayor-math-prime, prime-clerk, mayor-math,
# adjudicate-brief) each document a bead-scoped artifact_root form, and that
# push-the-fleet no longer documents the old bare-rig-root dispatch form.
# Does not require a live city — pure text-fixture check.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PUSH_SKILL="$PACK_ROOT/subdomains/dev/skills/push-the-fleet/SKILL.md"
WORK_SKILL="$PACK_ROOT/skills/work/SKILL.md"
MAYOR_PRIME_SKILL="$PACK_ROOT/skills/mayor-math-prime/SKILL.md"
PRIME_CLERK_SKILL="$PACK_ROOT/skills/prime-clerk/SKILL.md"
MAYOR_MATH_SKILL="$PACK_ROOT/skills/mayor-math/SKILL.md"
ADJUDICATE_BRIEF_SKILL="$PACK_ROOT/skills/adjudicate-brief/SKILL.md"

fail() {
  echo "I'm sorry, I can't do that - $1" >&2
  exit 1
}

[ -f "$PUSH_SKILL" ] || fail "missing $PUSH_SKILL"
[ -f "$WORK_SKILL" ] || fail "missing $WORK_SKILL"
[ -f "$MAYOR_PRIME_SKILL" ] || fail "missing $MAYOR_PRIME_SKILL"
[ -f "$PRIME_CLERK_SKILL" ] || fail "missing $PRIME_CLERK_SKILL"
[ -f "$MAYOR_MATH_SKILL" ] || fail "missing $MAYOR_MATH_SKILL"
[ -f "$ADJUDICATE_BRIEF_SKILL" ] || fail "missing $ADJUDICATE_BRIEF_SKILL"

CHECKS=0
PASS=0

check() {
  CHECKS=$((CHECKS + 1))
  if eval "$2"; then
    PASS=$((PASS + 1))
    echo "  PASS: $1"
  else
    echo "  FAIL: $1"
  fi
}

# 1. push-the-fleet no longer documents the bare rig-root dispatch form.
check "push-the-fleet: no bare rig-root artifact_root in dispatch example" \
  '! grep -q "artifact_root=<rig-artifact-root>" "$PUSH_SKILL"'

# 2. push-the-fleet documents the per-bead scoped form.
check "push-the-fleet: documents .gc-builds/<bead-id> scoping" \
  'grep -q "artifact_root=<rig-root>/.gc-builds/<bead-id>" "$PUSH_SKILL"'

# 3. mathcity.work documents the per-bead scoped form for build-basic-briefed.
check "mathcity.work: documents .gc-builds/<bead> scoping for build-basic-briefed" \
  'grep -q "artifact_root=<rig-root>/.gc-builds/<bead>" "$WORK_SKILL"'

# 4. mayor-math-prime documents the per-bead scoped form for build-basic-briefed.
check "mayor-math-prime: documents .gc-builds/<artifact-bead> scoping for build-basic-briefed" \
  'grep -q "artifact_root=<rig-root>/.gc-builds/<artifact-bead>" "$MAYOR_PRIME_SKILL"'

# 5. prime-clerk documents the per-bead scoped form for build-basic-briefed.
check "prime-clerk: documents .gc-builds/<artifact-bead> scoping for build-basic-briefed" \
  'grep -q "artifact_root=<rig-root>/.gc-builds/<artifact-bead>" "$PRIME_CLERK_SKILL"'

# 6. mayor-math documents the per-bead scoped form for build-basic-briefed.
check "mayor-math: documents .gc-builds/<bead> scoping for build-basic-briefed" \
  'grep -q "artifact_root=<rig-root>/.gc-builds/<bead>" "$MAYOR_MATH_SKILL"'

# 7. adjudicate-brief documents the per-bead scoped form for build-basic-briefed.
check "adjudicate-brief: documents .gc-builds/<ARTIFACT> scoping for build-basic-briefed" \
  'grep -q "artifact_root=<city-root>/hecke/.gc-builds/<ARTIFACT>" "$ADJUDICATE_BRIEF_SKILL"'

echo ""
if [ "$PASS" -eq "$CHECKS" ]; then
  echo "PASS $PASS/$CHECKS - artifact_root scoping regression test"
  exit 0
else
  echo "FAIL $PASS/$CHECKS - artifact_root scoping regression test"
  exit 1
fi
