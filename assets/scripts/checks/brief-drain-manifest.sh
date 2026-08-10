#!/bin/sh
# brief-drain-manifest.sh — emit pending manifest entries in unlock order.
#
# Reads stack/.index.jsonl (relative to BRIEF_ROOT, default .beads/briefs),
# filters out entries that are already decided/archived, then sorts by
# unlock_count (descending) and writes two output files:
#
#   <out_dir>/no-brainer-slugs.txt  — one slug per line, gate_profile=no_brainer
#   <out_dir>/full-brief-slugs.txt  — one slug per line, everything else
#
# Both files are always created (possibly empty).  Exit 0 on success.
# Exit 1 if the manifest is missing or contains invalid JSON lines.
#
# Environment:
#   BRIEF_ROOT   Root of the brief pipeline artifact tree. Default: .beads/briefs
#                (rig-relative per assets/brief-pipeline/paths.toml)
#   OUT_DIR      Directory to write output files into. Default: $BRIEF_ROOT/.drain-run
#
# Requires: sort, awk (POSIX); jq optional (used when available for validation).
set -eu

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
BRIEF_ROOT="${BRIEF_ROOT:-.beads/briefs}"
MANIFEST="$BRIEF_ROOT/stack/.index.jsonl"
OUT_DIR="${OUT_DIR:-${BRIEF_ROOT}/.drain-run}"

fail() {
  printf 'brief-drain-manifest: %s\n' "$*" >&2
  exit 1
}

mkdir -p "$OUT_DIR"
NB_FILE="$OUT_DIR/no-brainer-slugs.txt"
FULL_FILE="$OUT_DIR/full-brief-slugs.txt"
: > "$NB_FILE"
: > "$FULL_FILE"

if [ ! -f "$MANIFEST" ]; then
  # Nothing to drain; both output files are empty.
  exit 0
fi

# Use a temporary file to hold sorted pending entries: "<unlock_count> <slug> <profile>"
TMP_PENDING="$(mktemp "${TMPDIR:-/tmp}/bdm-pending.XXXXXX")"
trap 'rm -f "$TMP_PENDING"' EXIT

while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] && continue

  # Validate JSON when jq is available.
  if command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$line" | jq -e . >/dev/null 2>&1 ||
      fail "invalid JSON in $MANIFEST: $line"
  fi

  # Extract fields with awk (POSIX; handles simple JSON strings and numbers).
  # Fields expected: "slug", "gate_profile", "unlock_count", "status"
  slug=""
  gate_profile=""
  unlock_count="0"
  status=""

  if command -v jq >/dev/null 2>&1; then
    slug=$(printf '%s\n' "$line" | jq -r '.slug // ""')
    gate_profile=$(printf '%s\n' "$line" | jq -r '.gate_profile // ""')
    unlock_count=$(printf '%s\n' "$line" | jq -r '(.unlock_count // 0) | tostring')
    status=$(printf '%s\n' "$line" | jq -r '.status // ""')
  else
    # POSIX awk fallback for simple single-line JSON objects.
    slug=$(printf '%s\n' "$line" | awk -F'"' '{ for(i=1;i<=NF;i++) if ($i=="slug") { print $(i+2); exit } }')
    gate_profile=$(printf '%s\n' "$line" | awk -F'"' '{ for(i=1;i<=NF;i++) if ($i=="gate_profile") { print $(i+2); exit } }')
    status=$(printf '%s\n' "$line" | awk -F'"' '{ for(i=1;i<=NF;i++) if ($i=="status") { print $(i+2); exit } }')
    unlock_count=$(printf '%s\n' "$line" | awk -F'"' '
      BEGIN { found=0 }
      {
        for(i=1;i<=NF;i++) {
          if ($i ~ /unlock_count/) {
            # Value follows the key; grab numeric from remaining text
            rest = substr($0, index($0, "unlock_count") + length("unlock_count"))
            match(rest, /[0-9]+/)
            if (RSTART > 0) { print substr(rest, RSTART, RLENGTH); found=1 }
          }
        }
        if (!found) print "0"
      }')
  fi

  [ -z "$slug" ] && continue  # skip malformed entries missing slug

  # Skip already-decided or archived entries.
  case "$status" in
    decided|archived) continue ;;
  esac

  printf '%s %s %s\n' "$unlock_count" "$slug" "$gate_profile" >> "$TMP_PENDING"
done < "$MANIFEST"

[ -f "$TMP_PENDING" ] || touch "$TMP_PENDING"

# Sort descending by unlock_count (first field). NOTE: this is NOT insertion-order
# stable — POSIX sort, as a last resort, compares whole lines, so ties among
# equal unlock_count values order lexically (by slug then profile), not by the
# order they appeared in the manifest.
sort -k1,1nr "$TMP_PENDING" | while IFS=' ' read -r _uc slug profile; do
  [ -z "$slug" ] && continue
  case "$profile" in
    no_brainer|no-brainer) printf '%s\n' "$slug" >> "$NB_FILE" ;;
    *)                     printf '%s\n' "$slug" >> "$FULL_FILE" ;;
  esac
done

exit 0
