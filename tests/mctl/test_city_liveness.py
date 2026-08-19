"""mctl must fail fast when the rig's Gas City data plane is not running.

A rig configured for Dolt server mode is unusable when the managed server is
down. Without an explicit liveness check every bead command instead blocks on
a `bd` subprocess until its timeout, which reads as a hang and buries the real
cause. These tests pin the fast, explicit failure.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

# A liveness probe plus process start must stay well under the bd timeout.
FAST_FAILURE_SECONDS = 4.0


def closed_port() -> int:
    """Bind and release a port so we know nothing is listening on it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def server_mode_runtime(tmp_path: Path, port: int | None) -> tuple[Path, Path]:
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
    (beads / "config.yaml").write_text("issue_prefix: mc\ndolt.mode: server\n", encoding="utf-8")
    if port is not None:
        (beads / "dolt-server.port").write_text(f"{port}\n", encoding="utf-8")
    return city_root, rig_root


def run_mctl(*args: str, cwd: Path) -> tuple[subprocess.CompletedProcess[str], float]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("MCTL_BEADS_FIXTURE", None)
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    return result, time.monotonic() - started


def test_briefs_list_errors_immediately_when_city_is_not_active(tmp_path: Path):
    city_root, _rig_root = server_mode_runtime(tmp_path, closed_port())

    result, elapsed = run_mctl(
        "briefs", "list", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0
    assert "MCTL_CITY_NOT_ACTIVE" in result.stderr, result.stderr
    assert elapsed < FAST_FAILURE_SECONDS, f"took {elapsed:.2f}s to report a dead city"


def test_work_ready_errors_immediately_when_city_is_not_active(tmp_path: Path):
    city_root, _rig_root = server_mode_runtime(tmp_path, closed_port())

    result, elapsed = run_mctl(
        "work", "ready", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0
    assert "MCTL_CITY_NOT_ACTIVE" in result.stderr, result.stderr
    assert elapsed < FAST_FAILURE_SECONDS, f"took {elapsed:.2f}s to report a dead city"


def test_dead_city_diagnostic_names_the_endpoint_and_next_command(tmp_path: Path):
    port = closed_port()
    city_root, _rig_root = server_mode_runtime(tmp_path, port)

    result, _elapsed = run_mctl(
        "briefs", "list", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert str(port) in result.stderr, result.stderr
    assert "gc supervisor" in result.stderr or "gc dolt" in result.stderr, result.stderr


def test_context_reports_city_not_active_without_failing(tmp_path: Path):
    """`mctl context` is the diagnostic surface, so it must still answer."""
    city_root, _rig_root = server_mode_runtime(tmp_path, closed_port())

    result, _elapsed = run_mctl(
        "context", "--city", str(city_root), "--rig", "mathcity", "--json", cwd=REPO_ROOT
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["city_active"] is False


def test_embedded_rig_without_server_config_is_not_probed(tmp_path: Path):
    """A rig with no server port is embedded-mode; liveness must not block it."""
    city_root, rig_root = server_mode_runtime(tmp_path, None)
    (rig_root / ".beads" / "config.yaml").write_text("issue_prefix: mc\n", encoding="utf-8")

    result, _elapsed = run_mctl(
        "context", "--city", str(city_root), "--rig", "mathcity", "--json", cwd=REPO_ROOT
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["city_active"] is None


def test_human_context_output_shows_liveness(tmp_path: Path):
    """The field exists to diagnose a broken city, so the human view needs it.

    Hiding city_active behind --json puts the one fact a human wants during an
    outage in the output shape they are least likely to be using.
    """
    city_root, _rig_root = server_mode_runtime(tmp_path, closed_port())

    result, _elapsed = run_mctl(
        "context", "--city", str(city_root), "--rig", "mathcity", cwd=REPO_ROOT
    )

    assert result.returncode == 0, result.stderr
    assert "city" in result.stdout.lower()
    assert "not reachable" in result.stdout.lower() or "inactive" in result.stdout.lower()


def test_human_context_output_shows_a_healthy_data_plane(tmp_path: Path):
    city_root, rig_root = server_mode_runtime(tmp_path, None)
    (rig_root / ".beads" / "config.yaml").write_text("issue_prefix: mc\n", encoding="utf-8")

    result, _elapsed = run_mctl(
        "context", "--city", str(city_root), "--rig", "mathcity", cwd=REPO_ROOT
    )

    assert result.returncode == 0, result.stderr
    assert "embedded" in result.stdout.lower() or "not use a dolt server" in result.stdout.lower()
