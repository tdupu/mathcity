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
import os
from pathlib import Path
import re
import sys
import threading
import time
from http import HTTPStatus
from typing import Any

from .app import Dashboard, Request
from .client import McpClient, StdioMcpClient
from .theme import FONT_DIR


MAX_BODY_BYTES = 256 * 1024

#: The page the /restart button lands on while the process re-execs. It refreshes
#: itself, so once the re-exec'd server rebinds the port the operator's browser
#: reconnects to the fresh page without another click.
_RESTART_PAGE = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<meta http-equiv=\"refresh\" content=\"2\"><title>Restarting…</title></head>"
    "<body style=\"font-family: Georgia, serif; padding: 2rem; color: #2d2b2b;\">"
    "<h1 style=\"font-size: 1.05rem;\">Restarting the dashboard…</h1>"
    "<p>The server is re-execing to pick up the current checkout. "
    "This page reconnects in a moment.</p></body></html>"
)

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
            if self.path == "/restart":
                self._restart()
                return
            self._respond(Request.from_wire("POST", self.path, body))

        def _restart(self) -> None:
            """Re-exec this serving process so it picks up the current checkout.

            The dashboard imports its code at process start, so a merge is
            invisible until it restarts (#210). This is a server-LIFECYCLE action,
            not a brief write, so it lives in the wrapper rather than in the pure
            `Dashboard.handle` -- `MUTATION_ROUTES` stays exactly ("/preview",
            "/apply"). Respond first, then replace the process image: the listening
            socket is close-on-exec (PEP 446), so the port frees on exec and the
            re-exec'd `mctl dashboard serve` (same argv) binds it fresh. Loopback
            only, so a lifecycle endpoint here is safe.
            """
            payload = _RESTART_PAGE.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()

            def _reexec() -> None:
                time.sleep(0.4)  # let the response finish flushing to the client
                os.execv(sys.executable, [sys.executable, *sys.argv])

            threading.Thread(target=_reexec, daemon=True).start()

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
    dashboard: str = "both",
) -> tuple[ThreadingHTTPServer, str]:
    """Build a server and report the URL it is actually bound to.

    Returns the real port so a caller that asked for 0 can print something an
    operator can paste into a browser.
    """
    httpd = ThreadingHTTPServer(
        (host, port),
        make_handler(Dashboard(client, city_wide=city_wide, rig=rig, dashboard=dashboard)),
    )
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    return httpd, f"http://{bound_host}:{bound_port}"


def teardown_from_args(args: argparse.Namespace) -> int:
    """`mctl dashboard teardown`: the session-end step `#154` was missing.

    Stops live dashboards for this city (all, or the one on `--port`) and clears
    their stamps, reaping dead stamps in passing. Returns non-zero if any stop
    failed, so a caller (or a session-end hook) can tell a clean teardown from
    one that left a process it could not kill.
    """
    from mctl_core import dashboards as _dashboards

    city = Path(args.city) if args.city else Path.cwd()
    report = _dashboards.teardown(city, port=getattr(args, "port", None))
    for entry in report["stopped"]:
        print(f"stopped dashboard pid {entry['pid']} on port {entry['port']}", file=sys.stderr)
    for entry in report["failed"]:
        print(
            f"FAILED to stop dashboard pid {entry['pid']} on port {entry['port']} -- "
            "it may still be running; check by hand (ps/kill)",
            file=sys.stderr,
        )
    if not report["stopped"] and not report["failed"]:
        print("no running dashboards to tear down for this city", file=sys.stderr)
    return 0 if not report["failed"] else 1


def internal_tool_count() -> int:
    """How many tools an `internal` MCP client sees, read from the LIVE roster.

    `#162`: the banner below hard-coded `16` and printed it on every dashboard
    start, long after the surface had grown -- a stale count reinforced dozens
    of times a night (see `#154`). Deriving it from `mcp_server.TOOLS` means it
    can never disagree with the roster it describes (CT13.3's own pass
    condition: defer to a live enumeration, never name one).
    """
    from mctl_core import mcp_server

    return len(mcp_server.TOOLS)


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
    dashboard = getattr(args, "dashboard", "both") or "both"
    httpd, url = make_server(
        client,
        host=args.host,
        port=args.port,
        city_wide=city_wide,
        rig=args.rig,
        dashboard=dashboard,
    )
    print(f"mctl dashboard on {url}", file=sys.stderr)
    print(
        f"  scope: {'city-wide (every registered rig)' if city_wide else 'rig ' + args.rig}",
        file=sys.stderr,
    )
    print(f"  dashboard: {dashboard}", file=sys.stderr)
    if dashboard == "city":
        # Binding is not rendering (mc-wbwel). Say so where the operator looks.
        print(
            "  WARNING: /city and /orders are measured at ~112s with no response. "
            "This process is serving; those two screens are not. See mc-wbwel.",
            file=sys.stderr,
        )
    print(
        f"  MCP client class: internal (all {internal_tool_count()} tools); "
        f"server: {' '.join(client.command)}",
        file=sys.stderr,
    )

    # #207: stamp this process so dashboard_status/dashboard_restart can see it.
    # Best-effort and never fatal to serving: the stamp names pid, the bound
    # port, and the commit THIS process imported (serving.SERVING_COMMIT,
    # captured once at import -- the #210 semantic). Removed on shutdown so a
    # dead stamp cannot masquerade as a live dashboard (#154).
    from pathlib import Path as _Path
    from mctl_core import dashboards as _dashboards, serving as _serving

    bound_port = httpd.server_address[1]
    stamp_city = _Path(args.city) if args.city else _Path.cwd()
    try:
        _dashboards.write_stamp(
            stamp_city,
            pid=os.getpid(),
            host=args.host,
            port=bound_port,
            url=url,
            rig=args.rig,
            serving_commit=_serving.SERVING_COMMIT,
            started_at=_serving.SERVER_STARTED_AT,
            dashboard=dashboard,
        )
    except OSError:
        pass  # a dashboard that cannot stamp itself still serves
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _dashboards.remove_stamp(stamp_city, os.getpid())
        httpd.server_close()
        client.close()
    return 0
