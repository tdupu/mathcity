"""`http.server` glue for the dashboard, and the `mctl dashboard serve` entry.

Standard library only, for the same reason Slice 6 declined the installed
`mcp` SDK: this repository declares no Python dependencies, so anything that
needed `pip install` or `npm install` would make the test suite depend on one
developer's machine. A threaded `http.server` serving server-rendered HTML is
enough for a single-operator local tool and adds nothing to maintain.

Bound to loopback by default and never given a listen-on-all default. The
dashboard runs as an `internal` MCP client -- it must, since the rollout gate
shows an external client zero tools -- so the surface it fronts is the full
fifteen, including the mutating four. That is safe on 127.0.0.1 behind a
preview-first confirm path, and would not be safe on a routable interface.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any

from .app import Dashboard, Request
from .client import McpClient, StdioMcpClient


MAX_BODY_BYTES = 256 * 1024


def make_handler(dashboard: Dashboard) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "mctl-dashboard"
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            self._respond(Request.from_wire("GET", self.path))

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            length = min(int(self.headers.get("Content-Length") or 0), MAX_BODY_BYTES)
            body = self.rfile.read(length).decode("utf-8") if length else ""
            self._respond(Request.from_wire("POST", self.path, body))

        def _respond(self, request: Request) -> None:
            response = dashboard.handle(request)
            payload = response.body.encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(payload)))
            # An operator page whose state is seconds old is worse than a slow
            # one: a cached brief list is a stale claim about a live queue.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("dashboard: " + (fmt % args) + "\n")

    return Handler


def make_server(
    client: McpClient, *, host: str = "127.0.0.1", port: int = 8471
) -> tuple[ThreadingHTTPServer, str]:
    """Build a server and report the URL it is actually bound to.

    Returns the real port so a caller that asked for 0 can print something an
    operator can paste into a browser.
    """
    httpd = ThreadingHTTPServer((host, port), make_handler(Dashboard(client)))
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    return httpd, f"http://{bound_host}:{bound_port}"


def serve_from_args(args: argparse.Namespace) -> int:
    """Entry point for `mctl dashboard serve`, wired from mctl_core.cli."""
    client = StdioMcpClient(
        city=Path(args.city) if args.city else None,
        rig=args.rig,
    )
    httpd, url = make_server(client, host=args.host, port=args.port)
    print(f"mctl dashboard on {url}", file=sys.stderr)
    print(f"  MCP client class: internal (all 15 tools); server: {' '.join(client.command)}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        client.close()
    return 0
