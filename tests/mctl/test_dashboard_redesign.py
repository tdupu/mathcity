"""Tests for the redesigned dashboard surface.

`test_dashboard_views.py` is the honesty contract and is deliberately not
touched by the redesign -- it must keep passing unchanged. This file covers
what the redesign adds: the token system, the query-string view state, and the
stack table.

Two of these tests exist because the failure they catch is silent. An
undefined CSS custom property does not error; the browser drops the
declaration and the element inherits, so a page with a missing token looks
*nearly* right. And a static table min-width does not error either; it just
crushes the title column once enough columns are toggled on.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


# --------------------------------------------------------------------------
# theme
# --------------------------------------------------------------------------


def test_every_token_the_design_uses_has_a_value():
    """The prototype references 21 colour variables; all must resolve.

    The design's own stylesheet never shipped with the handoff, so thirteen of
    these had no stated value and were reconstructed from LMFDB's ramp. A
    missing one fails silently in the browser, which is why this is asserted
    rather than eyeballed.
    """
    from mctl_dashboard import theme

    required = {
        "--color-bg",
        "--color-surface",
        "--color-text",
        "--color-divider",
        "--color-accent",
        *(f"--color-accent-{n}" for n in range(100, 1000, 100)),
        *(f"--color-neutral-{n}" for n in range(100, 1000, 100)),
        "--font-heading",
        "--font-body",
        "--font-mono",
        "--radius-sm",
        "--radius-md",
        "--radius-lg",
    }
    missing = sorted(required - set(theme.TOKENS))
    assert not missing, f"tokens with no value: {missing}"


def test_the_stylesheet_declares_every_token_it_uses():
    """No `var(--x)` may reference a name `:root` never defines."""
    from mctl_dashboard import theme

    declared = set(re.findall(r"(--[a-z0-9-]+)\s*:", theme.STYLESHEET))
    used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)", theme.STYLESHEET))
    undeclared = sorted(used - declared)
    assert not undeclared, f"used but never declared: {undeclared}"


def test_fonts_are_self_hosted_not_fetched():
    """A loopback tool must not phone out for a typeface.

    GC1 forbids a CDN; GC2 keeps the dashboard on 127.0.0.1. A remote font URL
    would quietly break both, and would also leak which rig is being read to
    whoever serves the font.
    """
    from mctl_dashboard import theme

    assert "https://" not in theme.STYLESHEET
    assert "http://" not in theme.STYLESHEET
    assert "fonts.googleapis" not in theme.STYLESHEET
    assert "fonts.gstatic" not in theme.STYLESHEET


def test_the_stoplight_scale_is_defined_once():
    """Five states, each with fg/bg/edge. Re-inlining hex is how they drift."""
    from mctl_dashboard import theme

    assert set(theme.STOP) == {"error", "held", "warn", "go", "ok"}
    for name, entry in theme.STOP.items():
        assert set(entry) == {"fg", "bg", "edge"}, name


def test_every_colour_comes_from_the_design_system_not_a_reconstruction():
    """Provenance survives contact with the next maintainer.

    Thirteen of these were once interpolated from LMFDB's ramp, because the
    design's stylesheet had not shipped. It has since arrived, so no colour
    should still carry the reconstruction marker -- and this test is what
    stops one being reintroduced by hand later.
    """
    from mctl_dashboard import theme

    source = (Path(theme.__file__)).read_text(encoding="utf-8")
    colour_lines = [
        line
        for line in source.splitlines()
        if re.search(r'"--color-[a-z0-9-]+":', line)
    ]
    assert colour_lines, "no colour tokens found to check"
    for line in colour_lines:
        assert "[template]" in line or "[design]" in line, f"no provenance: {line.strip()}"
        assert "[lmfdb]" not in line, f"reconstructed value reintroduced: {line.strip()}"


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------


def test_the_table_min_width_grows_with_visible_columns():
    """A static min-width starves the title column as columns are toggled on.

    The title column declares no width and absorbs the remainder, so the
    remainder has to be computed from what is actually visible.
    """
    from mctl_dashboard import state

    lean = state.ViewState(columns=("slug", "rig"))
    fat = state.ViewState(columns=state.COLUMN_KEYS)
    assert fat.table_min_width > lean.table_min_width
    assert lean.table_min_width == 46 + 104 + 290 + 86


def test_sorting_the_current_column_flips_direction():
    from mctl_dashboard import state

    view = state.ViewState(sort_key="score", sort_dir=-1)
    assert "sort_dir=1" in view.sort_link("score")


def test_a_new_numeric_column_starts_descending():
    """Clicking Unlock should answer 'which unlocks most', not 'least'."""
    from mctl_dashboard import state

    view = state.ViewState(sort_key="score", sort_dir=-1)
    assert "sort_dir=-1" in view.sort_link("unlock")
    assert "sort_dir=1" in view.sort_link("rig")


def test_toggling_a_column_back_on_restores_canonical_order():
    """Columns must not drift into the order the operator happened to click."""
    from mctl_dashboard import state

    view = state.ViewState(columns=("slug", "rig", "unlock"))
    without = view.toggle_column("rig")
    assert without == ("slug", "unlock")
    again = state.ViewState(columns=without).toggle_column("rig")
    assert again == ("slug", "rig", "unlock")


def test_unknown_query_values_fall_back_rather_than_raising():
    """A hand-edited URL must not be a way to 500 the dashboard."""
    from mctl_dashboard import state

    view = state.parse(
        {"view": "../etc/passwd", "sort_dir": "banana", "cursor": "-3", "scope": "nope"}
    )
    assert view.view == "queue"
    assert view.scope == "stack"
    assert view.sort_dir in (-1, 1)
    assert view.cursor == 0


def test_view_state_round_trips_through_a_query_string():
    from urllib.parse import parse_qs, urlparse

    from mctl_dashboard import state

    original = state.ViewState(
        view="queue",
        scope="errors",
        rig="mathcity",
        all_rigs=True,
        sort_key="unlock",
        sort_dir=1,
        columns=("slug", "rig", "unlock"),
    )
    parsed = urlparse(original.url())
    assert parsed.path == "/queue"
    again = state.parse({k: v[0] for k, v in parse_qs(parsed.query).items()})
    assert again.scope == "errors"
    assert again.all_rigs is True
    assert again.sort_key == "unlock"
    assert again.sort_dir == 1
    assert again.columns == ("slug", "rig", "unlock")


# --------------------------------------------------------------------------
# stack table
# --------------------------------------------------------------------------


def test_health_outranks_the_cursor_in_row_colour():
    """An error row must not be recoloured by the cursor sitting on it.

    If the cursor won, running j/k down the table would make a violation look
    like an ordinary selected row for as long as the cursor rested there.
    """
    from mctl_dashboard.screens import stack

    error_row = {"kind": "error", "sev": "error"}
    assert stack.row_background(error_row, index=3, cursor=3) == "#fbeceb"

    held_row = {"kind": "full", "sev": "error"}
    assert stack.row_background(held_row, index=3, cursor=3) == "#fdeedd"

    warn_row = {"kind": "full", "sev": "warn"}
    assert stack.row_background(warn_row, index=3, cursor=3) == "#fbf4d5"

    clean_row = {"kind": "full", "sev": "ok"}
    assert stack.row_background(clean_row, index=3, cursor=3) == "var(--color-accent-100)"


def test_sorting_and_column_toggles_need_no_javascript():
    """GC3. Sorting is an anchor; the column picker is a GET form."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    # Headings only exist on a populated table, so assert against one.
    html = stack.table(
        [{"bead_id": "mc-1", "title": "A brief", "sev": "ok"}],
        state.ViewState(),
        queued=(),
    )
    picker = stack.column_picker(state.ViewState())
    for fragment in (html, picker):
        for banned in ("onclick", "onchange", "onsubmit", "javascript:"):
            assert banned not in fragment.lower(), banned
    assert 'href="/queue?' in html, "sortable headings must be links"
    assert 'method="get"' in picker.lower()


