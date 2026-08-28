"""Issue<->bead pairing for the #186 tracker view.

The pairing is `external_ref == "gh-<number>"`, exactly. Two properties are
load-bearing and both are pinned here:

1. **A numeric match is not a pairing.** `gh-56-followup` is not issue 56.
   Title/substring matching is what produced the duplicate beads in mc-vwkn7 --
   five pairs, two of which escaped title-match dedup entirely.
2. **Unpaired and unknown are different claims.** "The store answered and holds
   no bead for this issue" is actionable (#180 mints one). "The store did not
   answer" is not, and dispatching off it would mint duplicates.

Measured context, so the numbers here are not arbitrary: on the live mathcity
store 2026-08-28, **7 of 1142 beads carry an external_ref** against ~100 open
issues. The unpaired row is the common case, not the edge case.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import tracker  # noqa: E402


def _issue(number: int, *, state: str = "OPEN", title: str = "t"):
    return {"number": number, "title": title, "url": f"https://x/{number}", "state": state}


def _bead(bead_id: str, ref: str | None, status: str = "open"):
    return {"id": bead_id, "external_ref": ref, "title": "b", "status": status}


# -- the ref parser --------------------------------------------------------


@pytest.mark.parametrize("ref,expected", [("gh-56", 56), ("gh-1", 1), ("  gh-49  ", 49)])
def test_exact_refs_parse(ref, expected) -> None:
    assert tracker.issue_number_from_ref(ref) == expected


@pytest.mark.parametrize(
    "ref",
    [
        "gh-56-followup",  # NOT issue 56
        "see-gh-56",  # NOT issue 56
        "gh-",
        "gh-x",
        "56",
        "",
        None,
        123,
        [],
    ],
)
def test_near_misses_do_not_parse(ref) -> None:
    """A ref that merely CONTAINS a number is not that issue."""
    assert tracker.issue_number_from_ref(ref) is None


# -- pairing ---------------------------------------------------------------


def test_a_bead_pairs_to_its_issue() -> None:
    rows = tracker.build_rows([_issue(56)], [_bead("mc-2kf", "gh-56")])
    assert rows[0].pairing == tracker.PAIRED
    assert rows[0].bead_ids == ("mc-2kf",)


def test_an_issue_with_no_bead_is_unpaired_not_unknown() -> None:
    rows = tracker.build_rows([_issue(56)], [])
    assert rows[0].pairing == tracker.UNPAIRED
    assert rows[0].needs_bead is True


def test_an_unreadable_store_is_unknown_not_unpaired() -> None:
    """The distinction the whole module exists for."""
    rows = tracker.build_rows([_issue(56)], None, store_unreadable="dolt refused")
    assert rows[0].pairing == tracker.UNKNOWN
    assert rows[0].unknown_reason == "dolt refused"


def test_unknown_never_reports_needing_a_bead() -> None:
    """Dispatching off 'the store did not answer' would mint duplicates."""
    rows = tracker.build_rows([_issue(56)], None, store_unreadable="timeout")
    assert rows[0].needs_bead is False


def test_a_near_miss_ref_does_not_pair() -> None:
    """mc-vwkn7's failure shape: a cheap predicate standing in for a semantic one."""
    rows = tracker.build_rows([_issue(56)], [_bead("mc-x", "gh-56-followup")])
    assert rows[0].pairing == tracker.UNPAIRED
    assert rows[0].bead_ids == ()


def test_a_closed_issue_without_a_bead_does_not_need_one() -> None:
    rows = tracker.build_rows([_issue(56, state="CLOSED")], [])
    assert rows[0].pairing == tracker.UNPAIRED
    assert rows[0].needs_bead is False


# -- duplicates, the mc-vwkn7 signature ------------------------------------


def test_two_beads_on_one_issue_are_both_kept() -> None:
    """Modelling this one-to-one would hide the condition worth surfacing."""
    rows = tracker.build_rows(
        [_issue(53)], [_bead("mc-zmx", "gh-53"), _bead("mc-50ql", "gh-53")]
    )
    assert rows[0].is_duplicated is True
    assert set(rows[0].bead_ids) == {"mc-zmx", "mc-50ql"}


