"""#173: approving a sourceless brief permanently bricked it. Regression from #157.

THE DIAGNOSTIC THAT BRICKS IT IS MINE. I added MWRK013 in #157 so that a closed
source bead would stop reporting as dispatchable. I excluded exactly one case --
a MISSING source stays MWRK012's business -- and did not consider a third
configuration:

    _work_item    if not source_id:
                      blockers.append(MWRK011 "requires a source bead dependency")
                      source_id = brief_id        <- the brief becomes its OWN source
                      ...
                      _closed_source_blockers()   <- MINE. requires the source OPEN

`briefs_adjudicate` closes the brief, because closing it is what adjudication IS.
The brief is then its own closed source, MWRK013 fires, and the brief can never
be dispatched. CT4.5 MANDATES adjudicating before dispatch, so the prescribed
workflow walks into it.

The contradiction is the tell: MWRK011 says there is no source and MWRK013 says
the source is closed. A brief cannot be in both worlds.

WHY THE FIX IS IN MY CHECK AND NOT IN THE FALLBACK. I assumed the synthetic
source was the defect and measured before acting: `source_id` feeds
`WorkItem.bead_id` (the `WorkItem(...)` return in `_work_item`) and 17 other
references -- sally counted them. Removing it would empty
`bead_id` in every payload for a sourceless brief. The fallback is load-bearing.

When the brief IS its own source, "is the source closed?" reduces to "is the
brief closed?" -- which adjudication guarantees. The question is not merely
inconvenient there; it is meaningless, and asking it produces an answer that
contradicts the blocker sitting beside it.

My #157 tests could not have caught this: all five construct a source bead
DISTINCT from the brief. No fixture put them in the same object.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core import work  # noqa: E402


class StubCtx:
    city_root = Path("/tmp/stub-city")
    rig_root = Path("/tmp/stub-city/stub-rig")
    rig_id = "stub-rig"
    rig_db = "stub-db"
    trace_id = "stub-trace"


def bead(bead_id: str, *, status: str, deps: tuple[str, ...] = ()) -> Bead:
    return Bead(
        id=bead_id, title=bead_id, status=status, issue_type="decision", labels=(),
        source_dependencies=deps, created_at=None, updated_at=None, raw={},
    )


def test_a_brief_that_is_its_own_source_is_not_blocked_for_being_closed():
    """The brick. An adjudicated sourceless brief is closed BY DEFINITION."""
    brief = bead("brief-1", status="closed")          # adjudication closed it
    assert work._closed_source_blockers(
        StubCtx(), brief_id="brief-1", source=brief
    ) == []


def test_a_REAL_closed_source_bead_is_still_blocked():
    """#157 must survive. If this fails the original defect is back."""
    closed_source = bead("src-1", status="closed")
    blockers = work._closed_source_blockers(
        StubCtx(), brief_id="brief-1", source=closed_source
    )
    assert [d.code for d in blockers] == ["MWRK013"]


def test_a_real_OPEN_source_is_still_not_blocked():
    open_source = bead("src-1", status="open")
    assert work._closed_source_blockers(
        StubCtx(), brief_id="brief-1", source=open_source
    ) == []


def test_a_missing_source_is_still_left_to_MWRK012():
    assert work._closed_source_blockers(
        StubCtx(), brief_id="brief-1", source=None
    ) == []


def test_the_two_contradictory_blockers_can_never_co_occur():
    """MWRK011 (no source) and MWRK013 (source closed) describe incompatible
    worlds. This asserts the structural property rather than one instance of it.
    """
    self_source = bead("brief-1", status="closed")
    codes = [d.code for d in work._closed_source_blockers(
        StubCtx(), brief_id="brief-1", source=self_source
    )]
    assert "MWRK013" not in codes
