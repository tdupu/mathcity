#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT/assets/scripts/brief-shuffle-fast-drain.py"
GATES="$ROOT/assets/brief-pipeline/gates.toml"
PRESENT="$ROOT/skills/present-briefs/SKILL.md"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/brief-shuffle-three-track-e2e.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

RIG="$TMP/rig"
BRIEFS="$RIG/.beads/briefs"
PILE="$BRIEFS/.pile"
STACK="$BRIEFS/stack"
mkdir -p "$PILE"

SELECTOR="$TMP/stack-selector.py"
awk '/^python3 - "\$STACK_DIR" <<'\''PY'\''$/{found=1; next} found && /^PY$/{exit} found {print}' "$PRESENT" >"$SELECTOR"
test -s "$SELECTOR"

python3 - "$GATES" "$PILE" <<'PY'
import sys
import tomllib
from pathlib import Path

gates_path = Path(sys.argv[1])
pile = Path(sys.argv[2])
with gates_path.open("rb") as handle:
    config = tomllib.load(handle)

gate_names = {gate["id"]: gate["evidence_key"] for gate in config["gates"]}
profiles = config["profiles"]

def evidence(profile):
    lines = []
    for gate_id in profiles[profile]["gates"]:
        key = gate_names[gate_id]
        if gate_id == "G9":
            lines.append(f"{key}: PASS classifier_state=known_non_no_brainer reason=task-2a-e2e classified_at=2026-08-16T00:00:00Z")
        else:
            lines.append(f"{key}: PASS")
    return "\n".join(lines)

fixtures = {
    "01-standard-artifact": ("standard", """---
brief_slug: 01-standard-artifact
gate_profile: standard
brief_kind: work
source_bead: task-2a-standard-source
source_formula: build-basic-briefed
provenance: source-local-task-2a-three-track-e2e
status: ready
---

# Standard artifact work brief

## Gate Evidence
{evidence}
"""),
    "02-decision-track": ("decision", """---
brief_slug: 02-decision-track
brief_kind: decision
gate_profile: decision
source_bead: task-2a-decision-source
legacy_source: decisions-track/02-decision-track-brief.md
feedback_sink: brief_quality_failure
status: ready
---

# Decision-shaped brief

action_block:
  on_approve: []
  on_reject: []
  on_defer: []

## Gate Evidence
{evidence}
"""),
    "03-producer-repair": ("producer_repair", """---
brief_slug: 03-producer-repair
brief_kind: producer_repair
gate_profile: producer_repair
source_bead: task-2a-producer-source
feedback_sink: brief_quality_failure
producer_contract: brief-producer-repair.v1
repair_source_formula: brief-producer-failure-rollup
repair_failed_gate: G9
repair_failure_fingerprint: task-2a-synthetic-producer-failure
replay_command: bash tests/brief-shuffle-fast-drain-three-track-e2e/smoke_test.sh
status: ready
---

# Producer repair brief

## Gate Evidence
{evidence}
"""),
}

for slug, (profile, template) in fixtures.items():
    (pile / f"{slug}.md").write_text(template.format(evidence=evidence(profile)), encoding="utf-8")
PY

report="$(python3 "$SCRIPT" --brief-root "$BRIEFS" --gate-config "$GATES" --apply --json --no-external)"
python3 - "$report" <<'PY'
import json
import sys

report = json.loads(sys.argv[1])
expected = ["01-standard-artifact", "02-decision-track", "03-producer-repair"]
assert report["promoted"] == expected, report
assert report["rejected"] == [], report
assert report["skipped"] == [], report
assert report["remaining_pile"] == 0, report
PY

for slug in 01-standard-artifact 02-decision-track 03-producer-repair; do
  test ! -e "$PILE/$slug.md"
  test -f "$STACK/$slug.md"
done

python3 - "$STACK/.index.jsonl" <<'PY'
import json
import sys

expected = ["01-standard-artifact", "02-decision-track", "03-producer-repair"]
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
assert [row["slug"] for row in rows] == expected, rows
assert [row["path"] for row in rows] == [f"stack/{slug}.md" for slug in expected], rows
PY

selector_output="$(cd "$RIG" && python3 "$SELECTOR" "$STACK")"
for slug in 01-standard-artifact 02-decision-track 03-producer-repair; do
  grep -Fq "stack/$slug.md" <<<"$selector_output"
done

printf 'brief-shuffle-fast-drain three-track E2E: ok\n'
