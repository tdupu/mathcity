"""The Slice 6 client harness must run green in CI, not only by hand.

A server with no client cannot be demonstrated end to end, and a slice that
ships only scaffolding is exactly what this plan's slice rules forbid. The
harness is the vertical proof: it speaks the real stdio transport to a real
server subprocess and asserts a typed round trip and a typed failure.

These tests run the harness the same way an operator does and assert on its
machine-readable report, so the harness cannot rot into a hand-run script.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
HARNESS = SCRIPTS_ROOT / "mctl_mcp_harness.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

EXPECTED_CHECKS = (
    "connect",
    "tools_list",
    "typed_read_round_trip",
    "typed_schema_error",
    "no_passthrough_tool",
    "rollout_gate",
)


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def run_harness(city_root: Path, rig_root: Path, *extra: str):
    env = os.environ.copy()
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("MCTL_MCP_ENABLE_EXTERNAL_TOOLS", None)
    return subprocess.run(
        [
            sys.executable, str(HARNESS),
            "--city", str(city_root), "--rig", "mathcity", "--json", *extra,
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env, timeout=180,
    )


def test_the_harness_runs_green_against_a_fixture_city(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_harness(city_root, rig_root)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["passed"] is True
    assert tuple(check["name"] for check in report["checks"]) == EXPECTED_CHECKS
    assert all(check["passed"] for check in report["checks"])


def test_the_harness_talks_to_a_real_server_subprocess_over_stdio(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    report = json.loads(run_harness(city_root, rig_root).stdout)

    assert report["transport"] == "stdio"
    assert report["server"]["name"] == "mctl"
    assert report["server_command"][1].endswith("mctl.py")
    assert report["server_command"][2:4] == ["mcp", "serve"]


def test_the_harness_asserts_the_expected_tool_names(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    report = json.loads(run_harness(city_root, rig_root).stdout)

    listing = next(check for check in report["checks"] if check["name"] == "tools_list")
    assert listing["passed"] is True
    # 29 = 23 base + gates_status (#119) + molecules_list/_show (#111) +
    # orders_status + formulas_catalog + create_issue_bead (#170).
    # Deliberate literal: here the count IS the assertion, an independent
    # statement of expected surface size. Registry-relative would be
    # tautological -- the harness asserting what the harness says.
    assert len(listing["evidence"]["tools"]) == 34  # + create_github_issue (#185)
    # + briefs_present + decisions_to_briefs (#177)
    assert "briefs_list" in listing["evidence"]["tools"]
    assert listing["evidence"]["missing"] == []


def test_the_harness_validates_the_read_response_against_the_wire_schema(tmp_path: Path):
    """Typed round trip: validated against the schema the server transmitted."""
    city_root, rig_root = runtime_fixture(tmp_path)

    report = json.loads(run_harness(city_root, rig_root).stdout)

    check = next(check for check in report["checks"] if check["name"] == "typed_read_round_trip")
    assert check["passed"] is True
    assert check["evidence"]["tool"] == "briefs_list"
    assert check["evidence"]["schema_source"] == "tools/list"
    assert check["evidence"]["schema_errors"] == []
    assert check["evidence"]["brief_count"] >= 1


def test_the_harness_proves_the_typed_error_path(tmp_path: Path):
    """The central Slice 6 claim: a bad call fails as a typed schema error."""
    city_root, rig_root = runtime_fixture(tmp_path)

    report = json.loads(run_harness(city_root, rig_root).stdout)

    check = next(check for check in report["checks"] if check["name"] == "typed_schema_error")
    assert check["passed"] is True
    evidence = check["evidence"]
    assert evidence["jsonrpc_error_code"] == -32602
    assert evidence["diagnostic_code"] == "MCTL_MCP_INVALID_ARGUMENTS"
    assert evidence["schema_errors"], "a typed failure must name the failing field"
    assert evidence["schema_errors"][0]["path"] == "brief_id"
    assert evidence["looks_like_a_traceback"] is False
    assert evidence["is_prose_only"] is False


def test_the_harness_exercises_the_rollout_gate_rather_than_bypassing_it(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    report = json.loads(run_harness(city_root, rig_root).stdout)

    check = next(check for check in report["checks"] if check["name"] == "rollout_gate")
    assert check["passed"] is True
    assert check["evidence"]["internal_tool_count"] == 34  # + create_github_issue (#185)
    # + briefs_present + decisions_to_briefs (#177)
    assert check["evidence"]["external_tool_count"] == 0
    assert check["evidence"]["external_call_diagnostic"] == "MCTL_MCP_TOOL_DISABLED"


def test_the_harness_fails_loudly_when_a_check_cannot_be_satisfied(tmp_path: Path):
    """A harness that cannot fail is not a proof."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_harness(city_root, rig_root, "--expect-tool", "briefs_teleport")

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["passed"] is False
    listing = next(check for check in report["checks"] if check["name"] == "tools_list")
    assert listing["passed"] is False
    assert listing["evidence"]["missing"] == ["briefs_teleport"]


def test_the_harness_human_output_names_every_check(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    env = os.environ.copy()
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")

    result = subprocess.run(
        [sys.executable, str(HARNESS), "--city", str(city_root), "--rig", "mathcity"],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env, timeout=180,
    )

    assert result.returncode == 0, result.stderr
    for name in EXPECTED_CHECKS:
        assert name in result.stdout
    assert "PASS" in result.stdout
