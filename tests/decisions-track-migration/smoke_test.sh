#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/assets/scripts/brief-decisions-track-inventory.py"
PROOF5="$ROOT/tests/decisions-track-migration/proof5_no_nonterminal_unmapped.py"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/decisions-track-migration.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.beads/decisions-track" "$TMP/.beads/briefs/stack"

cat >"$TMP/.beads/decisions-track/manifest.jsonl" <<'JSONL'
{"n":1,"slug":"ready-one","status":"ready","unlock_count":4}
{"n":2,"slug":"deferred-one","status":"ready","defer_until":"2999-01-01","unlock_count":3}
{"n":3,"slug":"done-one","status":"adjudicated","unlock_count":2}
{"n":4,"slug":"missing-file","status":"ready","unlock_count":1}
{"n":5,"slug":"ready-near-miss","status":"ready-for-adjudication","unlock_count":8}
{"n":6,"slug":"needs-revision-free-text","status":"needs-revision(check-zero-ZFC-partial:V5-pipeline-membership-is-semantic;option-A=add-model-call-language)","unlock_count":4}
{"n":7,"slug":"on-hold-needs-revision","status":"on-hold-needs-revision","unlock_count":8}
{"n":8,"slug":"briefed-free-text","status":"briefed","unlock_count":4}
{"n":9,"slug":"brief-prep-dispatched","status":"brief-prep-dispatched","unlock_count":3}
{"n":10,"slug":"approved-slung","status":"approved-slung","unlock_count":3}
{"n":11,"slug":"terminal-free-text","status":"adjudicated:approve-b(move-cliff-part2;rehome-filed)","unlock_count":9}
{"n":12,"slug":"moot-terminal","status":"moot-stale","unlock_count":9}
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
cat >"$TMP/.beads/decisions-track/05-ready-near-miss-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Ready Near Miss
MD
cat >"$TMP/.beads/decisions-track/06-needs-revision-free-text-brief.md" <<'MD'
---
status: needs-revision
---
# Needs Revision Free Text
MD
cat >"$TMP/.beads/decisions-track/07-on-hold-needs-revision-brief.md" <<'MD'
---
status: on-hold-needs-revision
---
# On Hold Needs Revision
MD
cat >"$TMP/.beads/decisions-track/08-briefed-free-text-brief.md" <<'MD'
---
status: briefed
---
# Briefed Free Text
MD
cat >"$TMP/.beads/decisions-track/09-brief-prep-dispatched-brief.md" <<'MD'
---
status: brief-prep-dispatched
---
# Brief Prep Dispatched
MD
cat >"$TMP/.beads/decisions-track/10-approved-slung-brief.md" <<'MD'
---
status: approved-slung
---
# Approved Slung
MD
cat >"$TMP/.beads/decisions-track/11-terminal-free-text-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Terminal Free Text
MD
cat >"$TMP/.beads/decisions-track/12-moot-terminal-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Moot Terminal
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
for key in [
    (5,"ready-near-miss"),
    (6,"needs-revision-free-text"),
    (7,"on-hold-needs-revision"),
    (8,"briefed-free-text"),
    (9,"brief-prep-dispatched"),
    (10,"approved-slung"),
]:
    assert actions[key] == "copy_to_pile_review", (key, actions[key])
assert actions[(11,"terminal-free-text")] == "preserve_terminal"
assert actions[(12,"moot-terminal")] == "preserve_terminal"
assert actions[(99,"orphan")] == "preserve_file_without_manifest"
assert actions[(1,"wrong-slug")] == "preserve_file_without_manifest"
assert sum(r["kind"] == "malformed_manifest_row" for r in rows) == 4
print("decisions-track migration inventory: ok")
PY

python3 "$PROOF5" "$TMP/out.jsonl"

cat >"$TMP/bad-proof5.jsonl" <<'JSONL'
{"kind":"manifest_row","legacy_n":70,"legacy_slug":"sandbox-remaining-reject-moot-batch","legacy_file":"/tmp/70-sandbox-remaining-reject-moot-batch-brief.md","manifest_status":"on-hold-needs-revision","file_status":"ready-for-adjudication","defer_until":null,"unlock_count":8,"mapped_unified_path":null,"migration_action":"preserve_unknown_status","reason":"red-first fixture"}
JSONL
if python3 "$PROOF5" "$TMP/bad-proof5.jsonl"; then
  echo "expected proof 5 to fail on preserved non-terminal manifest row" >&2
  exit 1
fi

if python3 "$SCRIPT" inventory --rig-root "$TMP" --output "$TMP/missing-parent/out.jsonl"; then
  echo "expected missing output parent to fail" >&2
  exit 1
fi
