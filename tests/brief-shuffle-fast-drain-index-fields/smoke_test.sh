#!/usr/bin/env bash
# mc-jdyr1: brief-shuffle-fast-drain invented an index field it never measured.
#
# THE DEFECT
# ----------
# Every row the drain promoted into stack/.index.jsonl carried a hardcoded
# "unlock_count": 0. The drain does not count unlocks and has no way to know the
# value, so the 0 was not a measurement — it was a fabrication that reads as one.
# A consumer cannot tell "this brief has never been unlocked" from "nobody
# looked", which is the same class of error as MBRF001 two lines above it: a
# field that looks like a fact about the brief but is an artifact of the writer.
#
# WHY A FAILS-BEFORE TEST AND NOT A GREP
# --------------------------------------
# Asserting the source no longer contains the literal would pass against a
# writer that moved the fabrication somewhere else. This drives the real drain
# end-to-end and inspects the row it actually wrote.
#
# HOW THIS TEST COULD FAIL (P6.2)
# -------------------------------
# It would be useless if the brief never promoted — an empty index trivially
# contains no unlock_count. So it asserts a row was written and that the fields
# the drain DOES measure are still present, before asserting the invented one is
# gone. A fix that broke promotion, or that stripped the row bare, fails here.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DRAIN="$ROOT/assets/scripts/brief-shuffle-fast-drain.py"
GATES="$ROOT/assets/brief-pipeline/gates.toml"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/brief-shuffle-index-fields.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

BEAD_FIXTURE="$TMP/beads.jsonl"
: >"$BEAD_FIXTURE"

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

lines = []
for gate_id in config["profiles"]["standard"]["gates"]:
    key = keys[gate_id]
    if gate_id == "G9":
        status = ("PASS classifier_state=known_non_no_brainer reason=fixture "
                  "classified_at=2026-08-16T00:00:00Z")
    else:
        status = "PASS"
    lines.append(f"{key}: {status}")
evidence = "\n".join(lines)

(pile / "index-fields.md").write_text(f"""---
brief_slug: index-fields
brief_kind: artifact
gate_profile: standard
source_bead: source-index-fields
source_formula: simple-work-briefed
source_step: file-brief
producer_contract: brief-producer.v1
---

# Index-fields brief

## Gate Evidence
{evidence}
""", encoding="utf-8")
PY

python3 "$DRAIN" --brief-root "$BRIEFS" --gate-config "$GATES" \
  --bead-fixture "$BEAD_FIXTURE" --apply --json --no-external >/dev/null

python3 - "$BRIEFS" <<'PY'
import json
import sys
from pathlib import Path

index = Path(sys.argv[1]) / "stack" / ".index.jsonl"
if not index.exists():
    raise SystemExit("FAIL: no stack index was written — the brief did not promote, "
                     "so this test proves nothing about invented fields")

rows = [json.loads(line) for line in index.read_text().splitlines() if line.strip()]
if not rows:
    raise SystemExit("FAIL: stack index is empty — nothing promoted")

row = next((r for r in rows if r.get("slug") == "index-fields"), None)
if row is None:
    raise SystemExit(f"FAIL: expected slug not in index; got {[r.get('slug') for r in rows]}")

# Control: the fields the drain genuinely measures must survive the fix.
for field in ("slug", "path", "source", "created_at"):
    if field not in row:
        raise SystemExit(f"FAIL: fix stripped a real field: {field} missing from {row}")

# THE REPRO: a value the drain never measured must not be invented.
if "unlock_count" in row:
    raise SystemExit(
        f"FAIL: unlock_count was invented into the index row (value "
        f"{row['unlock_count']!r}); the drain does not measure unlocks"
    )

print("PASS: index row carries only measured fields; no invented unlock_count")
PY