def test_a_single_bead_is_not_flagged_duplicated() -> None:
    rows = tracker.build_rows([_issue(53)], [_bead("mc-zmx", "gh-53")])
    assert rows[0].is_duplicated is False


# -- briefs ----------------------------------------------------------------


def test_briefs_follow_their_bead() -> None:
    rows = tracker.build_rows(
        [_issue(56)],
        [_bead("mc-2kf", "gh-56")],
        {"mc-2kf": [{"brief_id": "mc-yu0u9"}]},
    )
    assert rows[0].briefs == ({"brief_id": "mc-yu0u9"},)


def test_a_paired_bead_with_no_brief_carries_none() -> None:
    rows = tracker.build_rows([_issue(56)], [_bead("mc-2kf", "gh-56")], {})
    assert rows[0].briefs == ()


# -- the summary -----------------------------------------------------------


def test_summary_counts_the_three_states_separately() -> None:
    rows = tracker.build_rows(
        [_issue(1), _issue(2), _issue(3)],
        [_bead("mc-a", "gh-1")],
    )
    s = tracker.summarize(rows)
    assert (s["issues"], s["paired"], s["unpaired"], s["unknown"]) == (3, 1, 2, 0)
    assert s["needs_bead"] == 2


def test_summary_refuses_a_needs_bead_count_when_anything_is_unknown() -> None:
    """A partial denominator rendered as a total is how a useless number is born."""
    rows = tracker.build_rows([_issue(1), _issue(2)], None, store_unreadable="down")
    s = tracker.summarize(rows)
    assert s["needs_bead"] is None
    assert s["unknown"] == 2


def test_empty_store_and_unreadable_store_summarize_differently() -> None:
    """The control that proves the two are not collapsed."""
    answered = tracker.summarize(tracker.build_rows([_issue(1)], []))
    refused = tracker.summarize(tracker.build_rows([_issue(1)], None, store_unreadable="x"))
    assert answered["needs_bead"] == 1
    assert refused["needs_bead"] is None


# -- input hygiene ---------------------------------------------------------


def test_an_issue_without_a_number_is_skipped_not_guessed() -> None:
    rows = tracker.build_rows([{"title": "no number"}, _issue(7)], [])
    assert [r.number for r in rows] == [7]


# -- issue open, bead closed: found in live data, not invented ------------


def test_open_issue_whose_only_bead_is_closed_is_flagged() -> None:
    """Live case on first run: issue #55 open, its bead mc-6jk closed."""
    rows = tracker.build_rows([_issue(55)], [_bead("mc-6jk", "gh-55", status="closed")])
    assert rows[0].is_orphaned_by_bead is True
    assert rows[0].pairing == tracker.PAIRED


def test_an_open_bead_is_not_flagged_orphaned() -> None:
    rows = tracker.build_rows([_issue(56)], [_bead("mc-2kf", "gh-56")])
    assert rows[0].is_orphaned_by_bead is False


def test_one_open_bead_among_closed_ones_is_not_orphaned() -> None:
    rows = tracker.build_rows(
        [_issue(53)],
        [_bead("mc-a", "gh-53", status="closed"), _bead("mc-b", "gh-53")],
    )
    assert rows[0].is_orphaned_by_bead is False


def test_no_bead_at_all_is_unpaired_not_orphaned() -> None:
    """Absence is unpaired's job; the two call for opposite actions."""
    rows = tracker.build_rows([_issue(56)], [])
    assert rows[0].is_orphaned_by_bead is False
    assert rows[0].needs_bead is True


def test_a_closed_issue_with_a_closed_bead_is_not_flagged() -> None:
    rows = tracker.build_rows(
        [_issue(55, state="CLOSED")], [_bead("mc-6jk", "gh-55", status="closed")]
    )
    assert rows[0].is_orphaned_by_bead is False
