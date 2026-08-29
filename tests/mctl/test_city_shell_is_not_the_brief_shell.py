"""The city dashboard must not render as the brief manager.

Before the city shell existed, `/city` went through `render.page()`, which
unconditionally emits the brief masthead ("Brief Manager"), the brief keyboard
map, and the brief pipeline sidebar (Stack / Pile / Adjudicated / priority
list). The city page therefore branded itself as the wrong instrument, offered
six keyboard bindings that do nothing on a page of panels, and -- because the
city routes pass no `counts` -- rendered every pipeline chip blank, which reads
as "this city has no briefs" rather than "this page never asked".

EVERY assertion here is paired with a POSITIVE CONTROL on a brief route. An
assertion that `/city` lacks "Brief Manager" is worthless on its own: it also
passes if the string is spelled differently, if the shell stopped rendering, or
if the route 500s. The control proves the same probe finds the string where it
genuinely belongs, so a failure means the city page changed and not that the
test went blind.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_dashboard import render


#: Furniture that belongs to the brief manager and must never appear on a city
#: page. Each is load-bearing: these are controls that silently do nothing
#: outside the brief pipeline.
#:
#: "Brief Manager" is deliberately NOT a bare substring here. The city sidebar
#: links back to the brief dashboard ("Brief Manager — stack"), which is wanted:
#: the two share a port and an operator needs a route between them. What must
#: not appear is the WORDMARK -- the page claiming to *be* the brief manager --
#: so that is asserted separately, in its exact masthead form.
BRIEF_ONLY = (
    "Pile — awaiting gates",
    "Adjudicated — closed",
    "My priority list",
    "No-brainers — DRY RUN",
)

#: The wordmark as `masthead()` emits it. Matching the closing tag is what
#: separates "brands itself Brief Manager" from "links to the Brief Manager".
BRIEF_WORDMARK = ">Brief Manager</div>"


def _city_html() -> str:
    return render.city_page(
        "City",
        "/city",
        ["<section>panel</section>"],
        context={"city_root": "/tmp/city"},
        state={"rigs": "17/18 healthy", "panes": "6/18", "data_plane": "reachable"},
    )


def _brief_html() -> str:
    return render.page(
        "Queue",
        "/queue",
        ["<section>panel</section>"],
        context={"city_root": "/tmp/city"},
        counts={"stack": 3, "adjudicated": 1},
    )


def test_city_page_carries_none_of_the_brief_furniture() -> None:
    """The city shell drops all five, and the brief shell still has them.

    The second half is the control. Without it this test would pass on a
    `city_page` that returned the empty string.
    """
    city = _city_html()
    brief = _brief_html()
    for marker in BRIEF_ONLY:
        assert marker not in city, f"city page still renders brief furniture: {marker!r}"
        # CONTROL: the same substring probe, on the shell that should have it.
        assert marker in brief, (
            f"positive control failed: {marker!r} is absent from the BRIEF shell too, "
            "so this test cannot distinguish a fixed city page from a broken probe"
        )


def test_city_page_does_not_brand_itself_as_the_brief_manager() -> None:
    """The wordmark, not the word.

    Linking to the brief dashboard is wanted; claiming to be it is the defect.
    """
    city = _city_html()
    assert BRIEF_WORDMARK not in city
    # CONTROL: the brief shell carries the wordmark in exactly this form, so a
    # pass above means the city shell dropped it rather than the markup moving.
    assert BRIEF_WORDMARK in _brief_html()
    # And the wanted cross-link is still there -- guarding the over-correction
    # of deleting the route between the two dashboards to make a test pass.
    assert "Brief Manager — stack" in city


def test_city_page_identifies_itself_as_the_city() -> None:
    city = _city_html()
    assert "City Operations" in city
    assert "<title>City - city operations</title>" in city
    # CONTROL: the brief shell must NOT claim to be the city, or the wordmark
    # assertion above would pass on a shell that branded everything the same.
    assert "City Operations" not in _brief_html()


def test_city_page_offers_the_city_surfaces_not_the_brief_lanes() -> None:
    city = _city_html()
    for href, _label in render.CITY_NAV:
        assert f'href="{href}"' in city
    # The cross-link back is deliberate: two dashboards share a port and an
    # operator needs a route between them that is not the back button.
    assert "Brief Manager — stack" in city


def test_city_key_map_does_not_advertise_bindings_that_do_nothing() -> None:
    """The brief bindings act on a row cursor; the city page has no rows."""
    city = _city_html()
    for binding in ("next row", "previous row", "open the brief under the cursor"):
        assert binding not in city
    # CONTROL: those phrases exist in the brief key map, so their absence here
    # is a property of the city shell rather than of the wording.
    brief = _brief_html()
    assert "next row" in brief


def test_absent_city_state_renders_as_a_dash_never_as_zero() -> None:
    """A value the page did not read must not render as a measured zero.

    This is the defect that shipped in the first cut of the masthead: the chip
    read `rigs` from a key `city_health` does not use, got nothing, and printed
    "0 healthy" above a panel listing eighteen rigs.
    """
    blank = render.city_page("City", "/city", [], context={}, state={})
    assert "&mdash;" in blank or "—" in blank
    assert "0 healthy" not in blank
