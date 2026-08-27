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


def _outcome_reader():
    """A reader whose event log records one failure and one completion."""

    def read(what: str):
        if what == "orders":
            return [
                {"name": "dolt-health", "scoped_name": "city:dolt-health", "type": "exec",
                 "trigger": "cooldown", "interval": "5m", "enabled": True, "source": "city"},
                {"name": "mol-dog-compactor", "scoped_name": "mol-dog-compactor",
                 "type": "exec", "trigger": "cooldown", "interval": "1m",
                 "enabled": True, "source": "pack"},
            ]
        if what == "history":
            return []
        if what == "events":
            return [
                {"type": "order.completed", "subject": "dolt-health",
                 "ts": "2026-08-22T05:07:33Z"},
                {"type": "order.failed", "subject": "mol-dog-compactor",
                 "ts": "2026-08-22T05:10:00Z"},
            ]
        if what == "formulas":
            return ["brief-gate-keep"]
        raise KeyError(what)

    return read


def test_a_failed_outcome_and_the_failing_count_both_render(tmp_path):
    """mc-0mhh: a failing order is visible AND counted above the table.

    Before this the screen claimed every outcome was `unknown` and rendered no
    failing count, so an order the event log records as failed was invisible."""
    from mctl_dashboard.app import Request

    dash = _dash(tmp_path)
    dash.orders_reader = _outcome_reader()
    html = dash.handle(Request.get("/orders")).body

    assert 'data-outcome="failed"' in html, "a failed order must render as failed"
    assert "1 failing" in html, "the failing count belongs above the table"
    # And the order that completed must not be dressed as failed.
    assert 'data-outcome="completed"' in html


def test_a_scoped_name_is_shown_when_it_differs_from_the_name(tmp_path):
    """mc-0mhh: 'Show scoped names when they differ from names.'"""
    from mctl_dashboard.app import Request

    dash = _dash(tmp_path)
    dash.orders_reader = _outcome_reader()
    html = dash.handle(Request.get("/orders")).body

    assert "city:dolt-health" in html, "a scoped name that differs must be shown"


def test_the_orders_route_wires_a_reader_from_the_client_city(tmp_path, monkeypatch):
    """mc-0mhh acceptance: the served route is built through ordinary
    construction, NOT by a test assigning `dash.orders_reader` by hand.

    Observed-failing before the fix: `_orders` used a stopgap reader that raised
    'no orders reader configured', so nothing was read from the client's city.
    """
    import mctl_core.orders as orders_core
    from mctl_dashboard.app import Request

    seen: dict = {}

    def fake_city_reader(city_root):
        seen["city"] = city_root

        def read(what: str):
            if what == "orders":
                return [{"name": "wired-order", "scoped_name": "wired-order",
                         "type": "exec", "trigger": "cooldown", "interval": "5m",
                         "enabled": True, "source": "city"}]
            if what in ("history", "events"):
                return []
            if what == "formulas":
                return []
            raise KeyError(what)

        return read

    monkeypatch.setattr(orders_core, "city_reader", fake_city_reader)

    dash = _dash(tmp_path)  # NO orders_reader injection
    html = dash.handle(Request.get("/orders")).body

    assert seen.get("city") is not None, "the route built no reader from the city"
    assert seen["city"] == dash.client.city, "the reader must bind to the client's city"
    assert "no orders reader configured" not in html, "the stopgap must be gone"
    assert "wired-order" in html, "the production-wired reader must reach the page"
