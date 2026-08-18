"""Live dispatch must be gated by intent, not by the test fixture.

apply_dispatch_plan refused live dispatch with `if ctx.beads_fixture is None`,
so "dispatch is disabled pending the canary" and "we are running in a test"
were the same switch. Setting MCTL_BEADS_FIXTURE in a live context would arm
dispatch and redirect canonical reads to a flat file at once, and the
production branch was unreachable.

Worse, the enabled branch never invoked `gc sling`. It wrote provenance,
appended event and trace rows, and returned "applied": true, flipping the
bead's readiness to `dispatched` — recording a dispatch that never happened.
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

APPROVED_BRIEF = "mc-approved"


def runtime(tmp_path: Path, gc_exit: int = 0) -> tuple[Path, Path, Path, Path]:
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
    (rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (rig_root / ".beads" / "decisions-track").mkdir(parents=True)
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    shutil.copy2(WORK_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gc_log = tmp_path / "gc-argv.jsonl"
    gc_log.write_text("", encoding="utf-8")
    shim = bin_dir / "gc"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"open({str(gc_log)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"code = {gc_exit}\n"
        "if code:\n"
        "    sys.stderr.write('sling failed\\n')\n"
        "    sys.exit(code)\n"
        "sys.stdout.write(json.dumps({'dispatched': True}))\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return city_root, rig_root, bin_dir, gc_log


def run_dispatch(
    city_root: Path, rig_root: Path, bin_dir: Path, *, enable: bool
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    if enable:
        env["MCTL_ENABLE_LIVE_DISPATCH"] = "1"
    else:
        env.pop("MCTL_ENABLE_LIVE_DISPATCH", None)
    return subprocess.run(
        [
            sys.executable, str(MCTL), "work", "dispatch", APPROVED_BRIEF,
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def gc_calls(gc_log: Path) -> list[list[str]]:
    return [json.loads(line) for line in gc_log.read_text(encoding="utf-8").splitlines() if line]


def provenance_files(rig_root: Path) -> list[Path]:
    root = rig_root / ".beads" / "mctl" / "provenance"
    return sorted(root.rglob("*.toml")) if root.is_dir() else []


def test_fixture_alone_no_longer_arms_live_dispatch(tmp_path: Path):
    """A test fixture must not be what enables a production side effect."""
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path)

    result = run_dispatch(city_root, rig_root, bin_dir, enable=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is False
    assert not gc_calls(gc_log)


def test_disabled_dispatch_writes_nothing(tmp_path: Path):
    city_root, rig_root, bin_dir, _gc_log = runtime(tmp_path)

    run_dispatch(city_root, rig_root, bin_dir, enable=False)

    assert not provenance_files(rig_root), "recorded provenance for a dispatch that never ran"
    assert not (rig_root / ".beads" / "mctl" / "events").exists()


def test_disabled_dispatch_leaves_readiness_untouched(tmp_path: Path):
    """A phantom provenance row flips readiness to `dispatched` and blocks retry."""
    city_root, rig_root, bin_dir, _gc_log = runtime(tmp_path)

    run_dispatch(city_root, rig_root, bin_dir, enable=False)

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    status = subprocess.run(
        [
            sys.executable, str(MCTL), "work", "status", APPROVED_BRIEF,
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["work"]["readiness"] == "ready"


def test_enabled_dispatch_actually_invokes_gc_sling(tmp_path: Path):
    """`applied: true` must mean the sling really ran."""
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path)

    result = run_dispatch(city_root, rig_root, bin_dir, enable=True)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    calls = gc_calls(gc_log)
    assert calls, "applied a dispatch without invoking gc sling"
    assert calls[0][0] == "sling"
    assert provenance_files(rig_root), "no provenance recorded for a real dispatch"


def test_failed_sling_is_not_recorded_as_a_dispatch(tmp_path: Path):
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path, gc_exit=1)

    result = run_dispatch(city_root, rig_root, bin_dir, enable=True)

    assert result.returncode != 0
    assert "MWRK_DISPATCH_COMMAND_FAILED" in result.stderr, result.stderr
    assert gc_calls(gc_log), "gc was never called"
    assert not provenance_files(rig_root), "recorded provenance for a failed dispatch"
