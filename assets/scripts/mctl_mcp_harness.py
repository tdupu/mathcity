#!/usr/bin/env python3
"""A minimal MCP client that proves the mctl MCP server end to end.

Slice 6 ships a server; a server with no client cannot be demonstrated, and a
slice that lands scaffolding no vertical consumes is what the plan's own slice
rules forbid. This is that client. It is small on purpose -- a proof, not a
product -- and it asserts exactly the claims Slice 6 makes:

  connect                  a real subprocess, a real stdio handshake
  tools_list               the declared typed surface is present
  typed_read_round_trip    a read response validates against the output schema
                           the server TRANSMITTED, not one compiled in here
  typed_schema_error       a bad call fails as a typed schema error -- not a
                           stack trace, not a prose string
  no_passthrough_tool      no shell/gc/bd/mctl/exec tool, no raw command field
  rollout_gate             the external surface really is closed

The typed-error check is the one that matters most. The entire argument for
MCP over prose skills is that failures stop being advisory; if a bad call
produced an untyped error, this slice would not have delivered its claim.

Run it by hand:

    python3 assets/scripts/mctl_mcp_harness.py --city <city-root> --rig <rig>
    python3 assets/scripts/mctl_mcp_harness.py --city <city-root> --rig <rig> --json

Exit status is 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.mcp_server import FORBIDDEN_TOOL_NAMES
from mctl_core.schemas import schema_errors

MCTL = SCRIPTS_ROOT / "mctl.py"

EXPECTED_TOOLS = (
    "briefs_adjudicate",
    "briefs_create",
    "briefs_defer",
    "briefs_doctor",
    "briefs_list",
    "briefs_options",
    "briefs_present",
    "briefs_show",
    "briefs_validate",
    "city_health",
    "context_resolve",
    "context_rigs",
    "decisions_to_briefs",
    "fleet_sessions",
    "formulas_catalog",
    "gates_status",
    "mayor_boot",
    "mayor_city_state",
    "mayor_conservation",
    "molecules_list",
    "molecules_show",
    "orders_status",
    "trace_replay_preview",
    "trace_show",
    "work_claim",
    "work_dispatch",
    "work_dispatch_event",
    "work_provenance",
    "work_ready",
    "work_status",
)

CLIENT_INFO = {"name": "mctl-mcp-harness", "version": "0.6.0"}
PROTOCOL_VERSION = "2025-06-18"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detail": self.detail,
            "evidence": self.evidence,
            "name": self.name,
            "passed": self.passed,
        }


class StdioClient:
    """The smallest MCP client that is still a real one.

    It speaks newline-delimited JSON-RPC 2.0 to a server subprocess over pipes
    -- the actual MCP stdio transport -- rather than calling the server object
    in-process. An in-process client would prove the handlers work and nothing
    about whether the server is reachable.
    """

    def __init__(self, command: list[str], cwd: Path | None = None):
        self.command = command
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(cwd) if cwd else None,
        )
        self._next_id = 0

    def __enter__(self) -> "StdioClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self.process.poll() is None:
            assert self.process.stdin is not None
            self.process.stdin.close()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                self.process.kill()

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        return self._send(
            {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        )

    def notify(self, method: str) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.process.stdin.flush()

    def _send(self, message: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"server closed the connection: {stderr.strip()}")
        return json.loads(line)

    # convenience wrappers

    def initialize(self) -> dict[str, Any]:
        response = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self.notify("notifications/initialized")
        return response

    def tools(self) -> list[dict[str, Any]]:
        return self.request("tools/list")["result"]["tools"]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})


def server_command(city: str | None, rig: str | None, client_class: str) -> list[str]:
    command = [sys.executable, str(MCTL), "mcp", "serve", "--client-class", client_class]
    if city:
        command += ["--city", city]
    if rig:
        command += ["--rig", rig]
    return command


def _looks_like_a_traceback(payload: object) -> bool:
    rendered = json.dumps(payload)
    return "Traceback (most recent call last)" in rendered or 'File "' in rendered


def run_checks(city: str | None, rig: str | None, expected: tuple[str, ...]) -> dict[str, Any]:
    checks: list[Check] = []
    command = server_command(city, rig, "internal")
    server_info: dict[str, Any] = {}

    with StdioClient(command) as client:
        # 1. connect
        handshake = client.initialize()["result"]
        server_info = handshake.get("serverInfo", {})
        checks.append(
            Check(
                name="connect",
                passed=(
                    server_info.get("name") == "mctl"
                    and handshake.get("capabilities", {}).get("tools") is not None
                ),
                detail=f"handshake with {server_info.get('name')} {server_info.get('version')}",
                evidence={
                    "protocolVersion": handshake.get("protocolVersion"),
                    "serverInfo": server_info,
                },
            )
        )

        # 2. tools_list
        tools = client.tools()
        names = [tool["name"] for tool in tools]
        missing = [name for name in expected if name not in names]
        checks.append(
            Check(
                name="tools_list",
                passed=not missing,
                detail=f"{len(names)} tools listed, {len(missing)} expected name(s) missing",
                evidence={"missing": missing, "tools": sorted(names)},
            )
        )

        # 3. typed_read_round_trip -- validate against the transmitted schema
        schemas = {tool["name"]: tool.get("outputSchema") for tool in tools}
        response = client.call("briefs_list", {})
        structured = response.get("result", {}).get("structuredContent")
        schema = schemas.get("briefs_list")
        failures = (
            schema_errors(structured, schema)
            if isinstance(structured, dict) and isinstance(schema, dict)
            else [{"message": "no structuredContent or no transmitted outputSchema"}]
        )
        briefs = structured.get("briefs", []) if isinstance(structured, dict) else []
        checks.append(
            Check(
                name="typed_read_round_trip",
                passed=not failures and bool(structured) and bool(briefs),
                detail="briefs_list validated against the outputSchema the server transmitted",
                evidence={
                    "artifact_trust": (structured or {}).get("artifact_trust"),
                    "brief_count": len(briefs),
                    "schema_errors": failures,
                    "schema_source": "tools/list",
                    "tool": "briefs_list",
                    "trace_id": (structured or {}).get("trace_id"),
                },
            )
        )

        # 4. typed_schema_error -- the central Slice 6 claim
        bad = client.call("briefs_show", {"brief_id": 123})
        error = bad.get("error") or {}
        data = error.get("data") or {}
        failures = data.get("schema_errors")
        typed = isinstance(failures, list) and bool(failures)
        checks.append(
            Check(
                name="typed_schema_error",
                passed=(
                    "result" not in bad
                    and error.get("code") == -32602
                    and (data.get("diagnostic") or {}).get("code") == "MCTL_MCP_INVALID_ARGUMENTS"
                    and typed
                    and not _looks_like_a_traceback(bad)
                ),
                detail="a wrongly typed argument failed as a structured schema error",
                evidence={
                    "diagnostic_code": (data.get("diagnostic") or {}).get("code"),
                    "is_prose_only": not typed,
                    "jsonrpc_error_code": error.get("code"),
                    "looks_like_a_traceback": _looks_like_a_traceback(bad),
                    "schema_errors": failures if typed else [],
                },
            )
        )

        # 5. no_passthrough_tool
        offenders = sorted(set(names) & FORBIDDEN_TOOL_NAMES)
        raw_argument_tools = sorted(
            tool["name"]
            for tool in tools
            if {"command", "argv"} & set(tool.get("inputSchema", {}).get("properties", {}))
        )
        checks.append(
            Check(
                name="no_passthrough_tool",
                passed=not offenders and not raw_argument_tools,
                detail="the surface exposes typed domain tools only",
                evidence={
                    "forbidden_names_present": offenders,
                    "tools_accepting_raw_commands": raw_argument_tools,
                },
            )
        )
        internal_tool_count = len(names)

    # 6. rollout_gate -- a second server, asked for the external surface.
    #    The gate is exercised, not bypassed: check 2 above asked for the
    #    internal surface explicitly and this asks for the external one.
    external_command = server_command(city, rig, "external")
    with StdioClient(external_command) as client:
        client.initialize()
        external_names = [tool["name"] for tool in client.tools()]
        blocked = client.call("briefs_list", {})
        blocked_error = blocked.get("error") or {}
        blocked_code = ((blocked_error.get("data") or {}).get("diagnostic") or {}).get("code")
    checks.append(
        Check(
            name="rollout_gate",
            passed=(
                internal_tool_count == len(expected)
                and external_names == []
                and blocked_code == "MCTL_MCP_TOOL_DISABLED"
            ),
            detail="external clients see no tools and cannot call one",
            evidence={
                "external_call_diagnostic": blocked_code,
                "external_tool_count": len(external_names),
                "internal_tool_count": internal_tool_count,
            },
        )
    )

    return {
        "checks": [check.to_dict() for check in checks],
        "passed": all(check.passed for check in checks),
        "server": server_info,
        "server_command": command,
        "transport": "stdio",
    }


def render(report: dict[str, Any]) -> str:
    lines = [f"mctl MCP harness -- transport {report['transport']}"]
    width = max(len(check["name"]) for check in report["checks"])
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  [{status}] {check['name']:<{width}}  {check['detail']}")
        if not check["passed"]:
            lines.append(f"         evidence: {json.dumps(check['evidence'], sort_keys=True)}")
    lines.append("PASSED" if report["passed"] else "FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mctl-mcp-harness", description=__doc__)
    parser.add_argument("--city", help="registered Gas City root passed to the server")
    parser.add_argument("--rig", help="registered rig identifier passed to the server")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    parser.add_argument(
        "--expect-tool",
        action="append",
        default=[],
        help="additional tool name the surface must expose (repeatable)",
    )
    args = parser.parse_args(argv)

    expected = EXPECTED_TOOLS + tuple(args.expect_tool)
    try:
        report = run_checks(args.city, args.rig, expected)
    except RuntimeError as error:
        report = {
            "checks": [Check("connect", False, str(error)).to_dict()],
            "passed": False,
            "server": {},
            "server_command": server_command(args.city, args.rig, "internal"),
            "transport": "stdio",
        }
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
