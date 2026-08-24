"""#203: orders_status / formulas_catalog must satisfy their DECLARED schema.

`orders_status` built `diagnostics` as `list[str]`, but every MCP response is
validated against the shared object schema (`diagnostics` items are objects with
code/message/severity). Every call therefore died FATAL
`MCTL_MCP_OUTPUT_SCHEMA_VIOLATION` at `diagnostics[0]` -- the one path a fixture
with a healthy event log never exercises, because the diagnostic is only
appended when a read fails.

These tests reproduce the server's own post-handler step (setdefault diagnostics,
inject trace_id) and then run the exact `schema_errors` check the dispatcher runs
(mcp_server.py), against the tool's declared `output_schema`. A string diagnostic
fails them; a typed object passes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import mcp_server  # noqa: E402
from mctl_core.orders import EVENT_LOG_ONLY, formulas_catalog, orders_status  # noqa: E402
from mctl_core.schemas import schema_errors  # noqa: E402


def _output_schema(tool_name: str) -> dict:
    tool = next(t for t in mcp_server.TOOLS if t.name == tool_name)
    return tool.output_schema


def _as_served(payload: dict) -> dict:
    """Reproduce the dispatcher envelope: diagnostics default + injected trace_id.

    Mirrors mcp_server.MctlServer.handle so the test validates what a client
    actually receives, not the bare handler return.
    """
    payload.setdefault("diagnostics", [])
    payload["trace_id"] = "trace-fixture"
    return payload


def _failing_reader(*failing: str):
    def read(what: str):
        if what in failing:
            raise RuntimeError(f"gc {what} unavailable")
        return []

    return read


def test_event_log_only_response_satisfies_declared_schema():
    """The MCP request path (EVENT_LOG_ONLY) with a missing event log validates."""
    payload = _as_served(orders_status(_failing_reader("events"), mode=EVENT_LOG_ONLY))
    violations = schema_errors(payload, _output_schema("orders_status"))
    assert violations == [], (
        f"orders_status EVENT_LOG_ONLY response violates its declared schema: {violations}"
    )
    # And the diagnostics really are the typed objects the schema requires.
    assert payload["diagnostics"], "the missing-event-log path must emit a diagnostic"
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in payload["diagnostics"]
    )


def test_unreachable_catalog_response_satisfies_declared_schema():
    """The full read path with a failed catalog read validates against schema."""
    payload = _as_served(orders_status(_failing_reader("orders")))
    violations = schema_errors(payload, _output_schema("orders_status"))
    assert violations == [], (
        f"orders_status unreachable response violates its declared schema: {violations}"
    )


def test_formulas_catalog_unreachable_response_satisfies_declared_schema():
    """formulas_catalog shares `_unreachable`; its failed read must validate too."""
    payload = _as_served(formulas_catalog(_failing_reader("formulas")))
    violations = schema_errors(payload, _output_schema("formulas_catalog"))
    assert violations == [], (
        f"formulas_catalog unreachable response violates its declared schema: {violations}"
    )
