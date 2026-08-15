#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/assets/scripts/brief-decisions-track-inventory.py"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/decisions-track-migration.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.beads/decisions-track" "$TMP/.beads/briefs/stack"

cat >"$TMP/.beads/decisions-track/manifest.jsonl" <<'JSONL'
{"n":1,"slug":"ready-one","status":"ready","unlock_count":4}
{"n":2,"slug":"deferred-one","status":"ready","defer_until":"2999-01-01","unlock_count":3}
{"n":3,"slug":"done-one","status":"adjudicated","unlock_count":2}
{"n":4,"slug":"missing-file","status":"ready","unlock_count":1}
{bad json
["not", "an", "object"]
{"slug":"missing-number","status":"ready"}
{"n":"not-an-integer","slug":"bad-number","status":"ready"}
JSONL

cat >"$TMP/.beads/decisions-track/01-ready-one-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Ready
MD
cat >"$TMP/.beads/decisions-track/02-deferred-one-brief.md" <<'MD'
---
status: ready-for-adjudication
defer_until: 2999-01-01
---
# Deferred
MD
cat >"$TMP/.beads/decisions-track/03-done-one-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Done
MD
cat >"$TMP/.beads/decisions-track/99-orphan-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Orphan
MD
cat >"$TMP/.beads/decisions-track/01-wrong-slug-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Wrong slug
MD

python3 "$SCRIPT" inventory --rig-root "$TMP" --output "$TMP/out.jsonl"
python3 - "$TMP/out.jsonl" <<'PY'
import json, sys
rows=[json.loads(line) for line in open(sys.argv[1]) if line.strip()]
required={"kind","legacy_n","legacy_slug","legacy_file","manifest_status","file_status","defer_until","unlock_count","mapped_unified_path","migration_action","reason"}
assert all(required <= set(row) for row in rows)
actions={(r.get("legacy_n"), r.get("legacy_slug")): r["migration_action"] for r in rows if r["kind"] != "malformed_manifest_row"}
assert actions[(1,"ready-one")] == "copy_to_pile"
assert actions[(2,"deferred-one")] == "copy_to_pile_deferred"
assert actions[(3,"done-one")] == "preserve_terminal"
assert actions[(4,"missing-file")] == "preserve_missing_file"
assert actions[(99,"orphan")] == "preserve_file_without_manifest"
assert actions[(1,"wrong-slug")] == "preserve_file_without_manifest"
assert sum(r["kind"] == "malformed_manifest_row" for r in rows) == 4
print("decisions-track migration inventory: ok")
PY

if python3 "$SCRIPT" inventory --rig-root "$TMP" --output "$TMP/missing-parent/out.jsonl"; then
  echo "expected missing output parent to fail" >&2
  exit 1
fi
