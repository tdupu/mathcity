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
    """
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


def stop_instance(instance: DashboardInstance) -> bool:
    """SIGTERM the instance, escalating to SIGKILL if it will not exit.

    Returns whether the process is gone afterwards. A restart must not claim
    success on a stop that did not take (`P6.2`).
    """
    import signal

    try:
        os.kill(instance.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True  # already gone
    except OSError:
        return False
    deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not pid_alive(instance.pid):
            return True
        time.sleep(0.1)
    try:
        os.kill(instance.pid, signal.SIGKILL)
    except OSError:
        pass
    time.sleep(0.1)
    return not pid_alive(instance.pid)


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
