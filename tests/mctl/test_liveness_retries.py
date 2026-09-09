"""One refused handshake must not fail the whole city closed (#196).

`probe_city` decided liveness from a SINGLE `socket.create_connection` with no
retry, and `city_not_active_diagnostic` is the shared fail-closed gate both the
CLI and the MCP server run through. So one transient refusal turned into
MCTL_CITY_NOT_ACTIVE for every rig, every read, on both adapters at once —
measured live as a dashboard that showed a healthy populated city on one page
and "17/17 rigs not reachable" on the next.

Fail-closed is right for the gate. Deciding it from one packet is not: a
managed Dolt server that is briefly saturated is not a city that is down, and
the two are indistinguishable from a single connect.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import liveness  # noqa: E402


def _rig(tmp_path: Path, port: int = 14315) -> Path:
    rig = tmp_path / "rig"
    (rig / ".beads").mkdir(parents=True)
    (rig / ".beads" / "dolt-server.port").write_text(str(port), encoding="utf-8")
    (rig / ".beads" / "config.yaml").write_text("dolt:\n  mode: server\n", encoding="utf-8")
    return rig


class _Conn:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_a_single_transient_refusal_does_not_fail_the_city(tmp_path, monkeypatch):
    """The defect. One blip, then success -> the city is ALIVE."""
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("connection refused")
        return _Conn()

    monkeypatch.setattr(liveness.socket, "create_connection", flaky)
    monkeypatch.setattr(liveness.time, "sleep", lambda *_: None)
    result = liveness.probe_city(_rig(tmp_path))
    assert result.active is True, result.detail
    assert calls["n"] >= 2, "it did not retry"


def test_a_real_outage_is_still_reported_down(tmp_path, monkeypatch):
    """Fail-closed is preserved: every attempt refused -> active False."""
    monkeypatch.setattr(
        liveness.socket, "create_connection",
        lambda *a, **k: (_ for _ in ()).throw(OSError("connection refused")),
    )
    monkeypatch.setattr(liveness.time, "sleep", lambda *_: None)
    result = liveness.probe_city(_rig(tmp_path))
    assert result.active is False
    assert "attempt" in (result.detail or "").lower(), (
        "the detail must say how many attempts were made, or a reader cannot "
        f"tell a blip from an outage: {result.detail!r}"
    )


def test_a_healthy_endpoint_costs_ONE_attempt(tmp_path, monkeypatch):
    """Positive control: retries must not be spent when the first connect works."""
    calls = {"n": 0}

    def ok(*a, **k):
        calls["n"] += 1
        return _Conn()

    monkeypatch.setattr(liveness.socket, "create_connection", ok)
    result = liveness.probe_city(_rig(tmp_path))
    assert result.active is True
    assert calls["n"] == 1, f"a healthy endpoint was probed {calls['n']} times"
