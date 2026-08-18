"""Without --json, mctl must render for a human.

Plan §1 promises "concise human output or structured JSON". The CLI already
branched on --json, but _render_brief_payload returned json.dumps on both
paths, so --json was a no-op and every command emitted JSON regardless. An
operator CLI that only speaks JSON does not meet the promise.
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
WORK_STATE = FIXTURES / "work_state"


def runtime(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    schema_dst = source_checkout / "assets" / "bead-filter"
    schema_dst.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "assets" / "bead-filter" / "dispatch-provenance-schema.toml",
        schema_dst / "dispatch-provenance-schema.toml",
    )
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    shutil.copy2(WORK_STATE / "beads.jsonl", beads / "issues.jsonl")
    return city_root, rig_root


def run(city_root: Path, rig_root: Path, *args: str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    return subprocess.run(
        [sys.executable, str(MCTL), *args, "--city", str(city_root), "--rig", "mathcity"],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def test_briefs_list_without_json_is_not_json(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "briefs", "list")

    assert result.returncode == 0, result.stderr
    assert not is_json(result.stdout), "--json is still a no-op for briefs list"


def test_briefs_list_human_output_names_the_briefs(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "briefs", "list")

    assert "mc-approved" in result.stdout
    assert "mc-open" in result.stdout


def test_json_flag_still_produces_json(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "briefs", "list", "--json")

    assert result.returncode == 0, result.stderr
    assert is_json(result.stdout)
    assert json.loads(result.stdout)["briefs"]


def test_work_ready_without_json_is_not_json(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "work", "ready")

    assert result.returncode == 0, result.stderr
    assert not is_json(result.stdout)


def test_doctor_without_json_surfaces_codes(tmp_path: Path):
    """Diagnostics are the point of doctor; they must survive the rendering."""
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "briefs", "doctor")

    assert result.returncode == 0, result.stderr
    assert not is_json(result.stdout)
    assert "MBRF" in result.stdout or "no diagnostics" in result.stdout.lower()


def test_human_output_still_reports_the_trace_id(tmp_path: Path):
    """Every payload carries a trace_id; it must not be lost in rendering."""
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "briefs", "list")

    assert "trace" in result.stdout.lower()


def test_work_status_human_output_shows_readiness_and_blockers(tmp_path: Path):
    city_root, rig_root = runtime(tmp_path)

    result = run(city_root, rig_root, "work", "status", "mc-open")

    assert result.returncode == 0, result.stderr
    assert not is_json(result.stdout)
    assert "blocked" in result.stdout.lower()
    assert "MWRK010" in result.stdout
