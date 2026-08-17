"""Behavior tests for the Slice 2 read-only mctl brief commands."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.beads import read_beads


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    (rig_root / ".beads").mkdir(exist_ok=True)
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def run_mctl(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
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


def brief_command(city_root: Path, *args: str) -> tuple[str, ...]:
    return ("briefs", *args, "--city", str(city_root), "--rig", "mathcity")


def tree_digest(root: Path) -> dict[Path, str]:
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def beads_fixture(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def test_briefs_list_returns_only_decision_beads_and_supports_filters(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "list", "--status", "pending", "--label", "release", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [brief["brief_id"] for brief in payload["briefs"]] == ["mc-open"]
    assert payload["briefs"][0]["bead_id"] == "mc-open"
    assert payload["briefs"][0]["canonical_source"] == "bead_store"
    assert payload["trace_id"]


def test_briefs_show_reports_canonical_bead_redundant_artifacts_and_policy_refs(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "show", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["brief"]["bead_id"] == "mc-open"
    assert payload["brief"]["canonical_source"] == "bead_store"
    assert {artifact["kind"] for artifact in payload["brief"]["redundant_artifacts"]} == {
        "pile",
        "stack_index",
        "decision_toml",
        "legacy_decisions_track",
    }
    assert payload["brief"]["policy_references"]
    assert payload["trace_id"]


def test_briefs_options_disables_mutations_when_doctor_reports_errors(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "options", "mc-broken", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    mutation_options = [
        option
        for option in payload["options"]
        if option["id"] in {"adjudicate", "defer", "dispatch-work"}
    ]
    assert mutation_options
    assert all(not option["enabled"] for option in mutation_options)
    assert {option["disabled_reason"]["code"] for option in mutation_options} >= {
        "MBRF004"
    }
    assert payload["trace_id"]


def test_briefs_doctor_reports_inconsistent_cache_without_rewriting_fixture_state(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "MBRF002" in {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert payload["severity_counts"]["ERROR"] >= 1
    assert any(
        item["brief_id"] == "mc-file-only" and item["diagnostics"]
        for item in payload["brief_diagnostics"]
    )
    assert tree_digest(rig_root) == before
    assert payload["trace_id"]


def test_briefs_doctor_blocks_unproven_legacy_decisions_track_state(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    codes = {diagnostic["code"] for diagnostic in json.loads(result.stdout)["diagnostics"]}
    assert "MBRF008" in codes
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes


def test_brief_commands_fail_closed_from_source_checkout_without_explicit_context():
    result = run_mctl("briefs", "list", "--json", cwd=SOURCE_CHECKOUT)

    assert result.returncode != 0
    assert "MCTL_CONTEXT_SOURCE_CHECKOUT" in result.stderr


def test_brief_commands_require_an_explicit_rig_from_source_checkout(tmp_path: Path):
    city_root, _ = runtime_fixture(tmp_path)

    result = run_mctl(
        "briefs", "list", "--city", str(city_root), "--json", cwd=REPO_ROOT
    )

    assert result.returncode != 0
    assert "MCTL_CONTEXT_SOURCE_CHECKOUT" in result.stderr


def test_runtime_bead_reader_ignores_passive_jsonl_export(monkeypatch, tmp_path: Path):
    _, rig_root = runtime_fixture(tmp_path)

    def canonical_bd_list(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='[{"id":"mc-canonical","title":"Canonical","status":"open","issue_type":"decision","labels":["brief-open"],"dependencies":["mc-source"]}]',
            stderr="",
        )

    monkeypatch.setattr("mctl_core.beads.subprocess.run", canonical_bd_list)

    assert [bead.id for bead in read_beads(rig_root)] == ["mc-canonical"]


def test_fixture_bead_reader_requires_explicit_fixture_injection(monkeypatch, tmp_path: Path):
    _, rig_root = runtime_fixture(tmp_path)

    def unexpected_bd_list(*args, **kwargs):
        raise AssertionError("explicit fixture loading must not invoke bd")

    monkeypatch.setattr("mctl_core.beads.subprocess.run", unexpected_bd_list)

    assert [bead.id for bead in read_beads(rig_root, fixture_path=beads_fixture(rig_root))] == [
        "mc-open",
        "mc-broken",
        "mc-closed",
        "mc-adjudicated",
        "mc-work",
    ]


def test_legacy_marker_does_not_bypass_the_unproven_migration_blocker(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    marker = (
        rig_root
        / ".beads"
        / "briefs"
        / "migrations"
        / "2026-08-15-decisions-track-inventory.jsonl"
    )
    marker.parent.mkdir(parents=True)
    marker.write_text("historical migration inventory\n")

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    codes = {diagnostic["code"] for diagnostic in json.loads(result.stdout)["diagnostics"]}
    assert "MBRF008" in codes
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes


def test_doctor_brief_scope_ignores_unrelated_cache_and_legacy_drift(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    doctor = run_mctl(
        *brief_command(city_root, "doctor", "--brief", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    options = run_mctl(
        *brief_command(city_root, "options", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert doctor.returncode == 0, doctor.stderr
    assert json.loads(doctor.stdout)["diagnostics"] == []
    assert options.returncode == 0, options.stderr
    assert all(
        option["enabled"]
        for option in json.loads(options.stdout)["options"]
        if option["id"] in {"adjudicate", "defer", "dispatch-work"}
    )


def test_closed_brief_diagnostic_has_canonical_data_location_and_policy_ref(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--brief", "mc-closed", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    diagnostic = next(
        item
        for item in json.loads(result.stdout)["diagnostics"]
        if item["code"] == "MBRF005"
    )
    assert diagnostic["facts"]["data_location"] == "bd list --json (rig database fixture_mathcity)"
    assert diagnostic["facts"]["policy_reference"] == "B2.2"


def test_nonpending_option_diagnostic_has_canonical_data_location_and_policy_ref(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "options", "mc-adjudicated", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    diagnostic = next(
        option["disabled_reason"]
        for option in json.loads(result.stdout)["options"]
        if option["id"] == "adjudicate"
    )
    assert diagnostic["code"] == "MBRF011"
    assert diagnostic["facts"]["data_location"] == "bd list --json (rig database fixture_mathcity)"
    assert diagnostic["facts"]["policy_reference"] == "B2.2"
