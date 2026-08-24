"""A debugging dashboard must have a teardown step (`#154`).

Eight `mctl dashboard serve` processes were listening at once on Taylor's
machine -- seven agent debug servers started across ten hours and never torn
down, because no teardown step existed. The adjacent hazard is the dangerous
one: with eight servers on eight ports, "the dashboard" stops being a
well-defined referent, and an agent can point a browser at a stale server still
running old code, watch a fix "work", and report success while the real
dashboard never got it.

`#207` gave every dashboard a startup STAMP and made dead stamps self-prune, so
stray and dead instances are now VISIBLE (`dashboard_status`). This adds the
missing ACTION: `dashboards.teardown` / `mctl dashboard teardown` stops live
instances (all, or one port) and removes their stamps, and reaps dead stamps in
passing -- the session-end step whose absence let the servers accrue.

`P6.2` on the mutation: a stop that does not take is reported as a failure with
its stamp left in place, never silently counted as torn down.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_core import dashboards  # noqa: E402


def _stamp(city, *, pid, port):
    dashboards.write_stamp(
        city, pid=pid, host="127.0.0.1", port=port, url=f"http://127.0.0.1:{port}",
        rig=None, serving_commit="abc1234", started_at="2026-08-24T00:00:00+00:00",
    )


def test_teardown_stops_every_live_instance_and_removes_its_stamp(tmp_path, monkeypatch):
    city = tmp_path
    _stamp(city, pid=101, port=8491)
    _stamp(city, pid=102, port=8480)
    monkeypatch.setattr(dashboards, "pid_alive", lambda pid: True)
    stopped_pids: list = []
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: stopped_pids.append(inst.pid) or True)

    report = dashboards.teardown(city)

    assert sorted(stopped_pids) == [101, 102]
    assert {r["pid"] for r in report["stopped"]} == {101, 102}
    assert report["failed"] == []
    assert list(dashboards.stamp_dir(city).glob("*.json")) == [], "stamps must be removed"


def test_teardown_with_a_port_stops_only_that_instance(tmp_path, monkeypatch):
    city = tmp_path
    _stamp(city, pid=101, port=8491)
    _stamp(city, pid=102, port=8480)
    monkeypatch.setattr(dashboards, "pid_alive", lambda pid: True)
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: True)

    report = dashboards.teardown(city, port=8491)

    assert [r["port"] for r in report["stopped"]] == [8491]
    remaining = {p.stem for p in dashboards.stamp_dir(city).glob("*.json")}
    assert remaining == {"102"}, "the untargeted instance must be left alone"


def test_teardown_reports_a_failed_stop_and_keeps_its_stamp(tmp_path, monkeypatch):
    city = tmp_path
    _stamp(city, pid=101, port=8491)
    monkeypatch.setattr(dashboards, "pid_alive", lambda pid: True)
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: False)

    report = dashboards.teardown(city)

    assert report["stopped"] == []
    assert [r["pid"] for r in report["failed"]] == [101]
    assert {p.stem for p in dashboards.stamp_dir(city).glob("*.json")} == {"101"}, (
        "a stamp whose process would not stop must remain, not read as torn down"
    )


def test_teardown_reaps_dead_stamps_in_passing(tmp_path, monkeypatch):
    """The stray/leak the issue is about: a stamp whose process is already gone
    is not a running dashboard. Teardown clears it without trying to stop it."""
    city = tmp_path
    _stamp(city, pid=9999, port=8479)  # dead
    monkeypatch.setattr(dashboards, "pid_alive", lambda pid: False)
    monkeypatch.setattr(dashboards, "stop_instance", lambda inst: (_ for _ in ()).throw(AssertionError("must not stop a dead pid")))

    report = dashboards.teardown(city)

    assert report["stopped"] == [] and report["failed"] == []
    assert list(dashboards.stamp_dir(city).glob("*.json")) == [], "dead stamp must be reaped"


def test_the_teardown_cli_verb_is_wired(tmp_path, monkeypatch):
    """`mctl dashboard teardown` must reach the teardown, not error at parse."""
    from mctl_core import cli

    calls: list = []
    monkeypatch.setattr(
        "mctl_dashboard.server.teardown_from_args",
        lambda args: calls.append(args) or 0,
    )

    rc = cli.main(["dashboard", "teardown", "--city", str(tmp_path)])

    assert rc == 0
    assert len(calls) == 1
    assert calls[0].dashboard_command == "teardown"
