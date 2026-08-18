"""Mutations must lose races loudly instead of overwriting a concurrent verdict.

plan_adjudication reads the brief, runs doctor_briefs, and writes afterwards.
In that window the review patrol, a decision-dispatch order, or a second
operator session can adjudicate the same brief. Nothing detected that, so
"mutating commands fail closed" was aspirational.

`bd update` already ships the primitive: --if-status writes nothing on
mismatch and exits 13 specifically to mean "another actor won the race, and
retrying this guard is pointless." These tests pin that mctl uses it and
distinguishes a lost race from an ordinary failure.
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
OBSERVED_STATUS = "open"


def beads_payload() -> list[dict[str, object]]:
    return [
        {
            "id": BRIEF_ID,
            "title": "Pending brief",
            "status": OBSERVED_STATUS,
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
    """Runtime whose bd shim fails `update` with a configurable exit code."""
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
    argv_log = tmp_path / "bd-argv.jsonl"
    argv_log.write_text("", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "bd"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "argv = sys.argv[1:]\n"
        f"open({str(argv_log)!r}, 'a').write(json.dumps(argv) + '\\n')\n"
        "if argv and argv[0] == 'update':\n"
        f"    code = {update_exit}\n"
        "    if code:\n"
        "        sys.stderr.write('precondition failed\\n')\n"
        "        sys.exit(code)\n"
        "    sys.stdout.write(json.dumps({'id': argv[1], 'status': 'closed'}))\n"
        "else:\n"
        f"    sys.stdout.write(open({str(payload_path)!r}).read())\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return city_root, bin_dir, argv_log


def adjudicate(city_root: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env.pop("MCTL_BEADS_FIXTURE", None)
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", BRIEF_ID,
            "--verdict", "approve", "--reason", "race guard",
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def update_argv(argv_log: Path) -> list[str]:
    rows = [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines() if line]
    updates = [row for row in rows if row and row[0] == "update"]
    assert len(updates) == 1, f"expected one bd update, saw {updates}"
    return updates[0]


def test_adjudicate_guards_on_the_observed_status(tmp_path: Path):
    city_root, bin_dir, argv_log = runtime(tmp_path)

    result = adjudicate(city_root, bin_dir)

    assert result.returncode == 0, result.stderr
    argv = update_argv(argv_log)
    assert "--if-status" in argv, f"no optimistic-concurrency guard in {argv}"
    assert argv[argv.index("--if-status") + 1] == OBSERVED_STATUS


def test_lost_race_gets_its_own_diagnostic_code(tmp_path: Path):
    """bd exit 13 means another actor won; that must not look like a crash."""
    city_root, bin_dir, _argv_log = runtime(tmp_path, update_exit=13)

    result = adjudicate(city_root, bin_dir)

    assert result.returncode != 0
    assert "MCTL_BEAD_UPDATE_RACE_LOST" in result.stderr, result.stderr


def test_ordinary_failure_is_not_reported_as_a_lost_race(tmp_path: Path):
    city_root, bin_dir, _argv_log = runtime(tmp_path, update_exit=1)

    result = adjudicate(city_root, bin_dir)

    assert result.returncode != 0
    assert "MCTL_BEAD_UPDATE_RACE_LOST" not in result.stderr
    assert "MCTL_CANONICAL_BEAD_UPDATE_FAILED" in result.stderr, result.stderr


def test_dry_run_plans_the_guard_without_writing(tmp_path: Path):
    city_root, bin_dir, argv_log = runtime(tmp_path)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env.pop("MCTL_BEADS_FIXTURE", None)

    result = subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", BRIEF_ID,
            "--verdict", "approve", "--reason", "race guard", "--dry-run",
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is False
    update = payload["effect_plan"]["bead_updates"][0]
    assert update["if_status"] == OBSERVED_STATUS
    rows = [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines() if line]
    assert not [row for row in rows if row and row[0] == "update"], "dry run wrote"
