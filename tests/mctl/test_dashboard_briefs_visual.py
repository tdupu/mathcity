"""Structural tests for the Brief Manager visual port.

These cover the pieces the visual-design pass added on top of the redesigned
surface, each of which fails *silently* in a browser if it regresses, so it is
asserted here rather than eyeballed:

* the two OFL typefaces travel inside the stylesheet as `data:` URIs, so the
  page is self-contained with no `/fonts/` request and nothing to phone out
  for (design handoff: "embed the fonts", repo GC1/GC2: a loopback tool must
  not fetch);
* the `FIXTURES · NOT LIVE DATA` badge the DRIFT demands "before anyone sees
  the prototype" renders in the shell whenever the data is not live (repo P6.2
  honesty invariant);
* the §4 alternatives are click-to-adopt: one link fills approve + the option +
  a reason quoting it, with JavaScript off;
* the triage-first stack carries `resolve →` / `send back →` row actions on the
  rows whose data qualifies for one;
* every count the shell shows derives from the counts mapping it is handed, not
  an authored literal (convention F33).

They are deliberately kept out of `test_dashboard_redesign.py` so the two files
can move independently.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


# --------------------------------------------------------------------------
# fonts embedded as data: URIs
# --------------------------------------------------------------------------


def test_the_fonts_are_embedded_as_data_uris_not_a_fonts_route():
    """The typeface travels inside the stylesheet, not over a second request."""
    from mctl_dashboard import theme

    assert "data:font/woff2;base64," in theme.STYLESHEET
    # No served-font URL survives: the page must be self-contained.
    assert "url('/fonts/" not in theme.STYLESHEET
    assert 'url("/fonts/' not in theme.STYLESHEET


def test_one_face_is_embedded_per_present_font_file():
    """Every vendored `.woff2` becomes exactly one `@font-face` with its bytes."""
    from mctl_dashboard import theme

    present = [name for name in theme.FONT_FILES if (theme.FONT_DIR / name).is_file()]
    faces = theme.STYLESHEET.count("data:font/woff2;base64,")
    assert faces == len(present) == 3


def test_embedded_fonts_do_not_reintroduce_a_remote_fetch():
    """Embedding must not smuggle an http(s) URL back into the sheet."""
    from mctl_dashboard import theme

    assert "http://" not in theme.STYLESHEET
    assert "https://" not in theme.STYLESHEET


# --------------------------------------------------------------------------
# FIXTURES badge (repo P6.2 honesty invariant)
# --------------------------------------------------------------------------


def test_the_fixtures_badge_renders_when_data_is_not_live():
    from mctl_dashboard import render
    from mctl_dashboard.provenance import DataProvenance

    html = render.provenance_banner(DataProvenance(fixtures=(("hecke", "/x/fix.json"),)))
    assert "FIXTURES" in html and "NOT LIVE DATA" in html
    assert 'data-live="false"' in html


def test_the_fixtures_badge_is_absent_on_live_data():
    from mctl_dashboard import render
    from mctl_dashboard.provenance import DataProvenance

    html = render.provenance_banner(DataProvenance(fixtures=()))
    assert "FIXTURES" not in html
    assert 'data-live="true"' in html


def test_the_shell_emits_the_provenance_region_on_every_page():
    """The badge is emitted by the shell, so no screen can forget it."""
    from mctl_dashboard import render
    from mctl_dashboard.provenance import DataProvenance

    page = render.page(
        "T", "/queue", ["<p>body</p>"],
        provenance=DataProvenance(fixtures=(("hecke", "/x"),)),
    )
    assert 'data-region="data-provenance"' in page
    assert "FIXTURES" in page


# --------------------------------------------------------------------------
# §4 click-to-adopt
# --------------------------------------------------------------------------


_BRIEF = {
    "bead_id": "he-1",
    "brief_id": "he-1",
    "decision_options": [
        {"label": "A", "title": "Merge as filed"},
        {"label": "B", "title": "Split first"},
    ],
}


def _open_option():
    return [{"id": "adjudicate", "enabled": True}]


def test_each_named_option_carries_an_adopt_link():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_BRIEF, _open_option(), state.ViewState(), rig="hecke")
    assert 'data-region="adopt-option"' in html
    assert "prefill=adopt:A" in html and "prefill=adopt:B" in html
    # The adopt link is a link, not a script hook, and lands on the panel.
    assert "#mc-adjudicate" in html


def test_adopting_an_option_fills_approve_the_option_and_a_quoted_reason():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        _BRIEF, _open_option(), state.ViewState(), rig="hecke", prefill="adopt:B"
    )
    # Verdict approve is preselected...
    assert re.search(r'value="approve"[^>]*checked', html)
    # ...the option radio for B is selected...
    assert re.search(r'name="option" value="B"[^>]*checked', html)
    # ...and the reason quotes the option in the brief's own words.
    assert "Adopting option B: Split first." in html


def test_adopt_preselects_only_its_own_option_not_accept_as_filed():
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(
        _BRIEF, _open_option(), state.ViewState(), prefill="adopt:A"
    )
    # "Accept the recommendation as filed" (value="") must NOT be checked when
    # a specific option was adopted.
    assert not re.search(r'name="option" value=""[^>]*checked', html)
    assert re.search(r'name="option" value="A"[^>]*checked', html)


def test_click_to_adopt_stays_preview_first():
    """Adopting fills the form; it never writes. The form still posts /preview."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    html = panel.entry(_BRIEF, _open_option(), state.ViewState(), prefill="adopt:A")
    assert 'action="/preview"' in html
    # No adopt link points at a mutation route.
    assert 'href="/apply' not in html and 'href="/preview' not in html


