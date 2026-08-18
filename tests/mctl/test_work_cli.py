"""Behavior tests for Slice 4 mctl work controls."""
from __future__ import annotations

import hashlib
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


def runtime_fixture(tmp_path: Path, *, legacy_manifest: str = "") -> tuple[Path, Path]:
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
    (rig_root / ".beads").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "decisions").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "stack").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl").write_text(
        "", encoding="utf-8"
    )
    (rig_root / ".beads" / "decisions-track").mkdir(parents=True)
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text(
        legacy_manifest, encoding="utf-8"
    )
    shutil.copy2(WORK_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    shutil.copytree(WORK_STATE / "provenance", rig_root / ".beads" / "mctl" / "provenance")
    return city_root, rig_root


def run_mctl(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if beads_fixture is not None:
        env["MCTL_BEADS_FIXTURE"] = str(beads_fixture)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def work_command(city_root: Path, *args: str) -> tuple[str, ...]:
    return ("work", *args, "--city", str(city_root), "--rig", "mathcity")


def beads_fixture(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def tree_digest(root: Path) -> dict[Path, str]:
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_work_ready_lists_only_approved_canonical_briefs_without_provenance(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *work_command(city_root, "ready", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [item["brief_id"] for item in payload["work"]] == ["mc-approved"]
    item = payload["work"][0]
    assert item["bead_id"] == "source-ready"
    assert item["readiness"] == "ready"
    assert item["blockers"] == []
    assert payload["trace_id"]


def test_work_status_reports_policy_and_readiness_blockers(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *work_command(city_root, "status", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    item = json.loads(result.stdout)["work"]
    assert item["readiness"] == "blocked"
    assert "MWRK010" in {diagnostic["code"] for diagnostic in item["blockers"]}


def test_work_provenance_accepts_valid_schema_fixture(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *work_command(city_root, "provenance", "mc-dispatched", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["provenance"]["bead_id"] == "source-dispatched"
    assert payload["provenance"]["dispatch"]["formula"] == "work-briefed"
    assert payload["diagnostics"] == []


def test_work_provenance_rejects_invalid_schema_with_stable_code(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *work_command(city_root, "provenance", "mc-invalid-provenance", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MWRK_PROVENANCE_INVALID" in result.stderr


def test_work_dispatch_dry_run_returns_payload_without_mutating_fixture(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *work_command(city_root, "dispatch", "mc-approved", "--dry-run", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is False
    assert payload["effect_plan"]["operation"] == "work.dispatch"
    assert payload["effect_plan"]["target_brief_id"] == "mc-approved"
    assert payload["effect_plan"]["formula_invocation"]["formula"] == "work-briefed"
    assert "source-ready" in payload["effect_plan"]["formula_invocation"]["command"]
    assert tree_digest(rig_root) == before


def test_armed_dispatch_writes_provenance_and_event_with_trace(tmp_path: Path):
    """Provenance is written only when live dispatch is explicitly armed.

    The bead fixture used to double as the live-dispatch switch; it no longer
    does, so this test arms MCTL_ENABLE_LIVE_DISPATCH and supplies a gc shim.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "gc"
    fixture = beads_fixture(rig_root)
    shim.write_text(
        "#!/usr/bin/env python3\nimport json, sys\n"
        # A real sling claims the bead; MWRK003 verifies the claim landed.
        f"path = {str(fixture)!r}\n"
        "rows = [json.loads(l) for l in open(path).read().splitlines() if l.strip()]\n"
        "for row in rows:\n"
        "    if row['id'] == 'source-ready':\n"
        "        row['assignee'] = 'mathcity/gc.run-operator'\n"
        "open(path, 'w').write(''.join(json.dumps(r, sort_keys=True) + '\\n' for r in rows))\n"
        "sys.stdout.write(json.dumps({'dispatched': True}))\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["MCTL_BEADS_FIXTURE"] = str(beads_fixture(rig_root))
    env["MCTL_ENABLE_LIVE_DISPATCH"] = "1"
    result = subprocess.run(
        [sys.executable, str(MCTL), *work_command(city_root, "dispatch", "mc-approved", "--json")],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    trace_id = payload["trace_id"]
    provenance = (rig_root / ".beads" / "mctl" / "provenance" / "source-ready.toml").read_text(
        encoding="utf-8"
    )
    assert f'trace_id = "{trace_id}"' in provenance
    event_files = list((rig_root / ".beads" / "mctl" / "events").glob("*.jsonl"))
    assert event_files
    assert trace_id in event_files[0].read_text(encoding="utf-8")


def test_work_dispatch_is_blocked_by_legacy_decisions_track_uncertainty(tmp_path: Path):
    city_root, rig_root = runtime_fixture(
        tmp_path, legacy_manifest='{"slug":"mc-approved","status":"ready"}\n'
    )

    result = run_mctl(
        *work_command(city_root, "dispatch", "mc-approved", "--dry-run", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in result.stderr
