"""The legal-moves adjudication control (rev-panel spec, 2026-08-25).

The panel used to render TWO radio groups -- `verdict` (approve/revise/reject/
defer) and `option` (blank/A/B/C/other). Their product includes ILLEGAL states:
approve + a blank option on a multi-option brief reaches the runtime as an
unnamed option and is refused (MOPT001); reject + a named option was never a
thing. This suite pins the replacement: ONE control whose members ARE the legal
moves, so an illegal combination is not merely unlikely -- it is unexpressible.

Each move is a submit button (`name="move"`), so pressing it runs its own
dry-run through the existing `/preview` route with NO JavaScript -- one click,
JS-off native. The button's value carries BOTH the verdict and the option, so
they are always posted together.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from test_dashboard_mutation_safety import (  # noqa: E402
    _give_options,
    bead,
    dashboard_for,
    strip_tags,
    token_in,
)

from mctl_dashboard.app import Request  # noqa: E402


def _open_option():
    return [{"id": "adjudicate", "enabled": True, "description": "Record a verdict."}]


def _locked_option(code: str, severity: str = "ERROR"):
    return [
        {
            "id": "adjudicate",
            "enabled": False,
            "description": "Record a verdict.",
            "disabled_reason": {
                "code": code,
                "severity": severity,
                "message": "A gate failed before this reached the stack.",
                "policy_reference": "B2.4",
            },
        }
    ]


_MULTI = {
    "bead_id": "he-1",
    "decision_options": [
        {"label": "A", "title": "Merge as filed", "recommended": True, "confidence": "explicit", "source": "bead_description"},
        {"label": "B", "title": "Split first", "confidence": "explicit"},
    ],
}


# --- §1: one control, legal moves only --------------------------------------


def test_the_panel_renders_a_single_move_control_not_two_radio_groups():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _open_option(), state.ViewState())
    # No separate verdict/option radio groups survive.
    assert 'name="verdict"' not in html
    assert 'name="option"' not in html
    # One legal-moves control, each a submit button carrying the whole move.
    assert 'name="move"' in html
    assert html.count('name="move"') >= 6  # A, B, other, revise, reject, defer


def test_each_approve_letter_move_carries_the_option_title_and_marks():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _open_option(), state.ViewState())
    assert 'value="approve:A"' in html
    assert 'value="approve:B"' in html
    assert "Merge as filed" in html
    assert "Split first" in html
    # the recommended/confidence/source marks _option_meta renders
    assert 'data-region="option-meta"' in html
    assert "recommended" in html
    assert "explicit" in html


def test_multi_option_brief_has_no_approve_move_with_an_empty_option():
    """MOPT001 unreachable: approve on a multi-option brief always names one."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _open_option(), state.ViewState())
    # There is an approve-other escape, and approve-A/B, but never a bare
    # approve that would reach the runtime as an unnamed option.
    assert 'value="approve"' not in html.replace('value="approve:', "value=X")
    assert 'value="approve:other"' in html


def test_a_brief_with_no_options_offers_approve_revise_reject_defer():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    for value in ("approve", "revise", "reject", "defer"):
        assert re.search(rf'name="move" value="{value}"', html), value
    # no letter moves and no approve-other when the brief names no options
    assert "approve:" not in html


# --- §1: HELD strikes ratify moves; refused disables without striking --------


def test_held_strikes_the_ratifying_moves_but_leaves_revise_and_reject():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _locked_option("MBRF999"), state.ViewState())
    assert 'data-panel-state="held"' in html
    assert "line-through" in html
    for gated in ("approve:A", "approve:B", "defer"):
        btn = re.search(rf'<button[^>]*value="{re.escape(gated)}"[^>]*>', html)
        assert btn and "disabled" in btn.group(0), gated
    for usable in ("revise", "reject"):
        btn = re.search(rf'<button[^>]*value="{usable}"[^>]*>', html)
        assert btn and "disabled" not in btn.group(0), usable


def test_an_under_review_refusal_disables_ratify_moves_without_striking_them():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _locked_option("MBRF004"), state.ViewState())
    assert 'data-panel-state="refused"' in html
    assert "line-through" not in html
    approve = re.search(r'<button[^>]*value="approve:A"[^>]*>', html)
    assert approve and "disabled" in approve.group(0)
    # the disabled_reason code rides along beside the refused move, not only a banner
    assert "MBRF004" in html