def test_the_table_escapes_brief_content():
    """Titles come from bead descriptions, which are not trusted markup."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table(
        [{"bead_id": "mc-1", "title": "<script>alert(1)</script>", "sev": "ok"}],
        state.ViewState(),
        queued=(),
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_the_key_legend_explains_every_row_colour():
    """A colour with no legend entry is a colour the operator has to guess."""
    from mctl_dashboard.screens import stack

    legend = stack.key_legend()
    for label in ("ERROR", "HELD", "WARN", "OK"):
        assert label in legend
    assert "cursor" in legend.lower()


def test_an_empty_stack_says_so_rather_than_rendering_a_bare_table():
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table([], state.ViewState(), queued=())
    assert "no briefs" in html.lower()


# --------------------------------------------------------------------------
# page shell
# --------------------------------------------------------------------------


def test_the_header_counts_link_to_the_screens_they_describe():
    """A chip must never disagree with its destination.

    Both the chip and the screen it opens read one counts mapping, so they
    cannot drift; rendering the chip as a link to that screen is the visible
    half of the same rule.
    """
    from mctl_dashboard import render

    html = render.page(
        "Brief stack",
        "/queue",
        ["<p>body</p>"],
        counts={"pile": 6, "stack": 14, "deferred": 3, "errors": 2},
        context={"city_root": "~/gt", "rig_id": "mathcity"},
    )
    assert 'href="/pile"' in html
    assert 'href="/deferred"' in html
    assert ">6<" in html


def test_the_shell_needs_no_javascript_to_navigate():
    from mctl_dashboard import render

    html = render.page("x", "/queue", [], counts={}, context={})
    for banned in ("onclick=", "onchange=", "onsubmit=", "javascript:"):
        assert banned not in html.lower(), banned


def test_the_footer_explains_the_dry_run_badge():
    """The badge appears on classifier and preview output; it needs a legend."""
    from mctl_dashboard import render

    html = render.page("x", "/queue", [], counts={}, context={})
    assert "DRY RUN" in html
    assert "no bead writes" in html.lower()


def test_the_page_still_declares_a_responsive_viewport():
    """test_dashboard_views.py asserts this; the redesign must not drop it."""
    from mctl_dashboard import render

    html = render.page("x", "/queue", [], counts={}, context={})
    assert 'name="viewport"' in html
    assert "width=device-width" in html
    assert "@media (max-width:" in html


# --------------------------------------------------------------------------
# knowls
# --------------------------------------------------------------------------


def test_a_knowl_needs_no_javascript():
    """Disclosure is <details>, which also brings keyboard and AT behaviour."""
    from mctl_dashboard import knowl

    html = knowl.tokenize(
        "This violates B2.4.",
        key="s1",
        rules={"B2.4": {"name": "Source dependency required", "text": "...", "file": "POLICY.md"}},
    )
    assert "<details" in html and "<summary" in html
    assert "onclick" not in html.lower()


def test_an_unresolved_identifier_stays_plain_text():
    """A knowl that expands to nothing is worse than no knowl.

    The design's fixtures cite MC-E101/E113/E207, none of which exist in the
    real 72-code registry. Rendering them as knowls would promise an
    explanation the dashboard cannot give.
    """
    from mctl_dashboard import knowl

    html = knowl.tokenize("Raises MC-E101.", key="s1")
    assert "MC-E101" in html
    assert "<details" not in html


def test_a_real_diagnostic_code_resolves_from_the_registry():
    from mctl_dashboard import knowl

    registry = knowl.diagnostic_registry()
    assert "MBRF004" in registry, "the 72-code registry should load"
    html = knowl.tokenize("Blocked by MBRF004.", key="s1")
    assert "<details" in html
    assert "source dependency" in html.lower()


def test_knowl_text_is_escaped():
    from mctl_dashboard import knowl

    html = knowl.tokenize("<script>alert(1)</script> cites B2.4", key="s1")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# --------------------------------------------------------------------------
# brief detail
# --------------------------------------------------------------------------


def test_the_renderer_contains_no_markdown_parser():
    """The core parses; the dashboard renders.

    A second parser here would re-implement the section mapping and drift from
    what `briefs_show` reports, which is the failure `client.py` exists to
    prevent.
    """
    import inspect

    from mctl_dashboard.screens import brief

    source = inspect.getsource(brief)
    for banned in ("startswith('#')", 'startswith("#")', "lstrip('#')", 'split("\\n#")'):
        assert banned not in source, f"looks like markdown parsing: {banned}"


def test_unmapped_sections_are_rendered_not_dropped():
    """Most real sections do not map to a numbered slot.

    Across 25 live hecke briefs there were 42 unmapped sections against 31
    mapped. Dropping the unmapped ones would silently discard the majority of
    every brief's content.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    payload = {
        "bead_id": "he-1",
        "title": "t",
        "sections": [
            {"section_index": 1, "section_key": "what_is_being_decided",
             "heading": "Decision", "body": "Pick A.", "match": "heading"},
            {"section_index": None, "section_key": None,
             "heading": "Encoding", "body": "The chain complex.", "match": "unmapped"},
        ],
        "body_diagnostics": [],
    }
    html = brief.detail(payload, state.ViewState())
    assert "Encoding" in html
    assert "The chain complex." in html


def test_a_brief_with_no_headings_renders_its_body_and_says_why():
    """36% of live pending briefs have no headings at all (MBRF041)."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    payload = {
        "bead_id": "he-2",
        "title": "t",
        "body": "One paragraph of prose, no headings anywhere.",
        "sections": [],
        "body_diagnostics": [{"code": "MBRF041", "message": "no markdown headings"}],
    }
    html = brief.detail(payload, state.ViewState())
    assert "One paragraph of prose" in html
    assert "MBRF041" in html


def test_absent_sections_are_not_rendered_as_empty_slots():
    """An empty §5 would assert the author omitted a required section.

    No live brief carries all seven. Rendering the five it lacks as empty
    headings would make every brief look non-compliant, when in fact the
    parser simply found no heading that mapped.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    payload = {
        "bead_id": "he-3",
        "title": "t",
        "sections": [
            {"section_index": 1, "section_key": "what_is_being_decided",
             "heading": "Decision", "body": "Pick A.", "match": "heading"},
        ],
        "body_diagnostics": [],
    }
    html = brief.detail(payload, state.ViewState())
    assert "Risks" not in html, "an absent section must not be drawn as an empty slot"


