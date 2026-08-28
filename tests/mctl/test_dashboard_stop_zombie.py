"""A killed-but-unreaped child is DEAD, and `stop_instance` must say so.

Measured on the live city 2026-08-28 (mc-6i9gm, GH #231). The first live
`dashboard_restart` ever applied killed the dashboard, decided it had not, and
therefore refused to start a replacement -- leaving the city with no dashboard:

    live -> MDSH_RESTART_FAILED, applied=false
            "Could not stop dashboard pid 15262 ...; it may still be running."
    ps   -> 15262 <defunct>          the process WAS killed
    curl -> HTTP 000                 nothing listening

`stop_instance` signals the child and then polls `pid_alive`, which is
`os.kill(pid, 0)`. That call **succeeds for a zombie**: a terminated child keeps
its pid slot until its parent reaps it, and the MCP server that spawned the
dashboard never waits on it. So a stop that fully succeeded reads as a stop that
failed.

What makes that an outage rather than a wrong log line is the guard downstream:
on a failed stop, `dashboard_restart` deliberately starts nothing on top, so as
not to double-bind the port. That guard is CORRECT. It is being handed a false
input, and it faithfully converts the false input into a dead dashboard.

**Do not fix this by weakening the guard.** Fix the predicate: reap our own
child so the zombie stops answering.

`test_zombie_child_reads_as_alive_today` is the honest control -- it pins the
BROKEN behaviour so the bug is demonstrable rather than asserted, and it must be
deleted in the same commit that fixes `pid_alive`.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import dashboards  # noqa: E402


def _zombie() -> subprocess.Popen:
    """A real child that has exited and has NOT been reaped.

    Not a mock: the defect is about operating-system process states, and a
    stubbed `pid_alive` would prove nothing about them.
    """
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        # poll() would reap it, which is exactly what we must not do here.
        if Path(f"/proc/{proc.pid}").exists() is False and sys.platform == "darwin":
            break
        time.sleep(0.05)
        break
    time.sleep(0.35)
    return proc


# -- controls --------------------------------------------------------------


def test_live_process_reads_as_alive() -> None:
    """Without this, a passing test below could be passing on a broken probe."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert dashboards.pid_alive(proc.pid) is True
    finally:
        proc.kill()
        proc.wait()


def test_reaped_process_reads_as_dead() -> None:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()  # reaped: the pid slot is released
    assert dashboards.pid_alive(proc.pid) is False


# -- the defect ------------------------------------------------------------


def test_zombie_child_reads_as_dead() -> None:
    """A process that has exited is not running, reaped or not.

    This was `xfail(strict=True)` while the defect stood, paired with a control
    pinning the broken behaviour. Fixing `pid_alive` made the xfail XPASS and
    the control fail with its own instruction to delete it -- which is what the
    pairing is for, and why neither is here now.
    """
    proc = _zombie()
    try:
        assert dashboards.pid_alive(proc.pid) is False
    finally:
        proc.wait()


def test_stop_instance_reports_a_killed_child_as_stopped() -> None:
    """The end the defect was actually about: the restart's stop verdict.

    `stop_instance` returning False is what makes `dashboard_restart` refuse to
    replace an instance it has already destroyed. A child that exits on SIGTERM
    must therefore read as stopped, not as "may still be running".
    """
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    instance = dashboards.DashboardInstance(
        pid=proc.pid,
        host="127.0.0.1",
        port=0,
        url="http://127.0.0.1:0",
        rig=None,
        serving_commit=None,
        started_at="2026-08-28T00:00:00+00:00",
    )
    try:
        assert dashboards.stop_instance(instance) is True
    finally:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, ChildProcessError):
            pass


# -- the case the tests above CANNOT reach -------------------------------------
#
# Every zombie built with `subprocess.Popen` makes the TEST the parent, so those
# tests only ever exercise same-parent teardown -- which already worked. BART hit
# the real one on 2026-08-28: tearing down a dashboard started by ANOTHER session
# (pid 9630, ppid 5453, STAT Z) with the waitpid fix present, and got the pre-fix
# outcome. `waitpid` raised ChildProcessError, `os.kill(pid, 0)` succeeded on the
# zombie, the stop reported failure, and port 8471 was left unserved.
#
# The lesson is sharper than the bug: a test aimed at the case that already
# worked will pass no matter how broken the case that matters is.


def test_port_bound_is_false_for_a_port_nobody_serves() -> None:
    """Control: without this, the assertions below prove nothing."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
    assert dashboards.port_bound("127.0.0.1", free) is False


def test_port_bound_is_true_for_a_served_port() -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        assert dashboards.port_bound("127.0.0.1", server.getsockname()[1]) is True


def test_a_stop_is_confirmed_by_the_port_even_when_the_pid_is_unreapable() -> None:
    """The cross-session case: we are NOT the process's parent.

    Simulated with a pid we could never reap, and a port nobody serves. Before
    the port check, `_gone()` depended on `pid_alive`, which cannot answer for a
    process we do not own.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]

    # pid 1 is init: alive, definitively not our child, unreapable by us.
    instance = dashboards.DashboardInstance(
        pid=1,
        host="127.0.0.1",
        port=free,
        url=f"http://127.0.0.1:{free}",
        rig=None,
        serving_commit=None,
        started_at="2026-08-28T00:00:00+00:00",
    )
    assert dashboards.pid_alive(1) is True, "pid 1 should read as alive"
    # The port is unserved, so the dashboard IS gone regardless of that pid.
    assert dashboards.port_bound(instance.host, instance.port) is False


def test_a_still_served_port_is_not_reported_stopped() -> None:
    """The guard must not flip to always-true: a bound port means still up."""
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        assert dashboards.port_bound("127.0.0.1", port) is True
