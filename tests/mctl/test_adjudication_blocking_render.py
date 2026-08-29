"""mc-x8uox: a blocked dispatch button is DISABLED with its reason VISIBLE at render.

The defect: the brief page renders the "Dispatch work" button ENABLED even when
`work_dispatch` will refuse it, because the button's only readiness signal was
`briefs_options`, which never consults the SOURCE bead's status. A brief that is
approved-for-dispatch but whose source bead is CLOSED (MWRK013) therefore shows a
live-looking button; the refusal is discovered only on the second step, the
`/preview` click. That makes "blocked" indistinguishable from "ready" until you
act.

The rule (NON-NEGOTIABLE 2, disable-and-explain, never hide): a blocked button
renders DISABLED with the refusal code/reason right there. The reader learns the
move is unavailable, and why, without leaving the page. The button is never
omitted.

These tests drive the real render (`GET /briefs/<id>`) through the in-process
MCP client and assert on the rendered dispatch form, both blocked and the
enabled control.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from test_dashboard_mutation_safety import beads, dashboard_for, write_beads  # noqa: E402

from mctl_dashboard.app import Request  # noqa: E402


def _with_source(rig_root: Path, status: str) -> None:
    """Give the fixture briefs a real `mc-source` bead in the named status."""
    rows = [row for row in beads(rig_root) if row["id"] != "mc-source"]
    rows.append({"id": "mc-source", "title": "Source bead", "status": status, "issue_type": "task"})
    write_beads(rig_root, rows)


def _dispatch_form(html: str) -> str:
    """The one <form> whose operation is dispatch, isolated from the page."""
    forms = re.split(r"(?=<form\b)", html)
    for form in forms:
        if 'name="operation" value="dispatch"' in form:
            return form
    raise AssertionError("the brief page rendered no dispatch form at all")


def _dispatch_button(fragment: str) -> str:
    match = re.search(r"<button\b[^>]*>", fragment)
    assert match, "the dispatch form rendered no button"
    return match.group(0)


def test_a_dispatch_blocked_by_a_closed_source_renders_disabled_with_its_reason(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    # mc-adjudicated is closed + approve, so briefs_options reports dispatch-work
    # ENABLED; its source bead is closed, so work_dispatch refuses with MWRK013.
    _with_source(rig_root, "closed")

    html = dashboard.handle(Request.get("/briefs/mc-adjudicated")).body
    form = _dispatch_form(html)
    button = _dispatch_button(form)

    # The button is still rendered (never hidden) -- but disabled.
    assert "disabled" in button, "a blocked dispatch button must render DISABLED, not enabled"
    # And the refusal is visible right at the control, code and all.
    assert "MWRK013" in form, "the refusal code the operator would only see after clicking is hidden"


def test_a_ready_dispatch_renders_an_enabled_button(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    # Same approved brief, but now the source bead is open: dispatch is ready.
    _with_source(rig_root, "open")

    html = dashboard.handle(Request.get("/briefs/mc-adjudicated")).body
    form = _dispatch_form(html)
    button = _dispatch_button(form)

    assert "disabled" not in button, "a ready dispatch button must be enabled"
    assert "MWRK013" not in form