# --------------------------------------------------------------------------
# triage-first stack row actions
# --------------------------------------------------------------------------


def test_an_untitled_brief_offers_send_back():
    from mctl_dashboard.screens import stack

    html = stack._quick_action({"bead_id": "he-2", "title": ""}, "he-2", "hecke")
    assert "send back" in html
    assert "prefill=incomplete" in html
    assert 'class="mc-quick"' in html


def test_a_no_brainer_row_offers_resolve():
    from mctl_dashboard.screens import stack

    html = stack._quick_action({"title": "Real", "kind": "nobrainer"}, "he-4", "hecke")
    assert "resolve" in html
    assert "#mc-adjudicate" in html


def test_an_ordinary_row_offers_no_quick_action():
    from mctl_dashboard.screens import stack

    assert stack._quick_action({"title": "Real work", "kind": ""}, "he-3", "hecke") == ""


def test_the_quick_action_renders_in_the_stack_table():
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table(
        [{"bead_id": "he-2", "brief_id": "he-2", "title": "", "rig_id": "hecke"}],
        state.ViewState(),
    )
    assert 'data-region="quick-action"' in html
    assert "send back" in html


def test_the_quick_action_never_writes_directly():
    """Row actions are links into the panel, not a mutation route."""
    from mctl_dashboard.screens import stack

    for brief, bid in (
        ({"title": "", "bead_id": "e"}, "e"),
        ({"title": "x", "kind": "nobrainer"}, "n"),
    ):
        html = stack._quick_action(brief, bid, "hecke")
        assert "/preview" not in html and "/apply" not in html


# --------------------------------------------------------------------------
# F33: counts derive from the query, never an authored literal
# --------------------------------------------------------------------------


def test_the_masthead_counts_come_from_the_counts_mapping():
    from mctl_dashboard import render

    html = render.masthead({"stack": 7, "errors": 2}, {"city_root": "~/gt"})
    assert ">7<" in html.replace(" ", "")  # the stack count is the one passed
    assert ">2<" in html.replace(" ", "")


def test_a_count_not_measured_is_a_dash_not_a_zero():
    from mctl_dashboard import render

    html = render.masthead({"stack": 7}, {"city_root": "~/gt"})
    # pile has no source in the typed surface: it must show a dash, not 0.
    assert "&mdash;" in html
    assert "pile 0" not in html


# --------------------------------------------------------------------------
# stoplight table renders with its edge tints
# --------------------------------------------------------------------------


def test_a_warn_brief_row_carries_the_warn_stoplight_edge():
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack
    from mctl_dashboard.theme import STOP

    warn_brief = {
        "bead_id": "he-9",
        "brief_id": "he-9",
        "title": "Degraded but decidable",
        "rig_id": "hecke",
        "diagnostics": [{"severity": "WARN", "code": "MBRF999"}],
    }
    html = stack.table([warn_brief], state.ViewState())
    assert f"inset 3px 0 0 {STOP['warn']['edge']}" in html
