"""#66: the defer window was written and then collapsed to a boolean.

`briefs_defer` writes three facts — `defer_until` onto the bead, `defer_reason`
and `deferred_at` into its metadata. `_defer_until` read the date, compared it,
and returned `True`/`False`, discarding everything. So the Deferred screen could
say a brief was deferred and not until when, by whom, or why — and it said so in
its own panel: *"The defer window is not shown, because it is not readable."*

THE SHARPER HALF, and the reason `expired` exists as a field. The old predicate
returned `False` for an expired deferral AND for a brief that was never
deferred. Those are different things: one is a brief that is now DUE, the other
is a brief nobody parked. Collapsing them is how a brief comes back from a
window nobody was told had closed.

`_defer_until`'s own semantics are deliberately UNCHANGED — `decision_state`
callers branch on it, and an expired deferral is correctly no longer "deferred".
It now derives from `deferral_detail` so the two cannot drift apart, which is
what the last two tests pin.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.briefs import _defer_until, deferral_detail

FUTURE = (date.today() + timedelta(days=30)).isoformat()
PAST = (date.today() - timedelta(days=30)).isoformat()


class _Bead:
    """Minimal stand-in: `deferral_detail` reads only `raw`."""

    def __init__(self, raw):
        self.raw = raw


def _deferred(until=None, reason=None, deferred_at=None, key="defer_until"):
    raw = {}
    if until is not None:
        raw[key] = until
    metadata = {}
    if reason is not None:
        metadata["defer_reason"] = reason
    if deferred_at is not None:
        metadata["deferred_at"] = deferred_at
    if metadata:
        raw["metadata"] = metadata
    return _Bead(raw)


# --- the three facts that were being discarded -----------------------------


def test_all_three_written_facts_come_back() -> None:
    detail = deferral_detail(
        _deferred(until=FUTURE, reason="waiting on the server window", deferred_at="2026-08-01T00:00:00Z")
    )
    assert detail["until"] == FUTURE
    assert detail["reason"] == "waiting on the server window"
    assert detail["deferred_at"] == "2026-08-01T00:00:00Z"


def test_the_legacy_key_is_read_too() -> None:
    """`deferred_until` and `defer_until` were both accepted before; keep both."""
    assert deferral_detail(_deferred(until=FUTURE, key="deferred_until"))["until"] == FUTURE


def test_a_brief_with_no_deferral_returns_none() -> None:
    """None, not an empty dict: 'not deferred' is a fact, not a blank record."""
    assert deferral_detail(_Bead({})) is None
    assert deferral_detail(_Bead({"metadata": {}})) is None


# --- expired is REPORTED, not filtered -------------------------------------


def test_an_expired_deferral_is_still_a_deferral() -> None:
    """The whole point. The old boolean erased this row entirely."""
    detail = deferral_detail(_deferred(until=PAST, reason="window closed"))
    assert detail is not None, "an expired deferral must not read as no deferral"
    assert detail["expired"] is True
    assert detail["until"] == PAST


def test_an_unexpired_deferral_is_not_expired() -> None:
    assert deferral_detail(_deferred(until=FUTURE))["expired"] is False


def test_no_date_means_expiry_is_unknown_not_false() -> None:
    """P6.2: 'we cannot tell whether the window passed' is not 'it has not'."""
    detail = deferral_detail(_deferred(reason="parked, no date recorded"))
    assert detail is not None
    assert detail["until"] is None
    assert detail["expired"] is None, "None, never False — False asserts it is still open"


# --- decision_state semantics must NOT move --------------------------------


def test_defer_until_still_true_only_for_an_open_window() -> None:
    assert _defer_until(_deferred(until=FUTURE)) is True


def test_defer_until_still_false_for_expired_and_absent() -> None:
    """Unchanged on purpose: an expired deferral is correctly not 'deferred'.
    The information is preserved on `deferral`, not in this predicate."""
    assert _defer_until(_deferred(until=PAST)) is False
    assert _defer_until(_Bead({})) is False
    assert _defer_until(_deferred(reason="no date")) is False


def test_the_predicate_and_the_detail_cannot_drift() -> None:
    """`_defer_until` derives from `deferral_detail`, so a change to one moves
    the other. Two independent readers of the same field is how they disagreed."""
    for bead in (_deferred(until=FUTURE), _deferred(until=PAST), _Bead({}), _deferred(reason="r")):
        detail = deferral_detail(bead)
        expected = bool(detail and detail["until"] and detail["expired"] is False)
        assert _defer_until(bead) is expected
