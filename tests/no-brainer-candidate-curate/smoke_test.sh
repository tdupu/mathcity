#!/usr/bin/env bash
# The no-brainer candidate accumulation loop must be able to fire.
#
# Defect: gates are constructed either by hand or by no-brainer accumulation.
# The accumulation half has never run once -- `no-brainer-candidate-curate`
# does not appear in `order.fired` in any of the six .gc/events.jsonl archives
# (2026-07-18 -> 2026-08-20). Git shows why: it was born trigger="manual",
# scope="rig" in 7715c4f (2026-08-10) and was never touched. Two independent
# reasons it cannot work:
#
#   1. trigger="manual" -- nothing schedules it.
#   2. scope="rig" -- the candidates are at the CITY ROOT (24 in
#      <city-root>/.beads/.gates-candidate-pile, 3 in
#      <city-root>/.beads/briefs/.gates-candidate-pile), which is not a
#      registered rig. This is the identical unreachability bug already
#      diagnosed for the pile drain (see tests/brief-pile-drain/smoke_test.sh).
#
# The fix mirrors the drain: a city-scoped sibling, with the rig-scoped order
# kept because one rig (lmfdb) does hold a candidate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RIG_ORDER="$ROOT/orders/no-brainer-candidate-curate.toml"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Scan directives, never raw file: a TOML comment explaining the retired
# $HOME-absolute root must not read as the defect it warns about.
directives() { sed 's/[[:space:]]*$//' "$1" | grep -vE '^[[:space:]]*#'; }

# --- 1. The accumulation loop can fire without a human ----------------------
if directives "$RIG_ORDER" | grep -Eq '^trigger[[:space:]]*=[[:space:]]*"manual"'; then
  no "no-brainer-candidate-curate is trigger=manual; the accumulation loop can never fire on its own"
else
  ok "no-brainer-candidate-curate has a self-firing trigger"
fi

# --- 2. A city-scoped curate order exists -----------------------------------
city_curate=""
for order in "$ROOT"/orders/no-brainer-candidate-curate*.toml; do
  grep -Eq '^scope[[:space:]]*=[[:space:]]*"city"' "$order" || continue
  grep -Eq '^formula[[:space:]]*=[[:space:]]*"no-brainer-candidate-curate"' "$order" || continue
  city_curate="$order"
  break
done

if [ -n "$city_curate" ]; then
  ok "a city-scoped order runs the curate formula ($(basename "$city_curate"))"
else
  no "every curate order is rig-scoped; the city-root candidate piles are unreachable"
fi

# --- 3. Its condition targets the city-root candidate piles -----------------
# Both roots are live: .beads/.gates-candidate-pile (24) is the one
# catch-no-brainer's SKILL.md names, and .beads/briefs/.gates-candidate-pile
# (3) is the artifact_root form the formula also resolves. Checking only one
# leaves the other stranded.
if [ -n "$city_curate" ]; then
  if grep -Fq '.beads/.gates-candidate-pile' "$city_curate" \
     && grep -Fq '.beads/briefs/.gates-candidate-pile' "$city_curate"; then
    ok "the city curate order's condition checks both candidate roots"
  else
    no "the city curate order does not check both city-root candidate piles"
  fi
  if directives "$city_curate" | grep -Eq '\$HOME/|\$\{HOME[:}]|~/\.gc'; then
    no "the city curate order uses an absolute \$HOME candidate root (retired by gsp-5h17)"
  else
    ok "the city curate order's candidate root is city-root-relative"
  fi
fi

# --- 4. The rig-scoped curate order survives --------------------------------
# lmfdb holds 1 candidate; adding the city order must not take its path away.
if grep -Eq '^scope[[:space:]]*=[[:space:]]*"rig"' "$RIG_ORDER"; then
  ok "the rig-scoped curate order is still present for rig candidate piles"
else
  no "the rig-scoped curate order lost its rig scope"
fi

echo "no-brainer-candidate-curate: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
