"""Behavior tests for the `bin/mctl` executable shim.

`bin/mctl` is the only supported entry point for callers outside this
checkout. It must be a faithful, transparent wrapper around
`assets/scripts/mctl.py`: same arguments, same stdout/stderr, same exit
code, and — critically — the same *invocation cwd*, because
`mctl_core.context.resolve_context` discovers the city from `Path.cwd()`
ancestry. A shim that cd'd anywhere would silently change discovery.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "bin" / "mctl"
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

# `mctl` stamps a fresh uuid4 trace id into every payload, so two runs of the
# same command can never be literally byte-identical. Normalising just the
# uuids keeps the rest of the comparison byte-exact.
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


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
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def _env(beads_fixture: Path | None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if beads_fixture is not None:
        env["MCTL_BEADS_FIXTURE"] = str(beads_fixture)
    return env


def run_shim(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SHIM), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=_env(beads_fixture),
    )


def run_direct(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=_env(beads_fixture),
    )


def normalize(text: str) -> str:
    return UUID_RE.sub("<trace-id>", text)


def outside_repo(tmp_path: Path) -> Path:
    """A cwd guaranteed to be outside this checkout."""
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    assert not cwd.resolve().is_relative_to(REPO_ROOT)
    return cwd


def test_shim_exists_and_is_executable() -> None:
    assert SHIM.is_file(), f"missing executable entry point: {SHIM}"
    assert os.access(SHIM, os.X_OK), f"{SHIM} is not executable"


def test_shim_matches_direct_invocation_from_outside_the_repo(tmp_path: Path) -> None:
    city_root, _ = runtime_fixture(tmp_path)
    cwd = outside_repo(tmp_path)
    args = ("context", "--city", str(city_root), "--rig", "mathcity", "--explain")

    shim = run_shim(*args, cwd=cwd)
    direct = run_direct(*args, cwd=cwd)

    assert shim.returncode == 0, shim.stderr
    assert normalize(shim.stdout) == normalize(direct.stdout)
    assert normalize(shim.stderr) == normalize(direct.stderr)


def test_shim_json_output_is_byte_identical(tmp_path: Path) -> None:
    city_root, rig_root = runtime_fixture(tmp_path)
    cwd = outside_repo(tmp_path)
    fixture = rig_root / ".beads" / "issues.jsonl"
    args = (
        "briefs",
        "list",
        "--city",
        str(city_root),
        "--rig",
        "mathcity",
        "--json",
    )

    shim = run_shim(*args, cwd=cwd, beads_fixture=fixture)
    direct = run_direct(*args, cwd=cwd, beads_fixture=fixture)

    assert shim.returncode == 0, shim.stderr
    assert normalize(shim.stdout).encode() == normalize(direct.stdout).encode()


def test_shim_propagates_success_and_failure_exit_codes(tmp_path: Path) -> None:
    city_root, _ = runtime_fixture(tmp_path)
    cwd = outside_repo(tmp_path)

    ok = ("context", "--city", str(city_root), "--rig", "mathcity", "--json")
    assert run_shim(*ok, cwd=cwd).returncode == 0
    assert run_direct(*ok, cwd=cwd).returncode == 0

    # Diagnostic failure path (ContextError -> return 1).
    bad_city = ("context", "--city", str(tmp_path / "no-such-city"), "--rig", "mathcity")
    shim_bad = run_shim(*bad_city, cwd=cwd)
    direct_bad = run_direct(*bad_city, cwd=cwd)
    assert shim_bad.returncode == direct_bad.returncode == 1
    assert normalize(shim_bad.stderr) == normalize(direct_bad.stderr)

    # argparse failure path (exit 2) — proves the shim does not collapse every
    # nonzero status to 1.
    shim_usage = run_shim(cwd=cwd)
    direct_usage = run_direct(cwd=cwd)
    assert shim_usage.returncode == direct_usage.returncode == 2


def test_shim_does_not_change_the_invocation_cwd(tmp_path: Path) -> None:
    """City discovery walks up from cwd; the shim must not relocate it."""
    city_root, _ = runtime_fixture(tmp_path)
    nested = city_root / "mathcity"
    args = ("context", "--rig", "mathcity", "--explain")

    shim = run_shim(*args, cwd=nested)
    direct = run_direct(*args, cwd=nested)

    assert shim.returncode == 0, shim.stderr
    assert "cwd ancestry" in shim.stdout
    assert f"City root: {city_root}" in shim.stdout
    assert normalize(shim.stdout) == normalize(direct.stdout)


def test_shim_works_through_a_symlink(tmp_path: Path) -> None:
    """Repo root is resolved from the shim's real location, not $0's dir."""
    city_root, _ = runtime_fixture(tmp_path)
    cwd = outside_repo(tmp_path)
    linked = tmp_path / "mctl-link"
    linked.symlink_to(SHIM)

    result = subprocess.run(
        [str(linked), "context", "--city", str(city_root), "--rig", "mathcity", "--json"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=_env(None),
    )
    assert result.returncode == 0, result.stderr
