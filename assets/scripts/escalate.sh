#!/bin/sh
# escalate.sh — file an escalation bead and optionally ping the overseer.
#
# Usage:
#   escalate.sh --title <title> --body <body> --priority <0-4> [--rig <rig>]
#
# Priority semantics:
#   P0/P1  → bd create + bd label add human + gc mail send + osascript notification
#   P2–P4  → bd create + bd label add human (bead only, no immediate ping)
#
# No absolute paths are used; bd/gc/osascript must be on PATH.
# The --rig flag is forwarded to bd commands when provided.
set -eu

TITLE=""
BODY=""
PRIORITY=""
RIG=""

# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------

while [ $# -gt 0 ]; do
  case "$1" in
    --title)
      TITLE="$2"; shift 2 ;;
    --body)
      BODY="$2"; shift 2 ;;
    --priority)
      PRIORITY="$2"; shift 2 ;;
    --rig)
      RIG="$2"; shift 2 ;;
    *)
      echo "escalate: unknown argument: $1" >&2
      exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

die() {
  echo "escalate: $*" >&2
  exit 1
}

[ -n "$TITLE" ]    || die "--title is required"
[ -n "$PRIORITY" ] || die "--priority is required"

# Normalize: strip leading P/p so P0 and 0 both work
PNUM="$(printf '%s' "$PRIORITY" | sed 's/^[Pp]//')"
case "$PNUM" in
  0|1|2|3|4) ;;
  *) die "--priority must be 0-4 (got: $PRIORITY)" ;;
esac

# ---------------------------------------------------------------------------
# create escalation bead
# ---------------------------------------------------------------------------

bd_create() {
  if [ -n "$RIG" ]; then
    bd create --type=task --priority="$PNUM" --description "$BODY" "$TITLE" -C "$RIG" --json
  else
    bd create --type=task --priority="$PNUM" --description "$BODY" "$TITLE" --json
  fi
}

# Parse the bead id out of `bd create --json`. Prefer jq; fall back to a sed
# extraction of the "id" field so the script works without jq installed.
extract_id() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.id // empty' 2>/dev/null
  else
    sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1
  fi
}

BEAD_ID="$(bd_create | extract_id | tr -d '[:space:]')"
[ -n "$BEAD_ID" ] || die "bd create did not return an id"

# Flag the bead as needing human attention
if [ -n "$RIG" ]; then
  bd label add "$BEAD_ID" human -C "$RIG"
else
  bd label add "$BEAD_ID" human
fi

echo "escalate: created bead $BEAD_ID (P${PNUM})"

# ---------------------------------------------------------------------------
# P0/P1: immediate ping
# ---------------------------------------------------------------------------

if [ "$PNUM" -le 1 ]; then
  SUBJECT="[P${PNUM} ESCALATION] ${TITLE}"
  MAIL_BODY="Bead: ${BEAD_ID}

Priority: P${PNUM}

${BODY}"

  gc mail send human -s "$SUBJECT" -m "$MAIL_BODY"

  _SAFE_TITLE="$(printf '%s' "$TITLE"   | tr -d '"\\\n')"
  _SAFE_BEAD="$(printf '%s' "$BEAD_ID" | tr -d '"\\\n')"
  osascript -e "display notification \"${_SAFE_TITLE}\" with title \"[P${PNUM}] Escalation\" subtitle \"Bead: ${_SAFE_BEAD}\""

  echo "escalate: P${PNUM} ping sent (mail + notification)"
fi

exit 0
