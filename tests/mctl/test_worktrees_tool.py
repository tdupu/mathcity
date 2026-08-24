"""#120 — worktrees_status must be reachable as a typed, city-scoped tool.

Modeled on test_costs_tool.py / test_fleet_sessions.py. The load-bearing
assertions: the tool is registered CITY_SCOPE (like fleet_sessions,
gates_status -- it fans across every registered rig, not one), and the
declared output schema names is_orphan/is_registered as two separate fields
and created_by/step as the honest-unrecorded fields.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))


def _spec(name: str):
    from mctl_core.mcp_server import TOOLS

    return next((t for t in TOOLS if t.name == name), None)


def test_worktrees_status_is_a_registered_tool():
    assert _spec("worktrees_status") is not None, "no typed tool exposes the worktree inventory"


def test_the_tool_is_city_scoped_not_rig_scoped():
    from mctl_core.mcp_server import CITY_SCOPE

    spec = _spec("worktrees_status")
    assert spec.scope == CITY_SCOPE


def test_the_tool_declares_is_orphan_and_is_registered_as_separate_fields():
    spec = _spec("worktrees_status")
    schema = repr(spec.output_schema)
    assert "is_orphan" in schema
    assert "is_registered" in schema


def test_the_tool_declares_created_by_and_step_and_molecule():
    spec = _spec("worktrees_status")
    schema = repr(spec.output_schema)
    for field in ("created_by", "step", "molecule"):
        assert field in schema, f"{field} is not in the declared output"


def test_the_tool_declares_harvestable_and_merged_and_commits():
    spec = _spec("worktrees_status")
    schema = repr(spec.output_schema)
    for field in ("harvestable", "merged", "commits"):
        assert field in schema, f"{field} is not in the declared output"


def test_the_tool_handler_shapes_via_the_injected_reader():
    from mctl_core.mcp_server import CityScope
    from mctl_core.mcp_server import TOOLS

    spec = _spec("worktrees_status")

    scope = CityScope(
        city_root=Path("/tmp/city"),
        discovery_path="/tmp/city",
        invocation_cwd=Path("/tmp/city"),
        trace_id="test-trace",
        rigs=(),
        config={},
    )
    payload = spec.handler(scope, {})
    # Zero registered rigs is a real, measured state -- not "unreachable".
    assert payload["state"] == "healthy"
    assert payload["total"] == 0
    assert payload["worktrees"] == []
    assert payload["orphans"] is None


def test_the_dashboard_allowlist_names_worktrees_status():
    """`ALLOWED_TOOLS` is spelled out, never derived -- so it must be updated."""
    from mctl_dashboard.client import ALLOWED_TOOLS

    assert "worktrees_status" in ALLOWED_TOOLS
