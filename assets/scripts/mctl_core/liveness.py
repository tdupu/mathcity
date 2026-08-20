"""Gas City data-plane liveness probing.

A rig configured for Dolt server mode routes every `bd` call through the
managed server. When that server is down, `bd` blocks until its own timeout,
so mctl would otherwise present a dead city as a hang. Probing the configured
endpoint directly turns that into an immediate, named failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket
import json
import subprocess
from typing import TYPE_CHECKING

from .diagnostics import Diagnostic, Severity

if TYPE_CHECKING:  # pragma: no cover - import cycle guard, context imports this module
    from .context import MctlContext


PROBE_TIMEOUT_SECONDS = 0.5
SERVER_MODE_MARKERS = ("dolt.mode: server", "dolt.mode:server")


@dataclass(frozen=True)
class CityLiveness:
    """Result of probing a rig's data plane.

    `active` is None when the rig does not use a server at all (embedded Dolt),
    which is a valid configuration and must never block a command.
    """

    active: bool | None
    endpoint: str | None
    detail: str

    @property
    def required(self) -> bool:
        return self.active is not None


def _port_file(rig_root: Path, city_root: Path | None) -> Path | None:
    candidates = [rig_root / ".beads" / "dolt-server.port"]
    if city_root is not None:
        candidates.append(city_root / ".beads" / "dolt-server.port")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _declares_server_mode(rig_root: Path) -> bool:
    config = rig_root / ".beads" / "config.yaml"
    if not config.is_file():
        return False
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(marker in text for marker in SERVER_MODE_MARKERS)


def _read_port(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def probe_city(
    rig_root: Path,
    city_root: Path | None = None,
    *,
    timeout: float = PROBE_TIMEOUT_SECONDS,
) -> CityLiveness:
    """Probe the rig's configured Dolt endpoint without running `bd`."""
    port_file = _port_file(rig_root, city_root)
    if port_file is None:
        if _declares_server_mode(rig_root):
            return CityLiveness(
                active=False,
                endpoint=None,
                detail=(
                    "rig config declares dolt.mode: server but no "
                    ".beads/dolt-server.port was found"
                ),
            )
        return CityLiveness(active=None, endpoint=None, detail="rig does not use a Dolt server")

    port = _read_port(port_file)
    if port is None:
        return CityLiveness(
            active=False, endpoint=None, detail=f"unreadable port file {port_file}"
        )

    endpoint = f"127.0.0.1:{port}"
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return CityLiveness(active=True, endpoint=endpoint, detail="endpoint accepted a connection")
    except OSError as error:
        return CityLiveness(
            active=False, endpoint=endpoint, detail=f"{endpoint} refused a connection: {error}"
        )


def city_not_active_diagnostic(ctx: "MctlContext") -> Diagnostic:
    """The shared fail-closed gate for a dead data plane.

    Both adapters need it -- the CLI before running a command, the MCP server
    before running a tool -- and a second copy would be a second definition of
    "the city is down". It lives beside the probe that decides that.
    """
    facts = {
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl city liveness gate",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if ctx.city_endpoint is not None:
        facts["data_location"] = ctx.city_endpoint
    return Diagnostic(
        severity=Severity.FATAL,
        code="MCTL_CITY_NOT_ACTIVE",
        message=(
            "The Gas City data plane for this rig is not reachable, so canonical "
            "bead state cannot be read."
        ),
        hint="Start the city with `gc supervisor run`, then re-run this command.",
        facts=facts,
        trace_id=ctx.trace_id,
    )


# NO DEFAULT TIMEOUT, on purpose.
#
# The comment that used to sit here said "a timeout tighter than the tool turns
# every slow call into 'cannot tell'" -- and then set 30 seconds anyway. On
# 2026-08-20 a supervisor carrying ~111k open file descriptors made a plain
# `gc status` take 92s. The probe gave up at 30s, returned None, and the caller's
# gate refused. Every dispatch in the city was blocked, and it presented as "the
# mayor will not sling work" rather than "the supervisor is sick".
#
# A slow answer is still an answer. The only thing a deadline buys here is the
# ability to convert it into a wrong one, because the caller cannot distinguish
# "the control plane is down" from "I stopped listening". So the probe waits.
#
# Callers who genuinely cannot block may pass an explicit timeout and handle the
# None themselves -- but that is an opt-in with a known cost, not the default.
CONTROL_PLANE_TIMEOUT_SECONDS = None


def probe_control_plane(
    city_root: Path | str | None = None,
    timeout: float | None = CONTROL_PLANE_TIMEOUT_SECONDS,
) -> bool | None:
    """Whether THIS city's controller is up and able to route work.

    This is a SEPARATE question from `probe_city`. `gc stop` brings down the
    city controller but leaves the managed Dolt server running under its own
    watchdog, so the data plane keeps answering while nothing is left to route
    a sling to. Bead reads only need Dolt; dispatch needs both.

    The question must be asked PER CITY, not per machine. `gc supervisor status`
    reports the launchd-managed daemon, which stays up across `gc stop` — it
    exited 0 in exactly the state this gate exists to catch, so the gate never
    fired and an armed dispatch sling'd into a stopped city (found live
    2026-08-19). `gc status --city <root> --json` answers for this city:
    `controller.running` is false while the city is stopped or still starting,
    and `suspended` is true for a city that routes nothing regardless.

    Returns None when `gc` is unavailable or its answer cannot be parsed, so
    callers can distinguish "not routing" from "cannot tell".

    Waits as long as `gc` takes by default -- see CONTROL_PLANE_TIMEOUT_SECONDS.
    A deadline here cannot make a sick control plane healthy; it can only turn a
    slow truth into an unknown, which the caller's gate then treats as a refusal.
    """
    command = ["gc", "status", "--json"]
    if city_root is not None:
        command[2:2] = ["--city", str(city_root)]
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("suspended") is True:
        return False
    controller = payload.get("controller")
    if not isinstance(controller, dict):
        return None
    running = controller.get("running")
    if not isinstance(running, bool):
        return None
    return running
