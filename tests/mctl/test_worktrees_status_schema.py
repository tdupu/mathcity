"""#203: worktrees_status must satisfy its DECLARED schema, on both the happy
path and the failed-read path.

Modeled on `test_orders_status_schema.py`: reproduces the dispatcher's own
envelope step (`setdefault diagnostics`, inject `trace_id`) and runs the exact
`schema_errors` check the dispatcher runs, against the tool's declared
`output_schema`. A string diagnostic (rather than a typed object) fails this;
`worktrees_status` never emits one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import mcp_server  # noqa: E402
from mctl_core.schemas import schema_errors  # noqa: E402
from mctl_core.worktrees import worktrees_status  # noqa: E402


def _output_schema(tool_name: str) -> dict:
    tool = next(t for t in mcp_server.TOOLS if t.name == tool_name)
    return tool.output_schema


def _as_served(payload: dict) -> dict:
    payload.setdefault("diagnostics", [])
    payload["trace_id"] = "trace-fixture"
    return payload


def _reader(rigs, rows_by_root, *, fail_rigs=()):
    def read(op, *args):
        if op == "rigs":
            return rigs
        if op == "worktree_rows":
            _name, root = args
            if root in fail_rigs:
                raise RuntimeError(f"git worktree list unavailable: {root}")
            return rows_by_root.get(root, [])
        raise KeyError(op)

    return read


def _raw_row(path):
    return {
        "path": path,
        "branch": "main",
        "head": "deadbeef",
        "bare": False,
        "detached": False,
        "locked_reason": None,
        "prunable_reason": None,
        "committed_at": "2026-08-01T00:00:00Z",
        "merged": True,
        "commits_ahead": 0,
        "size_bytes": 2048,
    }


def test_healthy_response_with_rows_satisfies_declared_schema():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(rigs, {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1")]})

    payload = _as_served(worktrees_status(read))

    violations = schema_errors(payload, _output_schema("worktrees_status"))
    assert violations == [], f"worktrees_status healthy response violates its declared schema: {violations}"


def test_roster_unreachable_response_satisfies_declared_schema():
    def read(op, *args):
        raise RuntimeError("rig roster unavailable")

    payload = _as_served(worktrees_status(read))

    violations = schema_errors(payload, _output_schema("worktrees_status"))
    assert violations == [], f"worktrees_status unreachable response violates its declared schema: {violations}"
    assert payload["diagnostics"], "the unreachable path must emit a diagnostic"
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d) for d in payload["diagnostics"]
    )


def test_partial_rig_failure_response_satisfies_declared_schema():
    rigs = [{"name": "hecke", "root": "/rigs/hecke"}, {"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1")]},
        fail_rigs={"/rigs/hecke"},
    )

    payload = _as_served(worktrees_status(read))

    violations = schema_errors(payload, _output_schema("worktrees_status"))
    assert violations == [], f"worktrees_status degraded response violates its declared schema: {violations}"


def test_every_rig_failing_response_satisfies_declared_schema():
    rigs = [{"name": "hecke", "root": "/rigs/hecke"}]
    read = _reader(rigs, {}, fail_rigs={"/rigs/hecke"})

    payload = _as_served(worktrees_status(read))

    violations = schema_errors(payload, _output_schema("worktrees_status"))
    assert violations == [], f"worktrees_status all-rigs-failed response violates its declared schema: {violations}"
