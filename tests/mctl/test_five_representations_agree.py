"""After a real adjudication, every representation must AGREE — not merely exist.

`fa3ebee` made adjudication write all five representations of a verdict. The
existing coverage in `test_adjudication_writes_decisions_track_row.py` is good and
this file does not duplicate it; it closes two holes that survive it.

HOLE 1 — one of the five is checked for EXISTENCE, not agreement.
`test_every_representation_agrees_after_adjudication` asserts content for four
representations and, for `decisions/<id>.toml`, calls:

    def decision_toml_exists(fixture) -> bool:
        return (... / f"{fixture.id}.toml").is_file()

`.is_file()`. It never opens it. **A decision record carrying the PREVIOUS
adjudication's verdict passes that test**, because a stale file is still a file —
and a stale decision record is precisely the failure the five-representation work
exists to prevent. Grepping the whole suite for an assertion on that file's verdict
returns nothing.

HOLE 2 — the agreement test covers the LEGACY lane only.
The stack lane has three tests and all three assert what it must NOT have (a
manifest row). Nothing asserts that a stack-lane brief's four applicable
representations agree after a verdict. That is the majority path.

WHY THIS IS NOT HYPOTHETICAL: driving a real adjudication through the MCP on
2026-08-21 produced `MCTL_BRIEF_FRONTMATTER_UNWRITABLE` — the bead recorded
`reject` while the brief document's frontmatter was never updated, because
`briefs_create` had written a document with no frontmatter block for
`briefs_adjudicate` to rewrite. Four of five representations agreed and one was
silently stale, at WARN, with the operation reporting success. No test caught it,
and these two holes are why.

HOW THESE TESTS COULD FAIL (P6.2): each asserts CONTENT, and each is paired with a
control that would catch a fixture which never adjudicated at all — otherwise
"agrees" could be satisfied by every representation being uniformly untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_adjudication_writes_decisions_track_row import (  # noqa: E402
    LEGACY_ID,
    STACK_ID,
    _build,
    adjudicate,
    bead_status,
    index_row,
    read_frontmatter,
    manifest_row,
)

import tomllib  # noqa: E402


def decision_toml(fixture) -> dict:
    """The content the existing helper never opens."""
    path = fixture.brief_root / "decisions" / f"{fixture.id}.toml"
    assert path.is_file(), f"no decision record at {path.name}"
    with path.open("rb") as handle:
        return tomllib.load(handle)


@pytest.fixture
def legacy(tmp_path: Path):
    return _build(tmp_path, LEGACY_ID)


@pytest.fixture
def stack_track(tmp_path: Path):
    return _build(tmp_path, STACK_ID)


# --- HOLE 1: the decision record's CONTENT --------------------------------
def test_the_decision_record_carries_the_verdict_not_merely_exists(legacy):
    """`.is_file()` cannot tell a fresh record from last week's."""
    adjudicate(legacy, verdict="reject", reason="content, not existence")

    record = decision_toml(legacy)
    assert record.get("verdict") == "reject", (
        f"decision record does not carry the verdict: {record!r}"
    )
    assert str(record.get("status", "")).startswith("adjudicated"), (
        f"decision record status disagrees with the bead: {record!r}"
    )


def test_control_an_unadjudicated_brief_has_no_verdict_in_its_record(legacy):
    """The control for the test above.

    Without this, a decision record that arrived pre-populated would satisfy the
    verdict assertion without adjudication having written anything.
    """
    record = decision_toml(legacy)
    assert record.get("verdict") is None, (
        "the fixture's decision record already carries a verdict before "
        f"adjudication; the test above proves nothing: {record!r}"
    )


def test_re_adjudicating_updates_the_record_rather_than_leaving_the_first_verdict(legacy):
    """A stale record is the exact failure `.is_file()` cannot see."""
    adjudicate(legacy, verdict="approve", reason="first")
    adjudicate(legacy, verdict="reject", reason="second")

    record = decision_toml(legacy)
    assert record.get("verdict") == "reject", (
        f"decision record still carries the FIRST verdict: {record!r}"
    )


# --- HOLE 2: the stack lane agrees too ------------------------------------
def test_a_stack_lane_brief_has_all_four_applicable_representations_agreeing(stack_track):
    """The majority path. Four, not five: a stack brief has no manifest row.

    That absence is asserted by the existing suite and is correct; what was
    missing is that the other four agree with each other.
    """
    adjudicate(stack_track, verdict="reject", reason="stack lane agreement")

    assert bead_status(stack_track) == "closed"

    record = decision_toml(stack_track)
    assert record.get("verdict") == "reject", f"decision record: {record!r}"

    row = index_row(stack_track)
    assert str(row["status"]).startswith("adjudicated"), f"index row: {row!r}"

    front = read_frontmatter(stack_track.doc)
    assert front["status"].startswith("adjudicated"), f"frontmatter: {front!r}"
    assert front.get("verdict") == "reject", (
        f"frontmatter status was updated but its verdict disagrees: {front!r}"
    )
