"""#157: `work_ready` reported CLOSED source beads as ready with zero blockers.

QUIMBY measured it across all 17 rigs: `work_ready` returned exactly two
dispatchable items city-wide, and BOTH were closed throwaway test beads. `gc`
then refused the same bead at formula-instantiation time --

    [FATAL] MWRK_DISPATCH_COMMAND_FAILED
    detail: formulas v2 target gsp-odm8cx is closed

-- so the two layers disagreed and the READ was the one that was wrong. The
write was safe the whole time.

Reading `_work_item` confirms the mechanism: it checks `source is None`
(MWRK012), `source.has_active_assignee` (MWRK001) and open child workflows
(MWRK002), and NEVER consults `source.status`. A closed bead clears every
blocker, so `blockers: []` did not mean "no blockers" -- it meant "never asked".

`Bead.is_open` already existed and already encoded the right vocabulary
(`open · hooked · in_progress · blocked · review · testing`). The check was
absent, not wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402


class StubCtx:
    """Minimal context: `_diagnostic` reads exactly these three attributes.

    A stub rather than a reshaped helper. `_closed_source_blockers` returns a
    real Diagnostic because every other blocker in `_work_item` does, and
    changing production shape to suit a fixture would be the tail wagging the
    dog.
    """
    city_root = Path("/tmp/stub-city")
    rig_root = Path("/tmp/stub-city/stub-rig")
    rig_id = "stub-rig"
    trace_id = "stub-trace"
    rig_db = "stub-db"          # _canonical_bead_location reads this


def make_bead(bead_id: str, *, status: str = "open", deps: tuple[str, ...] = ()) -> Bead:
    return Bead(
        id=bead_id,
        title=bead_id,
        status=status,
        issue_type="task",
        labels=(),
        source_dependencies=deps,
        created_at=None,
        updated_at=None,
        raw={},
    )


# --- the vocabulary this fix leans on ---------------------------------------

def test_is_open_is_false_for_closed_and_true_for_the_working_states():
    """The fix must not invent a second status vocabulary beside this one."""
    assert make_bead("b", status="closed").is_open is False
    for live in ("open", "hooked", "in_progress", "blocked", "review", "testing"):
        assert make_bead("b", status=live).is_open is True


def test_case_is_not_load_bearing():
    # stick-dog's case-sensitive grep is the precedent for checking this.
    assert make_bead("b", status="CLOSED").is_open is False
    assert make_bead("b", status="Closed").is_open is False


# --- the defect itself ------------------------------------------------------

def test_a_closed_source_bead_produces_a_blocker(monkeypatch, tmp_path):
    """RED before the fix: a closed source clears every check and reports ready."""
    from mctl_core import work

    brief = make_bead("brief-1", deps=("src-1",))
    closed_source = make_bead("src-1", status="closed")
    blockers = work._closed_source_blockers(  # type: ignore[attr-defined]
        StubCtx(), brief_id="brief-1", source=closed_source
    )
    assert blockers, "a closed source bead must produce a blocker"
    assert any(d.code == "MWRK013" for d in blockers)


def test_an_open_source_bead_produces_no_blocker():
    """The guard must not refuse everything -- that would pass by accident."""
    from mctl_core import work

    open_source = make_bead("src-1", status="open")
    assert work._closed_source_blockers(  # type: ignore[attr-defined]
        StubCtx(), brief_id="brief-1", source=open_source
    ) == []


def test_a_missing_source_is_left_to_MWRK012_not_double_reported():
    """`source is None` already has its own blocker; this must not add a second."""
    from mctl_core import work

    assert work._closed_source_blockers(  # type: ignore[attr-defined]
        StubCtx(), brief_id="brief-1", source=None
    ) == []
