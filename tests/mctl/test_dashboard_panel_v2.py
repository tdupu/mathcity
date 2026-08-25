"""Structural tests for the ADR-0002 verdict-panel rework.

ADR 0002 (verdict-panel spec, 2026-08-24) reworks the adjudication panel on top
of the Brief Manager visual port. It is DASHBOARD-ONLY and reads types that
already exist on main -- there is no new backend. These tests pin the parts a
browser fails silently on, one per ADR decision:

* D1 -- two synthetic options are ALWAYS present: REC ("Accept the
  recommendation as filed") and OTHER ("propose your own"), so approving never
  requires declaring an alternative, even for a brief that names none;
* D2 -- click-to-adopt fills verdict + disposition + reason, and only Submit
  records (covered end-to-end in test_dashboard_briefs_visual; re-pinned here
  for the preview-first contract);
* D3 -- one Submit, no separate Review step; the dry-run effect plan renders as
  a passive block under the panel; defer is a fourth verdict with a one-line
  meaning hint on every verdict;
* D5 -- HELD strikes ratifying verdicts through from the option's typed
  `disabled_reason`, malformed keeps its "closed with no verdict field"
  meaning, and the pile row is a read-only banner with no controls;
* D5(chips) -- the fake per-option blast / reversible / gates chips are gone;
  option cards render only what the parsed option carries (recommended,
  confidence, source);
* D6 -- Save draft is browser-local, labelled as not following the operator,
  and never a mutation.

The reader for every one of these is named in the assertion: the parsed option
type (`BriefDecisionOption` -> `decision_options`), the action option type
(`BriefOption.enabled` / `disabled_reason`), and the `briefs_defer` tool.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _open_option():
    return [{"id": "adjudicate", "enabled": True, "description": "Record a verdict."}]


def _locked_option(code: str, severity: str = "ERROR"):
    """An adjudicate action option that `briefs_options` reports disabled.

    Shaped like `BriefOption.to_dict()`: `enabled=False` plus a typed
    `disabled_reason` diagnostic. This is the REAL grounding for HELD.
    """
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


# --------------------------------------------------------------------------
# D1: the two synthetic options are always present
# --------------------------------------------------------------------------


def test_a_no_option_brief_offers_a_bare_approve_no_letter_required():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    # A brief that names no options offers Approve · Revise · Reject · Defer.
    # Approve carries no option, so there is no synthetic "recommendation" or
    # "other" letter to pick and nothing MOPT001 could be about.
    assert re.search(r'name="move" value="approve"', html)
    assert "approve:" not in html
    assert 'name="option_other"' not in html


def test_approve_is_never_blocked_by_a_missing_alternative():
    """D1: agreeing must never require declaring an alternative."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    # A brief that names no options still offers approve, un-disabled.
    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    approve = re.search(r'<button[^>]*value="approve"[^>]*>', html)
    assert approve and "disabled" not in approve.group(0)


# --------------------------------------------------------------------------
# D3: defer is a verdict with a hint; one-click submit; passive dry run
# --------------------------------------------------------------------------


def test_all_four_move_kinds_render_with_a_one_line_hint():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    for move in ("approve", "revise", "reject", "defer"):
        assert re.search(rf'<button[^>]*name="move" value="{move}"', html), move
    # Each move carries its meaning hint, rendered.
    assert html.count('data-region="verdict-hint"') == 4
    for hint in panel.VERDICT_HINTS.values():
        assert hint in html


def test_defer_carries_a_window_field_used_only_for_defer():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    assert 'data-region="defer-window"' in html
    assert 'name="days"' in html


def test_the_submit_is_one_click_not_a_review_step():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    # Each move is its own submit button; there is no separate Submit/Review step.
    assert '<button type="submit" name="move"' in html
    assert "Review verdict" not in html
    # Still posts through the existing preview route (preview-first, D2).
    assert 'action="/preview"' in html


def test_the_dry_run_plan_is_a_passive_block_under_the_panel():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    assert 'data-region="dry-run-plan"' in html
    # It is render-only: no form, no button, no mutation route inside it.
    block = html.split('data-region="dry-run-plan"', 1)[1]
    block = block.split("</section>", 1)[0]
    assert "<form" not in block and "<button" not in block


def test_defer_verdict_routes_to_the_existing_briefs_defer_tool():
    """D3: no new backend -- verdict=defer translates to `briefs_defer`.

    The panel posts defer through the adjudicate form; the dashboard resolves
    it to the defer Operation (which wraps the pre-existing `briefs_defer`
    tool), so the recorded preview carries defer and /apply follows it.
    """
    from mctl_dashboard.app import OPERATIONS

    assert OPERATIONS["defer"].tool == "briefs_defer"


