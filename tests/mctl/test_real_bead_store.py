"""End-to-end mctl tests against a real bd bead store.

Every other mctl test injects MCTL_BEADS_FIXTURE, which short-circuits the
`bd` subprocess adapter and reads a static JSONL file instead. That leaves the
canonical path — bd invocation, bd's own JSON contract, bd's write semantics —
completely unexercised, and lets fixtures encode states real bd rejects.

These tests build an isolated embedded-Dolt store with `bd init` (no Gas City
server, no live rig) and drive mctl against real beads. They never touch a
production rig.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"


def bd_available() -> bool:
    return shutil.which("bd") is not None


requires_bd = pytest.mark.skipif(not bd_available(), reason="bd is not installed")


def run_bd(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["BD_NON_INTERACTIVE"] = "1"
    result = subprocess.run(
        ["bd", *args], cwd=cwd, text=True, capture_output=True, check=False, env=env
    )
    assert result.returncode == 0, f"bd {' '.join(args)} failed: {result.stderr}"
    return result


def create_bead(cwd: Path, title: str, issue_type: str) -> str:
    payload = json.loads(run_bd("create", title, "-t", issue_type, "--json", cwd=cwd).stdout)
    return str(payload["id"])


@pytest.fixture(scope="module")
def seeded_store(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Create one real bd store; tests copy it so each gets an isolated clone.

    `bd init` costs seconds, so it runs once. Dependencies use `related`, which
    is the type real rigs use to link a brief to its source bead — `blocks`
    would make bd refuse to close the brief while the source is open.
    """
    store_root = tmp_path_factory.mktemp("real_bead_store")
    run_bd("init", "--prefix", "mc", "--non-interactive", cwd=store_root)

    approved = create_bead(store_root, "Approved brief", "decision")
    approved_source = create_bead(store_root, "Ready source work", "task")
    run_bd("link", approved, approved_source, "--type", "related", cwd=store_root)
    run_bd(
        "update", approved, "--set-metadata", "verdict=approve", "--status", "closed",
        cwd=store_root,
    )

    pending = create_bead(store_root, "Pending brief", "decision")
    pending_source = create_bead(store_root, "Unapproved source work", "task")
    run_bd("link", pending, pending_source, "--type", "related", cwd=store_root)

    orphan = create_bead(store_root, "Brief with no source", "decision")

    return {
        "beads_dir": store_root / ".beads",
        "approved": approved,
        "approved_source": approved_source,
        "pending": pending,
        "orphan": orphan,
    }


def runtime_with_real_store(tmp_path: Path, seeded: dict[str, object]) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    rig_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seeded["beads_dir"], rig_root / ".beads")
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    return city_root, rig_root


def run_mctl(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run mctl with NO bead fixture, so the real bd adapter is exercised."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("MCTL_BEADS_FIXTURE", None)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def bead_row(rig_root: Path, bead_id: str) -> dict[str, object]:
    rows = json.loads(
        run_bd("list", "--all", "--limit", "0", "--json", "--readonly", cwd=rig_root).stdout
    )
    matches = [row for row in rows if row["id"] == bead_id]
    assert matches, f"{bead_id} not found in the real store"
    return matches[0]


@requires_bd
def test_briefs_list_reads_real_decision_beads(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "briefs", "list", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    brief_ids = {brief["brief_id"] for brief in json.loads(result.stdout)["briefs"]}
    assert seeded_store["approved"] in brief_ids
    assert seeded_store["pending"] in brief_ids
    assert seeded_store["orphan"] in brief_ids
    # Source beads are tasks, not decisions, so they must not appear as briefs.
    assert seeded_store["approved_source"] not in brief_ids


@requires_bd
def test_doctor_flags_real_brief_without_source_dependency(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "briefs", "doctor", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    by_brief = {
        entry["brief_id"]: {diagnostic["code"] for diagnostic in entry["diagnostics"]}
        for entry in payload["brief_diagnostics"]
    }
    assert "MBRF004" in by_brief[seeded_store["orphan"]]
    assert "MBRF004" not in by_brief.get(seeded_store["approved"], set())


@requires_bd
def test_work_ready_uses_real_dependencies_and_verdict_metadata(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "work", "ready", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    work = json.loads(result.stdout)["work"]
    assert [item["brief_id"] for item in work] == [seeded_store["approved"]]
    assert work[0]["bead_id"] == seeded_store["approved_source"]


@requires_bd
def test_work_status_blocks_real_brief_without_approving_verdict(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "work", "status", str(seeded_store["pending"]),
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    item = json.loads(result.stdout)["work"]
    assert item["readiness"] == "blocked"
    assert "MWRK001" in {blocker["code"] for blocker in item["blockers"]}


@requires_bd
def test_adjudicate_dry_run_leaves_the_real_bead_untouched(tmp_path: Path, seeded_store):
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    brief_id = str(seeded_store["pending"])
    before = bead_row(rig_root, brief_id)

    result = run_mctl(
        "briefs", "adjudicate", brief_id, "--verdict", "approve",
        "--reason", "dry run must not write", "--dry-run",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is False
    after = bead_row(rig_root, brief_id)
    assert after["status"] == before["status"]
    assert after.get("metadata") == before.get("metadata")


@requires_bd
def test_adjudicate_writes_verdict_through_bd_to_the_real_bead(tmp_path: Path, seeded_store):
    """The canonical write path: mctl -> bd update -> real bead store."""
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    brief_id = str(seeded_store["pending"])
    assert bead_row(rig_root, brief_id)["status"] == "open"

    result = run_mctl(
        "briefs", "adjudicate", brief_id, "--verdict", "approve",
        "--reason", "real bead write",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is True

    after = bead_row(rig_root, brief_id)
    assert after["status"] == "closed"
    metadata = after.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    assert metadata.get("verdict") == "approve"
    assert metadata.get("verdict_reason") == "real bead write"


@requires_bd
def test_live_dispatch_stays_fail_closed_against_a_real_store(tmp_path: Path, seeded_store):
    """Dispatch must refuse to sling for real until a runtime canary exists."""
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "work", "dispatch", str(seeded_store["approved"]),
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0
    assert "MWRK_LIVE_DISPATCH_NOT_ENABLED" in result.stderr, result.stderr
