"""The rebind, exercised end to end against a real dashboard process.

GH #231 exists because no live `dashboard_restart` had ever been applied. When
one finally was (2026-08-28), it killed the dashboard, misread its own zombie
child as still running, concluded the stop had failed, and therefore refused to
start a replacement -- an outage rather than a rebind (mc-6i9gm).

WHAT THIS FILE DOES AND DOES NOT PROVE. It pins that **stop-then-start actually
hands back a serving dashboard**, against a real spawned `mctl dashboard serve`
on a real port rather than a monkeypatched seam. That is worth having: a mocked
stop would have passed happily throughout the entire period the real one was
broken.

It does **NOT** discriminate on the zombie bug. Measured: these tests pass both
with and without the `pid_alive` fix, because Python's `subprocess` module reaps
finished children whenever a new `Popen` is constructed -- so the test process
cleans up the very zombie that production leaves lying around. Treating a green
run here as evidence that mc-6i9gm is fixed would be exactly the "check that
cannot fail" error the fix was found by avoiding.

**The discriminating tests are in `test_dashboard_stop_zombie.py`** (revert-proven:
2 fail without the fix). This file is the integration companion, scoped to the
rebind path itself.

Spawns real processes and binds a real port; still finishes in seconds.
No custom pytest marker: this repo registers none, and inventing an
unregistered one only emits warnings.
"""
from __future__ import annotations

import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import dashboards  # noqa: E402

CITY_ROOT = Path.home() / "gt"

pytestmark = pytest.mark.skipif(
    not (CITY_ROOT / "city.toml").exists(),
    reason="needs a real city root to serve",
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _listening(port: int, *, timeout: float) -> bool:
    """Poll the PORT, which is the dashboard's actual contract."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as s:
            s.settimeout(0.4)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def _gone(port: int, *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as s:
            s.settimeout(0.4)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return True
        time.sleep(0.2)
    return False


def _instance_on(port: int) -> dashboards.DashboardInstance | None:
    for inst in dashboards.discover(CITY_ROOT):
        if inst.port == port:
            return inst
    return None


@pytest.fixture
def served_port():
    """A real dashboard on a free port, torn down however the test ends.

    Teardown is unconditional -- the #154 rule is that whoever starts a
    dashboard stops it, and a test that leaks one is the exact failure that
    rule was written for.
    """
    port = _free_port()
    dashboards.start_instance(city_root=CITY_ROOT, host="127.0.0.1", port=port, rig=None)
    try:
        assert _listening(port, timeout=30), "the dashboard never bound its port"
        yield port
    finally:
        inst = _instance_on(port)
        if inst is not None:
            dashboards.stop_instance(inst)
            dashboards.remove_stamp(CITY_ROOT, inst.pid)


def test_a_started_dashboard_serves(served_port: int) -> None:
    """Control. Without this, the rebind test could pass on a dead port."""
    with urllib.request.urlopen(f"http://127.0.0.1:{served_port}/pile", timeout=90) as r:
        assert r.status == 200


def test_stop_then_start_rebinds(served_port: int) -> None:
    """The #231 question: does a stop-then-start actually hand back a server?

    This is the sequence `dashboard_restart` runs. Before mc-6i9gm the stop
    reported failure on a process it had killed, so the start never happened
    and the port stayed dead.
    """
    old = _instance_on(served_port)
    assert old is not None, "the instance left no discoverable stamp"

    assert dashboards.stop_instance(old) is True, (
        "stop_instance reported failure on a process it killed -- mc-6i9gm"
    )
    dashboards.remove_stamp(CITY_ROOT, old.pid)
    assert _gone(served_port, timeout=20), "the port was still bound after a successful stop"

    dashboards.start_instance(
        city_root=CITY_ROOT, host="127.0.0.1", port=served_port, rig=None
    )
    assert _listening(served_port, timeout=30), "nothing bound the port after the restart"

    new = _instance_on(served_port)
    assert new is not None
    assert new.pid != old.pid, "the rebind returned the same pid; nothing was replaced"

    with urllib.request.urlopen(f"http://127.0.0.1:{served_port}/pile", timeout=90) as r:
        assert r.status == 200, "the rebound dashboard does not serve"


def test_stopped_dashboard_leaves_no_zombie_claiming_to_be_alive(served_port: int) -> None:
    """The specific misreading that caused the outage.

    After a stop, the old pid must not report alive -- that false positive is
    what made `dashboard_restart` refuse to replace what it had just destroyed.
    """
    inst = _instance_on(served_port)
    assert inst is not None
    dashboards.stop_instance(inst)
    dashboards.remove_stamp(CITY_ROOT, inst.pid)
    assert dashboards.pid_alive(inst.pid) is False, (
        "the stopped dashboard still reads as alive -- a zombie is not a process"
    )
    # restore so the fixture's teardown has something coherent to clean up
    dashboards.start_instance(
        city_root=CITY_ROOT, host="127.0.0.1", port=served_port, rig=None
    )
    _listening(served_port, timeout=30)
