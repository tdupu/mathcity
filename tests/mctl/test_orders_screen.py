"""#117 — orders and formulas must be ON A PAGE, not merely computable.

Rule 1 of the city-dashboard recovery: a slice does not close until something
renders. Five slices closed with typed tools and zero pixels (#153). These tests
assert the page, not the tool.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _dash(tmp_path):
    import multi_rig
    from mctl_dashboard.app import Dashboard
    from mctl_dashboard.client import InProcessMcpClient

    fixture = multi_rig.build(tmp_path)
    client = InProcessMcpClient(city=fixture.city_root, env=fixture.env)
    return Dashboard(client, city_wide=True, rig=None)


def _orders_reader():
    def read(what: str):
        if what == "orders":
            return [
                {"name": "dolt-health", "scoped_name": "dolt-health", "type": "exec",
                 "trigger": "cooldown", "interval": "5m", "enabled": True,
                 "description": "Check dolt server health", "source": "city"},
                {"name": "brief-gate-keep", "scoped_name": "brief-gate-keep", "type": "formula",
                 "trigger": "condition", "interval": "", "enabled": True,
                 "description": "Gate the brief", "source": "pack"},
            ]
        if what == "history":
            return [{"order": "dolt-health", "bead_id": "gt-wisp-1",
                     "executed": "2026-08-22T05:07:33Z"}]
        if what == "formulas":
            return ["brief-archive-sweep", "brief-gate-keep"]
        raise KeyError(what)

    return read


def test_the_orders_page_renders_order_names(tmp_path):
    from mctl_dashboard.app import Request

    dash = _dash(tmp_path)
    dash.orders_reader = _orders_reader()
    html = dash.handle(Request.get("/orders")).body

    assert "dolt-health" in html, "an order the city has is not on the page"
    assert "brief-gate-keep" in html


def test_the_orders_page_says_unknown_never_green(tmp_path):
    """The load-bearing render assertion.

    `dolt-health` HAS run. The city records no outcome for it (#156), so the
    page must say `unknown` -- not a tick, not `ok`, not blank. A blank cell
    reads as "fine" to every operator who has ever seen a table.
    """
    from mctl_dashboard.app import Request

    dash = _dash(tmp_path)
    dash.orders_reader = _orders_reader()
    html = dash.handle(Request.get("/orders")).body

    assert "unknown" in html.lower(), "an unrecorded outcome must render as unknown"
    for green in ("✓", "&check;", ">ok<", "success"):
        assert green not in html, f"page implies success it cannot know: {green!r}"


def test_the_orders_page_renders_formulas_too(tmp_path):
    from mctl_dashboard.app import Request

    dash = _dash(tmp_path)
    dash.orders_reader = _orders_reader()
    html = dash.handle(Request.get("/orders")).body

    assert "brief-archive-sweep" in html, "formulas are the other half of #117"


def test_an_unreachable_read_renders_a_reason_not_zero(tmp_path):
    """§5.4: a failed probe never renders as a value."""
    from mctl_dashboard.app import Request

    def broken(what: str):
        raise RuntimeError("gc unavailable")

    dash = _dash(tmp_path)
    dash.orders_reader = broken
    html = dash.handle(Request.get("/orders")).body

    assert "unavailable" in html.lower() or "could not" in html.lower()
    assert "0 orders" not in html.lower(), "an unreadable surface must not render as zero"
