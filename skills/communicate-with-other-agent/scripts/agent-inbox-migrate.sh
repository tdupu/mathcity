#!/usr/bin/env bash
# agent-inbox-migrate.sh — one-shot V1 → V2 upgrade
# Usage: agent-inbox-migrate.sh PROJECT_DIR
#
# Splits PROJECT_DIR/.claude/.agent-inbox.md into per-recipient files
# under PROJECT_DIR/.claude/inbox/<recipient-uuid>.md, then renames the
# legacy inbox to .agent-inbox-migrated-<YYYY-MM-DD-HHMM>.md so the next
# `read` legacy-fallback no longer triggers.
#
# Idempotent: re-running on an already-migrated project is a no-op.
# Safe to invoke when no legacy inbox exists.
set -euo pipefail

PROJECT_DIR="${1:-}"
[[ -n "$PROJECT_DIR" ]] || { echo "usage: agent-inbox-migrate.sh PROJECT_DIR" >&2; exit 1; }
[[ -d "$PROJECT_DIR" ]] || { echo "PROJECT_DIR does not exist: $PROJECT_DIR" >&2; exit 1; }

LEGACY="$PROJECT_DIR/.claude/.agent-inbox.md"
INBOX_DIR="$PROJECT_DIR/.claude/inbox"

if [[ ! -f "$LEGACY" ]]; then
    echo "no legacy inbox at $LEGACY — nothing to migrate"
    exit 0
fi

if [[ ! -s "$LEGACY" ]]; then
    # Empty file — just rename to clear the auto-detect path.
    STAMP="$(date '+%Y-%m-%d-%H%M')"
    MIGRATED="$PROJECT_DIR/.claude/.agent-inbox-migrated-$STAMP.md"
    mv "$LEGACY" "$MIGRATED"
    echo "migrated empty legacy inbox → $MIGRATED"
    exit 0
fi

mkdir -p "$INBOX_DIR/archive"

# Walk the legacy file as a sequence of YAML-frontmatter entries.
# Each entry begins with `---`, then has `from:`/`to:`/`at:`/optional `subject:`,
# then another `---`, then body lines until the next `---` (or EOF).
#
# This awk emits each entry to <INBOX_DIR>/<to-uuid>.md, preserving format byte-for-byte
# (apart from a leading newline added so files concatenate cleanly).
awk -v dir="$INBOX_DIR" '
    BEGIN { entry=""; recipient="" }
    /^---$/ {
        if (in_header == 1) {
            in_header = 0
            entry = entry "---\n"
            next
        } else if (entry != "" && recipient != "") {
            # Closing --- of header? No, this is the next entry boundary OR end of body.
            # We treat any --- after the header as a body-only separator unless followed by from:.
            # Simpler approach: flush on any --- preceded by some prior body, then start new entry.
            target = dir "/" recipient ".md"
            printf("\n%s", entry) >> target
            close(target)
            entry = ""
            recipient = ""
            in_header = 1
            entry = entry "---\n"
            next
        } else {
            in_header = 1
            entry = entry "---\n"
            next
        }
    }
    {
        entry = entry $0 "\n"
        if (in_header == 1 && $1 == "to:") {
            recipient = $2
        }
    }
    END {
        if (entry != "" && recipient != "") {
            target = dir "/" recipient ".md"
            printf("\n%s", entry) >> target
            close(target)
        }
    }
' "$LEGACY"

# Report per-recipient counts.
echo "split per-recipient file counts:"
shopt -s nullglob
for f in "$INBOX_DIR"/*.md; do
    count=$(grep -c '^at:' "$f" 2>/dev/null || echo 0)
    echo "  $(basename "$f")  $count entries"
done

STAMP="$(date '+%Y-%m-%d-%H%M')"
MIGRATED="$PROJECT_DIR/.claude/.agent-inbox-migrated-$STAMP.md"
mv "$LEGACY" "$MIGRATED"
echo "legacy inbox renamed → $MIGRATED"
