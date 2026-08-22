"""Slice 8 dashboard: the real transports, end to end.

The view tests drive the dashboard through an in-process MCP client so they
stay fast. That would prove the handlers work and nothing about whether an
operator can actually reach them, so this file runs the shipped path: a real
`mctl mcp serve` subprocess over stdio, behind a real `http.server` bound to
loopback, driven with `urllib`.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_dashboard.client import StdioMcpClient
from mctl_dashboard.server import make_server

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


class RunningDashboard:
    def __init__(self, tmp_path: Path):
        self.city_root, self.rig_root = runtime_fixture(tmp_path)
        self.client = StdioMcpClient(
            city=self.city_root,
            rig="mathcity",
            env={"MCTL_BEADS_FIXTURE": str(self.rig_root / ".beads" / "issues.jsonl")},
        )
        self.httpd, self.url = make_server(self.client, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def __enter__(self) -> "RunningDashboard":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=10)
        self.client.close()

    def get(self, path: str) -> tuple[int, str, str]:
        try:
            with urllib.request.urlopen(self.url + path, timeout=60) as response:
                return response.status, response.read().decode("utf-8"), response.headers["Content-Type"]
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8"), error.headers["Content-Type"]

    def post(self, path: str, **form: str) -> tuple[int, str]:
        data = urllib.parse.urlencode(form).encode("utf-8")
        request = urllib.request.Request(self.url + path, data=data, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

    def bead(self, bead_id: str) -> dict:
        path = self.rig_root / ".beads" / "issues.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        return next(row for row in rows if row["id"] == bead_id)


def test_the_dashboard_serves_the_overview_over_real_http(tmp_path: Path):
    with RunningDashboard(tmp_path) as running:
        status, html, content_type = running.get("/")

    assert status == 200
    assert content_type.startswith("text/html")
    assert "width=device-width" in html
    assert "mathcity" in html


def test_the_dashboard_speaks_stdio_to_a_real_mctl_mcp_serve_subprocess(tmp_path: Path):
    with RunningDashboard(tmp_path) as running:
        command = running.client.command
        tools = [tool["name"] for tool in running.client.list_tools()]

    assert command[1].endswith("mctl.py")
    assert command[2:4] == ["mcp", "serve"]
    assert "--client-class" in command
    assert command[command.index("--client-class") + 1] == "internal"
    # The server's full internal surface, not the dashboard's own narrower
    # `ALLOWED_TOOLS` (18): this asserts the subprocess was launched as an
    # internal client, which is what makes any tool visible at all.
    assert len(tools) == 24, "an external client would see zero tools here"  # 24 since gates_status (#119) was exposed
    assert "briefs_adjudicate" in tools


def test_an_operator_can_preview_and_apply_a_verdict_over_http(tmp_path: Path):
    with RunningDashboard(tmp_path) as running:
        status, preview_html = running.post(
            "/preview",
            operation="adjudicate",
            brief_id="mc-open",
            verdict="approve",
            reason="approved from the dashboard",
        )
        assert status == 200, preview_html
        token = re.search(r'name="token" value="([^"]+)"', preview_html).group(1)
        assert running.bead("mc-open")["status"] == "open", "preview must not mutate"

        applied_status, applied_html = running.post("/apply", token=token)

        assert applied_status == 200, applied_html
        assert running.bead("mc-open")["status"] == "closed"
        assert running.bead("mc-open")["metadata"]["verdict"] == "approve"


def test_an_unknown_path_is_a_typed_404_not_a_stack_trace(tmp_path: Path):
    with RunningDashboard(tmp_path) as running:
        status, body, _ = running.get("/etc/passwd")

    assert status == 404
    assert "Traceback" not in body
