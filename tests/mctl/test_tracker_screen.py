"""Rendering for the #186 tracker screen.

The screen's whole job is to make ABSENCE legible: 102 of 107 open issues have
no bead (measured 2026-08-28), so most of what it draws is a gap. These tests
pin that every gap is a *stated* value and that the three states never collapse
into one another:

    no bead    the store was read, nothing claims this issue   -> work (#180)
    unknown    the store did not answer                        -> NOT work
    —          no bead exists, so no brief is reachable HERE    -> not a claim
               that none exists

A blank cell would read as "fine" for all three, which is the failure mode this
codebase keeps naming.

The screen deliberately does not import `mctl_core` (`screens/city.py:513`), so
it duplicates three state strings. `test_states_match_the_model` asserts the
duplication cannot drift.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import tracker as model  # noqa: E402
from mctl_dashboard.screens import tracker as screen  # noqa: E402


def _row(**over):
    """A TrackerRow built through the real model, not a hand-rolled stub.

    Using the model means a change to its semantics breaks these tests rather
    than silently leaving the screen asserting against a shape nothing produces.
    """
    issue = {
        "number": over.pop("number", 186),
        "title": over.pop("title", "a tracker view"),
        "url": over.pop("url", "https://github.com/tdupu/mathcity/issues/186"),
        "state": over.pop("state", "OPEN"),
    }
    beads = over.pop("beads", [])
    briefs_by_bead = over.pop("briefs_by_bead", None)
    unreadable = over.pop("store_unreadable", None)
    rows = model.build_rows(
        [issue],
        None if unreadable else beads,
        briefs_by_bead,
        store_unreadable=unreadable,
    )
    return rows[0]


def _bead(bid, ref, status="open"):
    return {"id": bid, "external_ref": ref, "status": status}


# -- the duplication guard -------------------------------------------------


def test_states_match_the_model() -> None:
    """The screen copies three strings from the model; they must not drift."""
    assert (screen.PAIRED, screen.UNPAIRED, screen.UNKNOWN) == (
        model.PAIRED,
        model.UNPAIRED,
        model.UNKNOWN,
    )


# -- absence is stated, never blank ----------------------------------------


def test_an_unpaired_issue_says_no_bead() -> None:
    html = screen.bead_cell(_row(beads=[]))
    assert "no bead" in html
    assert 'data-pairing="unpaired"' in html


def test_an_unreadable_store_says_unknown_not_no_bead() -> None:
    html = screen.bead_cell(_row(store_unreadable="dolt refused"))
    assert "unknown" in html
    assert "no bead" not in html
    assert "dolt refused" in html  # the reason is carried, not swallowed


def test_no_bead_and_unknown_render_differently() -> None:
    """The distinction the screen exists to preserve."""
    assert screen.bead_cell(_row(beads=[])) != screen.bead_cell(
        _row(store_unreadable="x")
    )


def test_an_unpaired_issue_does_not_claim_it_has_no_brief() -> None:
    """It has no bead, so no brief is reachable — a different statement."""
    html = screen.brief_cell(_row(beads=[]))
    # Assert on the data attribute, not a substring: the explanatory tooltip
    # legitimately contains the words "no brief" while stating the opposite.
    assert 'data-brief="not-applicable"' in html
    assert 'data-brief="none"' not in html


def test_a_paired_bead_with_no_brief_does_say_no_brief() -> None:
    html = screen.brief_cell(_row(beads=[_bead("mc-2kf", "gh-186")]))
    assert "no brief" in html


# -- the live-data conditions ----------------------------------------------


def test_a_closed_bead_on_an_open_issue_is_flagged() -> None:
    """Live case #55 / mc-6jk."""
    html = screen.bead_cell(_row(beads=[_bead("mc-6jk", "gh-186", status="closed")]))
    assert 'data-flag="bead-closed"' in html


def test_two_beads_are_flagged_as_duplicated() -> None:
    """The mc-vwkn7 signature."""
    html = screen.bead_cell(
        _row(beads=[_bead("mc-a", "gh-186"), _bead("mc-b", "gh-186")])
    )
    assert 'data-flag="duplicated"' in html
    assert "mc-a" in html and "mc-b" in html


# -- readiness -------------------------------------------------------------


def test_readiness_needs_bead_for_an_open_unpaired_issue() -> None:
    assert 'data-readiness="needs-bead"' in screen.readiness_cell(_row(beads=[]))


def test_readiness_is_unknown_when_the_store_did_not_answer() -> None:
    """Never 'needs a bead' — that would dispatch work off an unread store."""
    html = screen.readiness_cell(_row(store_unreadable="x"))
    assert 'data-readiness="unknown"' in html
    assert "needs-bead" not in html


def test_readiness_needs_brief_when_paired_but_unbriefed() -> None:
    html = screen.readiness_cell(_row(beads=[_bead("mc-2kf", "gh-186")]))
    assert 'data-readiness="needs-brief"' in html


def test_readiness_briefed_when_a_brief_exists() -> None:
    html = screen.readiness_cell(
        _row(beads=[_bead("mc-2kf", "gh-186")], briefs_by_bead={"mc-2kf": [{"brief_id": "b1"}]})
    )
    assert 'data-readiness="briefed"' in html


# -- the issue link, asked for by name -------------------------------------


def test_the_issue_number_links_to_the_tracker() -> None:
    html = screen.issue_cell(_row())
    assert 'href="https://github.com/tdupu/mathcity/issues/186"' in html
    assert "#186" in html


def test_a_missing_url_still_renders_the_number() -> None:
    html = screen.issue_cell(_row(url=""))
    assert "#186" in html
    assert "<a " not in html


# -- escaping --------------------------------------------------------------


def test_a_hostile_title_is_escaped() -> None:
    html = screen.issue_cell(_row(title="<script>alert(1)</script>"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_an_ampersand_in_a_title_survives_the_summary_join() -> None:
    """The separator is a raw entity; escaping must not be undone wholesale."""
    html = screen.summary_line({"issues": 1, "paired": 0, "unpaired": 1, "needs_bead": 1})
    assert "&middot;" in html
    assert "&amp;middot;" not in html


# -- the summary -----------------------------------------------------------


def test_summary_prints_unknown_rather_than_zero_for_an_unknown_count() -> None:
    html = screen.summary_line({"issues": 2, "paired": 0, "unpaired": 0, "needs_bead": None})
    assert "unknown needing one" in html
    assert "0 needing one" not in html


def test_summary_reports_a_real_count_when_known() -> None:
    """Control: the test above must not pass on a function that always says unknown."""
    html = screen.summary_line({"issues": 2, "paired": 0, "unpaired": 2, "needs_bead": 2})
    assert "2 needing one" in html


# -- whole-screen ----------------------------------------------------------


def test_render_states_a_github_failure_instead_of_an_empty_table() -> None:
    html = screen.render([], {}, issues_unreadable="gh is not installed")
    assert "could not be read" in html
    assert "not a count of zero" in html
    assert "tracker-table" not in html


def test_render_distinguishes_no_issues_from_a_failed_read() -> None:
    empty = screen.render([], {"issues": 0})
    failed = screen.render([], {}, issues_unreadable="timeout")
    assert "tracker-empty" in empty
    assert empty != failed


def test_render_draws_a_row_per_issue() -> None:
    rows = [_row(number=1), _row(number=2)]
    html = screen.render(rows, {"issues": 2, "paired": 0, "unpaired": 2, "needs_bead": 2})
    body = html.split("<tbody>")[1].split("</tbody>")[0]
    assert body.count("<tr>") == 2  # <thead> carries one too
    assert "tracker-table" in html
