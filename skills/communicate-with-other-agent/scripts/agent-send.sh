#!/usr/bin/env bash
# agent-send.sh — V2 (username-layout): <username>/<date>/<timestamp> canonical
# Usage: agent-send.sh FROM TO SUBJECT BODY_FILE [INBOX_DIR_OVERRIDE]
#
# Canonical write (the human adjudicator ruling 2026-07-22):
#   <INBOX_DIR>/<to-name>/<YYYY-MM-DD>/<HH-MM-SS>-from-<from-name>-<subject-slug>.md
#   - to-name / from-name resolved via a UUID->role-name map (fallback: 8-char
#     uuid prefix, so routing NEVER fails on an unmapped agent).
#   - ONE FILE PER MESSAGE, timestamped leaf, local time.
# Backward-compat write:
#   <INBOX_DIR>/<TO>.md  (flat, APPENDED) — existing per-recipient monitors keep
#   firing through the cutover. The `to:` line still carries the raw UUID, so
#   `grep '^to:.*<UUID>'` monitors are unaffected.
#
# Inbox-dir resolution precedence (highest wins):
#   1. INBOX_DIR_OVERRIDE positional arg (5th) — explicit caller-supplied path
#   2. $CLAUDE_INBOX_DIR environment variable
#   3. CWD walk-up looking for .claude/inbox/ (V2) or .claude/.agent-inbox.md (V1)
#   4. Fallback: $(pwd)/.claude/inbox/
#
# UUID->name map: optional external file at
#   <INBOX_DIR>/.agent-names.map  (lines: "<uuid> <name>").
# Keep local human names and UUIDs in that untracked file, not in this script.
#
# The 5th positional arg is OPTIONAL — backward-compatible with 4-arg callers.
set -euo pipefail

FROM="$1"; TO="$2"; SUBJECT="$3"; BODY_FILE="$4"
INBOX_DIR_OVERRIDE="${5:-}"

UUID_RE='^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
[[ "$FROM" =~ $UUID_RE ]] || { echo "bad FROM uuid: $FROM" >&2; exit 2; }
[[ "$TO"   =~ $UUID_RE ]] || { echo "bad TO uuid: $TO" >&2; exit 2; }
[[ -f "$BODY_FILE" ]] || { echo "body file missing: $BODY_FILE" >&2; exit 2; }

# --- Inbox directory resolution ---
INBOX_DIR=""
if [[ -n "$INBOX_DIR_OVERRIDE" ]]; then
    INBOX_DIR="$INBOX_DIR_OVERRIDE"
    mkdir -p "$INBOX_DIR"
else
    INBOX_DIR="${CLAUDE_INBOX_DIR:-}"
fi
if [[ -z "$INBOX_DIR" ]]; then
    dir="$(pwd)"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.claude/inbox" ]]; then
            INBOX_DIR="$dir/.claude/inbox"; break
        fi
        if [[ -f "$dir/.claude/.agent-inbox.md" ]]; then
            INBOX_DIR="$dir/.claude/inbox"; mkdir -p "$INBOX_DIR"
            echo "LEGACY_INBOX_DETECTED: $dir/.claude/.agent-inbox.md" >&2
            break
        fi
        dir="$(dirname "$dir")"
    done
fi
if [[ -z "$INBOX_DIR" ]]; then
    INBOX_DIR="$(pwd)/.claude/inbox"; mkdir -p "$INBOX_DIR"
fi

# --- UUID -> human-readable role name ---
# bash 3.2 compatible (macOS default has no `declare -A`): optional external
# <INBOX_DIR>/.agent-names.map (lines "<uuid> <name>") + prefix fallback.
NAMES_FILE="$INBOX_DIR/.agent-names.map"
resolve_name() {
    local uuid="$1" name=""
    if [[ -z "$name" && -f "$NAMES_FILE" ]]; then
        name="$(awk -v u="$uuid" '$1==u {print $2; exit}' "$NAMES_FILE")"
    fi
    [[ -z "$name" ]] && name="${uuid:0:8}"
    printf '%s' "$name"
}
TO_NAME="$(resolve_name "$TO")"
FROM_NAME="$(resolve_name "$FROM")"

# --- Subject slug (filesystem-safe) ---
slug="$(printf '%s' "$SUBJECT" | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-40)"
[[ -z "$slug" ]] && slug="msg"

# --- Canonical path: <to-name>/<date>/<HH-MM-SS>-from-<from-name>-<slug>.md ---
TODAY="$(date '+%Y-%m-%d')"
HMS="$(date '+%H-%M-%S')"
CANON_DIR="$INBOX_DIR/$TO_NAME/$TODAY"
mkdir -p "$CANON_DIR"
CANON_FILE="$CANON_DIR/${HMS}-from-${FROM_NAME}-${slug}.md"
n=1; while [[ -e "$CANON_FILE" ]]; do
    CANON_FILE="$CANON_DIR/${HMS}-from-${FROM_NAME}-${slug}-${n}.md"; n=$((n+1))
done

# --- Flat backward-compat path (appended; no rotation — V2 uses per-message files) ---
FLAT_INBOX="$INBOX_DIR/$TO.md"
[[ -f "$FLAT_INBOX" ]] || touch "$FLAT_INBOX"

TS="$(date '+%Y-%m-%d %H:%M:%S %z')"
MSG="$(printf '\n---\nfrom: %s (%s)\nto:   %s (%s)\nat:   %s\nsubject: %s\n---\n' \
       "$FROM" "$FROM_NAME" "$TO" "$TO_NAME" "$TS" "$SUBJECT")"

# Canonical: one file per message. Flat: appended for legacy monitors.
{ printf '%s' "$MSG"; cat "$BODY_FILE"; printf '\n'; } > "$CANON_FILE"
{ printf '%s' "$MSG"; cat "$BODY_FILE"; printf '\n'; } >> "$FLAT_INBOX"

echo "sent at $TS to $CANON_FILE (flat: $FLAT_INBOX)"
