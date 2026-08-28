"""Dashboard process lifecycle, made queryable and deliberately restartable.

`#207`. The dashboard runs as a hand-launched `mctl dashboard serve` process,
separate from the `mctl mcp serve` server that answers tool calls. Its lifecycle
was invisible from the typed surface: an MCP-only Mayor could neither report
which commit a dashboard was serving (the `#210`/`#164` stamp lived only on the
page) nor restart a stale instance deliberately -- the only remedy was a human
finding the PID and re-running the command in a terminal.

This module makes the lifecycle honest and typed. A serving dashboard writes a
STAMP at startup naming its pid, port, city and the commit its code imported
(`serving.SERVING_COMMIT`, captured once at import -- the `#210` semantic: a
stale process reports its OWN startup commit, not the checkout's current HEAD).
The stamp is the single measurable source `dashboard_status` reads;
`dashboard_restart` stops a named instance and re-serves from current code.

`P6.2` governs every read: a stamp whose serving commit could not be captured
reports `serving_known=False`, never a placeholder a caller would later compare
against `origin/main` as if it were a revision. And restart never happens
automatically -- that inversion is exactly what `#164`/`#210` reject.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import serving


#: Where a city's dashboards leave their stamps. Under the city root so a
#: city-scoped tool finds them the same way it finds `city.toml`; hidden so it
#: does not clutter the tree. One file per pid.
STAMP_SUBDIR = (".mctl", "dashboards")

#: How long to wait for a stopped instance to exit before escalating SIGTERM to
#: SIGKILL. Short: a local dashboard is an `http.server`, not a database.
STOP_TIMEOUT_SECONDS = 10.0

#: `dashboard_serve` (start) waits this long for a freshly-spawned instance to
#: bind its port and write its stamp before it STOPS waiting. A local
#: `http.server` binds in well under a second; this budget is generous. `P6.3`:
#: reaching it is `still_starting` -- a distinct non-failure state carrying
#: elapsed, NEVER rendered as `failed`.
START_CONFIRM_TIMEOUT_SECONDS = 5.0

#: A warn threshold STRICTLY beneath the start deadline (`P6.3`): crossing it
#: means the start is slow, and the elapsed time is surfaced, before the
#: deadline itself is ever reached.
START_CONFIRM_WARN_SECONDS = 2.0


def stamp_dir(city_root: Path) -> Path:
    return Path(city_root).joinpath(*STAMP_SUBDIR)


def stamp_path(city_root: Path, pid: int) -> Path:
    return stamp_dir(city_root) / f"{pid}.json"


def write_stamp(
    city_root: Path,
    *,
    pid: int,
    host: str,
    port: int,
    url: str,
    rig: str | None,
    serving_commit: str | None,
    started_at: str,
) -> Path:
    """Record a serving dashboard's identity so it becomes queryable.

    `serving_commit` is the caller's OWN import-time commit
    (`serving.SERVING_COMMIT`), or `None` if it could not be read -- written
    through faithfully so `discover` can report `serving_known=False` rather
    than invent a revision (`P6.2`).
    """
    path = stamp_path(city_root, pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "pid": pid,
                "host": host,
                "port": port,
                "url": url,
                "rig": rig,
                "serving_commit": serving_commit,
                "started_at": started_at,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def remove_stamp(city_root: Path, pid: int) -> None:
    """Best-effort removal of one stamp. Never raises: a dashboard shutting down
    must not fail because its stamp is already gone."""
    try:
        stamp_path(city_root, pid).unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def pid_alive(pid: int) -> bool:
    """Whether a process with this pid exists and we may signal it.

    `os.kill(pid, 0)` sends no signal; it only checks existence/permission.
    `ESRCH` means gone, `EPERM` means alive but not ours (still a live process).

    **A zombie is not alive.** `os.kill(pid, 0)` succeeds for a terminated child
    that its parent has not reaped -- the pid slot is held until someone waits
    on it -- so the raw check reports a dead process as running. That is not
    hypothetical: on 2026-08-28 the first live `dashboard_restart` killed the
    dashboard, read its own zombie as still running, and therefore refused to
    start a replacement (mc-6i9gm / GH #231). The refusal was the correct
    response to a failed stop; the stop had not failed.

    So reap first. `waitpid(WNOHANG)` clears our own exited children and makes
    the `os.kill` below answer honestly; `ChildProcessError` means the pid is
    not our child, and the ordinary check decides. Reaping a child we spawned is
    the caller's job anyway, so this fixes a leak as well as the predicate.
    """
    try:
        reaped, _status = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except ChildProcessError:
        pass  # not our child -- os.kill below is the authority
    except (OSError, ValueError):
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


@dataclass(frozen=True)
class DashboardInstance:
    pid: int
    host: str
    port: int
    url: str
    rig: str | None
    serving_commit: str | None
    started_at: str
    #: Filled by `discover` against the checkout's current HEAD, so a caller
    #: reading one instance does not have to re-derive staleness itself.
    current_commit: str | None = None

    @property
    def serving_known(self) -> bool:
        """`P6.2`: False means the commit could not be captured -- not a claim
        about any revision."""
        return self.serving_commit is not None

    @property
    def stale(self) -> bool:
        """True only when BOTH commits are known and differ. Unknown is never
        reported as stale, and never as current -- see `staleness_known`."""
        if self.serving_commit is None or self.current_commit is None:
            return False
        return self.serving_commit != self.current_commit

    @property
    def staleness_known(self) -> bool:
        return self.serving_commit is not None and self.current_commit is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "rig": self.rig,
            "serving_commit": self.serving_commit,
            "serving_known": self.serving_known,
            "started_at": self.started_at,
            "current_commit": self.current_commit,
            "stale": self.stale,
            "staleness_known": self.staleness_known,
        }


def _read_stamp(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def discover(city_root: Path, *, current_commit: str | None = None, prune: bool = True) -> list[DashboardInstance]:
    """Every LIVE dashboard this city has stamped, newest port last.

    A stamp whose process is gone is not a running dashboard; it is excluded and
    (unless `prune=False`) its stale file removed, so dead stamps cannot accrue
    the way stray servers did in `#154`. `current_commit` defaults to a fresh
    read of the checkout HEAD so each instance carries its own staleness.
    """
    directory = stamp_dir(city_root)
    if not directory.is_dir():
        return []
    if current_commit is None:
        current_commit = serving.read_commit(serving.PACK_ROOT)
    instances: list[DashboardInstance] = []
    for path in sorted(directory.glob("*.json")):
        data = _read_stamp(path)
        if not data or "pid" not in data:
            continue
        pid = int(data["pid"])
        if not pid_alive(pid):
            if prune:
                try:
                    path.unlink()
                except OSError:
                    pass
            continue
        instances.append(
            DashboardInstance(
                pid=pid,
                host=str(data.get("host") or "127.0.0.1"),
                port=int(data.get("port") or 0),
                url=str(data.get("url") or ""),
                rig=data.get("rig"),
                serving_commit=data.get("serving_commit"),
                started_at=str(data.get("started_at") or ""),
                current_commit=current_commit,
            )
        )
    instances.sort(key=lambda inst: inst.port)
    return instances


# ---------------------------------------------------------------------------
# the mutation seams: stop an instance, start a fresh one
#
# Module-level so `dashboard_restart` reaches them by name and a test can
# monkeypatch them without spawning or killing a real process. Both have real
# implementations for production.
# ---------------------------------------------------------------------------


def teardown(city_root: Path, *, port: int | None = None) -> dict[str, object]:
    """Stop live dashboards and clear their stamps -- the missing #154 step.

    `discover` already reaps dead stamps (a process that is gone is not a running
    dashboard), so a plain teardown also cleans up the strays that accrued. Each
    live instance (all of them, or the one on `port`) is stopped and its stamp
    removed; a stop that does not take is reported as a failure with its stamp
    LEFT IN PLACE (`P6.2`: never count an instance that may still be up as torn
    down).
    """
    instances = discover(city_root)  # prunes dead stamps as a side effect
    targets = [inst for inst in instances if port is None or inst.port == port]
    stopped: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    for inst in targets:
        if stop_instance(inst):
            remove_stamp(city_root, inst.pid)
            stopped.append(inst.to_dict())
        else:
            failed.append(inst.to_dict())
    return {"requested_port": port, "stopped": stopped, "failed": failed}


def port_bound(host: str, port: int, *, timeout: float = 0.4) -> bool:
    """Whether anything is currently serving `host:port`.

    **This is the authoritative liveness signal for a dashboard, and pid state
    is not.** A dashboard's contract is "something serves this port", which any
    process can observe regardless of who spawned what. `pid_alive` cannot say
    that across a process boundary: a zombie answers `os.kill(pid, 0)`, and
    only the zombie's own parent can reap it.

    Measured 2026-08-28 (mc-6i9gm): a session tearing down a dashboard it did
    not start got `waitpid -> ChildProcessError`, fell through to
    `os.kill(pid, 0)`, and read a defunct process as running. Port 8471 was
    left unserved while the tool reported the stop had failed.
    """
    import socket

    with socket.socket() as probe:
        probe.settimeout(timeout)
        return probe.connect_ex((host or "127.0.0.1", int(port))) == 0


def stop_instance(instance: DashboardInstance) -> bool:
    """SIGTERM the instance, escalating to SIGKILL if it will not exit.

    Returns whether the dashboard is gone afterwards. A restart must not claim
    success on a stop that did not take (`P6.2`).

    **Stopped is decided by the PORT, with pid state as a fast path only.**
    The pid check short-circuits the common same-parent case; the port check is
    what makes the answer correct when the caller is not the dashboard's parent,
    which is the ordinary cross-session teardown and the case mc-6i9gm was
    filed for. A pid we cannot reap tells us nothing; an unbound port tells us
    everything.
    """
    import signal

    def _gone() -> bool:
        # Port first: it is the contract, and it is true regardless of
        # parentage. `pid_alive` remains as a cheap confirmation for the case
        # where we DO own the child and can reap it.
        if not port_bound(instance.host, instance.port):
            return True
        return not pid_alive(instance.pid)

    try:
        os.kill(instance.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True  # already gone
    except OSError:
        return False
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _gone():
            return True
        time.sleep(0.1)
    try:
        os.kill(instance.pid, signal.SIGKILL)
    except OSError:
        pass
    time.sleep(0.1)
    return _gone()


def start_instance(*, city_root: Path, host: str, port: int, rig: str | None) -> dict[str, object]:
    """Launch a fresh detached `mctl dashboard serve` from current code.

    Detached (`start_new_session=True`, streams to devnull) so the new
    dashboard outlives the short-lived MCP call that asked for it. Reports the
    commit it will import -- the checkout's current HEAD, read fresh here --
    which is the whole reason to restart: to move a stale instance onto it.
    """
    mctl = Path(__file__).resolve().parents[1] / "mctl.py"
    command = [sys.executable, str(mctl), "dashboard", "serve", "--city", str(city_root), "--port", str(port), "--host", host]
    if rig:
        command += ["--rig", rig]
    with open(os.devnull, "wb") as devnull:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
            cwd=str(city_root),
        )
    return {
        "pid": proc.pid,
        "serving_commit": serving.read_commit(serving.PACK_ROOT),
        "started_at": serving.SERVER_STARTED_AT,
        "url": f"http://{host}:{port}",
    }


def confirm_started(
    city_root: Path,
    *,
    pid: int,
    timeout: float = START_CONFIRM_TIMEOUT_SECONDS,
    warn: float = START_CONFIRM_WARN_SECONDS,
) -> dict[str, object]:
    """Turn a freshly-spawned dashboard's bare pid into three-valued evidence.

    `start_instance` returns the child's pid immediately -- before the child has
    imported its code, bound its port, or written its stamp. This waits for the
    child to PROVE it came up, honoring the fail-loud / deadline triad:

    - ``confirmed`` -- the child wrote its stamp within the deadline, which
      `server.serve_from_args` does only AFTER binding the port. A real start.
    - ``died`` -- the child process exited before stamping (`P6.1`): the port
      did not bind, or the import blew up. A genuine failure the caller renders
      loudly, never as a start that took.
    - ``still_starting`` -- the deadline elapsed with the process still alive
      but not yet stamped (`P6.3`): the CALLER stopped waiting; this is not a
      verdict on the child. It carries ``elapsed`` and is named distinctly so a
      slow start is never collapsed into a dead one.

    ``slow`` is True once ``warn`` (strictly below ``timeout``) is crossed, so
    the caller can surface the elapsed time before the deadline is reached.
    """
    started = time.monotonic()
    while True:
        elapsed = time.monotonic() - started
        if stamp_path(city_root, pid).exists():
            return {"state": "confirmed", "elapsed": elapsed, "slow": elapsed >= warn}
        if not pid_alive(pid):
            return {"state": "died", "elapsed": elapsed, "slow": elapsed >= warn}
        if elapsed >= timeout:
            return {"state": "still_starting", "elapsed": elapsed, "slow": True}
        time.sleep(0.05)
