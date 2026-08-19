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


CONTROL_PLANE_TIMEOUT_SECONDS = 10


def probe_control_plane(timeout: float = CONTROL_PLANE_TIMEOUT_SECONDS) -> bool | None:
    """Whether the Gas City supervisor is running.

    This is a SEPARATE question from `probe_city`. `gc stop` brings down the
    supervisor and city controller but leaves the managed Dolt server running
    under its own watchdog, so the data plane keeps answering while nothing is
    left to route work to. Bead reads only need Dolt; dispatch needs both.

    Returns None when `gc` is unavailable, so callers can distinguish "no
    supervisor" from "cannot tell".
    """
    try:
        result = subprocess.run(
            ["gc", "supervisor", "status"],
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode == 0
