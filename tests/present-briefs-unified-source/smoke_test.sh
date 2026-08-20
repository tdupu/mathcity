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
cat >"$STACK/native-adjudicated.md" <<'EOF'
---
status: adjudicated
---

# already handled
EOF
cat >"$STACK/native-ready.md" <<'EOF'
---
status: ready
---

# still ready
EOF
cat >"$STACK/native-approved.md" <<'EOF'
---
status: approved
---

# approved by brief-prep and still presentable
EOF
cat >"$STACK/native-revise.md" <<'EOF'
---
status: revise
---

# already sent back
EOF
# Rows whose filtering signal lives in the INDEX ROW, not in frontmatter. Each
# file is created with no frontmatter block, so frontmatter_status() returns ""
# and the row field stays the only thing that can filter the entry -- every
# assertion below keeps exactly the discriminating power it had.
#
# The files must exist at all because frontmatter_status() now fails CLOSED on
# an unreadable brief (B4). Before that fix an index row could point at nothing
# and still be presented, which is how adjudicated work got re-presented; these
# rows were relying on that. Creating the fixture files is the repair -- the
# assertions are unchanged.
for missing in future ready legacy-adjudicated legacy-approved brief-prep-dispatched migrated; do
  printf '# %s\n' "$missing" >"$STACK/$missing.md"
done
printf '%s\n' \
  "{\"slug\":\"future\",\"path\":\"$STACK/future.md\",\"unlock_count\":9,\"defer_until\":\"2999-01-01\"}" \
  "{\"slug\":\"ready\",\"path\":\"$STACK/ready.md\",\"unlock_count\":4}" \
  "{\"slug\":\"legacy-adjudicated\",\"path\":\"$STACK/legacy-adjudicated.md\",\"unlock_count\":8,\"manifest_status\":\"adjudicated\"}" \
  "{\"slug\":\"legacy-approved\",\"path\":\"$STACK/legacy-approved.md\",\"unlock_count\":8,\"manifest_status\":\"approved\"}" \
  "{\"slug\":\"brief-prep-dispatched\",\"path\":\"$STACK/brief-prep-dispatched.md\",\"unlock_count\":8,\"manifest_status\":\"brief-prep-dispatched\"}" \
  "{\"slug\":\"native-adjudicated\",\"path\":\"$STACK/native-adjudicated.md\",\"unlock_count\":7}" \
  "{\"slug\":\"native-ready\",\"path\":\"$STACK/native-ready.md\",\"unlock_count\":6}" \
  "{\"slug\":\"native-approved\",\"path\":\"$STACK/native-approved.md\",\"unlock_count\":5}" \
  "{\"slug\":\"native-revise\",\"path\":\"$STACK/native-revise.md\",\"unlock_count\":4}" >"$STACK/.index.jsonl"

stack_out="$(python3 "$STACK_SELECTOR" "$STACK")"
if grep -Fq "$STACK/future.md" <<<"$stack_out"; then
  echo "FAIL: future-deferred stack entry was printed" >&2
  exit 1
fi
if grep -Fq "$STACK/legacy-adjudicated.md" <<<"$stack_out"; then
  echo "FAIL: adjudicated manifest_status stack entry was printed" >&2
  exit 1
fi
if grep -Fq "$STACK/legacy-approved.md" <<<"$stack_out"; then
  echo "FAIL: terminal legacy approved stack entry was printed" >&2
  exit 1
fi
if grep -Fq "$STACK/brief-prep-dispatched.md" <<<"$stack_out"; then
  echo "FAIL: brief-prep-dispatched stack entry was printed" >&2
  exit 1
fi
grep -Fq 'must write `status: ready`' "$SKILL"
grep -Fq 'not use `briefed` or `present-it-pending` to mean "ready for presentation"' "$SKILL"
if grep -Fq "$STACK/native-adjudicated.md" <<<"$stack_out"; then
  echo "FAIL: adjudicated native stack entry was printed" >&2
  exit 1
fi
if grep -Fq "$STACK/native-revise.md" <<<"$stack_out"; then
  echo "FAIL: revise native stack entry was printed" >&2
  exit 1
fi
grep -Fq "$STACK/ready.md" <<<"$stack_out"
grep -Fq "$STACK/native-ready.md" <<<"$stack_out"
grep -Fq "$STACK/native-approved.md" <<<"$stack_out"

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
