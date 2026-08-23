"""City-wide health: the data plane's three-valued liveness, plus the
resource pressure that has twice presented as mysterious latency instead of
a named alarm (`tdupu/mathcity#70`, dashboard handoff `#114`).

`data_plane` distinguishes three states, not two, because a boolean collapses
exactly the case this module exists to catch: the Dolt server can be
reachable while one or more of its databases is quarantined -- up, but not to
be trusted. `gc dolt health --json` already names quarantined databases with
a reason; this module reads that rather than inventing a second definition of
"degraded".

Resource pressure (file descriptors, disk) is read fresh on every call and
carries no history: there is nowhere in this city today that records an fd
sample over time, so `fds_trend` is honestly `"unknown"`, never guessed from
one point. See `MCTL_HEALTH_NO_FD_HISTORY`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence

from .context import CityScope, RegisteredRig
from .diagnostics import Diagnostic, Severity

DATA_PLANE_HEALTHY = "healthy"
DATA_PLANE_QUARANTINED = "reachable_quarantined"
DATA_PLANE_UNREACHABLE = "unreachable"

#: The data plane's state was not established. #159: a `gc` timeout was being
#: charged to Dolt -- `data_plane: "unreachable"` while Dolt answered in 113ms
#: with 18 databases. What was broken was the probe.
#:
#: This is the None-vs-Unknown distinction this module already makes elsewhere,
#: applied to its own headline field. "We could not ask" is not "the answer is
#: no", and spelling them the same way sends a reader looking in the wrong
#: place with 17 rigs corroborating.
DATA_PLANE_UNKNOWN = "unknown"

#: The detail `probe_dolt_health` emits when `gc` ANSWERED and the answer was
#: that the server is down. That is a measurement about the subject; every
#: other non-success is a fact about the probe. Matched on the detail because
#: `PROBE_REFUSED` was carrying both cases.
DOLT_ANSWERED_DOWN_DETAIL = "gc dolt health reports server.reachable=false"

PROBE_SUCCEEDED = "succeeded"
PROBE_TIMED_OUT = "timed_out"
PROBE_REFUSED = "refused"

#: `gc dolt health` has no fixed deadline of its own; this is the deadline
#: THIS probe imposes on the subprocess call. A probe that hangs as long as
#: the thing it is checking is not a probe -- see liveness.py's own note on
#: why CONTROL_PLANE_TIMEOUT_SECONDS is None for a *different*, non-negotiable
#: reason. Here the probe result itself is allowed to say "timed_out"; the gc
#: status probe cannot, because a slow answer there is still an answer.
#:
#: Set generously (30s, matching fleet.py's probes) on measured evidence: a
#: live run against this city on 2026-08-20 took 39s under concurrent agent
#: load, well past a naive 10s guess. A tool this loose about deadlines is
#: exactly the failure mode #70/#114 describe if the number is too tight --
#: a real answer discarded and reported as "unreachable".
DOLT_HEALTH_PROBE_TIMEOUT_SECONDS = 30.0

#: Headroom below `kern.maxfilesperproc` that counts as "approaching the
#: ceiling" for a flood-condition alarm. Chosen from the live incident this
#: module exists for: 138,230 held against a 138,240 cap -- ten of headroom --
#: was already past the point of usefulness for a threshold. 5,000 gives an
#: operator room to act before the ceiling, not just a name for having hit it.
FD_HEADROOM_ALARM_THRESHOLD = 5000


@dataclass(frozen=True)
class ProbeResult:
    name: str
    outcome: str  # succeeded | timed_out | refused
    timeout_seconds: float | None
    latency_ms: float | None
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "detail": self.detail,
            "latency_ms": self.latency_ms,
            "name": self.name,
            "outcome": self.outcome,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class FloodCondition:
    resource: str
    detail: str
    growth: str  # measured value, or "unknown" -- see module docstring
    since: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "detail": self.detail,
            "growth": self.growth,
            "resource": self.resource,
            "since": self.since,
        }


@dataclass(frozen=True)
class RigDiskUsage:
    rig_id: str
    bytes_used: int | None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"bytes_used": self.bytes_used, "reason": self.reason, "rig_id": self.rig_id}


@dataclass(frozen=True)
class ResourcePressure:
    fds_used: int | None
    fds_limit: int | None
    fds_trend: str
    disk_per_rig: tuple[RigDiskUsage, ...]
    flood_conditions: tuple[FloodCondition, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "disk_per_rig": [d.to_dict() for d in self.disk_per_rig],
            "fds_limit": self.fds_limit,
            "fds_trend": self.fds_trend,
            "fds_used": self.fds_used,
            "flood_conditions": [f.to_dict() for f in self.flood_conditions],
        }


@dataclass(frozen=True)
class PerRigHealth:
    rig_id: str
    state: str  # healthy | degraded | unreachable
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"reason": self.reason, "rig_id": self.rig_id, "state": self.state}


@dataclass(frozen=True)
class CityHealthReport:
    data_plane: str
    probe_results: tuple[ProbeResult, ...]
    resources: ResourcePressure
    per_rig: tuple[PerRigHealth, ...]
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "data_plane": self.data_plane,
            "per_rig": [r.to_dict() for r in self.per_rig],
            "probe_results": [p.to_dict() for p in self.probe_results],
            "resources": self.resources.to_dict(),
        }


def _run_json(
    command: Sequence[str], *, timeout: float, cwd: Path | None = None
) -> tuple[Mapping[str, object] | None, str]:
    """Run a `gc ... --json` command and parse its stdout.

    Returns `(None, detail)` on any failure -- process error, timeout,
    non-JSON output -- rather than raising, because a probe that can crash
    the tool it serves is not a probe.
    """
    try:
        result = subprocess.run(
            list(command), text=True, capture_output=True, check=False, timeout=timeout, cwd=cwd
        )
    except subprocess.TimeoutExpired:
        return None, f"{command[0]} did not answer within {timeout}s"
    except OSError as error:
        return None, f"{command[0]} could not be run: {error}"
    # `gc` writes advisory warnings (e.g. tmux liveness cache misses) to
    # stdout ahead of the JSON object on some subcommands -- carve from the
    # first `{` rather than assume stdout is JSON alone.
    text = result.stdout
    start = text.find("{")
    if start == -1:
        return None, f"{command[0]} produced no JSON object (exit {result.returncode})"
    try:
        payload = json.loads(text[start:])
    except json.JSONDecodeError as error:
        return None, f"{command[0]} produced unparseable JSON: {error}"
    if not isinstance(payload, dict):
        return None, f"{command[0]} produced a non-object JSON value"
    return payload, ""


def probe_dolt_health(
    city_root: Path, *, timeout: float = DOLT_HEALTH_PROBE_TIMEOUT_SECONDS
) -> tuple[ProbeResult, Mapping[str, object] | None]:
    """Probe the managed Dolt server: reachability, latency, quarantine.

    `gc dolt health` is the authoritative source for quarantine state --
    reading it here rather than re-deriving quarantine from Dolt directly
    keeps one definition of "quarantined", the same one `gc dolt` commands
    already use.

    Runs with `cwd=city_root` rather than a trailing `--city` flag: measured
    directly, `gc dolt health` rejects `--city` in every position tried
    ("unknown flag: --city") even though it is listed under the command's
    own `--help`, while `gc status` and `gc session list` both accept it
    normally. That inconsistency belongs to `gc` itself, not this probe --
    working around it here rather than papering over the mismatch by
    silently succeeding either way.
    """
    started = time.monotonic()
    payload, detail = _run_json(["gc", "dolt", "health", "--json"], timeout=timeout, cwd=city_root)
    elapsed_ms = (time.monotonic() - started) * 1000
    if payload is None:
        outcome = PROBE_TIMED_OUT if "did not answer" in detail else PROBE_REFUSED
        return (
            ProbeResult(
                name="dolt_health",
                outcome=outcome,
                timeout_seconds=timeout,
                latency_ms=None,
                detail=detail,
            ),
            None,
        )
    server = payload.get("server")
    server = server if isinstance(server, dict) else {}
    reachable = server.get("reachable")
    latency_ms = server.get("latency_ms")
    if reachable is False:
        return (
            ProbeResult(
                name="dolt_health",
                outcome=PROBE_REFUSED,
                timeout_seconds=timeout,
                latency_ms=float(latency_ms) if isinstance(latency_ms, (int, float)) else None,
                detail="gc dolt health reports server.reachable=false",
            ),
            payload,
        )
    return (
        ProbeResult(
            name="dolt_health",
            outcome=PROBE_SUCCEEDED,
            timeout_seconds=timeout,
            latency_ms=(
                float(latency_ms) + elapsed_ms
                if isinstance(latency_ms, (int, float))
                else None
            ),
            detail="gc dolt health answered",
        ),
        payload,
    )


_SUPERVISOR_PID_PATTERN = re.compile(r"^\s*\S+\s+(\d+)\s")


def _find_supervisor_pid() -> int | None:
    """The PID of the `gc supervisor run` process, or None if not found.

    Uses `pgrep -f`, the same discovery this city used by hand during the
    2026-08-20 incident. If more than one process matches, the first is used
    and the ambiguity is not resolved further -- a known limitation, not a
    silent wrong answer: `probe_supervisor_fds` reports it could not resolve
    a single PID when `pgrep` returns more than one line.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", "gc supervisor run"], text=True, capture_output=True, check=False
        )
    except OSError:
        return None
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        return None
    try:
        return int(lines[0].strip())
    except ValueError:
        return None


