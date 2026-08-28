"""Typed, scope-declaring reads of the canonical bead store (#245).

The typed surface had 45 tools and none of them read a bead, so every bead
question fell through to `bd list --json` in a shell -- whose default is OPEN
beads only. That default is a CLI convenience: right for a human at a terminal,
wrong for an agent building an answer, and silent either way.

The correction is NOT "read more rows". `read_beads` already passes `--all`
(`beads.py:BD_LIST_ARGS`) and always did. The correction is that **a read must
state the scope it applied**, because a filtered result and a complete result
are indistinguishable once they are a bare list of rows. With `matched` beside
`total_in_store` in one payload, "23 decision beads exist" cannot be written
over a 23-of-129 read -- the answer contradicts the mistake in the same breath.

This is P6.2 turned on reads: a check that could not have failed must not render
as a check that passed, and a read that could not have seen everything must not
render as a census.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .beads import Bead


def beads_list_payload(
    beads: Iterable[Bead],
    *,
    status: Sequence[str] | None = None,
    issue_type: str | None = None,
    has_verdict: bool | None = None,
) -> Mapping[str, Any]:
    """Enumerate beads, and declare the scope the enumeration applied.

    `status` narrows to the named statuses, case-insensitively. `issue_type`
    narrows to one kind. `has_verdict` selects ruled (`True`) or unruled
    (`False`) beads -- the axis behind "can you see my adjudications?", which
    otherwise costs a full-store read and a client-side filter, which is exactly
    where the reported mistake got in.

    Omitting all three is a CENSUS -- every bead the store returned -- which is
    the honest default and the opposite of `bd list`'s.

    The `scope` block is not optional and not advisory. It is the reason this
    function exists: `statuses_excluded` names what was dropped, and
    `total_in_store` is the denominator a caller needs before it can describe
    `matched` as anything at all. **`total_in_store` always counts the WHOLE
    store**, never the narrowed set -- a denominator that shrinks with the
    filter would report 4-of-4 for a read that dropped a row, which is the bug
    with extra steps.
    """
    everything = list(beads)
    total_in_store = len(everything)
    rows = everything

    status_filter: list[str] | None = None
    if status is not None:
        wanted = {str(s).lower() for s in status}
        rows = [bead for bead in rows if bead.status.lower() in wanted]
        status_filter = [str(s) for s in status]

    if issue_type is not None:
        rows = [bead for bead in rows if bead.issue_type == issue_type]

    if has_verdict is not None:
        rows = [bead for bead in rows if (_verdict(bead) is not None) is has_verdict]

    # Statuses present in the store that this read did NOT return. Derived from
    # the store rather than from a fixed vocabulary, so a status nobody
    # anticipated still shows up as excluded instead of vanishing silently.
    returned = {bead.status.lower() for bead in rows}
    excluded = sorted(
        {bead.status for bead in everything if bead.status.lower() not in returned}
    )

    return {
        "beads": [_row(bead) for bead in rows],
        "scope": {
            "status_filter": status_filter,
            "statuses_excluded": excluded,
            "issue_type_filter": issue_type,
            "has_verdict_filter": has_verdict,
            "matched": len(rows),
            "total_in_store": total_in_store,
        },
    }


def beads_show_payload(beads: Iterable[Bead], bead_id: str) -> Mapping[str, Any]:
    """One bead in full, by id, with its metadata verbatim.

    `bead_comment` has been able to WRITE to a bead by id since mc-ilia, while
    nothing could read one -- so a correction could be appended to a record the
    author had no way to inspect first. This closes that.

    Metadata is returned whole rather than cherry-picked because `verdict_reason`
    carries the adjudicator's own words, at paragraph length, and is the field
    that actually answers "can you see my adjudications?".

    A miss returns `bead: None` WITH `found: False` rather than an empty object.
    An absence that renders like a blank record is the same failure as rows that
    render like a census: it reads as an answer when it is the lack of one.
    """
    for bead in beads:
        if bead.id == bead_id:
            row = dict(_row(bead))
            row["labels"] = list(bead.labels)
            row["source_dependencies"] = list(bead.source_dependencies)
            row["description"] = bead.description
            row["metadata"] = dict(_metadata(bead))
            return {"bead": row, "found": True}
    return {"bead": None, "found": False}


def _metadata(bead: Bead) -> Mapping[str, Any]:
    raw = bead.raw.get("metadata")
    return raw if isinstance(raw, Mapping) else {}


def _verdict(bead: Bead) -> str | None:
    value = _metadata(bead).get("verdict")
    return value if isinstance(value, str) and value else None


def _adjudicated_by(bead: Bead) -> str | None:
    value = _metadata(bead).get("adjudicated_by")
    return value if isinstance(value, str) and value else None


def _row(bead: Bead) -> Mapping[str, Any]:
    """One bead, with the verdict fields inline.

    `verdict` and `adjudicated_by` are typed rather than left in `raw` because a
    verdict with no named adjudicator is a materially different record from one
    with a name on it -- 28 of the live store's 104 verdicts are unattributed --
    and that distinction has to survive the read rather than being recoverable
    only by a second pass.
    """
    return {
        "id": bead.id,
        "title": bead.title,
        "status": bead.status,
        "issue_type": bead.issue_type,
        "assignee": bead.assignee,
        "created_at": bead.created_at,
        "updated_at": bead.updated_at,
        "verdict": _verdict(bead),
        "adjudicated_by": _adjudicated_by(bead),
    }
