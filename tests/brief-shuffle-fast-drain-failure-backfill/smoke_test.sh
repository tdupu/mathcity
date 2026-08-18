#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DRAIN="$ROOT/assets/scripts/brief-shuffle-fast-drain.py"
BACKFILL="$ROOT/assets/scripts/brief-quality-failure-record.py"
GATES="$ROOT/assets/brief-pipeline/gates.toml"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/brief-shuffle-fast-drain-backfill.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

BRIEFS="$TMP/.beads/briefs"
PILE="$BRIEFS/.pile"
mkdir -p "$PILE"

python3 - "$GATES" "$PILE" <<'PY'
import sys
import tomllib
from pathlib import Path

with open(sys.argv[1], "rb") as handle:
    config = tomllib.load(handle)
pile = Path(sys.argv[2])
keys = {gate["id"]: gate["evidence_key"] for gate in config["gates"]}

def evidence(profile, failed_gate):
    lines = []
    for gate_id in config["profiles"][profile]["gates"]:
        key = keys[gate_id]
        if gate_id == failed_gate:
            status = "FAIL - controlled backfill fixture"
        elif gate_id == "G9":
            status = "PASS classifier_state=known_non_no_brainer reason=fixture classified_at=2026-08-16T00:00:00Z"
        else:
            status = "PASS"
        lines.append(f"{key}: {status}")
    return "\n".join(lines)

(pile / "producer-origin.md").write_text(f"""---
brief_slug: producer-origin
brief_kind: artifact
gate_profile: standard
source_bead: source-producer-origin
source_formula: simple-work-briefed
source_step: file-brief
producer_contract: brief-producer.v1
---

# Producer-origin brief

## Gate Evidence
{evidence("standard", "G4")}
""", encoding="utf-8")

(pile / "repair-origin.md").write_text(f"""---
brief_slug: repair-origin
brief_kind: producer_repair
gate_profile: producer_repair
source_bead: source-repair-origin
feedback_sink: brief_quality_failure
producer_contract: brief-producer-repair.v1
repair_source_formula: brief-producer-failure-rollup
repair_failed_gate: G5
repair_failure_fingerprint: controlled-fixture
replay_command: true
---

# Repair brief

## Gate Evidence
{evidence("producer_repair", "G5")}
""", encoding="utf-8")

collision = pile / "recovery-collision.md"
collision_text = (pile / "producer-origin.md").read_text()
collision_text = collision_text.replace("producer-origin", "recovery-collision")
collision_text = collision_text.replace("source-producer-origin", "source-recovery-collision")
collision_text = collision_text.replace("G4 Critical-review: FAIL - controlled backfill fixture", "G4 Critical-review: PASS")
collision.write_text(collision_text, encoding="utf-8")
staging = pile.parent / ".staging/fast-drain-recovery-collision"
staging.mkdir(parents=True)
(staging / "brief.md").write_text(collision_text, encoding="utf-8")
(staging / ".claimed_by").write_text(
    '{"owner":"brief-shuffle-fast-drain","source_path":".pile/recovery-collision.md"}\n',
    encoding="utf-8",
)
PY

report="$(python3 "$DRAIN" --brief-root "$BRIEFS" --gate-config "$GATES" --apply --json --no-external)"
python3 - "$report" <<'PY'
import json
import sys

report = json.loads(sys.argv[1])
assert report["rejected"] == ["producer-origin", "repair-origin"], report
assert report["promoted"] == ["recovery-collision"], report
assert report["recovered"] == ["recovery-collision"], report
PY

test -f "$BRIEFS/.pile/.rejected/producer-origin/rejection.json"
test -f "$BRIEFS/.pile/.rejected/repair-origin/rejection.json"

python3 "$BACKFILL" --brief-root "$BRIEFS" >/dev/null

QUALITY="$BRIEFS/.brief-quality-failure-pile/producer-origin.toml"
PRODUCER="$BRIEFS/.producer-failure-pile/producer-origin.toml"
test -f "$QUALITY"
test -f "$PRODUCER"
grep -Fq 'schema = "brief_quality_failure.v1"' "$QUALITY"
grep -Fq 'failed_gate = "G4"' "$QUALITY"
grep -Fq 'schema = "brief-producer-failure.v1"' "$PRODUCER"
grep -Fq 'source_bead = "source-producer-origin"' "$PRODUCER"
test ! -e "$BRIEFS/.brief-quality-failure-pile/repair-origin.toml"
test ! -e "$BRIEFS/.producer-failure-pile/repair-origin.toml"
test ! -e "$BRIEFS/.brief-quality-failure-pile/recovery-collision-recovery.toml"
test ! -e "$BRIEFS/.producer-failure-pile/recovery-collision-recovery.toml"

printf 'brief-shuffle-fast-drain failure backfill E2E: ok\n'
