"""`mc-lj0sh`: the two lifecycle verbs `#207` left on the CLI, made typed.

`#207` delivered `dashboard_status` (observe) and `dashboard_restart` (rebind)
and left **start** and **stop** reachable only from `mctl dashboard serve` /
`mctl dashboard teardown`. An MCP-only Mayor asked to launch a dashboard from a
cold start (Taylor, 2026-08-26) could neither bring one up nor take one down --
the request simply stopped. `dashboard_restart` cannot substitute: it stops a
*named, stamped* instance, and from a cold start there is nothing to name.

This closes the surface to all four verbs:

- `dashboard_serve` (gated create): dry-run by default; refuses a double-bind
  when a dashboard is already stamped on the port (`MDSH_PORT_IN_USE`),
  symmetric with restart's `MDSH_NO_INSTANCE`. The `#164`/`#210` safety that
  gates restart does NOT apply -- starting where none runs swaps no contract.
- `dashboard_teardown` (gated destroy): dry-run by default; a live call stops
  the instances `#154`'s CLI teardown would, and a stop that does not take is
  `MDSH_TEARDOWN_FAILED` with its stamp left in place (`P6.2`).

`confirm_started` is the fail-loud/deadline seam under `dashboard_serve`:
`start_instance` returns a bare pid before the child has bound anything, so the
result is proven against the stamp the child writes only after it binds --
`confirmed`, `died` (a real failure, `P6.1`), or `still_starting` (a distinct
non-failure state carrying elapsed, `P6.3` -- never a failed start).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mctl_core import dashboards  # noqa: E402
from test_mcp_server import call, runtime_fixture, server  # noqa: E402


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
        started_at="2026-08-27T00:00:00+00:00",
    )


def _structured(city_root, rig_root, name, args=None):
    return call(server(city_root, rig_root), name, args or {})["result"]["structuredContent"]


# ---------------------------------------------------------------------------
# confirm_started: a bare pid turned into three-valued evidence
# ---------------------------------------------------------------------------


def test_confirm_started_reports_confirmed_once_a_stamp_appears(tmp_path):
    """A stamp is written only AFTER the child binds its port, so its presence
    is proof the start took."""
    city = tmp_path
    _write(city, pid=os.getpid(), port=8471, commit="abc1234")  # our own pid, alive

    outcome = dashboards.confirm_started(city, pid=os.getpid())

    assert outcome["state"] == "confirmed"
    assert outcome["elapsed"] >= 0.0


def test_confirm_started_reports_died_when_the_child_exits_before_stamping(tmp_path):
    """`P6.1`: a child that exits before it stamps did not bind the port. That is
    a real failure, named -- never reported as a start that took."""
    city = tmp_path  # no stamp written; DEAD_PID is not alive

    outcome = dashboards.confirm_started(city, pid=DEAD_PID, timeout=1.0)

    assert outcome["state"] == "died"


def test_confirm_started_reports_still_starting_at_the_deadline_not_failed(tmp_path):
    """`P6.3`: a live process that has not stamped by the deadline is
    `still_starting` with elapsed -- the caller stopped waiting; the child did
    not fail. It must never collapse into `died`/`failed`."""
    city = tmp_path  # our pid is alive but never stamps within the window

    started = time.monotonic()
    outcome = dashboards.confirm_started(city, pid=os.getpid(), timeout=0.2, warn=0.05)
    elapsed = time.monotonic() - started

    assert outcome["state"] == "still_starting"
    assert outcome["slow"] is True  # the warn threshold fired below the deadline
    assert outcome["elapsed"] >= 0.2
    assert elapsed < 2.0  # it returned promptly at the deadline, did not hang


# ---------------------------------------------------------------------------
# dashboard_serve: the create verb
# ---------------------------------------------------------------------------


def test_dashboard_serve_is_dry_run_by_default_and_starts_nothing(tmp_path, monkeypatch):
    city_root, rig_root = runtime_fixture(tmp_path)
    starts: list = []
    monkeypatch.setattr(dashboards, "start_instance", lambda **kw: starts.append(kw) or {})

    structured = _structured(city_root, rig_root, "dashboard_serve", {"port": 8471})

    assert structured["applied"] is False
    assert starts == [], "a dry run must start nothing"
    assert structured["plan"]["port"] == 8471


def test_dashboard_serve_refuses_a_double_bind_on_an_occupied_port(tmp_path, monkeypatch):
    """Symmetric with restart's MDSH_NO_INSTANCE: a start onto a port that
    already has a stamped dashboard is refused, never a silent double-bind."""
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8471, commit="abc1234")
    monkeypatch.setattr(
        dashboards, "start_instance", lambda **kw: (_ for _ in ()).throw(AssertionError("must not start"))
    )

    structured = _structured(city_root, rig_root, "dashboard_serve", {"port": 8471, "dry_run": False})

    assert structured["applied"] is False
    codes = [d["code"] for d in structured["diagnostics"]]
    assert "MDSH_PORT_IN_USE" in codes


def test_dashboard_serve_applied_starts_and_confirms_the_instance(tmp_path, monkeypatch):
    city_root, rig_root = runtime_fixture(tmp_path)
    monkeypatch.setattr(
        dashboards, "start_instance",
        lambda **kw: {"pid": 4242, "serving_commit": "newc0de", "started_at": "t", "url": f"http://127.0.0.1:{kw['port']}"},
    )
    monkeypatch.setattr(
        dashboards, "confirm_started", lambda city_root, **kw: {"state": "confirmed", "elapsed": 0.1, "slow": False}
    )

    structured = _structured(city_root, rig_root, "dashboard_serve", {"port": 8471, "dry_run": False})

    assert structured["applied"] is True
    assert structured["confirmed"] is True
    assert structured["pid"] == 4242
    assert structured["serving_commit"] == "newc0de"


def test_dashboard_serve_reports_a_child_that_died_before_binding(tmp_path, monkeypatch):
    """`P6.1`: a started child that exits before it stamps is a real failure --
    MDSH_SERVE_FAILED, applied=false -- not a start silently reported clean."""
    city_root, rig_root = runtime_fixture(tmp_path)
    monkeypatch.setattr(
        dashboards, "start_instance",
        lambda **kw: {"pid": 4242, "serving_commit": "newc0de", "started_at": "t", "url": "u"},
    )
    monkeypatch.setattr(
        dashboards, "confirm_started", lambda city_root, **kw: {"state": "died", "elapsed": 0.3, "slow": False}
    )

    structured = _structured(city_root, rig_root, "dashboard_serve", {"port": 8471, "dry_run": False})

    assert structured["applied"] is False
    codes = [d["code"] for d in structured["diagnostics"]]
    assert "MDSH_SERVE_FAILED" in codes


def test_dashboard_serve_still_starting_is_a_warn_not_a_failure(tmp_path, monkeypatch):
    """`P6.3`: a start still coming up at the deadline is applied=true with a
    WARN naming elapsed and a distinct `still_starting` state -- never failed."""
    city_root, rig_root = runtime_fixture(tmp_path)
    monkeypatch.setattr(
        dashboards, "start_instance",
        lambda **kw: {"pid": 4242, "serving_commit": "newc0de", "started_at": "t", "url": "u"},
    )
    monkeypatch.setattr(
        dashboards, "confirm_started", lambda city_root, **kw: {"state": "still_starting", "elapsed": 5.0, "slow": True}
    )

    structured = _structured(city_root, rig_root, "dashboard_serve", {"port": 8471, "dry_run": False})

    assert structured["applied"] is True
    assert structured["confirmed"] is False
    assert structured["state"] == "still_starting"
    diags = structured["diagnostics"]
    assert any(d["code"] == "MDSH_SERVE_STILL_STARTING" for d in diags)
    assert all(d["severity"] != "FATAL" for d in diags)


# ---------------------------------------------------------------------------
# dashboard_teardown: the destroy verb
# ---------------------------------------------------------------------------


def test_dashboard_teardown_is_dry_run_by_default_and_stops_nothing(tmp_path, monkeypatch):
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8471, commit="abc1234")
    monkeypatch.setattr(
        dashboards, "teardown", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not tear down"))
    )

    structured = _structured(city_root, rig_root, "dashboard_teardown")

    assert structured["applied"] is False
    would = [inst["port"] for inst in structured["plan"]["would_stop"]]
    assert 8471 in would


def test_dashboard_teardown_applied_stops_the_instances(tmp_path, monkeypatch):
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8471, commit="abc1234")
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: True)

    structured = _structured(city_root, rig_root, "dashboard_teardown", {"dry_run": False})

    assert structured["applied"] is True
    stopped_ports = [entry["port"] for entry in structured["stopped"]]
    assert 8471 in stopped_ports
    assert structured["failed"] == []
    assert dashboards.stamp_path(city_root, os.getpid()).exists() is False


def test_dashboard_teardown_reports_a_stop_that_did_not_take(tmp_path, monkeypatch):
    """`P6.2`: a stop that fails leaves its stamp in place and is reported
    MDSH_TEARDOWN_FAILED -- a torn-down count never includes a live process."""
    city_root, rig_root = runtime_fixture(tmp_path)
    _write(city_root, pid=os.getpid(), port=8471, commit="abc1234")
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: False)  # could not stop

    structured = _structured(city_root, rig_root, "dashboard_teardown", {"dry_run": False})

    assert structured["applied"] is True
    codes = [d["code"] for d in structured["diagnostics"]]
    assert "MDSH_TEARDOWN_FAILED" in codes
    assert structured["stopped"] == []
    failed_ports = [entry["port"] for entry in structured["failed"]]
    assert 8471 in failed_ports
    assert dashboards.stamp_path(city_root, os.getpid()).exists() is True, "a failed stop must leave its stamp"


# ---------------------------------------------------------------------------
# the served contract: all four verbs typed, start/teardown gated correctly
# ---------------------------------------------------------------------------


def _served_spec(instance, name: str) -> dict:
    response = instance.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    for tool in response["result"]["tools"]:
        if tool["name"] == name:
            return tool
    raise AssertionError(f"{name} is not served: {[t['name'] for t in response['result']['tools']]}")


def test_all_four_lifecycle_verbs_are_served(tmp_path):
    inst = server(*runtime_fixture(tmp_path))
    for name in ("dashboard_status", "dashboard_restart", "dashboard_serve", "dashboard_teardown"):
        _served_spec(inst, name)  # raises if absent


def test_serve_and_teardown_are_mutating_and_dry_run_first(tmp_path):
    inst = server(*runtime_fixture(tmp_path))
    for name in ("dashboard_serve", "dashboard_teardown"):
        spec = _served_spec(inst, name)
        assert spec["_meta"]["mctl"]["mutating"] is True, name
        assert spec["_meta"]["mctl"]["external_ready"] is False, name
        dry_run = spec["inputSchema"]["properties"]["dry_run"]
        assert dry_run["type"] == "boolean" and dry_run["default"] is True, name
