"""Plan §4's dispatch-safety invariants, MWRK001-MWRK003.

The plan assigns these three codes to dispatch safety:

    MWRK001  bead already has an active assignee
    MWRK002  open child workflow already exists for the same source
    MWRK003  dispatch returned success but assignee verification failed

work.py had reassigned all three to unrelated readiness checks, so the codes
meant different things in the plan and the code *and* none of the real
invariants existed. These three are precisely the double-dispatch and
lost-claim protections, and §3 makes stable codes the thing the Slice 6 MCP
surface and Slice 8 dashboard switch on.

The readiness checks now live at MWRK010+.
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

BRIEF = "mc-approved"
SOURCE = "source-ready"


def approved_pair(
    *,
    assignee: str | None = None,
    extra: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    source: dict[str, object] = {
        "id": SOURCE,
        "title": "Ready source work",
        "status": "open",
        "issue_type": "task",
        "labels": [],
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }
    if assignee is not None:
        source["assignee"] = assignee
    rows: list[dict[str, object]] = [
        {
            "id": BRIEF,
            "title": "Approved work brief",
            "status": "closed",
            "issue_type": "decision",
            "labels": ["brief-closed"],
            "dependencies": [
                {"issue_id": BRIEF, "depends_on_id": SOURCE, "type": "related"}
            ],
            "metadata": {"verdict": "approve"},
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
        source,
    ]
    rows.extend(extra or [])
    return rows


def child_workflow(status: str) -> dict[str, object]:
    return {
        "id": "mc-child-workflow",
        "title": "Existing workflow for the same source",
        "status": status,
        "issue_type": "task",
        "labels": [],
        "metadata": {"gc.root_bead_id": SOURCE, "gc.kind": "workflow"},
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }


def runtime(tmp_path: Path, rows: list[dict[str, object]], *, sling_assigns: bool = True):
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
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")

    fixture = beads / "issues.jsonl"
    fixture.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "gc"
    # A real sling claims the bead. Simulate that by stamping an assignee on
    # the fixture, or not, to exercise assignee verification.
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        # The control-plane gate is CITY-scoped and fails closed: an armed
        # dispatch refuses unless `gc status --json` confirms a running
        # controller. Declare one so these tests exercise the sling path.
        "if sys.argv[1:2] == ['status']:\n"
        "    sys.stdout.write(json.dumps({'controller': {'running': True,\n"
        "        'status': 'ready'}, 'suspended': False})); sys.exit(0)\n"
        f"assign = {sling_assigns!r}\n"
        f"path = {str(fixture)!r}\n"
        "if assign:\n"
        "    rows = [json.loads(l) for l in open(path).read().splitlines() if l.strip()]\n"
        "    for row in rows:\n"
        f"        if row['id'] == {SOURCE!r}:\n"
        "            row['assignee'] = 'mathcity/gc.run-operator'\n"
        "    open(path, 'w').write(''.join(json.dumps(r, sort_keys=True) + '\\n' for r in rows))\n"
        "sys.stdout.write(json.dumps({'dispatched': True}))\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return city_root, rig_root, bin_dir, fixture


def run_mctl(*args: str, bin_dir: Path, fixture: Path, arm: bool = False):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["MCTL_BEADS_FIXTURE"] = str(fixture)
    if arm:
        env["MCTL_ENABLE_LIVE_DISPATCH"] = "1"
    else:
        env.pop("MCTL_ENABLE_LIVE_DISPATCH", None)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def status_codes(city_root: Path, bin_dir: Path, fixture: Path) -> set[str]:
    result = run_mctl(
        "work", "status", BRIEF, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir, fixture=fixture,
    )
    assert result.returncode == 0, result.stderr
    return {b["code"] for b in json.loads(result.stdout)["work"]["blockers"]}


def test_mwrk001_blocks_a_source_bead_that_already_has_an_assignee(tmp_path: Path):
    """Dispatching a claimed bead is the lost-claim / double-dispatch case."""
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, approved_pair(assignee="someone-else")
    )

    assert "MWRK001" in status_codes(city_root, bin_dir, fixture)


def test_mwrk001_does_not_fire_for_an_unassigned_source(tmp_path: Path):
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, approved_pair())

    assert "MWRK001" not in status_codes(city_root, bin_dir, fixture)


def test_mwrk002_blocks_when_an_open_child_workflow_exists(tmp_path: Path):
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, approved_pair(extra=[child_workflow("in_progress")])
    )

    assert "MWRK002" in status_codes(city_root, bin_dir, fixture)


def test_mwrk002_ignores_a_closed_child_workflow(tmp_path: Path):
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, approved_pair(extra=[child_workflow("closed")])
    )

    assert "MWRK002" not in status_codes(city_root, bin_dir, fixture)


def test_dispatch_is_blocked_while_the_bead_is_claimed(tmp_path: Path):
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, approved_pair(assignee="someone-else")
    )

    result = run_mctl(
        "work", "dispatch", BRIEF, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir, fixture=fixture, arm=True,
    )

    assert result.returncode != 0
    assert "MWRK_DISPATCH_BLOCKED" in result.stderr


def test_mwrk003_is_a_pending_claim_not_a_fatal(tmp_path: Path):
    """#212: a sling that exits 0 DISPATCHED. The claim landing is separate.

    The claim does NOT arrive as a source-bead assignee -- work-briefed
    associates it on the minted molecule and the source's
    `execution.work_associated` event, ~210s after the sling. Reading the
    (never-set) assignee and raising MWRK003 FATAL reported every successful
    live dispatch as failed, and -- raising before provenance was written --
    made the retry mint a duplicate convoy (#213). The dispatch now succeeds
    with claim=`pending` and a NON-FATAL MWRK003 naming the recheck.
    """
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, approved_pair(), sling_assigns=False
    )

    result = run_mctl(
        "work", "dispatch", BRIEF, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir, fixture=fixture, arm=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert payload["claim"] == "pending"
    warnings = {d["code"]: d["severity"] for d in payload.get("diagnostics", [])}
    assert warnings.get("MWRK003") == "WARN", payload


def test_verified_dispatch_succeeds(tmp_path: Path):
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, approved_pair(), sling_assigns=True
    )

    result = run_mctl(
        "work", "dispatch", BRIEF, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir, fixture=fixture, arm=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is True


def test_readiness_checks_moved_out_of_the_reserved_range(tmp_path: Path):
    """The old readiness meanings must no longer squat on MWRK001-003."""
    rows = approved_pair()
    rows[0]["metadata"] = {}  # drop the approving verdict
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

    codes = status_codes(city_root, bin_dir, fixture)
    assert "MWRK010" in codes, f"no-approving-verdict should be MWRK010 now: {codes}"
    assert "MWRK001" not in codes


def test_mwrk010_does_not_fire_on_a_real_compound_approval(tmp_path: Path):
    """#160: `work.py` gates on a private reader that only recognises the
    four bare words `approve`/`approved`/`accept`/`accepted`.

    Measured live against `he-8hoo` (rig hecke, 2026-08-22): its recorded
    verdict is the typed field `metadata.verdict = "APPROVE-OPTION-A"` --
    a real approval, sourced exactly the way `briefs_list` (which already
    uses `verdicts.read_verdict`) reads it. `work_status` disagrees on the
    same bead: MWRK010, "no approving verdict". Every real approving brief
    census'd for #160 carried a compound verdict shaped like this one, not
    a bare word -- so this fixture is not a corner case, it is the
    population the fix has to serve.
    """
    rows = approved_pair()
    rows[0]["metadata"] = {"verdict": "APPROVE-OPTION-A"}
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

    codes = status_codes(city_root, bin_dir, fixture)
    assert "MWRK010" not in codes, (
        f"a real compound approval must not read as no-verdict: {codes}"
    )


def test_mwrk010_still_fires_on_reject_and_revise(tmp_path: Path):
    """The safety-critical control for #160's fix: widening the match from
    an exact set to a prefix check must not widen it far enough to catch the
    opposite polarity. A brief whose recorded verdict rejects or asks for
    revision must still be refused for dispatch.
    """
    for verdict_text in ("reject: not ready", "revise: needs more work"):
        rows = approved_pair()
        rows[0]["metadata"] = {"verdict": verdict_text}
        city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

        codes = status_codes(city_root, bin_dir, fixture)
        assert "MWRK010" in codes, (
            f"{verdict_text!r} must still block dispatch, got: {codes}"
        )
        tmp_path = tmp_path / "next"  # fresh tree per iteration