def probe_supervisor_fds() -> tuple[int | None, int | None, str]:
    """`(fds_used, fds_limit, detail)` for the running supervisor process.

    `fds_limit` comes from `sysctl kern.maxfilesperproc` -- the OS-level
    per-process ceiling -- not `ulimit -n`, which reports the shell's own
    limit (1,048,576 here) and is not the binding constraint; the 2026-08-20
    incident hit the sysctl ceiling at 138,240 while `ulimit -n` reported a
    number 7x higher and irrelevant to the failure.
    """
    pid = _find_supervisor_pid()
    if pid is None:
        return None, None, "no single `gc supervisor run` process found (pgrep -f)"
    try:
        lsof_result = subprocess.run(
            ["lsof", "-p", str(pid)], text=True, capture_output=True, check=False
        )
    except OSError as error:
        return None, None, f"lsof failed: {error}"
    if lsof_result.returncode not in (0, 1):  # lsof exits 1 when a process has no open files
        return None, None, f"lsof exited {lsof_result.returncode}"
    used = max(0, len(lsof_result.stdout.splitlines()) - 1)  # minus the header row
    try:
        sysctl_result = subprocess.run(
            ["sysctl", "-n", "kern.maxfilesperproc"], text=True, capture_output=True, check=False
        )
        limit = int(sysctl_result.stdout.strip())
    except (OSError, ValueError):
        return used, None, "kern.maxfilesperproc unreadable"
    return used, limit, f"pid {pid}"


