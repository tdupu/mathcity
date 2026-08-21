"""The stack must offer only briefs a verdict can actually be recorded on.

Taylor: *"I only need to see briefs I can actually rule on."*

The stack filtered on `decision_state == pending` and stopped there. Measured on
the live city: **172 pending, of which 89 carry a bead and 83 do not.** A
bead-less brief is refused outright by the write path --

    MBRF010: No canonical brief bead named '<id>' was found

-- so more than half the queue was briefs that would turn him away after he had
read them and chosen a verdict. That is worse than a shorter queue: it spends the
scarcest thing in the loop, which is his attention, on rows that cannot move.

Two rules this must not break, both learned the hard way:

**`MBRF004` does NOT disqualify.** It gates *approve* while leaving *revise* and
*reject* live -- verified directly against `mctl`, all three verdicts, on a real
brief. Filtering those out would hide briefs he can legitimately send back, which
is the same error pointed the other way. The discriminator is **a bead**, not
**a clean bill of health**.

**Excluded is not dropped.** Anything held back is counted and named, never
silently absent. A queue that quietly shrinks is indistinguishable from a city
that quietly emptied -- the defect this dashboard has spent two days removing.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import rulable, unrulable_reason


def _brief(**over):
    row = {"brief_id": "b", "decision_state": "pending", "bead_id": "b", "rig_id": "hq"}
    row.update(over)
    return row


# ---------------------------------------------------------------------------
# what counts as rulable
# ---------------------------------------------------------------------------


def test_a_pending_bead_backed_brief_is_rulable():
    assert rulable(_brief()) is True


def test_a_brief_with_no_bead_is_not_rulable():
    """MBRF010 refuses it; offering it wastes a decision."""
    assert rulable(_brief(bead_id=None)) is False


def test_mbrf004_does_not_disqualify():
    """The rule that would be easiest to get wrong.

    MBRF004 gates approve and leaves revise/reject live, so the brief is still
    rulable -- just not approvable.
    """
    brief = _brief(diagnostics=[{"code": "MBRF004", "severity": "ERROR"}])
    assert rulable(brief) is True


def test_an_adjudicated_brief_is_not_rulable():
    assert rulable(_brief(decision_state="adjudicated")) is False


# ---------------------------------------------------------------------------
# the reason is nameable, because excluded is not dropped
# ---------------------------------------------------------------------------


def test_the_reason_names_the_missing_bead():
    reason = unrulable_reason(_brief(bead_id=None))
    assert reason and "bead" in reason.lower()


def test_a_rulable_brief_has_no_reason():
    assert unrulable_reason(_brief()) is None


# ---------------------------------------------------------------------------
# the stack scope applies it
# ---------------------------------------------------------------------------


def test_lane_membership_is_left_alone():
    """Rulability is applied in the queue handler, NOT in `_scoped`.

    `_scoped` answers "which lane is this brief in". Rulability answers "could
    a verdict land on it". Folding the second into the first broke two existing
    tests whose fixtures were minimal for unrelated reasons -- which was the
    design telling me they are different questions.
    """
    from mctl_dashboard.app import _scoped

    briefs = [_brief(brief_id="ok"), _brief(brief_id="nobead", bead_id=None)]
    assert len(_scoped(briefs, "stack")) == 2


# ---------------------------------------------------------------------------
# excluded is counted and named on the page
# ---------------------------------------------------------------------------


def test_the_page_says_how_many_were_held_back():
    from mctl_dashboard.screens import stack as stack_screen

    note = stack_screen.held_back_note([_brief(bead_id=None), _brief(bead_id=None)])
    assert "2" in note


def test_the_page_names_why():
    from mctl_dashboard.screens import stack as stack_screen

    note = stack_screen.held_back_note([_brief(bead_id=None)])
    assert "bead" in note.lower()


def test_no_note_when_nothing_was_held_back():
    from mctl_dashboard.screens import stack as stack_screen

    assert stack_screen.held_back_note([]) == ""
