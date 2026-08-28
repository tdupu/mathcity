"""#245: a bead read that returns rows without describing its own filter.

The typed surface has 45 tools and none reads a bead, so every bead question
falls through to `bd list --json` in a shell. `bd list` defaults to OPEN beads
only -- a CLI convenience that is silently correct for a human at a terminal
and silently wrong for an agent building an answer.

Measured cost, 2026-08-28: an agent filtered to `issue_type=decision`, got 23
rows, and reported "23 decision beads, all open, zero carry verdicts" to the
repo owner -- who had asked whether his adjudications still existed. The truth
was 129 decision beads, 106 of them closed, 104 carrying verdicts. Nothing was
lost. The read had excluded 106 rows and said nothing about it.

`read_beads` (beads.py:348) was never the problem: `BD_LIST_ARGS` already
passes `--all`. The problem is that a *filtered* result and a *complete* result
are indistinguishable once they are a bare list of rows.

So the fix is not "read more rows", it is: **a read must state the scope it
applied.** With `matched: 23` beside `total_in_store: 129` in the same payload,
the false report is unwriteable -- the answer contradicts the mistake in the
same breath. That is P6.2 ("a check that could not have failed must not render
as a check that passed") applied to reads rather than to checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.bead_reads import beads_list_payload  # noqa: E402


def _bead(bead_id: str, status: str, issue_type: str = "decision") -> Bead:
    return Bead(
        id=bead_id,
        title=f"bead {bead_id}",
        status=status,
        issue_type=issue_type,
        labels=(),
        source_dependencies=(),
        created_at="2026-08-01T00:00:00Z",
        updated_at="2026-08-01T00:00:00Z",
        raw={"id": bead_id, "status": status, "issue_type": issue_type},
    )


def _store() -> tuple[Bead, ...]:
    """Three open decisions, five closed -- the shape that produced the defect."""
    return (
        _bead("mc-o1", "open"),
        _bead("mc-o2", "open"),
        _bead("mc-o3", "open"),
        _bead("mc-c1", "closed"),
        _bead("mc-c2", "closed"),
        _bead("mc-c3", "closed"),
        _bead("mc-c4", "closed"),
        _bead("mc-c5", "closed"),
    )


def test_a_status_filtered_read_reports_what_it_excluded():
    """The payload must name `total_in_store` beside `matched`.

    This is the whole point of the tool. Without `total_in_store` a caller
    filtered to `open` sees 3 rows and cannot tell 3-of-3 from 3-of-8, which is
    exactly the 23-of-23 vs 23-of-129 error that produced the false report.
    """
    payload = beads_list_payload(_store(), status=("open",))

    assert [b["id"] for b in payload["beads"]] == ["mc-o1", "mc-o2", "mc-o3"]

    scope = payload["scope"]
    assert scope["matched"] == 3
    assert scope["total_in_store"] == 8
    assert scope["status_filter"] == ["open"]
    assert scope["statuses_excluded"] == ["closed"]


def test_an_unfiltered_read_is_a_census_and_says_so():
    """No filter -> matched == total_in_store, and nothing is excluded.

    The default must be the honest one. `bd list`'s default is open-only, which
    is the trap; this tool's default follows BD_LIST_ARGS (`--all`).
    """
    payload = beads_list_payload(_store())

    scope = payload["scope"]
    assert scope["matched"] == 8
    assert scope["total_in_store"] == 8
    assert scope["status_filter"] is None
    assert scope["statuses_excluded"] == []


def test_scope_is_always_present_even_when_nothing_matches():
    """An empty result is the most dangerous one to report bare.

    Zero rows reads as "there are none" unless the payload says how many were
    looked at. `absent here` and `absent everywhere` must stay distinguishable.
    """
    payload = beads_list_payload(_store(), status=("in_progress",))

    assert payload["beads"] == []
    assert payload["scope"]["matched"] == 0
    assert payload["scope"]["total_in_store"] == 8
