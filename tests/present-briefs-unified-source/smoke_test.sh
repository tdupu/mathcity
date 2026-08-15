#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILL="$ROOT/skills/present-briefs/SKILL.md"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/present-briefs-unified-source.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

STACK_SELECTOR="$TMP/stack-selector.py"
LEGACY_SELECTOR="$TMP/legacy-selector.py"
awk '/^### Method 1 — stack index/{section=1; next} section && /python3 - "\$STACK_DIR" <<'"'"'PY'"'"'/{found=1; next} found && /^PY$/{exit} found {print}' "$SKILL" >"$STACK_SELECTOR"
awk '/^### Method 2 — decisions-track legacy fallback/{section=1; next} section && /python3 - "\$DECISIONS_DIR" <<'"'"'PY'"'"'/{found=1; next} found && /^PY$/{exit} found {print}' "$SKILL" >"$LEGACY_SELECTOR"
test -s "$STACK_SELECTOR"
test -s "$LEGACY_SELECTOR"

STACK="$TMP/stack"
DECISIONS="$TMP/decisions-track"
MARKER="$TMP/migration-marker.jsonl"
mkdir -p "$STACK" "$DECISIONS"
printf '%s\n' \
  "{\"slug\":\"future\",\"path\":\"$STACK/future.md\",\"unlock_count\":9,\"defer_until\":\"2999-01-01\"}" \
  "{\"slug\":\"ready\",\"path\":\"$STACK/ready.md\",\"unlock_count\":4}" >"$STACK/.index.jsonl"

stack_out="$(python3 "$STACK_SELECTOR" "$STACK")"
if grep -Fq "$STACK/future.md" <<<"$stack_out"; then
  echo "FAIL: future-deferred stack entry was printed" >&2
  exit 1
fi
grep -Fq "$STACK/ready.md" <<<"$stack_out"

printf '%s\n' '{"n":1,"slug":"legacy","status":"ready","unlock_count":3}' >"$DECISIONS/manifest.jsonl"
printf '# legacy\n' >"$DECISIONS/01-legacy-brief.md"
: >"$MARKER"

marker_out="$(STACK_INDEX="$STACK/.index.jsonl" MIGRATION_MARKER="$MARKER" INCLUDE_LEGACY_DECISIONS=0 python3 "$LEGACY_SELECTOR" "$DECISIONS")"
test -z "$marker_out"

flag_out="$(STACK_INDEX="$STACK/.index.jsonl" MIGRATION_MARKER="$MARKER" INCLUDE_LEGACY_DECISIONS=1 python3 "$LEGACY_SELECTOR" "$DECISIONS")"
grep -Fq "$DECISIONS/01-legacy-brief.md" <<<"$flag_out"

printf '%s\n' "{\"slug\":\"migrated\",\"path\":\"$STACK/migrated.md\",\"unlock_count\":3,\"legacy_source\":\"decisions-track/01-legacy-brief.md\"}" >>"$STACK/.index.jsonl"
duplicate_out="$(STACK_INDEX="$STACK/.index.jsonl" MIGRATION_MARKER="$MARKER" INCLUDE_LEGACY_DECISIONS=1 python3 "$LEGACY_SELECTOR" "$DECISIONS")"
test -z "$duplicate_out"

echo "PASS - present-briefs unified source selectors"
