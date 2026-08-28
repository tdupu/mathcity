"""`unlock_count` is int-OR-SENTINEL, and the stack screen must survive both.

`skills/create-brief/SKILL.md` does not merely permit a non-integer here, it
*mandates* one: ":67 when you cannot reach the store: write
`UNKNOWN-NOT-COMPUTED`. NEVER write `0`." The reasoning is that `0` is a
measurement claiming the brief blocks nothing, which sorts a live blocker to
the bottom of an `unlock_count`-ranked stack. So the sentinel is a deliberate
honesty contract, not dirty data, and a brief carrying it is CORRECT.

`stack.py` then coerced that field with a bare `float()` guarded only against
`None`, at two sites. The result, measured on the live city 2026-08-28: the
whole `/queue` page -- the dashboard's landing view -- rendered
"Something went wrong" with `ValueError: could not convert string to float:
'UNKNOWN-NOT-COMPUTED'`, triggered by a single brief
(`gascity-packs .pile/gsp-oodpqb.md`) written correctly per the skill.

SKILL.md:91 predicted exactly this and left it unclosed: "The stack sorts by
`unlock_count`, and **how consumers order a non-integer is unspecified**."
These tests specify it: a non-numeric `unlock_count` is UNKNOWN -- it never
raises, and it never silently becomes `0.0`, because a sentinel that sorts
identically to a measured zero has thrown away the distinction it exists to
preserve.

`age_days` (`stack.py:63-76`) is the in-file precedent being matched: it
already parses defensively and returns `None` on unparseable input.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import stack  # noqa: E402

SENTINEL = "UNKNOWN-NOT-COMPUTED"


def _brief(unlock, **over):
    """A stack row carrying `unlock`, otherwise wholly unremarkable."""
    row = {
        "unlock_count": unlock,
        "priority": "P2",
        "created_at": "2026-08-28T02:00:00Z",
        "title": "a brief",
        "rig_id": "gascity-packs",
    }
    row.update(over)
    return row


# -- the control ------------------------------------------------------------
# If these fail, the tests below prove nothing: they would be passing on a
# function that cannot compute a score at all, rather than on one that
# tolerates the sentinel.


def test_numeric_unlock_still_scores() -> None:
    assert isinstance(stack.score(_brief(4)), int)


def test_numeric_unlock_outranks_smaller_one() -> None:
    assert stack.score(_brief(9)) > stack.score(_brief(1))


def test_numeric_unlock_sorts_ahead_of_unknown() -> None:
    """Known beats unknown -- the ordering the sentinel must not destroy."""
    assert stack.sort_value(_brief(3), "unlock") < stack.sort_value(
        _brief(SENTINEL), "unlock"
    )


# -- the defect ------------------------------------------------------------


def test_score_survives_the_sentinel() -> None:
    stack.score(_brief(SENTINEL))  # stack.py:116 -- raised ValueError


def test_sort_value_unlock_survives_the_sentinel() -> None:
    stack.sort_value(_brief(SENTINEL), "unlock")  # stack.py:143 -- raised


def test_sort_value_score_survives_the_sentinel() -> None:
    """`score` reaches :116 by a second path; fixing :143 alone leaves it live."""
    stack.sort_value(_brief(SENTINEL), "score")


@pytest.mark.parametrize("junk", [SENTINEL, "", "  ", "n/a", "3 briefs", None, [], {}])
def test_no_unparseable_unlock_raises(junk) -> None:
    """The contract is the FIELD's, not this one sentinel's."""
    stack.score(_brief(junk))
    stack.sort_value(_brief(junk), "unlock")
    stack.sort_value(_brief(junk), "score")


# -- the sentinel must not become a measurement ----------------------------


def test_sentinel_does_not_masquerade_as_zero() -> None:
    """The whole point of the sentinel is that it is NOT the number 0.

    Coercing it to 0.0 would stop the crash and reintroduce the exact bug
    SKILL.md:67 forbids -- an unmeasured brief sorting as "blocks nothing".
    """
    assert stack.sort_value(_brief(SENTINEL), "unlock") != stack.sort_value(
        _brief(0), "unlock"
    )


def test_sentinel_sorts_last_against_a_measured_zero() -> None:
    """Unknown is worse-known than a real 0, so it sorts after it."""
    assert stack.sort_value(_brief(0), "unlock") < stack.sort_value(
        _brief(SENTINEL), "unlock"
    )


def test_sentinel_scores_like_an_absent_field_not_like_zero() -> None:
    """A sentinel unlock carries no unlock signal -- same as the field missing."""
    assert stack.score(_brief(SENTINEL)) == stack.score(_brief(None))
