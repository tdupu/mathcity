#!/bin/sh
# Stack-low combo check for the brief pipeline.
#
# Shared hook logic for the post-decision gate (gsp-xhc) and the
# stack-low watchdog trigger (gsp-i9j): single hook, dual event emit.
# The file-or-sendback-route formula runs this after routing and rings
# `brief.stack_low` when it exits 0.
#
#   exit 0  -> stack is LOW (any combo signal <= threshold); ring the bell
#   exit 1  -> stack is healthy
#
# Combo signals (the human adjudicator 2026-06-30: "a,b,c all seem good. I think a
# combination of these should be good."), measured over stack/*.md:
#   approved   — briefs with 'status: approved' frontmatter (the human adjudicator-ready)
#   total      — all stack briefs
#   unlock_pos — briefs with unlock_count > 0 (prioritized subset)
#
# LOW = union: ANY signal <= STACK_LOW_THRESHOLD (default 1; canonical
# value documented in assets/brief-pipeline/thresholds.toml [stack_low]).
#
# Caveat for pipelines that do not use unlock_count frontmatter: the
# unlock_pos signal reads 0 there, so the union check always fires.
# Tune the signal patterns (or drop unlock_pos) when wiring a rig whose
# briefs lack that field — tracked as gsp-i9j's refinement work.
#
# Prints the counts as a one-line JSON object on stdout either way, so
# callers can attach it verbatim as the event payload.
set -eu

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
ROOT="${BRIEF_ROOT:-.beads/briefs}"
THRESHOLD="${STACK_LOW_THRESHOLD:-1}"

approved=0
total=0
unlock_pos=0

if [ -d "$ROOT/stack" ]; then
  for f in "$ROOT"/stack/*.md; do
    [ -f "$f" ] || continue
    total=$((total + 1))
    if grep -Eq '^status:[[:space:]]*approved[[:space:]]*$' "$f"; then
      approved=$((approved + 1))
    fi
    if awk '/^unlock_count:[[:space:]]*[0-9]+/ { if ($2 + 0 > 0) found = 1 } END { exit(found ? 0 : 1) }' "$f"; then
      unlock_pos=$((unlock_pos + 1))
    fi
  done
fi

low=false
[ "$approved" -le "$THRESHOLD" ] && low=true
[ "$total" -le "$THRESHOLD" ] && low=true
[ "$unlock_pos" -le "$THRESHOLD" ] && low=true

printf '{"approved":%d,"total":%d,"unlock_pos":%d,"threshold":%d,"low":%s}\n' \
  "$approved" "$total" "$unlock_pos" "$THRESHOLD" "$low"

[ "$low" = "true" ] && exit 0
exit 1
