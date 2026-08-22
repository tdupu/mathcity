"""Unusable briefs get their own lane. They are never hidden.

Taylor, correcting the filter that shipped:

    "I should be able to SEE other briefs. I just want the adjudication menu
     taken away if I can't rule on them."
    "They should really be separated out as like 'junk briefs' or something.
     It is a good signal for debugging."

The first version filtered unrulable briefs out of the queue entirely. That
was wrong in the way this dashboard keeps finding wrong elsewhere: **the page
looks healthy because the unhealthy rows are gone.** A hidden brief is a brief
nobody debugs, and the person best placed to notice a broken population was
the one person the filter hid it from.

**`MBRF004` is NOT junk.** Taylor's condition is "if I can't rule on them",
and an `MBRF004` brief CAN be ruled on -- the gate stops `approve` and leaves
`revise` and `reject` live, measured against `mctl` on a real brief, all three
verdicts. Those briefs stay in the stack with the approve control inert and
the reason on the row. Sweeping them into junk would take away the only
action currently available on ~70 of ~90 open briefs.

So "junk" means exactly one thing, and it is drawn from the write path's own
behaviour rather than from a hand-maintained taxonomy:

    no verdict of any kind can land on this brief

which today is: no canonical bead (`MBRF010`), malformed, already adjudicated.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import is_junk, junk_reason, rulable


def _brief(**over):
    row = {"brief_id": "b", "decision_state": "pending", "bead_id": "b", "rig_id": "hq"}
    row.update(over)
    return row


def _mbrf004(**over):
    return _brief(diagnostics=[{"code": "MBRF004", "severity": "ERROR"}], **over)


# ---------------------------------------------------------------------------
# what junk means
# ---------------------------------------------------------------------------


def test_a_brief_with_no_bead_is_junk():
    """MBRF010: adjudicate refuses it outright. No verdict can land."""
    assert is_junk(_brief(bead_id=None)) is True


def test_an_mbrf004_brief_is_NOT_junk():
    """The distinction that must not be lost.

    approve is gated; revise and reject are live. Taylor can still act on it,
    so it belongs in the stack.
    """
    assert is_junk(_mbrf004()) is False


def test_an_mbrf004_brief_is_still_rulable():
    assert rulable(_mbrf004()) is True


def test_an_ordinary_open_brief_is_not_junk():
    assert is_junk(_brief()) is False


# ---------------------------------------------------------------------------
# the reason is stated, with its code
# ---------------------------------------------------------------------------


def test_the_reason_names_the_code():
    """He should read why without clicking through -- clicking to discover
    you cannot act was the original complaint."""
    reason = junk_reason(_brief(bead_id=None))
    assert reason and "MBRF010" in reason


def test_a_usable_brief_has_no_junk_reason():
    assert junk_reason(_brief()) is None


def test_an_mbrf004_brief_has_no_junk_reason():
    assert junk_reason(_mbrf004()) is None


# ---------------------------------------------------------------------------
# the stack stops hiding; junk gets its own lane
# ---------------------------------------------------------------------------


def _city(tmp_path):
    import multi_rig
    from mctl_dashboard.app import Dashboard
    from mctl_dashboard.client import InProcessMcpClient

    fixture = multi_rig.build(tmp_path)
    client = InProcessMcpClient(city=fixture.city_root, env=fixture.env)
    return Dashboard(client, city_wide=True, rig=None)


def _rows(app, path):
    import re

    from mctl_dashboard.app import Request

    body = app.handle(Request.get(path)).body
    # The stack renders rows as `data-href`; the pipeline lanes render them as
    # plain `<a href>`. Match both so this helper describes "a link to a
    # brief" rather than one screen's markup.
    return re.findall(r'(?:data-)?href="(/briefs/[^"]+)"', body), body


def test_the_stack_no_longer_hides_a_junk_brief_by_vanishing_it(tmp_path):
    """It leaves the stack because it is IN THE JUNK LANE, not because it
    was filtered into nothing. The fixture's `legacy-unmapped` has no bead."""
    app = _city(tmp_path)
    stack_hrefs, _ = _rows(app, "/queue")
    junk_hrefs, _ = _rows(app, "/junk")
    assert junk_hrefs, "the junk lane rendered no rows; this test cannot fail"
    assert any("legacy-unmapped" in h for h in junk_hrefs), "junk brief is nowhere"
    assert not any("legacy-unmapped" in h for h in stack_hrefs)


def test_the_junk_lane_states_the_reason_with_its_code(tmp_path):
    _, body = _rows(_city(tmp_path), "/junk")
    assert "MBRF010" in body


def test_the_stack_still_shows_rulable_briefs(tmp_path):
    """The guard: the lane split must not empty the queue it exists to sharpen."""
    stack_hrefs, _ = _rows(_city(tmp_path), "/queue")
    assert stack_hrefs


def test_the_queue_shows_the_junk_count_without_opening_the_lane(tmp_path):
    """The size of the problem is the debugging signal he asked for."""
    _, body = _rows(_city(tmp_path), "/queue")
    assert 'data-region="junk-count"' in body
