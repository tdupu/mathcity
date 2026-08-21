"""The adjudicated screen said the verdict was unreadable. It is readable.

The screen carried: "The verdict itself is not readable, only that one was
recorded... to_dict never emits it" -- and rendered an em dash in the verdict
column. Measured against the live city, all 197 adjudicated briefs carry a
verdict object with `text`, `source` and `confidence`. approve 84, revise 10,
and so on.

So the screen was withholding the one column it exists for, on the strength of
a claim that had stopped being true. That is worse than an empty column: it
tells the operator the data does not exist.

Provenance travels with it, because it matters: a verdict lifted out of a
close_reason at low confidence is not the same artifact as a typed field.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import pipeline


def _brief(verdict=None, **over):
    row = {"brief_id": "b1", "bead_id": "b1", "title": "t", "rig_id": "hq",
           "decision_state": "adjudicated"}
    if verdict is not None:
        row["verdict"] = verdict
    row.update(over)
    return row


def test_the_verdict_text_is_rendered():
    html = pipeline.adjudicated([_brief({"text": "approve", "source": "typed_field",
                                         "confidence": "high"})])
    assert "approve" in html


def test_the_old_claim_is_gone():
    html = pipeline.adjudicated([_brief({"text": "approve", "source": "typed_field",
                                         "confidence": "high"})])
    assert "not readable" not in html


def test_provenance_travels_with_the_verdict():
    """close_reason at low confidence is not a typed field, and must not look
    like one."""
    html = pipeline.adjudicated([_brief({"text": "REJECT-MOOT", "source": "close_reason",
                                         "confidence": "low"})])
    assert "close_reason" in html
    assert "low" in html


def test_a_brief_with_no_verdict_still_renders_a_dash():
    html = pipeline.adjudicated([_brief()])
    assert "&mdash;" in html or "—" in html


def _ordered_ids(html: str, ids: list[str]) -> list[str]:
    """The order `ids` actually appear in `html`, left to right."""
    positions = [(html.index(f'>{i}<'), i) for i in ids]
    return [i for _, i in sorted(positions)]


def test_rows_are_sorted_newest_first_by_updated_at():
    """The heading says "newest first". Measured live: it was not sorted at
    all -- rows for 2026-07-15 rendered ahead of 2026-07-23, and same-day
    rows were not ordered internally either. `bead_id` doubles as the row
    id here so the test can check rendered order without parsing HTML.
    """
    briefs = [
        _brief(bead_id="oldest", updated_at="2026-07-01T00:00:00Z"),
        _brief(bead_id="newest", updated_at="2026-08-19T15:51:56Z"),
        _brief(bead_id="middle", updated_at="2026-07-23T22:00:15Z"),
    ]
    html = pipeline.adjudicated(briefs)
    assert _ordered_ids(html, ["oldest", "newest", "middle"]) == [
        "newest",
        "middle",
        "oldest",
    ]


def test_a_missing_updated_at_sorts_last_not_dropped():
    briefs = [
        _brief(bead_id="dated", updated_at="2026-07-01T00:00:00Z"),
        _brief(bead_id="undated", updated_at=None),
    ]
    html = pipeline.adjudicated(briefs)
    assert "undated" in html  # not dropped
    assert _ordered_ids(html, ["dated", "undated"]) == ["dated", "undated"]
