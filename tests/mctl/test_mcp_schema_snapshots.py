"""Snapshot the MCP tool schemas so breaking changes are visible in review.

Plan Slice 6 step 8. The schemas are the contract every MCP client codes
against; without a snapshot a renamed field or a loosened type lands as an
invisible diff inside a large implementation file.

Regenerate deliberately, never reflexively:

    MCTL_UPDATE_MCP_SNAPSHOT=1 python3 -m pytest tests/mctl/test_mcp_schema_snapshots.py

and read the resulting diff as a compatibility review.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server
from mctl_core.schemas import DIAGNOSTIC_SCHEMA, schema_errors, unsupported_keywords

SNAPSHOT = Path(__file__).resolve().parent / "fixtures" / "mcp_tool_schemas.json"

FORBIDDEN_TOOL_NAMES = {"shell", "gc", "bd", "mctl", "run_command", "exec", "run_shell"}


def current() -> dict[str, object]:
    return {
        tool.name: {
            "description": tool.description,
            "external_ready": tool.external_ready,
            "inputSchema": tool.input_schema,
            "mutating": tool.mutating,
            "outputSchema": tool.output_schema,
            "title": tool.title,
        }
        for tool in mcp_server.TOOLS
    }


def rendered(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_every_tool_has_a_schema_snapshot():
    if os.environ.get("MCTL_UPDATE_MCP_SNAPSHOT") == "1":
        SNAPSHOT.write_text(rendered(current()), encoding="utf-8")

    assert SNAPSHOT.is_file(), (
        f"{SNAPSHOT} is missing; regenerate with MCTL_UPDATE_MCP_SNAPSHOT=1"
    )
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert set(snapshot) == set(current()), "a tool was added or removed without a snapshot update"
    assert snapshot == current(), (
        "MCP tool schemas changed. Review the diff as a client-compatibility "
        "change, then regenerate with MCTL_UPDATE_MCP_SNAPSHOT=1."
    )


def test_the_snapshot_names_no_generic_command_execution_tool():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert not set(snapshot) & FORBIDDEN_TOOL_NAMES


def test_every_snapshot_schema_is_a_closed_object():
    """Open input objects silently accept whatever a client invents."""
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    for name, entry in snapshot.items():
        assert entry["inputSchema"]["type"] == "object", name
        assert entry["inputSchema"]["additionalProperties"] is False, name
        assert entry["outputSchema"]["type"] == "object", name


def test_every_output_schema_requires_the_diagnostic_envelope():
    """Plan §4: diagnostics and a trace id in every response, not most."""
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    for name, entry in snapshot.items():
        required = set(entry["outputSchema"]["required"])
        assert {"diagnostics", "trace_id"} <= required, name
        assert entry["outputSchema"]["properties"]["diagnostics"]["items"] == DIAGNOSTIC_SCHEMA, name


def test_every_artifact_bearing_output_schema_requires_artifact_trust():
    """Q5 is unresolved, so artifact state may never be reported unqualified."""
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    artifact_bearing = {
        "briefs_list",
        "briefs_present",
    "briefs_show",
        "briefs_doctor",
        "briefs_validate",
        "briefs_relay_adjudication",
        "briefs_defer",
        "briefs_create",
    }

    for name in artifact_bearing:
        required = set(snapshot[name]["outputSchema"]["required"])
        assert {"artifact_trust", "untrusted_diagnostics"} <= required, name


def test_mutating_tools_declare_a_dry_run_field_that_defaults_to_true():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    mutating = [name for name, entry in snapshot.items() if entry["mutating"]]
    assert sorted(mutating) == [
        "bead_comment",
        "briefs_create",
        "briefs_defer",
        "briefs_relay_adjudication",
        "commission_brief",
        "create_defect_bead",
        "create_github_issue",
        "create_issue_bead",
        "dashboard_restart",
        "decisions_to_briefs",
        "standardize_github_issue",
        "work_dispatch",
        "work_dispatch_event",
    ]
    for name in mutating:
        dry_run = snapshot[name]["inputSchema"]["properties"]["dry_run"]
        assert dry_run["type"] == "boolean", name
        assert dry_run["default"] is True, name
        assert snapshot[name]["external_ready"] is False, name


def test_no_schema_uses_a_keyword_the_validator_cannot_enforce():
    """An advertised constraint nobody checks is worse than no constraint."""
    for tool in mcp_server.TOOLS:
        assert unsupported_keywords(tool.input_schema) == set(), tool.name
        assert unsupported_keywords(tool.output_schema) == set(), tool.name


def test_the_snapshot_is_itself_schema_valid():
    """A snapshot that no longer parses as JSON Schema proves nothing."""
    meta = {
        "type": "object",
        "required": ["type"],
        "properties": {"type": {"type": "string"}},
        "additionalProperties": True,
    }
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    for name, entry in snapshot.items():
        assert schema_errors(entry["inputSchema"], meta) == [], name
        assert schema_errors(entry["outputSchema"], meta) == [], name