# --------------------------------------------------------------------------
# D5: HELD strikes ratifying verdicts from the typed disabled_reason
# --------------------------------------------------------------------------


def test_held_strikes_approve_and_defer_from_the_typed_disabled_reason():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _locked_option("MBRF999"), state.ViewState())
    assert 'data-panel-state="held"' in html
    assert "line-through" in html
    # The coded reason from BriefOption.disabled_reason is shown.
    assert "MBRF999" in html
    # Ratifying moves are struck/inert; returning moves stay usable.
    for gated in ("approve", "defer"):
        found = re.search(rf'<button[^>]*value="{gated}"[^>]*>', html)
        assert found and "disabled" in found.group(0), gated
    for usable in ("revise", "reject"):
        found = re.search(rf'<button[^>]*value="{usable}"[^>]*>', html)
        assert found and "disabled" not in found.group(0), usable


def test_an_under_review_refusal_disables_defer_without_striking_it():
    """MBRF004 is structural incompleteness, not a violation: no strike."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _locked_option("MBRF004"), state.ViewState())
    assert 'data-panel-state="refused"' in html
    assert "line-through" not in html


def test_malformed_keeps_the_closed_with_no_verdict_field_meaning():
    from mctl_dashboard.screens import pipeline

    html = pipeline.malformed([{"bead_id": "he-9", "title": "t", "decision_state": "malformed"}])
    assert "closed with no verdict field" in html.lower()


def test_the_pile_row_is_a_read_only_banner_with_no_controls():
    """D5: the pile joins the matrix as a banner + gate-state, no controls."""
    from mctl_dashboard.screens import pipeline

    html = pipeline.pile()
    assert 'data-region="pile"' in html
    # Read-only: nothing to submit, no mutation route.
    assert "<form" not in html and "<button" not in html
    assert "/preview" not in html and "/apply" not in html


# --------------------------------------------------------------------------
# D5(chips): the fake per-option chips are gone; real marks render
# --------------------------------------------------------------------------


_BRIEF_WITH_OPTIONS = {
    "bead_id": "he-1",
    "decision_options": [
        {
            "label": "A",
            "title": "Merge as filed",
            "recommended": True,
            "confidence": "explicit",
            "source": "bead_description",
        },
        {"label": "B", "title": "Split first", "recommended": False, "confidence": "explicit"},
    ],
}


def test_option_cards_render_confidence_source_and_recommended():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_BRIEF_WITH_OPTIONS, _open_option(), state.ViewState())
    assert 'data-region="option-meta"' in html
    assert "recommended" in html
    assert "explicit" in html  # confidence
    assert "bead_description" in html  # source


def test_the_fake_blast_reversible_gates_chips_are_absent():
    """D5: those fields do not exist on the parsed option type; do not draw them."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_BRIEF_WITH_OPTIONS, _open_option(), state.ViewState()).lower()
    for fiction in ("blast", "reversible", "gates chip"):
        assert fiction not in html


# --------------------------------------------------------------------------
# D6: Save draft is browser-local, labelled, and never a mutation
# --------------------------------------------------------------------------


def test_save_draft_is_present_and_labelled_browser_local():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    assert 'data-region="save-draft"' in html
    assert "does not follow you" in html
    assert "Save draft" in html


def test_save_draft_never_posts_to_a_mutation_route():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState())
    box = html.split('data-region="save-draft"', 1)[1].split("</div>", 1)[0]
    # The buttons are type=button (they do not submit the form) and carry no
    # mutation route of their own.
    assert 'type="button"' in box
    assert "/preview" not in box and "/apply" not in box


def test_save_draft_is_wired_to_local_storage_only():
    """The persistence is machine-local: localStorage, no network."""
    from mctl_dashboard import assets

    assert "localStorage" in assets.SCRIPT
    assert "mctl-draft:" in assets.SCRIPT
    # No fetch/XHR: a draft never leaves the browser.
    assert "fetch(" not in assets.SCRIPT and "XMLHttpRequest" not in assets.SCRIPT


def test_the_panel_ships_no_inline_event_handlers():
    """JS stays in one module; the panel has no onclick/onchange attributes."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _open_option(), state.ViewState()).lower()
    for banned in ("onclick", "onchange", "onsubmit", "javascript:"):
        assert banned not in html
