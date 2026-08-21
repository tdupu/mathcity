"""An empty stack must say WHY it is empty.

A rig-scoped dashboard pointed at a rig with no briefs renders an empty stack,
an empty priority list and blank counts -- identical to a dashboard that is
broken. It is in fact correct on an empty set, which is the worst version of
this: nothing on the page distinguishes "there is nothing here" from "I could
not look", and the operator's next move differs completely between the two.

Same defect as a check that passes because it could not run. The page must name
the scope that produced the emptiness and what exists outside it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import stack
from mctl_dashboard.state import ViewState


def _view():
    return ViewState()


def test_empty_and_nothing_elsewhere_says_only_that():
    html = stack.table([], _view(), elsewhere=None)
    assert "No briefs on this stack" in html
    assert "exist in" not in html


def test_empty_but_briefs_exist_elsewhere_names_the_count_and_the_scope():
    html = stack.table([], _view(), elsewhere={"rig": "mathcity", "total": 415, "rigs": 17})
    assert "mathcity" in html
    assert "415" in html
    assert "17" in html


def test_it_tells_the_operator_how_to_see_them():
    """Naming the problem without the remedy still leaves him stuck."""
    html = stack.table([], _view(), elsewhere={"rig": "mathcity", "total": 415, "rigs": 17})
    assert "--rig" in html or "all rigs" in html


def test_a_non_empty_stack_never_carries_the_notice():
    briefs = [{"brief_id": "b1", "title": "t", "rig_id": "hq"}]
    html = stack.table(briefs, _view(), elsewhere={"rig": "mathcity", "total": 415, "rigs": 17})
    assert "415" not in html
