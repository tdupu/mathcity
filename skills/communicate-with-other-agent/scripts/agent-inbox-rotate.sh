#!/usr/bin/env bash
# agent-inbox-rotate.sh — V2: hybrid trigger (4h elapsed OR ≥30 entries OR prior calendar day)
# Usage: agent-inbox-rotate.sh INBOX_DIR [RECIPIENT_UUID]
#
# With RECIPIENT_UUID: check that one per-recipient file and rotate if a trigger fires.
# Without: sweep every <INBOX_DIR>/<uuid>.md.
# Exit 0 always. Prints "INBOX_ROTATED: <archive_path>" per rotation.
set -uo pipefail

INBOX_DIR="${1:-}"
RECIPIENT="${2:-}"
[[ -n "$INBOX_DIR" ]] || { echo "usage: agent-inbox-rotate.sh INBOX_DIR [RECIPIENT_UUID]" >&2; exit 1; }
[[ -d "$INBOX_DIR" ]] || exit 0   # no inbox dir yet — nothing to rotate

mkdir -p "$INBOX_DIR/archive"

# Hybrid trigger thresholds. Documented in SKILL.md "rotate" section.
MAX_AGE_SECONDS=$((4 * 3600))    # 4 hours since file's first entry
MAX_ENTRIES=30                   # entries per file before rotation
TODAY=$(date '+%Y-%m-%d')

rotate_one() {
    local inbox="$1"
    local uuid="$2"
    [[ -f "$inbox" ]] || return 0
    [[ -s "$inbox" ]] || return 0  # empty file — nothing to rotate

    # Trigger 1 — calendar-day change (legacy V1 trigger, kept as safety net).
    local last_date
    last_date=$(grep '^at:' "$inbox" | tail -1 | awk '{print $2}')
    local day_trigger=0
    if [[ -n "$last_date" && "$last_date" != "$TODAY" ]]; then
        day_trigger=1
    fi

    # Trigger 2 — entry count (V2).
    local entries
    entries=$(grep -c '^at:' "$inbox" 2>/dev/null || echo 0)
    local count_trigger=0
    if [[ "$entries" -ge "$MAX_ENTRIES" ]]; then
        count_trigger=1
    fi

    # Trigger 3 — wall-clock age since first entry (V2).
    # Reads the first `at:` line, parses its timestamp, compares to now.
    local first_at first_epoch now_epoch age_trigger=0
    first_at=$(grep '^at:' "$inbox" | head -1 | sed 's/^at:[[:space:]]*//')
    if [[ -n "$first_at" ]]; then
        # `date -j -f` is BSD/macOS; `date -d` is GNU. Try both.
        first_epoch=$(date -j -f '%Y-%m-%d %H:%M:%S %z' "$first_at" '+%s' 2>/dev/null \
                    || date -d "$first_at" '+%s' 2>/dev/null \
                    || echo "")
        now_epoch=$(date '+%s')
        if [[ -n "$first_epoch" ]]; then
            if (( now_epoch - first_epoch >= MAX_AGE_SECONDS )); then
                age_trigger=1
            fi
        fi
    fi

    if (( day_trigger + count_trigger + age_trigger == 0 )); then
        return 0
    fi

    local archive="$INBOX_DIR/archive/${uuid}-$(date '+%Y-%m-%d-%H%M').md"
    # mv is atomic; if a concurrent process already rotated, mv fails silently.
    if mv "$inbox" "$archive" 2>/dev/null; then
        touch "$inbox"
        local reason=""
        [[ "$age_trigger"   = 1 ]] && reason+="age "
        [[ "$count_trigger" = 1 ]] && reason+="count "
        [[ "$day_trigger"   = 1 ]] && reason+="day "
        echo "INBOX_ROTATED: $archive (trigger=${reason% })"
    fi
}

if [[ -n "$RECIPIENT" ]]; then
    rotate_one "$INBOX_DIR/$RECIPIENT.md" "$RECIPIENT"
else
    # Sweep mode — rotate every per-recipient file in the dir.
    shopt -s nullglob
    for f in "$INBOX_DIR"/*.md; do
        # Skip files inside archive/ (the for-loop won't recurse, but be explicit).
        base=$(basename "$f" .md)
        rotate_one "$f" "$base"
    done
fi
