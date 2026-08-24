"""#185: mint a defect bead with NO GitHub issue required.

`create_issue_bead` needs an issue to already exist. `create_defect_bead` is the
"not conversely" case of the owner's rule -- *"all github issues paired with a
bead, but not conversely"*: a Mayor that finds a defect can record it as a bead
even when no issue has been filed yet. The minted bead is an OPEN task carrying
`metadata.defect_report=true` and NO `gh.issue` key.

Task 2 also EXTRACTS the label->priority mapper `create_issue_bead` already uses
(#206) to a shared location so both tools honour a `priority/pN` label instead of
flattening every defect to bd's default priority.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server
from mctl_core.beads import priority_from_labels
from mctl_core.schemas import schema_errors

from test_mcp_server import CITY_ROOT, SOURCE_CHECKOUT, call, tree_digest


def empty_rig_fixture(tmp_path: Path) -> tuple[Path, Path]:
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
    (beads / "issues.jsonl").write_text("", encoding="utf-8")
    return city_root, rig_root


def server(city_root: Path, rig_root: Path):
    environment = {"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")}
    return mcp_server.MctlMcpServer(
        default_city=city_root, default_rig="mathcity", client_class="internal", env=environment
    )


# --- the shared mapper, extracted (#206) -------------------------------------


def test_priority_from_labels_maps_pN_to_bd_priority():
    assert priority_from_labels(("priority/p1",)) == 1
    assert priority_from_labels(("kind/bug", "priority/p3")) == 3
    assert priority_from_labels(("priority/p3", "priority/p0")) == 0  # most severe wins
    assert priority_from_labels(("kind/bug",)) is None  # absent stays unset


def test_create_issue_bead_still_maps_priority_after_extraction(tmp_path, monkeypatch):
    """Regression pin: the extraction must not un-fix #206's p1->P1 mapping."""
    from mctl_core import effects
    from mctl_core.github_issues import IssueSnapshot

    city_root, rig_root = empty_rig_fixture(tmp_path)
    issue = IssueSnapshot(
        repo="tdupu/mathcity",
        number=98,
        title="a p1 defect",
        body="body",
        labels=("kind/bug", "priority/p1"),
        state="OPEN",
        url="https://github.com/tdupu/mathcity/issues/98",
    )
    monkeypatch.setattr(effects, "fetch_issue", lambda *a, **k: issue)

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 98, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["effect_plan"]["bead_creates"][0]["priority"] == 1


# --- the mint --------------------------------------------------------------


def test_mints_open_task_bead_flagged_defect_with_no_gh_issue_key(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)

    structured = call(
        server(city_root, rig_root),
        "create_defect_bead",
        {
            "title": "orders_status FATALs on every call",
            "body": "The declared schema and the handler have drifted.",
            "labels": ["priority/p1"],
            "dry_run": True,
        },
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    create = structured["effect_plan"]["bead_creates"][0]
    assert create["issue_type"] == "task"
    assert create["metadata"]["defect_report"] == "true"
    assert "gh.issue" not in create["metadata"], "a defect bead has no paired issue yet"
    assert create["priority"] == 1
    assert create["labels"] == [], "priority/pN is a slash label bd rejects; it maps, not lands"


def test_dry_run_touches_nothing(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    before = tree_digest(rig_root)

    call(
        server(city_root, rig_root),
        "create_defect_bead",
        {"title": "x", "body": "y", "dry_run": True},
    )

    assert tree_digest(rig_root) == before


def test_a_defect_without_a_priority_label_leaves_priority_unset(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)

    structured = call(
        server(city_root, rig_root),
        "create_defect_bead",
        {"title": "x", "body": "y", "dry_run": True},
    )["result"]["structuredContent"]

    assert "priority" not in structured["effect_plan"]["bead_creates"][0]


# --- refuse orphan duplicates at scale (§4) ---------------------------------


def test_refuses_to_mint_a_duplicate_open_defect(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    beads_path = rig_root / ".beads" / "issues.jsonl"
    beads_path.write_text(
        '{"id": "mc-dup", "title": "orders_status FATALs on every call", "status": "open", '
        '"issue_type": "task", "metadata": {"defect_report": "true"}}\n',
        encoding="utf-8",
    )

    result = call(
        server(city_root, rig_root),
        "create_defect_bead",
        {"title": "orders_status FATALs on every call", "body": "y", "dry_run": True},
    )["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MGHW_DUPLICATE_DEFECT" in codes


def test_a_closed_defect_of_the_same_title_does_not_block(tmp_path):
    """A resolved defect must not stop a new one; only an OPEN duplicate does."""
    city_root, rig_root = empty_rig_fixture(tmp_path)
    beads_path = rig_root / ".beads" / "issues.jsonl"
    beads_path.write_text(
        '{"id": "mc-old", "title": "recurring defect", "status": "closed", '
        '"issue_type": "task", "metadata": {"defect_report": "true"}}\n',
        encoding="utf-8",
    )

    structured = call(
        server(city_root, rig_root),
        "create_defect_bead",
        {"title": "recurring defect", "body": "y", "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["effect_plan"]["bead_creates"], "a closed duplicate must not block"


# --- #203 served-schema pattern ---------------------------------------------


def _output_schema(name: str) -> dict:
    return next(t for t in mcp_server.TOOLS if t.name == name).output_schema


def test_served_success_response_satisfies_declared_schema(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)

    structured = call(
        server(city_root, rig_root),
        "create_defect_bead",
        {"title": "x", "body": "y", "dry_run": True},
    )["result"]["structuredContent"]

    assert schema_errors(structured, _output_schema("create_defect_bead")) == []
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in structured["diagnostics"]
    )


def test_served_refusal_carries_typed_diagnostic_objects(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    beads_path = rig_root / ".beads" / "issues.jsonl"
    beads_path.write_text(
        '{"id": "mc-dup", "title": "dupe", "status": "open", "issue_type": "task", '
        '"metadata": {"defect_report": "true"}}\n',
        encoding="utf-8",
    )

    structured = call(
        server(city_root, rig_root),
        "create_defect_bead",
        {"title": "dupe", "body": "y", "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["diagnostics"]
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in structured["diagnostics"]
    )
