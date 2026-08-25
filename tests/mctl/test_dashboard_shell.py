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

from mctl_dashboard import staleness
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