def test_the_decision_section_is_flagged_when_it_is_not_first():
    """Decision-at-Top is an invariant of the brief form, so a violation shows."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    payload = {
        "bead_id": "he-4",
        "title": "t",
        "sections": [
            {"section_index": 2, "section_key": "recommended_answer",
             "heading": "Rationale", "body": "Because.", "match": "heading"},
            {"section_index": 1, "section_key": "what_is_being_decided",
             "heading": "Decision", "body": "Pick A.", "match": "heading"},
        ],
        "body_diagnostics": [],
    }
    html = brief.detail(payload, state.ViewState())
    assert "decision-at-top" in html.lower()


def test_brief_detail_escapes_body_content():
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    payload = {
        "bead_id": "he-5",
        "title": "<script>x</script>",
        "body": "<img src=x onerror=alert(1)>",
        "sections": [],
        "body_diagnostics": [],
    }
    html = brief.detail(payload, state.ViewState())
    assert "<script>x</script>" not in html
    assert "onerror=alert(1)>" not in html


# --------------------------------------------------------------------------
# adjudication panel
# --------------------------------------------------------------------------


def _option(enabled: bool, code: str = "", severity: str = "ERROR"):
    entry = {"id": "adjudicate", "enabled": enabled, "description": "Record a verdict."}
    if not enabled:
        entry["disabled_reason"] = {
            "code": code,
            "severity": severity,
            "message": "Brief bead has no source dependency.",
            "policy_reference": "B2.1",
        }
    return [entry]


def test_a_verdict_submits_without_javascript():
    """The panel is a form into the existing preview route, not a widget."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(True), state.ViewState())
    assert 'action="/preview"' in html
    assert 'method="post"' in html.lower()
    for banned in ("onclick", "onchange", "onsubmit", "javascript:"):
        assert banned not in html.lower()


def test_the_panel_never_offers_a_repair_affordance():
    """GC4/GC7 -- CI bans these strings anywhere in rendered output."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(True), state.ViewState())
    for banned in ('action="/repair"', ">Repair<", ">Fix<", "Fix these", "auto-repair"):
        assert banned not in html


def test_an_under_review_refusal_is_disabled_but_not_struck_through():
    """MBRF004 is structural incompleteness, not a violation.

    It means the brief is not linked to what it decides -- nothing is
    known-bad and nothing would be ratified. Striking the verdicts through
    would tell the operator the brief is wrong, when what is missing is an
    edge. On the live queue this fires on roughly two thirds of pending
    briefs, so getting it wrong would condemn most of the stack.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(False, "MBRF004"), state.ViewState())
    assert "line-through" not in html
    assert "MBRF004" in html
    assert "not linked to what it decides" in html.lower()
    assert 'data-panel-state="refused"' in html


def test_a_real_gate_failure_is_held_and_strikes_every_verdict_but_reject():
    """HELD is the other thing: approving would ratify a known violation."""
    import re

    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        {"bead_id": "he-1"}, _option(False, "MBRF999"), state.ViewState()
    )
    assert 'data-panel-state="held"' in html
    assert "line-through" in html
    allowed = re.search(r'<input[^>]*value="reject"[^>]*>', html)
    assert allowed and "disabled" not in allowed.group(0)


def test_refusal_gates_ratifying_but_never_returning():
    """Refusal restricts what you may ratify, never what you may send back.

    The earlier version of this test asserted that *every* verdict went dark in
    a refused state. That encoded a real defect: on the body-less briefs the
    only sensible verdict is "revise, go add fields", and gating it left the
    adjudicator with no move at all. `approve` stays gated -- ratifying an
    unreadable brief is exactly what refusal is for.
    """
    import re

    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    for code in ("MBRF004", "MBRF999"):
        html = panel.entry({"bead_id": "he-1"}, _option(False, code), state.ViewState())

        approve = re.search(r'<input[^>]*value="approve"[^>]*>', html)
        assert approve and "disabled" in approve.group(0), (code, "approve must stay gated")

        for verdict in ("revise", "reject"):
            found = re.search(rf'<input[^>]*value="{verdict}"[^>]*>', html)
            assert found and "disabled" not in found.group(0), (code, verdict)


def test_a_returnable_brief_has_a_usable_form():
    """Freeing the radio is pointless if the reason box and submit stay locked."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(False, "MBRF004"), state.ViewState())
    assert '<textarea name="reason"' in html
    assert "disabled" not in html.split('name="reason"')[1].split(">")[0]
    assert '<button class="btn btn-primary" type="submit">' in html


def test_the_no_brainer_flag_is_present_and_is_not_a_verdict():
    """Ticking it records a classifier signal, not a disposition."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(True), state.ViewState())
    assert 'name="no_brainer"' in html
    assert 'name="no_brainer_reason"' in html
    # It must not be one of the verdict radios.
    assert 'name="verdict" value="no_brainer"' not in html


def test_the_no_brainer_flag_survives_refusal():
    """The empty briefs are exactly the ones Taylor wants to flag."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(False, "MBRF004"), state.ViewState())
    assert 'name="no_brainer"' in html


def test_a_reason_is_required():
    """No bare verdict -- the reason is what a future reader actually reads."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(True), state.ViewState())
    assert "required" in html
    assert 'name="reason"' in html


def test_the_verdict_set_is_not_a_closed_four():
    """12 of 86 closed briefs carry a compound verdict; leave room."""
    from mctl_dashboard.screens import panel

    names = {name for name, _label in panel.VERDICTS}
    assert len(panel.VERDICTS) >= 4
    assert {"approve", "reject"} <= names


# --------------------------------------------------------------------------
# sorting on a column with no data
# --------------------------------------------------------------------------


def test_the_default_sort_uses_a_column_that_has_values():
    """Score is empty on every real brief until unlock_count exists.

    Defaulting to it means the stack opens ordered by nothing, which looks
    exactly like a working sort. Age is derived from created_at and is always
    present, so it is the honest default until #66 lands.
    """
    from mctl_dashboard import state

    assert state.ViewState().sort_key == "age"


