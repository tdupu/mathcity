"""Shell defects visible on every page (rev spec sections 6.1, 6.2, 6.4).

The shell is the chrome every screen renders through -- the staleness banner,
the masthead's runtime line, and the footer. Three things it got wrong, each
measured from saved pages of the running instance:

* 6.1 The staleness banner emitted a bare ``<p class="review-note">`` above the
  masthead, so the first thing on the page was a loose, un-bannered paragraph
  sitting above the brand. It must get the same full-width banner treatment the
  provenance banner has -- a real banner in the shell, not a paragraph.
* 6.2 The masthead showed ``store mathcity`` because ``context["rig_db"]`` had
  fallen back to the rig id (``context_resolve`` defaults ``rig_db`` to the rig
  id when no db is configured). The store cell must name the honest bead store,
  not echo the rig name.
* 6.4 The footer dropped the trace id on lane and brief pages because the shell
  was never handed one. The context payload the shell already carries names a
  ``trace_id``; the footer must surface it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard import render, staleness
from mctl_dashboard.theme import STYLESHEET


# ---------------------------------------------------------------------------
# 6.1 The staleness banner is a real shell banner, not a loose paragraph
# ---------------------------------------------------------------------------


def test_staleness_banner_is_a_block_banner_not_a_review_note_paragraph():
    """The banner must be a full-width shell banner, like the provenance one --
    not the inset ``review-note`` paragraph style meant for use inside panels."""
    html = staleness.banner(staleness.compare(served="abc1234", current="def5678"))
    assert html.lstrip().startswith("<div"), html[:80]
    assert 'class="review-note"' not in html
    assert "mc-banner" in html
    assert 'data-region="served-code"' in html


def test_every_staleness_state_renders_as_a_banner():
    """Stale, fresh and unknown all render through the same banner treatment."""
    for state in (
        staleness.compare(served="abc1234", current="def5678"),  # stale
        staleness.compare(served="abc1234", current="abc1234"),  # fresh
        staleness.compare(served="abc1234", current=None),       # unknown
    ):
        html = staleness.banner(state)
        assert html.lstrip().startswith("<div"), html[:80]
        assert "mc-banner" in html
        assert 'class="review-note"' not in html


def test_theme_defines_the_shell_banner_class():
    """The banner styling lives in the theme, alongside the other shared CSS."""
    assert ".mc-banner" in STYLESHEET


# ---------------------------------------------------------------------------
# 6.2 The masthead names the real store, not the rig id
# ---------------------------------------------------------------------------


def test_masthead_store_is_the_bead_store_not_the_rig_id():
    """When ``rig_db`` has fallen back to the rig id, the masthead must show the
    honest bead store (``.beads``), not the rig name repeated as a store."""
    html = render.masthead(
        {},
        {"city_root": "~/gt", "rig_id": "mathcity", "rig_db": "mathcity"},
    )
    assert ">store</span> .beads" in html
    # the rig name must not be presented as the store
    assert ">store</span> mathcity" not in html


def test_masthead_store_keeps_a_genuinely_distinct_store_name():
    """A configured store name that is not just the rig id echoed back is real
    information and is shown as-is."""
    html = render.masthead(
        {},
        {"city_root": "~/gt", "rig_id": "mathcity", "rig_db": "fixture_mathcity"},
    )
    assert ">store</span> fixture_mathcity" in html


# ---------------------------------------------------------------------------
# 6.4 The footer carries the trace id on lane and brief pages
# ---------------------------------------------------------------------------


def test_footer_shows_the_trace_id_from_the_context_payload():
    """Lane and brief pages hand the shell a context carrying a ``trace_id``;
    the footer must surface it even when no explicit trace_id is passed."""
    html = render.page(
        "Brief",
        "/briefs",
        ["<section>x</section>"],
        context={"rig_id": "mathcity", "rig_db": "mathcity", "trace_id": "trace-abc123"},
    )
    footer = html.split('data-region="footer"', 1)[1]
    assert "trace-abc123" in footer


def test_an_explicit_trace_id_wins_over_the_context_trace():
    """A caller that passes a specific trace_id is not overridden by context."""
    html = render.page(
        "x",
        "/queue",
        [],
        trace_id="explicit-1",
        context={"trace_id": "ctx-2"},
    )
    footer = html.split('data-region="footer"', 1)[1]
    assert "explicit-1" in footer
    assert "ctx-2" not in footer


def test_no_trace_anywhere_leaves_the_footer_without_one():
    """No trace in the context and none passed: the footer omits it rather than
    inventing an empty one."""
    html = render.page("x", "/queue", [], context={"rig_id": "mathcity"})
    footer = html.split('data-region="footer"', 1)[1]
    assert "trace " not in footer


# --- restart button in the staleness banner (Taylor: "a restart button would be nice") ---


def test_stale_banner_offers_a_one_click_restart():
    """When the served code is behind the checkout, the banner carries a real
    restart control -- a plain POST form to /restart (JS-off), not just prose."""
    from mctl_dashboard import staleness

    html = staleness.banner(staleness.compare(served="aaaaaaa", current="bbbbbbb"))
    assert 'action="/restart"' in html
    assert 'method="post"' in html
    assert 'data-region="restart"' in html


def test_unknown_age_banner_also_offers_restart():
    from mctl_dashboard import staleness

    html = staleness.banner(staleness.compare(served="aaaaaaa", current=None))
    assert 'action="/restart"' in html


def test_clean_banner_has_no_restart_button():
    """A process that matches its checkout needs no restart affordance."""
    from mctl_dashboard import staleness

    html = staleness.banner(staleness.compare(served="aaaaaaa", current="aaaaaaa"))
    assert "/restart" not in html


def test_restart_is_not_a_mutation_route():
    """The restart is a server-lifecycle action, not a brief write; the two
    brief-write routes stay exactly what they were."""
    from mctl_dashboard.app import Dashboard

    assert Dashboard.MUTATION_ROUTES == ("/preview", "/apply")
