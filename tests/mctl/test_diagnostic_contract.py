"""The Diagnostic payload must match plan §2's typed shape.

Plan §2 specifies Diagnostic fields: policy_ref, provenance_ref,
suggested_next_command, bead_id, brief_slug, data_location, city_path,
rig_name, rig_path. The implementation collapsed all of them into an untyped
`facts: Mapping[str, str]`, so every MCP tool and dashboard consumer would
have to string-dig into `facts` — and would break whenever a fact key was
renamed. Slice 6 freezes this shape into MCP schemas, so it has to be right
before then.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

ORPHAN_BRIEF = "mc-orphan"

# Plan §2 Diagnostic fields that carry context beyond severity/code/message.
TYPED_CONTEXT_FIELDS = (
    "city_path",
    "rig_name",
    "rig_path",
    "brief_slug",
    "data_location",
    "policy_ref",
    "provenance_ref",
)


def runtime(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    # A decision bead with no source dependency triggers MBRF004, which the
    # plan's invariant table ties to policy B2.1.
    (beads / "issues.jsonl").write_text(
        json.dumps(
            {
                "id": ORPHAN_BRIEF,
                "title": "Brief with no source",
                "status": "open",
                "issue_type": "decision",
                "labels": [],
                "created_at": "2026-08-10T12:00:00Z",
                "updated_at": "2026-08-11T12:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return city_root, rig_root


def run_mctl(*args: str, beads_fixture: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(beads_fixture)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def mbrf004(city_root: Path, rig_root: Path) -> dict[str, object]:
    result = run_mctl(
        "briefs", "doctor", "--city", str(city_root), "--rig", "mathcity", "--json",
        beads_fixture=rig_root / ".beads" / "issues.jsonl",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    for entry in payload["brief_diagnostics"]:
        for diagnostic in entry["diagnostics"]:
            if diagnostic["code"] == "MBRF004":
                return diagnostic
    raise AssertionError(f"MBRF004 not emitted: {result.stdout}")


def test_diagnostic_exposes_plan_typed_fields_at_top_level(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    diagnostic = mbrf004(city_root, rig_root)

    missing = [field for field in TYPED_CONTEXT_FIELDS if field not in diagnostic]
    assert not missing, (
        f"Diagnostic is missing plan §2 typed fields {missing}; consumers would "
        f"have to string-dig into facts. Payload: {sorted(diagnostic)}"
    )


def test_typed_fields_carry_the_right_values(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    diagnostic = mbrf004(city_root, rig_root)

    assert diagnostic["policy_ref"] == "B2.1"
    assert diagnostic["brief_slug"] == ORPHAN_BRIEF
    assert diagnostic["rig_name"] == "mathcity"
    assert diagnostic["rig_path"] == str(rig_root)
    assert diagnostic["city_path"] == str(city_root)
    assert diagnostic["provenance_ref"]
    assert diagnostic["data_location"]


def test_facts_stays_populated_for_existing_consumers(tmp_path: Path):
    """Typed fields are added alongside facts, not swapped for it."""
    city_root, rig_root = runtime(tmp_path)

    diagnostic = mbrf004(city_root, rig_root)

    assert diagnostic["facts"]["brief_id"] == ORPHAN_BRIEF
    assert diagnostic["facts"]["policy_reference"] == "B2.1"


def test_unset_typed_fields_are_null_not_absent(tmp_path: Path):
    """A stable schema means the key is always present, even when empty."""
    city_root, rig_root = runtime(tmp_path)

    diagnostic = mbrf004(city_root, rig_root)

    assert "suggested_next_command" in diagnostic
