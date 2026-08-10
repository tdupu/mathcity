#!/bin/sh
# decision-alignment-check.sh — CHECK-B for decision-enforce formula
#
# Verifies that the source bead's current state is consistent with the
# recorded bd-decision verdict. All checks are mechanical/binary.
# Judgment-bearing corrections route to Mayor/the human adjudicator — never auto-fixed here.
#
# Exit codes:
#   0 — bead state and verdict are aligned; enforcement passes
#   1 — misaligned (state does not match verdict); BLOCK
#   2 — cannot determine alignment (bd error, missing data); fail closed
#
# Environment (set by gc from formula vars):
#   GC_VAR_SOURCE_BEAD       — bead ID of the adjudicated work item (required)
#   GC_VAR_BRIEF_SLUG        — brief slug for follow-up bead title checks
#   GC_VAR_EXPECTED_VERDICT  — expected verdict; empty = read from bd decision bead
#   GC_VAR_ARTIFACT_ROOT     — brief pipeline root, default .beads/briefs
#                              (rig-relative per assets/brief-pipeline/paths.toml)
#   GC_CITY_PATH             — city root (default <city-root>)

set -eu

SOURCE_BEAD="${GC_VAR_SOURCE_BEAD:-}"
BRIEF_SLUG="${GC_VAR_BRIEF_SLUG:-}"
EXPECTED_VERDICT="${GC_VAR_EXPECTED_VERDICT:-}"
ARTIFACT_ROOT="${GC_VAR_ARTIFACT_ROOT:-.beads/briefs}"
CITY="${GC_CITY_PATH:-${GC_CITY:-$HOME/gt}}"

fail_misaligned() {
  printf 'decision-alignment-check: MISALIGNED: %s\n' "$*" >&2
  exit 1
}

fail_closed() {
  printf 'decision-alignment-check: fail-closed: %s\n' "$*" >&2
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
# Resolve the recorded verdict
# ---------------------------------------------------------------------------
# If EXPECTED_VERDICT is set, that IS the expected verdict (and we verify
# the recorded one matches). If empty, read it from the bd type=decision
# bead — under the one-bead model (B2.2) that is the brief bead itself,
# carrying the verdict fields recorded at adjudication.

recorded_verdict=""

# Fetch the most-recent bd type=decision bead referencing SOURCE_BEAD
# (the brief bead under the one-bead model, or a standalone decision bead
# for non-brief authorizations).
decision_json="$(bd list --type decision --all --json 2>/dev/null)" || fail_closed "bd list --type decision failed"

recorded_verdict="$(printf '%s\n' "$decision_json" | \
  jq -r --arg id "$SOURCE_BEAD" \
    'map(select(
       (.metadata.source_bead // "") == $id or
       (.description // "" | test($id; ""))
     )) | sort_by(.created_at) | last | .metadata.decision // .metadata.verdict // ""' \
  2>/dev/null)" || recorded_verdict=""

# Fallback: read from brief-pipeline decision file when BRIEF_SLUG is set.
if [ -z "$recorded_verdict" ] && [ -n "$BRIEF_SLUG" ]; then
  for root in "$CITY"/*/"$ARTIFACT_ROOT"; do
    dec_file="$root/decisions/$BRIEF_SLUG.toml"
    if [ -f "$dec_file" ]; then
      recorded_verdict="$(grep '^decision[[:space:]]*=' "$dec_file" 2>/dev/null | \
        head -n1 | sed 's/.*=[[:space:]]*//' | tr -d '"')" || true
      break
    fi
  done
  if [ -z "$recorded_verdict" ] && [ -f "$ARTIFACT_ROOT/decisions/$BRIEF_SLUG.toml" ]; then
    recorded_verdict="$(grep '^decision[[:space:]]*=' "$ARTIFACT_ROOT/decisions/$BRIEF_SLUG.toml" 2>/dev/null | \
      head -n1 | sed 's/.*=[[:space:]]*//' | tr -d '"')" || true
  fi
fi

if [ -z "$recorded_verdict" ]; then
  fail_closed "no recorded verdict found for source_bead=$SOURCE_BEAD — run CHECK-A (decision-record-exists) first"
fi

# If EXPECTED_VERDICT is set, verify the recorded verdict matches.
if [ -n "$EXPECTED_VERDICT" ] && [ "$recorded_verdict" != "$EXPECTED_VERDICT" ]; then
  fail_misaligned "recorded verdict '$recorded_verdict' does not match expected '$EXPECTED_VERDICT' for bead $SOURCE_BEAD — supersede the decision record via mathcity.record-decision if the verdict changed"
fi

# Use recorded_verdict for alignment check.
verdict="$recorded_verdict"

# ---------------------------------------------------------------------------
# Fetch source bead state
# ---------------------------------------------------------------------------
bead_json="$(bd show "$SOURCE_BEAD" --json 2>/dev/null)" || fail_closed "bd show $SOURCE_BEAD failed"

count="$(printf '%s\n' "$bead_json" | jq 'if type == "array" then length else 0 end' 2>/dev/null)" || fail_closed "jq parse error on bead JSON"
[ "${count:-0}" -gt 0 ] || fail_closed "bead $SOURCE_BEAD not found"

