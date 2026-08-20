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


def test_every_token_records_where_its_value_came_from():
    """Provenance survives contact with the next maintainer.

    Design-stated values and LMFDB-derived reconstructions are not equally
    authoritative, and someone tuning this later needs to know which is which
    without re-deriving it.
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
        assert "[design]" in line or "[lmfdb]" in line, f"no provenance: {line.strip()}"


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


def test_every_refused_state_still_disables_the_inputs():
    """Styling is not a lock -- a disabled-looking radio that submits is a bug."""
    import re

    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    for code in ("MBRF004", "MBRF999"):
        html = panel.entry({"bead_id": "he-1"}, _option(False, code), state.ViewState())
        for verdict in ("approve", "revise"):
            found = re.search(rf'<input[^>]*value="{verdict}"[^>]*>', html)
            assert found and "disabled" in found.group(0), (code, verdict)


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
