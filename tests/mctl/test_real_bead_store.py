"""End-to-end mctl tests against a real bd bead store.

Every other mctl test injects MCTL_BEADS_FIXTURE, which short-circuits the
`bd` subprocess adapter and reads a static JSONL file instead. That leaves the
canonical path — bd invocation, bd's own JSON contract, bd's write semantics —
completely unexercised, and lets fixtures encode states real bd rejects.

These tests build an isolated embedded-Dolt store with `bd init` (no Gas City
server, no live rig) and drive mctl against real beads. They never touch a
production rig.
"""
from __future__ import annotations

import json
import os
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


def bd_available() -> bool:
    return shutil.which("bd") is not None


requires_bd = pytest.mark.skipif(not bd_available(), reason="bd is not installed")


def run_bd(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["BD_NON_INTERACTIVE"] = "1"
    result = subprocess.run(
        ["bd", *args], cwd=cwd, text=True, capture_output=True, check=False, env=env
    )
    assert result.returncode == 0, f"bd {' '.join(args)} failed: {result.stderr}"
    return result


def create_bead(cwd: Path, title: str, issue_type: str) -> str:
    payload = json.loads(run_bd("create", title, "-t", issue_type, "--json", cwd=cwd).stdout)
    return str(payload["id"])


@pytest.fixture(scope="module")
def seeded_store(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Create one real bd store; tests copy it so each gets an isolated clone.

    `bd init` costs seconds, so it runs once. Dependencies use `related`, which
    is the type real rigs use to link a brief to its source bead — `blocks`
    would make bd refuse to close the brief while the source is open.
    """
    store_root = tmp_path_factory.mktemp("real_bead_store")
    run_bd("init", "--prefix", "mc", "--non-interactive", cwd=store_root)

    approved = create_bead(store_root, "Approved brief", "decision")
    approved_source = create_bead(store_root, "Ready source work", "task")
    run_bd("link", approved, approved_source, "--type", "related", cwd=store_root)
    run_bd(
        "update", approved, "--set-metadata", "verdict=approve", "--status", "closed",
        cwd=store_root,
    )

    pending = create_bead(store_root, "Pending brief", "decision")
    pending_source = create_bead(store_root, "Unapproved source work", "task")
    run_bd("link", pending, pending_source, "--type", "related", cwd=store_root)

    orphan = create_bead(store_root, "Brief with no source", "decision")

    return {
        "beads_dir": store_root / ".beads",
        "approved": approved,
        "approved_source": approved_source,
        "pending": pending,
        "orphan": orphan,
    }


def runtime_with_real_store(tmp_path: Path, seeded: dict[str, object]) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    rig_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seeded["beads_dir"], rig_root / ".beads")
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    return city_root, rig_root


def run_mctl(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run mctl with NO bead fixture, so the real bd adapter is exercised."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("MCTL_BEADS_FIXTURE", None)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def bead_row(rig_root: Path, bead_id: str) -> dict[str, object]:
    rows = json.loads(
        run_bd("list", "--all", "--limit", "0", "--json", "--readonly", cwd=rig_root).stdout
    )
    matches = [row for row in rows if row["id"] == bead_id]
    assert matches, f"{bead_id} not found in the real store"
    return matches[0]


@requires_bd
def test_briefs_list_reads_real_decision_beads(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "briefs", "list", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    brief_ids = {brief["brief_id"] for brief in json.loads(result.stdout)["briefs"]}
    assert seeded_store["approved"] in brief_ids
    assert seeded_store["pending"] in brief_ids
    assert seeded_store["orphan"] in brief_ids
    # Source beads are tasks, not decisions, so they must not appear as briefs.
    assert seeded_store["approved_source"] not in brief_ids


@requires_bd
def test_doctor_flags_real_brief_without_source_dependency(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "briefs", "doctor", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    by_brief = {
        entry["brief_id"]: {diagnostic["code"] for diagnostic in entry["diagnostics"]}
        for entry in payload["brief_diagnostics"]
    }
    assert "MBRF004" in by_brief[seeded_store["orphan"]]
    assert "MBRF004" not in by_brief.get(seeded_store["approved"], set())


@requires_bd
def test_work_ready_uses_real_dependencies_and_verdict_metadata(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "work", "ready", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    work = json.loads(result.stdout)["work"]
    assert [item["brief_id"] for item in work] == [seeded_store["approved"]]
    assert work[0]["bead_id"] == seeded_store["approved_source"]


@requires_bd
def test_work_status_blocks_real_brief_without_approving_verdict(tmp_path: Path, seeded_store):
    city_root, _rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "work", "status", str(seeded_store["pending"]),
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    item = json.loads(result.stdout)["work"]
    assert item["readiness"] == "blocked"
    assert "MWRK010" in {blocker["code"] for blocker in item["blockers"]}


@requires_bd
def test_adjudicate_dry_run_leaves_the_real_bead_untouched(tmp_path: Path, seeded_store):
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    brief_id = str(seeded_store["pending"])
    before = bead_row(rig_root, brief_id)

    result = run_mctl(
        "briefs", "adjudicate", brief_id, "--verdict", "approve",
        "--reason", "dry run must not write", "--dry-run",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is False
    after = bead_row(rig_root, brief_id)
    assert after["status"] == before["status"]
    assert after.get("metadata") == before.get("metadata")


@requires_bd
def test_adjudicate_writes_verdict_through_bd_to_the_real_bead(tmp_path: Path, seeded_store):
    """The canonical write path: mctl -> bd update -> real bead store."""
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    brief_id = str(seeded_store["pending"])
    assert bead_row(rig_root, brief_id)["status"] == "open"

    result = run_mctl(
        "briefs", "adjudicate", brief_id, "--verdict", "approve",
        "--reason", "real bead write",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is True

    after = bead_row(rig_root, brief_id)
    assert after["status"] == "closed"
    metadata = after.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    assert metadata.get("verdict") == "approve"
    assert metadata.get("verdict_reason") == "real bead write"


@requires_bd
def test_unarmed_dispatch_is_inert_against_a_real_store(tmp_path: Path, seeded_store):
    """Without MCTL_ENABLE_LIVE_DISPATCH, dispatch must not sling or record."""
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_mctl(
        "work", "dispatch", str(seeded_store["approved"]),
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is False
    assert not (rig_root / ".beads" / "mctl" / "provenance").exists()


def all_bead_rows(rig_root: Path) -> list[dict[str, object]]:
    return json.loads(
        run_bd("list", "--all", "--limit", "0", "--json", "--readonly", cwd=rig_root).stdout
    )


def brief_body(tmp_path: Path) -> Path:
    path = tmp_path / "body.md"
    path.write_text(
        # #169: carries `## Gate Evidence` because briefs_create now refuses
        # without it. This fixture drives a REAL bd store, so a brief it mints
        # would have been a real brief the drain auto-rejects.
        "## What is being decided\n\nShip the dispatch policy?\n\n"
        "## Gate Evidence\n\nG5: n/a -- no server surface touched.\n",
        encoding="utf-8",
    )
    return path


@requires_bd
def test_create_dry_run_adds_no_bead_to_the_real_store(tmp_path: Path, seeded_store):
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    before = {row["id"] for row in all_bead_rows(rig_root)}

    result = run_mctl(
        "briefs", "create", "--title", "Decide dispatch policy",
        "--body-file", str(brief_body(tmp_path)),
        "--source", str(seeded_store["approved_source"]), "--dry-run",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is False
    assert {row["id"] for row in all_bead_rows(rig_root)} == before


@requires_bd
def test_create_writes_a_real_decision_bead_through_bd(tmp_path: Path, seeded_store):
    """The canonical creation path: mctl -> bd create -> real bead store.

    The MCTL_BEADS_FIXTURE seam cannot prove a write works; only bd can.
    """
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    before = {row["id"] for row in all_bead_rows(rig_root)}

    result = run_mctl(
        "briefs", "create", "--title", "Decide dispatch policy",
        "--body-file", str(brief_body(tmp_path)),
        "--source", str(seeded_store["approved_source"]),
        "--label", "brief-open", "--requested-by", "operator",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert payload["actual_effects"][0]["kind"] == "bead_create"

    new_id = str(payload["actual_effects"][0]["target"])
    assert new_id not in before, "bd must have minted a fresh bead id"
    row = bead_row(rig_root, new_id)
    assert row["issue_type"] == "decision"
    assert row["status"] == "open"
    assert "brief-open" in (row.get("labels") or [])

    # Redundant artifacts land only after bd accepted the canonical write.
    assert (rig_root / ".beads" / "briefs" / ".pile" / f"{new_id}.md").is_file()
    assert (rig_root / ".beads" / "briefs" / "decisions" / f"{new_id}.toml").is_file()


@requires_bd
def test_a_real_created_brief_passes_validation_and_doctor(tmp_path: Path, seeded_store):
    """Creation must not manufacture a brief its own invariants reject."""
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)

    created = run_mctl(
        "briefs", "create", "--title", "Decide dispatch policy",
        "--body-file", str(brief_body(tmp_path)),
        "--source", str(seeded_store["approved_source"]),
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )
    assert created.returncode == 0, created.stderr
    new_id = str(json.loads(created.stdout)["actual_effects"][0]["target"])

    validated = run_mctl(
        "briefs", "validate", new_id,
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert validated.returncode == 0, validated.stderr
    payload = json.loads(validated.stdout)
    assert payload["valid"] is True, payload["diagnostics"]
    # B2.1: bd recorded the source link, so the brief is not malformed.
    assert "MBRF004" not in {
        str(diagnostic["code"]) for diagnostic in payload["diagnostics"]
    }


# --- the cross-store edge hazard, against the real binary --------------------
#
# These pin the measurement the verified-relate design rests on. It is a claim
# about a binary this repository does not own, so it belongs in a test that
# runs the binary rather than in a comment that ages.


def run_bd_unchecked(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """`run_bd` asserts exit 0; these tests are about what the exit code says."""
    env = os.environ.copy()
    env["BD_NON_INTERACTIVE"] = "1"
    return subprocess.run(
        ["bd", *args], cwd=cwd, text=True, capture_output=True, check=False, env=env
    )


@requires_bd
def test_bd_dep_relate_refuses_an_id_this_store_cannot_resolve(tmp_path: Path, seeded_store):
    """`relate` does NOT share `dep add`'s silent-loss defect.

    Measured 2026-08-20 against bd 1.1.0 with two isolated stores. A foreign
    store's bead id behaves here exactly as an unknown id does, because
    resolution is per-store either way -- which is why one store is enough to
    pin the behaviour.
    """
    _city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)

    result = run_bd_unchecked(
        "dep", "relate", str(seeded_store["approved_source"]), "zz-not-in-this-store",
        cwd=rig_root,
    )

    assert result.returncode != 0, "relate must refuse, not silently drop the edge"
    assert "failed to resolve" in (result.stderr + result.stdout)


@requires_bd
def test_bd_dep_add_silently_records_an_edge_no_hydrating_read_returns(
    tmp_path: Path, seeded_store
):
    """The live defect, reproduced: exit 0, counted, and invisible.

    `bd show` reports it in `dependency_count` and omits it from
    `dependencies`; `bd dep list` returns nothing. Only the raw listing
    carries the row -- which is what makes `verify_relation` able to catch it.
    """
    _city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    local = str(seeded_store["approved_source"])

    added = run_bd_unchecked("dep", "add", local, "zz-not-in-this-store", "-t", "related", cwd=rig_root)

    assert added.returncode == 0, "the defect is precisely that this exits 0"
    shown = json.loads(run_bd("show", local, "--json", cwd=rig_root).stdout)
    shown = shown[0] if isinstance(shown, list) else shown
    hydrated = shown.get("dependencies") or []
    assert not any(entry.get("id") == "zz-not-in-this-store" for entry in hydrated)
    assert shown.get("dependency_count", 0) > len(hydrated), (
        "the count must claim an edge the hydrated list does not carry"
    )
    listed = json.loads(run_bd("dep", "list", local, "--json", cwd=rig_root).stdout)
    assert not any(entry.get("id") == "zz-not-in-this-store" for entry in listed)


@requires_bd
def test_verify_relation_catches_the_real_dangling_edge(tmp_path: Path, seeded_store):
    """The detection, proven against a real store rather than a fixture."""
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.beads import read_beads, verify_relation

    _city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    local = str(seeded_store["approved_source"])
    run_bd("dep", "add", local, "zz-not-in-this-store", "-t", "related", cwd=rig_root)

    beads = read_beads(rig_root)
    verification = verify_relation(beads, local, "zz-not-in-this-store")

    assert verification.edge_recorded is True, "the dangling row IS in the raw listing"
    assert verification.unresolved_endpoints == ("zz-not-in-this-store",)
    assert verification.verified is False
    # A real, resolvable edge in the same store still verifies, so the check
    # is discriminating rather than simply refusing everything.
    assert verify_relation(beads, str(seeded_store["approved"]), local).verified is True


@requires_bd
def test_dispatch_event_writes_a_verified_edge_in_a_real_store(tmp_path: Path, seeded_store):
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    source = str(seeded_store["approved_source"])

    result = run_mctl(
        "work", "dispatch-event", source,
        "--dispatch-command", f"gc sling mathcity/gc.run-operator {source} --on work-briefed",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    verified = [
        effect for effect in payload["actual_effects"] if effect["kind"] == "bead_relate_verified"
    ]
    assert verified and verified[0]["verified"] is True

    event_id = next(
        effect["target"] for effect in payload["actual_effects"] if effect["kind"] == "bead_create"
    )
    row = bead_row(rig_root, str(event_id))
    assert row["issue_type"] == "event"
    edges = {
        entry.get("depends_on_id")
        for entry in (row.get("dependencies") or [])
        if isinstance(entry, dict)
    }
    assert source in edges


@requires_bd
def test_dispatch_event_refuses_a_foreign_bead_id_against_a_real_store(
    tmp_path: Path, seeded_store
):
    """The precondition, not the verification: nothing is created at all."""
    city_root, rig_root = runtime_with_real_store(tmp_path, seeded_store)
    before = {
        row["id"]
        for row in json.loads(
            run_bd("list", "--all", "--limit", "0", "--json", "--readonly", cwd=rig_root).stdout
        )
    }

    result = run_mctl(
        "work", "dispatch-event", "zz-not-in-this-store",
        "--dispatch-command", "gc sling mathcity/gc.run-operator zz --on work-briefed",
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT,
    )

    assert result.returncode == 1
    assert "MWRK_BEAD_NOT_FOUND" in result.stderr
    after = {
        row["id"]
        for row in json.loads(
            run_bd("list", "--all", "--limit", "0", "--json", "--readonly", cwd=rig_root).stdout
        )
    }
    assert after == before, "a refused precondition must leave no orphan event bead"
