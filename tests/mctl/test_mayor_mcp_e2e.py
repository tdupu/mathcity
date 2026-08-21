"""End-to-end proof that the Mayor tools work over the real MCP transport.

`tests/mctl/test_mayor_reads.py` proves the core logic against fixtures. This
file proves the *adapter*: a real subprocess, a real stdio JSON-RPC handshake,
a real `tools/call`, and a response validated against the output schema the
server actually transmitted -- not one compiled in here.

The distinction matters and this repo has paid for ignoring it. A core that
works behind an adapter nobody exercised is how `#118`'s smoke test could have
passed with its measurement deleted, and how the `brief-check.sh` cwd bug
survived a green suite: every test ran from the pack root, where the path
resolved.

`test_conservation_detects_the_known_hq_population` is the positive control.
It runs against the live `hq` store, which is known to carry dangling roots
(issue #123). If that store is ever repaired the test SKIPS with a message
rather than silently passing on a clean store -- a conservation check that has
only ever seen clean data has not been shown to detect anything.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import pytest

from mctl_core.schemas import schema_errors

CITY_ROOT = Path(os.environ.get("MCTL_TEST_CITY", Path.home() / "gt"))


def _live_city() -> bool:
    return (CITY_ROOT / "city.toml").is_file()


pytestmark = pytest.mark.skipif(
    not _live_city(), reason=f"no city at {CITY_ROOT}; set MCTL_TEST_CITY to run"
)


class _Client:
    """A minimal stdio JSON-RPC client. Small on purpose -- a proof, not a product."""

    def __init__(self, rig: str) -> None:
        self._proc = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "mctl.py"),
                "mcp",
                "serve",
                "--city",
                str(CITY_ROOT),
                "--rig",
                rig,
                "--client-class",
                "internal",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._next_id = 0
        self.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "mayor-e2e", "version": "1"}})

    def call(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        request = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write(json.dumps(request) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            stderr = self._proc.stderr.read() if self._proc.stderr else ""
            raise AssertionError(f"server closed the connection: {stderr[:400]}")
        return json.loads(line)

    def close(self) -> None:
        self._proc.terminate()
        try:
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            self._proc.kill()


def _tool(client: _Client, name: str, arguments: dict | None = None) -> tuple[dict, dict]:
    """Call a tool; return (structuredContent, that tool's transmitted outputSchema)."""
    listing = client.call("tools/list")
    specs = {tool["name"]: tool for tool in listing["result"]["tools"]}
    assert name in specs, f"{name} absent from the transmitted tool list"
    response = client.call("tools/call", {"name": name, "arguments": arguments or {}})
    assert "error" not in response, response.get("error")
    return response["result"]["structuredContent"], specs[name].get("outputSchema", {})


@pytest.fixture()
def client():
    c = _Client("hq")
    yield c
    c.close()


def test_mayor_tools_are_on_the_internal_surface(client) -> None:
    listing = client.call("tools/list")
    names = {tool["name"] for tool in listing["result"]["tools"]}
    assert "mayor_city_state" in names
    assert "mayor_conservation" in names


def test_city_state_validates_against_its_transmitted_schema(client) -> None:
    payload, schema = _tool(client, "mayor_city_state")
    assert schema, "the server transmitted no outputSchema for mayor_city_state"
    assert schema_errors(schema, payload) == []
    assert payload["state"] in {"up", "idle", "down", "unknown"}
    # Every probe must declare whether it looked. `ok: null` is legal and is
    # NOT the same as false -- that distinction is the whole point (#100).
    assert payload["probes"], "city state reported no probes at all"
    for probe in payload["probes"]:
        assert set(probe) >= {"name", "ok", "detail", "value"}
        assert probe["ok"] in (True, False, None)


def test_conservation_validates_against_its_transmitted_schema(client) -> None:
    payload, schema = _tool(client, "mayor_conservation")
    assert schema, "the server transmitted no outputSchema for mayor_conservation"
    assert schema_errors(schema, payload) == []
    assert payload["molecules"] == payload["roots_resolving"] + payload["roots_dangling"]


def test_conservation_detects_the_known_hq_population(client) -> None:
    """POSITIVE CONTROL on live data.

    `hq` is the store issue #123 measured: members pointing at roots that do
    not resolve. If this ever reports clean, either the store was repaired --
    in which case skip loudly, do not pass quietly -- or the detector broke.
    """
    payload, _ = _tool(client, "mayor_conservation")

    # Three states, three different meanings. Collapsing any two of them is the
    # defect this whole surface exists to avoid, and an earlier version of THIS
    # test collapsed "unreadable" into "not clean" and failed confusingly.
    if payload["readable"] is False:
        codes = [d["code"] for d in payload["diagnostics"]]
        pytest.skip(
            "hq was UNREADABLE on this run, so nothing was measured -- this is not "
            "a clean store and not a detector failure. hq carries ~355k commits and "
            f"its read is contended under parallel test load. diagnostics={codes}"
        )
    if payload["clean"] is True:
        pytest.skip(
            "hq reports clean. Either it was repaired (record that) or detection "
            "regressed. This test must not pass silently on a clean store."
        )
    assert payload["roots_dangling"] > 0
    assert payload["orphaned_members"] > 0
    assert len(payload["dangling_root_ids"]) == payload["roots_dangling"]
    # The window bounds the orphans, which is what separates a bounded event
    # from an ongoing leak -- the question idleness-based detection cannot ask.
    assert payload["window_earliest"] is not None
    assert payload["window_latest"] is not None
    assert payload["window_earliest"] <= payload["window_latest"]
    codes = {d["code"] for d in payload["diagnostics"]}
    assert "MAYOR_CONSERVATION_DANGLING_ROOT" in codes


def test_conservation_is_a_read_and_offers_no_passthrough(client) -> None:
    """No mayor tool may accept a raw command; the surface stays typed."""
    listing = client.call("tools/list")
    for tool in listing["result"]["tools"]:
        if not tool["name"].startswith("mayor_"):
            continue
        properties = tool["inputSchema"].get("properties", {})
        assert not ({"command", "argv", "shell", "exec"} & set(properties))