def test_sorting_by_an_empty_column_says_so_out_loud():
    """Silence here reads as 'sorted, and this is the order'."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    briefs = [{"bead_id": "he-1", "title": "a"}, {"bead_id": "he-2", "title": "b"}]
    note = stack.empty_sort_note(briefs, state.ViewState(sort_key="score"))
    assert note, "an all-empty sort column must be announced"
    assert "score" in note.lower()
    assert "no values" in note.lower()


def test_no_notice_when_the_sort_column_has_values():
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    briefs = [{"bead_id": "he-1", "title": "a", "created_at": "2026-08-01T00:00:00Z"}]
    assert stack.empty_sort_note(briefs, state.ViewState(sort_key="age")) == ""


# --------------------------------------------------------------------------
# pipeline screens
# --------------------------------------------------------------------------


def test_the_pile_names_its_gap_rather_than_rendering_empty():
    """Nothing reads the pile through the typed surface yet.

    An empty table would say "the pile is empty", which is a measurement
    nobody took.
    """
    from mctl_dashboard.screens import pipeline

    html = pipeline.pile()
    assert "#66" in html
    assert "not" in html.lower()
    assert 'data-region="pile"' in html


def test_a_truly_empty_deferred_list_differs_from_an_unreadable_one():
    """Zero deferred briefs is a fact; unreadable windows is a gap.

    Collapsing the two would let a broken read look like a quiet queue.
    """
    from mctl_dashboard.screens import pipeline

    empty = pipeline.deferred([])
    assert "no briefs are deferred" in empty.lower()
    assert "#66" not in empty.split("</h1>")[0]

    listed = pipeline.deferred([{"bead_id": "he-1", "title": "t", "decision_state": "deferred"}])
    assert "window" in listed.lower()
    assert "#66" in listed


def test_adjudicated_says_the_verdict_is_not_readable():
    """The verdict is the point of this screen and the payload lacks it.

    `_verdict` computes one internally to classify decision_state, but
    `to_dict` never emits it -- so the screen can say which briefs were
    decided and not what was decided. Silence would imply no verdict existed.
    """
    from mctl_dashboard.screens import pipeline

    html = pipeline.adjudicated(
        [{"bead_id": "he-1", "title": "t", "decision_state": "adjudicated",
          "updated_at": "2026-08-01T00:00:00Z"}]
    )
    assert "he-1" in html
    assert "verdict" in html.lower()
    assert "#66" in html


def test_adjudicated_offers_no_reopen_control():
    """B3.8 -- decision beads are immutable; a change of mind is a new bead.

    Explaining that in prose is wanted; offering a control is not. So this
    checks for the affordance, not the word.
    """
    import re

    from mctl_dashboard.screens import pipeline

    html = pipeline.adjudicated(
        [{"bead_id": "he-1", "title": "t", "decision_state": "adjudicated"}]
    )
    assert not re.search(r"<(button|form)\b", html), "no control may undo a decision"
    assert "never reopened" in html.lower(), "and the page should say why"


def test_malformed_briefs_are_surfaced_with_their_caveat():
    """19 of 114 live briefs are `malformed`, and the design has no lane.

    Leaving them out of the nav makes them invisible. Showing the count bare
    would be worse: "malformed" means closed with no verdict *field*, not
    damaged, and the caveat has to travel with the number.
    """
    from mctl_dashboard.screens import pipeline

    html = pipeline.malformed(
        [{"bead_id": "he-1", "title": "t", "decision_state": "malformed"}]
    )
    assert "he-1" in html
    assert "closed with no verdict field" in html.lower()
    assert "damaged" in html.lower(), "the caveat must rebut the word malformed"
    assert "read this count carefully" in html.lower()


# --------------------------------------------------------------------------
# priority list
# --------------------------------------------------------------------------


def test_the_priority_list_starts_empty_with_a_real_empty_state():
    """It is the operator's own ordering, so it begins with nothing in it."""
    from mctl_dashboard.screens import priority

    html = priority.screen([])
    assert "nothing here yet" in html.lower()
    assert "go to the stack" in html.lower()


def test_reordering_works_without_javascript():
    """Drag is the enhancement; move-up/move-down links are the baseline."""
    from mctl_dashboard.screens import priority

    html = priority.screen(
        [{"bead_id": "he-1", "title": "a"}, {"bead_id": "he-2", "title": "b"}]
    )
    assert html.count("move up") >= 1
    assert html.count("move down") >= 1
    for banned in ("onclick", "onchange", "javascript:"):
        assert banned not in html.lower()


def test_the_ordering_is_not_presented_as_canonical():
    """No policy defines importance; this is one clerk's hypothesis.

    Persisting it server-side would make one operator's experiment look like a
    fact about briefs, which is why it lives in the browser.
    """
    from mctl_dashboard.screens import priority

    html = priority.screen([{"bead_id": "he-1", "title": "a"}])
    assert "your own ordering" in html.lower()
    assert "this browser" in html.lower()


def test_moving_the_first_item_up_is_a_no_op_not_an_error():
    from mctl_dashboard.screens import priority

    assert priority.reorder(["a", "b", "c"], "a", "up") == ["a", "b", "c"]
    assert priority.reorder(["a", "b", "c"], "c", "down") == ["a", "b", "c"]


def test_moving_an_item_down_lands_where_a_reader_expects():
    """The prototype's splice arithmetic shifted downward moves by one."""
    from mctl_dashboard.screens import priority

    assert priority.reorder(["a", "b", "c"], "a", "down") == ["b", "a", "c"]
    assert priority.reorder(["a", "b", "c"], "c", "up") == ["a", "c", "b"]


def test_reorder_ignores_an_unknown_id():
    """A stale link must not raise."""
    from mctl_dashboard.screens import priority

    assert priority.reorder(["a", "b"], "zzz", "up") == ["a", "b"]


# --------------------------------------------------------------------------
# finishing the surface
# --------------------------------------------------------------------------


def test_the_keys_chip_has_something_to_open():
    """The header links to #mc-keys; that anchor has to exist."""
    from mctl_dashboard import render

    html = render.page("x", "/queue", [], counts={}, context={})
    assert 'href="#mc-keys"' in html
    assert 'id="mc-keys"' in html


def test_the_key_map_lists_every_binding_the_script_implements():
    """A key map that disagrees with the code teaches the wrong keys."""
    from mctl_dashboard import assets, render

    html = render.page("x", "/queue", [], counts={}, context={})
    for key in ("j", "k", "enter"):
        assert f">{key}<" in html or f"<b>{key}" in html, key
    # Anything the script binds must appear in the map.
    for bound in ("'j'", "'k'", "'enter'"):
        assert bound in assets.SCRIPT


def test_producing_formula_is_no_longer_a_column():
    """cozy: no verified source for which formula filed a brief.

    provenance.py is wired to work_provenance -- dispatch provenance -- not to
    brief production. A sixth em dash helps nobody, so the column is dropped
    until a producer actually records one.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    assert "formula" not in state.COLUMN_KEYS
    assert "formula" not in stack.UNFED_COLUMNS


def test_the_mbrf004_copy_reports_the_shrink_as_done():
    """It happened: 120 -> 71 blocked, brief population 280 -> 197.

    Copy that still says "expect this to shrink" would be describing a future
    that has already arrived.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    options = [
        {
            "id": "adjudicate",
            "enabled": False,
            "disabled_reason": {
                "code": "MBRF004",
                "severity": "ERROR",
                "message": "Brief bead has no source dependency.",
            },
        }
    ]
    html = panel.entry({"bead_id": "he-1"}, options, state.ViewState())
    assert "expect this population to shrink" not in html.lower()
    assert "49" in html or "71" in html, "cite the measured outcome"


# --------------------------------------------------------------------------
# the generic attribute renderer
# --------------------------------------------------------------------------


def test_absent_fields_do_not_render_at_all():
    """No em-dash rows, no 'not exposed' apology.

    A brief that has no `verdict` has not been adjudicated -- that is a fact
    about the brief, not a gap in the data, and drawing an empty row for it
    invents a hole.
    """
    from mctl_dashboard import fields

    html = fields.attributes({"status": "ready", "track": "pack-hygiene"})
    assert "status" in html and "track" in html
    for absent in ("verdict", "unlock_count", "gates", "priority"):
        assert absent not in html, absent


