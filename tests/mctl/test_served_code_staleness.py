"""`#164`: the served page never says how old the code behind it is.

Taylor's dashboard was pid 25400, started 10:20, **seven hours stale** — it
predated `#160`, `#117`, `#109`/`#111` and `#128`. Molecules and Orders+Formulas
were merged and not on his page while he was being told they rendered. Three
times in one day, and each time a human had to notice and bounce a process.

The dashboard is a long-running process that loaded its Python once. Nothing
about that is wrong. What is wrong is that **the page cannot say so**: it
renders merged-and-absent features identically to never-built ones, and an
operator reading it has no way to tell "this feature does not exist" from "this
process predates it".

This does not restart anything. Restarting is a decision with an owner and a
blast radius; **saying what you are serving is not.** An operator who can see
"serving code from 7 hours and 14 commits ago" can act; one who cannot is being
quietly misinformed by a page that looks current.

**P6.2 applies to the staleness check itself.** If the comparison cannot be
made — no git, detached checkout, unreadable ref — the banner says the age is
unknown. It must never render "current" from a check that did not run, which
would be the same defect one level up.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard import staleness


def test_same_commit_is_not_stale():
    s = staleness.compare(served="abc1234", current="abc1234")
    assert s.is_stale is False
    assert s.is_known is True


def test_a_different_commit_is_stale():
    s = staleness.compare(served="abc1234", current="def5678")
    assert s.is_stale is True
    assert s.is_known is True


def test_an_unknown_current_commit_is_not_reported_as_current():
    """The P6.2 case, applied to this check.

    If we cannot read the checkout's HEAD we do not know whether the process
    is stale. Rendering that as "up to date" is the exact failure this banner
    exists to prevent, one level up.
    """
    s = staleness.compare(served="abc1234", current=None)
    assert s.is_known is False
    assert s.is_stale is False  # not a claim of freshness -- see is_known


def test_an_unknown_served_commit_is_also_unknown():
    s = staleness.compare(served=None, current="abc1234")
    assert s.is_known is False


# ---------------------------------------------------------------------------
# what the page says
# ---------------------------------------------------------------------------


def test_a_stale_page_says_so_and_names_both_commits():
    html = staleness.banner(staleness.compare(served="abc1234", current="def5678"))
    assert "abc1234" in html and "def5678" in html
    assert "restart" in html.lower()


def test_a_current_page_states_it_rather_than_staying_silent():
    """Silence is what we are removing. A page that says nothing about its own
    age is indistinguishable from one that has never been checked."""
    html = staleness.banner(staleness.compare(served="abc1234", current="abc1234"))
    assert "abc1234" in html


def test_an_unknown_comparison_says_unknown_not_current():
    html = staleness.banner(staleness.compare(served="abc1234", current=None))
    low = html.lower()
    assert "unknown" in low or "could not" in low
    assert "up to date" not in low


# ---------------------------------------------------------------------------
# structural: a screen cannot omit it
# ---------------------------------------------------------------------------


def test_the_shell_always_emits_the_served_code_region():
    """Same guarantee as the provenance badge, for the same reason: a screen
    cannot forget what it does not build."""
    from mctl_dashboard import render

    assert 'data-region="served-code"' in render.page("t", "queue", ["<p>x</p>"])


def test_the_banner_is_not_behind_a_conditional():
    """`if staleness:` around the call would reintroduce the omission."""
    from pathlib import Path

    src = (ROOT / "assets" / "scripts" / "mctl_dashboard" / "render.py").read_text()
    body = src[src.index("def page("):]
    line = next(l for l in body.splitlines() if "staleness_banner" in l and "(" in l)
    assert line.strip().startswith("staleness_banner("), line
