"""#160: `work_dispatch` gated on a private, superseded verdict reader.

`work.py` shadowed `verdicts.py`'s reader with its own `_verdict`, which only
checked the typed `metadata.verdict` / `decision` / `recorded_verdict` fields.
Measured across the live six-store city those fields resolved 10 of 139
closed decision beads; `close_reason` -- the field `bd close` actually
writes, non-empty on 138 of the 139 -- was never read, and neither was the
canonical `VERDICT: ... | AUTHORIZER: ...` block `briefs.py` reads out of
`notes`. The result: `briefs_list` reported a bead as carrying an approving
verdict while `work_status` reported the same bead as having none --
`MWRK010` on every real brief in the city.

The fix is one shared reader (`verdicts.is_approved_for_dispatch`) that both
`briefs.py` and `work.py` now call, so the two surfaces cannot disagree by
construction. These tests fix the two live cases from #160's own census
(`he-8hoo`: verdict in `notes`; `he-hbyr`/`he-skli`: verdict in
`close_reason`) and assert the shared reader -- and both call sites -- agree
on them.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core import briefs, verdicts, work  # noqa: E402


def make_bead(bead_id: str, *, status: str = "closed", raw: dict[str, object]) -> Bead:
    return Bead(
        id=bead_id,
        title=bead_id,
        status=status,
        issue_type="task",
        labels=(),
        source_dependencies=(),
        created_at=None,
        updated_at=None,
        raw=raw,
    )


# --- the two live #160 census cases, reconstructed as fixtures --------------

def test_verdict_in_close_reason_is_approved_for_dispatch():
    """he-hbyr / he-skli's shape: bd close's own field carries the verdict."""
    bead = make_bead("he-hbyr", raw={"close_reason": "approve"})
    assert verdicts.is_approved_for_dispatch(bead) is True


def test_verdict_in_notes_is_approved_for_dispatch():
    """he-8hoo's exact shape: the canonical VERDICT block lives in notes."""
    bead = make_bead(
        "he-8hoo",
        raw={"notes": "VERDICT: approve | AUTHORIZER: taylor"},
    )
    assert verdicts.is_approved_for_dispatch(bead) is True


def test_a_bead_with_no_readable_verdict_is_not_approved():
    """The old reader's false positives are not being traded for new ones."""
    bead = make_bead("he-none", raw={"close_reason": "Closed"})
    assert verdicts.is_approved_for_dispatch(bead) is False


def test_an_open_bead_is_never_approved_regardless_of_close_reason():
    """A verdict recorded before the bead is actually closed must not count."""
    bead = make_bead(
        "he-open", status="open", raw={"close_reason": "approve"}
    )
    assert verdicts.is_approved_for_dispatch(bead) is False


# --- the defect itself: briefs_list and work_status must agree --------------

def test_briefs_and_work_share_the_exact_same_reader():
    """Not just equal results -- the same function object, so they cannot
    re-drift the way #160 happened: one file editing its own copy."""
    assert work.is_approved_for_dispatch is verdicts.is_approved_for_dispatch


def test_briefs_approved_for_dispatch_agrees_with_the_shared_reader():
    """`briefs.py` kept a wrapper (`_approved_for_dispatch`) for its own call
    site; it must not silently regain a private implementation."""
    for bead in (
        make_bead("he-hbyr", raw={"close_reason": "approve"}),
        make_bead("he-8hoo", raw={"notes": "VERDICT: approve | AUTHORIZER: taylor"}),
        make_bead("he-none", raw={"close_reason": "Closed"}),
    ):
        assert briefs._approved_for_dispatch(bead) == verdicts.is_approved_for_dispatch(  # type: ignore[attr-defined]
            bead
        )


def test_a_bead_the_old_reader_missed_would_have_disagreed_with_briefs_list():
    """RED against the pre-fix reader: reconstructs the exact #160 symptom --
    same bead, `briefs_list` says approved, `work_status` says no verdict --
    and shows the shared reader closes the gap the old private one left open.
    """
    bead = make_bead("he-8hoo", raw={"notes": "VERDICT: approve | AUTHORIZER: taylor"})

    briefs_side_has_verdict = verdicts.read_verdict(bead) is not None
    work_side_is_approved = verdicts.is_approved_for_dispatch(bead)

    assert briefs_side_has_verdict is True
    assert work_side_is_approved is True

    # The bug: metadata.verdict / decision / recorded_verdict, checked in
    # isolation the way work.py's deleted `_verdict` did, sees nothing here.
    old_reader_would_see = bead.raw.get("verdict") or bead.raw.get("decision")
    assert old_reader_would_see is None, (
        "fixture no longer reproduces #160 -- the old private reader would "
        "have found a typed field and the regression case is void"
    )
