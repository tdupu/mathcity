"""An adjudication that does not reach TIER_ADJUDICATED did not count.

`classify_tier` (materialize_plan.py:292-298) is what decides whether a brief was
disposed of. `materialize_plan.py:379` then uses that tier to decide whether a
materialized bead is created `closed` or `open`. So a verdict that fails to reach
`A-adjudicated` does not merely carry a cosmetic label -- it re-materializes as
OPEN WORK, with the verdict sitting on the bead and the tier saying nobody decided.

Measured on a real MCP adjudication (`gsp-4xwync`, 2026-08-21): closed, verdict
`reject`, `adjudicated_at` set -- classifies `C-no-disposition`.

TWO INDEPENDENT CAUSES, and these tests separate them on purpose, because fixing
either one alone leaves the path broken and the other invisible:

  1. `adjudicated_by` is never written by the adjudicate effect.
  2. `classify_tier` reads all three fields from the brief document's FRONTMATTER,
     and `briefs_create` emits a document with no frontmatter block at all
     (effects.py:220 says so in its own words).

Cause 1 alone is what `test_the_legacy_lane_...` isolates: that fixture's document
HAS frontmatter, so only the missing authorizer can fail it. If someone fixes the
authorizer and only that test goes green, cause 2 is still live and this file still
says so.

HOW THESE COULD FAIL (P6.2): the control below hands `classify_tier` a complete
frontmatter dict and asserts `A-adjudicated`. If the classifier itself were broken
or the constant renamed, the control fails and the two red tests below mean nothing.
Without it, "does not reach TIER_ADJUDICATED" could be satisfied by a classifier
that never returns that tier for any input.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
SCRIPTS = Path(__file__).resolve().parents[2] / "assets" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mctl_core.materialize_plan import (  # noqa: E402
    TIER_ADJUDICATED,
    TIER_OPEN,
    classify_tier,
)
from test_adjudication_writes_decisions_track_row import (  # noqa: E402
    LEGACY_ID,
    _build,
    adjudicate,
    read_frontmatter,
)


@pytest.fixture
def legacy(tmp_path: Path):
    return _build(tmp_path, LEGACY_ID)


# --- CONTROL --------------------------------------------------------------
def test_control_the_classifier_does_return_the_adjudicated_tier():
    """If this fails, the two tests below prove nothing about adjudication."""
    complete = {
        "verdict": "reject",
        "adjudicated_by": "someone",
        "adjudicated_at": "2026-08-21T19:41:14Z",
    }
    assert classify_tier(complete) == TIER_ADJUDICATED

    # And it must NOT reach the tier on a verdict alone -- otherwise the
    # authorizer requirement below is not a requirement.
    assert classify_tier({"verdict": "reject"}) != TIER_ADJUDICATED


# --- CAUSE 1, isolated: the authorizer is never written --------------------
#: strict=True is load-bearing. A plain xfail reports XPASS and stays GREEN when
#: the defect is fixed, so the marker would outlive it silently and this file would
#: become a test that cannot fail. Strict makes the day it is fixed a loud failure
#: whose remedy is deleting the marker -- so the fix and the test that named the
#: defect stay attached. Pattern established by trans on #137.
@pytest.mark.xfail(
    reason="#155 cause 1: the adjudicate effect never writes adjudicated_by",
    strict=True,
)
def test_the_legacy_lane_adjudication_reaches_the_adjudicated_tier(legacy):
    """This fixture's document HAS frontmatter, so only cause 1 can fail it.

    Red today: adjudication writes `status` and `verdict` into the frontmatter
    and never writes `adjudicated_by`, so the classifier falls short of the tier.
    """
    adjudicate(legacy, verdict="reject", reason="tier check")

    front = read_frontmatter(legacy.doc)
    tier = classify_tier(front)

    assert tier == TIER_ADJUDICATED, (
        "a completed adjudication did not reach TIER_ADJUDICATED -- "
        f"tier={tier!r}, frontmatter={front!r}. "
        "materialize_plan.py:379 will therefore create this brief's bead as OPEN."
    )


# --- CAUSE 2 lives in a different file, deliberately -------------------------
# There WAS a cause-2 test here and it was VACUOUS. It read:
#
#     front: dict[str, str] = {}
#     assert classify_tier(front) == TIER_ADJUDICATED
#
# A hardcoded empty mapping. True forever, whatever `briefs_create` does, so it
# could not detect a fix and could not fail -- a test that could not pass, in the
# file written to catch tests that cannot fail. Its docstring claimed it "asserts
# the CONSEQUENCE rather than the mechanism, so it stays meaningful whichever way
# the fix goes"; it stayed MEANINGLESS whichever way the fix goes.
#
# I found it only by applying the cause-2 fix and watching this file not notice.
# Reading it twice had not been enough; exercising it was.
#
# The real coverage drives the actual create path through the CLI and reads the
# document off disk:
#
#     tests/mctl/test_created_brief_carries_frontmatter.py   (fix/155-create-emits-frontmatter)
#
# It is red before that fix and green after, which is what this one could never be.
