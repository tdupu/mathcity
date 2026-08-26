"""mc-ilia: the typed surface can correct its own records, append-only.

The write surface was create-only -- nothing attached a note to an existing
bead -- so a record filed on a premise later refuted (mc-8ij1) stayed wrong
permanently, and the correction had to become a whole second bead (mc-5ir2).
`bead_comment` closes that: it appends a comment to an existing bead and NEVER
edits the description, so what was believed and when stays readable beside the
correction (P1.19 append-don't-edit / P5.4). It wraps `bd comment`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server
from mctl_core.schemas import schema_errors

from test_mcp_server import CITY_ROOT, SOURCE_CHECKOUT, call, tree_digest


def rig_with_bead(tmp_path: Path, row: str) -> tuple[Path, Path]:
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
    (beads / "issues.jsonl").write_text(row, encoding="utf-8")
    return city_root, rig_root


def server(city_root: Path, rig_root: Path):
    environment = {"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")}
    return mcp_server.MctlMcpServer(
        default_city=city_root, default_rig="mathcity", client_class="internal", env=environment
    )


ROW = (
    '{"id": "mc-8ij1", "title": "the /city route is broken", "status": "open", '
    '"issue_type": "task", "description": "The dashboard /city route is specifically '
    'broken while /briefs is healthy."}\n'
)


def _output_schema(name: str) -> dict:
    return next(t for t in mcp_server.TOOLS if t.name == name).output_schema


def test_plans_a_comment_on_an_existing_bead(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)

    structured = call(
        server(city_root, rig_root),
        "bead_comment",
        {"bead_id": "mc-8ij1",
         "comment": "Superseded in part by mc-dpe7: both routes swing 10-30x.",
         "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    comments = structured["effect_plan"]["bead_comments"]
    assert len(comments) == 1
    assert comments[0]["bead_id"] == "mc-8ij1"
    assert "mc-dpe7" in comments[0]["text"]
    # append-only: this plan touches no bead_updates and no bead_creates
    assert structured["effect_plan"]["bead_updates"] == []
    assert structured["effect_plan"]["bead_creates"] == []


def test_apply_appends_a_comment_and_never_edits_the_description(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)

    structured = call(
        server(city_root, rig_root),
        "bead_comment",
        {"bead_id": "mc-8ij1", "comment": "Refuted; see mc-dpe7.", "dry_run": False},
    )["result"]["structuredContent"]

    assert structured["applied"] is True
    import json
    rows = [json.loads(line) for line in
            (rig_root / ".beads" / "issues.jsonl").read_text().splitlines() if line.strip()]
    bead = next(r for r in rows if r["id"] == "mc-8ij1")
    # the original description is byte-for-byte intact
    assert bead["description"] == (
        "The dashboard /city route is specifically broken while /briefs is healthy."
    )
    # and the comment is recorded, append-only
    assert any("mc-dpe7" in str(c.get("text", "")) for c in bead.get("comments", []))


def test_dry_run_touches_nothing(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)
    before = tree_digest(rig_root)

    call(server(city_root, rig_root), "bead_comment",
         {"bead_id": "mc-8ij1", "comment": "note", "dry_run": True})

    assert tree_digest(rig_root) == before


def test_refuses_a_comment_on_a_nonexistent_bead(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)

    result = call(server(city_root, rig_root), "bead_comment",
                  {"bead_id": "mc-nope", "comment": "note", "dry_run": True})["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MBCM_NO_SUCH_BEAD" in codes


def test_refuses_an_empty_comment(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)

    result = call(server(city_root, rig_root), "bead_comment",
                  {"bead_id": "mc-8ij1", "comment": "   ", "dry_run": True})["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MBCM_EMPTY_COMMENT" in codes


def test_served_response_satisfies_declared_schema(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)

    structured = call(server(city_root, rig_root), "bead_comment",
                      {"bead_id": "mc-8ij1", "comment": "note", "dry_run": True})[
        "result"]["structuredContent"]

    assert schema_errors(structured, _output_schema("bead_comment")) == []
