#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORDER="$ROOT/orders/brief-shuffle-fast-drain.toml"
OLD_ORDER="$ROOT/orders/brief-shuffle-pile.toml"
FORMULA="$ROOT/formulas/brief-shuffle-fast-drain.toml"
SCRIPT="$ROOT/assets/scripts/brief-shuffle-fast-drain.py"
GATES="$ROOT/assets/brief-pipeline/gates.toml"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/brief-shuffle-fast-drain.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
# Canonical pile membership is the bead query (POLICY B2.4), so the drain
# needs a bead source. This fixture has no bd store, so it injects an empty
# one through the same seam mctl_core.beads.read_beads uses: no brief bead
# means UNRESOLVED, not closed, so these slugs still drain.
BEAD_FIXTURE="$TMP/beads.jsonl"
: >"$BEAD_FIXTURE"

test -f "$ORDER"
test -f "$FORMULA"
grep -Fq 'formula = "brief-shuffle-fast-drain"' "$ORDER"
grep -Fq 'brief-shuffle-fast-drain.py' "$FORMULA"
grep -Fq -- '--apply --json --no-external' "$FORMULA"
grep -Fq 'check = "false"' "$OLD_ORDER"
grep -Fq 'brief-shuffle-fast-drain' "$OLD_ORDER"

python3 - "$GATES" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as handle:
    config = tomllib.load(handle)
for profile in ("standard", "decision", "lost_bead_filter", "producer_repair", "no_brainer"):
    assert config["profiles"][profile]["gates"], profile
PY

BRIEFS="$TMP/.beads/briefs"
mkdir -p "$BRIEFS/.pile"
python3 - "$GATES" "$BRIEFS/.pile/controlled-fail.md" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as handle:
    config = tomllib.load(handle)
names = {gate["id"]: gate["evidence_key"] for gate in config["gates"]}
lines = []
for gate_id in config["profiles"]["standard"]["gates"]:
    key = names[gate_id]
    status = "FAIL - controlled smoke fixture" if gate_id == "G4" else "PASS"
    if gate_id == "G9":
        status += " classifier_state=known_non_no_brainer reason=smoke classified_at=2026-08-16T00:00:00Z"
    lines.append(f"{key}: {status}")
open(sys.argv[2], "w").write("---\nbrief_slug: controlled-fail\ngate_profile: standard\nsource_bead: smoke-source\n---\n\n## Gate Evidence\n" + "\n".join(lines) + "\n")
PY

report="$(python3 "$SCRIPT" --brief-root "$BRIEFS" --gate-config "$GATES" --bead-fixture "$BEAD_FIXTURE" --max-items 1 --apply --json --no-external)"
python3 - "$report" <<'PY'
import json
import sys

report = json.loads(sys.argv[1])
assert report["rejected"] == ["controlled-fail"]
assert "G4 Critical-review: FAIL" in report["reasons"]["controlled-fail"]
PY
test -f "$BRIEFS/.pile/.rejected/controlled-fail/brief.md"
test -f "$BRIEFS/.pile/.rejected/controlled-fail/rejection.json"

printf 'brief-shuffle-fast-drain smoke test: ok\n'
