"""#160: `work.py` gated dispatch on a SUPERSEDED private verdict reader.

`briefs_list` says a brief is approved; `work_status` says it has no verdict.
Both are reading the same bead. They disagree because there are two readers and
`work.py` has its own, older one:

    briefs.py::_verdict  -> verdicts.read_verdict
                            reads `close_reason` (what `bd close` actually
                            writes, non-empty on 138 of 139 closed decision
                            beads in the live city) AND the canonical
                            `VERDICT: ... | AUTHORIZER: ...` block in `notes`
    work.py::_verdict    -> raw["verdict"|"decision"|"recorded_verdict"]
                            and metadata.* -- NEVER close_reason, NEVER notes

`work.py` already imports from `.verdicts` (line 19: `brief_population`,
`is_brief_bead`), so the canonical reader was one name away the whole time.

The consequence is `MWRK010` on every real brief: the verdict IS recorded, in
the field `bd close` writes, and the dispatch gate cannot see it. That is what
held the entire dispatch queue.

This is a one-real-copy defect (P1.9): the fix is to delete the second reader,
not to teach it the extra fields.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core import work  # noqa: E402


def closed_bead(**raw) -> Bead:
    return Bead(
        id="brief-1",
        title="brief-1",
        status="closed",
        issue_type="decision",
        labels=(),
        source_dependencies=("src-1",),
        created_at=None,
        updated_at=None,
        raw=raw,
    )


def test_a_verdict_in_close_reason_is_approved_for_dispatch():
    """The live-city case: `bd close` writes close_reason and nothing else.

    138 of 139 closed decision beads carry it. Before this fix, every one of
    them reported MWRK010 "no approving verdict" while briefs_list reported the
    same beads as approved.
    """
    bead = closed_bead(close_reason="approve")
    assert work._approved_for_dispatch(bead) is True


def test_a_verdict_in_the_notes_VERDICT_block_is_approved_for_dispatch():
    bead = closed_bead(notes="VERDICT: approve | AUTHORIZER: taylor")
    assert work._approved_for_dispatch(bead) is True


def test_a_typed_verdict_field_still_works():
    """Control. The old reader's cases must not regress."""
    assert work._approved_for_dispatch(closed_bead(verdict="approve")) is True


def test_a_rejecting_verdict_is_NOT_approved():
    """The guard must not approve everything -- that would pass by accident."""
    assert work._approved_for_dispatch(closed_bead(close_reason="reject")) is False


def test_an_open_bead_is_not_approved_even_with_an_approving_verdict():
    """Status still matters: adjudication closes the brief."""
    bead = Bead(
        id="b", title="b", status="open", issue_type="decision", labels=(),
        source_dependencies=("s",), created_at=None, updated_at=None,
        raw={"close_reason": "approve"},
    )
    assert work._approved_for_dispatch(bead) is False


def test_work_and_briefs_agree_on_the_same_bead():
    """The actual bug: two readers, one bead, two answers.

    This is the assertion that would have caught #160 on the day the second
    reader was introduced.
    """
    from mctl_core import briefs

    bead = closed_bead(close_reason="approve")
    assert work._approved_for_dispatch(bead) == briefs._approved_for_dispatch(bead)
