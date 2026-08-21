"""`fleet_sessions` (dashboard handoff #112): occupied AND empty slots as one
list, and the honest `limit_state` gap.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import fleet as fleet_mod
from mctl_core.context import CityScope


def _scope(tmp_path: Path) -> CityScope:
    return CityScope(
        city_root=tmp_path,
        discovery_path=str(tmp_path),
        invocation_cwd=tmp_path,
        trace_id="test-trace",
        rigs=(),
        config={},
    )


class _FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def _mock_gc(monkeypatch, *, status_agents, sessions):
    def fake_run(command, **kwargs):
        if command[:2] == ["gc", "status"]:
            return _FakeCompleted(json.dumps({"agents": status_agents}))
        if command[:3] == ["gc", "session", "list"]:
            return _FakeCompleted(json.dumps({"sessions": sessions}))
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(fleet_mod.subprocess, "run", fake_run)


def test_a_configured_slot_with_no_matching_session_is_an_empty_row(tmp_path, monkeypatch):
    _mock_gc(
        monkeypatch,
        status_agents=[{"qualified_name": "bd.dog-2", "scope": "city", "running": False}],
        sessions=[],
    )

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert len(report.slots) == 1
    slot = report.slots[0]
    assert slot.qualified_name == "bd.dog-2"
    assert slot.occupied is False
    assert slot.holds is None
    assert slot.idle_reason == "slot is empty"


def test_an_occupied_slot_carries_the_sessions_own_detail(tmp_path, monkeypatch):
    _mock_gc(
        monkeypatch,
        status_agents=[{"qualified_name": "bd.dog-1", "scope": "city", "running": True}],
        sessions=[
            {
                "id": "gt-abc123",
                "agent_name": "bd.dog-1",
                "template": "bd.dog",
                "state": "active",
                "last_active": "0001-01-01T00:00:00Z",
            }
        ],
    )

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert len(report.slots) == 1
    slot = report.slots[0]
    assert slot.occupied is True
    assert slot.holds == "gt-abc123"
    assert slot.state == "active"
    assert slot.template == "bd.dog"


def test_rig_scoped_agent_joins_on_rig_slash_agent_name(tmp_path, monkeypatch):
    _mock_gc(
        monkeypatch,
        status_agents=[
            {"qualified_name": "hecke/core.control-dispatcher", "scope": "rig", "running": True}
        ],
        sessions=[
            {
                "id": "gt-xyz789",
                "agent_name": "core.control-dispatcher",
                "rig": "hecke",
                "template": "core.control-dispatcher",
                "state": "asleep",
                "last_active": "0001-01-01T00:00:00Z",
            }
        ],
    )

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert len(report.slots) == 1
    assert report.slots[0].occupied is True
    assert report.slots[0].holds == "gt-xyz789"


def test_a_session_with_no_matching_configured_slot_still_renders(tmp_path, monkeypatch):
    """A session `gc status` does not know about is not nothing -- dropping
    it would silently shrink the roster below the number of real sessions.
    """
    _mock_gc(
        monkeypatch,
        status_agents=[],
        sessions=[
            {
                "id": "gt-orphan1",
                "agent_name": "mystery.agent",
                "template": "mystery",
                "state": "active",
                "last_active": "0001-01-01T00:00:00Z",
            }
        ],
    )

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert len(report.slots) == 1
    assert report.slots[0].occupied is True
    assert report.slots[0].qualified_name == "mystery.agent"


def test_never_active_sentinel_is_not_treated_as_a_real_timestamp(tmp_path, monkeypatch):
    """Go's zero-value time (never active) must not compute as ~2000 years idle."""
    _mock_gc(
        monkeypatch,
        status_agents=[{"qualified_name": "bd.dog-1", "scope": "city", "running": True}],
        sessions=[
            {
                "id": "gt-abc123",
                "agent_name": "bd.dog-1",
                "template": "bd.dog",
                "state": "start-pending",
                "last_active": "0001-01-01T00:00:00Z",
            }
        ],
    )

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert report.slots[0].idle_for_seconds is None
    assert report.slots[0].idle_reason == "never active"


def test_limit_state_is_always_unknown_and_the_gap_is_diagnosed(tmp_path, monkeypatch):
    """No quota/usage-window recording exists yet (handoff §4.5) -- asserting
    'unknown' pins the gap so a future recording landing must change this
    test, not silently leave it green while quietly still guessing.
    """
    _mock_gc(
        monkeypatch,
        status_agents=[{"qualified_name": "bd.dog-1", "scope": "city", "running": True}],
        sessions=[
            {
                "id": "gt-abc123",
                "agent_name": "bd.dog-1",
                "template": "bd.dog",
                "state": "active",
                "last_active": "0001-01-01T00:00:00Z",
            }
        ],
    )

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert all(slot.limit_state == "unknown" for slot in report.slots)
    codes = {d.code for d in report.diagnostics}
    assert "MCTL_FLEET_LIMIT_STATE_UNRECORDED" in codes


def test_status_probe_failure_is_a_diagnostic_not_a_silent_empty_roster(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        if command[:2] == ["gc", "status"]:
            return _FakeCompleted("not json at all", returncode=1)
        return _FakeCompleted(json.dumps({"sessions": []}))

    monkeypatch.setattr(fleet_mod.subprocess, "run", fake_run)

    report = fleet_mod.build_fleet_sessions(_scope(tmp_path))

    assert report.slots == ()
    codes = {d.code for d in report.diagnostics}
    assert "MCTL_FLEET_STATUS_PROBE_FAILED" in codes
