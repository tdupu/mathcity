#!/bin/sh
# stale-claim-check.sh — mechanical stale-claim gate
#
# Exit codes:
#   0 — claim is fresh; work may proceed
#   1 — claim is stale (lease expired, heartbeat silent, or bd stale listed)
#   2 — bead not found or bd unavailable; fail closed
#
# Environment:
#   GC_BEAD_ID              — bead to check (required if $1 not supplied)
#   STALE_CLAIM_WINDOW_SECONDS — heartbeat silence threshold (default: 3600)
#
# Usage:
#   stale-claim-check.sh [bead-id]

set -eu

BEAD_ID="${1:-${GC_BEAD_ID:-}}"
WINDOW="${STALE_CLAIM_WINDOW_SECONDS:-3600}"

fail_stale() {
  printf 'stale-claim: %s\n' "$*" >&2
  exit 1
}

fail_closed() {
  printf 'stale-claim: fail-closed: %s\n' "$*" >&2
  exit 2
}

if [ -z "$BEAD_ID" ]; then
  fail_closed "no bead id: set GC_BEAD_ID or pass bead-id as first argument"
fi

if ! command -v bd >/dev/null 2>&1; then
  fail_closed "bd not found in PATH"
fi

if ! command -v jq >/dev/null 2>&1; then
  fail_closed "jq not found in PATH"
fi

# Fetch bead JSON. bd show exits nonzero if the bead is not found.
bead_json="$(bd show "$BEAD_ID" --json 2>/dev/null)" || fail_closed "bd show $BEAD_ID failed"

# Validate we got a non-empty JSON array with at least one entry.
count="$(printf '%s\n' "$bead_json" | jq 'if type == "array" then length else 0 end' 2>/dev/null)" || fail_closed "jq parse error"
[ "${count:-0}" -gt 0 ] || fail_closed "bead $BEAD_ID not found (empty result)"

# Extract relevant timestamp fields (empty string if null/absent).
lease_expires="$(printf '%s\n' "$bead_json" | jq -r '.[0].lease_expires_at // empty' 2>/dev/null)" || true
heartbeat="$(printf '%s\n' "$bead_json" | jq -r '.[0].heartbeat_at // empty' 2>/dev/null)" || true
status="$(printf '%s\n' "$bead_json" | jq -r '.[0].status // empty' 2>/dev/null)" || true

# If the bead is not in-progress/claimed, there is nothing to check.
case "${status:-}" in
  in_progress|claimed|active)
    : # fall through to staleness checks
    ;;
  *)
    # Not a claimed bead; gate does not apply (no claim = not stale).
    printf 'stale-claim: status=%s — no active claim; gate N/A (pass)\n' "${status:-unknown}" >&2
    exit 0
    ;;
esac

# Helper: parse an ISO-8601/RFC-3339 timestamp to a Unix epoch integer.
# Uses date(1); macOS date requires -j -f; GNU date accepts -d.
to_epoch() {
  ts="$1"
  [ -n "$ts" ] || return 1
  # Try GNU date first, then macOS date.
  if date --version >/dev/null 2>&1; then
    date -d "$ts" +%s 2>/dev/null
  else
    date -j -f '%Y-%m-%dT%H:%M:%S' "${ts%%.*}" +%s 2>/dev/null ||
    date -j -f '%Y-%m-%dT%H:%M:%SZ' "${ts%%\.*}Z" +%s 2>/dev/null ||
    return 1
  fi
}

now="$(date +%s)"

# Check 1: lease expiry.
if [ -n "$lease_expires" ]; then
  lease_epoch="$(to_epoch "$lease_expires")" || true
  if [ -n "$lease_epoch" ] && [ "$now" -gt "$lease_epoch" ]; then
    fail_stale "lease expired at $lease_expires (now=$now, lease=$lease_epoch)"
  fi
fi

# Check 2: heartbeat silence.
if [ -n "$heartbeat" ]; then
  hb_epoch="$(to_epoch "$heartbeat")" || true
  if [ -n "$hb_epoch" ]; then
    silence=$(( now - hb_epoch ))
    if [ "$silence" -gt "$WINDOW" ]; then
      fail_stale "heartbeat silent for ${silence}s (threshold=${WINDOW}s, last=$heartbeat)"
    fi
  fi
else
  # No heartbeat recorded on a claimed bead — treat as stale.
  fail_stale "no heartbeat recorded on claimed bead $BEAD_ID (fail closed)"
fi

# Check 3: bd stale listing.
# bd stale --days 0 would include everything; use a 1-day floor to avoid
# false positives on freshly-claimed beads with no heartbeat-age data.
stale_window_days=$(( (WINDOW / 86400) + 1 ))
stale_window_days=$(( stale_window_days < 1 ? 1 : stale_window_days ))

if bd stale --status in_progress --days "$stale_window_days" --json 2>/dev/null |
     jq -e --arg id "$BEAD_ID" 'map(.id) | index($id) != null' >/dev/null 2>&1; then
  fail_stale "bead $BEAD_ID appears in bd stale --status in_progress --days $stale_window_days"
fi

printf 'stale-claim: bead %s claim is fresh (lease ok, heartbeat recent, not in bd stale)\n' "$BEAD_ID" >&2
exit 0