bead_status="$(printf '%s\n' "$bead_json" | jq -r '.[0].status // empty' 2>/dev/null)" || bead_status=""
bead_assignee="$(printf '%s\n' "$bead_json" | jq -r '.[0].assignee // empty' 2>/dev/null)" || bead_assignee=""

# ---------------------------------------------------------------------------
# Alignment rules (mechanical; each verdict has a binary check)
# ---------------------------------------------------------------------------
case "$verdict" in
  approve)
    # After approval: source bead must be assigned to the owning rig's
    # merge-queue session — <rig>/<merge_target> per brief-decision-dispatch
    # (default gc.publisher; gastown cities may use gastown.refinery) —
    # OR status in_progress with an assignee matching that session.
    case "${bead_assignee:-}" in
      *publisher*|*refinery*)
        : # aligned
        ;;
      *)
        # Not yet assigned to the merge queue — misaligned if status is not
        # in a "heading to merge queue" transient state. open + unassigned
        # is bad.
        case "${bead_status:-}" in
          open|ready)
            fail_misaligned "verdict=approve but bead $SOURCE_BEAD is status='${bead_status}' assignee='${bead_assignee:-none}' — should be assigned to the rig merge-queue session (<rig>/gc.publisher, or gastown.refinery in gastown cities); route to Mayor/the human adjudicator to reconcile"
            ;;
          *)
            # in_progress or other transient — give benefit of the doubt only
            # if assignee matches the merge-queue session, else still misaligned.
            fail_misaligned "verdict=approve but bead $SOURCE_BEAD assignee='${bead_assignee:-none}' does not match the merge-queue session (/publisher/ or /refinery/) (status='${bead_status}') — route to Mayor/the human adjudicator"
            ;;
        esac
        ;;
    esac
    ;;

  reject)
    # After rejection: either a follow-up [rejected] bead exists, OR the
    # source bead is closed with reason containing "rejected".
    follow_up_found=false
    if [ -n "$BRIEF_SLUG" ]; then
      follow_json="$(bd list --json 2>/dev/null)" || follow_json=""
      if [ -n "$follow_json" ] && printf '%s\n' "$follow_json" | \
           jq -e --arg slug "$BRIEF_SLUG" \
             'map(select(.title | test("\\[rejected\\].*" + $slug; ""))) | length > 0' \
             >/dev/null 2>&1; then
        follow_up_found=true
      fi
    fi
    if [ "$follow_up_found" = "false" ]; then
      # Check if source bead is closed with rejected reason.
      bead_closed_reason="$(printf '%s\n' "$bead_json" | jq -r '.[0].closed_reason // .[0].close_reason // empty' 2>/dev/null)" || bead_closed_reason=""
      case "${bead_status:-},${bead_closed_reason:-}" in
        closed,*reject*|closed,*[Rr]ejected*)
          follow_up_found=true
          ;;
      esac
    fi
    if [ "$follow_up_found" = "false" ]; then
      fail_misaligned "verdict=reject but no [rejected] follow-up bead found for '$BRIEF_SLUG' and source bead $SOURCE_BEAD is not closed-as-rejected — route to Mayor/the human adjudicator"
    fi
    ;;

  revise)
    # After revise: either a [revise] follow-up bead exists, OR the source
    # bead is open (returned to author for revision).
    revise_follow_found=false
    if [ -n "$BRIEF_SLUG" ]; then
      follow_json="$(bd list --json 2>/dev/null)" || follow_json=""
      if [ -n "$follow_json" ] && printf '%s\n' "$follow_json" | \
           jq -e --arg slug "$BRIEF_SLUG" \
             'map(select(.title | test("\\[revise\\].*" + $slug; ""))) | length > 0' \
             >/dev/null 2>&1; then
        revise_follow_found=true
      fi
    fi
    if [ "$revise_follow_found" = "false" ]; then
      # Acceptable: source bead is open (returned for revision).
      case "${bead_status:-}" in
        open|ready)
          revise_follow_found=true
          ;;
      esac
    fi
    if [ "$revise_follow_found" = "false" ]; then
      fail_misaligned "verdict=revise but no [revise] follow-up bead found and source bead $SOURCE_BEAD is not open (status='${bead_status}') — route to Mayor/the human adjudicator"
    fi
    ;;

  defer)
    # After defer: source bead must be open (deferred = no-op; stays open).
    case "${bead_status:-}" in
      open|ready)
        : # aligned
        ;;
      *)
        fail_misaligned "verdict=defer but source bead $SOURCE_BEAD has status='${bead_status}' (expected open/ready) — route to Mayor/the human adjudicator"
        ;;
    esac
    ;;

  *)
    fail_closed "unknown verdict '$verdict' in decision record — cannot check alignment"
    ;;
esac

printf 'decision-alignment-check: PASS: bead %s status=%s assignee=%s aligned with verdict=%s\n' \
  "$SOURCE_BEAD" "${bead_status:-unknown}" "${bead_assignee:-none}" "$verdict" >&2
exit 0
