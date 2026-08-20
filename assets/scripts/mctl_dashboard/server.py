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
import re
import sys
from http import HTTPStatus
from typing import Any

from .app import Dashboard, Request
from .client import McpClient, StdioMcpClient
from .theme import FONT_DIR


MAX_BODY_BYTES = 256 * 1024

#: The only filenames `/fonts/` will serve. A whitelist rather than a
#: traversal check, because this is the one path whose target is chosen by the
#: URL.
_FONT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}\.woff2")


def make_handler(dashboard: Dashboard) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "mctl-dashboard"
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            if self.path.startswith("/fonts/"):
                self._serve_font(self.path[len("/fonts/") :])
                return
            self._respond(Request.from_wire("GET", self.path))

        def _serve_font(self, name: str) -> None:
            """Serve one vendored woff2, or 404.

            The name is matched against a strict pattern rather than joined and
            resolved: this is the only path in the dashboard that reads a file
            chosen by the URL, so it gets a whitelist, not a traversal check.
            Anything with a slash, a dot-segment or an unexpected extension
            fails the match and never reaches the filesystem.
            """
            if not _FONT_NAME.fullmatch(name):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            path = FONT_DIR / name
            try:
                payload = path.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "font/woff2")
            self.send_header("Content-Length", str(len(payload)))
            # Fonts are content-addressed by filename and never change in place,
            # unlike every other response this server sends.
            self.send_header("Cache-Control", "max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(payload)

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
    client: McpClient,
    *,
    host: str = "127.0.0.1",
    port: int = 8471,
    city_wide: bool = False,
    rig: str | None = None,
) -> tuple[ThreadingHTTPServer, str]:
    """Build a server and report the URL it is actually bound to.

    Returns the real port so a caller that asked for 0 can print something an
    operator can paste into a browser.
    """
    httpd = ThreadingHTTPServer(
        (host, port), make_handler(Dashboard(client, city_wide=city_wide, rig=rig))
    )
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    return httpd, f"http://{bound_host}:{bound_port}"


def serve_from_args(args: argparse.Namespace) -> int:
    """Entry point for `mctl dashboard serve`, wired from mctl_core.cli."""
    # `--rig` omitted means city-wide. The MCP server is then started without
    # a default rig, and every read either names one explicitly or opts into
    # `all_rigs` -- so a page can never silently resolve to "whichever rig the
    # server happened to be pinned to".
    city_wide = not args.rig
    client = StdioMcpClient(
        city=Path(args.city) if args.city else None,
        rig=args.rig,
    )
    httpd, url = make_server(
        client, host=args.host, port=args.port, city_wide=city_wide, rig=args.rig
    )
    print(f"mctl dashboard on {url}", file=sys.stderr)
    print(
        f"  scope: {'city-wide (every registered rig)' if city_wide else 'rig ' + args.rig}",
        file=sys.stderr,
    )
    print(f"  MCP client class: internal (all 16 tools); server: {' '.join(client.command)}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        client.close()
    return 0
