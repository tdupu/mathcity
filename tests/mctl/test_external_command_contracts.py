"""Contract tests for the external commands mctl shells out to.

mctl drives two binaries it does not own: `bd` (canonical bead reads and
writes) and `gc` (formula dispatch). Nothing else in the suite asserts the
argv mctl constructs, and nothing checks that argv against the installed
binaries, so a flag rename in bd or gc would silently produce a broken
command — for `gc sling` the command is only recorded as provenance, so the
breakage would not surface until a live dispatch.

These tests pin both halves: the argv mctl builds, and the flags the live
binaries actually accept.
"""
from __future__ import annotations

import json
import os
import re
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

BRIEF_ID = "mc-pending"
SOURCE_ID = "source-pending"

requires_bd = pytest.mark.skipif(shutil.which("bd") is None, reason="bd is not installed")
requires_gc = pytest.mark.skipif(shutil.which("gc") is None, reason="gc is not installed")


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


def recording_bd_runtime(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Runtime whose `bd` records every argv and answers list/update/create."""
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
        "    sys.stdout.write(json.dumps({'id': argv[1], 'status': 'closed'}))\n"
        "elif argv and argv[0] == 'create':\n"
        "    sys.stdout.write(json.dumps({'id': 'mc-created', 'status': 'open'}))\n"
        "elif argv and argv[0] == 'link':\n"
        "    sys.stdout.write('')\n"
        "else:\n"
        f"    sys.stdout.write(open({str(payload_path)!r}).read())\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return city_root, rig_root, bin_dir, argv_log


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


def recorded_argv(argv_log: Path) -> list[list[str]]:
    return [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines() if line]


def help_flags(command: list[str]) -> set[str]:
    """Extract the long flags a binary's --help advertises."""
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return set(re.findall(r"--[a-zA-Z0-9][a-zA-Z0-9-]*", result.stdout + result.stderr))


def long_flags_in(argv: list[str]) -> set[str]:
    return {arg for arg in argv if arg.startswith("--")}


def test_adjudicate_builds_the_expected_bd_update_argv(tmp_path: Path):
    city_root, _rig_root, bin_dir, argv_log = recording_bd_runtime(tmp_path)

    result = run_mctl(
        "briefs", "adjudicate", BRIEF_ID, "--verdict", "approve", "--reason", "argv pin",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    updates = [argv for argv in recorded_argv(argv_log) if argv and argv[0] == "update"]
    assert len(updates) == 1, f"expected exactly one bd update, saw {updates}"
    argv = updates[0]
    assert argv[1] == BRIEF_ID
    assert argv[-1] == "--json"
    assert "--status" in argv and argv[argv.index("--status") + 1] == "closed"
    metadata = {argv[i + 1] for i, arg in enumerate(argv) if arg == "--set-metadata"}
    assert "verdict=approve" in metadata
    assert "verdict_reason=argv pin" in metadata


@requires_bd
def test_bd_accepts_every_flag_mctl_passes_to_bd_update():
    """The live bd must still advertise the update flags mctl constructs."""
    advertised = help_flags(["bd", "update", "--help"])
    for flag in ("--status", "--set-metadata", "--defer", "--json"):
        assert flag in advertised, f"installed bd no longer advertises {flag}"


@requires_bd
def test_bd_accepts_every_flag_mctl_passes_to_bd_list():
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.beads import BD_LIST_ARGS

    advertised = help_flags(["bd", "list", "--help"])
    for flag in long_flags_in(list(BD_LIST_ARGS)):
        assert flag in advertised, f"installed bd no longer advertises {flag}"


@requires_gc
def test_gc_accepts_every_flag_mctl_puts_in_a_dispatch_command(tmp_path: Path):
    """The `gc sling` argv mctl records as provenance must be a real command.

    mctl never executes this command today, so flag drift in gc would sit
    undetected in provenance rows until a live dispatch ran it.
    """
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.work import _formula_invocation

    class _Ctx:
        rig_id = "mathcity"
        rig_root = tmp_path / "rig"

    class _Item:
        brief_id = BRIEF_ID
        bead_id = SOURCE_ID

    command = list(_formula_invocation(_Ctx(), _Item())["command"])
    assert command[:2] == ["gc", "sling"]

    advertised = help_flags(["gc", "sling", "--help"])
    for flag in long_flags_in(command):
        assert flag in advertised, f"installed gc sling no longer advertises {flag}"


def test_bd_timeout_default_clears_the_dolt_trouble_threshold():
    """5s is the latency CLAUDE.md calls a Dolt-trouble symptom.

    A full read of the largest live rig already takes 1-5s, so a 5s timeout
    makes bead commands fail exactly during the incident they diagnose.
    """
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core import beads

    assert beads.bd_timeout_seconds() > 5


def test_bd_timeout_is_configurable(monkeypatch: pytest.MonkeyPatch):
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core import beads

    monkeypatch.setenv("MCTL_BD_TIMEOUT_SECONDS", "45")
    assert beads.bd_timeout_seconds() == 45


def test_bd_timeout_ignores_unusable_values(monkeypatch: pytest.MonkeyPatch):
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core import beads

    monkeypatch.setenv("MCTL_BD_TIMEOUT_SECONDS", "not-a-number")
    assert beads.bd_timeout_seconds() == beads.DEFAULT_BD_TIMEOUT_SECONDS
    monkeypatch.setenv("MCTL_BD_TIMEOUT_SECONDS", "0")
    assert beads.bd_timeout_seconds() == beads.DEFAULT_BD_TIMEOUT_SECONDS


def test_create_builds_the_expected_bd_create_and_link_argv(tmp_path: Path):
    """Brief creation is bead-first, so its argv is part of the contract."""
    city_root, _rig_root, bin_dir, argv_log = recording_bd_runtime(tmp_path)
    body = tmp_path / "body.md"
    # #169: carries `## Gate Evidence`; briefs_create refuses without it.
    body.write_text(
        "## What is being decided\n\nShip it?\n\n"
        "## Gate Evidence\n\nG5: n/a -- no server surface touched.\n",
        encoding="utf-8",
    )

    result = run_mctl(
        "briefs", "create", "--title", "Decide dispatch policy",
        "--body-file", str(body), "--source", SOURCE_ID, "--label", "brief-open",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    creates = [argv for argv in recorded_argv(argv_log) if argv and argv[0] == "create"]
    assert len(creates) == 1, f"expected exactly one bd create, saw {creates}"
    argv = creates[0]
    assert argv[1] == "Decide dispatch policy"
    assert argv[-1] == "--json"
    assert argv[argv.index("--type") + 1] == "decision"
    assert argv[argv.index("--labels") + 1] == "brief-open"
    assert "## What is being decided" in argv[argv.index("--description") + 1]

    links = [argv for argv in recorded_argv(argv_log) if argv and argv[0] == "link"]
    assert len(links) == 1, f"expected exactly one bd link, saw {links}"
    assert links[0][2] == SOURCE_ID
    assert links[0][links[0].index("--type") + 1] == "related"


@requires_bd
def test_bd_accepts_every_flag_mctl_passes_to_bd_create():
    advertised = help_flags(["bd", "create", "--help"])
    for flag in ("--type", "--description", "--labels", "--metadata", "--json"):
        assert flag in advertised, f"installed bd no longer advertises {flag}"


@requires_bd
def test_bd_accepts_every_flag_mctl_passes_to_bd_link():
    advertised = help_flags(["bd", "link", "--help"])
    assert "--type" in advertised, "installed bd link no longer advertises --type"


def test_relate_builds_a_bare_positional_bd_dep_relate_argv(tmp_path: Path):
    """`bd dep relate a b`, and nothing else.

    Pinned separately from `bd dep add`, which mctl deliberately does NOT
    use: measured against bd 1.1.0 on 2026-08-20, `bd dep add <local-id>
    <unresolvable-id>` exits 0 and writes a row every hydrating read hides,
    while `relate` refuses the same id. A future edit that "simplified" this
    to `dep add` would reintroduce the silent-loss path.
    """
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.beads import BeadRelate, apply_bead_relate

    _city_root, rig_root, bin_dir, argv_log = recording_bd_runtime(tmp_path)
    env_path = os.environ["PATH"]
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{env_path}"
    try:
        apply_bead_relate(rig_root, BeadRelate(source_id="mc-event", target_id=SOURCE_ID))
    finally:
        os.environ["PATH"] = env_path

    relates = [argv for argv in recorded_argv(argv_log) if argv[:2] == ["dep", "relate"]]
    assert relates == [["dep", "relate", "mc-event", SOURCE_ID]]


@requires_bd
def test_bd_still_offers_the_dep_relate_subcommand():
    result = subprocess.run(
        ["bd", "dep", "--help"], text=True, capture_output=True, check=False
    )
    assert "relate" in result.stdout + result.stderr, (
        "installed bd no longer advertises `dep relate`"
    )


@requires_bd
def test_bd_accepts_every_event_flag_mctl_passes_to_bd_create():
    """The path-B provenance event is a typed `bd create --type event`."""
    advertised = help_flags(["bd", "create", "--help"])
    for flag in ("--event-category", "--event-target", "--event-payload"):
        assert flag in advertised, f"installed bd no longer advertises {flag}"


def test_a_dispatch_event_create_carries_the_event_flags(tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.beads import BeadCreate, apply_bead_create

    _city_root, rig_root, bin_dir, argv_log = recording_bd_runtime(tmp_path)
    env_path = os.environ["PATH"]
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{env_path}"
    try:
        apply_bead_create(
            rig_root,
            BeadCreate(
                placeholder_id="(pending)",
                title="dispatch provenance for source-pending",
                body="{}",
                issue_type="event",
                event_category="dispatch.provenance",
                event_target=SOURCE_ID,
                event_payload='{"schema": "dispatch-provenance.v1"}',
            ),
        )
    finally:
        os.environ["PATH"] = env_path

    argv = next(argv for argv in recorded_argv(argv_log) if argv[0] == "create")
    assert argv[argv.index("--type") + 1] == "event"
    assert argv[argv.index("--event-category") + 1] == "dispatch.provenance"
    assert argv[argv.index("--event-target") + 1] == SOURCE_ID
    assert "dispatch-provenance.v1" in argv[argv.index("--event-payload") + 1]


def test_a_non_event_create_passes_no_event_flags(tmp_path: Path):
    """bd rejects --event-* on every other type, so they are keyed on the type."""
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.beads import BeadCreate, apply_bead_create

    _city_root, rig_root, bin_dir, argv_log = recording_bd_runtime(tmp_path)
    env_path = os.environ["PATH"]
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{env_path}"
    try:
        apply_bead_create(
            rig_root,
            BeadCreate(
                placeholder_id="(pending)",
                title="Decide something",
                body="body",
                event_category="dispatch.provenance",
            ),
        )
    finally:
        os.environ["PATH"] = env_path

    argv = next(argv for argv in recorded_argv(argv_log) if argv[0] == "create")
    assert not long_flags_in(argv) & {"--event-category", "--event-target", "--event-payload"}
