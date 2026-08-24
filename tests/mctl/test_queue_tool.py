"""#113 — the queue projection must be reachable as a typed tool.

Modeled on test_orders_tool.py. The load-bearing assertion is
`test_the_tool_reports_blocked_on_for_a_blocked_bead`: a tool that returns the
six populations but strips `blocked_on` would satisfy a naive "is it
registered" check and leave the gap the brief calls out by name.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))


def _spec(name: str):
    from mctl_core.mcp_server import TOOLS

    return next((t for t in TOOLS if t.name == name), None)


def test_queue_status_is_a_registered_tool():
    assert _spec("queue_status") is not None, "no typed tool exposes the queue projection"


def test_the_tool_declares_next_up_is_prediction_in_its_output_schema():
    """Registration is not enough -- the REQUIRED prediction flag must be in the contract."""
    spec = _spec("queue_status")
    schema = repr(spec.output_schema)
    assert "next_up_is_prediction" in schema, "the prediction flag is not in the declared output"


def test_the_tool_declares_all_six_populations_in_its_output_schema():
    spec = _spec("queue_status")
    schema = repr(spec.output_schema)
    for population in ("ready_unclaimed", "blocked", "tail", "starved", "deferred", "next_up"):
        assert population in schema, f"{population} is not in the declared output"


def test_the_tool_reports_blocked_on_for_a_blocked_bead():
    from mctl_core.queue import queue_status

    def read(what: str):
        return {
            "ready_explain": {
                "ready": [],
                "blocked": [
                    {
                        "id": "mc-blocked",
                        "title": "Waiting on its dependency",
                        "blocked_by": [{"id": "mc-dep", "title": "The dependency"}],
                    }
                ],
            },
            "unclaimed": [],
            "deferred": [],
            "routed_ids": set(),
        }[what]

    out = queue_status(read)
    assert out["blocked"][0]["blocked_on"] == "mc-dep"
    assert out["next_up_is_prediction"] is True


def test_the_dashboard_allowlist_names_queue_status():
    """`ALLOWED_TOOLS` is spelled out, never derived -- so it must be updated."""
    from mctl_dashboard.client import ALLOWED_TOOLS

    assert "queue_status" in ALLOWED_TOOLS