def test_an_unknown_field_still_renders():
    """The point of the renderer: a producer adds a field, it appears.

    If unknown keys were dropped, every new field would need a dashboard
    release before anyone could see it.
    """
    from mctl_dashboard import fields

    html = fields.attributes({"blast_radius": "shared paths", "invented_later": 7})
    assert "blast_radius" in html or "blast radius" in html
    assert "shared paths" in html
    assert "invented_later" in html or "invented later" in html
    assert "7" in html


def test_known_fields_get_known_treatment():
    """unlock_count is a figure; track is a filter; verdict is a verdict."""
    from mctl_dashboard import fields

    html = fields.attributes({"unlock_count": 9, "track": "pack-hygiene", "verdict": "APPROVE"})
    assert "tnum" in html, "figures should be tabular"
    assert 'href="/queue?' in html and "pack-hygiene" in html, "track should filter"
    assert "APPROVE" in html


def test_field_values_are_escaped():
    from mctl_dashboard import fields

    html = fields.attributes({"note": "<script>alert(1)</script>"})
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_provenance_is_shown_when_given_and_never_invented():
    """A frontmatter value and a bead value are not equally attested.

    When the core says where a field came from, show it. When it does not,
    show nothing rather than guessing -- a wrong provenance claim is worse
    than none.
    """
    from mctl_dashboard import fields

    with_src = fields.attributes({"unlock_count": 9}, sources={"unlock_count": "frontmatter"})
    assert "frontmatter" in with_src

    without = fields.attributes({"unlock_count": 9})
    assert "frontmatter" not in without and "bead" not in without


def test_a_disagreement_between_sources_is_shown_not_resolved():
    """cozy preserves both when bead and file disagree; so must the page.

    Picking a winner silently would make the dashboard the place a conflict
    disappears.
    """
    from mctl_dashboard import fields

    html = fields.attributes(
        {"priority": "P1"},
        conflicts={"priority": {"bead": "P2", "frontmatter": "P1"}},
    )
    assert "P1" in html and "P2" in html
    assert "disagree" in html.lower()


def test_empty_attributes_render_nothing_rather_than_an_empty_shell():
    from mctl_dashboard import fields

    assert fields.attributes({}) == ""


# --------------------------------------------------------------------------
# city-wide scope
# --------------------------------------------------------------------------


def _city_dashboard(tmp_path):
    """A city-wide dashboard over the multi-rig fixture."""
    import multi_rig
    from mctl_dashboard.app import Dashboard
    from mctl_dashboard.client import InProcessMcpClient

    fixture = multi_rig.build(tmp_path)
    client = InProcessMcpClient(city=fixture.city_root)
    return Dashboard(client, city_wide=True, rig=None)


def test_the_redesigned_screens_work_city_wide(tmp_path):
    """Every new screen was built and tested rig-scoped only.

    In city scope `rig` is None and `briefs_list` needs `all_rigs`, so the
    handlers raised ToolFailure and the routes returned nothing at all.
    """
    from mctl_dashboard.app import Request

    dashboard = _city_dashboard(tmp_path)
    for path in ("/queue", "/deferred", "/adjudicated", "/malformed", "/priority"):
        response = dashboard.handle(Request.get(path))
        assert response.status == 200, f"{path} -> {response.status}"


def test_a_degraded_rig_is_named_on_the_redesigned_screens(tmp_path):
    """Honesty property 4, which the new screens were missing.

    A rig that cannot be read contributes no rows, so a city-wide total is
    silently short and looks complete. The older views render a named row with
    the reason; the redesigned ones have to as well, or the redesign quietly
    drops the property.
    """
    from mctl_dashboard.app import Request

    dashboard = _city_dashboard(tmp_path)
    html = dashboard.handle(Request.get("/queue")).body
    assert 'data-region="degraded-rigs"' in html, (
        "city-wide screens must account for unreadable rigs"
    )


# --------------------------------------------------------------------------
# the remaining design features
# --------------------------------------------------------------------------


