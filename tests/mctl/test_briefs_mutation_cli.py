"""Behavior tests for Slice 3 mctl brief mutation commands."""
from __future__ import annotations

import hashlib
import json
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"


def runtime_fixture(tmp_path: Path, *, legacy_manifest: str = "") -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text(
        legacy_manifest, encoding="utf-8"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def run_mctl(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
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


def beads_fixture(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def tree_digest(root: Path) -> dict[Path, str]:
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_adjudicate_dry_run_returns_effect_plan_without_mutating_fixture(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(
            city_root,
            "adjudicate",
            "mc-open",
            "--verdict",
            "approve",
            "--reason",
            "ready",
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is False
    assert payload["effect_plan"]["operation"] == "briefs.adjudicate"
    assert payload["effect_plan"]["target_brief_id"] == "mc-open"
    assert payload["effect_plan"]["preconditions"] == []
    assert payload["effect_plan"]["bead_updates"][0]["status"] == "closed"
    assert payload["effect_plan"]["bead_updates"][0]["metadata"]["verdict"] == "approve"
    assert payload["trace_id"] == payload["effect_plan"]["trace_id"]
    assert tree_digest(rig_root) == before


def test_adjudicate_applies_canonical_bead_then_redundant_cache_and_events(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    stack_index = rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl"
    stack_index.write_text(
        stack_index.read_text(encoding="utf-8")
        + '{"slug":"mc-other","path":"mc-other.md","unlock_count":9}\n',
        encoding="utf-8",
    )

    result = run_mctl(
        *brief_command(
            city_root,
            "adjudicate",
            "mc-open",
            "--verdict",
            "approve",
            "--reason",
            "ready",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert [effect["kind"] for effect in payload["actual_effects"]][:2] == [
        "bead_update",
        "cache_update",
    ]
    rows = {row["id"]: row for row in read_jsonl(beads_fixture(rig_root))}
    assert rows["mc-open"]["status"] == "closed"
    assert rows["mc-open"]["metadata"]["verdict"] == "approve"
    assert rows["mc-open"]["metadata"]["verdict_reason"] == "ready"
    decision_cache = (rig_root / ".beads" / "briefs" / "decisions" / "mc-open.toml").read_text(
        encoding="utf-8"
    )
    assert 'status = "adjudicated"' in decision_cache
    assert 'verdict = "approve"' in decision_cache
    stack_rows = {row["slug"]: row for row in read_jsonl(stack_index)}
    assert stack_rows["mc-open"]["status"] == "adjudicated"
    assert "status" not in stack_rows["mc-other"]
    event_files = list((rig_root / ".beads" / "mctl" / "events").glob("*.jsonl"))
    trace_files = list((rig_root / ".beads" / "mctl" / "traces").glob("*.jsonl"))
    assert event_files
    assert trace_files
    assert payload["trace_id"] in event_files[0].read_text(encoding="utf-8")
    assert payload["trace_id"] in trace_files[0].read_text(encoding="utf-8")


def test_defer_dry_run_requires_non_empty_reason(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "defer", "mc-open", "--until", "2999-01-01", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MCTL_MUTATION_REASON_REQUIRED" in result.stderr


def test_mutation_fails_when_doctor_reports_blocking_diagnostics(tmp_path: Path):
    """RE-POINTED by #137: the blocker is MBRF005, no longer MBRF004.

    This test names the general behaviour -- a blocking diagnostic refuses the
    mutation -- so it needs a diagnostic that actually blocks. MBRF004 stopped
    being one when #137 downgraded it to WARN, on the grounds that a producer's
    omission must not refuse a human's verdict. `mc-closed` (closed with no
    recorded verdict) still raises MBRF005/ERROR through the same gate, so the
    behaviour under test is unchanged and still genuinely exercised.
    """
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "adjudicate",
            "mc-closed",
            "--verdict",
            "approve",
            "--reason",
            "ready",
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS" in result.stderr
    assert "MBRF005" in result.stderr


def test_mutation_fails_when_legacy_decisions_track_proof_is_required(tmp_path: Path):
    city_root, rig_root = runtime_fixture(
        tmp_path, legacy_manifest='{"slug":"mc-open","status":"ready"}\n'
    )

    result = run_mctl(
        *brief_command(
            city_root,
            "adjudicate",
            "mc-open",
            "--verdict",
            "approve",
            "--reason",
            "ready",
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in result.stderr


def test_defer_applies_defer_until_and_reason_to_canonical_bead(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "defer",
            "mc-open",
            "--reason",
            "waiting on owner",
            "--until",
            "2999-01-01",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    rows = {row["id"]: row for row in read_jsonl(beads_fixture(rig_root))}
    assert rows["mc-open"]["status"] == "deferred"
    assert rows["mc-open"]["defer_until"] == "2999-01-01"
    assert rows["mc-open"]["metadata"]["defer_reason"] == "waiting on owner"


def test_a_blocked_brief_can_still_be_revised(tmp_path: Path):
    """Refusal gates ratifying, not returning.

    `mc-broken` raises MBRF004, which blocks an approval and should. It must
    not block a revision: an unlinked, bodiless brief is exactly the brief an
    adjudicator sends back, and gating that leaves the malformed population
    with no route out of the queue at all.
    """
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root, "adjudicate", "mc-broken",
            "--verdict", "revise",
            "--reason", "No body and no source dependency; add the required fields.",
            "--dry-run", "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    # The CLI still exits non-zero because an ERROR-severity finding is
    # reported -- that convention is unchanged and deliberate. What matters is
    # that the plan was produced rather than vetoed.
    assert "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS" not in result.stderr
    assert "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["effect_plan"]["bead_updates"], "no plan was produced"
    assert payload["effect_plan"]["bead_updates"][0]["metadata"]["verdict"] == "revise"


def test_a_blocked_brief_can_still_be_rejected(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root, "adjudicate", "mc-broken",
            "--verdict", "reject",
            "--reason", "Not a brief; it decides about no other bead.",
            "--dry-run", "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["effect_plan"]["bead_updates"][0]["metadata"]["verdict"] == "reject"


def test_approving_a_blocked_brief_is_still_refused(tmp_path: Path):
    """The half of the gate that must survive: no ratifying an unreadable brief.

    RE-POINTED by #137 from `mc-broken` to `mc-closed`, and the guarantee is the
    point rather than the fixture. `mc-broken`'s only defect was MBRF004 -- a
    producer omitting a source link -- which #137 downgraded to WARN precisely
    because a producer's omission must not stop a human's verdict from being
    recorded. Keeping this test on `mc-broken` would have asserted the defect.

    `mc-closed` (closed with no recorded verdict, MBRF005/ERROR) still blocks
    through the same gate, so the assertion below is unchanged and the guarantee
    -- some briefs cannot be ratified -- is still genuinely exercised.

    NOTE for whoever touches MBRF005 next: it is itself under review, and it is
    self-sealing (the gate refuses to record a verdict on a brief whose defect is
    a missing verdict). When that is resolved this test needs re-pointing again,
    most likely at MBRF010 -- no canonical bead -- which is the durable version of
    "unreadable" because there is nothing to write to. Do not resolve it by
    deleting this test; the guarantee outlives every particular blocker.
    """
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root, "adjudicate", "mc-closed",
            "--verdict", "approve",
            "--reason", "looks fine",
            "--dry-run", "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    assert result.returncode != 0
    assert "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS" in result.stderr


def test_returning_a_blocked_brief_still_reports_the_finding(tmp_path: Path):
    """Demoted to advisory, not suppressed -- the record must still carry it."""
    import json

    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root, "adjudicate", "mc-broken",
            "--verdict", "revise",
            "--reason", "Add the required fields.",
            "--dry-run", "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    payload = json.loads(result.stdout)
    codes = {item.get("code") for item in payload.get("diagnostics") or ()}
    assert "MBRF004" in codes, payload.get("diagnostics")
