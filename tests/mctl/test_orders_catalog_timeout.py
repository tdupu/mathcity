"""#156 follow-up — the catalog read must be BOUNDED, not merely handled.

The merged reader gives each `gc` call `timeout=120`, three calls deep, so the
worst case is 360 s. Measured in-city, `gc order list --json` alone takes
**89 s** and the whole tool timed out at 120 s when I finally ran it.

The failure-handling path was already correct: a raising catalog degrades to
`unreachable`, never to zero. That was never the bug. The bug is that the tool
WAITS -- it is registered, schema-correct, correctly-degrading, and unusable.
CT13.1: presence is not performance.

So the assertion is about the BUDGET, which is the thing that was wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.orders import CATALOG_TIMEOUT_SECONDS, EVENT_LOG_ONLY, orders_status  # noqa: E402

EVENTS = [
    {"type": "order.fired", "subject": "orphan-sweep", "ts": "2026-08-22T14:10:00Z"},
    {"type": "order.failed", "subject": "orphan-sweep", "ts": "2026-08-22T14:10:34Z"},
]


def test_the_catalog_budget_is_servable():
    """89 s measured; 120 s budget. The bound must be under what a caller waits."""
    assert CATALOG_TIMEOUT_SECONDS <= 15, (
        "a catalog read that can take 89s must be bounded well under it, "
        "so the tool degrades fast instead of hanging"
    )


def test_event_log_only_mode_never_touches_gc():
    """The outcomes half is a local file. It must be servable with zero subprocesses."""
    calls = []

    def read(what: str):
        calls.append(what)
        if what == "events":
            return EVENTS
        raise AssertionError(f"EVENT_LOG_ONLY must not read {what!r}")

    out = orders_status(read, mode=EVENT_LOG_ONLY)
    assert calls == ["events"], f"touched more than the event log: {calls}"
    assert out["known_outcomes"]["orphan-sweep"] == "failed"


def test_event_log_only_reports_the_catalog_as_unreachable_not_zero():
    def read(what: str):
        if what == "events":
            return EVENTS
        raise AssertionError("should not be called")

    out = orders_status(read, mode=EVENT_LOG_ONLY)
    assert out["state"] == "unreachable"
    assert out["total"] is None, "None means we did not look; 0 would be a lie"
    assert any("not read" in str(d) or "order list" in str(d) for d in out["diagnostics"])