def test_rows_can_be_ticked_and_added_together():
    """Bulk add: tick several, add them in one go.

    A GET form, so it works with scripting off -- the ticks are checkboxes
    carrying bead ids and the button submits them to the priority list.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table(
        [{"bead_id": "he-1", "title": "a"}, {"bead_id": "he-2", "title": "b"}],
        state.ViewState(),
        queued=(),
    )
    assert 'name="pick"' in html and 'value="he-1"' in html
    assert 'action="/priority"' in html
    assert "onclick" not in html.lower()


def test_the_rig_picker_is_a_dropdown_defaulting_to_all_rigs():
    """A real dropdown, in the header, as the design draws it.

    An earlier attempt used `<select multiple size="1">`, which browsers draw
    as a one-line list box indistinguishable from a broken text input -- it
    rendered as `rig all rigs [agent_skills] Apply` and looked like a defect.
    """
    from mctl_dashboard import render

    html = render.rig_picker(("hecke", "gascity", "mathcity"), selected=())
    assert "multiple" not in html, "a one-line multi-select draws as a broken text box"
    assert html.count("<option") >= 4, "every rig plus an all-rigs default"
    assert 'value=""' in html and "all rigs" in html.lower()
    # Submits on change, and still submits without script.
    assert "onchange" in html
    assert "<noscript>" in html


def test_the_importance_sliders_exist_and_submit_without_javascript():
    """Four weights, 0-10, in a GET form with an Apply button."""
    from mctl_dashboard import render
    from mctl_dashboard.screens import stack

    html = render.importance(stack.DEFAULT_WEIGHTS)
    assert html.count('type="range"') == 4
    assert 'method="get"' in html.lower()
    for key in stack.DEFAULT_WEIGHTS:
        assert f'name="w_{key}"' in html
    assert "onchange" not in html.lower()


def test_the_sliders_say_what_they_currently_affect():
    """Score is empty until unlock_count lands, so the sliders move nothing.

    Rendering four live-looking controls that change no visible output would
    be the same failure as a sort over an empty column.
    """
    from mctl_dashboard import render
    from mctl_dashboard.screens import stack

    html = render.importance(stack.DEFAULT_WEIGHTS)
    assert "score" in html.lower()


def test_the_sidebar_lists_the_next_few_queued_briefs():
    from mctl_dashboard import render

    empty = render.sidebar("/queue", {}, queued=())
    assert "nothing queued" in empty.lower()

    filled = render.sidebar("/queue", {}, queued=("he-1", "he-2"))
    assert "he-1" in filled and "he-2" in filled


def test_weights_round_trip_through_the_query_string():
    from mctl_dashboard import state

    view = state.parse({"w_unlock": "3", "w_age": "9", "w_prio": "0"})
    assert view.weights["unlock"] == 3
    assert view.weights["age"] == 9
    assert view.weights["prio"] == 0
    assert "w_unlock=3" in view.url()


def test_hostile_weight_values_fall_back():
    from mctl_dashboard import state

    view = state.parse({"w_unlock": "banana", "w_age": "-5", "w_prio": "999"})
    for value in view.weights.values():
        assert 0 <= value <= 10


def test_the_masthead_names_the_city_even_city_wide(tmp_path):
    """City-wide is exactly when 'which city am I reading' matters most.

    `context_resolve` needs a rig and hard-errors without one, so the
    redesigned handlers passed no context at all in city scope and the header
    rendered `city —`. Spanning 17 rigs with no statement of which city they
    belong to is the masthead failing at its only job.
    """
    from mctl_dashboard.app import Request

    dashboard = _city_dashboard(tmp_path)
    html = dashboard.handle(Request.get("/queue")).body
    marker = html.split(">city</span>")[1][:40]
    assert "—" not in marker, f"city not named city-wide: {marker!r}"


def test_the_page_body_can_never_scroll_horizontally():
    """The design's rule: wide content scrolls in its own container.

    A control row that did not wrap pushed the body to 547px at a 390px
    viewport. No unit test caught it because none of them lay the page out,
    so the rule is asserted in the stylesheet instead.
    """
    from mctl_dashboard import theme

    assert "overflow-x: hidden" in theme.STYLESHEET
    assert ".scroll-x { overflow-x: auto" in theme.STYLESHEET


def test_a_brief_link_carries_its_rig_city_wide(tmp_path):
    """City-wide, clicking a brief must reach the brief.

    A brief lives in exactly one rig's store, so a city-wide detail page
    cannot resolve one without being told which. The stack's links dropped
    the rig, so every click returned HTTP 400 rig-required -- the primary
    navigation path, broken in the scope where the dashboard spans 17 rigs.
    """
    from mctl_dashboard.app import Request

    dashboard = _city_dashboard(tmp_path)
    html = dashboard.handle(Request.get("/queue")).body
    import re

    hrefs = re.findall(r'data-href="([^"]+)"', html)
    assert hrefs, "no brief rows rendered"
    for href in hrefs:
        assert "rig=" in href, f"brief link has no rig: {href}"

    # And following it must not land on rig-required. The href is HTML-escaped
    # (`&amp;`), as an href attribute must be, so unescape before parsing --
    # the browser does the same.
    import html as html_mod

    first = html_mod.unescape(hrefs[0])
    path, _, query = first.partition("?")
    params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
    response = dashboard.handle(Request.get(path, **params))
    assert 'data-region="rig-required"' not in response.body, (
        f"{first} still resolves to rig-required"
    )


def test_a_brief_says_up_front_whether_it_can_be_adjudicated():
    """Whether you can act is the first thing you need, not the last.

    The panel sits below the body, the properties and the diagnostics -- about
    59% down a real page. On a brief that is refused, the reader scrolls all
    of that to reach four disabled controls. Decision-at-Top is the rule for
    briefs; the page about a brief owes the reader the same.
    """
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    refused = [
        {
            "id": "adjudicate",
            "enabled": False,
            "disabled_reason": {"code": "MBRF004", "message": "no source dependency"},
        }
    ]
    html = brief.detail(
        {"bead_id": "gt-1", "title": "t", "sections": [], "body_diagnostics": []},
        state.ViewState(),
        options=refused,
    )
    banner = html.split('data-region="brief-status"')[1][:400]
    assert "MBRF004" in banner
    assert "#mc-adjudicate" in html, "there should be a jump to the panel"
    # And the status must come before the panel it describes.
    assert html.index('data-region="brief-status"') < html.index("mc-adjudicate")


def test_an_empty_brief_that_is_also_refused_says_both():
    """Nothing to read and nothing to do is worth stating once, plainly."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    html = brief.detail(
        {
            "bead_id": "gt-1",
            "title": "t",
            "body": "",
            "sections": [],
            "body_diagnostics": [{"code": "MBRF040", "message": "no description"}],
        },
        state.ViewState(),
        options=[{"id": "adjudicate", "enabled": False,
                  "disabled_reason": {"code": "MBRF004", "message": "no source"}}],
    )
    status = html.split('data-region="brief-status"')[1][:700]
    # Was "nothing to read here and nothing you can record". The second half
    # became false when revise stopped being gated, and the first half framed
    # an empty brief as a dead end rather than as the reason to return it.
    assert "grounds to return" in status.lower()
    assert "send it back" in status.lower()


def test_an_adjudicable_brief_says_so_too():
    from mctl_dashboard import state
    from mctl_dashboard.screens import brief

    html = brief.detail(
        {"bead_id": "gt-1", "title": "t", "sections": [], "body_diagnostics": []},
        state.ViewState(),
        options=[{"id": "adjudicate", "enabled": True}],
    )
    status = html.split('data-region="brief-status"')[1][:300]
    assert "ready" in status.lower() or "can be" in status.lower()


def test_the_core_field_provenance_is_unpacked_not_dumped():
    """cozy ships `fields` as {name: {value, source, conflict, readings}}.

    Rendered generically it stringifies as a Python repr -- agent exhaust
    leaking into the operator's page. It is exactly the provenance the
    renderer was built for, so it is unpacked into value + source instead.
    """
    from mctl_dashboard import fields

    payload = {
        "bead_id": "gt-1",
        "fields": {
            "priority": {
                "value": "1",
                "source": "bead",
                "conflict": False,
                "readings": [{"source": "bead", "value": "1"}],
            }
        },
    }
    html = fields.attributes(**fields.unpack(payload))
    assert "priority" in html
    assert ">1<" in html or "1</span>" in html
    assert "bead" in html
    assert "readings" not in html, "internal structure must not leak"
    assert "{" not in html and "'" not in html, "no Python repr in the page"


def test_a_conflicting_field_surfaces_both_readings():
    from mctl_dashboard import fields

    payload = {
        "fields": {
            "priority": {
                "value": "1",
                "source": "bead",
                "conflict": True,
                "readings": [
                    {"source": "bead", "value": "1"},
                    {"source": "frontmatter", "value": "P2"},
                ],
            }
        }
    }
    html = fields.attributes(**fields.unpack(payload))
    assert "disagree" in html.lower()
    assert "P2" in html and "1" in html


def _adj_op():
    class _Op:
        name = "adjudicate"

    return _Op()


def test_the_no_brainer_flag_reaches_the_bead():
    """A control that posts a field the handler drops is decoration.

    The core has no no-brainer field yet, so the flag is folded into the reason
    that is written to the bead. This test is what stops it from silently
    becoming a no-op again.
    """
    from mctl_dashboard.app import NO_BRAINER_MARKER, _arguments_for

    args = _arguments_for(
        _adj_op(),
        "he-1",
        {"verdict": "revise", "reason": "needs fields", "no_brainer": "1",
         "no_brainer_reason": "empty brief, classifier should have caught it"},
        None,
    )
    assert args["verdict"] == "revise"
    assert "needs fields" in args["reason"]
    assert NO_BRAINER_MARKER in args["reason"]
    assert "classifier should have caught it" in args["reason"]


def test_an_unticked_no_brainer_box_changes_nothing():
    from mctl_dashboard.app import NO_BRAINER_MARKER, _arguments_for

    args = _arguments_for(
        _adj_op(), "he-1", {"verdict": "revise", "reason": "needs fields"}, None
    )
    assert args["reason"] == "needs fields"
    assert NO_BRAINER_MARKER not in args["reason"]


def test_the_banner_does_not_claim_a_dead_end():
    """It used to say "nothing you can record" -- which is now false."""
    from mctl_dashboard import state  # noqa: F401
    from mctl_dashboard.screens import brief as brief_screen

    html = brief_screen.status_banner({"bead_id": "he-1"}, _option(False, "MBRF004"))
    assert "cannot be adjudicated" not in html
    assert "nothing you can record" not in html
    assert "send it back" in html
    assert "revise or reject" in html


