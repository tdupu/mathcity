"""`city_health` (dashboard handoff #114): the three-valued data-plane probe
and the resource-pressure alarm that #70 should have had the first time.

Every test constructs the exact subprocess output being probed for and
asserts the derived state, rather than trusting the module's own summary of
itself -- a check that always finds what it expects is not a check.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import health as health_mod
from mctl_core.context import CityScope, RegisteredRig


def _scope(tmp_path: Path, *rig_names: str) -> CityScope:
    return CityScope(
        city_root=tmp_path,
        discovery_path=str(tmp_path),
        invocation_cwd=tmp_path,
        trace_id="test-trace",
        rigs=tuple(
            RegisteredRig(name=name, root=tmp_path / name, db=name) for name in rig_names
        ),
        config={},
    )


class _FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def test_data_plane_is_healthy_when_reachable_and_nothing_quarantined(tmp_path, monkeypatch):
    dolt_payload = {"server": {"reachable": True, "latency_ms": 12}, "quarantine": []}

    def fake_run(command, **kwargs):
        # #176: build_city_health now makes TWO kinds of call -- the city-level
        # `gc dolt health` probe AND a per-rig `bd list` read, because per-rig
        # state is measured rather than inherited. A mock that answers only the
        # first turns every rig `unreachable`, which is the code behaving
        # correctly against a fixture that predates it.
        if command[:1] == ["bd"]:
            return _FakeCompleted("[]")
        assert command[:3] == ["gc", "dolt", "health"]
        return _FakeCompleted(json.dumps(dolt_payload))

    monkeypatch.setattr(health_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (100, 200000, "ok"))

    report = health_mod.build_city_health(_scope(tmp_path, "hecke"))

    assert report.data_plane == health_mod.DATA_PLANE_HEALTHY
    assert report.per_rig[0].state == "healthy"
    assert report.per_rig[0].reason == ""


def test_data_plane_is_quarantined_when_a_registered_rigs_db_is_named(tmp_path, monkeypatch):
    dolt_payload = {
        "server": {"reachable": True, "latency_ms": 12},
        "quarantine": [{"db": "hecke", "reason": "post-flatten hash mismatch"}],
    }

    def fake_run(command, **kwargs):
        if command[:1] == ["bd"]:
            return _FakeCompleted("[]")   # rig answers; quarantine still wins
        return _FakeCompleted(json.dumps(dolt_payload))

    monkeypatch.setattr(health_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (100, 200000, "ok"))

    report = health_mod.build_city_health(_scope(tmp_path, "hecke", "homog"))

    assert report.data_plane == health_mod.DATA_PLANE_QUARANTINED
    by_rig = {row.rig_id: row for row in report.per_rig}
    assert by_rig["hecke"].state == "degraded"
    assert by_rig["hecke"].reason == "post-flatten hash mismatch"
    # The rig NOT named in quarantine must not inherit the other rig's state --
    # a shared "degraded" verdict here would be exactly the collapsed-reason
    # failure §5 forbids.
    assert by_rig["homog"].state == "healthy"


def test_data_plane_is_UNKNOWN_when_the_probe_times_out(tmp_path, monkeypatch):
    """#159: a `gc` timeout was being charged to Dolt.

    This test previously asserted `DATA_PLANE_UNREACHABLE` here, and its own
    comment already named the distinction it was not enforcing:

        "A timed-out probe is not the same fact as a probe that answered
         'down' -- the detail must say which one happened."

    The distinction was preserved in the probe DETAIL, where a careful reader
    finds it, and lost in the headline field that every other reader trusts.
    On 2026-08-21 that produced `data_plane: "unreachable"` while Dolt answered
    in 113ms with 18 databases, and seventeen per-rig rows corroborating it --
    which were not seventeen observations but one probe's silence, repeated.

    The sibling test below still asserts `unreachable` for a server that
    explicitly answers down. That case is a measurement and must keep the word.
    """
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr(health_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (100, 200000, "ok"))

    report = health_mod.build_city_health(_scope(tmp_path, "hecke"))

    assert report.data_plane == health_mod.DATA_PLANE_UNKNOWN
    assert report.probe_results[0].outcome == health_mod.PROBE_TIMED_OUT
    # A timed-out probe is not the same fact as a probe that answered "down" --
    # the detail must say which one happened, not just that it failed. Now the
    # data_plane field says which one happened too.
    assert "did not answer" in report.probe_results[0].detail
    # #176 SUPERSEDES #159 for this row, and the reason is worth keeping.
    #
    # #159 made per-rig `unknown` when the CITY-level probe failed, because we
    # had not asked the rig -- that was honest reporting of ignorance. #176
    # removes the ignorance: every rig is now asked directly. A rig that does
    # not answer its own probe IS unreachable, which is a measurement rather
    # than an inherited guess.
    #
    # So per-rig `unknown` no longer exists, and cannot: there is no longer a
    # path where we report on a rig without asking it. The city-level
    # `data_plane` above still needs `unknown`, because THAT probe can still
    # fail to run.
    assert report.per_rig[0].state == "unreachable"


def test_data_plane_is_unreachable_when_the_server_explicitly_answers_down(tmp_path, monkeypatch):
    dolt_payload = {"server": {"reachable": False, "latency_ms": None}, "quarantine": []}

    def fake_run(command, **kwargs):
        if command[:1] == ["bd"]:
            return _FakeCompleted("[]")   # rig answers; quarantine still wins
        return _FakeCompleted(json.dumps(dolt_payload))

    monkeypatch.setattr(health_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (100, 200000, "ok"))

    report = health_mod.build_city_health(_scope(tmp_path, "hecke"))

    assert report.data_plane == health_mod.DATA_PLANE_UNREACHABLE
    # A real "down" answer is a REFUSED outcome, distinct from a timeout --
    # this is the control proving the two failure shapes are not conflated.
    assert report.probe_results[0].outcome == health_mod.PROBE_REFUSED


def test_flood_condition_fires_when_headroom_crosses_the_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(health_mod.subprocess, "run", lambda *a, **k: _FakeCompleted(
        json.dumps({"server": {"reachable": True}, "quarantine": []})
    ))
    # Exactly at the threshold: 138240 - 133240 = 5000, the alarm boundary.
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (133240, 138240, "pid 1"))

    report = health_mod.build_city_health(_scope(tmp_path))

    assert len(report.resources.flood_conditions) == 1
    assert report.resources.flood_conditions[0].resource == "file_descriptors"
    assert report.resources.fds_trend == "unknown"


def test_flood_condition_absent_with_comfortable_headroom(tmp_path, monkeypatch):
    monkeypatch.setattr(health_mod.subprocess, "run", lambda *a, **k: _FakeCompleted(
        json.dumps({"server": {"reachable": True}, "quarantine": []})
    ))
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (1000, 200000, "pid 1"))

    report = health_mod.build_city_health(_scope(tmp_path))

    assert report.resources.flood_conditions == ()


def test_fd_probe_failure_reports_none_not_zero(tmp_path, monkeypatch):
    """A check that cannot measure fds must say so, never print 0.

    0 fds used is a real, alarming value in its own right (nothing open at
    all would itself be strange for a live supervisor); collapsing "could
    not measure" into 0 would be indistinguishable from that and is exactly
    the failure class §5 names.
    """
    monkeypatch.setattr(health_mod.subprocess, "run", lambda *a, **k: _FakeCompleted(
        json.dumps({"server": {"reachable": True}, "quarantine": []})
    ))
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (None, None, "no single supervisor process"))

    report = health_mod.build_city_health(_scope(tmp_path))

    assert report.resources.fds_used is None
    assert report.resources.fds_limit is None
    assert report.resources.flood_conditions == ()  # cannot alarm on a value we do not have
    codes = {d.code for d in report.diagnostics}
    assert "MCTL_HEALTH_FD_PROBE_FAILED" in codes


def test_disk_usage_reports_reason_when_the_dolt_directory_is_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(health_mod.subprocess, "run", lambda *a, **k: _FakeCompleted(
        json.dumps({"server": {"reachable": True}, "quarantine": []})
    ))
    monkeypatch.setattr(health_mod, "probe_supervisor_fds", lambda: (100, 200000, "ok"))

    report = health_mod.build_city_health(_scope(tmp_path, "nonexistent-rig"))

    disk = report.resources.disk_per_rig[0]
    assert disk.bytes_used is None
    assert disk.reason is not None and "does not exist" in disk.reason
