"""#117 — orders_status + formulas_catalog, without the event log.

These cover the degraded path: what the tool reports when only `gc order list`
and `gc order history` are available. Outcomes come from the event log and the
cases that exercise them are in test_order_outcomes.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.orders import formulas_catalog, orders_status  # noqa: E402


def _reader(orders=None, formulas=None, history=None, fail=None):
    """A stand-in for the 30s `gc` calls. Injected so tests do not shell out."""

    def read(what: str):
        if fail == what:
            raise RuntimeError(f"gc {what} unavailable")
        return {"orders": orders or [], "formulas": formulas or [], "history": history or []}[what]

    return read


ORDER = {
    "name": "dolt-health",
    "scoped_name": "dolt-health",
    "description": "Check dolt server health without restarting it",
    "type": "exec",
    "trigger": "cooldown",
    "interval": "5m",
    "enabled": True,
    "formula_layer": "",
    "source": "city",
}


def test_orders_status_reports_each_order_with_its_trigger():
    out = orders_status(_reader(orders=[ORDER]))
    assert len(out["orders"]) == 1
    row = out["orders"][0]
    assert row["name"] == "dolt-health"
    assert row["trigger"] == "cooldown"
    assert row["enabled"] is True


def test_outcome_is_unknown_when_the_event_log_is_unavailable():
    """With no event log, an order that ran still has an unknown outcome.

    CORRECTED. This test previously asserted a blanket `unknown` on the claim
    that the city records no outcomes anywhere -- which was false: they are in
    `<city-root>/.gc/events.jsonl` (#156). What survives is narrower and still
    worth pinning: `gc order history` alone cannot settle an outcome, so a
    reader without the event log must say `unknown` rather than infer success
    from execution. The outcome-bearing cases live in test_order_outcomes.py.
    """
    history = [{"order": "dolt-health", "bead_id": "gt-wisp-1", "executed": "2026-08-22T05:07:33Z"}]
    out = orders_status(_reader(orders=[ORDER], history=history))
    row = out["orders"][0]
    assert row["last_outcome"] == "unknown", (
        "without the event log, execution alone must not imply success"
    )
    assert row["last_executed"] == "2026-08-22T05:07:33Z"


def test_an_order_that_never_ran_is_also_unknown_not_a_zero():
    """`never ran` and `ran, result unrecorded` are both unknown, distinguishably."""
    out = orders_status(_reader(orders=[ORDER], history=[]))
    row = out["orders"][0]
    assert row["last_outcome"] == "unknown"
    assert row["last_executed"] is None
    assert row["ever_ran"] is False


def test_a_failed_read_is_degraded_never_zero_orders():
    """A probe that could not run must not render as `there are no orders`."""
    out = orders_status(_reader(fail="orders"))
    assert out["state"] == "unreachable"
    assert out["orders"] == []
    assert out["total"] is None, "total must be None (unknown), never 0"
    # Diagnostics are typed OBJECTS (code/message/severity), never strings --
    # a string here dies FATAL against the declared MCP object schema (#203).
    assert any("unavailable" in d["message"].lower() for d in out["diagnostics"])
    assert all(isinstance(d, dict) and "code" in d for d in out["diagnostics"])


def test_formulas_catalog_lists_formulas():
    out = formulas_catalog(_reader(formulas=["brief-archive-sweep", "brief-gate-keep"]))
    assert out["total"] == 2
    assert "brief-gate-keep" in [f["name"] for f in out["formulas"]]


def test_formulas_catalog_failed_read_is_unknown_not_empty():
    out = formulas_catalog(_reader(fail="formulas"))
    assert out["state"] == "unreachable"
    assert out["total"] is None