def test_an_empty_brief_is_told_that_emptiness_is_grounds_to_return():
    from mctl_dashboard.screens import brief as brief_screen

    html = brief_screen.status_banner({"bead_id": "he-1", "body": ""}, _option(False, "MBRF004"))
    assert "grounds to return" in html


def test_an_open_brief_banner_is_unchanged():
    from mctl_dashboard.screens import brief as brief_screen

    html = brief_screen.status_banner({"bead_id": "he-1", "body": "x"}, _option(True))
    assert "Ready to adjudicate" in html


def test_the_panel_notice_says_what_is_still_possible():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(False, "MBRF004"), state.ViewState())
    assert "NOT YET ADJUDICABLE" not in html
    assert "APPROVE UNAVAILABLE" in html
    assert "Revise and reject remain available" in html


# --------------------------------------------------------------------------
# empty columns
# --------------------------------------------------------------------------


def _bare_brief(n: int) -> dict:
    """A brief carrying only what the core actually feeds today."""
    return {"bead_id": f"gt-{n}", "title": f"brief {n}", "rig_id": "hq",
            "canonical_source": "bead_store"}


def test_a_column_no_brief_can_feed_is_not_drawn():
    """Five columns of em dashes is noise presented as a table."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table([_bare_brief(i) for i in range(4)], state.parse({}))
    for label in ("Unlock", "Priority", "Opts", "Rec."):
        assert f">{label}<" not in html, f"{label} drew with no data behind it"


def test_a_column_with_even_one_value_is_kept():
    """Sparse is not empty -- one real value is a reason to show the column."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    briefs = [_bare_brief(i) for i in range(4)]
    briefs[2]["unlock_count"] = 7
    html = stack.table(briefs, state.parse({}))
    assert ">Unlock<" in html
    assert ">7<" in html


def test_asking_for_a_column_overrides_the_hiding():
    """Hidden by default is not hidden from someone who asked."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table(
        [_bare_brief(i) for i in range(3)], state.parse({"columns": "slug,unlock"})
    )
    assert ">Unlock<" in html


def test_the_hidden_columns_are_named_not_silently_dropped():
    """A quietly missing column reads as a column that does not exist."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table([_bare_brief(i) for i in range(4)], state.parse({}))
    assert "unlock_count" in html


# --------------------------------------------------------------------------
# queue navigation
# --------------------------------------------------------------------------


def test_queue_nav_places_the_brief_in_its_queue():
    from mctl_dashboard.screens import brief as brief_screen

    html = brief_screen.queue_nav(
        {"bead_id": "gt-2"},
        {"index": 4, "total": 115, "prev_id": "gt-1", "next_id": "gt-3"},
        rig="hq",
    )
    assert "brief 5 of 115" in html
    assert "/briefs/gt-1?rig=hq" in html
    assert "/briefs/gt-3?rig=hq" in html
    assert "/queue?rig=hq" in html


def test_queue_nav_omits_a_position_it_does_not_know():
    """A guessed "1 of 1" on a page reached from a 180-row queue is a lie."""
    from mctl_dashboard.screens import brief as brief_screen

    html = brief_screen.queue_nav({"bead_id": "gt-2"}, None, rig="hq")
    assert "brief " not in html
    assert "/queue?rig=hq" in html


def test_queue_nav_does_not_offer_a_next_that_does_not_exist():
    from mctl_dashboard.screens import brief as brief_screen

    html = brief_screen.queue_nav(
        {"bead_id": "gt-9"},
        {"index": 114, "total": 115, "prev_id": "gt-8", "next_id": None},
        rig="hq",
    )
    assert "brief 115 of 115" in html
    assert 'href="/briefs/gt-8?rig=hq"' in html
    assert "next &rarr;" in html
    assert 'href="/briefs/None' not in html


def test_other_is_not_sent_as_an_option_letter():
    """The core would reject "other" as an invalid option, and should."""
    from mctl_dashboard.app import PROPOSED_OPTION_MARKER, _arguments_for

    class _Op:
        name = "adjudicate"

    args = _arguments_for(
        _Op(), "he-1",
        {"verdict": "revise", "reason": "see below", "option": "other",
         "option_other": "Split it into two briefs and re-file."},
        None,
    )
    assert "option" not in args
    assert PROPOSED_OPTION_MARKER in args["reason"]
    assert "Split it into two briefs" in args["reason"]


def test_a_real_option_letter_still_goes_through_as_an_option():
    from mctl_dashboard.app import _arguments_for

    class _Op:
        name = "adjudicate"

    args = _arguments_for(
        _Op(), "he-1", {"verdict": "approve", "reason": "ok", "option": "B"}, None
    )
    assert args["option"] == "B"
    assert "proposed-option" not in args["reason"]


def test_the_disposition_control_offers_the_briefs_own_options():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        {"bead_id": "he-1",
         "decision_options": [{"label": "A", "title": "Merge as filed"},
                              {"label": "B", "title": "Split first"}]},
        _option(True), state.ViewState(),
    )
    assert 'value="A"' in html and "Merge as filed" in html
    assert 'value="B"' in html and "Split first" in html
    assert 'value="other"' in html
    assert 'name="option_other"' in html


def test_a_brief_with_no_options_says_so_rather_than_demanding_a_letter():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1"}, _option(True), state.ViewState())
    assert "names no options" in html
    assert 'value="other"' in html


# --------------------------------------------------------------------------
# keyboard map
# --------------------------------------------------------------------------


def test_every_advertised_key_is_actually_handled():
    """The map's docstring claims it cannot drift. Nothing enforced that.

    A key map listing a binding the code does not have teaches the wrong keys,
    which is worse than no map at all -- and the comment saying so was written
    without a test behind it.
    """
    import re

    from mctl_dashboard import render
    from mctl_dashboard.assets import SCRIPT

    handled = set(re.findall(r"key === '([a-z]+)'", SCRIPT))
    advertised = {key for key, _ in render.KEY_BINDINGS}
    missing = advertised - handled
    assert not missing, f"advertised but not handled: {sorted(missing)}"


def test_every_handled_key_is_advertised():
    """A working key nobody is told about is a feature that does not exist."""
    import re

    from mctl_dashboard import render
    from mctl_dashboard.assets import SCRIPT

    handled = set(re.findall(r"key === '([a-z]+)'", SCRIPT))
    advertised = {key for key, _ in render.KEY_BINDINGS}
    undocumented = handled - advertised
    assert not undocumented, f"handled but undocumented: {sorted(undocumented)}"


# --------------------------------------------------------------------------
# the standing return for an empty brief
# --------------------------------------------------------------------------


def test_an_empty_brief_offers_the_standing_return():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry({"bead_id": "he-1", "body": ""}, _option(True), state.ViewState())
    assert 'data-region="prefill-offer"' in html
    assert "prefill=incomplete" in html


def test_a_brief_with_a_body_is_not_offered_it():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        {"bead_id": "he-1", "body": "a real brief"}, _option(True), state.ViewState()
    )
    assert 'data-region="prefill-offer"' not in html


