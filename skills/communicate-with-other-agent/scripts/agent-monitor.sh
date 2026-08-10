#!/usr/bin/env bash
# agent-monitor.sh — V2: self-healing per-recipient inbox monitor
# Usage: agent-monitor.sh INBOX_FILE MY_UUID
#
# INBOX_FILE is the absolute path to the per-recipient file
# (<INBOX_DIR>/<MY_UUID>.md). Runs tail -F | awk filtering for messages with
# `to: MY_UUID` as a defence-in-depth check against misroutes. Restarts on
# pipeline exit with exponential backoff (30 s → 60 s → 120 s cap).
set -uo pipefail

INBOX="${1:-}"
MY_UUID="${2:-}"

UUID_RE='^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
[[ -n "$INBOX" ]]    || { echo "usage: agent-monitor.sh INBOX_FILE MY_UUID" >&2; exit 1; }
[[ -n "$MY_UUID" ]]  || { echo "usage: agent-monitor.sh INBOX_FILE MY_UUID" >&2; exit 1; }
[[ "$MY_UUID" =~ $UUID_RE ]] || { echo "bad UUID: $MY_UUID" >&2; exit 2; }

# Create inbox if missing so tail -F has something to watch.
[[ -f "$INBOX" ]] || { mkdir -p "$(dirname "$INBOX")"; touch "$INBOX"; }

INBOX_DIR="$(dirname "$INBOX")"

BACKOFF=30
ATTEMPT=0

while true; do
    ATTEMPT=$((ATTEMPT + 1))
    if [[ "$ATTEMPT" -gt 1 ]]; then
        echo "MONITOR_RESTART attempt=${ATTEMPT} backoff_was=${BACKOFF}s inbox=${INBOX}" >&2
    fi

    # Apply the hybrid trigger before each tail cycle.
    bash "$(dirname "$0")/agent-inbox-rotate.sh" "$INBOX_DIR" "$MY_UUID" >&2 || true

    set +o pipefail
    tail -F "$INBOX" | awk -v uuid="$MY_UUID" '
        $0 ~ ("^to:[[:space:]]+" uuid) { print; fflush() }
    '
    PIPE_EXIT=$?
    set -o pipefail

    echo "MONITOR_EXIT code=${PIPE_EXIT} retrying_in=${BACKOFF}s" >&2
    sleep "$BACKOFF"
    BACKOFF=$(( BACKOFF < 120 ? BACKOFF * 2 : 120 ))
done
