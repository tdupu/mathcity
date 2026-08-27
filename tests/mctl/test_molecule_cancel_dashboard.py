"""The dashboard control for the typed molecule cancel (mc-x06e).

Two layers: the screen renders the cancel control only when the molecule reports
it permitted (the root is still running), and the `/preview` route drives it
through the ordinary preview/apply guard rails -- operation token, typed
arguments, dry-run effect plan -- exactly as every other mutation does.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_dashboard.app import Dashboard, Request  # noqa: E402
from mctl_dashboard.client import InProcessMcpClient  # noqa: E402
from mctl_dashboard.screens import molecules as molecules_screen  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"


# --- screen-level: the gated control ---------------------------------------


def test_a_running_molecule_shows_the_cancel_control():
    payload = {"molecules": [{"id": "mc-root", "status": "in_progress",
                              "is_cancellable": True, "steps": []}]}
    html = molecules_screen.molecule_detail(payload, rig="mathcity")
    assert 'data-region="molecule-cancel"' in html
    assert 'name="operation" value="molecule_cancel"' in html
    assert 'value="mc-root"' in html
    assert 'name="rig" value="mathcity"' in html


def test_a_finished_molecule_shows_no_cancel_control():
    payload = {"molecules": [{"id": "mc-root", "status": "closed",
                              "is_cancellable": False, "steps": []}]}
    html = molecules_screen.molecule_detail(payload, rig="mathcity")
    assert 'data-region="molecule-cancel-unavailable"' in html
    assert 'name="operation" value="molecule_cancel"' not in html, (
        "a finished molecule must not offer a control that could only refuse"
    )


# --- route-level: preview through the real in-process tool ------------------


def _molecule_city(tmp_path: Path):
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    issues = rig_root / ".beads" / "issues.jsonl"
    shutil.copy2(BRIEF_STATE / "beads.jsonl", issues)
    molecule_rows = [
        {"id": "mc-mol", "title": "build-basic-briefed", "status": "in_progress",
         "issue_type": "task", "labels": [], "dependencies": [],
         "created_at": "2026-08-27T00:00:00Z", "updated_at": "2026-08-27T00:00:00Z",
         "metadata": {"gc.kind": "workflow", "gc.formula_name": "build-basic-briefed"}},
        {"id": "mc-step", "title": "Implement", "status": "open",
         "issue_type": "task", "labels": [], "dependencies": [],
         "created_at": "2026-08-27T00:00:00Z", "updated_at": "2026-08-27T00:00:00Z",
         "metadata": {"gc.root_bead_id": "mc-mol"}},
    ]
    with issues.open("a", encoding="utf-8") as handle:
        for row in molecule_rows:
            handle.write(json.dumps(row) + "\n")
    client = InProcessMcpClient(
        city=city_root, rig="mathcity",
        env={"MCTL_BEADS_FIXTURE": str(issues)},
    )
    return Dashboard(client, rig="mathcity")


def test_the_molecule_detail_route_renders_the_cancel_control(tmp_path):
    dash = _molecule_city(tmp_path)
    html = dash.handle(Request.get("/molecules/mc-mol")).body
    assert 'data-region="molecule-cancel"' in html
    assert "mc-mol" in html


def test_preview_drives_molecule_cancel_and_plans_to_close_the_run(tmp_path):
    dash = _molecule_city(tmp_path)
    response = dash.handle(
        Request.post(
            "/preview",
            operation="molecule_cancel",
            root_bead_id="mc-mol",
            rig="mathcity",
            reason="superseded",
        )
    )
    assert response.status == 200, response.body[:400]
    body = response.body
    # A dry-run preview that plans to close BOTH the open step and the root.
    assert "mc-step" in body
    assert "mc-mol" in body
    assert "closed" in body
    # Preview only -- the confirm control is offered, nothing was applied.
    assert "molecule cancel" in body.lower()
