#!/bin/sh
# mathcity/tests/check-city-policy-pillar-coverage/smoke_test.sh
#
# #161: check-city-policy's Step 2 hard-coded a pillar list that stopped at
# CT12, so CT13 -- Adopted, four rules -- was invisible to its own enforcement
# skill. An auditor following the skill literally reached PASS having never
# looked at CT13.
#
# The fix (this branch) is not "add CT13 to the list": Step 2 now derives the
# pillar set live from POLICY-city.md (`grep -oE '^## Pillar CT[0-9]+'`)
# instead of enumerating from memory, so a *future* pillar cannot repeat this
# by construction. This test guards the two ways that fix can rot back into
# the original defect:
#
#   A. the live-derivation instruction itself gets edited away (reverted to a
#      static enumeration) -- checked structurally, not by re-deriving pillars
#      ourselves, since this skill's "pillar list" is prose an agent reads,
#      not code we can execute.
#   B. a pillar exists in POLICY-city.md with no matching key-signals guidance
#      in check-city-policy/SKILL.md -- allowed by design (renders
#      "unaudited (no guidance)" per Step 2), but must never be SILENT: this
#      test fails loud instead, which is strictly more visible than the
#      skill's own runtime fallback and catches drift before an audit run.
#
# Self-contained: no live city, no gc/bd, no network.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="$(cd "$HERE/../.." && pwd)"
POLICY="$PACK/subdomains/dev/POLICY-city.md"
SKILL="$PACK/subdomains/dev/skills/check-city-policy/SKILL.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -f "$POLICY" ] || fail "POLICY-city.md missing at $POLICY"
[ -f "$SKILL" ] || fail "check-city-policy/SKILL.md missing at $SKILL"

echo "=== A. Step 2 derives the pillar list live, not from a static enumeration ==="

grep -q "grep -oE '\^## Pillar CT\[0-9\]+'" "$SKILL" \
  || fail "check-city-policy/SKILL.md no longer derives its pillar list live from
POLICY-city.md (the grep -oE '^## Pillar CT[0-9]+' instruction is missing from
Step 2). This is the actual #161 fix -- a hard-coded pillar list will fall
behind POLICY-city.md again the next time a pillar opens. Restore the
live-derivation instruction; do not go back to enumerating pillars by hand."

grep -qi 'unaudited (no guidance)' "$SKILL" \
  || fail "check-city-policy/SKILL.md no longer names the 'unaudited (no
guidance)' fallback for a pillar with no key-signals prose. Without it, a
pillar the live derivation finds but this skill has no guidance for is
silently skipped or silently passed -- exactly the P6.1 shape #161 exists to
prevent."

echo "ok: Step 2 derives pillars live and names the unaudited-but-visible fallback"

echo "=== B. every pillar POLICY-city.md declares has matching key-signals guidance ==="

policy_pillars=$(grep -oE '^## Pillar CT[0-9]+' "$POLICY" | grep -oE 'CT[0-9]+' | sort -u)
[ -n "$policy_pillars" ] || fail "found zero '## Pillar CT<N>' headings in POLICY-city.md -- \
either the heading format changed (update both this test and check-city-policy's \
grep pattern) or the file is unreadable"

missing=""
for p in $policy_pillars; do
  # The key-signals bullet format is "- **CT<N> --" (Step 2 of the skill).
  grep -qE -- "- \*\*${p} " "$SKILL" || missing="$missing $p"
done

[ -z "$missing" ] || fail "POLICY-city.md declares pillar(s)$missing with no matching
'- **CT<N> --' key-signals bullet in check-city-policy/SKILL.md Step 2. The live
derivation will still AUDIT these pillars (Step 2's fallback), but every pillar
should get hand-written guidance once discovered rather than being left
'unaudited (no guidance)' indefinitely -- see Step 2's own instruction to add
guidance after auditing a previously-unguided pillar. Add a key-signals bullet
for:$missing"

echo "ok: every pillar in POLICY-city.md ($policy_pillars) has key-signals guidance"

echo "=== C. the roll-up template's illustrative pillar list is not stale ==="

# The Output format section lists today's pillars as an EXAMPLE (Step 2's
# derivation is what actually governs at audit time) -- but a stale example
# is exactly the kind of thing that gets copy-pasted back into a literal
# enumeration by a future editor who doesn't read the surrounding prose.
rollup_pillars=$(sed -n '/Per-pillar roll-up:/,/^Remediation:/p' "$SKILL" \
  | grep -oE 'CT[0-9]+' | sort -u)

missing=""
for p in $policy_pillars; do
  echo "$rollup_pillars" | grep -qx "$p" || missing="$missing $p"
done
[ -z "$missing" ] || fail "POLICY-city.md pillar(s)$missing are absent from the
Output format section's illustrative roll-up list in check-city-policy/SKILL.md.
Update the example list so a future reader doesn't copy a stale template."

echo "ok: roll-up example covers $rollup_pillars"

echo "ALL CHECK-CITY-POLICY PILLAR-COVERAGE CHECKS PASSED"
