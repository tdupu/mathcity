"""Failing tests first: the control-plane probe must be CITY-scoped.

Regression for a live finding (2026-08-19): `gc stop` stops this city's
controller but leaves the machine-wide supervisor daemon running, so
`gc supervisor status` exits 0 and the gate never fired. An armed dispatch
ran a real `gc sling` into a stopped city and stranded a convoy.
"""
from __future__ import annotations
import json, os, sys, textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core import liveness


def _fake_gc(tmp_path: Path, payload: dict | None, *, exit_code: int = 0) -> None:
    """Put a `gc` on PATH that answers `status --city ... --json` from a fixture."""
    body = "" if payload is None else json.dumps(payload)
    shim = tmp_path / "gc"
    shim.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env python3
        import sys
        sys.stdout.write({body!r})
        sys.exit({exit_code})
        """), encoding="utf-8")
    shim.chmod(0o755)
    os.environ["PATH"] = f"{tmp_path}{os.pathsep}{os.environ['PATH']}"


def test_stopped_city_controller_is_not_active(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", os.environ["PATH"])
    _fake_gc(tmp_path, {"controller": {"running": False, "mode": "supervisor",
                                       "status": "stopped"}, "suspended": False})
    assert liveness.probe_control_plane(city_root=tmp_path) is False


def test_running_city_controller_is_active(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", os.environ["PATH"])
    _fake_gc(tmp_path, {"controller": {"running": True, "mode": "supervisor",
                                       "status": "ready"}, "suspended": False})
    assert liveness.probe_control_plane(city_root=tmp_path) is True


def test_suspended_city_is_not_active(tmp_path, monkeypatch):
    """A suspended city routes nothing even with a live controller."""
    monkeypatch.setenv("PATH", os.environ["PATH"])
    _fake_gc(tmp_path, {"controller": {"running": True, "status": "ready"},
                        "suspended": True})
    assert liveness.probe_control_plane(city_root=tmp_path) is False


def test_starting_city_is_not_yet_active(tmp_path, monkeypatch):
    """Mid-start is observably real: controller.running is false while the
    bead store comes up. Dispatch must refuse rather than sling into it."""
    monkeypatch.setenv("PATH", os.environ["PATH"])
    _fake_gc(tmp_path, {"controller": {"running": False, "mode": "supervisor",
                                       "status": "starting_bead_store"},
                        "suspended": False})
    assert liveness.probe_control_plane(city_root=tmp_path) is False


def test_unparseable_answer_is_cannot_tell(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", os.environ["PATH"])
    _fake_gc(tmp_path, None)
    assert liveness.probe_control_plane(city_root=tmp_path) is None


def test_probe_is_city_scoped_not_daemon_scoped(tmp_path, monkeypatch):
    """The exact live failure: the machine-wide daemon is up, this city is not.

    A daemon-scoped probe (`gc supervisor status`) exits 0 here and the gate
    never fires. Assert we never ask that question.
    """
    monkeypatch.setenv("PATH", os.environ["PATH"])
    argv_log = tmp_path / "argv.log"
    shim = tmp_path / "gc"
    shim.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env python3
        import sys, json
        open({str(argv_log)!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")
        if sys.argv[1:2] == ["supervisor"]:
            sys.stdout.write("Supervisor is running (PID 97153)")
            sys.exit(0)
        sys.stdout.write(json.dumps({{"controller": {{"running": False,
            "status": "stopped"}}, "suspended": False}}))
        """), encoding="utf-8")
    shim.chmod(0o755)
    os.environ["PATH"] = f"{tmp_path}{os.pathsep}{os.environ['PATH']}"

    assert liveness.probe_control_plane(city_root=tmp_path) is False
    calls = argv_log.read_text(encoding="utf-8")
    assert "supervisor status" not in calls, (
        "probe asked the machine-wide daemon; that question exits 0 while this "
        f"city's controller is stopped. argv was: {calls!r}"
    )
    assert "--city" in calls and "--json" in calls


def test_slow_gc_does_not_silently_open_the_gate(tmp_path, monkeypatch):
    """A probe timeout must not read as 'control plane is fine'.

    Live 2026-08-19: `gc status --city … --json` exceeded the 10s timeout on a
    healthy machine (gc carries seconds of baseline overhead). The probe
    returned None and the caller, testing `is False`, dispatched anyway.
    A safety gate that opens when it cannot see is not a gate.
    """
    monkeypatch.setenv("PATH", os.environ["PATH"])
    shim = tmp_path / "gc"
    shim.write_text("#!/bin/sh\nsleep 30\n", encoding="utf-8")
    shim.chmod(0o755)
    os.environ["PATH"] = f"{tmp_path}{os.pathsep}{os.environ['PATH']}"
    assert liveness.probe_control_plane(city_root=tmp_path, timeout=0.5) is None


def test_control_plane_timeout_allows_for_gc_latency():
    """gc routinely takes >10s. The timeout must not be tighter than the tool."""
    assert liveness.CONTROL_PLANE_TIMEOUT_SECONDS >= 30