def test_the_prefill_fills_the_form_and_records_nothing():
    """Filled in is not recorded -- every one still needs a human confirm."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        {"bead_id": "he-1", "body": ""}, _option(True), state.ViewState(),
        prefill="incomplete",
    )
    revise = re.search(r'<input[^>]*value="revise"[^>]*>', html)
    assert revise and "checked" in revise.group(0)
    assert "required fields" in html
    assert 'name="no_brainer" value="1" checked' in html
    # The offer is gone once taken, and the form is still a form.
    assert 'data-region="prefill-offer"' not in html
    assert '<button class="btn btn-primary" type="submit">' in html


def test_the_prefill_does_not_preselect_approve():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        {"bead_id": "he-1", "body": ""}, _option(True), state.ViewState(),
        prefill="incomplete",
    )
    approve = re.search(r'<input[^>]*value="approve"[^>]*>', html)
    assert approve and "checked" not in approve.group(0)


def test_the_brief_page_has_only_one_adjudication_form():
    """Two forms writing the same field is a chance to submit the wrong one."""
    from mctl_dashboard import render

    html = render.operation_forms(
        "he-1",
        [{"id": "adjudicate", "enabled": True}, {"id": "defer", "enabled": True}],
        rig="hq",
        omit=("adjudicate",),
    )
    assert 'value="adjudicate"' not in html
    assert "Preview adjudication" not in html
    # Defer and dispatch have no other home yet, so they must survive.
    assert 'value="defer"' in html
    assert "Preview deferral" in html


def test_omitting_nothing_keeps_the_legacy_form():
    from mctl_dashboard import render

    html = render.operation_forms("he-1", [{"id": "adjudicate", "enabled": True}], rig="hq")
    assert "Preview adjudication" in html


# --------------------------------------------------------------------------
# reading values the core supplies with provenance
# --------------------------------------------------------------------------


def _fielded(**pairs):
    """A row shaped the way `briefs_list` actually returns one."""
    return {
        "brief_id": "gt-1",
        "title": "t",
        "fields": {k: {"name": k, "value": v, "readings": []} for k, v in pairs.items()},
    }


def test_a_value_under_fields_is_read():
    """`briefs_list` returns most attributes with provenance, not at top level.

    unlock_count is on 185 of 308 live rows -- all of them inside `fields`.
    Reading only the top level saw None everywhere, which then made the
    hide-empty rule hide a column that had data.
    """
    from mctl_dashboard.screens import stack

    assert stack.cell_text(_fielded(unlock_count=7), "unlock") == "7"
    assert stack.cell_text(_fielded(priority=1), "prio") == "1"


def test_a_top_level_value_still_wins():
    from mctl_dashboard.screens import stack

    row = _fielded(unlock_count=7)
    row["unlock_count"] = 9
    assert stack.cell_text(row, "unlock") == "9"


def test_a_genuinely_absent_value_is_still_a_dash():
    from mctl_dashboard.screens import stack

    assert stack.cell_text(_fielded(track="x"), "unlock") == "—"


def test_a_zero_under_fields_is_a_value_not_an_absence():
    from mctl_dashboard.screens import stack

    assert stack.cell_text(_fielded(unlock_count=0), "unlock") == "0"


def test_a_column_with_fielded_data_is_not_hidden():
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    rows = [_fielded(unlock_count=3), _fielded(unlock_count=5)]
    html = stack.table(rows, state.parse({}))
    assert ">Unlock<" in html


# --------------------------------------------------------------------------
# a failed read is not an absent brief
# --------------------------------------------------------------------------


def _dashboard_whose_store_fails_with(code: str):
    """A dashboard whose reads all fail with one diagnostic code."""
    from mctl_dashboard.app import Dashboard
    from mctl_dashboard.client import ToolFailure

    class _Failing:
        def list_tools(self):
            return []

        def call(self, name, arguments=None):
            if name.startswith("briefs_"):
                raise ToolFailure(name, [{"code": code, "message": "x"}], {})
            return type("R", (), {"payload": {}, "artifact_trust": None,
                                  "diagnostics": [], "untrusted_diagnostics": []})()

    return Dashboard(_Failing())


def test_a_brief_that_is_absent_is_a_404():
    from mctl_dashboard.app import Request

    dash = _dashboard_whose_store_fails_with("MBRF010")
    response = dash.handle(Request.get("/briefs/gt-1", rig="hq"))
    assert response.status == 404
    assert "No such brief" in response.body


def test_a_brief_that_could_not_be_read_is_not_a_404():
    """Under load this page called a live brief missing. It had timed out."""
    from mctl_dashboard.app import Request

    dash = _dashboard_whose_store_fails_with("MCTL_STORE_TIMEOUT")
    response = dash.handle(Request.get("/briefs/gt-1", rig="hq"))
    assert response.status == 503
    assert "No such brief" not in response.body
    assert "did not answer" in response.body


def test_the_not_found_code_is_the_only_one_that_claims_absence():
    """Under load the page said "No such brief" about a brief that exists.

    Any ToolFailure was being rendered as a 404. A store that times out is a
    store that did not answer, and telling the operator their bead is gone
    sends them hunting for something that was never missing.
    """
    import inspect

    from mctl_dashboard import app as dash_app

    source = inspect.getsource(dash_app.Dashboard._brief)
    assert 'MBRF010' in source, "the not-found code must gate the 404"
    assert "unreadable" in source
    assert "status=503" in source


# --------------------------------------------------------------------------
# deferral is written to status, not to decision_state
# --------------------------------------------------------------------------


def _deferred_row():
    """A brief as `plan_deferral` actually leaves it.

    `effects.py::plan_deferral` writes `status="deferred"` on the bead.
    `decision_state` is computed separately and never takes that value, so a
    brief someone deliberately deferred still reads as `pending`.
    """
    return {"brief_id": "as-1", "title": "deferred one",
            "status": "deferred", "decision_state": "pending"}


def test_a_deferred_brief_is_deferred():
    from mctl_dashboard.app import is_deferred

    assert is_deferred(_deferred_row())
    assert is_deferred({"decision_state": "deferred"})
    assert not is_deferred({"status": "open", "decision_state": "pending"})


def test_a_deferred_brief_leaves_the_stack():
    """It was sitting in the queue of 115 as if it still needed a verdict."""
    from mctl_dashboard.app import _scoped

    rows = [_deferred_row(), {"brief_id": "b", "decision_state": "pending"}]
    stack_rows = _scoped(rows, "stack")
    assert [r["brief_id"] for r in stack_rows] == ["b"]


def test_a_deferred_brief_reaches_the_deferred_lane():
    from mctl_dashboard.app import _in_lane

    assert _in_lane(_deferred_row(), "deferred")
    assert not _in_lane({"decision_state": "pending"}, "deferred")


def test_the_other_lanes_are_unchanged():
    from mctl_dashboard.app import _in_lane

    assert _in_lane({"decision_state": "adjudicated"}, "adjudicated")
    assert _in_lane({"decision_state": "malformed"}, "malformed")
    assert not _in_lane(_deferred_row(), "adjudicated")


def test_one_brief_is_not_one_briefs():
    from mctl_dashboard.screens import pipeline

    html = pipeline.deferred([{"brief_id": "a", "status": "deferred"}])
    assert "1 brief<" in html or "1 brief " in html or ">1 brief" in html
    assert "1 briefs" not in html
