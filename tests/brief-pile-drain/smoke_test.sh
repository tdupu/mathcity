#!/usr/bin/env bash
# The city-root pile must have a drain path.
#
# Defect (clerk sweep B1): five briefs (n=19-23) sat in
# <city-root>/.beads/briefs/.pile/ from 2026-08-15 with no order able to reach
# them. Every brief order was scope="rig", and the city root is not a
# registered rig in city.toml -- so `brief-*:rig:gt` never appears in
# .gc/events.jsonl even once. Meanwhile the city root holds the ONLY populated
# stack in the city (89 files / 88 index rows); all 15 rig stacks are empty.
# The order fired where there was nothing to drain and never where there was.
#
# The fix is a city-scoped sibling of brief-shuffle-fast-drain, not a change to
# where producers deposit -- see orders/brief-shuffle-fast-drain-city.toml for
# the evidence behind that choice.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Every scan below runs over `directives`, never the raw file. A TOML comment
# is prose: an order documenting why $HOME roots were retired, or a step
# warning an agent off $PACK_DIR, must not read as the defect it warns about.
# The first pass of this test failed on its own comments for exactly that
# reason -- the unanchored-match defect class, reproduced in the detector.
directives() { sed 's/[[:space:]]*$//' "$1" | grep -vE '^[[:space:]]*#'; }

# The lines a runtime actually executes: everything inside a ``` fence. A
# formula `description` is agent-executed instructions, but only the fenced
# command block is the command -- surrounding prose may legitimately NAME a
# bad path in order to warn against it, and lines 40/44 of the drain step do
# exactly that.
fenced() {
  awk '/^[[:space:]]*```/ { infence = !infence; next } infence' "$1"
}

# --- 1. Some brief order is city-scoped and drains a pile -------------------
# Not merely "a city-scoped brief order exists" (five already did, none of them
# drains) -- it must run a drain formula.
city_drain=""
for order in "$ROOT"/orders/brief-*.toml; do
  grep -Eq '^scope[[:space:]]*=[[:space:]]*"city"' "$order" || continue
  grep -Eq '^formula[[:space:]]*=[[:space:]]*"brief-shuffle-fast-drain"' "$order" || continue
  city_drain="$order"
  break
done

if [ -n "$city_drain" ]; then
  ok "a city-scoped order runs the drain formula ($(basename "$city_drain"))"
else
  no "every brief order is rig-scoped; the city-root pile has no drain path"
fi

# --- 2. Its condition targets the city-root pile ---------------------------
# City-scoped condition checks run with the city root as cwd (the idiom in
# brief-producer-failure-rollup-on-pile.toml), so the path must be
# city-root-relative, never $HOME-absolute -- the retired gsp-1pv shape.
if [ -n "$city_drain" ]; then
  if grep -Fq '.beads/briefs/.pile' "$city_drain"; then
    ok "the city drain order's condition targets .beads/briefs/.pile"
  else
    no "the city drain order does not check the city-root pile"
  fi
  # Anchored on the expansion being USED as a path prefix -- `$HOME/` or
  # `~/.gc` -- not on the token appearing anywhere in the file.
  if directives "$city_drain" | grep -Eq '\$HOME/|\$\{HOME[:}]|~/\.gc'; then
    no "the city drain order uses an absolute \$HOME pile root (retired by gsp-5h17)"
  else
    ok "the city drain order's pile root is city-root-relative, not \$HOME-absolute"
  fi
fi

# --- 3. Rig-scoped drain survives -------------------------------------------
# 7 briefs do sit in rig piles (gascity-packs 4, hecke 2, lmfdb 1). Adding the
# city drain must not take their drain away.
if grep -Eq '^scope[[:space:]]*=[[:space:]]*"rig"' "$ROOT/orders/brief-shuffle-fast-drain.toml"; then
  ok "the rig-scoped drain order is still present for rig piles"
else
  no "the rig-scoped drain order lost its rig scope"
fi

# --- 4. No cwd-relative pack asset in the drain step ------------------------
# Same root cause as #73 and the two brief-check.sh defects: the ralph runner's
# cwd is an agent work dir, never the pack root, so a bare `assets/...` literal
# resolves to nothing in production while passing a suite that runs from the
# pack root.
FORMULA="$ROOT/formulas/brief-shuffle-fast-drain.toml"
# A cwd-relative literal is `assets/` at the START of a path -- i.e. not
# preceded by `/`, which is what `<mathcity-pack-root>/assets/...` and
# `"$SOMETHING/assets/..."` both are.
RELATIVE_ASSET='(^|[^/[:alnum:]_.-])assets/'

# (4a) Nothing inside the fenced command block may be cwd-relative.
if fenced "$FORMULA" | grep -Eq "$RELATIVE_ASSET"; then
  no "the drain step's command block still has a cwd-relative assets/ literal"
  fenced "$FORMULA" | grep -nE "$RELATIVE_ASSET" | sed 's/^/    /'
else
  ok "the drain step's command block has no cwd-relative assets/ literal"
fi

# (4b) And no line ANYWHERE may hand a cwd-relative assets/ path to an
# interpreter or a flag, fenced or not -- an unfenced "Run python3
# assets/scripts/x.py" breaks in production just as surely.
INVOCATION="(python3?|bash|sh|/bin/sh)[[:space:]]+[^|]*${RELATIVE_ASSET}|--[a-z-]+[[:space:]]+assets/"
if directives "$FORMULA" | grep -Eq "$INVOCATION"; then
  no "the drain formula invokes a command on a cwd-relative assets/ path"
  directives "$FORMULA" | grep -nE "$INVOCATION" | sed 's/^/    /'
else
  ok "the drain formula never invokes a cwd-relative assets/ path"
fi

# Anchored on the expansion being USED -- `$PACK_DIR/` -- so the step may warn
# an agent off the variable by name without tripping its own detector.
if directives "$FORMULA" | grep -Eq '\$\{?(GC_)?PACK_DIR[:}]?/'; then
  no "brief-shuffle-fast-drain.toml expands \$PACK_DIR, which is never injected for a formula step"
else
  ok "brief-shuffle-fast-drain.toml does not rely on \$PACK_DIR"
fi

echo "brief-pile-drain: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
