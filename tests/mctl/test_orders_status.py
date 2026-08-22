"""#117 — orders_status + formulas_catalog.

The load-bearing test here is `test_outcome_is_unknown_not_green`. `gc order
history` records THAT an order ran and never WHETHER it succeeded (#156), so
every outcome this tool reports is genuinely unknown. A tool that renders the
24 orders with history as healthy would be asserting something the city does
not know -- P6.2, in the noun Taylor asked for by name.
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


def test_outcome_is_unknown_not_green():
    """An order WITH history still has an unknown outcome.

    This fails if anyone maps "it executed" to "it succeeded". The history
    entry carries no outcome field; inventing one is the defect #156 names.
    """
    history = [{"order": "dolt-health", "bead_id": "gt-wisp-1", "executed": "2026-08-22T05:07:33Z"}]
    out = orders_status(_reader(orders=[ORDER], history=history))
    row = out["orders"][0]
    assert row["last_outcome"] == "unknown", (
        "an order that ran has an unknown outcome -- the city records no result"
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
    assert any("unavailable" in d.lower() for d in out["diagnostics"])


def test_formulas_catalog_lists_formulas():
    out = formulas_catalog(_reader(formulas=["brief-archive-sweep", "brief-gate-keep"]))
    assert out["total"] == 2
    assert "brief-gate-keep" in [f["name"] for f in out["formulas"]]


def test_formulas_catalog_failed_read_is_unknown_not_empty():
    out = formulas_catalog(_reader(fail="formulas"))
    assert out["state"] == "unreachable"
    assert out["total"] is None
