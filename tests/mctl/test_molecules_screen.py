"""#115 / #153 -- molecules must be ON A PAGE, not merely computable.

Rule 1 of the city-dashboard recovery: a slice does not close until something
renders. `molecules_list`/`molecules_show` were registered MCP tools reachable
from no page (`grep -rn molecules assets/scripts/mctl_dashboard/` found only
the client allowlist) before this route existed. These tests assert the page,
not the tool -- and specifically that the honesty invariants #115 exists to
protect survive all the way to the rendered HTML: a step with no declaration
must render `unknown`, and an unrecorded evidence link must render as "no
recorder", never as a cross or the word "broken".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import multi_rig  # noqa: E402
from mctl_dashboard.app import Dashboard, Request  # noqa: E402
from mctl_dashboard.client import InProcessMcpClient  # noqa: E402


ROOT_ID = "mc-molroot1"


def _bead_row(bead_id, title, status, issue_type, metadata):
    return {
        "id": bead_id,
        "title": title,
        "status": status,
        "issue_type": issue_type,
        "labels": [],
        "created_at": "2026-08-05T17:35:17Z",
        "updated_at": "2026-08-05T17:35:36Z",
        "metadata": metadata,
    }


def _molecule_fixture(tmp_path: Path) -> Path:
    """One molecule root with three steps: unknown (no declaration),
    complete (declared and satisfied), incomplete (declared, one missing)."""
    beads = [
        _bead_row(
            ROOT_ID,
            "build-basic-briefed",
            "open",
            "task",
            {"gc.kind": "workflow", "gc.formula_name": "build-basic-briefed"},
        ),
        _bead_row(
            "mc-molstep-unknown",
            "Dispatch step",
            "open",
            "task",
            {"gc.kind": "workflow-finalize", "gc.root_bead_id": ROOT_ID},
        ),
        _bead_row(
            "mc-molstep-complete",
            "Submit to pile",
            "closed",
            "task",
            {
                "gc.kind": "workflow-finalize",
                "gc.root_bead_id": ROOT_ID,
                "gc.expected_artifacts.v1": '["/city/.pile/brief.md"]',
                "gc.build.pile": "/city/.pile/brief.md",
            },
        ),
        _bead_row(
            "mc-molstep-incomplete",
            "Initialize staging",
            "open",
            "task",
            {
                "gc.kind": "workflow-finalize",
                "gc.root_bead_id": ROOT_ID,
                "gc.expected_artifacts.v1": '["/city/.staging/brief.md"]',
            },
        ),
        # CLOSED with a declared artifact that was never produced -- the ONE
        # genuine, checkable break `broken_at` may name (#115 review fix):
        # completion self-reported without producing the declared output.
        _bead_row(
            "mc-molstep-broken",
            "Finalize without output",
            "closed",
            "task",
            {
                "gc.kind": "workflow-finalize",
                "gc.root_bead_id": ROOT_ID,
                "gc.expected_artifacts.v1": '["/city/.pile/never-written.md"]',
            },
        ),
    ]
    path = tmp_path / "molecules.jsonl"
    path.write_text("\n".join(json.dumps(b) for b in beads) + "\n", encoding="utf-8")
    return path


def rig_dashboard(tmp_path: Path, rig: str = "mathcity"):
    fixture = multi_rig.build(tmp_path)
    fixture.env[f"MCTL_BEADS_FIXTURE_{rig}"] = str(_molecule_fixture(tmp_path))
    client = InProcessMcpClient(city=fixture.city_root, rig=rig, env=fixture.env)
    client.server.cwd = fixture.city_root
    return Dashboard(client, city_wide=False, rig=rig)


def _step_block(html: str, step_id: str) -> str:
    """The rendered HTML for exactly one step's `<section>`.

    The detail page renders every step in one document, and one fixture step
    (`mc-molstep-broken`) is DELIBERATELY the one genuine break -- so a test
    asserting another step's section has no break must not read the whole
    page, or the broken step's own "Break: artifact" text would poison it.
    """
    marker = '<section class="panel" data-region="molecule-step">'
    for part in html.split(marker)[1:]:
        if step_id in part.split("</h3>")[0]:
            return part
    raise AssertionError(f"step {step_id!r} not found in the rendered page")


def test_the_molecules_page_renders_the_root(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get("/molecules")).body
    assert ROOT_ID in html
    assert "build-basic-briefed" in html


def test_the_molecules_page_links_to_the_detail_page(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get("/molecules")).body
    assert f"/molecules/{ROOT_ID}" in html


def test_a_step_with_no_declaration_renders_unknown_on_the_detail_page(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    assert "mc-molstep-unknown" in html
    assert "unknown" in html.lower()


def test_a_satisfied_declaration_renders_complete(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    assert "mc-molstep-complete" in html
    assert "complete" in html.lower()
    # And the declared artifact path itself is shown, marked present.
    assert "/city/.pile/brief.md" in html
    assert "present" in html.lower()


def test_a_missing_declared_artifact_renders_incomplete_and_names_it(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    assert "mc-molstep-incomplete" in html
    assert "incomplete" in html.lower()
    assert "/city/.staging/brief.md" in html
    assert "missing" in html.lower()


def test_unrecorded_evidence_links_render_as_no_recorder_not_broken(tmp_path):
    """The honesty invariant, all the way to the pixel: `claimed`,
    `agent_active` and `commit` have no emitter. The page must never call
    them broken, and must never use a cross mark for them."""
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    low = html.lower()
    assert "no recorder" in low
    assert "claimed" in low and "agent_active" in low and "commit" in low
    # broken_at must never name one of the three unrecorded links.
    assert "break: <span class=\"mono\">claimed</span>" not in low
    assert "break: <span class=\"mono\">agent_active</span>" not in low
    assert "break: <span class=\"mono\">commit</span>" not in low


def test_the_page_never_renders_a_bare_cross_for_an_unrecorded_link(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    assert "✕" not in html and "&cross;" not in html


def test_an_open_step_with_a_pending_artifact_reports_no_break(tmp_path):
    """`mc-molstep-incomplete` is OPEN (still advancing) with a declared
    artifact not yet produced. That must NOT render as a break -- an
    unreached link on a healthy, in-flight molecule renders as 'not yet',
    never as a finding (the exact positional-blame defect #115 exists to
    prevent, caught in review before this landed). Scoped to this step's own
    section: the page also renders a genuinely broken step elsewhere."""
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    block = _step_block(html, "mc-molstep-incomplete")
    assert "break:" not in block.lower()
    assert "no checkable break" in block.lower()


def test_the_page_names_the_genuine_break_a_closed_step_with_a_missing_artifact(tmp_path):
    """`mc-molstep-broken` is CLOSED but its declared artifact was never
    produced -- the ONE checkable break: completion self-reported without
    the declared output. The page must name it."""
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get(f"/molecules/{ROOT_ID}")).body
    block = _step_block(html, "mc-molstep-broken")
    assert 'Break: <span class="mono">artifact</span>' in block


def test_an_unknown_molecule_id_renders_a_named_reason_not_a_blank_page(tmp_path):
    dash = rig_dashboard(tmp_path)
    html = dash.handle(Request.get("/molecules/mc-does-not-exist")).body
    assert "not found" in html.lower() or "no such" in html.lower()
