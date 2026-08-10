#!/bin/sh
# decision-record-exists.sh — CHECK-A for decision-enforce formula
#
# Verifies that a canonical `bd decision`-type bead exists for the
# adjudicated source bead, AND (when BRIEF_SLUG is set) that a brief-pipeline
# decision file also exists at ARTIFACT_ROOT/decisions/<slug>.toml.
#
# One-bead model (brief-system POLICY.md B2.2, 2026-07-12): the brief bead
# IS the decision bead — for brief adjudications the matching bead below is
# the brief bead itself (type=decision, closed with verdict fields), not a
# separately created decision bead. Standalone decision beads (push /
# kill-switch / non-brief authorizations) also satisfy the query.
#
# Exit codes:
#   0 — decision record(s) found; enforcement passes
#   1 — no decision record found; BLOCK downstream work
#   2 — bd unavailable or query error; fail closed
#
# Environment (set by gc from formula vars):
#   GC_VAR_SOURCE_BEAD   — bead ID of the adjudicated work item (required)
#   GC_VAR_BRIEF_SLUG    — brief slug to check the brief-pipeline record (optional)
#   GC_VAR_ARTIFACT_ROOT — brief pipeline root, default .beads/briefs
#                          (rig-relative per assets/brief-pipeline/paths.toml)
#   GC_CITY_PATH         — city root (default <city-root>)

set -eu

SOURCE_BEAD="${GC_VAR_SOURCE_BEAD:-}"
BRIEF_SLUG="${GC_VAR_BRIEF_SLUG:-}"
ARTIFACT_ROOT="${GC_VAR_ARTIFACT_ROOT:-.beads/briefs}"
CITY="${GC_CITY_PATH:-${GC_CITY:-$HOME/gt}}"

fail_block() {
  printf 'decision-record-exists: BLOCK: %s\n' "$*" >&2
  exit 1
}

fail_closed() {
  printf 'decision-record-exists: fail-closed: %s\n' "$*" >&2
  exit 2
}

if [ -z "$SOURCE_BEAD" ]; then
  fail_closed "GC_VAR_SOURCE_BEAD not set"
fi

if ! command -v bd >/dev/null 2>&1; then
  fail_closed "bd not found in PATH"
fi

if ! command -v jq >/dev/null 2>&1; then
  fail_closed "jq not found in PATH"
fi

# ---------------------------------------------------------------------------
# Check 1: bd decision bead referencing source_bead
# ---------------------------------------------------------------------------
# Query all open decision-type beads and check if any references SOURCE_BEAD
# in its metadata (source_bead key) or description body.
bd_found=false

decision_json="$(bd list --type decision --json 2>/dev/null)" || fail_closed "bd list --type decision failed"

if printf '%s\n' "$decision_json" | \
     jq -e --arg id "$SOURCE_BEAD" \
       'map(select(
          (.metadata.source_bead // "") == $id or
          (.description // "" | test($id; ""))
        )) | length > 0' >/dev/null 2>&1; then
  bd_found=true
fi

# Also scan closed decisions: a superseded or closed record still counts
# (the decision was recorded; the bead was acted on).
if [ "$bd_found" = "false" ]; then
  closed_json="$(bd list --type decision --all --json 2>/dev/null)" || true
  if [ -n "$closed_json" ] && printf '%s\n' "$closed_json" | \
       jq -e --arg id "$SOURCE_BEAD" \
         'map(select(
            (.metadata.source_bead // "") == $id or
            (.description // "" | test($id; ""))
          )) | length > 0' >/dev/null 2>&1; then
    bd_found=true
  fi
fi

# ---------------------------------------------------------------------------
# Check 2: brief-pipeline decision file (only when BRIEF_SLUG is set)
# ---------------------------------------------------------------------------
brief_file_found=true  # default pass when slug not provided
if [ -n "$BRIEF_SLUG" ]; then
  brief_file_found=false
  # Look in every rig's brief root under the city dir.
  for root in "$CITY"/*/"$ARTIFACT_ROOT"; do
    dec_file="$root/decisions/$BRIEF_SLUG.toml"
    if [ -f "$dec_file" ]; then
      brief_file_found=true
      break
    fi
  done
  # Also check the cwd-relative path (for single-rig invocations).
  if [ "$brief_file_found" = "false" ] && [ -f "$ARTIFACT_ROOT/decisions/$BRIEF_SLUG.toml" ]; then
    brief_file_found=true
  fi
fi

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$bd_found" = "true" ] && [ "$brief_file_found" = "true" ]; then
  printf 'decision-record-exists: PASS: bd decision record found for %s' "$SOURCE_BEAD"
  if [ -n "$BRIEF_SLUG" ]; then
    printf ' + brief-pipeline record found for %s' "$BRIEF_SLUG"
  fi
  printf '\n' >&2
  exit 0
fi

if [ "$bd_found" = "false" ]; then
  fail_block "no bd type=decision bead references source_bead=$SOURCE_BEAD — record the verdict on the brief bead and close it (one-bead model, B2.2; for standalone non-brief decisions use mathcity.record-decision) before proceeding"
fi

# bd_found=true but brief_file_found=false
fail_block "bd decision bead found for $SOURCE_BEAD but brief-pipeline record missing at ARTIFACT_ROOT/decisions/$BRIEF_SLUG.toml — file via brief-record-decision formula"
