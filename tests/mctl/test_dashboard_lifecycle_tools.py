"""`#207`: the dashboard lifecycle, made visible and deliberately restartable.

The dashboard runs as a hand-launched `mctl dashboard serve` process, separate
from the `mctl mcp serve` server that answers tool calls. Its lifecycle was
invisible from the typed surface: an MCP-only Mayor could neither report which
commit a dashboard was serving (the `#210`/`#164` stamp lived only on the page)
nor restart a stale instance deliberately -- the only remedy was a human finding
the PID and re-running the command in a terminal.

Two typed tools close the gap:

- `dashboard_status` (read): every running dashboard's pid/port/city and the
  commit its code imported, plus staleness vs the checkout's current HEAD.
- `dashboard_restart` (gated mutation): dry-run by default; a live call stops a
  named instance and re-serves from current code, returning old -> new commits.
  Restart stays DELIBERATE -- never automatic -- because that inversion is
  exactly what `#164`/`#210` reject (a silent contract swap mid-session is worse
  than a visible stale one).

A serving dashboard writes a STAMP at startup naming its pid, port and the
commit `serving.SERVING_COMMIT` froze at import -- the `#210` semantic: a stale
process reports its OWN startup commit, not the checkout's current HEAD. The
stamp is the single measurable source these tools read.

`P6.2` governs every read: a stamp whose serving commit could not be captured
reports `serving_known=False`, never a placeholder a caller would later compare
against `origin/main` as if it were a revision.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mctl_core import dashboards  # noqa: E402
from test_mcp_server import call, runtime_fixture, server, tree_digest  # noqa: E402


DEAD_PID = 2_000_000_000  # far above any real pid; os.kill(pid, 0) -> no such process


def _write(city_root: Path, *, pid: int, port: int, commit: str | None, **extra) -> None:
    dashboards.write_stamp(
        city_root,
        pid=pid,
        host="127.0.0.1",
        port=port,
        url=f"http://127.0.0.1:{port}",
        rig=extra.get("rig"),
        serving_commit=commit,
        started_at="2026-08-24T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# the stamp: a running dashboard's identity, made measurable
# ---------------------------------------------------------------------------


def test_a_written_stamp_is_discovered_with_its_fields(tmp_path):
    city = tmp_path
    _write(city, pid=os.getpid(), port=8491, commit="abc1234")

    found = dashboards.discover(city)

    assert len(found) == 1
    inst = found[0]
    assert inst.pid == os.getpid()
    assert inst.port == 8491
    assert inst.serving_commit == "abc1234"
    assert inst.serving_known is True


def test_a_stamp_for_a_dead_pid_is_not_reported_and_is_pruned(tmp_path):
    """The #154 hazard one layer up: a stamp whose process is gone must not read
    as a live dashboard. A dead stamp is pruned so it cannot accrue forever."""
    city = tmp_path
    _write(city, pid=DEAD_PID, port=8480, commit="dead123")

    found = dashboards.discover(city)

    assert found == []
    assert dashboards.stamp_path(city, DEAD_PID).exists() is False, "dead stamp not pruned"


def test_an_unknown_serving_commit_is_reported_unknown_not_as_a_placeholder(tmp_path):
    """`P6.2`: a stamp whose commit could not be captured says so; it never
    substitutes a sentinel that would be compared against origin/main."""
    city = tmp_path
    _write(city, pid=os.getpid(), port=8492, commit=None)

    inst = dashboards.discover(city)[0]

    assert inst.serving_known is False
    assert inst.serving_commit is None


# ---------------------------------------------------------------------------
# dashboard_status: the read
# ---------------------------------------------------------------------------


def test_dashboard_status_reports_the_running_instances(tmp_path):
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8491, commit="abc1234")

    structured = call(server(city_root, rig_root), "dashboard_status")["result"]["structuredContent"]

    assert structured["running"] is True
    ports = [inst["port"] for inst in structured["instances"]]
    assert 8491 in ports
    assert "current_commit" in structured  # the checkout HEAD to compare against


def test_dashboard_status_with_no_dashboard_says_so_rather_than_erroring(tmp_path):
    city_root, rig_root = runtime_fixture(tmp_path)

    structured = call(server(city_root, rig_root), "dashboard_status")["result"]["structuredContent"]

    assert structured["running"] is False
    assert structured["instances"] == []


def test_dashboard_status_flags_a_stale_instance(tmp_path):
    """A dashboard serving a commit other than the checkout's current HEAD is
    stale; status must SAY so (a WARN advisory), which is the whole point --
    the operator then decides whether to dashboard_restart it."""
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8491, commit="0ldc0de")

    structured = call(server(city_root, rig_root), "dashboard_status")["result"]["structuredContent"]

    inst = next(i for i in structured["instances"] if i["port"] == 8491)
    assert inst["stale"] is True
    codes = [d["code"] for d in structured["diagnostics"]]
    assert "MDSH_STALE_INSTANCE" in codes


# ---------------------------------------------------------------------------
# dashboard_restart: the gated mutation
# ---------------------------------------------------------------------------


def test_dashboard_restart_is_dry_run_by_default_and_touches_nothing(tmp_path, monkeypatch):
    """Mutation is opt-in: omitting dry_run previews, stops and starts nothing."""
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8491, commit="0ldc0de")
    stops: list = []
    starts: list = []
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: stops.append(inst) or True)
    monkeypatch.setattr(
        dashboards, "start_instance",
        lambda **kw: starts.append(kw) or {"pid": 999, "serving_commit": "new", "started_at": "t", "url": "u"},
    )

    structured = call(
        server(city_root, rig_root), "dashboard_restart", {"port": 8491}
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert stops == [] and starts == [], "a dry run must stop and start nothing"
    assert structured["plan"]["port"] == 8491
    assert structured["plan"]["old_commit"] == "0ldc0de"


def test_dashboard_restart_applied_stops_the_old_and_serves_the_new(tmp_path, monkeypatch):
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8491, commit="0ldc0de")
    stops: list = []
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: stops.append(inst.pid) or True)
    monkeypatch.setattr(
        dashboards, "start_instance",
        lambda **kw: {"pid": 4242, "serving_commit": "newc0de", "started_at": "t", "url": f"http://127.0.0.1:{kw['port']}"},
    )

    structured = call(
        server(city_root, rig_root), "dashboard_restart", {"port": 8491, "dry_run": False}
    )["result"]["structuredContent"]

    assert structured["applied"] is True
    assert stops == [os.getpid()], "the old instance must be stopped"
    assert structured["old_pid"] == os.getpid()
    assert structured["new_pid"] == 4242
    assert structured["old_commit"] == "0ldc0de"
    assert structured["new_commit"] == "newc0de"


def test_dashboard_restart_with_no_such_instance_is_a_named_refusal(tmp_path, monkeypatch):
    city_root, rig_root = runtime_fixture(tmp_path)
    called: list = []
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: called.append(inst) or True)

    structured = call(
        server(city_root, rig_root), "dashboard_restart", {"port": 9999, "dry_run": False}
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert called == [], "nothing may be stopped when the target does not exist"
    codes = [d["code"] for d in structured["diagnostics"]]
    assert "MDSH_NO_INSTANCE" in codes


def test_dashboard_restart_reports_a_failed_stop_rather_than_claiming_success(tmp_path, monkeypatch):
    """P6.2 for the mutation: if the stop step fails, do not report a clean
    restart. The operator must see the instance may still be up."""
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8491, commit="0ldc0de")
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: False)  # could not stop
    monkeypatch.setattr(dashboards, "start_instance", lambda **kw: pytest.fail("must not start after a failed stop"))

    structured = call(
        server(city_root, rig_root), "dashboard_restart", {"port": 8491, "dry_run": False}
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    codes = [d["code"] for d in structured["diagnostics"]]
    assert "MDSH_RESTART_FAILED" in codes


# ---------------------------------------------------------------------------
# the served contract (#203-style: assert what a caller actually receives)
# ---------------------------------------------------------------------------


def _served_spec(instance, name: str) -> dict:
    response = instance.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    for tool in response["result"]["tools"]:
        if tool["name"] == name:
            return tool
    raise AssertionError(f"{name} is not served: {[t['name'] for t in response['result']['tools']]}")


def test_both_tools_are_served(tmp_path):
    inst = server(*runtime_fixture(tmp_path))
    assert _served_spec(inst, "dashboard_status")["_meta"]["mctl"]["mutating"] is False
    assert _served_spec(inst, "dashboard_restart")["_meta"]["mctl"]["mutating"] is True


def test_restart_is_dry_run_first_in_its_served_schema(tmp_path):
    spec = _served_spec(server(*runtime_fixture(tmp_path)), "dashboard_restart")
    dry_run = spec["inputSchema"]["properties"]["dry_run"]
    assert dry_run["type"] == "boolean" and dry_run["default"] is True
    assert spec["_meta"]["mctl"]["external_ready"] is False
