"""MCP clients for the dashboard. Two transports, one allowlist.

The dashboard never calls `mctl_core` directly. Slice 8 step 2 makes that
binding -- "build the dashboard against MCP tools from Slice 6, not against ad
hoc shell commands" -- and it is the reason the dashboard cannot drift from
CLI semantics: there is exactly one place domain behavior lives, and this is a
client of it.

`ALLOWED_TOOLS` is spelled out rather than derived from the server's registry.
Deriving it would make the dashboard call whatever the server happened to
expose next, including something shell-shaped; naming them makes the
constraint reviewable, and `test_dashboard_views.py` cross-checks the list
against `mcp_server.TOOLS_BY_NAME` and `FORBIDDEN_TOOL_NAMES` so it cannot rot
into a lie.

That it is a *subset* is the point, and the subset is proper. The counts are
deliberately NOT written here as prose any more: this paragraph claimed
"eighteen tools and the dashboard may call sixteen" long after the server had
grown to twenty-four, and a stale count in a docstring is the same defect this
codebase keeps finding in its own checks -- a statement that reads as verified
and is not. `test_dashboard_views.py` cross-checks the membership against
`mcp_server.TOOLS_BY_NAME`, which is the assertion that cannot rot.
`work_claim` and `work_dispatch_event` serve the path-B commission flow in
`skills/work/SKILL.md`, which has no dashboard surface, so adding them here
would widen the boundary for nothing.

A city-wide page is still ONE call: `mctl_core/city.py` does the cross-rig
fan-out behind the declared `all_rigs` option, so the dashboard asks for a
city the same way it asks for a rig. It is not this layer's job to know that
sixteen bead stores were read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading
from typing import Any, Mapping, Protocol


SCRIPTS_ROOT = Path(__file__).resolve().parent.parent
MCTL = SCRIPTS_ROOT / "mctl.py"

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "mctl-dashboard", "version": "0.8.0"}

#: The typed domain tools the dashboard may call. Nothing else is.
#: Every tool the server registers must appear here or in DELIBERATELY_UNREACHABLE
#: below -- see tests/mctl/test_dashboard_tool_reachability.py for why.
ALLOWED_TOOLS = frozenset(
    {
        "orders_status",
        "formulas_catalog",
        "queue_status",
        "commission_brief",
        "context_resolve",
        "context_rigs",
        "fleet_sessions",
        "city_health",
        "gates_status",
        "blast_radius_registry",
        "molecules_list",
        "molecules_show",
        "briefs_list",
        "briefs_show",
        "briefs_options",
        "briefs_doctor",
        "briefs_validate",
        "briefs_adjudicate",
        "briefs_defer",
        "briefs_create",
    "briefs_present",
        "work_ready",
        "work_status",
        "work_provenance",
        "work_dispatch",
        "trace_show",
        "trace_replay_preview",
    }
)

#: The dashboard runs as an `internal` client. The rollout gate (plan §8)
#: defaults external clients to zero tools, and even armed leaves mutating
#: tools closed -- so an `external` dashboard could not show a brief, let
#: alone adjudicate one. It is safe here because the dashboard *is* mctl's own
#: front end: it spawns its own server subprocess and binds to loopback.
CLIENT_CLASS = "internal"


class UnknownToolError(Exception):
    """Raised when anything asks for a tool outside the typed surface."""


class ToolFailure(Exception):
    """A tool call the server answered with a typed error."""

    def __init__(self, tool: str, diagnostics: list[dict], payload: Mapping[str, Any]):
        codes = ", ".join(str(diagnostic.get("code")) for diagnostic in diagnostics) or "unknown"
        super().__init__(f"{tool} failed: {codes}")
        self.tool = tool
        self.diagnostics = diagnostics
        self.payload = dict(payload)


@dataclass(frozen=True)
class ToolResponse:
    tool: str
    payload: dict[str, Any]

    @property
    def diagnostics(self) -> list[dict]:
        return list(self.payload.get("diagnostics") or [])

    @property
    def untrusted_diagnostics(self) -> list[dict]:
        return list(self.payload.get("untrusted_diagnostics") or [])

    @property
    def artifact_trust(self) -> dict | None:
        trust = self.payload.get("artifact_trust")
        return dict(trust) if isinstance(trust, Mapping) else None

    @property
    def trace_id(self) -> str:
        return str(self.payload.get("trace_id") or "")


class McpClient(Protocol):
    def list_tools(self) -> list[dict]: ...

    def call(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolResponse: ...


class _JsonRpcClient:
    """Shared JSON-RPC plumbing: the allowlist gate and the result envelope."""

    def __init__(self) -> None:
        self._next_id = 0
        self._initialized = False
        # One pipe, one request at a time. `ThreadingHTTPServer` already
        # serves requests concurrently, and a city-wide page fans out on top
        # of that, so interleaved writes are reachable rather than theoretical
        # -- and two half-written JSON-RPC frames on one stdin is a corrupt
        # session, not a slow one.
        self._lock = threading.RLock()

    # -- transport hook --

    def _exchange(self, message: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    def _request(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            self._next_id += 1
            response = self._exchange(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id,
                    "method": method,
                    "params": dict(params or {}),
                }
            )
        if response is None:  # pragma: no cover - defensive
            raise ToolFailure(method, [], {})
        return response

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO},
        )

    # -- surface --

    def list_tools(self) -> list[dict]:
        self._ensure_initialized()
        return list(self._request("tools/list").get("result", {}).get("tools", []))

    def call(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolResponse:
        if name not in ALLOWED_TOOLS:
            # Refused before it reaches the wire. The server would refuse it
            # too, but a dashboard that *asks* for a passthrough tool has
            # already lost the argument.
            raise UnknownToolError(f"{name!r} is not one of the typed mctl tools")
        self._ensure_initialized()
        started = time.perf_counter()
        response = self._request("tools/call", {"name": name, "arguments": dict(arguments or {})})
        if os.environ.get("MCTL_TIME_CALLS"):
            # Per-call attribution, off by default. Page latency here is
            # dominated by a small number of core reads, and without this the
            # only available measurement is the total -- which tells you the
            # page is slow but not which read to overlap or cache.
            elapsed_ms = (time.perf_counter() - started) * 1000
            print(f"[timing] {name} {elapsed_ms:.0f}ms {dict(arguments or {})}",
                  file=sys.stderr, flush=True)
        if "error" in response:
            data = response["error"].get("data") or {}
            diagnostic = data.get("diagnostic")
            raise ToolFailure(name, [diagnostic] if diagnostic else [], data)
        result = response.get("result") or {}
        payload = result.get("structuredContent")
        if not isinstance(payload, Mapping):  # pragma: no cover - defensive
            raise ToolFailure(name, [], {})
        if result.get("isError"):
            raise ToolFailure(name, list(payload.get("diagnostics") or []), payload)
        return ToolResponse(tool=name, payload=dict(payload))


class InProcessMcpClient(_JsonRpcClient):
    """Speaks JSON-RPC to a server object in this process.

    Same messages, same handlers, no subprocess. Used by the view tests, where
    spawning a python interpreter per assertion would buy nothing;
    `test_dashboard_transport.py` covers the shipped stdio path.
    """

    def __init__(self, *, city: Path, rig: str | None = None, env: Mapping[str, str] | None = None):
        super().__init__()
        from mctl_core.mcp_server import MctlMcpServer

        # Kept so `clone()` can build a sibling with the same binding.
        self.city = Path(city)
        self.rig = rig
        self.env = dict(env or {})
        self.server = MctlMcpServer(
            default_city=Path(city),
            default_rig=rig,
            client_class=CLIENT_CLASS,
            env=dict(env or {}),
        )

    def _exchange(self, message: dict[str, Any]) -> dict[str, Any] | None:
        return self.server.handle(message)

    def clone(self) -> "InProcessMcpClient":
        """A sibling for concurrent reads (see `fanout`)."""
        return InProcessMcpClient(city=self.city, rig=self.rig, env=dict(self.env or {}))

    def close(self) -> None:
        return None


@dataclass
class StdioMcpClient(_JsonRpcClient):
    """Speaks the real MCP stdio transport to a real `mctl mcp serve` process.

    The only subprocess in this package, and its argv is fixed: no operator
    input reaches it, there is no shell, and the command is asserted by
    `test_dashboard_transport.py`.
    """

    city: Path | None = None
    rig: str | None = None
    env: Mapping[str, str] | None = None
    command: list[str] = field(default_factory=list)

    def clone(self) -> "StdioMcpClient":
        """A sibling connection, so independent reads can overlap.

        One stdio pipe cannot carry two conversations, so concurrency here
        means another process. They are created lazily and only up to
        `fanout.MAX_SIBLINGS`.
        """
        return StdioMcpClient(city=self.city, rig=self.rig, env=dict(self.env or {}))

    def __post_init__(self) -> None:
        super().__init__()
        self.command = [
            sys.executable,
            str(MCTL),
            "mcp",
            "serve",
            "--client-class",
            CLIENT_CLASS,
        ]
        if self.city:
            self.command += ["--city", str(self.city)]
        if self.rig:
            self.command += ["--rig", str(self.rig)]
        environment = os.environ.copy()
        environment.update({key: str(value) for key, value in dict(self.env or {}).items()})
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=environment,
        )

    def _server_gone(self, message: dict[str, Any], **facts: Any) -> ToolFailure:
        """The one diagnostic for "the subprocess is not there any more".

        Built here rather than inline because it has to be raised from two
        places that used to behave differently: the graceful death, where the
        child closed stdout and `readline()` returns empty, and the abrupt one,
        where the child is already gone and the *write* fails first.

        `#166`: only the graceful path was handled. A dashboard whose child had
        already died surfaced a raw `BrokenPipeError` on every route for an
        hour -- while the sentence the operator needed sat a few lines below,
        unreachable.
        """
        return ToolFailure(
            str(message.get("method")),
            [
                {
                    "severity": "FATAL",
                    "code": "MCTL_DASH_SERVER_GONE",
                    "message": "The mctl MCP server closed the connection.",
                    "hint": "Restart the dashboard; the server subprocess is no longer running.",
                    "facts": facts,
                }
            ],
            {},
        )

    def _exchange(self, message: dict[str, Any]) -> dict[str, Any] | None:
        assert self.process.stdin is not None
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, ValueError) as error:
            # The child died before this write. `poll()` carries its exit code,
            # which is the only evidence of WHY -- the live incident lost it
            # entirely and we still do not know what killed that process.
            # `ValueError` covers a closed pipe object, which presents the same
            # way to a caller.
            raise self._server_gone(
                message,
                exit_code=self.process.poll(),
                write_error=f"{type(error).__name__}: {error}",
            ) from None
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise self._server_gone(
                message, stderr=stderr.strip(), exit_code=self.process.poll()
            )
        return json.loads(line)

    def close(self) -> None:
        if self.process.poll() is None:
            assert self.process.stdin is not None
            self.process.stdin.close()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                self.process.kill()

