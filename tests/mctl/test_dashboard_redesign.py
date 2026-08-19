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
