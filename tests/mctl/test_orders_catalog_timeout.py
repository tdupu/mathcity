"""#156 follow-up — bounds are PER-CALLER, because the callers do not share a cost.

Measured across one night, same command, same city:

    gc order list --json      28.34s · 43.10s · 42.84s · 46.72s · 89s
    gc order history --json   55.46s

The dashboard calls both, so its real cost is the SUM -- ~84s today, higher
earlier. An MCP request cannot wait that long; a dashboard render always must.

A single module constant cannot serve both. My first attempt set one to 15s,
which meant the catalog timed out on EVERY call -- a path that cannot succeed,
shipped as graceful degradation. stick-dog measured it and refused it.

The old test asserted `CATALOG_TIMEOUT_SECONDS <= 15`: it checked the bound was
SMALL, never that it was ACHIEVABLE, so it passed on any number including zero.
These assert a bound against the cost it must accommodate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.orders import (  # noqa: E402
    DASHBOARD_CATALOG_TIMEOUT_SECONDS,
    EVENT_LOG_ONLY,
    MEASURED_CATALOG_WORST_SECONDS,
    orders_status,
)

EVENTS = [
    {"type": "order.fired", "subject": "orphan-sweep", "ts": "2026-08-22T14:10:00Z"},
    {"type": "order.failed", "subject": "orphan-sweep", "ts": "2026-08-22T14:10:34Z"},
]


def test_the_dashboard_bound_can_actually_succeed():
    """The bound must accommodate the worst measured cost of the calls it wraps.

    This is the assertion the first version lacked. A bound below the measured
    cost is a path that cannot succeed; it fails here rather than in production.
    """
    assert DASHBOARD_CATALOG_TIMEOUT_SECONDS >= MEASURED_CATALOG_WORST_SECONDS, (
        f"bound {DASHBOARD_CATALOG_TIMEOUT_SECONDS}s cannot accommodate the measured "
        f"worst case {MEASURED_CATALOG_WORST_SECONDS}s -- it would time out every call"
    )


def test_the_measured_worst_case_covers_both_calls_the_dashboard_makes():
    """The dashboard pays list + history. Budgeting for one is budgeting for half."""
    assert MEASURED_CATALOG_WORST_SECONDS >= 89 + 55, (
        "the dashboard makes two gc calls; the budget must cover their sum"
    )


def test_the_mcp_path_takes_no_catalog_bound_at_all():
    """EVENT_LOG_ONLY spawns no subprocess, so no timeout applies to it."""
    calls = []

    def read(what: str):
        calls.append(what)
        if what == "events":
            return EVENTS
        raise AssertionError(f"EVENT_LOG_ONLY must not read {what!r}")

    out = orders_status(read, mode=EVENT_LOG_ONLY)
    assert calls == ["events"]
    assert out["known_outcomes"]["orphan-sweep"] == "failed"
    assert out["total"] is None