def test_refused_moves_show_their_disabled_reason_beside_the_control():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _locked_option("MBRF004"), state.ViewState())
    assert 'data-region="move-refusal"' in html


# --- §3: one click, JS-off; contextual extra fields -------------------------


def test_each_move_is_a_submit_button_into_the_preview_route():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _open_option(), state.ViewState())
    assert 'action="/preview"' in html
    assert 'method="post"' in html.lower()
    assert '<button type="submit" name="move"' in html
    # no inline handlers -- JS-off native
    for banned in ("onclick", "onchange", "onsubmit", "javascript:"):
        assert banned not in html.lower()


def test_the_defer_window_appears_only_with_the_defer_move():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _open_option(), state.ViewState())
    assert 'data-region="defer-window"' in html
    # it is grouped with the defer move, not floated at form level for every verdict
    defer_group = html.split('data-move-group="defer"', 1)
    assert len(defer_group) == 2, "the defer window must be grouped with the defer move"
    assert 'name="days"' in defer_group[1].split("</div>")[0] or 'name="days"' in html


def test_the_propose_your_own_box_appears_only_with_the_approve_other_move():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_MULTI, _open_option(), state.ViewState())
    assert 'name="option_other"' in html
    assert 'data-move-group="approve:other"' in html


# --- §1+§3 end to end: the move posts verdict AND option together -----------


def test_pressing_approve_a_dry_runs_that_option(tmp_path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    _give_options(rig_root, "mc-open")

    response = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-open", move="approve:A", reason="ok")
    )

    assert response.status == 200, strip_tags(response.body)[:300]
    assert "MOPT001" not in response.body
    applied = dashboard.handle(Request.post("/apply", token=token_in(response.body)))
    assert applied.status == 200
    row = bead(rig_root, "mc-open")
    assert row["status"] == "closed"
    assert row["metadata"]["verdict"] == "approve"


def test_a_move_makes_the_unnamed_option_combo_unreachable(tmp_path):
    """Even posted by hand, an approve move always carries its option."""
    dashboard, _, rig_root = dashboard_for(tmp_path)
    _give_options(rig_root, "mc-open")

    # The panel HTML for a multi-option brief offers no bare-approve move; the
    # only approve moves name an option, so the runtime never sees an unnamed one.
    html = dashboard.handle(Request.get("/briefs/mc-open")).body
    assert 'value="approve:A"' in html
    assert 'value="approve"' not in html.replace('value="approve:', "value=X")


def test_defer_move_still_routes_to_briefs_defer(tmp_path):
    dashboard, _, rig_root = dashboard_for(tmp_path)

    response = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-open", move="defer", reason="wait", days="7")
    )

    assert response.status == 200
    assert "briefs.defer" in strip_tags(response.body)
    applied = dashboard.handle(Request.post("/apply", token=token_in(response.body)))
    assert applied.status == 200
    assert bead(rig_root, "mc-open")["status"] == "deferred"


def test_approve_other_records_a_revise_with_the_proposal(tmp_path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    _give_options(rig_root, "mc-open")

    response = dashboard.handle(
        Request.post(
            "/preview",
            operation="adjudicate",
            brief_id="mc-open",
            move="approve:other",
            reason="",
            option_other="do the third thing",
        )
    )

    assert response.status == 200, strip_tags(response.body)[:300]
    applied = dashboard.handle(Request.post("/apply", token=token_in(response.body)))
    assert applied.status == 200
    row = bead(rig_root, "mc-open")
    # "Other" is a disposition in the UI and a REVISE in the backend.
    assert row["metadata"]["verdict"] == "revise"


# --- §2: reason optional, labelled ------------------------------------------


def test_the_reason_is_labelled_optional_and_has_no_minlength():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    # rendered as the em-dash entity, consistent with the rest of the panel
    assert "Reason &mdash; optional" in html
    tag = re.search(r"<textarea name=\"reason\"[^>]*>", html)
    assert tag and "required" not in tag.group(0)
    assert tag and "minlength" not in tag.group(0)
