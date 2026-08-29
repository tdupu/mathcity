"""mc-p0wps: the three bead-write verbs over the MCP surface, end to end.

The plan-level tests pin the builders; these prove the thin handlers wire the
arguments through and that a dry run previews with NO side effect (#188): the
fixture store is byte-identical before and after.
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
    '{"id": "mc-b1", "title": "a plain open task", "status": "open", '
    '"issue_type": "task"}\n'
)


def test_bead_close_previews_a_close(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)
    before = tree_digest(rig_root / ".beads")
    structured = call(
        server(city_root, rig_root),
        "bead_close",
        {"bead_id": "mc-b1", "reason": "done with it", "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    updates = structured["effect_plan"]["bead_updates"]
    assert len(updates) == 1
    assert updates[0]["id"] == "mc-b1"
    assert updates[0]["status"] == "closed"
    assert updates[0]["if_status"] == "open"
    assert tree_digest(rig_root / ".beads") == before, "a dry run must not mutate"


def test_bead_hold_previews_a_label_add(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)
    structured = call(
        server(city_root, rig_root),
        "bead_hold",
        {"bead_id": "mc-b1", "label": "hold:soak", "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    changes = structured["effect_plan"]["bead_label_changes"]
    assert changes == [{"bead_id": "mc-b1", "label": "hold:soak", "action": "add"}]


def test_bead_release_previews_a_label_remove(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)
    structured = call(
        server(city_root, rig_root),
        "bead_release",
        {"bead_id": "mc-b1", "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    changes = structured["effect_plan"]["bead_label_changes"]
    assert changes == [{"bead_id": "mc-b1", "label": "hold", "action": "remove"}]


def test_bead_close_refusal_is_a_typed_error_not_a_crash(tmp_path):
    city_root, rig_root = rig_with_bead(tmp_path, ROW)
    response = call(
        server(city_root, rig_root),
        "bead_close",
        {"bead_id": "mc-nope", "dry_run": True},
    )["result"]
    assert response["isError"] is True, "a refusal is a typed error, not a crash"
    diagnostics = response["structuredContent"]["diagnostics"]
    # A precondition surfaces wrapped (like molecule_cancel): the top code is
    # MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS and the refusal's own code rides in
    # `facts.blocking_code`.
    blocking = [d.get("facts", {}).get("blocking_code") for d in diagnostics]
    assert "MBCL_NO_SUCH_BEAD" in blocking
