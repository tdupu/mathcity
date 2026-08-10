#!/bin/sh
# brief-stack-low.sh — combined stack-depth low-water probe for the brief
# pipeline (gsp-i9j; the human adjudicator 2026-06-30 "ring the bell" redesign).
#
# Measures three signals over the top-level *.md briefs in each configured
# brief directory (the human adjudicator 2026-06-30: "a combination of these should be
# good"):
#
#   approved    files whose YAML frontmatter matches '^status: approved'
#               (prefix match — includes approved-with-minor-residue; the
#               the human adjudicator-ready set)
#   total       all top-level *.md files (rough stack size; .pile/, archive
#               subdirs, and *.md.bak never match the glob)
#   unlock_pos  files whose 'unlock_count:' leading value is > 0 (the
#               prioritized subset)
#
# The stack is LOW when ANY signal is <= the trigger threshold.
#
# Exit status: 0 = low, 1 = healthy, 2 = usage error.
# Stdout: one-line JSON summary of the counts, threshold, and verdict.
#
#   --emit    When the stack is low, also emit the city event that order
#             brief-watchdog-refill-on-stack-low listens for (best-effort;
#             a failed emit never fails this script). Intended caller: the
#             post-decision hook (gsp-xhc) after filing a brief decision.
#
# Environment:
#   BRIEF_STACK_DIRS           space-separated brief directories
#                              (default: .beads/briefs/stack, rig-relative
#                              per assets/brief-pipeline/paths.toml)
#   BRIEF_STACK_LOW_THRESHOLD  trigger threshold (default: stack_low_trigger
#                              from assets/brief-pipeline/thresholds.toml,
#                              else 1)
#   BRIEF_STACK_LOW_EVENT      event type emitted with --emit
#                              (default: brief.stack-low)
set -eu

EMIT=0
case "${1:-}" in
  --emit) EMIT=1 ;;
  "") ;;
  *) echo "usage: brief-stack-low.sh [--emit]" >&2; exit 2 ;;
esac

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
THRESHOLDS="$SCRIPT_DIR/../brief-pipeline/thresholds.toml"

threshold="${BRIEF_STACK_LOW_THRESHOLD:-}"
if [ -z "$threshold" ] && [ -f "$THRESHOLDS" ]; then
  threshold=$(awk -F= '/^[ \t]*stack_low_trigger[ \t]*=/ { gsub(/[^0-9]/, "", $2); print $2; exit }' "$THRESHOLDS")
fi
: "${threshold:=1}"

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
dirs="${BRIEF_STACK_DIRS:-.beads/briefs/stack}"

approved=0
total=0
unlock_pos=0
for dir in $dirs; do
  [ -d "$dir" ] || continue
  set --
  for f in "$dir"/*.md; do
    [ -f "$f" ] && set -- "$@" "$f"
  done
  [ "$#" -gt 0 ] || continue

  total=$((total + $#))

  # grep exit 1 (no match) is masked by the pipe to wc — safe under set -e.
  n=$(grep -l '^status: approved' "$@" 2>/dev/null | wc -l | tr -d ' ')
  approved=$((approved + n))

  # Portable per-file flag counting (BSD awk has no ENDFILE): a file counts
  # when any unlock_count line's leading numeric value is > 0.
  n=$(awk '
    FNR == 1 { if (ok) c++; ok = 0 }
    /^unlock_count:/ { if ($2 + 0 > 0) ok = 1 }
    END { if (ok) c++; print c + 0 }
  ' "$@")
  unlock_pos=$((unlock_pos + n))
done

low=false
if [ "$approved" -le "$threshold" ]; then low=true; fi
if [ "$total" -le "$threshold" ]; then low=true; fi
if [ "$unlock_pos" -le "$threshold" ]; then low=true; fi

summary=$(printf '{"approved":%d,"total":%d,"unlock_pos":%d,"threshold":%d,"low":%s}' \
  "$approved" "$total" "$unlock_pos" "$threshold" "$low")

if [ "$low" = true ] && [ "$EMIT" -eq 1 ] && command -v gc >/dev/null 2>&1; then
  gc event emit "${BRIEF_STACK_LOW_EVENT:-brief.stack-low}" \
    --subject brief-stack \
    --message "brief stack low: approved=$approved total=$total unlock_pos=$unlock_pos threshold=$threshold" \
    --payload "$summary" >/dev/null 2>&1 || true
fi

printf '%s\n' "$summary"
if [ "$low" = true ]; then exit 0; else exit 1; fi
