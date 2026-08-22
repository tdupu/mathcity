"""#117 — order outcomes come from the event log, and punctual failure is not health.

REPLACES the premise of test_orders_status.py::test_outcome_is_unknown_not_green,
which asserted a blanket `unknown`. That was built on a measurement I got wrong:
`gc order history` carries no outcome, but `<city-root>/.gc/events.jsonl` does --
order.fired / order.completed / order.failed, 6,593 events across 74 subjects.

The load-bearing case is `mol-dog-compactor`: 61 fired, 0 completed, 60 failed.
It fires PUNCTUALLY, so any health signal keyed on "did it run lately" renders it
green. `orphan-sweep` (161 fired, 1 completed) is the second, so the test cannot
pass by special-casing one name.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.orders import orders_status  # noqa: E402

ORDERS = [
    {"name": "mol-dog-compactor", "type": "formula", "trigger": "cooldown", "enabled": True},
    {"name": "orphan-sweep", "type": "formula", "trigger": "cooldown", "enabled": True},
    {"name": "dolt-health", "type": "exec", "trigger": "cooldown", "enabled": True},
    {"name": "never-fired-order", "type": "exec", "trigger": "manual", "enabled": True},
]

EVENTS = [
    # fires punctually, never succeeds -- the case that must not render healthy
    {"type": "order.fired", "subject": "mol-dog-compactor", "ts": "2026-08-22T10:00:00Z"},
    {"type": "order.failed", "subject": "mol-dog-compactor", "ts": "2026-08-22T10:00:01Z"},
    {"type": "order.fired", "subject": "mol-dog-compactor", "ts": "2026-08-22T11:00:00Z"},
    {"type": "order.failed", "subject": "mol-dog-compactor", "ts": "2026-08-22T11:00:01Z"},
    # one ancient success, then only failures
    {"type": "order.completed", "subject": "orphan-sweep", "ts": "2026-01-01T00:00:00Z"},
    {"type": "order.fired", "subject": "orphan-sweep", "ts": "2026-08-22T11:30:00Z"},
    {"type": "order.failed", "subject": "orphan-sweep", "ts": "2026-08-22T11:30:02Z"},
    # a genuinely healthy one
    {"type": "order.fired", "subject": "dolt-health", "ts": "2026-08-22T11:45:00Z"},
    {"type": "order.completed", "subject": "dolt-health", "ts": "2026-08-22T11:45:01Z"},
]


def _reader():
    def read(what: str):
        return {"orders": ORDERS, "history": [], "events": EVENTS}[what]

    return read


def _row(payload, name):
    return next(r for r in payload["orders"] if r["name"] == name)


def test_a_failing_order_reports_failed_not_unknown():
    out = orders_status(_reader())
    assert _row(out, "mol-dog-compactor")["last_outcome"] == "failed"
    assert _row(out, "orphan-sweep")["last_outcome"] == "failed"


def test_a_succeeding_order_reports_completed():
    out = orders_status(_reader())
    assert _row(out, "dolt-health")["last_outcome"] == "completed"


def test_an_order_absent_from_the_log_is_unknown_not_healthy():
    """`unknown` survives -- but only for orders the log has never seen."""
    out = orders_status(_reader())
    row = _row(out, "never-fired-order")
    assert row["last_outcome"] == "unknown"
    assert row["ever_ran"] is False


def test_punctual_total_failure_is_not_healthy():
    """The §5.7 case, and the whole point of the slice.

    `mol-dog-compactor` fired more recently than anything else. A freshness
    signal renders it green. Health must be keyed on the OUTCOME.
    """
    out = orders_status(_reader())
    compactor = _row(out, "mol-dog-compactor")
    assert compactor["healthy"] is False, "an order that never succeeds is not healthy"
    assert compactor["last_executed"] is not None, "it did run -- freshness alone would say green"


def test_the_failing_orders_are_counted_where_a_reader_will_see_them():
    out = orders_status(_reader())
    assert out["failing"] == 2, "two orders last failed; the summary must say so"
    assert out["outcome_recorded"] == 3, "three of four orders have a recorded outcome"
