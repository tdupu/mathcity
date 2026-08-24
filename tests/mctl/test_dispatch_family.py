"""The work_dispatch DISPATCH-LAYER bug family: tdupu/mathcity #228, #212, #213.

These three share one subsystem and one root cause: the dispatch resolver and
its pre-sling safety checks read signals that the work-briefed execution path
NEVER writes on the source bead.

    #228  A multi-source brief re-slings its first source forever. The
          open-child-workflow check (MWRK002) keys on `gc.root_bead_id ==
          source`, but a REAL molecule ROOT carries `gc.var.source_bead` and
          its STEPS point at the run root -- never at the source. So the check
          is blind to every real molecule, the resolver never walks past a
          source already being worked, and P1.21 is violated.

    #212  The post-sling claim observer FATALs (MWRK003) when the source bead
          has no `assignee` -- but the claim lands as an open child molecule /
          `execution.work_associated`, never as a source assignee. Every
          successful live dispatch was reported as a fatal failure.

    #213  Because #212 FATALs before provenance is written, a retry re-slings
          and mints a SECOND synthetic input convoy instead of adopting the
          first.

The fixtures below model the REAL molecule/convoy shapes (from
`mctl_core.molecules`), not the hybrid shape the older MWRK002 test invented to
satisfy the blind predicate.
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

BRIEF = "mc-brief"
SOURCE_A = "mc-aaaa"
SOURCE_B = "mc-bbbb"


def _source(bead_id: str, *, status: str = "open", assignee: str | None = None) -> dict:
    row: dict = {
        "id": bead_id,
        "title": f"source {bead_id}",
        "status": status,
        "issue_type": "task",
        "labels": [],
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }
    if assignee is not None:
        row["assignee"] = assignee
    return row


def _brief(*source_ids: str) -> dict:
    return {
        "id": BRIEF,
        "title": "Approved multi-source work brief",
        "status": "closed",
        "issue_type": "decision",
        "labels": ["brief-closed"],
        "dependencies": [
            {"issue_id": BRIEF, "depends_on_id": sid, "type": "related"}
            for sid in source_ids
        ],
        "metadata": {"verdict": "approve"},
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }


def real_molecule_root(source_id: str, *, status: str = "in_progress") -> dict:
    """A molecule ROOT as `gc sling` actually mints it (mctl_core.molecules).

    gc.kind == "workflow", NO gc.root_bead_id, and the source it works is
    carried as the sling var `gc.var.source_bead`. The blind MWRK002 predicate
    (gc.root_bead_id == source) can never see this.
    """
    return {
        "id": f"mol-{source_id}",
        "title": "work-briefed",
        "status": status,
        "issue_type": "task",
        "labels": [],
        "metadata": {
            "gc.kind": "workflow",
            "gc.formula_name": "work-briefed",
            "gc.var.source_bead": source_id,
        },
        "created_at": "2026-08-24T08:30:00Z",
        "updated_at": "2026-08-24T08:33:00Z",
    }


def synthetic_input_convoy(source_id: str, *, cid: str = "mc-convoy", status: str = "open") -> dict:
    """An open synthetic input convoy depending on the source bead (#213)."""
    return {
        "id": cid,
        "title": f"input convoy for {source_id}",
        "status": status,
        "issue_type": "task",
        "labels": [],
        "metadata": {"gc.synthetic": True},
        "dependencies": [
            {"issue_id": cid, "depends_on_id": source_id, "type": "related"}
        ],
        "created_at": "2026-08-24T02:15:00Z",
        "updated_at": "2026-08-24T02:15:00Z",
    }


def runtime(
    tmp_path: Path,
    rows: list[dict],
    *,
    sling_assigns: bool = False,
    sling_mints_molecule: bool = False,
    sling_source: str = SOURCE_A,
):
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
    molecule_row = json.dumps(real_molecule_root(sling_source), sort_keys=True)
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "if sys.argv[1:2] == ['status']:\n"
        "    sys.stdout.write(json.dumps({'controller': {'running': True,\n"
        "        'status': 'ready'}, 'suspended': False})); sys.exit(0)\n"
        f"assign = {sling_assigns!r}\n"
        f"mint = {sling_mints_molecule!r}\n"
        f"path = {str(fixture)!r}\n"
        f"src = {sling_source!r}\n"
        f"molecule = {molecule_row!r}\n"
        "rows = [json.loads(l) for l in open(path).read().splitlines() if l.strip()]\n"
        "if assign:\n"
        "    for row in rows:\n"
        "        if row['id'] == src:\n"
        "            row['assignee'] = 'mathcity/gc.run-operator'\n"
        "if mint:\n"
        "    rows.append(json.loads(molecule))\n"
        "if assign or mint:\n"
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


def work_status(city_root: Path, bin_dir: Path, fixture: Path) -> dict:
    result = run_mctl(
        "work", "status", BRIEF, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir, fixture=fixture,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["work"]


def status_codes(city_root: Path, bin_dir: Path, fixture: Path) -> set[str]:
    return {b["code"] for b in work_status(city_root, bin_dir, fixture)["blockers"]}


def dispatch(city_root: Path, bin_dir: Path, fixture: Path):
    return run_mctl(
        "work", "dispatch", BRIEF, "--city", str(city_root), "--rig", "mathcity", "--json",
        bin_dir=bin_dir, fixture=fixture, arm=True,
    )


# --- #228: real-molecule detection --------------------------------------------

def test_mwrk002_fires_for_a_real_molecule_root(tmp_path: Path):
    """A real molecule working the source must be detected (#228 root cause).

    The molecule ROOT carries gc.var.source_bead, NOT gc.root_bead_id. The old
    predicate was blind to it, so a source already being worked read as
    dispatchable and got re-slung.
    """
    rows = [_brief(SOURCE_A), _source(SOURCE_A), real_molecule_root(SOURCE_A)]
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

    assert "MWRK002" in status_codes(city_root, bin_dir, fixture)


# --- #228: multi-source walk --------------------------------------------------

def test_multi_source_walks_past_a_source_being_worked(tmp_path: Path):
    """Source A is being worked (real molecule); the resolver must select B."""
    rows = [_brief(SOURCE_A, SOURCE_B), _source(SOURCE_A), _source(SOURCE_B),
            real_molecule_root(SOURCE_A)]
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

    item = work_status(city_root, bin_dir, fixture)
    assert item["bead_id"] == SOURCE_B, item
    assert item["readiness"] == "ready", item
    # The skip past A is named in the response.
    assert SOURCE_A in json.dumps(item.get("skipped_sources", []))


def test_multi_source_all_in_flight_refuses(tmp_path: Path):
    """When every source is already being worked, re-dispatch is refused."""
    rows = [_brief(SOURCE_A, SOURCE_B), _source(SOURCE_A), _source(SOURCE_B),
            real_molecule_root(SOURCE_A), real_molecule_root(SOURCE_B)]
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

    item = work_status(city_root, bin_dir, fixture)
    assert item["readiness"] != "ready", item
    assert "MWRK002" in {b["code"] for b in item["blockers"]}


# --- #213: synthetic convoy detection -----------------------------------------

def test_open_synthetic_input_convoy_blocks_redispatch(tmp_path: Path):
    """An open synthetic input convoy on the source means work is in flight."""
    rows = [_brief(SOURCE_A), _source(SOURCE_A), synthetic_input_convoy(SOURCE_A)]
    city_root, _rig, bin_dir, fixture = runtime(tmp_path, rows)

    assert "MWRK002" in status_codes(city_root, bin_dir, fixture)


# --- #212: claim observer is not fatal ----------------------------------------

def test_dispatch_that_mints_a_molecule_succeeds(tmp_path: Path):
    """The claim lands as a molecule, not a source assignee. That is success."""
    rows = [_brief(SOURCE_A), _source(SOURCE_A)]
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, rows, sling_assigns=False, sling_mints_molecule=True
    )

    result = dispatch(city_root, bin_dir, fixture)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert payload.get("claim") == "observed", payload


def test_dispatch_with_unobserved_claim_is_pending_not_fatal(tmp_path: Path):
    """Exit-0 sling with no observable claim yet: succeeded, claim pending."""
    rows = [_brief(SOURCE_A), _source(SOURCE_A)]
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, rows, sling_assigns=False, sling_mints_molecule=False
    )

    result = dispatch(city_root, bin_dir, fixture)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert payload.get("claim") == "pending", payload
    codes = {d["code"] for d in payload.get("diagnostics", [])}
    assert "MWRK003" in codes, payload
    severities = {d["code"]: d["severity"] for d in payload.get("diagnostics", [])}
    assert severities.get("MWRK003") == "WARN", severities


# --- #213: retry adopts instead of re-slinging --------------------------------

def test_retry_after_successful_dispatch_is_refused(tmp_path: Path):
    """A second dispatch must not re-sling and mint a second convoy (#213).

    The first exit-0 sling writes provenance AND mints a molecule, so the retry
    is REFUSED rather than minting a duplicate input convoy -- whether the
    refusal is reported as already-dispatched or as the open molecule blocking
    it (MWRK002), the invariant is that `gc sling` is not invoked a second time.
    """
    rows = [_brief(SOURCE_A), _source(SOURCE_A)]
    city_root, _rig, bin_dir, fixture = runtime(
        tmp_path, rows, sling_assigns=False, sling_mints_molecule=True
    )

    first = dispatch(city_root, bin_dir, fixture)
    assert first.returncode == 0, first.stderr

    second = dispatch(city_root, bin_dir, fixture)
    assert second.returncode != 0
    assert any(
        code in second.stderr
        for code in ("MWRK_ALREADY_DISPATCHED", "MWRK_DISPATCH_BLOCKED", "MWRK002")
    ), second.stderr
