#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/assets/scripts/brief-stack-index.py"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/brief-stack-index-reconcile.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

BRIEFS="$TMP/.beads/briefs"
STACK="$BRIEFS/stack"
ARCHIVE="$BRIEFS/.adjudicated-archive"
mkdir -p "$STACK" "$ARCHIVE"

cat >"$STACK/live.md" <<'MD'
# Live Brief
MD
cat >"$ARCHIVE/decided.md" <<'MD'
# Decided Brief
MD
cat >"$STACK/.index.jsonl" <<JSONL
{"slug":"live","path":"$STACK/live.md","unlock_count":3,"gate_profile":"standard"}
{"slug":"decided","path":"$STACK/decided.md","unlock_count":9,"gate_profile":"decision"}
{"slug":"already-marked","path":"$STACK/already-marked.md","unlock_count":1,"status":"archived"}
not json
JSONL

dry_run="$(python3 "$SCRIPT" reconcile-archive --brief-root "$BRIEFS")"
grep -Fq '"apply": false' <<<"$dry_run"
grep -Fq '"slug": "decided"' <<<"$dry_run"
if grep -Fq '"slug": "live"' <<<"$dry_run"; then
  echo "dry-run proposed removing a live stack row" >&2
  exit 1
fi
grep -Fq '"slug":"decided"' "$STACK/.index.jsonl" || {
  echo "dry-run modified the index" >&2
  exit 1
}

python3 "$SCRIPT" reconcile-archive --brief-root "$BRIEFS" --apply >/tmp/brief-stack-index-apply.out
if grep -Fq '"slug":"decided"' "$STACK/.index.jsonl"; then
  echo "apply left archived zombie row in the index" >&2
  exit 1
fi
grep -Fq '"slug":"live"' "$STACK/.index.jsonl"
grep -Fq 'not json' "$STACK/.index.jsonl"

cat >>"$STACK/.index.jsonl" <<JSONL
{"slug":"one-off","path":"$STACK/one-off.md","unlock_count":5}
JSONL
mkdir -p "$BRIEFS/archive/one-off"
cat >"$BRIEFS/archive/one-off/brief.md" <<'MD'
# One Off
MD

one_off="$(python3 "$SCRIPT" remove-archived-row --brief-root "$BRIEFS" --slug one-off)"
grep -Fq '"apply": false' <<<"$one_off"
grep -Fq '"slug": "one-off"' <<<"$one_off"
grep -Fq '"slug":"one-off"' "$STACK/.index.jsonl" || {
  echo "remove-archived-row dry-run modified the index" >&2
  exit 1
}

python3 "$SCRIPT" remove-archived-row --brief-root "$BRIEFS" --slug one-off --apply >/tmp/brief-stack-index-remove.out
if grep -Fq '"slug":"one-off"' "$STACK/.index.jsonl"; then
  echo "remove-archived-row apply left archived row in the index" >&2
  exit 1
fi

echo "brief stack index reconcile: ok"
