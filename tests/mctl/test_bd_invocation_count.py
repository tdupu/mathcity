"""Regression tests bounding how often mctl shells out to bd.

These tests deliberately do NOT set MCTL_BEADS_FIXTURE. They put a counting
`bd` shim on PATH so the real subprocess adapter in mctl_core.beads runs and
every invocation is recorded. A per-brief bd call makes `mctl work ready`
scale with the number of decision beads, which is unusable on a real rig.
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

DECISION_BEAD_COUNT = 12


def _beads_payload(count: int = DECISION_BEAD_COUNT) -> list[dict[str, object]]:
    """One approved brief plus its source bead, repeated `count` times."""
    rows: list[dict[str, object]] = []
    for index in range(count):
        brief_id = f"mc-brief-{index:02d}"
        source_id = f"source-{index:02d}"
        rows.append(
            {
                "id": brief_id,
                "title": f"Approved work brief {index}",
                "status": "closed",
                "issue_type": "decision",
                "labels": ["brief-closed"],
                "dependencies": [
                    {"issue_id": brief_id, "depends_on_id": source_id, "type": "blocks"}
                ],
                "metadata": {"verdict": "approve"},
                "created_at": "2026-08-10T12:00:00Z",
                "updated_at": "2026-08-11T12:00:00Z",
            }
        )
        rows.append(
            {
                "id": source_id,
                "title": f"Ready source work {index}",
                "status": "open",
                "issue_type": "task",
                "labels": ["release"],
                "created_at": "2026-08-10T12:00:00Z",
                "updated_at": "2026-08-11T12:00:00Z",
            }
        )
    return rows


def counting_bd_runtime(
    tmp_path: Path, count: int = DECISION_BEAD_COUNT
) -> tuple[Path, Path, Path, Path]:
    """Build a runtime fixture whose `bd` is a shim that records each call."""
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    (rig_root / ".beads" / "briefs" / "decisions").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "stack").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (rig_root / ".beads" / "decisions-track").mkdir(parents=True)
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")

    payload_path = tmp_path / "beads.json"
    payload_path.write_text(json.dumps(_beads_payload(count)), encoding="utf-8")

    call_log = tmp_path / "bd-calls.log"
    call_log.write_text("", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "bd"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"open({str(call_log)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        f"sys.stdout.write(open({str(payload_path)!r}).read())\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return city_root, rig_root, bin_dir, call_log


def run_mctl(*args: str, cwd: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env.pop("MCTL_BEADS_FIXTURE", None)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def bd_call_count(call_log: Path) -> int:
    return len([line for line in call_log.read_text(encoding="utf-8").splitlines() if line])


def test_work_ready_reads_beads_a_bounded_number_of_times(tmp_path: Path):
    city_root, _rig_root, bin_dir, call_log = counting_bd_runtime(tmp_path)

    result = run_mctl(
        "work",
        "ready",
        "--city",
        str(city_root),
        "--rig",
        "mathcity",
        "--json",
        cwd=REPO_ROOT,
        bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["work"]) == DECISION_BEAD_COUNT
    calls = bd_call_count(call_log)
    assert calls <= 2, (
        f"mctl work ready shelled out to bd {calls} times for "
        f"{DECISION_BEAD_COUNT} decision beads; the bead read must not scale "
        "with the number of briefs"
    )


def test_work_ready_bd_calls_do_not_grow_with_brief_count(tmp_path: Path):
    """A rig with 5x the briefs must cost the same number of bd calls."""
    small_city, _r1, small_bin, small_log = counting_bd_runtime(tmp_path / "small", count=2)
    small = run_mctl(
        "work", "ready", "--city", str(small_city), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=small_bin,
    )
    assert small.returncode == 0, small.stderr

    large_city, _r2, large_bin, large_log = counting_bd_runtime(tmp_path / "large", count=10)
    large = run_mctl(
        "work", "ready", "--city", str(large_city), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=large_bin,
    )
    assert large.returncode == 0, large.stderr

    assert len(json.loads(large.stdout)["work"]) == 5 * len(json.loads(small.stdout)["work"])
    assert bd_call_count(small_log) == bd_call_count(large_log), (
        f"bd calls grew from {bd_call_count(small_log)} to {bd_call_count(large_log)} "
        "when the brief count grew 5x"
    )


def test_briefs_list_reads_beads_once(tmp_path: Path):
    city_root, _rig_root, bin_dir, call_log = counting_bd_runtime(tmp_path)

    result = run_mctl(
        "briefs", "list", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    assert bd_call_count(call_log) == 1


def test_briefs_validate_all_reads_beads_a_bounded_number_of_times(tmp_path: Path):
    """`validate --all` walks every brief; it must still read the store once."""
    city_root, _rig_root, bin_dir, call_log = counting_bd_runtime(tmp_path)

    result = run_mctl(
        "briefs", "validate", "--all", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["brief_diagnostics"]) >= DECISION_BEAD_COUNT
    calls = bd_call_count(call_log)
    assert calls <= 2, (
        f"mctl briefs validate --all shelled out to bd {calls} times for "
        f"{DECISION_BEAD_COUNT} decision beads; the bead read must not scale "
        "with the number of briefs"
    )


def test_briefs_validate_all_bd_calls_do_not_grow_with_brief_count(tmp_path: Path):
    small_city, _r1, small_bin, small_log = counting_bd_runtime(tmp_path / "small", count=2)
    small = run_mctl(
        "briefs", "validate", "--all", "--city", str(small_city), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=small_bin,
    )
    assert small.returncode == 0, small.stderr

    large_city, _r2, large_bin, large_log = counting_bd_runtime(tmp_path / "large", count=10)
    large = run_mctl(
        "briefs", "validate", "--all", "--city", str(large_city), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=large_bin,
    )
    assert large.returncode == 0, large.stderr

    assert len(json.loads(large.stdout)["brief_diagnostics"]) == 5 * len(
        json.loads(small.stdout)["brief_diagnostics"]
    )
    assert bd_call_count(small_log) == bd_call_count(large_log), (
        f"bd calls grew from {bd_call_count(small_log)} to {bd_call_count(large_log)} "
        "when the brief count grew 5x"
    )