def _dolt_dir_size_bytes(city_root: Path, rig_db: str) -> tuple[int | None, str | None]:
    """Disk usage of one rig's Dolt directory, via `du -sk`.

    `gc dolt health`'s `databases[]` carries commits/open_beads but no size --
    only `orphans[]` does. Sizing a *registered* database is not wrapped
    anywhere today, so this reads the filesystem directly rather than
    inventing a number.
    """
    path = city_root / ".beads" / "dolt" / rig_db
    if not path.is_dir():
        return None, f"{path} does not exist"
    try:
        result = subprocess.run(
            ["du", "-sk", str(path)], text=True, capture_output=True, check=False, timeout=10.0
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"du failed: {error}"
    if result.returncode != 0:
        return None, f"du exited {result.returncode}"
    match = re.match(r"^(\d+)\s", result.stdout)
    if not match:
        return None, "du produced unparseable output"
    return int(match.group(1)) * 1024, None


def answered_that_dolt_is_down(probe: ProbeResult) -> bool:
    """Whether the probe ANSWERED, and the answer was that the server is down.

    `PROBE_REFUSED` is emitted for two incompatible situations: `gc` answered
    with `server.reachable=false`, which is a measurement, and `gc` failed for
    its own reasons, which is not. Only the first says anything about Dolt.
    """
    return probe.detail == DOLT_ANSWERED_DOWN_DETAIL


def data_plane_for(probe: ProbeResult, quarantine_by_db: Mapping[str, str]) -> str:
    """The data plane's state, or `unknown` when the probe did not establish it.

    #159. The old rule was `outcome != SUCCEEDED -> unreachable`, which turned
    every way of failing to ask into an answer. A probe timing out is a fact
    about `gc`; it is not evidence about Dolt, and Dolt was in fact healthy
    throughout the incident that produced this issue.
    """
    if probe.outcome == PROBE_SUCCEEDED:
        return DATA_PLANE_QUARANTINED if quarantine_by_db else DATA_PLANE_HEALTHY
    if answered_that_dolt_is_down(probe):
        return DATA_PLANE_UNREACHABLE
    return DATA_PLANE_UNKNOWN


def per_rig_state_for(probe: ProbeResult) -> str:
    """Per-rig state under a failed probe.

    Seventeen rigs reporting `unreachable` is what made the wrong conclusion
    persuasive: they were not seventeen observations, they were one probe's
    silence repeated seventeen times. If the probe established nothing, each
    row says `unknown` -- seventeen honest unknowns rather than seventeen
    corroborating errors.
    """
    return "unreachable" if answered_that_dolt_is_down(probe) else "unknown"


def build_city_health(scope: CityScope) -> CityHealthReport:
    """Assemble the full report. The only entry point this module exposes."""
    dolt_probe, dolt_payload = probe_dolt_health(scope.city_root)
    fds_used, fds_limit, fd_detail = probe_supervisor_fds()

    diagnostics: list[Diagnostic] = []
    quarantine_by_db: dict[str, str] = {}
    if dolt_payload is not None:
        for entry in dolt_payload.get("quarantine") or []:
            if isinstance(entry, dict) and isinstance(entry.get("db"), str):
                quarantine_by_db[entry["db"]] = str(entry.get("reason") or "quarantined")

    data_plane = data_plane_for(dolt_probe, quarantine_by_db)

    per_rig: list[PerRigHealth] = []
    disk_per_rig: list[RigDiskUsage] = []
    for rig in scope.rigs:
        if dolt_probe.outcome != PROBE_SUCCEEDED:
            per_rig.append(
                PerRigHealth(
                    rig_id=rig.name,
                    state=per_rig_state_for(dolt_probe),
                    reason=dolt_probe.detail,
                )
            )
        elif rig.db in quarantine_by_db:
            per_rig.append(
                PerRigHealth(
                    rig_id=rig.name, state="degraded", reason=quarantine_by_db[rig.db]
                )
            )
        else:
            per_rig.append(PerRigHealth(rig_id=rig.name, state="healthy", reason=""))

        size, size_reason = _dolt_dir_size_bytes(scope.city_root, rig.db)
        disk_per_rig.append(RigDiskUsage(rig_id=rig.name, bytes_used=size, reason=size_reason))

    flood_conditions: list[FloodCondition] = []
    if fds_used is not None and fds_limit is not None:
        headroom = fds_limit - fds_used
        if headroom <= FD_HEADROOM_ALARM_THRESHOLD:
            flood_conditions.append(
                FloodCondition(
                    resource="file_descriptors",
                    detail=(
                        f"{fds_used} fds held against a {fds_limit} cap ({headroom} of headroom, "
                        f"threshold {FD_HEADROOM_ALARM_THRESHOLD})"
                    ),
                    growth="unknown",
                )
            )
    else:
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARN,
                code="MCTL_HEALTH_FD_PROBE_FAILED",
                message="Could not measure the supervisor's file-descriptor usage.",
                hint=fd_detail,
                facts={"city_path": str(scope.city_root), "data_location": fd_detail},
                trace_id=scope.trace_id,
            )
        )

    diagnostics.append(
        Diagnostic(
            severity=Severity.INFO,
            code="MCTL_HEALTH_NO_FD_HISTORY",
            message=(
                "File-descriptor trend is unknown: no time-series sample store exists yet, "
                "so this reads one point in time and cannot say whether it is rising."
            ),
            hint="A recording slice (fd samples over time) is a gap, not a bug in this probe.",
            facts={"city_path": str(scope.city_root)},
            trace_id=scope.trace_id,
        )
    )

    resources = ResourcePressure(
        fds_used=fds_used,
        fds_limit=fds_limit,
        fds_trend="unknown",
        disk_per_rig=tuple(disk_per_rig),
        flood_conditions=tuple(flood_conditions),
    )

    return CityHealthReport(
        data_plane=data_plane,
        probe_results=(dolt_probe,),
        resources=resources,
        per_rig=tuple(per_rig),
        diagnostics=tuple(diagnostics),
    )
