"""Traces must record what actually happened, including on failure.

Plan §4 requires appending the TraceRecord before mutation, appending actual
effects after, and appending blocking diagnostics if the operation aborts.
The implementation built one row at plan time with `"actual_effects": []`
hardcoded and wrote it verbatim *after* mutating, so the persisted trace never
recorded what happened — and if the bead update raised, nothing was written at
all, leaving a failed adjudication with no trace.
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

BRIEF_ID = "mc-pending"
SOURCE_ID = "source-pending"


def beads_payload() -> list[dict[str, object]]:
    return [
        {
            "id": BRIEF_ID,
            "title": "Pending brief",
            "status": "open",
            "issue_type": "decision",
            "labels": ["brief-open"],
            "dependencies": [
                {"issue_id": BRIEF_ID, "depends_on_id": SOURCE_ID, "type": "related"}
            ],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
        {
            "id": SOURCE_ID,
            "title": "Source work",
            "status": "open",
            "issue_type": "task",
            "labels": [],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
    ]


def runtime(tmp_path: Path, update_exit: int = 0) -> tuple[Path, Path, Path]:
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

    payload_path = tmp_path / "beads.json"
    payload_path.write_text(json.dumps(beads_payload()), encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "bd"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "argv = sys.argv[1:]\n"
        "if argv and argv[0] == 'update':\n"
        f"    code = {update_exit}\n"
        "    if code:\n"
        "        sys.stderr.write('bd update failed\\n')\n"
        "        sys.exit(code)\n"
        "    sys.stdout.write(json.dumps({'id': argv[1], 'status': 'closed'}))\n"
        "else:\n"
        f"    sys.stdout.write(open({str(payload_path)!r}).read())\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return city_root, rig_root, bin_dir


def run_mctl(*args: str, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env.pop("MCTL_BEADS_FIXTURE", None)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def adjudicate(city_root: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    return run_mctl(
        "briefs", "adjudicate", BRIEF_ID, "--verdict", "approve", "--reason", "trace test",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir,
    )


def trace_rows(rig_root: Path) -> list[dict[str, object]]:
    traces = rig_root / ".beads" / "mctl" / "traces"
    rows: list[dict[str, object]] = []
    for path in sorted(traces.glob("*.jsonl")):
        rows.extend(
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        )
    return rows


def test_planned_phase_is_written_before_the_mutation(tmp_path: Path):
    city_root, rig_root, bin_dir = runtime(tmp_path)

    result = adjudicate(city_root, bin_dir)
    assert result.returncode == 0, result.stderr

    phases = [row.get("phase") for row in trace_rows(rig_root)]
    assert "planned" in phases, f"no planned trace row: {phases}"


def test_applied_phase_records_actual_effects(tmp_path: Path):
    city_root, rig_root, bin_dir = runtime(tmp_path)

    result = adjudicate(city_root, bin_dir)
    assert result.returncode == 0, result.stderr

    applied = [row for row in trace_rows(rig_root) if row.get("phase") == "applied"]
    assert applied, "no applied trace row"
    effects = applied[0]["actual_effects"]
    assert effects, "applied trace row recorded no actual effects"
    assert any(effect.get("kind") == "bead_update" for effect in effects)


def test_failed_mutation_still_leaves_a_trace(tmp_path: Path):
    """A failed or crashed adjudication must not vanish from the trace log."""
    city_root, rig_root, bin_dir = runtime(tmp_path, update_exit=1)

    result = adjudicate(city_root, bin_dir)
    assert result.returncode != 0

    rows = trace_rows(rig_root)
    assert rows, "a failed adjudication left no trace at all"
    phases = [row.get("phase") for row in rows]
    assert "planned" in phases
    assert "aborted" in phases, f"no aborted phase recorded: {phases}"


def test_aborted_phase_records_why(tmp_path: Path):
    city_root, rig_root, bin_dir = runtime(tmp_path, update_exit=1)

    adjudicate(city_root, bin_dir)

    aborted = [row for row in trace_rows(rig_root) if row.get("phase") == "aborted"]
    assert aborted
    assert aborted[0].get("blocking_diagnostics"), "abort recorded no diagnostics"


def test_all_phases_share_one_trace_id(tmp_path: Path):
    city_root, rig_root, bin_dir = runtime(tmp_path)

    result = adjudicate(city_root, bin_dir)
    payload = json.loads(result.stdout)

    trace_ids = {row["trace_id"] for row in trace_rows(rig_root)}
    assert trace_ids == {payload["trace_id"]}


def test_trace_show_folds_phases_into_one_record(tmp_path: Path):
    city_root, rig_root, bin_dir = runtime(tmp_path)
    result = adjudicate(city_root, bin_dir)
    trace_id = json.loads(result.stdout)["trace_id"]

    shown = run_mctl(
        "trace", "show", trace_id, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir,
    )

    assert shown.returncode == 0, shown.stderr
    record = json.loads(shown.stdout)["trace"]
    assert record["trace_id"] == trace_id
    assert record["operation"] == "briefs.adjudicate"
    assert record["planned_effects"]
    assert record["actual_effects"]


def test_trace_show_reports_an_unknown_trace_id(tmp_path: Path):
    city_root, _rig_root, bin_dir = runtime(tmp_path)

    shown = run_mctl(
        "trace", "show", "00000000-0000-0000-0000-000000000000",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir,
    )

    assert shown.returncode != 0
    assert "MCTL_TRACE_NOT_FOUND" in shown.stderr
