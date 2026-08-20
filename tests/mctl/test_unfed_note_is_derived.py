"""The unfed-column footnote must describe the table, not a past version of it.

The note used to be a fixed sentence: "Six columns show --" followed by a
hardcoded list. Both halves went stale. The dict it read named five columns,
not six, and `priority` had since acquired a source -- so on a live city-wide
queue the footnote named a column the table was visibly filling, and miscounted
the rest.

That is the same defect the footnote exists to prevent, one level up. An empty
cell is honest about having no value; a footnote that misreports which cells
those are teaches the reader to distrust cells that are correct.

So the note is derived from the rendered rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import stack


def _brief(**over):
    row = {"brief_id": "b1", "title": "t", "rig_id": "hq"}
    row.update(over)
    return row


def test_a_column_with_data_is_not_named_as_missing():
    briefs = [_brief(priority=1), _brief(priority=3)]
    assert "priority" not in stack.unfed_columns(briefs)


def test_a_column_without_data_is_named():
    briefs = [_brief(priority=1), _brief(priority=3)]
    assert "unlock_count" in stack.unfed_columns(briefs)


def test_one_row_with_a_value_is_enough_to_clear_the_column():
    """All-or-nothing: the claim is "the core cannot fill this", and one filled
    cell disproves it."""
    briefs = [_brief(), _brief(unlock_count=4)]
    assert "unlock_count" not in stack.unfed_columns(briefs)


def test_the_count_in_the_prose_matches_the_names_listed():
    briefs = [_brief(priority=2)]
    note = stack.unfed_note(briefs)
    names = stack.unfed_columns(briefs)
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
    assert words[len(names)] in note
    for name in names:
        assert name in note


def test_no_note_when_the_core_fills_everything():
    briefs = [_brief(priority=1, unlock_count=2, kind="doc",
                     decision_options=["a"], recommendation="ship")]
    assert stack.unfed_columns(briefs) == []
    assert stack.unfed_note(briefs) == ""
