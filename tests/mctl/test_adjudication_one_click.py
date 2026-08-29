"""mc-pf5pm: a verdict is ONE submit, and the re-plan guard is still atomic.

The panel used to take two clicks to record a verdict: press the move (a dry-run
`/preview` that renders the effect plan and a second "Apply this adjudication"
button), then press that button (`/apply`). Taylor's spec is one legible, honest
click. So a move submission now folds the preview and the apply into a single
request: it dry-runs, then runs the SAME guarded apply -- re-plan (`dry_run:True`),
abort if the state moved, then write (`dry_run:False`).

NON-NEGOTIABLE: the re-plan guard is preserved, not deleted. A weakened
write-path guard is the mc-jj7xg verdict_reason-corruption class. The guard test
below drives the two-step `/apply` route directly and asserts the abort-if-moved
path still fires; the negative control confirms an unchanged state applies.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from test_dashboard_mutation_safety import (  # noqa: E402
    bead,
    beads,
    dashboard_for,
    strip_tags,
    token_in,
    write_beads,
)

from mctl_dashboard.app import Request  # noqa: E402


def test_a_move_submission_records_the_verdict_in_one_click(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    assert bead(rig_root, "mc-open")["status"] == "open"

    # ONE submit: the move button posts to /preview and the verdict is recorded.
    response = dashboard.handle(
        Request.post(
            "/preview",
            operation="adjudicate",
            brief_id="mc-open",
            move="approve",
            reason="ready to ship",
        )
    )

    text = strip_tags(response.body)
    assert response.status == 200, text
    # It landed on the applied page, not a preview asking for a second click.
    assert "Applied" in text
    assert 'action="/apply"' not in response.body, "no separate apply step should remain"
    assert 'name="token"' not in response.body, "no confirm token second-click should be offered"
    # And the bead actually moved.
    row = bead(rig_root, "mc-open")
    assert row["status"] == "closed"
    assert row["metadata"]["verdict"] == "approve"


def test_the_one_click_path_still_runs_the_replan_guard(tmp_path: Path):
    """The single submit runs the guarded apply, so a move that fails the re-plan
    at confirm time aborts. Exercised on the /apply route the guard lives on."""
    dashboard, _, rig_root = dashboard_for(tmp_path)
    # A stale two-step: preview, then move the brief underneath, then confirm.
    token = token_in(
        dashboard.handle(
            Request.post(
                "/preview",
                operation="adjudicate",
                brief_id="mc-open",
                verdict="approve",
                reason="ready to ship",
            )
        ).body
    )
    rows = beads(rig_root)
    for row in rows:
        if row["id"] == "mc-open":
            row["title"] = "Retitled by another operator"
    write_beads(rig_root, rows)

    response = dashboard.handle(Request.post("/apply", token=token))

    assert response.status == 409, "a state that moved between plan and apply must abort"
    assert "MCTL_DASH_PREVIEW_STALE" in strip_tags(response.body)
    assert bead(rig_root, "mc-open")["status"] == "open", "nothing may be written once stale"


def test_an_unchanged_state_applies_cleanly(tmp_path: Path):
    """Negative control: the guard does not spuriously abort a still-fresh plan."""
    dashboard, _, rig_root = dashboard_for(tmp_path)
    token = token_in(
        dashboard.handle(
            Request.post(
                "/preview",
                operation="adjudicate",
                brief_id="mc-open",
                verdict="approve",
                reason="ready to ship",
            )
        ).body
    )

    response = dashboard.handle(Request.post("/apply", token=token))

    assert response.status == 200
    assert bead(rig_root, "mc-open")["status"] == "closed"
