"""#156 — the order-outcome projection must be reachable as a typed tool.

`mctl_core.orders` folds `<city-root>/.gc/events.jsonl` into a per-order outcome,
and nothing exposes it: zero registered tools carry "order" in their name. So an
MCP caller — which is how agents reach mctl — cannot learn that `orphan-sweep`
has fired 163 times and completed once.

The load-bearing assertion is `test_the_tool_reports_a_failing_order_as_failed`.
A tool that returns the catalog without outcomes would satisfy a naive "is it
registered" test and leave the gap exactly where it was.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))


def _spec(name: str):
    from mctl_core.mcp_server import TOOLS

    return next((t for t in TOOLS if t.name == name), None)


def test_orders_status_is_a_registered_tool():
    assert _spec("orders_status") is not None, "no typed tool exposes the order projection"


def test_formulas_catalog_is_a_registered_tool():
    assert _spec("formulas_catalog") is not None


def test_the_tool_declares_last_outcome_in_its_output_schema():
    """Registration is not enough — the outcome must be in the contract.

    A tool that returns names and triggers but no outcome is `#156` with a
    typed wrapper on it.
    """
    spec = _spec("orders_status")
    schema = repr(spec.output_schema)
    assert "last_outcome" in schema, "the outcome is not in the declared output"
    assert "healthy" in schema


def test_the_tool_reports_a_failing_order_as_failed(tmp_path):
    """The whole point: an order that fires and fails must say `failed`.

    Uses the same shape as the live data -- `orphan-sweep` fires punctually and
    fails -- so a projection that reported freshness instead of outcome fails
    this test.
    """
    from mctl_core.orders import orders_status

    events = [
        {"type": "order.fired", "subject": "orphan-sweep", "ts": "2026-08-22T14:10:00Z"},
        {"type": "order.failed", "subject": "orphan-sweep", "ts": "2026-08-22T14:10:34Z"},
    ]
    orders = [{"name": "orphan-sweep", "type": "exec", "trigger": "cooldown", "enabled": True}]

    def read(what: str):
        return {"orders": orders, "history": [], "events": events}[what]

    row = orders_status(read)["orders"][0]
    assert row["last_outcome"] == "failed"
    assert row["healthy"] is False


def test_the_dashboard_allowlist_names_the_new_tools():
    """`ALLOWED_TOOLS` is spelled out, never derived -- so it must be updated."""
    from mctl_dashboard.client import ALLOWED_TOOLS

    assert "orders_status" in ALLOWED_TOOLS
    assert "formulas_catalog" in ALLOWED_TOOLS
