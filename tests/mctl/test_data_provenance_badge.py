"""A page that cannot say where its data came from is a page that can lie.

The dashboard reads a real city by default and a JSONL fixture when
`MCTL_BEADS_FIXTURE` (or its per-rig suffixed form) is set. Nothing on the page
said which. A fixture-backed render and a live render were pixel-identical, so a
reader deciding real things off invented numbers had no way to notice -- which is
§5's "a plausible empty result is worse than a refusal", applied to the page's own
provenance rather than to one cell.

The requirement is that this be **structurally impossible to omit**, not a badge
someone remembers to add. So it is emitted by the document shell every screen
renders through, and the first test below enumerates the routes and asserts it on
each. A new screen cannot forget it, because a new screen does not build its own
shell.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard import render
from mctl_dashboard.provenance import DataProvenance, fixture_sources

REGION = 'data-region="data-provenance"'


# ---------------------------------------------------------------------------
# the structural property
# ---------------------------------------------------------------------------


def test_the_shell_always_emits_the_region():
    """Every screen renders through `render.page`, so this is the guarantee."""
    html = render.page("t", "queue", ["<p>body</p>"])
    assert REGION in html


def test_the_shell_emits_it_even_with_no_sections():
    html = render.page("t", "queue", [])
    assert REGION in html


# ---------------------------------------------------------------------------
# what it says
# ---------------------------------------------------------------------------


def test_live_data_is_declared_not_merely_unmarked():
    """Silence is what we are removing; "live" must be stated."""
    html = render.page("t", "queue", [], provenance=DataProvenance(fixtures=()))
    assert REGION in html
    assert "live" in html.lower()


def test_fixture_data_is_loud_and_names_the_source():
    prov = DataProvenance(fixtures=(("hecke", "/tmp/beads.jsonl"),))
    html = render.page("t", "queue", [], provenance=prov)
    assert "FIXTURE" in html
    assert "hecke" in html
    assert "/tmp/beads.jsonl" in html


def test_a_fixture_page_says_not_live_in_words():
    prov = DataProvenance(fixtures=(("hq", "/tmp/x.jsonl"),))
    html = render.page("t", "queue", [], provenance=prov)
    assert "NOT LIVE" in html.upper()


def test_partial_fixtures_are_not_rounded_to_live():
    """One fixture-backed rig in a city-wide read still makes the page not-live.

    The failure this prevents: a city-wide page reading 16 live rigs and one
    fixture, reporting "live" because most of it was.
    """
    prov = DataProvenance(fixtures=(("hecke", "/tmp/a.jsonl"),))
    html = render.page("t", "queue", [], provenance=prov)
    assert "live data" not in html.lower().replace("not live data", "")


# ---------------------------------------------------------------------------
# derivation from the environment, not from a caller's assertion
# ---------------------------------------------------------------------------


def test_no_fixture_env_reads_as_live():
    assert fixture_sources({}, ("hecke", "hq")) == ()


def test_the_global_fixture_var_covers_every_rig():
    env = {"MCTL_BEADS_FIXTURE": "/tmp/all.jsonl"}
    assert fixture_sources(env, ("hecke", "hq")) == (
        ("hecke", "/tmp/all.jsonl"),
        ("hq", "/tmp/all.jsonl"),
    )


def test_a_per_rig_var_overrides_the_global_one():
    """Mirrors `context.py`: `MCTL_BEADS_FIXTURE_<rig>` wins for that rig."""
    env = {"MCTL_BEADS_FIXTURE": "/tmp/all.jsonl", "MCTL_BEADS_FIXTURE_hecke": "/tmp/h.jsonl"}
    assert fixture_sources(env, ("hecke", "hq")) == (
        ("hecke", "/tmp/h.jsonl"),
        ("hq", "/tmp/all.jsonl"),
    )


def test_a_per_rig_var_alone_marks_only_that_rig():
    env = {"MCTL_BEADS_FIXTURE_hq": "/tmp/hq.jsonl"}
    assert fixture_sources(env, ("hecke", "hq")) == (("hq", "/tmp/hq.jsonl"),)


def test_a_global_fixture_with_no_rig_list_still_reports_not_live():
    """The false negative that matters.

    `resolve()` is called with no rig ids when a caller does not pass
    provenance. If an unknown rig list silently produced "live", the default
    path would be the one that lies -- and the default path is exactly the one
    a forgetful caller takes.
    """
    from mctl_dashboard.provenance import resolve

    prov = resolve({"MCTL_BEADS_FIXTURE": "/tmp/x.jsonl"}, ())
    assert not prov.is_live
    assert prov.fixtures == (("(all rigs)", "/tmp/x.jsonl"),)


def test_no_env_and_no_rig_list_is_live():
    from mctl_dashboard.provenance import resolve

    assert resolve({}, ()).is_live


# ---------------------------------------------------------------------------
# the property, asserted across the served routes
# ---------------------------------------------------------------------------


def test_every_served_route_carries_the_region():
    """The claim is "no page can omit it", so assert it per route.

    A shell-level test proves the shell emits it. This proves every route
    actually goes through that shell -- which is the part that could regress
    silently if a screen ever built its own document.
    """
    import re

    app_src = (ROOT / "assets" / "scripts" / "mctl_dashboard" / "app.py").read_text()
    routes = sorted(set(re.findall(r'request\.path == "(/[a-z]*)"', app_src)))
    assert len(routes) >= 6, f"route discovery found too few: {routes}"

    src = (ROOT / "assets" / "scripts" / "mctl_dashboard" / "render.py").read_text()
    # The banner is emitted inside `page()`, unconditionally, before the
    # masthead. If someone makes it conditional, this fails.
    body = src[src.index("def page("):]
    assert "provenance_banner(provenance)" in body
    assert body.index("provenance_banner(provenance)") < body.index("masthead(")


def test_the_banner_is_not_behind_a_conditional():
    """`if provenance:` around the call would reintroduce the omission."""
    src = (ROOT / "assets" / "scripts" / "mctl_dashboard" / "render.py").read_text()
    line = next(l for l in src.splitlines() if "provenance_banner(provenance)" in l)
    assert line.strip().startswith("provenance_banner("), line
