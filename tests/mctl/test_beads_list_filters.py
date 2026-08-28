"""#245: the filters the reported failure actually needed.

The question that exposed the gap was "can you see my adjudications?" -- i.e.
*which decision beads carry a verdict*. Answering it required pulling 1,152 rows
and post-filtering in the client, which is where the mistake got in.

`issue_type` and `has_verdict` are therefore not conveniences. They are the two
axes of the question the tool exists to answer, and each must compose with the
scope block so a narrowed read still reports its denominator.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.bead_reads import beads_list_payload  # noqa: E402


def _bead(
    bead_id: str,
    status: str,
    issue_type: str = "decision",
    verdict: str | None = None,
    adjudicated_by: str | None = None,
) -> Bead:
    metadata: dict[str, object] = {}
    if verdict is not None:
        metadata["verdict"] = verdict
    if adjudicated_by is not None:
        metadata["adjudicated_by"] = adjudicated_by
    return Bead(
        id=bead_id,
        title=f"bead {bead_id}",
        status=status,
        issue_type=issue_type,
        labels=(),
        source_dependencies=(),
        created_at="2026-08-01T00:00:00Z",
        updated_at="2026-08-01T00:00:00Z",
        raw={"id": bead_id, "metadata": metadata},
    )


def _store() -> tuple[Bead, ...]:
    """Two ruled decisions, one unruled, one ruled-but-unattributed, one task."""
    return (
        _bead("mc-d1", "closed", verdict="approve", adjudicated_by="Taylor Dupuy"),
        _bead("mc-d2", "closed", verdict="revise", adjudicated_by="Taylor Dupuy"),
        _bead("mc-d3", "open"),
        _bead("mc-d4", "closed", verdict="approve"),
        _bead("mc-t1", "open", issue_type="task"),
    )


def test_issue_type_narrows_and_the_denominator_stays_the_whole_store():
    """`total_in_store` must not silently become "total of this type".

    If narrowing to decisions also narrowed the denominator, the payload would
    say 4-of-4 and a caller could still not tell that a task bead was dropped.
    """
    payload = beads_list_payload(_store(), issue_type="decision")

    assert [b["id"] for b in payload["beads"]] == ["mc-d1", "mc-d2", "mc-d3", "mc-d4"]
    scope = payload["scope"]
    assert scope["issue_type_filter"] == "decision"
    assert scope["matched"] == 4
    assert scope["total_in_store"] == 5


def test_has_verdict_true_returns_only_ruled_beads():
    """The question that started this: which decisions were actually ruled."""
    payload = beads_list_payload(_store(), issue_type="decision", has_verdict=True)

    assert [b["id"] for b in payload["beads"]] == ["mc-d1", "mc-d2", "mc-d4"]
    assert payload["scope"]["has_verdict_filter"] is True
    assert payload["scope"]["matched"] == 3
    assert payload["scope"]["total_in_store"] == 5


def test_has_verdict_false_returns_only_unruled_beads():
    """The complement must work too, or "what still needs a verdict" has no answer."""
    payload = beads_list_payload(_store(), issue_type="decision", has_verdict=False)

    assert [b["id"] for b in payload["beads"]] == ["mc-d3"]
    assert payload["scope"]["has_verdict_filter"] is False


def test_a_ruled_bead_surfaces_its_verdict_and_adjudicator():
    """A row must carry the verdict, or the caller re-reads every bead to see it.

    `adjudicated_by` is included because a verdict with no named adjudicator is
    a different thing from one with a name on it -- 28 of the live store's 104
    verdicts are unattributed, and that distinction has to survive the read.
    """
    payload = beads_list_payload(_store(), issue_type="decision", has_verdict=True)
    by_id = {b["id"]: b for b in payload["beads"]}

    assert by_id["mc-d1"]["verdict"] == "approve"
    assert by_id["mc-d1"]["adjudicated_by"] == "Taylor Dupuy"
    assert by_id["mc-d4"]["verdict"] == "approve"
    assert by_id["mc-d4"]["adjudicated_by"] is None
